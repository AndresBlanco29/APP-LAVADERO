import tkinter as tk
from tkinter import ttk
import mensaje as mb
import Consultas
from zyntra_ui import *


class AjusteInventario:
    def __init__(self, parent=None, usuario=None, codigo_inicial=None):
        self.usuario = usuario or ""
        self.win = tk.Toplevel(parent) if parent else tk.Toplevel()
        prepare_modal(self.win, parent, "Ajuste de inventario", 980, 640, resizable=True)
        limit_minsize(self.win, 780, 480)
        self._pres_opciones = []
        self.items()
        if codigo_inicial:
            self.codigo.insert(0, str(codigo_inicial))
            self._cargar_producto()

    def items(self):
        footer = card_frame(self.win, padx=16, pady=10)
        footer.pack(side="bottom", fill="x", padx=12, pady=12)
        primary_button(footer, "Registrar ajuste", self._guardar, width=18).pack(
            side="left", fill="x", expand=True, padx=(0, 8)
        )
        danger_button(footer, "Cerrar", self.win.destroy, width=14).pack(side="left", fill="x", expand=True)

        wrap, card = scrollable_body(self.win, padx=20, pady=14)
        wrap.pack(fill="both", expand=True, padx=12, pady=(12, 0))
        styled_label(card, "Ajuste de inventario", FONT_HEADING, TEXT, BG_CARD).pack(anchor="w")
        styled_label(
            card,
            "Sume o reste existencia eligiendo la presentación. Internamente se convierte a la unidad base.",
            FONT_SMALL,
            TEXT_DIM,
            BG_CARD,
        ).pack(anchor="w", pady=(2, 10))

        row = tk.Frame(card, bg=BG_CARD)
        row.pack(fill="x", pady=(0, 8))
        box, self.codigo = labeled_field(row, "Código o nombre")
        box.pack(side="left", fill="x", expand=True, padx=(0, 8))
        primary_button(row, "Buscar", self._cargar_producto, width=10, font=FONT_SMALL).pack(side="left", pady=(18, 0))
        self.codigo.bind("<Return>", lambda _e: self._cargar_producto())

        self.lbl_prod = styled_label(card, "Seleccione un producto.", FONT_SUB, TEXT, BG_CARD)
        self.lbl_prod.pack(anchor="w", pady=(0, 4))
        self.lbl_stock = styled_label(card, "", FONT_SMALL, TEXT_DIM, BG_CARD)
        self.lbl_stock.pack(anchor="w", pady=(0, 10))

        row2 = tk.Frame(card, bg=BG_CARD)
        row2.pack(fill="x", pady=(0, 8))
        box_p = tk.Frame(row2, bg=BG_CARD)
        box_p.pack(side="left", fill="x", expand=True, padx=(0, 8))
        styled_label(box_p, "Presentación", FONT_LABEL, TEXT_MUTED, BG_CARD).pack(anchor="w")
        self.presentacion = ttk.Combobox(box_p, font=("Segoe UI", 11), style="Zyntra.TCombobox", state="readonly")
        self.presentacion.pack(fill="x", pady=(6, 0))
        box_c, self.cantidad = labeled_field(row2, "Cantidad")
        box_c.pack(side="left", fill="x", expand=True)

        row3 = tk.Frame(card, bg=BG_CARD)
        row3.pack(fill="x", pady=(0, 8))
        styled_label(row3, "Tipo", FONT_LABEL, TEXT_MUTED, BG_CARD).pack(anchor="w")
        tipos = tk.Frame(row3, bg=BG_CARD)
        tipos.pack(anchor="w", pady=(4, 0))
        self.var_tipo = tk.StringVar(value="ENTRADA")
        tk.Radiobutton(
            tipos, text="Entrada (sumar)", variable=self.var_tipo, value="ENTRADA",
            bg=BG_CARD, fg=TEXT, selectcolor=BG_INPUT, activebackground=BG_CARD, activeforeground=TEXT, font=FONT_LABEL,
        ).pack(side="left")
        tk.Radiobutton(
            tipos, text="Salida (restar)", variable=self.var_tipo, value="SALIDA",
            bg=BG_CARD, fg=TEXT, selectcolor=BG_INPUT, activebackground=BG_CARD, activeforeground=TEXT, font=FONT_LABEL,
        ).pack(side="left", padx=(16, 0))

        _, self.motivo = labeled_field(card, "Motivo")
        _.pack(fill="x", pady=(0, 10))

        styled_label(card, "Movimientos recientes", FONT_SUB, TEXT, BG_CARD).pack(anchor="w")
        self.mov_wrap, self.tree_mov = scrollable_tree(
            card,
            columns=("Fecha", "Tipo", "Cant", "Factor", "Base", "Motivo", "Usuario"),
            headings=("Fecha", "Tipo", "Cant.", "Conv.", "Base", "Motivo", "Usuario"),
            height=8,
            widths={"Fecha": 130, "Tipo": 80, "Cant": 60, "Factor": 50, "Base": 70, "Motivo": 180, "Usuario": 90},
        )
        self.tree_mov.column("Motivo", anchor="w")
        self.mov_wrap.pack(fill="both", expand=True, pady=(6, 0))
        self._producto = None

    def _presentacion(self):
        nombre = (self.presentacion.get() or "").strip()
        for item in self._pres_opciones:
            if item.get("nombre") == nombre:
                return item
        return self._pres_opciones[0] if self._pres_opciones else {"nombre": "Unidad", "factor": 1, "id": None}

    def _cargar_producto(self):
        texto = self.codigo.get().strip()
        if not texto:
            mb.showwarning("Ajuste", "Ingrese código o nombre.", parent=self.win)
            return
        row = None
        if texto.isdigit():
            row = Consultas.obtener_producto(texto)
        if not row:
            encontrados = Consultas.buscar_productos(texto, texto, texto) or []
            if encontrados:
                row = encontrados[0]
        datos = Consultas.parse_producto(row) if row else None
        if not datos:
            mb.showerror("Ajuste", "No se encontró el producto.", parent=self.win)
            return
        self._producto = datos
        self._pres_opciones = Consultas.listar_presentaciones(datos["id"]) or [
            {"nombre": "Unidad", "factor": 1, "id": None}
        ]
        self.presentacion["values"] = [p["nombre"] for p in self._pres_opciones]
        self.presentacion.set(self._pres_opciones[0]["nombre"])
        unidad = datos.get("unidad_base") or "Unidad"
        self.lbl_prod.config(text="{}  ·  {}".format(datos["id"], datos["nombre"]))
        self.lbl_stock.config(
            text=Consultas.texto_equivalencias(datos.get("cantidad") or 0, self._pres_opciones, unidad)
        )
        self._pintar_movimientos()
        self.cantidad.focus_set()

    def _pintar_movimientos(self):
        self.tree_mov.delete(*self.tree_mov.get_children())
        if not self._producto:
            return
        for row in Consultas.listar_movimientos_inventario(self._producto["id"]):
            self.tree_mov.insert("", "end", values=row)

    def _guardar(self):
        if not self._producto:
            self._cargar_producto()
            if not self._producto:
                return
        pres = self._presentacion()
        ok, msg = Consultas.ajustar_inventario(
            self._producto["id"],
            self.cantidad.get(),
            pres.get("factor") or 1,
            self.var_tipo.get(),
            self.motivo.get(),
            self.usuario,
            pres.get("id"),
        )
        if not ok:
            mb.showerror("Ajuste", msg, parent=self.win)
            return
        mb.showinfo("Ajuste", msg, parent=self.win)
        self.cantidad.delete(0, tk.END)
        self.motivo.delete(0, tk.END)
        self.codigo.delete(0, tk.END)
        self.codigo.insert(0, str(self._producto["id"]))
        self._cargar_producto()
