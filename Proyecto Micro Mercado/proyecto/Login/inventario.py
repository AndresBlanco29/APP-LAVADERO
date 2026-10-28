import tkinter as tk
from tkinter import ttk
import mensaje as mb
import nuevo_producto
import modificar_producto
import eliminar_producto
from agregar_mercancia import *
import Consultas
from usuarios import *
from datetime import datetime
from zyntra_ui import *
from exportes import exportar_xlsx, exportar_pdf


def _fecha_lote(valor):
    if not valor:
        return None
    if hasattr(valor, "date") and not isinstance(valor, datetime):
        try:
            return valor
        except Exception:
            return None
    if hasattr(valor, "date"):
        try:
            return valor.date()
        except Exception:
            return None
    try:
        return datetime.strptime(str(valor)[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def abrir_dialogo_vencimientos(parent, filas=None, dias=None):
    if dias is None:
        try:
            dias = int(Consultas.obtener_config_pos().get("dias_alerta_vence") or 30)
        except (TypeError, ValueError):
            dias = 30
    filas = filas if filas is not None else Consultas.lotes_por_vencer(dias)
    if not filas:
        mb.showinfo("Vencimientos", "No hay lotes por vencer en los próximos {} días.".format(dias), parent=parent)
        return
    dlg = tk.Toplevel(parent)
    prepare_modal(dlg, parent, "Próximos a vencer", 780, 440)
    card = card_frame(dlg, padx=16, pady=14)
    card.pack(fill="both", expand=True)
    styled_label(card, "Lotes vencidos o por vencer", FONT_HEADING, TEXT, BG_CARD).pack(anchor="w")
    styled_label(
        card,
        "Rojo: vencido o ≤ 7 días  ·  Naranja ≤ 15  ·  Amarillo según la alerta configurada",
        FONT_SMALL,
        TEXT_DIM,
        BG_CARD,
    ).pack(anchor="w", pady=(2, 8))
    wrap, tree = scrollable_tree(
        card,
        columns=("Codigo", "Producto", "Cantidad", "Vence", "Lote", "Proveedor", "Alerta"),
        headings=("Cód.", "Producto", "Cant.", "Vence", "Lote", "Proveedor", "Alerta"),
        height=10,
        widths={"Codigo": 60, "Producto": 160, "Cantidad": 70, "Vence": 90, "Lote": 80, "Proveedor": 120, "Alerta": 80},
    )
    tree.column("Producto", anchor="w")
    wrap.pack(fill="both", expand=True)
    hoy = datetime.now().date()
    for row in filas:
        fecha_d = _fecha_lote(row[4]) or hoy
        restantes = (fecha_d - hoy).days
        if restantes < 0:
            alerta, tag = "Vencido", "vence7"
        elif restantes <= 7:
            alerta, tag = "7 días", "vence7"
        elif restantes <= 15:
            alerta, tag = "15 días", "vence15"
        else:
            alerta, tag = "{} días".format(dias), "vence30"
        tree.insert(
            "",
            "end",
            values=(row[1], row[2], row[3], fecha_d.strftime("%d/%m/%Y"), row[5], row[6], alerta),
            tags=(tag,),
        )


def avisar_vencimientos(parent, app=None, filas=None, config=None):
    if app is None and parent is not None:
        try:
            app = getattr(parent.winfo_toplevel(), "zyntra_app", None)
        except Exception:
            app = None
    if app is not None and getattr(app, "_alerta_vence_ok", False):
        return
    filas = list(filas) if filas is not None else (Consultas.lotes_por_vencer() or [])
    if app is not None:
        app._alerta_vence_ok = True
    if not filas:
        return
    hoy = datetime.now().date()
    vencidos = 0
    urgentes = 0
    for row in filas:
        fecha_d = _fecha_lote(row[4])
        if not fecha_d:
            continue
        dias_rest = (fecha_d - hoy).days
        if dias_rest < 0:
            vencidos += 1
        elif dias_rest <= 7:
            urgentes += 1
    cfg = config if config is not None else Consultas.obtener_config_pos()
    ventana = (cfg or {}).get("dias_alerta_vence") or 30
    partes = ["Hay {} lote(s) próximos a vencer en los próximos {} días.".format(len(filas), ventana)]
    if vencidos:
        partes.append("{} ya vencido(s).".format(vencidos))
    if urgentes:
        partes.append("{} vence(n) en 7 días o menos.".format(urgentes))
    partes.append("\n¿Desea ver el detalle ahora?")
    if mb.askyesno("Alerta de vencimiento", "\n".join(partes), parent=parent):
        abrir_dialogo_vencimientos(parent, filas)


class Frm_inventario(tk.Frame):
    def __init__(self, parent, usuario):
        super().__init__(parent, bg=BG)
        self.usuario = usuario
        self.inventario = self
        self.items()

    def items(self):
        toolbar = card_frame(self, padx=12, pady=8)
        toolbar.pack(fill="x", pady=(0, 8))
        styled_label(toolbar, "Buscar producto", FONT_LABEL, TEXT_MUTED, BG_CARD).pack(anchor="w")
        row = tk.Frame(toolbar, bg=BG_CARD)
        row.pack(fill="x", pady=(6, 0))
        self.buscar_producto = styled_entry(row, width=36)
        self.buscar_producto.pack(side="left", fill="x", expand=True)
        self.buscar_producto.bind("<KeyRelease>", self.buscar)
        self.actualizar = secondary_button(row, "Actualizar tabla", self.actualizar_tabla, width=16)
        self.actualizar.pack(side="left", padx=(10, 0))

        actions = card_frame(self, padx=12, pady=8)
        actions.pack(side="bottom", fill="x")
        row1 = tk.Frame(actions, bg=BG_CARD)
        row1.pack(fill="x")
        primary_button(row1, "Crear un producto", self.abrir_nuevo_producto, width=20).pack(side="left", padx=(0, 8))
        secondary_button(row1, "Modificar un producto", self.abrir_modificar_producto, width=20).pack(side="left", padx=(0, 8))
        danger_button(row1, "Eliminar un producto", self.abrir_eliminar_producto, width=18).pack(side="left", padx=(0, 8))
        secondary_button(row1, "Ingreso de producto", self.abrir_agregar_mercancia, width=18).pack(side="left", padx=(0, 8))
        warning_button(row1, "Ajustar inventario", self.abrir_ajuste, width=16, font=FONT_SMALL).pack(side="left", padx=(0, 8))
        warning_button(row1, "Inventario físico", self.abrir_inventario_fisico, width=16, font=FONT_SMALL).pack(
            side="left", padx=(0, 8)
        )
        secondary_button(row1, "Kardex", self.abrir_kardex, width=12).pack(side="left", padx=(0, 8))
        secondary_button(row1, "Receta / Kit", self.abrir_receta, width=14).pack(side="left", padx=(0, 8))
        primary_button(row1, "Imprimir etiqueta", self.imprimir_etiqueta, width=16).pack(side="left")

        row2 = tk.Frame(actions, bg=BG_CARD)
        row2.pack(fill="x", pady=(10, 0))
        secondary_button(row2, "Mayor existencias", self.mayor_exis, width=16).pack(side="left", padx=(0, 8))
        secondary_button(row2, "Menor existencias", self.menor_exis, width=16).pack(side="left", padx=(0, 8))
        primary_button(row2, "Excel", self.exportar_excel, width=10).pack(side="left", padx=(0, 8))
        primary_button(row2, "PDF", self.generar_reporte, width=10).pack(side="left", padx=(0, 8))
        warning_button(row2, "Sugerido de compra", self.generar_sugerido, width=18, font=FONT_SMALL).pack(side="left", padx=(0, 8))
        warning_button(row2, "Próximos a vencer", self.mostrar_vencimientos, width=16, font=FONT_SMALL).pack(side="left", padx=(0, 8))
        secondary_button(row2, "Negocio", self.abrir_config_negocio, width=10, font=FONT_SMALL).pack(side="left")

        totals = tk.Frame(row2, bg=BG_CARD)
        totals.pack(side="right")
        t1 = tk.Frame(totals, bg=BG_CARD)
        t1.pack(side="left", padx=(0, 12))
        styled_label(t1, "Inversión total", FONT_LABEL, TEXT_MUTED, BG_CARD).pack(anchor="w")
        self.inversion_total = styled_entry(t1, width=16)
        self.inversion_total.pack()
        t2 = tk.Frame(totals, bg=BG_CARD)
        t2.pack(side="left")
        styled_label(t2, "Venta total", FONT_LABEL, TEXT_MUTED, BG_CARD).pack(anchor="w")
        self.venta_total = styled_entry(t2, width=16)
        self.venta_total.pack()

        self.tree_wrap, self.tree_productos = scrollable_tree(
            self,
            columns=("Codigo", "Nombre", "Precio_de_venta", "Precio_de_Compra", "Iva", "Cantidad", "Minimo", "Marca", "Categoria", "Ubicacion", "Vence"),
            headings=("Código", "Nombre", "P. venta", "P. compra", "IVA", "Existencia", "Mín.", "Marca", "Categoría", "Ubicación", "Vence"),
            height=5,
            widths={
                "Codigo": 70,
                "Nombre": 130,
                "Precio_de_venta": 75,
                "Precio_de_Compra": 75,
                "Iva": 70,
                "Cantidad": 140,
                "Minimo": 45,
                "Marca": 80,
                "Categoria": 80,
                "Ubicacion": 80,
                "Vence": 85,
            },
        )
        self.tree_productos.column("Nombre", anchor="w")
        self.tree_wrap.pack(fill="both", expand=True, pady=(0, 8))
        self.tree_productos.bind("<Double-1>", lambda _e: self.abrir_modificar_producto())

    def on_show(self):
        if should_refresh(self):
            self.actualizar_tabla()
        self.buscar_producto.focus_set()

    def _dias_vence(self, fecha):
        if not fecha:
            return None
        if isinstance(fecha, str):
            try:
                fecha = datetime.strptime(fecha[:10], "%Y-%m-%d").date()
            except ValueError:
                return None
        elif hasattr(fecha, "date") and not isinstance(fecha, datetime):
            pass
        elif hasattr(fecha, "date"):
            fecha = fecha.date()
        try:
            return (fecha - datetime.now().date()).days
        except Exception:
            return None

    def _valores_fila(self, row, vencimientos=None, pres_map=None):
        datos = Consultas.parse_producto(row)
        vence = (vencimientos or {}).get(int(datos["id"])) if datos and datos["id"] is not None else None
        vence_txt = ""
        tags = ()
        dias = self._dias_vence(vence)
        if dias is not None:
            if hasattr(vence, "strftime"):
                vence_txt = vence.strftime("%d/%m/%Y")
            else:
                vence_txt = str(vence)[:10]
            if dias <= 7:
                tags = ("vence7",)
            elif dias <= 15:
                tags = ("vence15",)
            elif dias <= 30:
                tags = ("vence30",)
        if not tags:
            try:
                bajo = float(datos["cantidad"] or 0) <= float(datos["stock_minimo"] or 10)
            except (TypeError, ValueError):
                bajo = False
            tags = ("bajo",) if bajo else ()
        try:
            pres = (pres_map or {}).get(int(datos["id"]), [])
            equiv = Consultas.texto_equivalencias(datos["cantidad"], pres, datos.get("unidad_base") or "Unidad")
        except Exception:
            equiv = str(datos["cantidad"])
        valores = (
            datos["id"],
            datos["nombre"],
            formato_dinero(datos["precio_venta"]),
            formato_dinero(datos["precio_compra"]),
            Consultas.iva_a_texto(datos.get("iva")),
            equiv,
            datos["stock_minimo"],
            datos["marca"],
            datos["categoria"],
            datos["ubicacion"],
            vence_txt,
        )
        return valores, tags

    def _preparar_filas(self, resultados, vencimientos=None, pres_map=None):
        filas = []
        total_inversion = 0
        total_venta = 0
        vencimientos = vencimientos if vencimientos is not None else {}
        pres_map = pres_map if pres_map is not None else {}
        for row in resultados or []:
            valores, tags = self._valores_fila(row, vencimientos, pres_map)
            filas.append((valores, tags))
            datos = Consultas.parse_producto(row)
            try:
                qty = float(datos["cantidad"] or 0)
                total_inversion += float(datos["precio_compra"] or 0) * qty
                total_venta += float(datos["precio_venta"] or 0) * qty
            except (TypeError, ValueError):
                pass
        return filas, total_inversion, total_venta

    def _pintar_inventario(self, data):
        filas, total_inversion, total_venta = data
        self.inversion_total.delete(0, tk.END)
        self.inversion_total.insert(0, formato_dinero(total_inversion))
        self.venta_total.delete(0, tk.END)
        self.venta_total.insert(0, formato_dinero(total_venta))
        fill_tree_chunked(self, self.tree_productos, filas, on_done=lambda: mark_refreshed(self))

    def _fetch_inventario(self, productos):
        return self._preparar_filas(
            productos,
            Consultas.mapa_vencimientos(),
            Consultas.mapa_presentaciones(),
        )

    def actualizar_tabla(self):
        load_async(self, lambda: self._fetch_inventario(Consultas.mostrar_Productos() or []), self._pintar_inventario)

    def buscar(self, event=None):
        debounce(self, "_buscar_job", 160, self._aplicar_busqueda)

    def _aplicar_busqueda(self):
        texto_buscado = self.buscar_producto.get().lower().strip()

        def fetch():
            if not texto_buscado:
                productos = Consultas.mostrar_Productos() or []
            else:
                productos = Consultas.buscar_productos(texto_buscado, texto_buscado, texto_buscado) or []
            return self._fetch_inventario(productos)

        load_async(self, fetch, self._pintar_inventario)

    def _modal_parent(self):
        return self.winfo_toplevel()

    def abrir_nuevo_producto(self):
        dlg = nuevo_producto.nuevo_producto(self._modal_parent())
        self.wait_window(dlg.nuevo)
        self.actualizar_tabla()

    def abrir_modificar_producto(self):
        codigo = None
        sel = self.tree_productos.selection()
        if sel:
            codigo = self.tree_productos.item(sel[0], "values")[0]
        dlg = modificar_producto.Modificar(self._modal_parent(), codigo_inicial=codigo)
        self.wait_window(dlg.modificar)
        self.actualizar_tabla()

    def abrir_eliminar_producto(self):
        dlg = eliminar_producto.Eliminar(self._modal_parent(), usuario=self.usuario)
        self.wait_window(dlg.eliminar)
        self.actualizar_tabla()

    def abrir_agregar_mercancia(self):
        dlg = Mercancia(self._modal_parent(), usuario=self.usuario)
        self.wait_window(dlg.mercancia)
        self.actualizar_tabla()

    def abrir_kardex(self):
        from kardex import KardexProducto
        codigo = None
        sel = self.tree_productos.selection()
        if sel:
            codigo = self.tree_productos.item(sel[0], "values")[0]
        dlg = KardexProducto(self._modal_parent(), codigo_inicial=codigo)
        self.wait_window(dlg.win)

    def abrir_ajuste(self):
        from ajuste_inventario import AjusteInventario
        codigo = None
        sel = self.tree_productos.selection()
        if sel:
            codigo = self.tree_productos.item(sel[0], "values")[0]
        dlg = AjusteInventario(self._modal_parent(), usuario=self.usuario, codigo_inicial=codigo)
        self.wait_window(dlg.win)
        self.actualizar_tabla()

    def abrir_inventario_fisico(self):
        from inventario_fisico import InventarioFisico
        dlg = InventarioFisico(self._modal_parent(), usuario=self.usuario)
        self.wait_window(dlg.win)
        self.actualizar_tabla()

    def abrir_config_negocio(self):
        cfg = Consultas.obtener_config_pos()
        dlg = tk.Toplevel(self._modal_parent())
        prepare_modal(dlg, self._modal_parent(), "Configurar negocio", 560, 620, resizable=True)
        card = card_frame(dlg, padx=22, pady=18)
        card.pack(fill="both", expand=True)
        styled_label(card, "Configuración del negocio", FONT_HEADING, TEXT, BG_CARD).pack(anchor="w", pady=(0, 8))
        styled_label(
            card,
            "Defina la base del gabinete y el recargo por datafono. El precio de inventario sigue siendo el valor real.",
            FONT_SMALL,
            TEXT_DIM,
            BG_CARD,
        ).pack(anchor="w", pady=(0, 12))
        styled_label(card, "Tipo de negocio", FONT_LABEL, TEXT_MUTED, BG_CARD).pack(anchor="w")
        tipo = ttk.Combobox(card, font=("Segoe UI", 11), style="Zyntra.TCombobox", values=Consultas.TIPOS_NEGOCIO, state="readonly")
        tipo.pack(fill="x", pady=(4, 10))
        tipo.set(cfg.get("tipo_negocio") or "Tienda")
        _, dias = labeled_field(card, "Días de alerta de vencimiento")
        _.pack(fill="x", pady=(0, 10))
        dias.insert(0, str(cfg.get("dias_alerta_vence") or 30))
        _, base = labeled_field(card, "Base del gabinete $ (queda en caja)")
        _.pack(fill="x", pady=(0, 10))
        bind_money_entry(base)
        base_val = int(round(float(cfg.get("base_gabinete") or 0)))
        if base_val:
            base.insert(0, formato_entrada(str(base_val)))
        _, pct = labeled_field(card, "% recargo datafono / tarjeta")
        _.pack(fill="x", pady=(0, 10))
        pct.insert(0, str(cfg.get("pct_recargo_tarjeta") if cfg.get("pct_recargo_tarjeta") is not None else 6))
        var_fefo = tk.BooleanVar(value=bool(cfg.get("usar_fefo", True)))
        tk.Checkbutton(
            card,
            text="Usar FEFO (vender primero el lote que vence antes)",
            variable=var_fefo,
            bg=BG_CARD,
            fg=TEXT,
            selectcolor=BG_INPUT,
            activebackground=BG_CARD,
            activeforeground=TEXT,
            font=FONT_LABEL,
        ).pack(anchor="w", pady=(0, 16))

        def guardar():
            try:
                alerta = int(dias.get() or 30)
                base_n = parse_dinero(base.get())
                pct_n = float(str(pct.get() or "0").replace(",", ".").replace("%", "").strip() or 0)
            except ValueError:
                mb.showerror("Configuración", "Revise base, porcentaje y días de alerta.", parent=dlg)
                return
            if base_n < 0 or pct_n < 0 or pct_n > 100:
                mb.showerror("Configuración", "Base y porcentaje deben ser válidos (0-100% el recargo).", parent=dlg)
                return
            Consultas.guardar_config_pos(
                tipo_negocio=tipo.get() or "Tienda",
                dias_alerta_vence=max(1, alerta),
                usar_fefo=var_fefo.get(),
                base_gabinete=base_n,
                pct_recargo_tarjeta=pct_n,
            )
            mb.showinfo("Configuración", "Datos del negocio actualizados.", parent=dlg)
            dlg.destroy()

        primary_button(card, "Guardar", guardar, width=20).pack(fill="x")

    def abrir_receta(self):
        from recetas import EditorReceta
        dlg = EditorReceta(self._modal_parent())
        self.wait_window(dlg.win)

    def imprimir_etiqueta(self):
        sel = self.tree_productos.selection()
        if not sel:
            mb.showwarning("Etiqueta", "Seleccione un producto en la tabla.", parent=self.inventario)
            return
        valores = self.tree_productos.item(sel[0], "values")
        try:
            from etiquetas import imprimir_etiqueta
            imprimir_etiqueta(valores[0], valores[1], valores[2], parent=self.inventario)
        except Exception as error:
            mb.showerror("Etiqueta", str(error), parent=self.inventario)

    def mostrar_vencimientos(self):
        abrir_dialogo_vencimientos(self._modal_parent())

    def mayor_exis(self):
        def fetch():
            productos = sorted(Consultas.mostrar_Productos() or [], key=lambda x: x[4], reverse=True)
            return self._fetch_inventario(productos)

        load_async(self, fetch, self._pintar_inventario)

    def menor_exis(self):
        def fetch():
            productos = sorted(Consultas.mostrar_Productos() or [], key=lambda x: x[4], reverse=False)
            return self._fetch_inventario(productos)

        load_async(self, fetch, self._pintar_inventario)

    def _filas_export(self):
        filas = []
        for item in self.tree_productos.get_children():
            valores = self.tree_productos.item(item, "values")
            precio_venta = float(valores[2] or 0)
            precio_compra = float(valores[3] or 0)
            cantidad = float(valores[5] or 0)
            filas.append(
                [
                    valores[0],
                    valores[1],
                    precio_compra,
                    precio_venta,
                    valores[4],
                    cantidad,
                    valores[6],
                    valores[7],
                    valores[8],
                    valores[9],
                    precio_compra * cantidad,
                    precio_venta * cantidad,
                ]
            )
        return filas

    def exportar_excel(self):
        filas = self._filas_export()
        if not filas:
            mb.showinfo("Exportar", "No hay productos para exportar.", parent=self.inventario)
            return
        encabezados = [
            "Código", "Nombre", "Precio compra", "Precio venta", "IVA", "Stock", "Mínimo",
            "Marca", "Categoría", "Ubicación", "Inversión", "Valor venta",
        ]
        extras = [
            f"Inversión total: {self.inversion_total.get()}",
            f"Valor de venta total: {self.venta_total.get()}",
        ]
        try:
            path = exportar_xlsx(encabezados, filas, "inventario.xlsx", "Inventario Zyntra POS", extras)
            mb.showinfo("Excel generado", f"Archivo guardado en:\n{path}", parent=self.inventario)
        except Exception as error:
            mb.showerror("Error", f"No se pudo exportar a Excel: {error}", parent=self.inventario)

    def generar_reporte(self):
        filas = self._filas_export()
        if not filas:
            mb.showinfo("Reporte", "No hay productos para generar el reporte.", parent=self.inventario)
            return
        try:
            nombre_usuario = usuarios.Obtener_Nombre_Empleado(self.usuario)
        except Exception:
            nombre_usuario = self.usuario
        encabezados = [
            "Código", "Nombre", "P. compra", "P. venta", "IVA", "Stock", "Mín.",
            "Marca", "Categoría", "Ubicación", "Inversión", "Valor venta",
        ]
        extras = [
            f"Inversión total: {self.inversion_total.get()}",
            f"Valor de venta total: {self.venta_total.get()}",
            f"Usuario en turno: {nombre_usuario}",
        ]
        try:
            path = exportar_pdf(
                f"Reporte de inventario — {datetime.now().strftime('%d/%m/%Y')}",
                encabezados,
                filas,
                "reporte_inventario.pdf",
                extras,
                apaisado=True,
            )
            mb.showinfo("Reporte generado", f"El PDF se guardó en:\n{path}", parent=self.inventario)
        except Exception as error:
            mb.showerror("Error", f"No se pudo generar el PDF: {error}", parent=self.inventario)

    def generar_sugerido(self):
        cfg = Consultas.obtener_config_pos()
        dias = int(cfg.get("dias_cobertura") or 15)
        filas = Consultas.sugerido_compra(dias)
        if not filas:
            mb.showinfo(
                "Sugerido",
                f"No hay productos por reponer según stock y ventas de los últimos {dias} días.",
                parent=self.inventario,
            )
            return
        encabezados = [
            "Proveedor", "Código", "Producto", "Stock", "Mínimo", f"Vendido {dias}d",
            "Prom. diario", "Sugerido", "Costo unit.", "Total compra",
        ]
        data = [
            [
                f["proveedor"], f["codigo"], f["nombre"], f["stock"], f["minimo"],
                f["vendido"], f["promedio"], f["sugerido"], f["costo"], f["total"],
            ]
            for f in filas
        ]
        extras = []
        totales = {}
        for f in filas:
            totales[f["proveedor"]] = totales.get(f["proveedor"], 0) + f["total"]
        for proveedor, total in totales.items():
            extras.append(f"{proveedor}: {formato_dinero(total)}")
        extras.append(f"Total sugerido: {formato_dinero(sum(totales.values()))}")
        try:
            path = exportar_xlsx(
                encabezados,
                data,
                "sugerido_compra.xlsx",
                f"Sugerido de compra — {dias} días (agrupado por proveedor)",
                extras,
            )
            mb.showinfo("Sugerido de compra", f"Excel agrupado por proveedor:\n{path}", parent=self.inventario)
        except Exception as error:
            mb.showerror("Error", f"No se pudo exportar el sugerido: {error}", parent=self.inventario)
