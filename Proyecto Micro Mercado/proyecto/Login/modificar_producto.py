import tkinter as tk
from tkinter import ttk
import mensaje as mb
import Consultas
from zyntra_ui import *


class Modificar:
    def __init__(self, parent=None, codigo_inicial=None):
        self.modificar = tk.Toplevel(parent) if parent else tk.Toplevel()
        prepare_modal(self.modificar, parent, "Modificar Producto", 1400, 860, resizable=True)
        limit_minsize(self.modificar, 780, 420)
        self.items()
        self._cargar_lista()
        if codigo_inicial:
            self.codigo_producto.delete(0, tk.END)
            self.codigo_producto.insert(0, str(codigo_inicial))
            self.Buscar_codigo()

    def items(self):
        body = tk.Frame(self.modificar, bg=BG)
        body.pack(fill="both", expand=True, padx=12, pady=12)
        body.grid_columnconfigure(0, weight=1)
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(0, weight=1)

        lista = card_frame(body, padx=14, pady=12)
        lista.grid(row=0, column=0, rowspan=2, sticky="nsew", padx=(0, 8))
        styled_label(lista, "Buscar o seleccionar", FONT_HEADING, TEXT, BG_CARD).pack(anchor="w")
        styled_label(lista, "Código, nombre, marca o categoría  ·  doble clic carga el producto", FONT_SMALL, TEXT_DIM, BG_CARD).pack(anchor="w", pady=(0, 8))
        self.buscar_lista = styled_entry(lista)
        self.buscar_lista.pack(fill="x")
        self.buscar_lista.bind("<KeyRelease>", self._filtrar_lista)
        self.buscar_lista.bind("<Return>", self._enter_busqueda)

        self.wrap, self.tree = scrollable_tree(
            lista,
            columns=("Codigo", "Nombre", "Precio", "Cantidad", "Marca"),
            headings=("Cód.", "Nombre", "P. venta", "Stock", "Marca"),
            height=10,
            widths={"Codigo": 60, "Nombre": 160, "Precio": 80, "Cantidad": 60, "Marca": 90},
        )
        self.tree.column("Nombre", anchor="w")
        self.wrap.pack(fill="both", expand=True, pady=(8, 0))
        self.tree.bind("<<TreeviewSelect>>", self._seleccionar_lista)
        self.tree.bind("<Double-1>", lambda _e: self._seleccionar_lista())
        self.tree.bind("<Return>", lambda _e: self._seleccionar_lista())

        form_wrap, form = scrollable_body(body, padx=18, pady=12)
        form_wrap.grid(row=0, column=1, sticky="nsew")
        styled_label(form, "Datos del producto", FONT_HEADING, TEXT, BG_CARD).pack(anchor="w", pady=(0, 8))

        row_code = tk.Frame(form, bg=BG_CARD)
        row_code.pack(fill="x", pady=(0, 6))
        box, self.codigo_producto = labeled_field(row_code, "Código")
        box.pack(side="left", fill="x", expand=True, padx=(0, 8))
        primary_button(row_code, "Buscar", self.Buscar_codigo, width=10, font=FONT_SMALL).pack(side="left", pady=(18, 0))
        self.codigo_producto.bind("<Return>", lambda _e: self.Buscar_codigo())

        _, self.nombre_producto = labeled_field(form, "Nombre")
        _.pack(fill="x", pady=(0, 6))

        row = tk.Frame(form, bg=BG_CARD)
        row.pack(fill="x", pady=(0, 6))
        box_c, self.precio_compra_producto = labeled_field(row, "Precio de compra (sin IVA)")
        box_c.pack(side="left", fill="x", expand=True, padx=(0, 6))
        box_iva, self.iva_producto = labeled_field(row, "IVA %")
        box_iva.pack(side="left", fill="x", expand=True, padx=(0, 6))
        box_g = tk.Frame(row, bg=BG_CARD)
        box_g.pack(side="left", fill="x", expand=True)
        styled_label(box_g, "Utilidad %", FONT_LABEL, TEXT_MUTED, BG_CARD).pack(anchor="w")
        self.ganancia_producto = ttk.Combobox(
            box_g, font=("Segoe UI", 11), style="Zyntra.TCombobox", values=Consultas.UTILIDAD_CHOICES, width=8
        )
        self.ganancia_producto.pack(fill="x", pady=(6, 0))
        self.ganancia_producto.set("20%")

        _, self.precio_venta_producto = labeled_field(form, "Precio de venta (con IVA)")
        _.pack(fill="x", pady=(0, 2))
        self.lbl_costo_iva = styled_label(form, "", FONT_SMALL, TEXT_DIM, BG_CARD)
        self.lbl_costo_iva.configure(wraplength=420, justify="left")
        self.lbl_costo_iva.pack(anchor="w", fill="x", pady=(0, 6))

        row2 = tk.Frame(form, bg=BG_CARD)
        row2.pack(fill="x", pady=(0, 6))
        box_q, self.cantidad_producto = labeled_field(row2, "Cantidad")
        box_q.pack(side="left", fill="x", expand=True, padx=(0, 8))
        box_m, self.marca_producto = labeled_field(row2, "Marca")
        box_m.pack(side="left", fill="x", expand=True)

        row_cat = tk.Frame(form, bg=BG_CARD)
        row_cat.pack(fill="x", pady=(0, 6))
        box_cat, self.categoria_producto = labeled_field(row_cat, "Categoría")
        box_cat.pack(side="left", fill="x", expand=True, padx=(0, 8))
        box_p = tk.Frame(row_cat, bg=BG_CARD)
        box_p.pack(side="left", fill="x", expand=True)
        styled_label(box_p, "Proveedor habitual", FONT_LABEL, TEXT_MUTED, BG_CARD).pack(anchor="w")
        self.proveedor_producto = ttk.Combobox(box_p, font=("Segoe UI", 11), style="Zyntra.TCombobox")
        self.proveedor_producto.pack(fill="x", pady=(6, 0))
        try:
            self.proveedor_producto["values"] = Consultas.llenar_combobox() or []
        except Exception:
            self.proveedor_producto["values"] = []

        row3 = tk.Frame(form, bg=BG_CARD)
        row3.pack(fill="x", pady=(0, 6))
        box_u, self.ubicacion_producto = labeled_field(row3, "Ubicación / estante")
        box_u.pack(side="left", fill="x", expand=True, padx=(0, 8))
        box_s, self.stock_minimo = labeled_field(row3, "Stock mínimo")
        box_s.pack(side="left", fill="x", expand=True)

        row_u = tk.Frame(form, bg=BG_CARD)
        row_u.pack(fill="x", pady=(0, 6))
        box_ub = tk.Frame(row_u, bg=BG_CARD)
        box_ub.pack(side="left", fill="x", expand=True, padx=(0, 8))
        styled_label(box_ub, "Unidad base", FONT_LABEL, TEXT_MUTED, BG_CARD).pack(anchor="w")
        self.unidad_base = ttk.Combobox(box_ub, font=("Segoe UI", 11), style="Zyntra.TCombobox", values=Consultas.UNIDADES_BASE)
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
            font=FONT_SMALL,
        ).pack(side="left", pady=(18, 0))

        from presentaciones import EditorPresentaciones
        self.editor_pres = EditorPresentaciones(
            form,
            get_costo_base=lambda: Consultas._a_float_precio(self.precio_compra_producto.get()) or 0,
            get_iva=lambda: self.iva_producto.get(),
            get_unidad=lambda: self.unidad_base.get() or "Unidad",
        )
        self.editor_pres.pack(fill="x", expand=False, pady=(4, 0))
        self.editor_pres.cargar()

        def _on_margen(utilidad_txt, venta_txt, manual_venta):
            if manual_venta:
                self.editor_pres.sincronizar_unidad(venta_txt, utilidad_txt)

        Consultas.conectar_margen_venta(
            self.precio_compra_producto,
            self.ganancia_producto,
            self.precio_venta_producto,
            self.iva_producto,
            self.lbl_costo_iva,
            on_margen=_on_margen,
        )

        def _ajustar_textos(event):
            self.lbl_costo_iva.configure(wraplength=max(event.width - 24, 240))

        form.bind("<Configure>", _ajustar_textos)

        actions = card_frame(body, padx=16, pady=10)
        actions.grid(row=1, column=1, sticky="ew", pady=(8, 0))
        primary_button(actions, "Guardar cambios", self.guardar_cambios, width=18).pack(side="left", fill="x", expand=True, padx=(0, 8))
        danger_button(actions, "Cancelar", self.cancelar_cambios, width=14).pack(side="left", fill="x", expand=True)

        if not self.codigo_producto.get():
            self.buscar_lista.focus_set()

    def _cargar_lista(self, filas=None):
        self.tree.delete(*self.tree.get_children())
        for row in filas if filas is not None else (Consultas.mostrar_Productos() or []):
            datos = Consultas.parse_producto(row)
            if not datos:
                continue
            self.tree.insert("", "end", values=(datos["id"], datos["nombre"], formato_dinero(datos["precio_venta"]), datos["cantidad"], datos["marca"]))

    def _filtrar_lista(self, event=None):
        texto = self.buscar_lista.get().strip()
        if not texto:
            self._cargar_lista()
            return
        resultados = Consultas.buscar_productos(texto, texto, texto)
        self._cargar_lista(resultados or [])

    def _enter_busqueda(self, event=None):
        texto = self.buscar_lista.get().strip()
        if texto.isdigit():
            self.codigo_producto.delete(0, tk.END)
            self.codigo_producto.insert(0, texto)
            self.Buscar_codigo()
            return "break"
        hijos = self.tree.get_children()
        if hijos:
            self.tree.selection_set(hijos[0])
            self.tree.focus(hijos[0])
            self._seleccionar_lista()
        return "break"

    def _seleccionar_lista(self, event=None):
        sel = self.tree.selection()
        if not sel:
            return
        codigo = self.tree.item(sel[0], "values")[0]
        self.codigo_producto.delete(0, tk.END)
        self.codigo_producto.insert(0, codigo)
        self._llenar_formulario(codigo)

    def _llenar_formulario(self, codigo):
        producto = Consultas.buscar_codigo(codigo)
        datos = Consultas.parse_producto(producto)
        if not datos:
            mb.showinfo("No encontrado", "No se encontró el producto con ese código", parent=self.modificar)
            return False
        pares = (
            (self.nombre_producto, datos["nombre"]),
            (self.precio_compra_producto, formato_entrada(str(int(round(float(datos["precio_compra"] or 0)))))),
            (self.precio_venta_producto, formato_entrada(str(int(round(float(datos["precio_venta"] or 0)))))),
            (self.cantidad_producto, datos["cantidad"]),
            (self.marca_producto, datos["marca"]),
            (self.categoria_producto, datos["categoria"]),
            (self.ubicacion_producto, datos["ubicacion"]),
            (self.stock_minimo, datos["stock_minimo"]),
        )
        for entry, valor in pares:
            entry.delete(0, "end")
            entry.insert(0, "" if valor is None else valor)
        self.proveedor_producto.set(datos.get("proveedor") or "")
        Consultas.escribir_iva(self.iva_producto, datos.get("iva"))
        self.unidad_base.set(datos.get("unidad_base") or "Unidad")
        self.var_fraccion.set(bool(datos.get("permite_fraccion", True)))
        self.ganancia_producto.set(
            Consultas.utilidad_a_texto(
                Consultas.margen_desde_precios(
                    datos.get("precio_compra"),
                    datos.get("precio_venta"),
                    datos.get("iva"),
                )
            )
        )
        if hasattr(self, "editor_pres"):
            self.editor_pres.cargar(Consultas.listar_presentaciones(datos["id"], solo_activas=False))
            self.editor_pres.sincronizar_unidad(
                self.precio_venta_producto.get(),
                self.ganancia_producto.get(),
            )
        return True

    def guardar_cambios(self):
        try:
            Codigo = self.codigo_producto.get().strip()
            Nombre = self.nombre_producto.get().strip()
            precio_compra = parse_dinero(self.precio_compra_producto.get())
            precio_venta = redondear_centena(parse_dinero(self.precio_venta_producto.get()))
            Cantidad = float(self.cantidad_producto.get())
            Marca = self.marca_producto.get().strip()
            categoria = self.categoria_producto.get().strip()
            ubicacion = self.ubicacion_producto.get().strip()
            stock_minimo = int(float(self.stock_minimo.get() or 10))

            if not all([Nombre, Marca, Codigo]):
                mb.showwarning("Advertencia", "Todos los campos son obligatorios", parent=self.modificar)
                return
            if precio_venta <= 0:
                mb.showerror("Error", "El precio de venta debe ser mayor a 0.", parent=self.modificar)
                return
            self.precio_venta_producto.delete(0, tk.END)
            self.precio_venta_producto.insert(0, formato_entrada(str(int(precio_venta))))
            if hasattr(self, "editor_pres"):
                self.editor_pres.sincronizar_unidad(
                    formato_entrada(str(int(precio_venta))),
                    self.ganancia_producto.get(),
                )

            producto_modi = Consultas.modificar_producto(
                Nombre, precio_venta, precio_compra, Cantidad, Marca, Codigo, categoria, ubicacion, stock_minimo,
                self.proveedor_producto.get().strip(),
                Consultas.iva_a_porcentaje(self.iva_producto.get()),
                self.unidad_base.get().strip() or "Unidad",
                1 if self.var_fraccion.get() else 0,
            )
            if producto_modi:
                Consultas.guardar_presentaciones(
                    Codigo,
                    self.editor_pres.valores() if hasattr(self, "editor_pres") else [],
                    precio_compra,
                    Consultas.iva_a_porcentaje(self.iva_producto.get()),
                )
                mb.showinfo("Éxito", "Producto modificado correctamente", parent=self.modificar)
                self.modificar.destroy()
            else:
                mb.showerror("Error", "No se pudo guardar. Verifique el código.", parent=self.modificar)
        except ValueError as error:
            mb.showerror("Error", "Revise precios, cantidad y stock mínimo. {}".format(error), parent=self.modificar)

    def cancelar_cambios(self):
        self.modificar.destroy()

    def Buscar_codigo(self, event=None):
        Codigo = self.codigo_producto.get().strip()
        if not Codigo:
            mb.showerror("Error", "Ingrese un código o seleccione un producto de la lista", parent=self.modificar)
            return
        if self._llenar_formulario(Codigo):
            for item in self.tree.get_children():
                if str(self.tree.item(item, "values")[0]) == str(Codigo):
                    self.tree.selection_set(item)
                    self.tree.see(item)
                    break
            self.nombre_producto.focus_set()
