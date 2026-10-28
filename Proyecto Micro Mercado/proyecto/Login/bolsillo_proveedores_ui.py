"""UI Bolsillo de proveedores — solo admin."""
import tkinter as tk
from tkinter import ttk
import mensaje as mb

from bolsillo_proveedores_svc import (
    LABEL_BILLETERA,
    acreditar_datafono_pendientes,
    reclasificar_medio_bolsillo,
    registrar_pago_proveedor,
    resumen_bolsillo_proveedores,
)
from cierre_general_svc import es_usuario_admin
from zyntra_ui import *


class BolsilloProveedoresView(tk.Frame):
    def __init__(self, parent, usuario=None, app=None):
        super().__init__(parent, bg=BG)
        self.usuario = usuario or (getattr(app, "usuario", None) if app else None)
        self.app = app
        self._data = {}
        if not es_usuario_admin(self.usuario):
            styled_label(
                self,
                "Acceso denegado: solo el administrador puede gestionar el bolsillo de proveedores.",
                FONT_HEADING,
                DANGER,
                BG,
            ).pack(expand=True)
            return
        self._build()
        self._cargar()

    def on_show(self):
        if es_usuario_admin(self.usuario):
            self._cargar()

    def _build(self):
        top = card_frame(self, padx=12, pady=10)
        top.pack(fill="x", pady=(0, 8))
        styled_label(top, "Proveedores", FONT_HEADING, TEXT, BG_CARD).pack(anchor="w")
        styled_label(
            top,
            "Disponible = efectivo sobrante (post-provisión) + billetera digital. "
            "Datafono → billetera el siguiente día hábil a las 14:00.",
            FONT_SMALL,
            TEXT_DIM,
            BG_CARD,
        ).pack(anchor="w", pady=(2, 8))
        actions = tk.Frame(top, bg=BG_CARD)
        actions.pack(fill="x")
        primary_button(actions, "Registrar pago", self._pago, width=16, height=1).pack(
            side="left", padx=(0, 8)
        )
        secondary_button(actions, "Obligación (crédito)", self._obligacion, width=18, height=1).pack(
            side="left", padx=(0, 8)
        )
        secondary_button(actions, "Corregir medio", self._reclasificar, width=14, height=1).pack(
            side="left", padx=(0, 8)
        )
        secondary_button(actions, "Actualizar", self._cargar, width=12, height=1).pack(side="left")

        self.saldos_box = card_frame(self, padx=12, pady=10)
        self.saldos_box.pack(fill="x", pady=(0, 8))
        self.lbl_ef = styled_label(self.saldos_box, "Efectivo: —", FONT_SUB, TEXT, BG_CARD)
        self.lbl_ef.pack(anchor="w")
        self.lbl_nq = styled_label(
            self.saldos_box, "{}: —".format(LABEL_BILLETERA), FONT_SUB, TEXT, BG_CARD
        )
        self.lbl_nq.pack(anchor="w")
        self.lbl_pend = styled_label(
            self.saldos_box, "Datafono pendiente (T+1 14:00): —", FONT_SUB, WARNING, BG_CARD
        )
        self.lbl_pend.pack(anchor="w")
        self.lbl_disp = styled_label(self.saldos_box, "Disponible: —", FONT_HEADING, CYAN, BG_CARD)
        self.lbl_disp.pack(anchor="w", pady=(6, 0))
        self.lbl_tot = styled_label(self.saldos_box, "Total (disp. + pendiente): —", FONT_SUB, TEXT, BG_CARD)
        self.lbl_tot.pack(anchor="w")
        self.lbl_int = styled_label(self.saldos_box, "", FONT_SMALL, TEXT_DIM, BG_CARD)
        self.lbl_int.pack(anchor="w")

        body = card_frame(self, padx=10, pady=8)
        body.pack(fill="both", expand=True)
        styled_label(body, "Movimientos (auditoría)", FONT_LABEL, TEXT, BG_CARD).pack(anchor="w")
        self.wrap, self.tree = scrollable_tree(
            body,
            columns=("Id", "Fecha", "Tipo", "Metodo", "Monto", "Ef", "Nq", "Dt", "Prov", "User"),
            headings=(
                "ID",
                "Fecha",
                "Tipo",
                "Medio",
                "Monto",
                "Ef",
                "Billetera",
                "Data",
                "Proveedor",
                "Usuario",
            ),
            height=14,
            widths={
                "Id": 45,
                "Fecha": 110,
                "Tipo": 130,
                "Metodo": 100,
                "Monto": 90,
                "Ef": 80,
                "Nq": 80,
                "Dt": 80,
                "Prov": 120,
                "User": 80,
            },
        )
        self.wrap.pack(fill="both", expand=True, pady=(6, 0))

    def _cargar(self):
        try:
            acreditar_datafono_pendientes(usuario_admin=self.usuario or "sistema")
        except Exception:
            pass
        data = resumen_bolsillo_proveedores(self.usuario)
        if data.get("error"):
            mb.showerror("Proveedores", data["error"], parent=self)
            return
        self._data = data
        s = data.get("saldos") or {}
        self.lbl_ef.config(text="Efectivo (sobrante): {}".format(formato_dinero(s.get("efectivo"))))
        self.lbl_nq.config(
            text="{}: {}".format(LABEL_BILLETERA, formato_dinero(s.get("nequi") or s.get("billetera_digital")))
        )
        self.lbl_pend.config(
            text="Datafono pendiente (T+1 14:00): {}".format(
                formato_dinero(s.get("datafono_pendiente"))
            )
        )
        self.lbl_disp.config(text="Disponible: {}".format(formato_dinero(s.get("disponible"))))
        self.lbl_tot.config(
            text="Total (disp. + pendiente): {}".format(formato_dinero(s.get("total")))
        )
        ok = bool(data.get("integridad_ok"))
        self.lbl_int.config(
            text="Integridad OK · pagos permiten saldo negativo + crédito por faltante"
            if ok
            else "ALERTA: integridad de saldos falló",
            fg=SUCCESS if ok else DANGER,
        )
        for i in self.tree.get_children():
            self.tree.delete(i)
        for m in data.get("movimientos") or []:
            metodo = m.get("metodo") or ""
            if metodo == "Nequi":
                metodo = LABEL_BILLETERA
            self.tree.insert(
                "",
                "end",
                values=(
                    m.get("id"),
                    str(m.get("fecha") or "")[:16],
                    m.get("tipo"),
                    metodo,
                    formato_dinero(m.get("monto")),
                    formato_dinero(m.get("efectivo")),
                    formato_dinero(m.get("nequi")),
                    formato_dinero(m.get("datafono")),
                    (m.get("proveedor_nombre") or "")[:24],
                    (m.get("usuario") or "")[:16],
                ),
            )

    def _pago(self):
        self._dialogo_pago(a_credito=False)

    def _obligacion(self):
        self._dialogo_pago(a_credito=True)

    def _dialogo_pago(self, a_credito=False):
        dlg = tk.Toplevel(self)
        titulo = "Obligación a crédito" if a_credito else "Pago / compra a proveedor"
        prepare_modal(dlg, self, titulo, 500, 520 if not a_credito else 380, resizable=True)
        card = card_frame(dlg, padx=14, pady=12)
        card.pack(fill="both", expand=True)
        styled_label(card, titulo, FONT_LABEL, TEXT, BG_CARD).pack(anchor="w")
        if a_credito:
            styled_label(
                card,
                "No descuenta efectivo ni billetera. Solo registra deuda.",
                FONT_SMALL,
                WARNING,
                BG_CARD,
            ).pack(anchor="w", pady=(2, 8))
        else:
            s = self._data.get("saldos") or {}
            styled_label(
                card,
                "Disponible — Ef {} · {} {} · Pend. datafono {}".format(
                    formato_dinero(s.get("efectivo")),
                    LABEL_BILLETERA,
                    formato_dinero(s.get("nequi")),
                    formato_dinero(s.get("datafono_pendiente")),
                ),
                FONT_SMALL,
                TEXT_DIM,
                BG_CARD,
            ).pack(anchor="w", pady=(2, 4))
            styled_label(
                card,
                "Efectivo y billetera van separados. Si no alcanza, el faltante queda a crédito "
                "(la compra no se bloquea; el saldo puede quedar negativo).",
                FONT_SMALL,
                WARNING,
                BG_CARD,
            ).pack(anchor="w", pady=(0, 8))

        vars_ = {
            "prov": tk.StringVar(),
            "total": tk.StringVar(),
            "ef": tk.StringVar(value="0"),
            "nq": tk.StringVar(value="0"),
            "ref": tk.StringVar(),
            "obs": tk.StringVar(),
        }
        for label, key in (
            ("Proveedor", "prov"),
            ("Valor total compra", "total"),
        ):
            row = tk.Frame(card, bg=BG_CARD)
            row.pack(fill="x", pady=2)
            styled_label(row, label, FONT_SMALL, TEXT_DIM, BG_CARD).pack(side="left")
            ttk.Entry(row, textvariable=vars_[key], width=28).pack(side="right")

        if not a_credito:
            styled_label(
                card,
                "Pagado ahora (suma ≤ total; faltante = crédito automático)",
                FONT_SMALL,
                TEXT_DIM,
                BG_CARD,
            ).pack(anchor="w", pady=(8, 2))
            for label, key in (("Efectivo", "ef"), (LABEL_BILLETERA, "nq")):
                row = tk.Frame(card, bg=BG_CARD)
                row.pack(fill="x", pady=2)
                styled_label(row, label, FONT_SMALL, TEXT_DIM, BG_CARD).pack(side="left")
                ttk.Entry(row, textvariable=vars_[key], width=18).pack(side="right")

        for label, key in (("Referencia", "ref"), ("Observación", "obs")):
            row = tk.Frame(card, bg=BG_CARD)
            row.pack(fill="x", pady=2)
            styled_label(row, label, FONT_SMALL, TEXT_DIM, BG_CARD).pack(side="left")
            ttk.Entry(row, textvariable=vars_[key], width=28).pack(side="right")

        def _parse(v):
            try:
                return round(float(str(v).replace(",", "").replace("$", "").strip() or 0), 2)
            except (TypeError, ValueError):
                return 0.0

        def guardar():
            nombre = vars_["prov"].get().strip()
            total = _parse(vars_["total"].get())
            if a_credito:
                ok, msg, _ = registrar_pago_proveedor(
                    self.usuario,
                    nombre,
                    total,
                    [],
                    referencia=vars_["ref"].get().strip(),
                    observacion=vars_["obs"].get().strip(),
                    a_credito=True,
                )
            else:
                origenes = [
                    {"metodo": "Efectivo", "monto": _parse(vars_["ef"].get())},
                    {"metodo": "Nequi", "monto": _parse(vars_["nq"].get())},
                ]
                origenes = [o for o in origenes if o["monto"] > 0]
                ok, msg, _ = registrar_pago_proveedor(
                    self.usuario,
                    nombre,
                    total,
                    origenes,
                    referencia=vars_["ref"].get().strip(),
                    observacion=vars_["obs"].get().strip(),
                    a_credito=False,
                )
            if ok:
                mb.showinfo("Proveedores", msg, parent=dlg)
                dlg.destroy()
                self._cargar()
            else:
                mb.showerror("Proveedores", msg, parent=dlg)

        primary_button(card, "Guardar", guardar, width=14, height=1).pack(anchor="w", pady=(14, 0))

    def _reclasificar(self):
        dlg = tk.Toplevel(self)
        prepare_modal(dlg, self, "Corregir medio en bolsillo", 440, 340, resizable=True)
        card = card_frame(dlg, padx=14, pady=12)
        card.pack(fill="both", expand=True)
        styled_label(
            card,
            "Mueve saldo entre Efectivo y Billetera digital (auditoría).",
            FONT_SMALL,
            TEXT_DIM,
            BG_CARD,
        ).pack(anchor="w", pady=(0, 8))
        origen = tk.StringVar(value="Efectivo")
        destino = tk.StringVar(value=LABEL_BILLETERA)
        monto = tk.StringVar()
        obs = tk.StringVar()
        opciones = ["Efectivo", LABEL_BILLETERA]
        for label, var, is_cmb in (
            ("Desde", origen, True),
            ("Hacia", destino, True),
            ("Monto", monto, False),
            ("Motivo", obs, False),
        ):
            row = tk.Frame(card, bg=BG_CARD)
            row.pack(fill="x", pady=3)
            styled_label(row, label, FONT_SMALL, TEXT_DIM, BG_CARD).pack(side="left")
            if is_cmb:
                ttk.Combobox(
                    row, textvariable=var, values=opciones, width=22, state="readonly"
                ).pack(side="right")
            else:
                ttk.Entry(row, textvariable=var, width=20).pack(side="right")

        def guardar():
            try:
                m = round(float(str(monto.get()).replace(",", "").strip() or 0), 2)
            except (TypeError, ValueError):
                m = 0
            ok, msg, _ = reclasificar_medio_bolsillo(
                self.usuario,
                origen.get(),
                destino.get(),
                m,
                observacion=obs.get().strip() or "Corrección auditada",
            )
            if ok:
                mb.showinfo("Proveedores", msg, parent=dlg)
                dlg.destroy()
                self._cargar()
            else:
                mb.showerror("Proveedores", msg, parent=dlg)

        primary_button(card, "Aplicar", guardar, width=12, height=1).pack(anchor="w", pady=(12, 0))
