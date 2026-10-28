"""UI Cierre general administrativo — solo admin (Entrega 2)."""
import tkinter as tk
from tkinter import ttk
import mensaje as mb

from cierre_general_svc import (
    CHECKLIST_CIERRE_GENERAL,
    anular_cierre_general,
    actualizar_checklist_dia,
    consolidar_cierre_general,
    crear_cierre_general,
    detalle_cierre_diario_admin,
    es_usuario_admin,
    listar_cierres_diarios_disponibles,
    listar_cierres_generales,
    obtener_cierre_general,
)
from provision_admin_svc import resumen_provision_admin
from zyntra_ui import *


class CierreGeneralView(tk.Frame):
    def __init__(self, parent, usuario=None, app=None):
        super().__init__(parent, bg=BG)
        self.usuario = usuario or (getattr(app, "usuario", None) if app else None)
        self.app = app
        self._sel_diarios = {}
        self._general_id = None
        if not es_usuario_admin(self.usuario):
            styled_label(
                self,
                "Acceso denegado: solo el administrador puede gestionar el cierre general.",
                FONT_HEADING,
                DANGER,
                BG,
            ).pack(expand=True)
            return
        self._build()
        self._cargar_lista()

    def _build(self):
        top = card_frame(self, padx=12, pady=10)
        top.pack(fill="x", pady=(0, 8))
        styled_label(top, "Cierre general administrativo", FONT_HEADING, TEXT, BG_CARD).pack(anchor="w")
        styled_label(
            top,
            "Seleccione cierres diarios, verifique el checklist y consolide. Solo admin.",
            FONT_SMALL,
            TEXT_DIM,
            BG_CARD,
        ).pack(anchor="w", pady=(2, 8))
        actions = tk.Frame(top, bg=BG_CARD)
        actions.pack(fill="x")
        primary_button(actions, "Nuevo cierre general", self._nuevo, width=20, height=1).pack(
            side="left", padx=(0, 8)
        )
        secondary_button(actions, "Actualizar", self._cargar_lista, width=12, height=1).pack(
            side="left", padx=(0, 8)
        )
        secondary_button(actions, "Abrir seleccionado", self._abrir_sel, width=16, height=1).pack(
            side="left", padx=(0, 8)
        )
        secondary_button(actions, "Provisión admin", self._ver_provision, width=14, height=1).pack(
            side="left", padx=(0, 8)
        )
        danger_button(actions, "Anular", self._anular_sel, width=10, height=1).pack(side="left")

        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True)
        left = card_frame(body, padx=10, pady=8)
        left.pack(side="left", fill="both", expand=True, padx=(0, 6))
        styled_label(left, "Cierres generales", FONT_LABEL, TEXT, BG_CARD).pack(anchor="w")
        self.wrap_g, self.tree_g = scrollable_tree(
            left,
            columns=("Id", "Estado", "Titulo", "Dias", "Ventas", "Diff", "Admin"),
            headings=("ID", "Estado", "Título", "Días", "Ventas", "Diff", "Admin"),
            height=12,
            widths={"Id": 50, "Estado": 100, "Titulo": 140, "Dias": 50, "Ventas": 90, "Diff": 80, "Admin": 80},
        )
        self.wrap_g.pack(fill="both", expand=True, pady=(6, 0))
        self.tree_g.bind("<Double-1>", lambda _e: self._abrir_sel())

        right = card_frame(body, padx=10, pady=8)
        right.pack(side="left", fill="both", expand=True, padx=(6, 0))
        styled_label(right, "Detalle / checklist", FONT_LABEL, TEXT, BG_CARD).pack(anchor="w")
        self.detalle_box = tk.Frame(right, bg=BG_CARD)
        self.detalle_box.pack(fill="both", expand=True, pady=(6, 0))
        styled_label(
            self.detalle_box,
            "Seleccione o cree un cierre general.",
            FONT_SMALL,
            TEXT_DIM,
            BG_CARD,
        ).pack(anchor="w")

    def on_show(self):
        if es_usuario_admin(self.usuario):
            self._cargar_lista()

    def _cargar_lista(self):
        if not hasattr(self, "tree_g"):
            return
        for i in self.tree_g.get_children():
            self.tree_g.delete(i)
        for g in listar_cierres_generales(80):
            self.tree_g.insert(
                "",
                "end",
                iid=str(g["id"]),
                values=(
                    g["id"],
                    g["estado"],
                    g["titulo"][:40],
                    g["dias"],
                    formato_dinero(g["total_ventas"]),
                    formato_dinero(g["total_diferencia"]),
                    g["admin_usuario"],
                ),
            )

    def _sel_id(self):
        sel = self.tree_g.selection()
        if not sel:
            return None
        try:
            return int(sel[0])
        except Exception:
            return None

    def _nuevo(self):
        diarios = listar_cierres_diarios_disponibles(limite=120)
        if not diarios:
            mb.showinfo("Cierre general", "No hay cierres diarios disponibles.", parent=self)
            return
        dlg = tk.Toplevel(self)
        prepare_modal(dlg, self, "Nuevo cierre general", 960, 620, resizable=True)
        shell = tk.Frame(dlg, bg=BG, padx=16, pady=14)
        shell.pack(fill="both", expand=True)

        styled_label(
            shell, "Seleccione uno o varios cierres diarios", FONT_HEADING, TEXT, BG
        ).pack(anchor="w")
        styled_label(
            shell,
            "Marque los días a incluir. Luego cree el borrador para verificar el checklist.",
            FONT_SMALL,
            TEXT_DIM,
            BG,
        ).pack(anchor="w", pady=(2, 10))

        list_wrap = card_frame(shell, padx=10, pady=10)
        list_wrap.pack(fill="both", expand=True)

        canvas = tk.Canvas(list_wrap, bg=BG_CARD, highlightthickness=0)
        scroll = ttk.Scrollbar(list_wrap, orient="vertical", command=canvas.yview)
        inner = tk.Frame(canvas, bg=BG_CARD)

        def _sync_scroll(_event=None):
            canvas.configure(scrollregion=canvas.bbox("all"))
            # Mantener el ancho del contenido = ancho del canvas
            canvas.itemconfigure(win_id, width=max(canvas.winfo_width() - 4, 100))

        win_id = canvas.create_window((0, 0), window=inner, anchor="nw")
        inner.bind("<Configure>", _sync_scroll)
        canvas.bind("<Configure>", _sync_scroll)
        canvas.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        def _unbind_wheel():
            try:
                canvas.unbind_all("<MouseWheel>")
            except Exception:
                pass

        dlg.protocol("WM_DELETE_WINDOW", lambda: (_unbind_wheel(), dlg.destroy()))

        vars_chk = {}
        for d in diarios:
            var = tk.BooleanVar(value=False)
            vars_chk[d["id"]] = var
            row = tk.Frame(
                inner,
                bg=BG_ELEVATED,
                highlightthickness=1,
                highlightbackground=BORDER,
                padx=10,
                pady=8,
            )
            row.pack(fill="x", pady=5, padx=2)

            chk = tk.Checkbutton(
                row,
                variable=var,
                bg=BG_ELEVATED,
                fg=TEXT,
                selectcolor=BG_INPUT,
                activebackground=BG_ELEVATED,
                activeforeground=TEXT,
                highlightthickness=0,
                bd=0,
            )
            chk.pack(side="left", padx=(0, 10), anchor="n")

            body = tk.Frame(row, bg=BG_ELEVATED)
            body.pack(side="left", fill="x", expand=True)

            line1 = "#{id}   {fecha}   ·   {vend}   ·   {est}".format(
                id=d["id"],
                fecha=str(d["fecha"])[:16],
                vend=d["vendedor"] or "-",
                est=d["estado"] or "-",
            )
            styled_label(body, line1, FONT_SUB, TEXT, BG_ELEVATED).pack(anchor="w")

            line2 = (
                "Ventas {v}    Ef {e}    Nequi {n}    Datafono {t}    Diff {diff}    Corr {c}"
            ).format(
                v=formato_dinero(d["ventas"]),
                e=formato_dinero(d["efectivo"]),
                n=formato_dinero(d["nequi"]),
                t=formato_dinero(d["datafono"]),
                diff=formato_dinero(d["diferencia"]),
                c=d["correcciones"],
            )
            styled_label(body, line2, FONT_SMALL, TEXT_DIM, BG_ELEVATED).pack(
                anchor="w", pady=(3, 0)
            )
            if d.get("observaciones"):
                obs = str(d.get("observaciones") or "").strip()
                if obs:
                    styled_label(
                        body,
                        "Obs: {}".format(obs[:110]),
                        FONT_SMALL,
                        TEXT_MUTED,
                        BG_ELEVATED,
                    ).pack(anchor="w", pady=(2, 0))

        footer = tk.Frame(shell, bg=BG)
        footer.pack(fill="x", pady=(12, 0))

        def crear():
            ids = [i for i, v in vars_chk.items() if v.get()]
            if not ids:
                mb.showwarning("Cierre general", "Marque al menos un día.", parent=dlg)
                return
            ok, msg, gid = crear_cierre_general(self.usuario, ids)
            if not ok:
                mb.showerror("Cierre general", msg, parent=dlg)
                return
            _unbind_wheel()
            mb.showinfo("Cierre general", msg, parent=dlg)
            dlg.destroy()
            self._cargar_lista()
            self._mostrar_detalle(gid)

        primary_button(footer, "Crear borrador", crear, width=18, height=1).pack(side="left")
        secondary_button(
            footer, "Cancelar", lambda: (_unbind_wheel(), dlg.destroy()), width=12, height=1
        ).pack(side="left", padx=(10, 0))

    def _abrir_sel(self):
        gid = self._sel_id()
        if not gid:
            mb.showwarning("Cierre general", "Seleccione un cierre general.", parent=self)
            return
        self._mostrar_detalle(gid)

    def _anular_sel(self):
        gid = self._sel_id()
        if not gid:
            mb.showwarning("Cierre general", "Seleccione un cierre.", parent=self)
            return
        if not mb.askyesno("Anular", "¿Anular el cierre general #{}?".format(gid), parent=self):
            return
        ok, msg = anular_cierre_general(self.usuario, gid, "Anulado desde POS")
        if ok:
            mb.showinfo("Cierre general", msg, parent=self)
            self._cargar_lista()
            self._mostrar_detalle(gid)
        else:
            mb.showerror("Cierre general", msg, parent=self)

    def _mostrar_detalle(self, gid):
        self._general_id = gid
        data = obtener_cierre_general(gid)
        for w in self.detalle_box.winfo_children():
            w.destroy()
        if not data:
            styled_label(self.detalle_box, "No encontrado", FONT_BODY, DANGER, BG_CARD).pack(anchor="w")
            return

        head = tk.Frame(self.detalle_box, bg=BG_CARD)
        head.pack(fill="x")
        styled_label(
            head,
            "#{}  {}  ·  {}".format(data["id"], data["titulo"], data["estado"]),
            FONT_SUB,
            CYAN,
            BG_CARD,
        ).pack(anchor="w")
        styled_label(
            head,
            "Ventas {}  ·  Ef {}  ·  Nequi {}  ·  Data {}  ·  Diff {}".format(
                formato_dinero(data["total_ventas"]),
                formato_dinero(data["total_efectivo"]),
                formato_dinero(data["total_nequi"]),
                formato_dinero(data["total_datafono"]),
                formato_dinero(data["total_diferencia"]),
            ),
            FONT_SMALL,
            TEXT,
            BG_CARD,
        ).pack(anchor="w", pady=(2, 2))
        dias_all = data.get("dias") or []
        n_ok = sum(
            1
            for d in dias_all
            if all(bool((d.get("checklist") or {}).get(k)) for k, _c, _l in CHECKLIST_CIERRE_GENERAL)
        )
        styled_label(
            head,
            "Días revisados: {}/{}".format(n_ok, len(dias_all)),
            FONT_SMALL,
            SUCCESS if n_ok and n_ok == len(dias_all) else TEXT_DIM,
            BG_CARD,
        ).pack(anchor="w", pady=(0, 6))

        prov = data.get("provision")
        if prov:
            self._pack_provision_block(head, prov, titulo="Provisión administrativa (aplicada)")
        elif data["estado"] not in ("CONSOLIDADO", "ANULADO"):
            try:
                from provision_admin_svc import previsualizar_provision_cierre_general

                prev = previsualizar_provision_cierre_general(gid)
                if prev:
                    self._pack_provision_block(
                        head, prev, titulo="Provisión estimada al consolidar (solo efectivo)"
                    )
            except Exception:
                pass

        list_area = tk.Frame(self.detalle_box, bg=BG_CARD)
        list_area.pack(fill="both", expand=True)

        canvas = tk.Canvas(list_area, bg=BG_CARD, highlightthickness=0)
        scroll = ttk.Scrollbar(list_area, orient="vertical", command=canvas.yview)
        inner = tk.Frame(canvas, bg=BG_CARD)

        def _sync(_e=None):
            canvas.configure(scrollregion=canvas.bbox("all"))
            canvas.itemconfigure(win_id, width=max(canvas.winfo_width() - 4, 80))

        win_id = canvas.create_window((0, 0), window=inner, anchor="nw")
        inner.bind("<Configure>", _sync)
        canvas.bind("<Configure>", _sync)
        canvas.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        for d in data.get("dias") or []:
            chk = d.get("checklist") or {}
            completo = all(bool(chk.get(k)) for k, _c, _l in CHECKLIST_CIERRE_GENERAL)
            borde = SUCCESS if completo else BORDER
            box = tk.Frame(
                inner,
                bg=BG_ELEVATED,
                padx=10,
                pady=8,
                highlightthickness=2 if completo else 1,
                highlightbackground=borde,
            )
            box.pack(fill="x", pady=5, padx=2)

            top_row = tk.Frame(box, bg=BG_ELEVATED)
            top_row.pack(fill="x")

            if completo:
                badge = tk.Label(
                    top_row,
                    text=" ✓ ",
                    bg=SUCCESS,
                    fg="#06140C",
                    font=("Segoe UI", 14, "bold"),
                    padx=6,
                    pady=2,
                )
                badge.pack(side="left", padx=(0, 8))
                styled_label(
                    top_row,
                    "REVISADO",
                    FONT_SMALL,
                    SUCCESS,
                    BG_ELEVATED,
                ).pack(side="left", padx=(0, 10))

            styled_label(
                top_row,
                "#{tid}  {fecha}  ·  {vend}  ·  {est_dia}".format(
                    tid=d["cierre_turno_id"],
                    fecha=str(d["fecha"])[:16],
                    vend=d["vendedor"],
                    est_dia=d["estado_dia"],
                ),
                FONT_SMALL,
                TEXT,
                BG_ELEVATED,
            ).pack(side="left", fill="x", expand=True)

            styled_label(
                box,
                "Diff {}  ·  Corr {}  ·  Obs: {}".format(
                    formato_dinero(d["diferencia"]),
                    d.get("correcciones") or 0,
                    (d.get("observaciones") or "-")[:90],
                ),
                FONT_SMALL,
                TEXT_DIM,
                BG_ELEVATED,
            ).pack(anchor="w", pady=(4, 0))

            btn_txt = "Ver checklist  ✓" if completo else "Checklist / detalle"
            secondary_button(
                box,
                btn_txt,
                lambda tid=d["cierre_turno_id"]: self._editar_dia(gid, tid),
                width=20,
                height=1,
                font=FONT_SMALL,
            ).pack(anchor="w", pady=(8, 0))

        bar = tk.Frame(self.detalle_box, bg=BG_CARD)
        bar.pack(fill="x", pady=(10, 0))
        if data["estado"] not in ("CONSOLIDADO", "ANULADO"):
            primary_button(
                bar,
                "Consolidar",
                lambda: self._consolidar(gid),
                width=14,
                height=1,
            ).pack(side="left", padx=(0, 8))

    def _editar_dia(self, gid, turno_id):
        data = obtener_cierre_general(gid)
        if not data:
            return
        dia = next((x for x in data["dias"] if x["cierre_turno_id"] == turno_id), None)
        if not dia:
            return
        det = detalle_cierre_diario_admin(turno_id) or {}
        dlg = tk.Toplevel(self)
        prepare_modal(dlg, self, "Día cierre #{}".format(turno_id), 720, 640, resizable=True)
        shell = tk.Frame(dlg, bg=BG, padx=14, pady=12)
        shell.pack(fill="both", expand=True)

        body_wrap = card_frame(shell, padx=12, pady=10)
        body_wrap.pack(fill="both", expand=True)

        canvas = tk.Canvas(body_wrap, bg=BG_CARD, highlightthickness=0)
        scroll = ttk.Scrollbar(body_wrap, orient="vertical", command=canvas.yview)
        card = tk.Frame(canvas, bg=BG_CARD)

        def _sync(_e=None):
            canvas.configure(scrollregion=canvas.bbox("all"))
            canvas.itemconfigure(win_id, width=max(canvas.winfo_width() - 4, 80))

        win_id = canvas.create_window((0, 0), window=card, anchor="nw")
        card.bind("<Configure>", _sync)
        canvas.bind("<Configure>", _sync)
        canvas.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        styled_label(
            card,
            "{}  ·  {}  ·  Diff {}".format(
                det.get("fecha"), det.get("vendedor"), formato_dinero(det.get("diferencia"))
            ),
            FONT_SUB,
            TEXT,
            BG_CARD,
        ).pack(anchor="w")
        styled_label(
            card,
            "Explicación vendedor: {}".format(det.get("observaciones") or "(sin observación)"),
            FONT_SMALL,
            TEXT_DIM,
            BG_CARD,
        ).pack(anchor="w", pady=(4, 8))
        for m in det.get("medios") or []:
            styled_label(
                card,
                "{}  Sis {}  Decl {}  Diff {}".format(
                    m.get("etiqueta"),
                    formato_dinero(m.get("sistema")),
                    formato_dinero(m.get("declarado")),
                    formato_dinero(m.get("diferencia")),
                ),
                FONT_SMALL,
                TEXT,
                BG_CARD,
            ).pack(anchor="w", pady=1)
        if det.get("correcciones"):
            styled_label(card, "Correcciones:", FONT_LABEL, WARNING, BG_CARD).pack(
                anchor="w", pady=(10, 2)
            )
            for c in det["correcciones"][:8]:
                styled_label(
                    card,
                    "#{} {}→{} {} · {}".format(
                        c.get("venta_id"),
                        c.get("metodo_anterior"),
                        c.get("metodo_nuevo"),
                        formato_dinero(c.get("monto")),
                        c.get("motivo") or "",
                    ),
                    FONT_SMALL,
                    TEXT_DIM,
                    BG_CARD,
                ).pack(anchor="w")

        styled_label(card, "Checklist admin", FONT_LABEL, CYAN, BG_CARD).pack(
            anchor="w", pady=(12, 6)
        )
        styled_label(
            card,
            "↑↓ mover  ·  Espacio marcar/desmarcar  ·  Enter guardar",
            FONT_SMALL,
            TEXT_DIM,
            BG_CARD,
        ).pack(anchor="w", pady=(0, 6))

        vars_c = {}
        chk_btns = []
        chk = dia.get("checklist") or {}
        editable = data["estado"] not in ("CONSOLIDADO", "ANULADO")

        def _scroll_to_widget(widget):
            try:
                dlg.update_idletasks()
                # Posición relativa del widget dentro del frame scrolleable
                y = widget.winfo_y()
                h = max(card.winfo_height(), 1)
                ch = max(canvas.winfo_height(), 1)
                frac = max(0.0, min(1.0, (y - 40) / max(h - ch, 1)))
                canvas.yview_moveto(frac)
            except Exception:
                pass

        def _paint_focus(active_idx):
            for i, btn in enumerate(chk_btns):
                if i == active_idx:
                    btn.configure(
                        bg=BG_INPUT,
                        activebackground=BG_INPUT,
                        highlightthickness=2,
                        highlightbackground=CYAN,
                        highlightcolor=CYAN,
                        fg=CYAN,
                    )
                else:
                    btn.configure(
                        bg=BG_CARD,
                        activebackground=BG_CARD,
                        highlightthickness=0,
                        fg=TEXT,
                    )

        def _focus_chk(idx):
            if not chk_btns:
                return
            idx = max(0, min(len(chk_btns) - 1, idx))
            btn = chk_btns[idx]
            btn.focus_set()
            _paint_focus(idx)
            _scroll_to_widget(btn)

        def _move_chk(delta, event=None):
            if not chk_btns:
                return "break"
            cur = dlg.focus_get()
            try:
                idx = chk_btns.index(cur)
            except ValueError:
                idx = 0 if delta > 0 else len(chk_btns) - 1
            _focus_chk(idx + delta)
            return "break"

        def _toggle_chk(event=None):
            w = dlg.focus_get()
            if w in chk_btns and editable:
                w.invoke()
            return "break"

        for key, _col, label in CHECKLIST_CIERRE_GENERAL:
            var = tk.BooleanVar(value=bool(chk.get(key)))
            vars_c[key] = var
            btn = tk.Checkbutton(
                card,
                text=label,
                variable=var,
                bg=BG_CARD,
                fg=TEXT,
                selectcolor=BG_INPUT,
                activebackground=BG_CARD,
                activeforeground=TEXT,
                font=FONT_BODY,
                padx=8,
                pady=6,
                anchor="w",
                takefocus=1 if editable else 0,
                state="normal" if editable else "disabled",
                highlightthickness=0,
                bd=0,
                cursor="hand2",
            )
            btn.pack(anchor="w", fill="x", pady=2)
            chk_btns.append(btn)
            btn.bind("<Up>", lambda e: _move_chk(-1, e))
            btn.bind("<Down>", lambda e: _move_chk(1, e))
            btn.bind("<Prior>", lambda e: _move_chk(-1, e))
            btn.bind("<Next>", lambda e: _move_chk(1, e))
            btn.bind("<space>", _toggle_chk)
            btn.bind("<FocusIn>", lambda e, b=btn: _paint_focus(chk_btns.index(b)))

        styled_label(card, "Nota admin", FONT_SMALL, TEXT_DIM, BG_CARD).pack(
            anchor="w", pady=(10, 2)
        )
        nota = styled_entry(card, width=50)
        nota.pack(fill="x", pady=(0, 4))
        nota.insert(0, dia.get("nota_admin") or "")
        # Desde el último check, Down pasa a la nota; desde la nota, Up vuelve al checklist
        if chk_btns:
            chk_btns[-1].bind(
                "<Down>",
                lambda e: (nota.focus_set(), _paint_focus(-1), "break")[-1],
            )
            nota.bind("<Up>", lambda e: (_focus_chk(len(chk_btns) - 1), "break")[-1])
            nota.bind("<FocusIn>", lambda _e: _paint_focus(-1))

        footer = tk.Frame(shell, bg=BG)
        footer.pack(fill="x", pady=(12, 0))

        def guardar():
            if data["estado"] in ("CONSOLIDADO", "ANULADO"):
                mb.showwarning(
                    "Cierre", "No editable en estado {}".format(data["estado"]), parent=dlg
                )
                return
            payload = {k: v.get() for k, v in vars_c.items()}
            ok, msg = actualizar_checklist_dia(self.usuario, gid, turno_id, payload, nota.get())
            if ok:
                mb.showinfo("Checklist", msg, parent=dlg)
                dlg.destroy()
                self._cargar_lista()
                self._mostrar_detalle(gid)
            else:
                mb.showerror("Checklist", msg, parent=dlg)

        btn_guardar = None
        if editable:
            btn_guardar = primary_button(
                footer, "Guardar checklist", guardar, width=18, height=1
            )
            btn_guardar.pack(side="left")
        secondary_button(footer, "Cerrar", dlg.destroy, width=12, height=1).pack(
            side="left", padx=(10, 0)
        )

        # Atajos globales del modal (no interferir con la nota)
        def _on_return(event=None):
            w = dlg.focus_get()
            if w is nota:
                return None
            if editable:
                guardar()
            return "break"

        dlg.bind("<Return>", _on_return)
        dlg.bind("<KP_Enter>", _on_return)
        dlg.bind("<Escape>", lambda _e: dlg.destroy())

        # Enfocar primer ítem pendiente (o el primero)
        if editable and chk_btns:
            start = 0
            for i, (key, _c, _l) in enumerate(CHECKLIST_CIERRE_GENERAL):
                if not vars_c[key].get():
                    start = i
                    break
            dlg.after(80, lambda: _focus_chk(start))

    def _pack_provision_block(self, parent, prov, titulo="Provisión administrativa"):
        box = tk.Frame(
            parent,
            bg=BG_ELEVATED,
            padx=10,
            pady=8,
            highlightthickness=1,
            highlightbackground=CYAN,
        )
        box.pack(fill="x", pady=(0, 8))
        styled_label(box, titulo, FONT_LABEL, CYAN, BG_ELEVATED).pack(anchor="w")
        lineas = [
            ("Ventas generales", formato_dinero(prov.get("ventas_generales"))),
            ("30%", formato_dinero(prov.get("treinta_porciento"))),
            ("Redondeo (obj. día)", formato_dinero(prov.get("provision_objetivo"))),
            ("Saldo pendiente ant.", formato_dinero(prov.get("saldo_pendiente_anterior"))),
            ("Objetivo total", formato_dinero(prov.get("objetivo_total"))),
            ("Efectivo disponible", formato_dinero(prov.get("efectivo_disponible"))),
            ("Efectivo provisionado", formato_dinero(prov.get("efectivo_provisionado"))),
            ("Nuevo saldo pendiente", formato_dinero(prov.get("nuevo_saldo_pendiente"))),
        ]
        for label, val in lineas:
            row = tk.Frame(box, bg=BG_ELEVATED)
            row.pack(fill="x", pady=1)
            styled_label(row, label, FONT_SMALL, TEXT_DIM, BG_ELEVATED).pack(side="left")
            styled_label(row, val, FONT_SMALL, TEXT, BG_ELEVATED).pack(side="right")

    def _mostrar_dialogo_provision(self, prov, titulo="Provisión administrativa"):
        if not prov:
            return
        dlg = tk.Toplevel(self)
        prepare_modal(dlg, self, titulo, 480, 420, resizable=True)
        card = card_frame(dlg, padx=16, pady=14)
        card.pack(fill="both", expand=True)
        self._pack_provision_block(card, prov, titulo=titulo)
        primary_button(card, "Cerrar", dlg.destroy, width=12, height=1).pack(anchor="w", pady=(12, 0))

    def _ver_provision(self):
        data = resumen_provision_admin(self.usuario)
        dlg = tk.Toplevel(self)
        prepare_modal(dlg, self, "Provisión administrativa", 720, 520, resizable=True)
        shell = tk.Frame(dlg, bg=BG, padx=14, pady=12)
        shell.pack(fill="both", expand=True)
        styled_label(shell, "Provisión administrativa (30% ventas · solo efectivo)", FONT_HEADING, TEXT, BG).pack(
            anchor="w"
        )
        styled_label(
            shell,
            "Saldo pendiente acumulado: {}".format(formato_dinero(data.get("saldo_pendiente"))),
            FONT_SUB,
            SUCCESS if _safe_float(data.get("saldo_pendiente")) == 0 else WARNING,
            BG,
        ).pack(anchor="w", pady=(6, 10))
        wrap, tree = scrollable_tree(
            shell,
            columns=("Id", "CG", "Estado", "Ventas", "Obj", "Prov", "Pend", "Fecha"),
            headings=("ID", "CG", "Estado", "Ventas", "Objetivo", "Provisionado", "Nuevo pend.", "Fecha"),
            height=12,
            widths={
                "Id": 45,
                "CG": 45,
                "Estado": 90,
                "Ventas": 90,
                "Obj": 90,
                "Prov": 100,
                "Pend": 100,
                "Fecha": 120,
            },
        )
        wrap.pack(fill="both", expand=True)
        for p in data.get("historial") or []:
            tree.insert(
                "",
                "end",
                values=(
                    p.get("id"),
                    p.get("cierre_general_id"),
                    p.get("estado"),
                    formato_dinero(p.get("ventas_generales")),
                    formato_dinero(p.get("objetivo_total")),
                    formato_dinero(p.get("efectivo_provisionado")),
                    formato_dinero(p.get("nuevo_saldo_pendiente")),
                    str(p.get("fecha") or "")[:16],
                ),
            )
        secondary_button(shell, "Cerrar", dlg.destroy, width=12, height=1).pack(anchor="w", pady=(10, 0))

    def _consolidar(self, gid):
        if not mb.askyesno(
            "Consolidar",
            "¿Consolidar el cierre general #{}?\n"
            "Se calculará la provisión administrativa y el ingreso al bolsillo de proveedores\n"
            "(efectivo sobrante + billetera digital; Datafono → billetera T+1 hábil 14:00).\n"
            "Un día consolidado no podrá volver a consolidarse.".format(gid),
            parent=self,
        ):
            return
        result = consolidar_cierre_general(self.usuario, gid)
        ok, msg = result[0], result[1]
        payload = result[2] if len(result) > 2 else None
        if ok:
            mb.showinfo("Cierre general", msg, parent=self)
            self._cargar_lista()
            self._mostrar_detalle(gid)
            prov = None
            ingreso_prov = None
            if isinstance(payload, dict) and (
                "provision" in payload or "proveedores" in payload
            ):
                prov = payload.get("provision")
                ingreso_prov = payload.get("proveedores")
            elif isinstance(payload, dict):
                prov = payload
            if prov:
                self._mostrar_dialogo_provision(prov, "Provisión aplicada al consolidar")
            if ingreso_prov:
                self._mostrar_dialogo_proveedores(ingreso_prov)
        else:
            mb.showerror("Cierre general", msg, parent=self)

    def _mostrar_dialogo_proveedores(self, ingreso):
        if not ingreso:
            return
        dlg = tk.Toplevel(self)
        prepare_modal(dlg, self, "Bolsillo proveedores", 460, 320, resizable=True)
        card = card_frame(dlg, padx=16, pady=14)
        card.pack(fill="both", expand=True)
        styled_label(card, "Ingreso a proveedores (post-provisión)", FONT_LABEL, CYAN, BG_CARD).pack(
            anchor="w"
        )
        for label, key in (
            ("Efectivo sobrante", "efectivo"),
            ("Nequi ventas", "nequi"),
            ("Datafono ventas", "datafono"),
            ("Total proveedores", "total"),
        ):
            row = tk.Frame(card, bg=BG_CARD)
            row.pack(fill="x", pady=2)
            styled_label(row, label, FONT_SMALL, TEXT_DIM, BG_CARD).pack(side="left")
            styled_label(
                row, formato_dinero(ingreso.get(key)), FONT_SMALL, TEXT, BG_CARD
            ).pack(side="right")
        primary_button(card, "Cerrar", dlg.destroy, width=12, height=1).pack(anchor="w", pady=(12, 0))


def _safe_float(v):
    try:
        return float(v or 0)
    except (TypeError, ValueError):
        return 0.0
