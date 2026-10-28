import tkinter as tk
from tkinter import ttk
import mensaje as mb

from Consultas import guardar_receta, mostrar_Productos, obtener_receta, parse_producto
from zyntra_ui import *


class EditorReceta:
    def __init__(self, parent=None):
        self.win = tk.Toplevel(parent) if parent else tk.Toplevel()
        prepare_modal(self.win, parent, "Receta / Kit", 720, 520, resizable=True)
        self.insumos = []
        self.items()

    def items(self):
        card = card_frame(self.win, padx=18, pady=16)
        card.pack(fill="both", expand=True)
        styled_label(card, "Insumos del producto de venta", FONT_HEADING, TEXT, BG_CARD).pack(anchor="w")
        styled_label(
            card,
            "Al vender el producto final se descontará cada insumo de la receta.",
            FONT_SMALL,
            TEXT_DIM,
            BG_CARD,
        ).pack(anchor="w", pady=(2, 10))

        row = tk.Frame(card, bg=BG_CARD)
        row.pack(fill="x")
        styled_label(row, "Producto final", FONT_LABEL, TEXT_MUTED, BG_CARD).pack(anchor="w")
        self.combo_final = ttk.Combobox(row, font=("Segoe UI", 11), style="Zyntra.TCombobox", state="readonly")
        self.combo_final.pack(fill="x", pady=(4, 8))
        self.productos = []
        for rowp in mostrar_Productos() or []:
            datos = parse_producto(rowp)
            self.productos.append(datos)
        self.combo_final["values"] = [f"{p['id']} — {p['nombre']}" for p in self.productos]
        self.combo_final.bind("<<ComboboxSelected>>", self._cargar_receta)

        add = tk.Frame(card, bg=BG_CARD)
        add.pack(fill="x", pady=(0, 8))
        self.combo_insumo = ttk.Combobox(add, font=("Segoe UI", 11), style="Zyntra.TCombobox", state="readonly")
        self.combo_insumo.pack(side="left", fill="x", expand=True)
        self.combo_insumo["values"] = [f"{p['id']} — {p['nombre']}" for p in self.productos]
        self.qty = styled_entry(add, width=8)
        self.qty.pack(side="left", padx=8)
        self.qty.insert(0, "1")
        plus_button(add, self._agregar).pack(side="left")

        self.wrap, self.tree = scrollable_tree(
            card,
            columns=("Id", "Insumo", "Cantidad"),
            headings=("ID", "Insumo", "Cant. por unidad"),
            height=8,
            widths={"Id": 70, "Insumo": 280, "Cantidad": 120},
        )
        self.tree.column("Insumo", anchor="w")
        self.wrap.pack(fill="both", expand=True)
        btns = tk.Frame(card, bg=BG_CARD)
        btns.pack(fill="x", pady=(10, 0))
        secondary_button(btns, "Quitar insumo", self._quitar, width=16).pack(side="left")
        primary_button(btns, "Guardar receta", self._guardar, width=16).pack(side="right")

    def _id_combo(self, combo):
        texto = combo.get()
        if not texto or "—" not in texto:
            return None
        try:
            return int(texto.split("—", 1)[0].strip())
        except ValueError:
            return None

    def _cargar_receta(self, event=None):
        producto_id = self._id_combo(self.combo_final)
        self.tree.delete(*self.tree.get_children())
        self.insumos = obtener_receta(producto_id) if producto_id else []
        for item in self.insumos:
            self.tree.insert("", "end", values=(item["insumo_id"], item["nombre"], item["cantidad"]))

    def _agregar(self):
        insumo_id = self._id_combo(self.combo_insumo)
        producto_id = self._id_combo(self.combo_final)
        if not producto_id or not insumo_id:
            mb.showwarning("Receta", "Seleccione producto final e insumo.", parent=self.win)
            return
        if insumo_id == producto_id:
            mb.showwarning("Receta", "Un producto no puede ser insumo de sí mismo.", parent=self.win)
            return
        try:
            cantidad = float(self.qty.get().replace(",", "."))
        except ValueError:
            mb.showerror("Receta", "La cantidad del insumo debe ser numérica.", parent=self.win)
            return
        if cantidad <= 0:
            return
        nombre = self.combo_insumo.get().split("—", 1)[-1].strip()
        self.tree.insert("", "end", values=(insumo_id, nombre, cantidad))

    def _quitar(self):
        for item in self.tree.selection():
            self.tree.delete(item)

    def _guardar(self):
        producto_id = self._id_combo(self.combo_final)
        if not producto_id:
            mb.showwarning("Receta", "Seleccione el producto final.", parent=self.win)
            return
        insumos = []
        for item in self.tree.get_children():
            valores = self.tree.item(item, "values")
            insumos.append({"insumo_id": int(valores[0]), "cantidad": float(valores[2])})
        if guardar_receta(producto_id, insumos):
            mb.showinfo("Receta", "Receta / kit guardado. Se descontará en cada venta.", parent=self.win)
            self.win.destroy()
        else:
            mb.showerror("Receta", "No se pudo guardar la receta.", parent=self.win)
