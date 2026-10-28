import tkinter as tk
from tkinter import ttk
import mensaje as mb
from Consultas import *
from zyntra_ui import *


class nuevo_producto:
    def __init__(self, parent=None):
        self.nuevo = tk.Toplevel(parent) if parent else tk.Toplevel()
        prepare_modal(self.nuevo, parent, "Crear un producto", 1400, 900, resizable=True)
        limit_minsize(self.nuevo, 720, 420)
        self.items()

    def items(self):
        footer = card_frame(self.nuevo, padx=20, pady=12)
        footer.pack(side="bottom", fill="x", padx=12, pady=12)
        wrap, card = scrollable_body(self.nuevo, padx=32, pady=22)
        wrap.pack(fill="both", expand=True, padx=12, pady=(12, 0))
        styled_label(card, "Crear un producto", FONT_HEADING, TEXT, BG_CARD).pack(anchor="w")
        intro = styled_label(
            card,
            "Elija si el precio de compra va sin IVA o con IVA. El porcentaje se escribe a mano.",
            FONT_SMALL,
            TEXT_DIM,
            BG_CARD,
        )
        intro.configure(wraplength=720, justify="left")
        intro.pack(anchor="w", fill="x", pady=(2, 14))

        _, self.codigo = labeled_field(card, "Código")
        self.codigo.configure(state="readonly")
        _.pack(fill="x", pady=(0, 8))

        _, self.nombre_producto = labeled_field(card, "Nombre")
        _.pack(fill="x", pady=(0, 8))
        self.nombre_producto.focus()

        self.lbl_compra = styled_label(card, "Precio de compra (sin IVA)", FONT_LABEL, TEXT_MUTED, BG_CARD)
        self.lbl_compra.pack(anchor="w")
        chk = tk.Frame(card, bg=BG_CARD)
        chk.pack(fill="x", pady=(4, 6))
        self.var_sin_iva = tk.BooleanVar(value=True)
        self.var_con_iva = tk.BooleanVar(value=False)
        self._lock_iva = False
        chk_style = dict(
            bg=BG_CARD,
            fg=TEXT,
            selectcolor=BG_INPUT,
            activebackground=BG_CARD,
            activeforeground=TEXT,
            font=FONT_LABEL,
        )
        tk.Checkbutton(chk, text="Sin IVA", variable=self.var_sin_iva, command=self._elegir_sin_iva, **chk_style).pack(
            side="left"
        )
        tk.Checkbutton(chk, text="Con IVA", variable=self.var_con_iva, command=self._elegir_con_iva, **chk_style).pack(
            side="left", padx=(16, 0)
        )

        row = tk.Frame(card, bg=BG_CARD)
        row.pack(fill="x", pady=(0, 8))
        box_precio = tk.Frame(row, bg=BG_CARD)
        box_precio.pack(side="left", fill="x", expand=True, padx=(0, 8))
        styled_label(box_precio, "Valor", FONT_LABEL, TEXT_MUTED, BG_CARD).pack(anchor="w")
        self.precio_compra_producto = styled_entry(box_precio)
        self.precio_compra_producto.pack(fill="x", pady=(6, 0))
        box_iva = tk.Frame(row, bg=BG_CARD)
        box_iva.pack(side="left", fill="x", expand=True)
        styled_label(box_iva, "IVA %", FONT_LABEL, TEXT_MUTED, BG_CARD).pack(anchor="w")
        self.iva_producto = styled_entry(box_iva)
        self.iva_producto.pack(fill="x", pady=(6, 0))

        row_p = tk.Frame(card, bg=BG_CARD)
        row_p.pack(fill="x", pady=(0, 2))
        box_g = tk.Frame(row_p, bg=BG_CARD)
        box_g.pack(side="left", fill="x", expand=True, padx=(0, 8))
        styled_label(box_g, "Utilidad %", FONT_LABEL, TEXT_MUTED, BG_CARD).pack(anchor="w")
        self.ganancia_producto = ttk.Combobox(
            box_g, font=("Segoe UI", 11), style="Zyntra.TCombobox", values=UTILIDAD_CHOICES
        )
        self.ganancia_producto.pack(fill="x", pady=(6, 0))
        self.ganancia_producto.set("20%")
        box_v, self.precio_venta_producto = labeled_field(row_p, "Precio de venta (con IVA)")
        box_v.pack(side="left", fill="x", expand=True)

        self.lbl_costo_iva = styled_label(card, "", FONT_SMALL, TEXT_DIM, BG_CARD)
        self.lbl_costo_iva.configure(wraplength=640, justify="left")
        self.lbl_costo_iva.pack(anchor="w", fill="x", pady=(0, 8))
        # conectar_margen se enlaza después de crear presentaciones
        self._aplicar_tipo_iva()

        row2 = tk.Frame(card, bg=BG_CARD)
        row2.pack(fill="x", pady=(0, 8))
        box_q, self.cantidad_producto = labeled_field(row2, "Cantidad (unidad base)")
        box_q.pack(side="left", fill="x", expand=True, padx=(0, 8))
        box_m, self.marca_producto = labeled_field(row2, "Marca")
        box_m.pack(side="left", fill="x", expand=True)

        row_u = tk.Frame(card, bg=BG_CARD)
        row_u.pack(fill="x", pady=(0, 8))
        box_ub = tk.Frame(row_u, bg=BG_CARD)
        box_ub.pack(side="left", fill="x", expand=True, padx=(0, 8))
        styled_label(box_ub, "Unidad base de inventario", FONT_LABEL, TEXT_MUTED, BG_CARD).pack(anchor="w")
        self.unidad_base = ttk.Combobox(box_ub, font=("Segoe UI", 11), style="Zyntra.TCombobox", values=UNIDADES_BASE)
        self.unidad_base.pack(fill="x", pady=(6, 0))
        self.unidad_base.set("Unidad")
        self.var_fraccion = tk.BooleanVar(value=True)
        tk.Checkbutton(
            row_u,
            text="Permitir venta fraccionada",
            variable=self.var_fraccion,
            bg=BG_CARD,
            fg=TEXT,
            selectcolor=BG_INPUT,
            activebackground=BG_CARD,
            activeforeground=TEXT,
            font=FONT_LABEL,
        ).pack(side="left", pady=(18, 0))

        _, self.categoria_producto = labeled_field(card, "Categoría")
        _.pack(fill="x", pady=(0, 8))

        row3 = tk.Frame(card, bg=BG_CARD)
        row3.pack(fill="x", pady=(0, 8))
        box_u, self.ubicacion_producto = labeled_field(row3, "Ubicación / estante")
        box_u.pack(side="left", fill="x", expand=True, padx=(0, 8))
        box_s, self.stock_minimo = labeled_field(row3, "Stock mínimo")
        box_s.pack(side="left", fill="x", expand=True)
        self.stock_minimo.insert(0, "10")

        row4 = tk.Frame(card, bg=BG_CARD)
        row4.pack(fill="x", pady=(0, 8))
        styled_label(row4, "Proveedor habitual", FONT_LABEL, TEXT_MUTED, BG_CARD).pack(anchor="w")
        self.proveedor_producto = ttk.Combobox(row4, font=("Segoe UI", 11), style="Zyntra.TCombobox")
        self.proveedor_producto.pack(fill="x", pady=(4, 0))
        try:
            self.proveedor_producto["values"] = llenar_combobox() or []
        except Exception:
            self.proveedor_producto["values"] = []

        from presentaciones import EditorPresentaciones

        self.editor_pres = EditorPresentaciones(
            card,
            get_costo_base=self._costo_base_actual,
            get_iva=lambda: self.iva_producto.get(),
            get_unidad=lambda: self.unidad_base.get() or "Unidad",
        )
        self.editor_pres.pack(fill="x", expand=False, pady=(0, 8))
        self.editor_pres.cargar()

        def _on_margen(utilidad_txt, venta_txt, manual_venta):
            if manual_venta:
                self.editor_pres.sincronizar_unidad(venta_txt, utilidad_txt)

        conectar_margen_venta(
            self.precio_compra_producto,
            self.ganancia_producto,
            self.precio_venta_producto,
            self.iva_producto,
            self.lbl_costo_iva,
            self.var_con_iva,
            on_margen=_on_margen,
        )

        def _ajustar_textos(event):
            ancho = max(event.width - 24, 280)
            self.lbl_costo_iva.configure(wraplength=ancho)
            intro.configure(wraplength=ancho)

        card.bind("<Configure>", _ajustar_textos)
        primary_button(footer, "Guardar", self.guardar_producto, width=18).pack(
            side="left", fill="x", expand=True, padx=(0, 8)
        )
        danger_button(footer, "Cancelar", self.cancelar_nuevo, width=18).pack(side="left", fill="x", expand=True)

        self.nuevo.update_idletasks()

        def _encajar():
            extra = footer.winfo_reqheight() + 48
            size_modal_to_content(self.nuevo, card, extra_height=extra)
            wrap.refresh_scroll()

        self.nuevo.after_idle(_encajar)

    def _elegir_sin_iva(self):
        if self._lock_iva:
            return
        self._lock_iva = True
        try:
            if self.var_sin_iva.get():
                self.var_con_iva.set(False)
            else:
                self.var_con_iva.set(True)
            self._aplicar_tipo_iva()
        finally:
            self._lock_iva = False

    def _elegir_con_iva(self):
        if self._lock_iva:
            return
        self._lock_iva = True
        try:
            if self.var_con_iva.get():
                self.var_sin_iva.set(False)
            else:
                self.var_sin_iva.set(True)
            self._aplicar_tipo_iva()
        finally:
            self._lock_iva = False

    def _aplicar_tipo_iva(self):
        con_iva = bool(self.var_con_iva.get())
        if con_iva:
            self.lbl_compra.config(text="Precio de compra (IVA incluido)")
            self.iva_producto.configure(state="normal")
        else:
            self.lbl_compra.config(text="Precio de compra (sin IVA)")
            self.iva_producto.configure(state="normal")
            self.iva_producto.delete(0, tk.END)
            self.iva_producto.configure(state="disabled")

    def guardar_producto(self):
        try:
            Nombre = self.nombre_producto.get().strip()
            precio_venta = self.precio_venta_producto.get().strip()
            precio_compra = self.precio_compra_producto.get().strip()
            cantidad = self.cantidad_producto.get().strip()
            marca = self.marca_producto.get().strip()
            categoria = self.categoria_producto.get().strip()
            ubicacion = self.ubicacion_producto.get().strip()
            stock_minimo = self.stock_minimo.get().strip() or "10"
            con_iva = bool(self.var_con_iva.get())
            iva_txt = self.iva_producto.get().strip()

            if not all([Nombre, precio_venta, precio_compra, cantidad, marca]):
                mb.showwarning("Advertencia", "Llene nombre, precios, cantidad y marca", parent=self.nuevo)
                return
            if con_iva:
                if not iva_txt:
                    mb.showerror("IVA", "Si el precio va con IVA, ingrese el porcentaje manualmente.", parent=self.nuevo)
                    self.iva_producto.configure(state="normal")
                    self.iva_producto.focus_set()
                    return
                if _a_float_precio(iva_txt.replace("%", "")) is None:
                    mb.showerror("IVA", "Ingrese un IVA numérico válido (por ejemplo 5 o 19).", parent=self.nuevo)
                    return
            iva_pct = iva_a_porcentaje(iva_txt) if con_iva else 0.0
            if con_iva and iva_pct <= 0:
                mb.showerror("IVA", "El IVA debe ser mayor a 0 cuando el precio incluye IVA.", parent=self.nuevo)
                return
            if iva_pct < 0 or iva_pct > 100:
                mb.showerror("Error", "El IVA debe estar entre 0 y 100.", parent=self.nuevo)
                return

            desglose = desglose_compra(precio_compra, iva_pct, con_iva)
            if not desglose or desglose["base"] <= 0:
                mb.showerror("Error", "Ingrese un precio de compra válido mayor a 0.", parent=self.nuevo)
                return
            precio_venta_n = redondear_centena(parse_dinero(precio_venta))
            if precio_venta_n <= 0:
                mb.showerror("Error", "El precio de venta debe ser mayor a 0.", parent=self.nuevo)
                return
            self.precio_venta_producto.delete(0, tk.END)
            self.precio_venta_producto.insert(0, formato_entrada(str(int(precio_venta_n))))
            if hasattr(self, "editor_pres"):
                self.editor_pres.sincronizar_unidad(
                    formato_entrada(str(int(precio_venta_n))),
                    self.ganancia_producto.get(),
                )

            producto_id = Agregar_Producto(
                Nombre,
                precio_venta_n,
                desglose["base"],
                cantidad,
                marca,
                categoria,
                ubicacion,
                int(stock_minimo),
                self.proveedor_producto.get().strip(),
                iva_pct,
                self.unidad_base.get().strip() or "Unidad",
                1 if self.var_fraccion.get() else 0,
            )
            presentaciones = self.editor_pres.valores() if hasattr(self, "editor_pres") else []
            if not presentaciones:
                presentaciones = [
                    {
                        "nombre": "Unidad",
                        "factor": 1,
                        "utilidad_pct": utilidad_a_porcentaje(self.ganancia_producto.get()),
                        "precio_venta": precio_venta_n,
                        "permite_venta": True,
                        "activo": True,
                        "es_default": True,
                        "unidad": self.unidad_base.get() or "Unidad",
                    }
                ]
            if producto_id:
                guardar_presentaciones(producto_id, presentaciones, desglose["base"], iva_pct)
            mb.showinfo("Éxito", "El producto se agregó correctamente", parent=self.nuevo)
            self.nuevo.destroy()
        except ValueError as error:
            mb.showerror("Error al agregar el producto: {}".format(error), parent=self.nuevo)

    def _costo_base_actual(self):
        d = desglose_compra(self.precio_compra_producto.get(), self.iva_producto.get(), bool(self.var_con_iva.get()))
        return d["base"] if d else 0

    def cancelar_nuevo(self):
        pregunta = mb.askyesno("Advertencia", "¿Desea cancelar el proceso?", parent=self.nuevo)
        if pregunta:
            self.nuevo.destroy()
