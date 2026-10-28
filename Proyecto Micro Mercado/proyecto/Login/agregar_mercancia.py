import tkinter as tk
from tkinter import ttk
import mensaje as mb
from zyntra_ui import *
from datetime import datetime
from tkcalendar import DateEntry


class Mercancia:
    def __init__(self, parent=None, usuario=None):
        self.total_a_pagar = 0
        self.subtotal_compra = 0
        self.iva_compra = 0
        self._monto_auto = True
        self.usuario = usuario
        self.mercancia = tk.Toplevel(parent) if parent else tk.Toplevel()
        prepare_modal(self.mercancia, parent, "Ingreso de producto", 1080, 860, resizable=True)
        self.items()

    def items(self):
        import Consultas

        win = self.mercancia
        limit_minsize(win, 780, 520)
        win.grid_columnconfigure(0, weight=1)
        win.grid_rowconfigure(2, weight=2)
        win.grid_rowconfigure(3, weight=3)
        win.grid_rowconfigure(4, weight=0, minsize=64)

        header = tk.Frame(win, bg=BG_HEADER, padx=18, pady=12)
        header.grid(row=0, column=0, sticky="ew")
        mark = tk.Label(
            header, text=" Z ", bg=PURPLE_DARK, fg=TEXT, font=("Segoe UI", 16, "bold"), padx=8, pady=2
        )
        mark.pack(side="left")
        titles = tk.Frame(header, bg=BG_HEADER)
        titles.pack(side="left", padx=(10, 0))
        styled_label(titles, APP_NAME, FONT_LOGO, TEXT, BG_HEADER).pack(anchor="w")
        styled_label(titles, "Ingreso de producto · facturas de compra", FONT_SMALL, TEXT_MUTED, BG_HEADER).pack(anchor="w")

        form = card_frame(win, padx=16, pady=12)
        form.grid(row=1, column=0, sticky="ew", padx=12, pady=(12, 8))
        form.grid_columnconfigure(0, weight=2)
        form.grid_columnconfigure(1, weight=1)
        form.grid_columnconfigure(2, weight=2)

        styled_label(form, "Proveedor", FONT_LABEL, TEXT_MUTED, BG_CARD).grid(row=0, column=0, sticky="w")
        styled_label(form, "N° factura", FONT_LABEL, TEXT_MUTED, BG_CARD).grid(
            row=0, column=1, sticky="w", padx=(10, 0)
        )
        styled_label(form, "Buscar producto", FONT_LABEL, TEXT_MUTED, BG_CARD).grid(
            row=0, column=2, sticky="w", padx=(10, 0)
        )
        self.añadir_proveedor = ttk.Combobox(form, font=("Segoe UI", 12), style="Zyntra.TCombobox")
        self.añadir_proveedor.grid(row=1, column=0, sticky="ew", padx=(0, 10), pady=(4, 0))
        self.llenar_combo()
        self.numero_factura = styled_entry(form)
        self.numero_factura.grid(row=1, column=1, sticky="ew", padx=(10, 10), pady=(4, 0))
        buscar_row = tk.Frame(form, bg=BG_CARD)
        buscar_row.grid(row=1, column=2, sticky="ew", pady=(4, 0))
        buscar_row.grid_columnconfigure(0, weight=1)
        self.buscar_producto = styled_entry(buscar_row)
        self.buscar_producto.grid(row=0, column=0, sticky="ew")
        self.buscar_producto.bind("<KeyRelease>", self.buscar)
        secondary_button(buscar_row, "Crear un producto", self._abrir_nuevo_producto, width=16, font=FONT_SMALL).grid(
            row=0, column=1, padx=(8, 0)
        )

        styled_label(form, "Producto", FONT_LABEL, TEXT_MUTED, BG_CARD).grid(
            row=2, column=0, sticky="w", pady=(10, 0)
        )
        styled_label(form, "Cantidad", FONT_LABEL, TEXT_MUTED, BG_CARD).grid(
            row=2, column=1, sticky="w", pady=(10, 0), padx=(10, 0)
        )
        styled_label(form, "IVA % (del producto)", FONT_LABEL, TEXT_MUTED, BG_CARD).grid(
            row=2, column=2, sticky="w", pady=(10, 0), padx=(10, 0)
        )
        self.mostrar_producto = styled_entry(form)
        self.mostrar_producto.grid(row=3, column=0, sticky="ew", padx=(0, 10), pady=(4, 0))
        qty_row = tk.Frame(form, bg=BG_CARD)
        qty_row.grid(row=3, column=1, sticky="ew", padx=(10, 10), pady=(4, 0))
        qty_row.grid_columnconfigure(0, weight=1)
        self.añadir_producto = styled_entry(qty_row, width=10)
        self.añadir_producto.grid(row=0, column=0, sticky="ew")
        self.añadir_producto.insert(0, "1")
        self.btn_agregar = plus_button(qty_row, self.agregar_funcion)
        self.btn_agregar.grid(row=0, column=1, padx=(8, 0))
        self.iva_linea = styled_entry(form)
        self.iva_linea.grid(row=3, column=2, sticky="ew", pady=(4, 0))

        precio_lab = tk.Frame(form, bg=BG_CARD)
        precio_lab.grid(row=4, column=0, sticky="w", pady=(10, 0))
        styled_label(precio_lab, "P. compra", FONT_LABEL, TEXT_MUTED, BG_CARD).pack(side="left")
        self.var_iva_incluido = tk.BooleanVar(value=False)
        radio_opts = dict(
            bg=BG_CARD,
            fg=TEXT,
            selectcolor=BG_INPUT,
            activebackground=BG_CARD,
            activeforeground=TEXT,
            font=FONT_SMALL,
        )
        tk.Radiobutton(
            precio_lab, text="Sin IVA", variable=self.var_iva_incluido, value=False, **radio_opts
        ).pack(side="left", padx=(12, 0))
        tk.Radiobutton(
            precio_lab, text="IVA incluido", variable=self.var_iva_incluido, value=True, **radio_opts
        ).pack(side="left", padx=(8, 0))
        styled_label(form, "Utilidad %", FONT_LABEL, TEXT_MUTED, BG_CARD).grid(
            row=4, column=1, sticky="w", pady=(10, 0), padx=(10, 0)
        )
        styled_label(form, "P. venta (con IVA)", FONT_LABEL, TEXT_MUTED, BG_CARD).grid(
            row=4, column=2, sticky="w", pady=(10, 0), padx=(10, 0)
        )
        self.precio_compra_linea = styled_entry(form)
        self.precio_compra_linea.grid(row=5, column=0, sticky="ew", padx=(0, 10), pady=(4, 0))
        self.ganancia_linea = ttk.Combobox(
            form, font=("Segoe UI", 11), style="Zyntra.TCombobox", values=Consultas.UTILIDAD_CHOICES
        )
        self.ganancia_linea.grid(row=5, column=1, sticky="ew", padx=(10, 10), pady=(4, 0))
        self.ganancia_linea.set("20%")
        self.precio_venta_linea = styled_entry(form)
        self.precio_venta_linea.grid(row=5, column=2, sticky="ew", pady=(4, 0))
        self.lbl_costo_iva = styled_label(form, "", FONT_SMALL, TEXT_DIM, BG_CARD)
        self.lbl_costo_iva.configure(wraplength=900, justify="left")
        self.lbl_costo_iva.grid(row=6, column=0, columnspan=3, sticky="w", pady=(4, 0))
        Consultas.conectar_margen_venta(
            self.precio_compra_linea,
            self.ganancia_linea,
            self.precio_venta_linea,
            self.iva_linea,
            self.lbl_costo_iva,
            self.var_iva_incluido,
        )

        lote = tk.Frame(form, bg=BG_CARD)
        lote.grid(row=7, column=0, columnspan=3, sticky="w", pady=(8, 0))
        self.var_vence = tk.BooleanVar(value=True)
        tk.Checkbutton(
            lote,
            text="Registrar lote",
            variable=self.var_vence,
            bg=BG_CARD,
            fg=TEXT,
            selectcolor=BG_INPUT,
            activebackground=BG_CARD,
            activeforeground=TEXT,
            font=FONT_LABEL,
        ).pack(side="left")
        styled_label(lote, "Vence", FONT_LABEL, TEXT_MUTED, BG_CARD).pack(side="left", padx=(16, 8))
        self.fecha_vence = DateEntry(
            lote,
            width=14,
            background=ACCENT,
            foreground="white",
            borderwidth=2,
            year=datetime.now().year,
            font=("Segoe UI", 10, "bold"),
            locale="es_ES",
        )
        self.fecha_vence.pack(side="left")
        styled_label(lote, "Presentación", FONT_LABEL, TEXT_MUTED, BG_CARD).pack(side="left", padx=(16, 8))
        self.presentacion_linea = ttk.Combobox(lote, font=("Segoe UI", 10), style="Zyntra.TCombobox", width=16, state="readonly")
        self.presentacion_linea.pack(side="left")
        self._pres_opciones = []

        catalog = card_frame(win, padx=12, pady=10)
        catalog.grid(row=2, column=0, sticky="nsew", padx=12, pady=(0, 8))
        styled_label(catalog, "Inventario", FONT_SUB, TEXT, BG_CARD).pack(anchor="w")
        wrap_cat, self.tree_productos = scrollable_tree(
            catalog,
            columns=("Codigo", "Nombre", "Precio_de_venta", "Precio_de_Compra", "Cantidad", "Iva"),
            headings=("Código", "Nombre", "P. venta", "P. compra", "Cantidad", "IVA"),
            height=5,
            widths={
                "Codigo": 70,
                "Nombre": 220,
                "Precio_de_venta": 90,
                "Precio_de_Compra": 90,
                "Cantidad": 70,
                "Iva": 90,
            },
        )
        self.tree_productos.column("Nombre", anchor="w")
        wrap_cat.pack(fill="both", expand=True, pady=(8, 0))

        for row in Consultas.mostrar_Productos() or []:
            valores = self._valores_catalogo(row)
            if valores:
                self.tree_productos.insert("", "end", values=valores)
        if self.tree_productos.get_children():
            first_item = self.tree_productos.get_children()[0]
            self.tree_productos.selection_set(first_item)
            self.obtener_datos_seleccionados()

        bottom = tk.Frame(win, bg=BG)
        bottom.grid(row=3, column=0, sticky="nsew", padx=12, pady=(0, 8))
        bottom.grid_columnconfigure(0, weight=3)
        bottom.grid_columnconfigure(1, weight=1)
        bottom.grid_rowconfigure(0, weight=1)

        cart = card_frame(bottom, padx=12, pady=10)
        cart.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        styled_label(cart, "Mercancía a ingresar", FONT_SUB, TEXT, BG_CARD).pack(anchor="w")
        wrap_cart, self.tree_productos_agregado = scrollable_tree(
            cart,
            columns=(
                "Nombre",
                "Presentacion",
                "Precio_de_Compra",
                "Tipo",
                "Agregar_Cantidad",
                "Iva",
                "Ganancia",
                "Precio_Venta",
                "Total_Linea",
                "Vence",
                "Factor",
                "PresId",
            ),
            headings=("Nombre", "Present.", "P. compra", "Tipo", "Cant.", "IVA", "Util. %", "P. venta", "Total", "Vence", "F", "Pid"),
            height=5,
            widths={
                "Nombre": 120,
                "Presentacion": 70,
                "Precio_de_Compra": 75,
                "Tipo": 70,
                "Agregar_Cantidad": 48,
                "Iva": 48,
                "Ganancia": 55,
                "Precio_Venta": 70,
                "Total_Linea": 70,
                "Vence": 80,
                "Factor": 1,
                "PresId": 1,
            },
        )
        self.tree_productos_agregado.column("Nombre", anchor="w")
        self.tree_productos_agregado["displaycolumns"] = (
            "Nombre",
            "Presentacion",
            "Precio_de_Compra",
            "Tipo",
            "Agregar_Cantidad",
            "Iva",
            "Ganancia",
            "Precio_Venta",
            "Total_Linea",
            "Vence",
        )
        wrap_cart.pack(fill="both", expand=True, pady=(8, 0))

        summary = card_frame(bottom, padx=14, pady=12)
        summary.grid(row=0, column=1, sticky="nsew")
        styled_label(summary, "Resumen", FONT_SUB, TEXT, BG_CARD).pack(anchor="w")
        styled_label(summary, "Método de pago", FONT_LABEL, TEXT_MUTED, BG_CARD).pack(anchor="w", pady=(8, 0))
        self.metodo_pago = ttk.Combobox(
            summary,
            font=("Segoe UI", 11),
            style="Zyntra.TCombobox",
            values=Consultas.METODOS_PAGO_COMPRA,
            state="readonly",
        )
        self.metodo_pago.pack(fill="x", pady=(4, 0))
        self.metodo_pago.set("Efectivo")
        self.metodo_pago.bind("<<ComboboxSelected>>", self._on_metodo_pago)
        styled_label(summary, "Monto pagado", FONT_LABEL, TEXT_MUTED, BG_CARD).pack(anchor="w", pady=(10, 0))
        self.ingresar_dinero = styled_entry(summary, width=16)
        self.ingresar_dinero.pack(fill="x", pady=(4, 0))
        bind_money_entry(self.ingresar_dinero, on_change=self._on_monto_manual)
        self._fila_resumen(summary, "Subtotal", "lbl_subtotal")
        self._fila_resumen(summary, "IVA", "lbl_iva")
        self._fila_resumen(summary, "Total de la compra", "lbl_total_resumen")
        self._fila_resumen(summary, "Monto pagado", "lbl_pagado")
        self._fila_resumen(summary, "Saldo pendiente", "lbl_saldo")
        self.lbl_metodo_resumen = styled_label(summary, "Método: Efectivo", FONT_SMALL, TEXT_DIM, BG_CARD)
        self.lbl_metodo_resumen.pack(anchor="w", pady=(8, 0))

        actions = card_frame(win, padx=12, pady=10)
        actions.grid(row=4, column=0, sticky="ew", padx=12, pady=(0, 12))
        self.quitar_producto_seleccionado = secondary_button(
            actions, "Quitar producto", self.quitar_producto, width=16
        )
        self.quitar_producto_seleccionado.pack(side="left")
        self.cancelar_compra = danger_button(actions, "Cancelar compra", self.cancelar, width=16)
        self.cancelar_compra.pack(side="left", padx=10)
        self.finalizar_compra = primary_button(actions, "Finalizar compra", self.comprar, width=16)
        self.finalizar_compra.pack(side="right")
        total_box = tk.Frame(actions, bg=BG_CARD)
        total_box.pack(side="right", padx=(0, 16))
        styled_label(total_box, "Total a pagar", FONT_LABEL, TEXT_MUTED, BG_CARD).pack(anchor="e")
        self.total = money_label(total_box, "$ 0", ("Segoe UI", 22, "bold"), CYAN, BG_CARD)
        self.total.pack(anchor="e")

        self.tree_productos.bind("<<TreeviewSelect>>", self.obtener_datos_seleccionados)
        self.tree_productos.bind("<Double-1>", lambda _e: self.agregar_funcion())
        self.añadir_producto.bind("<Return>", lambda _e: self.agregar_funcion())
        self.buscar_producto.focus_set()
        self._recalcular_totales()

    def _fila_resumen(self, parent, titulo, attr):
        styled_label(parent, titulo, FONT_LABEL, TEXT_MUTED, BG_CARD).pack(anchor="w", pady=(8, 0))
        lbl = styled_label(parent, "$ 0", FONT_BODY, TEXT, BG_CARD)
        lbl.pack(anchor="w", pady=(2, 0))
        setattr(self, attr, lbl)

    def _valores_catalogo(self, row):
        import Consultas

        datos = Consultas.parse_producto(row)
        if not datos:
            return None
        return (
            datos["id"],
            datos["nombre"],
            formato_dinero(datos["precio_venta"]),
            formato_dinero(datos["precio_compra"]),
            datos["cantidad"],
            Consultas.iva_a_texto(datos.get("iva")),
        )

    def _desglose_linea(self, precio=None, iva=None, incluido=None):
        import Consultas

        return Consultas.desglose_compra(
            self.precio_compra_linea.get() if precio is None else precio,
            self.iva_linea.get() if iva is None else iva,
            self.var_iva_incluido.get() if incluido is None else incluido,
        )

    def _datos_linea_cart(self, valores):
        import Consultas

        incluido = str(valores[3] if len(valores) > 3 else "") == "IVA incl."
        desglose = self._desglose_linea(
            valores[2] if len(valores) > 2 else 0,
            valores[5] if len(valores) > 5 else 0,
            incluido,
        )
        try:
            cantidad = float(valores[4] or 0)
            precio_venta = parse_dinero(valores[7] or 0) if len(valores) > 7 else 0
            factor = float(valores[10] or 1) if len(valores) > 10 else 1
        except (TypeError, ValueError):
            cantidad = 0
            precio_venta = 0
            factor = 1
        vence = valores[9] if len(valores) > 9 else ""
        return {
            "nombre": valores[0],
            "presentacion": valores[1] if len(valores) > 1 else "Unidad",
            "precio_ingresado": parse_dinero(valores[2] if len(valores) > 2 else 0),
            "iva_incluido": incluido,
            "cantidad": cantidad,
            "iva_txt": valores[5] if len(valores) > 5 else "0",
            "ganancia": valores[6] if len(valores) > 6 else "",
            "precio_venta": precio_venta,
            "vence": vence,
            "factor": factor or 1,
            "presentacion_id": valores[11] if len(valores) > 11 else None,
            "desglose": desglose,
        }

    def _monto_pagado(self):
        import Consultas

        n = Consultas._a_float_precio(self.ingresar_dinero.get())
        return 0.0 if n is None else n

    def _on_monto_manual(self, _event=None):
        self._monto_auto = False
        self._actualizar_saldo()

    def _on_metodo_pago(self, _event=None):
        metodo = (self.metodo_pago.get() or "Efectivo").strip()
        self._monto_auto = True
        if metodo.lower() == "crédito" or metodo.lower() == "credito":
            self.ingresar_dinero.delete(0, tk.END)
            self.ingresar_dinero.insert(0, "0")
        else:
            self.ingresar_dinero.delete(0, tk.END)
            self.ingresar_dinero.insert(0, formato_entrada(str(int(round(self.total_a_pagar or 0)))))
        self._actualizar_saldo()

    def _actualizar_saldo(self):
        pagado = max(0.0, self._monto_pagado())
        saldo = max(0.0, round((self.total_a_pagar or 0) - pagado, 2))
        self.lbl_subtotal.config(text=formato_dinero(self.subtotal_compra))
        self.lbl_iva.config(text=formato_dinero(self.iva_compra))
        self.lbl_total_resumen.config(text=formato_dinero(self.total_a_pagar))
        self.lbl_pagado.config(text=formato_dinero(pagado))
        color_saldo = WARNING if saldo > 0.009 else TEXT
        try:
            self.lbl_saldo.config(text=formato_dinero(saldo), fg=color_saldo)
        except tk.TclError:
            self.lbl_saldo.config(text=formato_dinero(saldo))
        self.lbl_metodo_resumen.config(text="Método: {}".format(self.metodo_pago.get() or "Efectivo"))
        return pagado, saldo

    def _recalcular_totales(self):
        base = 0.0
        iva = 0.0
        total = 0.0
        for item in self.tree_productos_agregado.get_children():
            linea = self._datos_linea_cart(self.tree_productos_agregado.item(item, "values"))
            d = linea.get("desglose")
            if not d:
                continue
            cantidad = linea["cantidad"]
            base += d["base"] * cantidad
            iva += d["iva"] * cantidad
            total += d["total"] * cantidad
        self.subtotal_compra = round(base, 2)
        self.iva_compra = round(iva, 2)
        self.total_a_pagar = round(total, 2)
        self.total.config(text=formato_dinero(self.total_a_pagar))
        if self._monto_auto:
            metodo = (self.metodo_pago.get() or "").strip().lower()
            self.ingresar_dinero.delete(0, tk.END)
            if metodo in ("crédito", "credito"):
                self.ingresar_dinero.insert(0, "0")
            else:
                self.ingresar_dinero.insert(0, formato_entrada(str(int(round(self.total_a_pagar)))))
        self._actualizar_saldo()

    def agregar_funcion(self):
        import Consultas

        try:
            nombre = self.mostrar_producto.get().strip()
            cantidad_txt = self.añadir_producto.get().strip().replace(",", ".")

            if not nombre:
                mb.showerror("Error", "Seleccione un producto.", parent=self.mercancia)
                return
            try:
                cantidad_a_agre = float(cantidad_txt)
            except (TypeError, ValueError):
                mb.showerror("Error", "Ingrese una cantidad válida mayor a 0.", parent=self.mercancia)
                return
            if cantidad_a_agre <= 0:
                mb.showerror("Error", "La cantidad debe ser mayor a 0.", parent=self.mercancia)
                return
            if abs(cantidad_a_agre - int(cantidad_a_agre)) < 0.0001:
                cantidad_a_agre = int(cantidad_a_agre)

            iva_txt = (self.iva_linea.get() or "").strip()
            iva_pct = Consultas.iva_a_porcentaje(iva_txt)
            if iva_txt and Consultas._a_float_precio(iva_txt.replace("%", "")) is None:
                mb.showerror("Error", "Ingrese un IVA numérico válido (por ejemplo 0, 5 o 19).", parent=self.mercancia)
                return
            if iva_pct < 0 or iva_pct > 100:
                mb.showerror("Error", "El IVA debe estar entre 0 y 100.", parent=self.mercancia)
                return
            iva_txt = Consultas.iva_a_texto(iva_pct)

            desglose = self._desglose_linea()
            if not desglose or desglose["base"] <= 0:
                mb.showerror("Error", "Ingrese un precio de compra válido mayor a 0.", parent=self.mercancia)
                return

            vence = self.fecha_vence.get_date().strftime("%Y-%m-%d") if self.var_vence.get() else ""
            iva_incluido = bool(self.var_iva_incluido.get())
            tipo = "IVA incl." if iva_incluido else "Sin IVA"
            precio_ingresado = desglose["total"] if iva_incluido else desglose["base"]
            ganancia_txt = self.ganancia_linea.get() or Consultas.utilidad_a_texto(
                Consultas.margen_desde_precios(desglose["base"], self.precio_venta_linea.get(), iva_txt)
            )
            try:
                precio_venta = redondear_centena(parse_dinero(self.precio_venta_linea.get()))
            except ValueError:
                precio_venta = Consultas.precio_venta_con_margen(desglose["base"], ganancia_txt, iva_txt) or 0
            if precio_venta <= 0:
                precio_venta = Consultas.precio_venta_con_margen(desglose["base"], ganancia_txt, iva_txt) or 0
            precio_venta = redondear_centena(precio_venta)

            pres = self._presentacion_compra()
            factor = float(pres.get("factor") or 1) or 1
            pres_nombre = pres.get("nombre") or "Unidad"
            pres_id = pres.get("id") or ""

            total_linea = round(desglose["total"] * cantidad_a_agre, 2)
            encontrado = False
            for item_agregado in self.tree_productos_agregado.get_children():
                linea = self._datos_linea_cart(self.tree_productos_agregado.item(item_agregado, "values"))
                misma_iva = Consultas.iva_a_porcentaje(linea["iva_txt"]) == iva_pct
                mismo_tipo = linea["iva_incluido"] == iva_incluido
                misma_pres = str(linea.get("presentacion") or "") == str(pres_nombre)
                try:
                    mismo_precio = abs(float(linea["precio_ingresado"] or 0) - float(precio_ingresado)) < 0.009
                except (TypeError, ValueError):
                    mismo_precio = False
                if linea["nombre"] == nombre and misma_iva and mismo_tipo and mismo_precio and misma_pres:
                    nueva_cantidad = linea["cantidad"] + cantidad_a_agre
                    if abs(nueva_cantidad - int(nueva_cantidad)) < 0.0001:
                        nueva_cantidad = int(nueva_cantidad)
                    vence_linea = vence or linea["vence"]
                    self.tree_productos_agregado.item(
                        item_agregado,
                        values=(
                            nombre,
                            pres_nombre,
                            formato_dinero(precio_ingresado),
                            tipo,
                            nueva_cantidad,
                            iva_txt,
                            ganancia_txt,
                            formato_dinero(int(precio_venta)),
                            formato_dinero(round(desglose["total"] * nueva_cantidad, 2)),
                            vence_linea,
                            factor,
                            pres_id,
                        ),
                    )
                    encontrado = True
                    break

            if not encontrado:
                self.tree_productos_agregado.insert(
                    "",
                    "end",
                    values=(
                        nombre,
                        pres_nombre,
                        formato_dinero(precio_ingresado),
                        tipo,
                        cantidad_a_agre,
                        iva_txt,
                        ganancia_txt,
                        formato_dinero(int(precio_venta)),
                        formato_dinero(total_linea),
                        vence,
                        factor,
                        pres_id,
                    ),
                )

            self._recalcular_totales()
            self.añadir_producto.delete(0, tk.END)
            self.añadir_producto.insert(0, "1")
        except ValueError as error:
            mb.showerror("Error al agregar {}".format(error), parent=self.mercancia)

    def quitar_producto(self):
        try:
            producto_seleccionado = self.tree_productos_agregado.selection()
            if not producto_seleccionado:
                mb.showwarning("Advertencia", "Debe seleccionar un producto", parent=self.mercancia)
                return

            for item in producto_seleccionado:
                self.tree_productos_agregado.delete(item)
            self._recalcular_totales()
        except ValueError as error:
            mb.showerror("Error", "Erro al quitar el producto seleccionado", parent=self.mercancia)

    def _limpiar_formulario(self, recargar_catalogo=True):
        import Consultas

        self.tree_productos_agregado.delete(*self.tree_productos_agregado.get_children())
        self.total_a_pagar = 0
        self._monto_auto = True
        if recargar_catalogo:
            self._recargar_catalogo()
        self.añadir_proveedor.set("")
        self.numero_factura.delete(0, tk.END)
        self.añadir_producto.delete(0, tk.END)
        self.añadir_producto.insert(0, "1")
        self.mostrar_producto.delete(0, tk.END)
        self.buscar_producto.delete(0, tk.END)
        self.ingresar_dinero.delete(0, tk.END)
        self.metodo_pago.set("Efectivo")
        self.var_iva_incluido.set(False)
        Consultas.escribir_iva(self.iva_linea, "")
        self.ganancia_linea.set("20%")
        self.precio_compra_linea.delete(0, tk.END)
        self.precio_venta_linea.delete(0, tk.END)
        self._recalcular_totales()
        self.buscar_producto.focus()

    def cancelar(self):
        confirmacion = mb.askyesno("Confirmar", "Desea cancelar?", parent=self.mercancia)
        if not confirmacion:
            return
        self._limpiar_formulario()
        mb.showinfo("Compra Cancelada", "La compra ha sido cancelada.", parent=self.mercancia)

    def comprar(self):
        import Consultas

        if not self.tree_productos_agregado.get_children():
            mb.showinfo("Sin artículos", "No hay artículos para comprar.", parent=self.mercancia)
            return

        ok_fac, factura_o_error = Consultas.validar_numero_factura(self.numero_factura.get())
        if not ok_fac:
            mb.showerror("Factura", factura_o_error, parent=self.mercancia)
            self.numero_factura.focus_set()
            return
        factura = factura_o_error

        pagado, saldo = self._actualizar_saldo()
        if pagado < 0:
            mb.showerror("Pago", "El monto pagado no puede ser negativo.", parent=self.mercancia)
            return
        if pagado - self.total_a_pagar > 0.009:
            mb.showerror(
                "Pago",
                "El monto pagado no puede ser mayor al total de la compra.",
                parent=self.mercancia,
            )
            return

        metodo = (self.metodo_pago.get() or "Efectivo").strip()
        proveedor = self.añadir_proveedor.get().strip()
        lineas = []
        for item in self.tree_productos_agregado.get_children():
            linea = self._datos_linea_cart(self.tree_productos_agregado.item(item, "values"))
            d = linea.get("desglose")
            if not d or linea["cantidad"] <= 0 or d["base"] <= 0:
                mb.showerror("Error", "Hay una línea con cantidad o precio inválido.", parent=self.mercancia)
                return
            producto_info = Consultas.obtener_producto_por_nombre(linea["nombre"])
            datos = Consultas.parse_producto(producto_info) if producto_info else None
            if not datos:
                mb.showerror("Error", f"No se encontró el producto: {linea['nombre']}", parent=self.mercancia)
                return
            try:
                precio_ingresado = float(linea["precio_ingresado"] or 0)
            except (TypeError, ValueError):
                precio_ingresado = d["total"] if linea["iva_incluido"] else d["base"]
            factor = float(linea.get("factor") or 1) or 1
            cantidad_base = Consultas.a_unidades_base(linea["cantidad"], factor)
            costo_base_unidad = round(d["base"] / factor, 4) if factor else d["base"]
            lineas.append(
                {
                    "nombre": linea["nombre"],
                    "cantidad": linea["cantidad"],
                    "cantidad_base": cantidad_base,
                    "factor": factor,
                    "presentacion_id": linea.get("presentacion_id"),
                    "presentacion_nombre": linea.get("presentacion") or "Unidad",
                    "iva_txt": linea["iva_txt"],
                    "vence": linea["vence"],
                    "iva_incluido": linea["iva_incluido"],
                    "precio_ingresado": precio_ingresado,
                    "precio_base": d["base"],
                    "costo_base_unidad": costo_base_unidad,
                    "iva_valor": d["iva"],
                    "total_linea": round(d["total"] * linea["cantidad"], 2),
                    "precio_venta": linea["precio_venta"],
                    "producto_id": datos["id"],
                    "cantidad_actual": datos["cantidad"],
                }
            )

        estado = "PENDIENTE" if saldo > 0.009 else "PAGADA"
        ok_doc, msg_doc, _compra_id = Consultas.registrar_compra_mercancia(
            {
                "numero_factura": factura,
                "proveedor": proveedor,
                "usuario": self.usuario or "",
                "metodo_pago": metodo,
                "monto_pagado": pagado,
                "saldo_pendiente": saldo,
                "subtotal": self.subtotal_compra,
                "iva": self.iva_compra,
                "total": self.total_a_pagar,
                "estado": estado,
            },
            [
                {
                    "producto_id": ln["producto_id"],
                    "nombre": ln["nombre"],
                    "cantidad": ln["cantidad"],
                    "iva_pct": ln["iva_txt"],
                    "iva_incluido": ln["iva_incluido"],
                    "precio_ingresado": ln["precio_ingresado"],
                    "precio_base": ln["precio_base"],
                    "iva_valor": ln["iva_valor"],
                    "total_linea": ln["total_linea"],
                    "precio_venta": ln["precio_venta"],
                    "fecha_vence": ln["vence"],
                    "presentacion_id": ln.get("presentacion_id"),
                    "presentacion_nombre": ln.get("presentacion_nombre"),
                    "factor": ln.get("factor") or 1,
                    "cantidad_base": ln.get("cantidad_base"),
                }
                for ln in lineas
            ],
            cajero=self.usuario or "",
        )
        if not ok_doc:
            mb.showerror("Compra", msg_doc, parent=self.mercancia)
            return

        for ln in lineas:
            cantidad_actual = ln["cantidad_actual"]
            try:
                cantidad_actual = float(cantidad_actual or 0)
            except (TypeError, ValueError):
                cantidad_actual = 0
            nueva_cantidad = cantidad_actual + ln.get("cantidad_base", ln["cantidad"])
            if abs(nueva_cantidad - int(nueva_cantidad)) < 0.0001:
                nueva_cantidad = int(nueva_cantidad)
            resultado = Consultas.actualizar_cantidad_producto(ln["nombre"], nueva_cantidad)
            if proveedor:
                Consultas.asignar_proveedor_producto(ln["nombre"], proveedor)
            Consultas.actualizar_precios_recepcion(
                ln["nombre"], ln.get("costo_base_unidad", ln["precio_base"]), ln["precio_venta"], ln["iva_txt"]
            )
            if ln["vence"]:
                Consultas.registrar_lote(
                    ln["producto_id"],
                    ln.get("cantidad_base", ln["cantidad"]),
                    ln["vence"],
                    proveedor,
                    costo=ln.get("costo_base_unidad") or 0,
                    factura=factura,
                    presentacion_id=ln.get("presentacion_id"),
                    presentacion_nombre=ln.get("presentacion_nombre") or "",
                )
            Consultas.registrar_movimiento_inventario(
                ln["producto_id"],
                "COMPRA",
                ln["cantidad"],
                ln.get("factor") or 1,
                "Compra factura {} · prov. {}".format(factura or "-", proveedor or "s/p"),
                self.usuario or "",
                ln.get("presentacion_id"),
            )
            if not resultado:
                mb.showerror(
                    "Error",
                    f"La compra se guardó, pero no se pudo actualizar el inventario de: {ln['nombre']}",
                    parent=self.mercancia,
                )
                return

        avisos = []
        for ln in lineas:
            avisos.extend(
                Consultas.alertas_margen_presentaciones(
                    ln["producto_id"],
                    ln.get("costo_base_unidad") or ln["precio_base"],
                    ln.get("iva_txt") or 0,
                )
            )
        extra_util = ""
        if avisos:
            extra_util = "\n\nOjo: algunas presentaciones quedaron con utilidad baja o negativa:\n- " + "\n- ".join(avisos[:8])

        self._limpiar_formulario()
        extra = ""
        if factura:
            extra += f"\nFactura: {factura}"
        extra += f"\nMétodo: {metodo}\nPagado: {formato_dinero(pagado)}"
        if saldo > 0.009:
            extra += f"\nSaldo pendiente: {formato_dinero(saldo)}"
        mb.showinfo(
            "Éxito",
            "Compra realizada e inventario actualizado." + extra + extra_util,
            parent=self.mercancia,
        )

    def llenar_combo(self):
        import Consultas
        proveedores = Consultas.llenar_combobox() or []
        self.añadir_proveedor["values"] = proveedores

    def _abrir_nuevo_producto(self):
        import nuevo_producto

        dlg = nuevo_producto.nuevo_producto(self.mercancia)
        self.mercancia.wait_window(dlg.nuevo)
        self._recargar_catalogo()
        self.llenar_combo()

    def _recargar_catalogo(self, filas=None):
        import Consultas

        self.tree_productos.delete(*self.tree_productos.get_children())
        for row in filas if filas is not None else (Consultas.mostrar_Productos() or []):
            valores = self._valores_catalogo(row)
            if valores:
                self.tree_productos.insert("", "end", values=valores)
        if self.tree_productos.get_children():
            first = self.tree_productos.get_children()[0]
            self.tree_productos.selection_set(first)
            self.obtener_datos_seleccionados()

    def buscar(self, event=None):
        import Consultas
        try:
            codigo = self.buscar_producto.get()
            self.tree_productos.delete(*self.tree_productos.get_children())
            resultados = Consultas.buscar_productos(codigo, codigo, codigo)
            for row in resultados or []:
                valores = self._valores_catalogo(row)
                if valores:
                    self.tree_productos.insert("", tk.END, values=valores)

            if self.tree_productos.get_children():
                self.first_item = self.tree_productos.get_children()[0]
                self.tree_productos.selection_set(self.first_item)
                self.obtener_datos_seleccionados()
        except ValueError as error:
            mb.showerror("Error al buscar el producto {}".format(error), parent=self.mercancia)

    def obtener_datos_seleccionados(self, event=None):
        import Consultas
        try:
            sel = self.tree_productos.selection()
            if not sel:
                self.mostrar_producto.delete(0, tk.END)
                return
            item = self.tree_productos.item(sel[0], "values")
            if not item:
                return
            self.mostrar_producto.delete(0, tk.END)
            self.mostrar_producto.insert(0, item[1])
            compra = parse_dinero(item[3] if len(item) > 3 else 0)
            venta = parse_dinero(item[2] if len(item) > 2 else 0)
            iva_txt = item[5] if len(item) > 5 else ""
            Consultas.escribir_iva(self.iva_linea, iva_txt)
            self.var_iva_incluido.set(False)
            self.precio_compra_linea.delete(0, tk.END)
            if compra > 0:
                self.precio_compra_linea.insert(0, formato_entrada(str(int(round(compra)))))
            self.precio_venta_linea.delete(0, tk.END)
            if venta > 0:
                self.precio_venta_linea.insert(0, formato_entrada(str(int(redondear_centena(venta)))))
            self.ganancia_linea.set(
                Consultas.utilidad_a_texto(Consultas.margen_desde_precios(compra, venta, iva_txt))
            )
            self._cargar_presentaciones_compra(item[0])
        except Exception as error:
            print("Error al obtener datos seleccionados: {}".format(error))
            mb.showerror("Error", "Error al obtener los datos seleccionados", parent=self.mercancia)

    def _cargar_presentaciones_compra(self, producto_id):
        import Consultas
        self._pres_opciones = Consultas.listar_presentaciones(producto_id) or []
        nombres = [p["nombre"] for p in self._pres_opciones] or ["Unidad"]
        self.presentacion_linea["values"] = nombres
        if self._pres_opciones:
            top = max(self._pres_opciones, key=lambda p: float(p.get("factor") or 1))
            self.presentacion_linea.set(top["nombre"])
        else:
            self.presentacion_linea.set("Unidad")
            self._pres_opciones = [{"id": None, "nombre": "Unidad", "factor": 1}]

    def _presentacion_compra(self):
        nombre = (self.presentacion_linea.get() or "Unidad").strip()
        for item in self._pres_opciones:
            if item.get("nombre") == nombre:
                return item
        return self._pres_opciones[0] if self._pres_opciones else {"nombre": "Unidad", "factor": 1, "id": None}
