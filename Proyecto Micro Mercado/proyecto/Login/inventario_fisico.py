import tkinter as tk
from tkinter import ttk
import mensaje as mb
import Consultas
from zyntra_ui import *


def _fmt_qty(valor):
    try:
        n = float(valor or 0)
    except (TypeError, ValueError):
        return "—"
    if abs(n - round(n)) < 0.001:
        return str(int(round(n)))
    return "{:.2f}".format(n)


class InventarioFisico:
    """Conteo cíclico asistido: muestra stock del sistema y guía producto a producto."""

    def __init__(self, parent=None, usuario=None):
        self.usuario = usuario or ""
        self.win = tk.Toplevel(parent) if parent else tk.Toplevel()
        prepare_modal(self.win, parent, "Inventario físico", 1100, 720, resizable=True)
        limit_minsize(self.win, 900, 560)
        self.sesion_id = None
        self.item_actual = None
        self._silenciar_cola = False
        self._items_cache = []
        self._mostrar_inicio()

    def _limpiar(self):
        for child in list(self.win.winfo_children()):
            child.destroy()

    # ── Pantalla inicio ─────────────────────────────────────────────
    def _mostrar_inicio(self):
        self._limpiar()
        self.sesion_id = None
        self.item_actual = None
        # Solo tablas de conteo (rápido). No correr ensure_schema() completo aquí.
        Consultas.ensure_inventario_fisico_schema()

        footer = card_frame(self.win, padx=14, pady=10)
        footer.pack(side="bottom", fill="x", padx=12, pady=12)
        primary_button(footer, "Nueva sesión", self._dialogo_nueva, width=16, height=1).pack(
            side="left", padx=(0, 8)
        )
        secondary_button(
            footer, "Continuar seleccionada", self._continuar_seleccion, width=20, height=1
        ).pack(side="left", padx=(0, 8))
        danger_button(footer, "Cerrar", self.win.destroy, width=12, height=1).pack(side="right")

        # Frame simple: scrollable_body + tree autofit provocaba CreateDIBSection / cuelgue.
        card = card_frame(self.win, padx=16, pady=12)
        card.pack(fill="both", expand=True, padx=12, pady=(12, 0))
        styled_label(card, "Inventario físico (asistido)", FONT_HEADING, TEXT, BG_CARD).pack(anchor="w")
        styled_label(
            card,
            "Compare existencia del sistema vs física. Puede pausar y continuar otro día hasta el 100%.",
            FONT_SMALL,
            TEXT_DIM,
            BG_CARD,
        ).pack(anchor="w", pady=(2, 10))

        styled_label(card, "Sesiones", FONT_SUB, CYAN, BG_CARD).pack(anchor="w")
        self.list_wrap, self.tree = scrollable_tree(
            card,
            columns=("Id", "Nombre", "Filtro", "Estado", "Avance", "Pct", "Inicio", "Usuario"),
            headings=("ID", "Nombre", "Filtro", "Estado", "Avance", "%", "Inicio", "Usuario"),
            height=14,
            widths={
                "Id": 50,
                "Nombre": 200,
                "Filtro": 160,
                "Estado": 80,
                "Avance": 90,
                "Pct": 50,
                "Inicio": 140,
                "Usuario": 100,
            },
            autofit=False,
        )
        self.list_wrap.pack(fill="both", expand=True, pady=(6, 0))
        self.tree.bind("<Double-1>", lambda _e: self._continuar_seleccion())
        self.win.after(30, self._cargar_sesiones)

    def _cargar_sesiones(self):
        try:
            if not hasattr(self, "tree") or not self.tree.winfo_exists():
                return
            self.tree.delete(*self.tree.get_children())
            for s in Consultas.listar_sesiones_inventario(limite=50):
                filtro = "Todos"
                if s["filtro_tipo"] == "categoria":
                    filtro = "Cat: {}".format(s["filtro_valor"] or "—")
                elif s["filtro_tipo"] == "ubicacion":
                    filtro = "Ubi: {}".format(s["filtro_valor"] or "—")
                self.tree.insert(
                    "",
                    "end",
                    values=(
                        s["id"],
                        s["nombre"],
                        filtro,
                        s["estado"],
                        "{}/{}".format(s["contados"], s["total"]),
                        "{}%".format(s["pct"]),
                        s["fecha_inicio"] or "",
                        s["usuario"] or "",
                    ),
                    tags=(s["estado"],),
                )
            self.tree.tag_configure("abierta", foreground=CYAN)
            self.tree.tag_configure("pausada", foreground=WARNING)
            self.tree.tag_configure("cerrada", foreground=TEXT_DIM)
        except Exception as error:
            print("Error al cargar sesiones: {}".format(error))
            try:
                mb.showerror("Inventario", "No se pudieron cargar las sesiones:\n{}".format(error), parent=self.win)
            except Exception:
                pass

    def _sesion_seleccionada(self):
        sel = self.tree.selection()
        if not sel:
            return None
        return int(self.tree.item(sel[0], "values")[0])

    def _continuar_seleccion(self):
        sid = self._sesion_seleccionada()
        if not sid:
            mb.showwarning("Inventario", "Seleccione una sesión.", parent=self.win)
            return
        try:
            sesion = Consultas.obtener_sesion_inventario(sid)
            if not sesion:
                mb.showerror("Inventario", "Sesión no encontrada.", parent=self.win)
                return
            if sesion["estado"] == "cerrada":
                self._mostrar_resumen(sid, solo_lectura=True)
                return
            Consultas.reanudar_sesion_inventario(sid)
            self._mostrar_trabajo(sid)
        except Exception as error:
            print("Error al continuar sesión: {}".format(error))
            mb.showerror("Inventario", "No se pudo abrir la sesión:\n{}".format(error), parent=self.win)

    def _dialogo_nueva(self):
        dlg = tk.Toplevel(self.win)
        prepare_modal(dlg, self.win, "Nueva sesión de conteo", 540, 520, resizable=True)
        limit_minsize(dlg, 480, 460)

        footer = card_frame(dlg, padx=14, pady=8)
        footer.pack(side="bottom", fill="x", padx=10, pady=10)

        card = card_frame(dlg, padx=16, pady=12)
        card.pack(fill="both", expand=True, padx=10, pady=(10, 0))
        styled_label(card, "Nueva sesión", FONT_HEADING, TEXT, BG_CARD).pack(anchor="w")
        styled_label(
            card,
            "Modo asistido: se muestra el stock del sistema al contar.",
            FONT_SMALL,
            TEXT_DIM,
            BG_CARD,
        ).pack(anchor="w", pady=(2, 8))

        _, ent_nombre = labeled_field(card, "Nombre de la sesión")
        _.pack(fill="x", pady=(0, 6))
        ent_nombre.insert(0, "Conteo {}".format(_fmt_fecha_corta()))

        styled_label(card, "Alcance", FONT_LABEL, TEXT_MUTED, BG_CARD).pack(anchor="w")
        var_filtro = tk.StringVar(value="todos")
        opts = tk.Frame(card, bg=BG_CARD)
        opts.pack(anchor="w", pady=(2, 6))
        for val, txt in (
            ("todos", "Todos los productos"),
            ("categoria", "Por categoría"),
            ("ubicacion", "Por ubicación"),
        ):
            tk.Radiobutton(
                opts,
                text=txt,
                variable=var_filtro,
                value=val,
                bg=BG_CARD,
                fg=TEXT,
                selectcolor=BG_INPUT,
                activebackground=BG_CARD,
                activeforeground=TEXT,
                font=FONT_LABEL,
                command=lambda: _sync_combo(),
            ).pack(anchor="w", pady=1)

        styled_label(card, "Valor del filtro", FONT_LABEL, TEXT_MUTED, BG_CARD).pack(anchor="w")
        combo = ttk.Combobox(card, font=("Segoe UI", 11), style="Zyntra.TCombobox", state="disabled")
        combo.pack(fill="x", pady=(4, 4))

        cats = Consultas.listar_categorias_productos()
        ubis = Consultas.listar_ubicaciones_productos()

        def _sync_combo():
            tipo = var_filtro.get()
            if tipo == "categoria":
                combo.configure(state="readonly")
                combo["values"] = cats
                if cats:
                    combo.set(cats[0])
                else:
                    combo.set("")
            elif tipo == "ubicacion":
                combo.configure(state="readonly")
                combo["values"] = ubis
                if ubis:
                    combo.set(ubis[0])
                else:
                    combo.set("")
            else:
                combo.set("")
                combo.configure(state="disabled")

        _sync_combo()

        def _crear():
            nombre = ent_nombre.get().strip()
            tipo = var_filtro.get()
            valor = combo.get().strip() if tipo != "todos" else ""
            sid, msg = Consultas.crear_sesion_inventario(
                nombre, tipo, valor, usuario=self.usuario
            )
            if not sid:
                mb.showerror("Inventario", msg, parent=dlg)
                return
            mb.showinfo("Inventario", msg, parent=dlg)
            dlg.destroy()
            self._mostrar_trabajo(sid)

        primary_button(footer, "Crear y empezar", _crear, width=16, height=1).pack(
            side="left", padx=(0, 8)
        )
        secondary_button(footer, "Cancelar", dlg.destroy, width=12, height=1).pack(side="left")
        ent_nombre.focus_set()

    # ── Pantalla de trabajo guiado ──────────────────────────────────
    def _mostrar_trabajo(self, sesion_id):
        self._limpiar()
        self.sesion_id = int(sesion_id)
        Consultas.reanudar_sesion_inventario(self.sesion_id)

        footer = card_frame(self.win, padx=12, pady=10)
        footer.pack(side="bottom", fill="x", padx=12, pady=12)
        primary_button(footer, "Guardar y siguiente  (Enter)", self._guardar_conteo, width=24, height=1).pack(
            side="left", padx=(0, 8)
        )
        secondary_button(footer, "Omitir", self._omitir, width=10, height=1).pack(side="left", padx=(0, 8))
        secondary_button(footer, "Pausar (seguir otro día)", self._pausar, width=22, height=1).pack(
            side="left", padx=(0, 8)
        )
        secondary_button(footer, "Resumen", lambda: self._mostrar_resumen(self.sesion_id), width=10, height=1).pack(
            side="left", padx=(0, 8)
        )
        danger_button(footer, "Inicio", self._mostrar_inicio, width=10, height=1).pack(side="right")

        body = tk.Frame(self.win, bg=BG)
        body.pack(fill="both", expand=True, padx=12, pady=(12, 0))

        left = card_frame(body, padx=16, pady=14)
        left.pack(side="left", fill="both", expand=True, padx=(0, 8))
        right = card_frame(body, padx=10, pady=10)
        right.pack(side="right", fill="y")

        sesion = Consultas.obtener_sesion_inventario(self.sesion_id) or {}
        self.lbl_titulo = styled_label(left, sesion.get("nombre") or "Sesión", FONT_HEADING, TEXT, BG_CARD)
        self.lbl_titulo.pack(anchor="w")
        self.lbl_progreso = styled_label(left, "", FONT_SUB, CYAN, BG_CARD)
        self.lbl_progreso.pack(anchor="w", pady=(4, 10))

        # Buscar / escanear
        scan = tk.Frame(left, bg=BG_CARD)
        scan.pack(fill="x", pady=(0, 10))
        styled_label(scan, "Buscar o escanear en esta sesión", FONT_LABEL, TEXT_MUTED, BG_CARD).pack(
            anchor="w"
        )
        row_s = tk.Frame(scan, bg=BG_CARD)
        row_s.pack(fill="x", pady=(4, 0))
        self.entry_buscar = styled_entry(row_s, font=FONT_POS)
        self.entry_buscar.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.entry_buscar.bind("<Return>", self._buscar_en_sesion)
        secondary_button(row_s, "Ir", lambda: self._buscar_en_sesion(), width=8, height=1).pack(side="left")

        # Producto actual (asistido)
        self.card_prod = tk.Frame(left, bg=BG_ELEVATED, padx=16, pady=14)
        self.card_prod.pack(fill="x", pady=(0, 10))
        self.lbl_codigo = styled_label(self.card_prod, "", FONT_SMALL, TEXT_DIM, BG_ELEVATED)
        self.lbl_codigo.pack(anchor="w")
        self.lbl_nombre = styled_label(self.card_prod, "", ("Segoe UI", 18, "bold"), TEXT, BG_ELEVATED)
        self.lbl_nombre.pack(anchor="w", pady=(2, 6))
        self.lbl_meta = styled_label(self.card_prod, "", FONT_SMALL, TEXT_MUTED, BG_ELEVATED)
        self.lbl_meta.pack(anchor="w")

        stocks = tk.Frame(self.card_prod, bg=BG_ELEVATED)
        stocks.pack(fill="x", pady=(12, 0))
        box_sys = tk.Frame(stocks, bg=BG_CARD, padx=12, pady=8)
        box_sys.pack(side="left", fill="x", expand=True, padx=(0, 8))
        styled_label(box_sys, "Stock en sistema", FONT_SMALL, TEXT_DIM, BG_CARD).pack(anchor="w")
        self.lbl_stock_sys = styled_label(box_sys, "—", ("Segoe UI", 22, "bold"), CYAN, BG_CARD)
        self.lbl_stock_sys.pack(anchor="w")
        self.lbl_equiv = styled_label(box_sys, "", FONT_SMALL, TEXT_DIM, BG_CARD)
        self.lbl_equiv.pack(anchor="w")

        box_diff = tk.Frame(stocks, bg=BG_CARD, padx=12, pady=8)
        box_diff.pack(side="left", fill="x", expand=True)
        styled_label(box_diff, "Diferencia (físico − sistema)", FONT_SMALL, TEXT_DIM, BG_CARD).pack(
            anchor="w"
        )
        self.lbl_diff = styled_label(box_diff, "—", ("Segoe UI", 22, "bold"), TEXT, BG_CARD)
        self.lbl_diff.pack(anchor="w")

        styled_label(left, "Cantidad física contada (unidad base)", FONT_LABEL, TEXT_MUTED, BG_CARD).pack(
            anchor="w"
        )
        self.entry_fisico = styled_entry(left, font=("Segoe UI", 20), justify="center")
        self.entry_fisico.pack(fill="x", pady=(4, 4), ipady=6)
        self.entry_fisico.bind("<KeyRelease>", self._preview_diff)
        self.entry_fisico.bind("<Return>", lambda _e: self._guardar_conteo())
        styled_label(
            left,
            "Al guardar se ajusta el stock automáticamente si hay diferencia (movimiento CONTEO).",
            FONT_SMALL,
            TEXT_DIM,
            BG_CARD,
        ).pack(anchor="w", pady=(0, 4))
        self.lbl_estado_item = styled_label(left, "", FONT_SMALL, WARNING, BG_CARD)
        self.lbl_estado_item.pack(anchor="w")

        # Lista lateral
        styled_label(right, "Cola de la sesión", FONT_LABEL, CYAN, BG_CARD).pack(anchor="w")
        self.cola_wrap, self.tree_cola = scrollable_tree(
            right,
            columns=("Estado", "Codigo", "Producto", "Sys"),
            headings=("Est.", "Cód.", "Producto", "Sist."),
            height=18,
            widths={"Estado": 55, "Codigo": 70, "Producto": 160, "Sys": 50},
            autofit=False,
        )
        self.cola_wrap.pack(fill="both", expand=True, pady=(6, 0))
        self.tree_cola.column("Producto", anchor="w")
        self.tree_cola.bind("<<TreeviewSelect>>", self._seleccionar_de_cola)
        self.tree_cola.tag_configure("pendiente", foreground=TEXT)
        self.tree_cola.tag_configure("contado", foreground=SUCCESS)
        self.tree_cola.tag_configure("ajustado", foreground=CYAN)
        self.tree_cola.tag_configure("omitido", foreground=TEXT_DIM)

        # Diferir carga para pintar la UI primero y evitar cuelgues
        self.win.after(30, lambda: self._refrescar_trabajo(cargar_siguiente=True))

    def _refrescar_trabajo(self, cargar_siguiente=False):
        try:
            if not hasattr(self, "lbl_progreso") or not self.lbl_progreso.winfo_exists():
                return
            sesion = Consultas.obtener_sesion_inventario(self.sesion_id) or {}
            self.lbl_progreso.config(
                text="Avance  {} / {}   ·   {}%   ·   modo asistido".format(
                    sesion.get("contados", 0),
                    sesion.get("total", 0),
                    sesion.get("pct", 0),
                )
            )
            self._pintar_cola()
            if not cargar_siguiente:
                return
            nxt = Consultas.siguiente_item_pendiente(self.sesion_id)
            if nxt:
                self._cargar_item(nxt, pintar_cola=False)
                self._resaltar_en_cola(nxt.get("id"))
            else:
                self.item_actual = None
                self.lbl_nombre.config(text="Sesión completa")
                self.lbl_codigo.config(text="")
                self.lbl_meta.config(text="No quedan productos pendientes.")
                self.lbl_stock_sys.config(text="—")
                self.lbl_equiv.config(text="")
                self.lbl_diff.config(text="—", fg=TEXT)
                self.entry_fisico.delete(0, tk.END)
                self.lbl_estado_item.config(
                    text="100% de la cola procesada. Revise el resumen o cierre la sesión.",
                    fg=SUCCESS,
                )
                self.win.after(
                    50,
                    lambda: self._ofrecer_resumen_completo(),
                )
        except Exception as error:
            print("Error al refrescar trabajo: {}".format(error))
            mb.showerror("Inventario", "Error al cargar el conteo:\n{}".format(error), parent=self.win)

    def _ofrecer_resumen_completo(self):
        try:
            if not self.win.winfo_exists():
                return
            if mb.askyesno(
                "Inventario",
                "No quedan pendientes.\n¿Ver resumen de la sesión?",
                parent=self.win,
            ):
                self._mostrar_resumen(self.sesion_id)
        except Exception:
            pass

    def _pintar_cola(self):
        if not hasattr(self, "tree_cola"):
            return
        self._silenciar_cola = True
        try:
            self._items_cache = Consultas.listar_items_sesion(self.sesion_id) or []
            self.tree_cola.delete(*self.tree_cola.get_children())
            actual_id = (self.item_actual or {}).get("id")
            for it in self._items_cache:
                est = (it.get("estado") or "pendiente")[:3].upper()
                iid = str(it["id"])
                self.tree_cola.insert(
                    "",
                    "end",
                    iid=iid,
                    values=(est, it["producto_id"], it["nombre"], _fmt_qty(it["stock_asignado"])),
                    tags=(it.get("estado") or "pendiente",),
                )
            if actual_id is not None:
                self._resaltar_en_cola(actual_id)
        finally:
            self._silenciar_cola = False

    def _resaltar_en_cola(self, item_id):
        if item_id is None or not hasattr(self, "tree_cola"):
            return
        iid = str(item_id)
        self._silenciar_cola = True
        try:
            if self.tree_cola.exists(iid):
                self.tree_cola.selection_set(iid)
                self.tree_cola.focus(iid)
                self.tree_cola.see(iid)
        except tk.TclError:
            pass
        finally:
            self._silenciar_cola = False

    def _stock_sistema_vivo(self, producto_id):
        try:
            return float(Consultas.cantidad_producto(producto_id) or 0)
        except Exception:
            return float(self.item_actual.get("stock_asignado") or 0) if self.item_actual else 0.0

    def _cargar_item(self, item, pintar_cola=True):
        if not item:
            return
        self.item_actual = item
        stock = self._stock_sistema_vivo(item["producto_id"])
        unidad = item.get("unidad_base") or "Unidad"
        try:
            equiv = Consultas.texto_equivalencias(
                stock,
                Consultas.listar_presentaciones(item["producto_id"]) or [],
                unidad,
            )
        except Exception:
            equiv = ""
        self.lbl_codigo.config(text="Código  {}".format(item["producto_id"]))
        self.lbl_nombre.config(text=item.get("nombre") or "—")
        meta = []
        if item.get("ubicacion"):
            meta.append("Ubicación: {}".format(item["ubicacion"]))
        if item.get("categoria"):
            meta.append("Categoría: {}".format(item["categoria"]))
        meta.append("Unidad: {}".format(unidad))
        self.lbl_meta.config(text="  ·  ".join(meta))
        self.lbl_stock_sys.config(text=_fmt_qty(stock))
        self.lbl_equiv.config(text=equiv or "")
        self.entry_fisico.delete(0, tk.END)
        if item.get("cantidad_fisica") is not None and item.get("estado") != "pendiente":
            self.entry_fisico.insert(0, _fmt_qty(item["cantidad_fisica"]))
        self.lbl_estado_item.config(
            text="Estado: {}".format(item.get("estado") or "pendiente"),
            fg=TEXT_MUTED,
        )
        self._preview_diff()
        if pintar_cola:
            self._pintar_cola()
        else:
            self._resaltar_en_cola(item.get("id"))
        try:
            self.entry_fisico.focus_set()
        except tk.TclError:
            pass

    def _preview_diff(self, event=None):
        if not self.item_actual:
            return
        try:
            stock = float(self.item_actual.get("stock_asignado") or 0)
            # Preferir stock vivo solo al guardar; en preview usa asignado si falla
            vivo = self._stock_sistema_vivo(self.item_actual["producto_id"])
            stock = vivo
        except Exception:
            stock = float(self.item_actual.get("stock_asignado") or 0)
        self.lbl_stock_sys.config(text=_fmt_qty(stock))
        texto = self.entry_fisico.get().strip().replace(",", ".")
        if texto == "":
            self.lbl_diff.config(text="—", fg=TEXT)
            return
        try:
            fisica = float(texto)
        except ValueError:
            self.lbl_diff.config(text="?", fg=WARNING)
            return
        diff = fisica - stock
        color = SUCCESS if abs(diff) < 0.001 else (DANGER if diff < 0 else WARNING)
        signo = "+" if diff > 0 else ""
        self.lbl_diff.config(text="{}{}".format(signo, _fmt_qty(diff)), fg=color)

    def _guardar_conteo(self):
        if not self.item_actual:
            mb.showinfo("Inventario", "No hay producto pendiente.", parent=self.win)
            return
        texto = self.entry_fisico.get().strip()
        if texto == "":
            mb.showwarning("Inventario", "Ingrese la cantidad física.", parent=self.win)
            self.entry_fisico.focus_set()
            return
        stock = self._stock_sistema_vivo(self.item_actual["producto_id"])
        try:
            fisica = float(texto.replace(",", "."))
        except ValueError:
            mb.showerror("Inventario", "Cantidad inválida.", parent=self.win)
            return
        diff = fisica - stock
        if abs(diff) > 0.0001:
            if not mb.askyesno(
                "Confirmar conteo",
                "Producto: {}\n\nSistema: {}\nFísico: {}\nDiferencia: {}{}\n\n"
                "¿Guardar y ajustar el stock?".format(
                    self.item_actual.get("nombre"),
                    _fmt_qty(stock),
                    _fmt_qty(fisica),
                    "+" if diff > 0 else "",
                    _fmt_qty(diff),
                ),
                parent=self.win,
            ):
                return
        ok, msg, _info = Consultas.registrar_conteo_item(
            self.item_actual["id"], fisica, usuario=self.usuario, aplicar_ajuste=True
        )
        if not ok:
            mb.showerror("Inventario", msg, parent=self.win)
            return
        self._refrescar_trabajo(cargar_siguiente=True)

    def _omitir(self):
        if not self.item_actual:
            return
        if not mb.askyesno(
            "Omitir",
            "¿Omitir {} por ahora? Podrá retomarlo más adelante solo si no cierra la sesión.".format(
                self.item_actual.get("nombre")
            ),
            parent=self.win,
        ):
            return
        # Omitting marks as done for progress; to re-open we'd need un-omit — for MVP ok
        ok, msg = Consultas.omitir_item_conteo(self.item_actual["id"], self.usuario)
        if not ok:
            mb.showerror("Inventario", msg, parent=self.win)
            return
        self._refrescar_trabajo(cargar_siguiente=True)

    def _pausar(self):
        if self.sesion_id:
            Consultas.pausar_sesion_inventario(self.sesion_id)
        mb.showinfo(
            "Inventario",
            "Sesión pausada. Puede continuar otro día desde la lista de sesiones.",
            parent=self.win,
        )
        self._mostrar_inicio()

    def _buscar_en_sesion(self, event=None):
        texto = self.entry_buscar.get().strip()
        if not texto:
            return
        it = Consultas.buscar_item_sesion_por_codigo(self.sesion_id, texto)
        if not it:
            mb.showwarning("Inventario", "No está en esta sesión.", parent=self.win)
            return
        self._cargar_item(it)
        self.entry_buscar.delete(0, tk.END)

    def _seleccionar_de_cola(self, event=None):
        if getattr(self, "_silenciar_cola", False):
            return
        sel = self.tree_cola.selection()
        if not sel:
            return
        try:
            item_id = int(sel[0])
        except (TypeError, ValueError):
            return
        if self.item_actual and int(self.item_actual.get("id") or 0) == item_id:
            return
        for it in self._items_cache or Consultas.listar_items_sesion(self.sesion_id):
            if int(it["id"]) == item_id:
                self._cargar_item(it, pintar_cola=False)
                break

    # ── Resumen ─────────────────────────────────────────────────────
    def _mostrar_resumen(self, sesion_id, solo_lectura=False):
        self._limpiar()
        self.sesion_id = int(sesion_id)
        sesion = Consultas.obtener_sesion_inventario(self.sesion_id) or {}
        resumen = Consultas.resumen_diferencias_sesion(self.sesion_id)

        footer = card_frame(self.win, padx=12, pady=10)
        footer.pack(side="bottom", fill="x", padx=12, pady=12)
        if not solo_lectura and sesion.get("estado") != "cerrada":
            primary_button(footer, "Seguir contando", lambda: self._mostrar_trabajo(self.sesion_id), width=16).pack(
                side="left", padx=(0, 8)
            )
            warning_button(
                footer,
                "Cerrar sesión (100%)",
                self._cerrar_sesion,
                width=18,
                font=FONT_SMALL,
            ).pack(side="left", padx=(0, 8))
        danger_button(footer, "Volver al inicio", self._mostrar_inicio, width=14, height=1).pack(side="right")

        card = card_frame(self.win, padx=16, pady=12)
        card.pack(fill="both", expand=True, padx=12, pady=(12, 0))
        styled_label(card, "Resumen · {}".format(sesion.get("nombre") or ""), FONT_HEADING, TEXT, BG_CARD).pack(
            anchor="w"
        )
        styled_label(
            card,
            "Avance {}/{} ({}%)  ·  Estado: {}".format(
                sesion.get("contados", 0),
                sesion.get("total", 0),
                sesion.get("pct", 0),
                sesion.get("estado"),
            ),
            FONT_SUB,
            CYAN,
            BG_CARD,
        ).pack(anchor="w", pady=(4, 10))

        kpis = tk.Frame(card, bg=BG_CARD)
        kpis.pack(fill="x", pady=(0, 10))
        for label, valor, color in (
            ("Faltantes (ítems)", len(resumen["faltantes"]), DANGER),
            ("Unid. faltantes", _fmt_qty(resumen["total_faltante_unidades"]), DANGER),
            ("Sobrantes (ítems)", len(resumen["sobrantes"]), WARNING),
            ("Unid. sobrantes", _fmt_qty(resumen["total_sobrante_unidades"]), WARNING),
            ("Cuadre exacto", len(resumen["cuadre"]), SUCCESS),
        ):
            box = tk.Frame(kpis, bg=BG_ELEVATED, padx=10, pady=8)
            box.pack(side="left", fill="x", expand=True, padx=3)
            styled_label(box, label, FONT_SMALL, TEXT_DIM, BG_ELEVATED).pack(anchor="w")
            styled_label(box, str(valor), FONT_SUB, color, BG_ELEVATED).pack(anchor="w")

        styled_label(card, "Diferencias registradas", FONT_LABEL, TEXT_MUTED, BG_CARD).pack(anchor="w")
        tw, tree = scrollable_tree(
            card,
            columns=("Codigo", "Producto", "Sistema", "Fisico", "Diff", "Estado"),
            headings=("Cód.", "Producto", "Sistema", "Físico", "Diff", "Estado"),
            height=14,
            widths={"Codigo": 70, "Producto": 240, "Sistema": 80, "Fisico": 80, "Diff": 70, "Estado": 80},
            autofit=False,
        )
        tw.pack(fill="both", expand=True, pady=(6, 0))
        tree.column("Producto", anchor="w")
        for it in Consultas.listar_items_sesion(self.sesion_id):
            if it.get("estado") == "pendiente":
                continue
            diff = it.get("diferencia")
            tree.insert(
                "",
                "end",
                values=(
                    it["producto_id"],
                    it["nombre"],
                    _fmt_qty(it.get("stock_al_contar")),
                    _fmt_qty(it.get("cantidad_fisica")),
                    "—" if diff is None else "{}{}".format("+" if diff > 0 else "", _fmt_qty(diff)),
                    it.get("estado"),
                ),
            )

    def _cerrar_sesion(self):
        sesion = Consultas.obtener_sesion_inventario(self.sesion_id) or {}
        pendientes = Consultas.listar_items_sesion(self.sesion_id, estado="pendiente")
        forzar = False
        if pendientes:
            if not mb.askyesno(
                "Cerrar sesión",
                "Quedan {} pendientes.\n¿Cerrar de todas formas? (los pendientes quedarán sin contar)".format(
                    len(pendientes)
                ),
                parent=self.win,
            ):
                return
            forzar = True
        elif sesion.get("pct", 0) < 100:
            if not mb.askyesno("Cerrar sesión", "¿Cerrar la sesión?", parent=self.win):
                return
        ok, msg = Consultas.cerrar_sesion_inventario(self.sesion_id, self.usuario, forzar=forzar)
        if not ok:
            mb.showerror("Inventario", msg, parent=self.win)
            return
        mb.showinfo("Inventario", msg, parent=self.win)
        self._mostrar_inicio()


def _fmt_fecha_corta():
    from datetime import datetime

    return datetime.now().strftime("%d/%m/%Y")
