import tkinter as tk
import mensaje as mb
from tkinter import ttk

from Consultas import *
from auditoria import log_accion
from zyntra_ui import *


def _dinero(valor):
    return parse_dinero(valor)


class SelectorCliente(tk.Toplevel):
    def __init__(self, parent, on_select):
        super().__init__(parent)
        self.on_select = on_select
        prepare_modal(self, parent, "Asociar cliente", 560, 420)
        card = card_frame(self, padx=18, pady=16)
        card.pack(fill="both", expand=True)
        styled_label(card, "Buscar cliente", FONT_HEADING, TEXT, BG_CARD).pack(anchor="w")
        self.buscar = styled_entry(card)
        self.buscar.pack(fill="x", pady=(8, 10))
        self.buscar.bind("<KeyRelease>", self._filtrar)
        self.wrap, self.tree = scrollable_tree(
            card,
            columns=("Id", "Nombre", "Documento", "Saldo", "Puntos"),
            headings=("ID", "Nombre", "Documento", "Saldo", "Puntos"),
            height=8,
            widths={"Id": 50, "Nombre": 160, "Documento": 100, "Saldo": 90, "Puntos": 70},
        )
        self.tree.column("Nombre", anchor="w")
        self.wrap.pack(fill="both", expand=True)
        self.tree.bind("<Double-1>", lambda _e: self._elegir())
        primary_button(card, "Seleccionar", self._elegir, width=18).pack(pady=(10, 0))
        self._filtrar()
        self.buscar.focus_set()

    def _filtrar(self, event=None):
        self.tree.delete(*self.tree.get_children())
        for cli in buscar_clientes(self.buscar.get().strip()):
            self.tree.insert("", "end", values=(cli["id"], cli["nombre"], cli["documento"], formato_dinero(cli["saldo"]), cli["puntos"]))

    def _elegir(self):
        sel = self.tree.selection()
        if not sel:
            mb.showwarning("Cliente", "Seleccione un cliente.", parent=self)
            return
        id_cliente = self.tree.item(sel[0], "values")[0]
        cliente = obtener_cliente(id_cliente)
        if cliente and self.on_select:
            self.on_select(cliente)
        self.destroy()


class CuentasPorCobrar(tk.Frame):
    def __init__(self, parent, usuario):
        super().__init__(parent, bg=BG)
        self.usuario = usuario
        self.cliente_id = None
        self.items()

    def items(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=3, minsize=260)
        self.grid_rowconfigure(2, weight=2, minsize=120)

        top = card_frame(self, padx=12, pady=8)
        top.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        styled_label(top, "Cuentas por cobrar y fidelización", FONT_HEADING, TEXT, BG_CARD).pack(anchor="w")
        row = tk.Frame(top, bg=BG_CARD)
        row.pack(fill="x", pady=(8, 0))
        self.buscar = styled_entry(row, width=32)
        self.buscar.pack(side="left", fill="x", expand=True)
        self.buscar.bind("<KeyRelease>", lambda _e: debounce(self, "_cli_job", 160, self._cargar_clientes))
        secondary_button(row, "Configurar puntos", self._configurar_puntos, width=16, font=FONT_SMALL).pack(side="left", padx=(8, 0))

        body = tk.Frame(self, bg=BG)
        body.grid(row=1, column=0, sticky="nsew", pady=(0, 8))
        body.grid_columnconfigure(0, weight=1)
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(0, weight=1)

        left = card_frame(body, padx=12, pady=10)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        styled_label(left, "Clientes", FONT_SUB, TEXT, BG_CARD).pack(anchor="w")
        self.wrap, self.tree = scrollable_tree(
            left,
            columns=("Id", "Nombre", "Documento", "Telefono", "Limite", "Saldo", "Puntos"),
            headings=("ID", "Nombre", "Doc.", "Teléfono", "Límite", "Saldo", "Pts"),
            height=6,
            widths={"Id": 40, "Nombre": 120, "Documento": 80, "Telefono": 80, "Limite": 70, "Saldo": 70, "Puntos": 50},
        )
        self.tree.column("Nombre", anchor="w")
        self.wrap.pack(fill="both", expand=True, pady=(8, 0))
        self.tree.bind("<<TreeviewSelect>>", self._seleccionar)

        right = card_frame(body, padx=12, pady=10)
        right.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        head = tk.Frame(right, bg=BG_CARD)
        head.pack(fill="x", pady=(0, 8))
        styled_label(head, "Ficha del cliente", FONT_SUB, TEXT, BG_CARD).pack(side="left", anchor="w")
        btns = tk.Frame(head, bg=BG_CARD)
        btns.pack(side="right")
        primary_button(btns, "Guardar", self._guardar, width=10, font=FONT_SMALL).pack(side="left", padx=(0, 6))
        secondary_button(btns, "Nuevo", self._limpiar, width=8, font=FONT_SMALL).pack(side="left")

        form_wrap = tk.Frame(right, bg=BG_CARD)
        form_wrap.pack(fill="both", expand=True)
        form_wrap.grid_columnconfigure(0, weight=1)
        form_wrap.grid_rowconfigure(0, weight=1)
        canvas = tk.Canvas(form_wrap, bg=BG_CARD, highlightthickness=0, bd=0)
        vsb = ttk.Scrollbar(form_wrap, orient="vertical", command=canvas.yview)
        form = tk.Frame(canvas, bg=BG_CARD)
        form_id = canvas.create_window((0, 0), window=form, anchor="nw")
        canvas.configure(yscrollcommand=vsb.set)

        def _sync_scroll(_event=None):
            canvas.configure(scrollregion=canvas.bbox("all"))
            canvas.itemconfigure(form_id, width=canvas.winfo_width())

        form.bind("<Configure>", _sync_scroll)
        canvas.bind("<Configure>", _sync_scroll)
        canvas.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")

        def _on_wheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            return "break"

        canvas.bind("<Enter>", lambda _e: canvas.bind_all("<MouseWheel>", _on_wheel))
        canvas.bind("<Leave>", lambda _e: canvas.unbind_all("<MouseWheel>"))
        form.bind("<Enter>", lambda _e: canvas.bind_all("<MouseWheel>", _on_wheel))
        form.bind("<Leave>", lambda _e: canvas.unbind_all("<MouseWheel>"))

        _, self.nombre = labeled_field(form, "Nombre")
        _.pack(fill="x", pady=(0, 6))
        rowf = tk.Frame(form, bg=BG_CARD)
        rowf.pack(fill="x", pady=(0, 6))
        b1, self.documento = labeled_field(rowf, "Cédula / NIT")
        b1.pack(side="left", fill="x", expand=True, padx=(0, 6))
        b2, self.telefono = labeled_field(rowf, "Teléfono")
        b2.pack(side="left", fill="x", expand=True)
        _, self.limite = labeled_field(form, "Límite de crédito")
        bind_money_entry(self.limite)
        _.pack(fill="x", pady=(0, 4))

        hist = card_frame(self, padx=12, pady=8)
        hist.grid(row=2, column=0, sticky="nsew", pady=(0, 8))
        styled_label(hist, "Historial de deudas y movimientos", FONT_LABEL, TEXT, BG_CARD).pack(anchor="w")
        self.mov_wrap, self.tree_mov = scrollable_tree(
            hist,
            columns=("Fecha", "Tipo", "Monto", "Puntos", "Venta", "Usuario", "Comentario"),
            headings=("Fecha", "Tipo", "Monto", "Pts", "Venta", "Usuario", "Comentario"),
            height=4,
            widths={"Fecha": 130, "Tipo": 80, "Monto": 80, "Puntos": 50, "Venta": 60, "Usuario": 90, "Comentario": 160},
        )
        self.tree_mov.column("Comentario", anchor="w")
        self.mov_wrap.pack(fill="both", expand=True, pady=(6, 0))

        footer = card_frame(self, padx=12, pady=8)
        footer.grid(row=3, column=0, sticky="ew")
        info = tk.Frame(footer, bg=BG_CARD)
        info.pack(fill="x")
        self.lbl_saldo = styled_label(info, "Saldo: $ 0", FONT_SUB, WARNING, BG_CARD)
        self.lbl_saldo.pack(side="left")
        self.lbl_puntos = styled_label(info, "Puntos: 0", FONT_SUB, CYAN, BG_CARD)
        self.lbl_puntos.pack(side="left", padx=(16, 0))
        abono = tk.Frame(footer, bg=BG_CARD)
        abono.pack(fill="x", pady=(8, 0))
        styled_label(abono, "Abono", FONT_LABEL, TEXT_MUTED, BG_CARD).pack(side="left")
        self.abono = styled_entry(abono, width=14)
        self.abono.pack(side="left", padx=8)
        bind_money_entry(self.abono)
        self.metodo_abono = ttk.Combobox(
            abono,
            font=("Segoe UI", 11),
            style="Zyntra.TCombobox",
            values=("Efectivo", "Nequi", "Transferencia"),
            width=14,
            state="readonly",
        )
        self.metodo_abono.set("Efectivo")
        self.metodo_abono.pack(side="left", padx=(0, 8))
        primary_button(abono, "Registrar abono", self._abonar, width=16).pack(side="left")

    def on_show(self):
        if should_refresh(self):
            self._cargar_clientes()
        self.buscar.focus_set()

    def _cargar_clientes(self):
        texto = self.buscar.get().strip()

        def ok(clientes):
            self.tree.delete(*self.tree.get_children())
            for cli in clientes or []:
                self.tree.insert(
                    "",
                    "end",
                    values=(cli["id"], cli["nombre"], cli["documento"], cli["telefono"], formato_dinero(cli["limite"]), formato_dinero(cli["saldo"]), cli["puntos"]),
                )
            mark_refreshed(self)

        load_async(self, lambda: buscar_clientes(texto), ok)

    def _seleccionar(self, event=None):
        sel = self.tree.selection()
        if not sel:
            return
        valores = self.tree.item(sel[0], "values")
        cliente = obtener_cliente(valores[0])
        if not cliente:
            return
        self.cliente_id = cliente["id"]
        for entry, valor in (
            (self.nombre, cliente["nombre"]),
            (self.documento, cliente["documento"]),
            (self.telefono, cliente["telefono"]),
            (self.limite, f"{cliente['limite']:.0f}"),
        ):
            entry.delete(0, tk.END)
            entry.insert(0, valor)
        self.lbl_saldo.config(text=f"Saldo: {formato_dinero(cliente['saldo'])}")
        self.lbl_puntos.config(text=f"Puntos: {cliente['puntos']}")
        self.tree_mov.delete(*self.tree_mov.get_children())
        for row in movimientos_cliente(self.cliente_id):
            self.tree_mov.insert("", "end", values=row)

    def _limpiar(self):
        self.cliente_id = None
        for entry in (self.nombre, self.documento, self.telefono, self.limite, self.abono):
            entry.delete(0, tk.END)
        self.lbl_saldo.config(text="Saldo: $ 0")
        self.lbl_puntos.config(text="Puntos: 0")
        self.tree_mov.delete(*self.tree_mov.get_children())
        self.nombre.focus_set()

    def _guardar(self):
        nombre = self.nombre.get().strip()
        documento = self.documento.get().strip()
        telefono = self.telefono.get().strip()
        try:
            limite = _dinero(self.limite.get())
        except ValueError:
            mb.showerror("Error", "El límite debe ser numérico.", parent=self)
            return
        if not nombre or not documento:
            mb.showwarning("Cliente", "Nombre y documento son obligatorios.", parent=self)
            return
        ok, msg = guardar_cliente(nombre, documento, telefono, limite, self.cliente_id)
        if ok:
            mb.showinfo("Éxito", "Cliente guardado.", parent=self)
            self._cargar_clientes()
        else:
            mb.showerror("Error", msg or "No se pudo guardar el cliente.", parent=self)

    def _abonar(self):
        if not self.cliente_id:
            mb.showwarning("Abono", "Seleccione un cliente.", parent=self)
            return
        monto = _dinero(self.abono.get())
        if monto <= 0:
            mb.showwarning("Abono", "Ingrese un monto válido.", parent=self)
            return
        metodo = (self.metodo_abono.get() or "Efectivo").strip()
        ok, msg = registrar_abono_cliente(
            self.cliente_id, monto, self.usuario, "Abono en {}".format(metodo.lower()), metodo
        )
        if not ok:
            mb.showerror("Abono", msg, parent=self)
            return
        log_accion(self.usuario, "Abono de crédito", f"Cliente #{self.cliente_id} abonó {formato_dinero(monto)} en {metodo}")
        mb.showinfo("Abono", "Abono registrado. Si fue en efectivo, ya entra a la caja.", parent=self)
        self.abono.delete(0, tk.END)
        self._cargar_clientes()
        cliente = obtener_cliente(self.cliente_id)
        if cliente:
            self.lbl_saldo.config(text=f"Saldo: {formato_dinero(cliente['saldo'])}")
            self.lbl_puntos.config(text=f"Puntos: {cliente['puntos']}")
            self.tree_mov.delete(*self.tree_mov.get_children())
            for row in movimientos_cliente(self.cliente_id):
                self.tree_mov.insert("", "end", values=row)

    def _configurar_puntos(self):
        cfg = obtener_config_pos()
        dlg = tk.Toplevel(self)
        prepare_modal(dlg, self, "Fidelización", 420, 280)
        card = card_frame(dlg, padx=22, pady=18)
        card.pack(fill="both", expand=True)
        styled_label(card, "Reglas de puntos", FONT_HEADING, TEXT, BG_CARD).pack(anchor="w", pady=(0, 10))
        _, pesos = labeled_field(card, "Pesos para ganar 1 punto")
        _.pack(fill="x", pady=(0, 8))
        pesos.insert(0, str(cfg["pesos_por_punto"]))
        _, valor = labeled_field(card, "Valor de cada punto al canjear ($)")
        _.pack(fill="x", pady=(0, 8))
        valor.insert(0, str(int(cfg["valor_punto"])))
        _, dias = labeled_field(card, "Días de cobertura para sugerido")
        _.pack(fill="x", pady=(0, 12))
        dias.insert(0, str(cfg["dias_cobertura"]))

        def guardar():
            try:
                guardar_config_pos(int(pesos.get()), float(valor.get()), int(dias.get() or 15))
                mb.showinfo("Configuración", "Reglas de fidelización actualizadas.", parent=dlg)
                dlg.destroy()
            except ValueError:
                mb.showerror("Error", "Ingrese valores numéricos.", parent=dlg)

        primary_button(card, "Guardar", guardar, width=20).pack(fill="x")
