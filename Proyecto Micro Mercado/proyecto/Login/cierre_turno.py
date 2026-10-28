"""Cierre diario con conciliación de medios de pago (Entrega 1)."""
import tkinter as tk
from tkinter import ttk
from datetime import datetime
import mensaje as mb

from Consultas import (
    guardar_cierre_turno,
    marcar_ticket_cierre_impreso,
    resumen_conciliacion_turno,
    listar_ventas_turno_pagos,
    reclasificar_pago_venta,
    calcular_estado_cierre,
    MEDIOS_RECLASIFICABLES,
    obtener_config_pos,
    listar_correcciones_cierre,
)
from Resumen_Cierre import generar_resumen
from ticket import imprimir_ticket_cierre
from zyntra_ui import *
import usuarios


def _a_float(texto):
    return parse_dinero(texto)


def _sumar_metodo(ventas, metodo):
    total = 0.0
    for venta in ventas or []:
        pagos = venta.get("pagos") or {}
        total += float(pagos.get(metodo, 0) or 0)
    return total


class CierreTurnoOverlay(tk.Frame):
    def __init__(self, parent, app, on_close, modo="definitivo"):
        super().__init__(parent, bg="#07090F")
        self.app = app
        self.on_close = on_close
        self.modo = "temporal" if str(modo).lower().startswith("temp") else "definitivo"
        self.datos = {}
        self.entries_decl = {}
        self.correcciones_sesion = 0
        self.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.lift()
        self._mostrar_conciliacion()

    # ---- helpers de turno ----
    def _nombre_cajero(self):
        try:
            return usuarios.usuarios.Obtener_Nombre_Empleado(self.app.usuario) or self.app.usuario
        except Exception:
            return self.app.usuario

    def _fecha_desde(self):
        inicio = getattr(self.app, "turno_inicio", None) or datetime.now()
        return inicio.strftime("%Y-%m-%d %H:%M:%S") if hasattr(inicio, "strftime") else str(inicio)

    def _cargar_resumen_sistema(self):
        fecha_desde = self._fecha_desde()
        nombre = self._nombre_cajero()
        resumen = resumen_conciliacion_turno(
            fecha_desde,
            getattr(self.app, "id_empleado", None),
            getattr(self.app, "usuario", None),
            nombre,
        )
        # Preferir memoria del turno si hay ventas locales
        ventas = [v for v in (getattr(self.app, "ventas_turno", []) or []) if not v.get("anulada")]
        if ventas:
            ef = _sumar_metodo(ventas, "Efectivo")
            neq = _sumar_metodo(ventas, "Nequi") + _sumar_metodo(ventas, "Transferencia")
            tar = _sumar_metodo(ventas, "Tarjeta")
            cred = _sumar_metodo(ventas, "Crédito")
            total_ventas = sum(float(v.get("total", 0) or 0) for v in ventas)
            articulos = sum(int(v.get("articulos", 0) or 0) for v in ventas)
            tickets = len(ventas)
            medios = resumen["medios"]
            # Mantener ajustes de caja (abonos/entradas/salidas) sobre efectivo
            abonos = float(resumen.get("abonos_efectivo") or 0)
            entradas = float(resumen.get("entradas") or 0)
            salidas = float(resumen.get("salidas") or 0)
            medios["Efectivo"] = {
                "metodo": "Efectivo",
                "etiqueta": "EFECTIVO",
                "sistema": round(ef + abonos + entradas - salidas, 2),
                "sistema_ventas": round(ef, 2),
                "abonos": abonos,
                "entradas": entradas,
                "salidas": salidas,
            }
            medios["Nequi"] = {
                "metodo": "Nequi",
                "etiqueta": "NEQUI",
                "sistema": round(neq + float(resumen.get("abonos_otros") or 0), 2),
            }
            medios["Tarjeta"] = {
                "metodo": "Tarjeta",
                "etiqueta": "DATAFONO",
                "sistema": round(tar, 2),
            }
            if cred > 0:
                medios["Crédito"] = {
                    "metodo": "Crédito",
                    "etiqueta": "CRÉDITO",
                    "sistema": round(cred, 2),
                }
            resumen["medios"] = medios
            resumen["total_ventas"] = total_ventas
            resumen["tickets"] = tickets
            resumen["articulos"] = articulos
            resumen["credito"] = cred
            raw = dict(resumen.get("metodos_raw") or {})
            raw["Efectivo"] = ef
            raw["Nequi"] = _sumar_metodo(ventas, "Nequi")
            raw["Transferencia"] = _sumar_metodo(ventas, "Transferencia")
            raw["Tarjeta"] = tar
            raw["Crédito"] = cred
            resumen["metodos_raw"] = raw
        return resumen

    # ---- UI: conciliación ----
    def _mostrar_conciliacion(self):
        for child in list(self.winfo_children()):
            child.destroy()
        self.resumen = self._cargar_resumen_sistema()
        card = card_frame(self, padx=28, pady=22)
        card.place(relx=0.5, rely=0.5, anchor="center")

        titulo = "Arqueo temporal" if self.modo == "temporal" else "Cierre diario — Conciliación"
        styled_label(card, titulo, FONT_HEADING, TEXT, BG_CARD).pack(anchor="w")
        styled_label(
            card,
            "Compare el valor del sistema con lo verificado en caja (EFECTIVO, NEQUI, DATAFONO).",
            FONT_SMALL,
            TEXT_DIM,
            BG_CARD,
        ).pack(anchor="w", pady=(4, 12))

        info = tk.Frame(card, bg=BG_ELEVATED, padx=12, pady=8)
        info.pack(fill="x", pady=(0, 10))
        styled_label(
            info,
            "Ventas {}  ·  Tickets {}  ·  Cajero {}".format(
                formato_dinero(self.resumen.get("total_ventas", 0)),
                self.resumen.get("tickets", 0),
                self._nombre_cajero(),
            ),
            FONT_SMALL,
            TEXT,
            BG_ELEVATED,
        ).pack(anchor="w")

        head = tk.Frame(card, bg=BG_CARD)
        head.pack(fill="x", pady=(0, 4))
        for i, txt in enumerate(("Medio", "Sistema", "Declarado", "Diferencia")):
            styled_label(head, txt, FONT_SMALL, TEXT_DIM, BG_CARD).grid(
                row=0, column=i, sticky="w", padx=6
            )
            head.columnconfigure(i, weight=1)

        self.entries_decl = {}
        self.lbl_diffs = {}
        body = tk.Frame(card, bg=BG_CARD)
        body.pack(fill="x")
        medios = self.resumen.get("medios") or {}
        # Orden: EFECTIVO, NEQUI, DATAFONO, luego otros
        orden = ["Efectivo", "Nequi", "Tarjeta"]
        for k in medios:
            if k not in orden:
                orden.append(k)
        for row_i, clave in enumerate(orden):
            info_m = medios.get(clave) or {}
            sistema = float(info_m.get("sistema") or 0)
            etiqueta = info_m.get("etiqueta") or clave.upper()
            row = tk.Frame(body, bg=BG_ELEVATED, padx=8, pady=8)
            row.pack(fill="x", pady=3)
            styled_label(row, etiqueta, FONT_SUB, TEXT, BG_ELEVATED).grid(row=0, column=0, sticky="w", padx=4)
            styled_label(row, formato_dinero(sistema), FONT_SUB, CYAN, BG_ELEVATED).grid(
                row=0, column=1, sticky="w", padx=4
            )
            entry = styled_entry(row, width=14, font=("Segoe UI", 14), justify="right")
            entry.grid(row=0, column=2, sticky="ew", padx=4)
            bind_money_entry(entry)
            entry.delete(0, "end")
            entry.insert(0, formato_entrada(str(int(sistema))) if abs(sistema - int(sistema)) < 0.001 else formato_entrada(str(sistema)))
            entry.bind("<KeyRelease>", lambda _e: self._actualizar_diffs())
            self.entries_decl[clave] = entry
            lbl_diff = styled_label(row, formato_dinero(0), FONT_SUB, SUCCESS, BG_ELEVATED)
            lbl_diff.grid(row=0, column=3, sticky="w", padx=4)
            self.lbl_diffs[clave] = lbl_diff
            for c in range(4):
                row.columnconfigure(c, weight=1)
            # Solo EFECTIVO/NEQUI/DATAFONO son editables de verificación; crédito informativo
            if clave == "Crédito":
                entry.configure(state="disabled")

        self.lbl_estado_prev = styled_label(card, "", FONT_SMALL, TEXT_DIM, BG_CARD)
        self.lbl_estado_prev.pack(anchor="w", pady=(10, 4))
        self._actualizar_diffs()

        actions = tk.Frame(card, bg=BG_CARD)
        actions.pack(fill="x", pady=(12, 0))
        primary_button(actions, "Continuar", self._ir_observacion_o_reclasificar, width=16).pack(
            side="left", padx=(0, 8)
        )
        if self.modo == "definitivo":
            secondary_button(actions, "Reclasificar pagos", self._mostrar_reclasificacion, width=18).pack(
                side="left", padx=(0, 8)
            )
        danger_button(actions, "Cancelar", self._cancelar, width=12).pack(side="left")

    def _leer_declarados(self):
        declared = {}
        for clave, entry in self.entries_decl.items():
            try:
                state = str(entry.cget("state"))
            except Exception:
                state = "normal"
            if state == "disabled":
                sistema = float((self.resumen.get("medios") or {}).get(clave, {}).get("sistema") or 0)
                declared[clave] = sistema
            else:
                declared[clave] = _a_float(entry.get())
        return declared

    def _actualizar_diffs(self):
        declared = self._leer_declarados()
        diffs = []
        for clave, entry in self.entries_decl.items():
            sistema = float((self.resumen.get("medios") or {}).get(clave, {}).get("sistema") or 0)
            declarado = float(declared.get(clave) or 0)
            diff = round(declarado - sistema, 2)
            diffs.append(diff)
            lbl = self.lbl_diffs.get(clave)
            if not lbl:
                continue
            color = SUCCESS if abs(diff) < 0.5 else (WARNING if diff > 0 else DANGER)
            signo = "+" if diff > 0.009 else ""
            lbl.configure(text="{}{}".format(signo, formato_dinero(diff)), fg=color)
        corr = int(self.resumen.get("correcciones") or 0) + self.correcciones_sesion
        estado = calcular_estado_cierre(diffs, corr)
        self.lbl_estado_prev.configure(
            text="Estado preliminar: {}  ·  Correcciones en turno: {}".format(estado, corr)
        )

    def _construir_datos(self, observacion=""):
        declared = self._leer_declarados()
        medios_list = []
        diffs = []
        for clave, info in (self.resumen.get("medios") or {}).items():
            sistema = float(info.get("sistema") or 0)
            declarado = float(declared.get(clave) or 0)
            diff = round(declarado - sistema, 2)
            diffs.append(diff)
            medios_list.append(
                {
                    "metodo": clave,
                    "etiqueta": info.get("etiqueta") or clave.upper(),
                    "sistema": sistema,
                    "declarado": declarado,
                    "diferencia": diff,
                }
            )
        corr = int(self.resumen.get("correcciones") or 0) + self.correcciones_sesion
        estado = calcular_estado_cierre(diffs, corr)
        ef_decl = float(declared.get("Efectivo") or 0)
        ef_sys = float((self.resumen.get("medios") or {}).get("Efectivo", {}).get("sistema") or 0)
        raw = self.resumen.get("metodos_raw") or {}
        nequi_sys = float((self.resumen.get("medios") or {}).get("Nequi", {}).get("sistema") or 0)
        tar_sys = float((self.resumen.get("medios") or {}).get("Tarjeta", {}).get("sistema") or 0)
        # Guardar Nequi declarado en columna Nequi; Transferencia histórica en Transferencia
        nequi_decl = float(declared.get("Nequi") or 0)
        return {
            "cajero": self._nombre_cajero(),
            "usuario": self.app.usuario,
            "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "inicio": self._fecha_desde(),
            "monto_inicial": float(getattr(self.app, "monto_inicial", 0) or 0),
            "conteo_fisico": ef_decl,
            "esperado": ef_sys,
            "descuadre": round(ef_decl - ef_sys, 2),
            "total_ventas": float(self.resumen.get("total_ventas") or 0),
            "articulos": int(self.resumen.get("articulos") or 0),
            "Efectivo": float((self.resumen.get("medios") or {}).get("Efectivo", {}).get("sistema_ventas")
                              or raw.get("Efectivo") or 0),
            "Nequi": float(raw.get("Nequi") or 0) if float(raw.get("Nequi") or 0) > 0 else nequi_sys,
            "Tarjeta": tar_sys,
            "Transferencia": float(raw.get("Transferencia") or 0),
            "Crédito": float(self.resumen.get("credito") or 0),
            "abonos": float(self.resumen.get("abonos_efectivo") or 0),
            "abonos_otros": float(self.resumen.get("abonos_otros") or 0),
            "entradas": float(self.resumen.get("entradas") or 0),
            "salidas": float(self.resumen.get("salidas") or 0),
            "tickets": int(self.resumen.get("tickets") or 0),
            "tipo": self.modo,
            "efectivo_retirar": max(ef_sys, 0),
            "base_dejada": float(getattr(self.app, "monto_inicial", 0) or 0),
            "estado": estado,
            "observacion": observacion,
            "correcciones": corr,
            "medios_conciliacion": medios_list,
            "nequi_declarado": nequi_decl,
            "tarjeta_declarado": float(declared.get("Tarjeta") or 0),
            "linea_tiempo": [],
        }

    def _ir_observacion_o_reclasificar(self):
        datos = self._construir_datos()
        if datos["estado"] == "CON_DESCUADRE":
            self._mostrar_observacion(datos)
        else:
            self._mostrar_confirmacion(datos)

    # ---- observación obligatoria ----
    def _mostrar_observacion(self, datos):
        self.datos = datos
        for child in list(self.winfo_children()):
            child.destroy()
        card = card_frame(self, padx=28, pady=22)
        card.place(relx=0.5, rely=0.5, anchor="center")
        styled_label(card, "Descuadre detectado", FONT_HEADING, WARNING, BG_CARD).pack(anchor="w")
        styled_label(
            card,
            "El cierre NO se bloquea, pero debe explicar la diferencia.",
            FONT_SMALL,
            TEXT_DIM,
            BG_CARD,
        ).pack(anchor="w", pady=(4, 12))

        for linea in datos.get("medios_conciliacion") or []:
            if abs(float(linea.get("diferencia") or 0)) < 0.5:
                continue
            box = tk.Frame(card, bg=BG_ELEVATED, padx=10, pady=6)
            box.pack(fill="x", pady=2)
            diff = float(linea["diferencia"])
            signo = "+" if diff > 0 else ""
            styled_label(
                box,
                "{}  Sistema {}  ·  Declarado {}  ·  Diff {}{}".format(
                    linea.get("etiqueta"),
                    formato_dinero(linea.get("sistema")),
                    formato_dinero(linea.get("declarado")),
                    signo,
                    formato_dinero(diff),
                ),
                FONT_SMALL,
                TEXT,
                BG_ELEVATED,
            ).pack(anchor="w")

        styled_label(card, "Observación / explicación *", FONT_LABEL, TEXT_MUTED, BG_CARD).pack(
            anchor="w", pady=(12, 4)
        )
        self.txt_obs = tk.Text(card, height=4, width=52, bg=BG_INPUT, fg=TEXT, insertbackground=TEXT,
                               font=FONT_BODY, relief="flat", wrap="word")
        self.txt_obs.pack(fill="x")
        actions = tk.Frame(card, bg=BG_CARD)
        actions.pack(fill="x", pady=(14, 0))
        primary_button(actions, "Continuar", self._confirmar_observacion, width=16).pack(
            side="left", padx=(0, 8)
        )
        danger_button(actions, "Volver", self._mostrar_conciliacion, width=12).pack(side="left")

    def _confirmar_observacion(self):
        texto = (self.txt_obs.get("1.0", "end") or "").strip()
        if len(texto) < 5:
            mb.showwarning(
                "Observación requerida",
                "Escriba una explicación de la diferencia (mínimo 5 caracteres).",
                parent=self,
            )
            return
        self.datos["observacion"] = texto
        self._mostrar_confirmacion(self.datos)

    # ---- reclasificación ----
    def _mostrar_reclasificacion(self):
        for child in list(self.winfo_children()):
            child.destroy()
        card = card_frame(self, padx=24, pady=20)
        card.place(relx=0.5, rely=0.5, anchor="center")
        styled_label(card, "Reclasificar medio de pago", FONT_HEADING, TEXT, BG_CARD).pack(anchor="w")
        styled_label(
            card,
            "El total de la venta no cambia. Solo se mueve el monto entre medios (queda auditado).",
            FONT_SMALL,
            TEXT_DIM,
            BG_CARD,
        ).pack(anchor="w", pady=(4, 10))

        ventas = listar_ventas_turno_pagos(
            self._fecha_desde(), getattr(self.app, "id_empleado", None), limite=60
        )
        if not ventas:
            styled_label(card, "No hay ventas en este turno.", FONT_BODY, TEXT_DIM, BG_CARD).pack(
                anchor="w", pady=8
            )
            secondary_button(card, "Volver", self._mostrar_conciliacion, width=14).pack(anchor="w")
            return

        lista_frame = tk.Frame(card, bg=BG_CARD)
        lista_frame.pack(fill="both", expand=True)
        canvas = tk.Canvas(lista_frame, bg=BG_CARD, highlightthickness=0, height=220)
        scroll = tk.Scrollbar(lista_frame, orient="vertical", command=canvas.yview)
        inner = tk.Frame(canvas, bg=BG_CARD)
        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=scroll.set)
        canvas.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        self._venta_sel = tk.IntVar(value=int(ventas[0]["id_venta"]))
        for v in ventas:
            pagos_txt = ", ".join(
                "{} {}".format(m, formato_dinero(monto)) for m, monto in (v.get("pagos") or {}).items()
            ) or "(sin pagos)"
            row = tk.Frame(inner, bg=BG_ELEVATED, padx=8, pady=6)
            row.pack(fill="x", pady=2)
            tk.Radiobutton(
                row,
                text="#{}  {}  ·  {}".format(v["id_venta"], formato_dinero(v["total"]), pagos_txt),
                variable=self._venta_sel,
                value=int(v["id_venta"]),
                bg=BG_ELEVATED,
                fg=TEXT,
                selectcolor=BG_INPUT,
                activebackground=BG_ELEVATED,
                activeforeground=TEXT,
                font=FONT_SMALL,
                anchor="w",
                justify="left",
            ).pack(fill="x")

        form = tk.Frame(card, bg=BG_CARD)
        form.pack(fill="x", pady=(12, 0))
        styled_label(form, "Desde", FONT_SMALL, TEXT_DIM, BG_CARD).grid(row=0, column=0, sticky="w")
        styled_label(form, "Hacia", FONT_SMALL, TEXT_DIM, BG_CARD).grid(row=0, column=1, sticky="w", padx=8)
        styled_label(form, "Monto", FONT_SMALL, TEXT_DIM, BG_CARD).grid(row=0, column=2, sticky="w")
        self.cmb_desde = ttk.Combobox(form, values=list(MEDIOS_RECLASIFICABLES), state="readonly", width=14)
        self.cmb_desde.set("Efectivo")
        self.cmb_desde.grid(row=1, column=0, sticky="w")
        self.cmb_hacia = ttk.Combobox(form, values=list(MEDIOS_RECLASIFICABLES), state="readonly", width=14)
        self.cmb_hacia.set("Nequi")
        self.cmb_hacia.grid(row=1, column=1, sticky="w", padx=8)
        self.entry_monto_rec = styled_entry(form, width=12)
        self.entry_monto_rec.grid(row=1, column=2, sticky="w")
        bind_money_entry(self.entry_monto_rec)
        styled_label(card, "Motivo *", FONT_SMALL, TEXT_DIM, BG_CARD).pack(anchor="w", pady=(10, 2))
        self.entry_motivo = styled_entry(card, width=48)
        self.entry_motivo.pack(fill="x")

        actions = tk.Frame(card, bg=BG_CARD)
        actions.pack(fill="x", pady=(14, 0))
        primary_button(actions, "Aplicar corrección", self._aplicar_reclasificacion, width=18).pack(
            side="left", padx=(0, 8)
        )
        secondary_button(actions, "Volver a conciliación", self._mostrar_conciliacion, width=20).pack(
            side="left"
        )

    def _aplicar_reclasificacion(self):
        id_venta = int(self._venta_sel.get())
        origen = self.cmb_desde.get()
        destino = self.cmb_hacia.get()
        monto = _a_float(self.entry_monto_rec.get())
        motivo = (self.entry_motivo.get() or "").strip()
        ok, msg = reclasificar_pago_venta(
            id_venta, origen, destino, monto, self.app.usuario, motivo
        )
        if not ok:
            mb.showerror("Reclasificación", msg, parent=self)
            return
        self.correcciones_sesion += 1
        # Actualizar memoria del turno si existe
        for v in getattr(self.app, "ventas_turno", []) or []:
            if int(v.get("id_venta") or 0) == id_venta:
                pagos = dict(v.get("pagos") or {})
                pagos[origen] = round(float(pagos.get(origen) or 0) - monto, 2)
                if pagos[origen] <= 0.009:
                    pagos.pop(origen, None)
                pagos[destino] = round(float(pagos.get(destino) or 0) + monto, 2)
                v["pagos"] = pagos
                break
        mb.showinfo("Listo", msg, parent=self)
        self._mostrar_reclasificacion()

    # ---- confirmación ----
    def _mostrar_confirmacion(self, datos):
        self.datos = datos
        for child in list(self.winfo_children()):
            child.destroy()
        card = card_frame(self, padx=28, pady=22)
        card.place(relx=0.5, rely=0.5, anchor="center")
        styled_label(
            card,
            "Confirmar cierre" if self.modo == "definitivo" else "Confirmar arqueo temporal",
            FONT_HEADING,
            TEXT,
            BG_CARD,
        ).pack(anchor="w")

        estado = datos.get("estado") or "CUADRADO"
        color = SUCCESS if estado.startswith("CUADRADO") else WARNING
        banner = tk.Frame(card, bg=BG_ELEVATED, padx=12, pady=10)
        banner.pack(fill="x", pady=(10, 10))
        styled_label(banner, "Estado del cierre", FONT_SMALL, TEXT_DIM, BG_ELEVATED).pack(anchor="w")
        styled_label(banner, estado, ("Segoe UI", 18, "bold"), color, BG_ELEVATED).pack(anchor="w")
        if datos.get("observacion"):
            styled_label(
                banner,
                "Obs: {}".format(datos["observacion"][:180]),
                FONT_SMALL,
                TEXT,
                BG_ELEVATED,
            ).pack(anchor="w", pady=(6, 0))

        grid = tk.Frame(card, bg=BG_CARD)
        grid.pack(fill="x")
        for i, linea in enumerate(datos.get("medios_conciliacion") or []):
            box = tk.Frame(grid, bg=BG_ELEVATED, padx=10, pady=8)
            box.grid(row=i // 2, column=i % 2, sticky="nsew", padx=4, pady=4)
            diff = float(linea.get("diferencia") or 0)
            styled_label(box, linea.get("etiqueta"), FONT_SMALL, TEXT_DIM, BG_ELEVATED).pack(anchor="w")
            styled_label(
                box,
                "Sis {}  ·  Decl {}  ·  Diff {}".format(
                    formato_dinero(linea.get("sistema")),
                    formato_dinero(linea.get("declarado")),
                    formato_dinero(diff),
                ),
                FONT_SMALL,
                TEXT,
                BG_ELEVATED,
            ).pack(anchor="w")
        grid.columnconfigure(0, weight=1)
        grid.columnconfigure(1, weight=1)

        actions = tk.Frame(card, bg=BG_CARD)
        actions.pack(fill="x", pady=(14, 0))
        if self.modo == "temporal":
            primary_button(
                actions, "Confirmar, imprimir y cerrar sesión", self._cerrar_temporal, width=30
            ).pack(side="left", padx=(0, 8))
            danger_button(actions, "Volver", self._mostrar_conciliacion, width=10).pack(side="left")
        else:
            styled_label(
                card,
                "El ticket se imprime siempre: adjúntelo al dinero en la caja fuerte.",
                FONT_SMALL,
                TEXT_DIM,
                BG_CARD,
            ).pack(anchor="w", pady=(4, 0))
            primary_button(
                actions, "Cerrar e imprimir ticket", self._cerrar_imprimir, width=22
            ).pack(side="left", padx=(0, 8))
            danger_button(actions, "Volver", self._mostrar_conciliacion, width=10).pack(side="left")

    def _imprimir_ticket_cierre(self, datos, cierre_id):
        payload = dict(datos or {})
        payload["cierre_id"] = cierre_id
        payload["id"] = cierre_id
        try:
            if not payload.get("lista_correcciones") and cierre_id:
                payload["lista_correcciones"] = listar_correcciones_cierre(
                    cierre_id=cierre_id, limite=50
                )
        except Exception:
            payload["lista_correcciones"] = []
        path, _texto, ok_print = imprimir_ticket_cierre(payload, ancho_mm=80, enviar_cola=True)
        if ok_print:
            marcar_ticket_cierre_impreso(cierre_id, True)
        else:
            marcar_ticket_cierre_impreso(cierre_id, False)
        return path, ok_print

    def _finalizar(self, imprimir=True):
        # Siempre se intenta imprimir el ticket de caja fuerte (no hay cierre sin impresión).
        self.datos["tipo"] = self.modo
        self.datos["ticket_impreso"] = 0
        try:
            from turno_linea_tiempo import (
                obtener_linea_tiempo_turno,
                registrar_evento_turno,
                linea_tiempo_a_json,
            )

            registrar_evento_turno(self.app, "cierre_definitivo")
            self.datos["linea_tiempo"] = obtener_linea_tiempo_turno(self.app)
            self.datos["linea_tiempo_json"] = linea_tiempo_a_json(self.datos["linea_tiempo"])
        except Exception as error:
            print("Aviso línea tiempo cierre: {}".format(error))
        try:
            cfg = obtener_config_pos()
            self.datos.setdefault("pct_proveedores", cfg.get("pct_proveedores", 65))
            self.datos.setdefault("pct_provisiones", cfg.get("pct_provisiones", 17))
            self.datos.setdefault("pct_utilidad", cfg.get("pct_utilidad", 18))
        except Exception:
            pass
        if self.datos.get("estado") == "CON_DESCUADRE" and len(str(self.datos.get("observacion") or "").strip()) < 5:
            mb.showwarning("Observación", "Falta la explicación del descuadre.", parent=self)
            self._mostrar_observacion(self.datos)
            return
        try:
            cierre_id = guardar_cierre_turno(self.datos)
        except Exception as error:
            mb.showerror("Error", "No se pudo guardar el cierre: {}".format(error), parent=self)
            return
        if not cierre_id:
            mb.showerror("Error", "No se pudo guardar el cierre.", parent=self)
            return
        try:
            cierre_id = int(cierre_id)
        except (TypeError, ValueError):
            cierre_id = 0

        path_ticket = None
        ok_print = False
        try:
            path_ticket, ok_print = self._imprimir_ticket_cierre(self.datos, cierre_id)
        except Exception as error:
            mb.showerror(
                "Impresión",
                "El cierre se guardó (#{}), pero falló el ticket:\n{}\n\n"
                "Podrá reimprimirlo en el siguiente turno o un administrador.".format(
                    cierre_id, error
                ),
                parent=self,
            )
            ok_print = False

        # PDF de respaldo (opcional, no sustituye el ticket térmico)
        try:
            self.datos["cierre_id"] = cierre_id
            generar_resumen(self.datos)
        except Exception:
            pass

        if ok_print:
            mb.showinfo(
                "Cierre e impresión",
                "Cierre #{} guardado.\nTicket enviado a la impresora.\n"
                "Adjúntelo al dinero en la caja fuerte.\n\nArchivo: {}".format(
                    cierre_id, path_ticket or "-"
                ),
                parent=self,
            )
        else:
            mb.showwarning(
                "Ticket pendiente",
                "Cierre #{} guardado, pero el ticket NO se imprimió "
                "(papel, impresora o energía).\n\n"
                "Reimprima el ticket en el próximo turno o pídale al administrador.".format(
                    cierre_id
                ),
                parent=self,
            )

        self._volver_a_login(limpiar_timeline=True)

    def _cerrar_temporal(self):
        self.datos["tipo"] = "temporal"
        self.datos["ticket_impreso"] = 0
        try:
            from turno_linea_tiempo import (
                obtener_linea_tiempo_turno,
                registrar_evento_turno,
                linea_tiempo_a_json,
            )

            registrar_evento_turno(self.app, "cierre_temporal")
            self.datos["linea_tiempo"] = obtener_linea_tiempo_turno(self.app)
            self.datos["linea_tiempo_json"] = linea_tiempo_a_json(self.datos["linea_tiempo"])
        except Exception as error:
            print("Aviso línea tiempo temporal: {}".format(error))
        try:
            cierre_id = guardar_cierre_turno(self.datos)
        except Exception:
            cierre_id = None
        try:
            if cierre_id:
                self._imprimir_ticket_cierre(self.datos, int(cierre_id))
        except Exception:
            pass
        mb.showinfo(
            "Arqueo temporal",
            "Retire {} de sus ventas y deje {} de base en el gabinete.\n\n"
            "Estado: {}\n\nLa sesión volverá al login para que otro cajero pueda abrir.".format(
                formato_dinero(self.datos.get("efectivo_retirar", 0)),
                formato_dinero(self.datos.get("base_dejada", 0)),
                self.datos.get("estado") or "-",
            ),
            parent=self,
        )
        self._volver_a_login(limpiar_timeline=False)

    def _volver_a_login(self, limpiar_timeline=False):
        """Cierra el turno/sesión de UI y vuelve al login sin cerrar la aplicación."""
        callback = self.on_close
        try:
            self.destroy()
        except Exception:
            pass
        if callback:
            try:
                callback()
            except Exception:
                pass
        app = self.app
        if limpiar_timeline:
            try:
                from turno_linea_tiempo import limpiar_linea_tiempo_turno

                limpiar_linea_tiempo_turno(app)
            except Exception:
                pass
        app.usuario = None
        app.es_admin = False
        app.id_empleado = None
        app.monto_inicial = 0.0
        app.turno_inicio = None
        app.ventas_turno = []
        app.shell = None
        app._permitir_salida = False
        app.show_login()

    def _cerrar_imprimir(self):
        self._finalizar(True)

    def _cancelar(self):
        callback = self.on_close
        self.destroy()
        if callback:
            callback()
