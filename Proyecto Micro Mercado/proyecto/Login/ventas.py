import tkinter as tk
from datetime import datetime
import mensaje as mb
from tkinter import ttk
from Consultas import *
from zyntra_ui import *


class VentaView(tk.Frame):
    def __init__(self, parent, shell):
        super().__init__(parent, bg=BG)
        self.shell = shell
        self.ventas = self
        self.usuario = shell.app.usuario
        self.total_ventas = 0.00
        self.total_tarjeta = 0.00
        self.total_articulos = 0
        self.empleado = self.usuario
        self.id_empleado = shell.app.id_empleado
        self.cuentas_espera = []
        self.cliente = None
        self._pres_map = {}
        self._silenciar_buscador = False
        self._nombre_autollenado = False
        self._qty_editor = None
        self._qty_item = None
        self._codigo_sel = ""
        self._pres_forzada = None
        self.items()

    def items(self):
        apply_ttk_styles(force=True)
        # --- Footer fijo (caja): acciones + totales + cobrar ---
        footer = card_frame(self, padx=12, pady=8)
        footer.pack(side="bottom", fill="x", pady=(6, 0))
        footer.configure(highlightthickness=1, highlightbackground=BORDER)

        acciones = tk.Frame(footer, bg=BG_CARD)
        acciones.pack(side="left", fill="y")
        self.btn_cancelarVenta = danger_button(
            acciones, "Cancelar Venta", self.cancelar_venta, width=14, height=2, font=FONT_POS_BTN
        )
        self.btn_cancelarVenta.pack(side="left", padx=(0, 8))
        self.btn_cancelarProducto = secondary_button(
            acciones, "Cancelar Producto", self.cancelar_producto, width=16, height=2, font=FONT_POS_BTN
        )
        self.btn_cancelarProducto.pack(side="left", padx=(0, 8))
        secondary_button(
            acciones, "En espera", self.poner_en_espera, width=12, height=2, font=FONT_POS_BTN
        ).pack(side="left", padx=(0, 8))
        self.btn_recuperar = secondary_button(
            acciones, "Recuperar (0)", self.recuperar_cuenta, width=14, height=2, font=FONT_POS_BTN
        )
        self.btn_recuperar.pack(side="left", padx=(0, 14))
        turno_box = tk.Frame(acciones, bg=BG_ELEVATED, padx=10, pady=6)
        turno_box.pack(side="left")
        styled_label(turno_box, "Turno", FONT_SMALL, TEXT_DIM, BG_ELEVATED).pack(anchor="w")
        self.turno = styled_label(turno_box, self.empleado, FONT_POS_BTN, TEXT, BG_ELEVATED)
        self.turno.pack(anchor="w")

        cobrar_box = tk.Frame(footer, bg=BG_ELEVATED, padx=12, pady=8)
        cobrar_box.pack(side="right")
        cobrar_box.configure(highlightthickness=1, highlightbackground=ACCENT)
        self.btn_cobrar = primary_button(
            cobrar_box, "F12  Cobrar", self.abrir_cobrar, width=14, height=2, font=("Segoe UI", 14, "bold")
        )
        self.btn_cobrar.pack(side="right")

        totales = tk.Frame(footer, bg=BG_CARD)
        totales.pack(side="right", padx=(0, 14))
        styled_label(totales, "Desc. (efectivo)", FONT_LABEL, CYAN, BG_CARD).pack(anchor="e")
        self.cobro = money_label(totales, "$ 0", FONT_POS_TOTAL, CYAN, BG_CARD)
        self.cobro.pack(anchor="e")
        self.cobro_tarj = styled_label(totales, "Tarjeta $ 0", ("Segoe UI", 14, "bold"), WARNING, BG_CARD)
        self.cobro_tarj.pack(anchor="e", pady=(2, 0))

        # --- Barra de captura (compacta, una sola franja) ---
        self.scan = card_frame(self, padx=10, pady=6)
        self.scan.pack(fill="x", pady=(0, 6))

        fields = tk.Frame(self.scan, bg=BG_CARD)
        fields.pack(fill="x")

        col_search = tk.Frame(fields, bg=BG_CARD)
        col_search.pack(side="left", fill="x", expand=True, padx=(0, 8))
        styled_label(
            col_search, "Buscar producto / código / barras", FONT_LABEL, TEXT_MUTED, BG_CARD
        ).pack(anchor="w")
        self.buscar_magico = styled_entry(col_search, font=FONT_POS)
        self.buscar_magico.pack(fill="x", pady=(2, 0), ipady=3)
        self.buscar_magico.bind("<KeyRelease>", self._filtrar_magico)
        self.buscar_magico.bind("<Return>", self._enter_magico)
        self.buscar_magico.bind("<KP_Enter>", self._enter_magico)
        self.buscar_magico.bind("<Tab>", self._enter_magico)
        self.buscar_magico.bind("<Down>", self._enfocar_sugerencias)
        self.buscar_magico.bind("<Escape>", lambda _e: self._ocultar_sugerencias())

        col_qty = tk.Frame(fields, bg=BG_CARD)
        col_qty.pack(side="left", padx=(0, 8))
        styled_label(col_qty, "Cant.", FONT_LABEL, TEXT_MUTED, BG_CARD).pack(anchor="w")
        self.cantidad_producto = styled_entry(col_qty, width=6, font=FONT_POS)
        self.cantidad_producto.pack(pady=(2, 0), ipady=3)
        self.cantidad_producto.bind("<Return>", self._enter_cantidad)
        self.cantidad_producto.bind("<KP_Enter>", self._enter_cantidad)
        self._reset_cantidad()

        col_pres = tk.Frame(fields, bg=BG_CARD)
        col_pres.pack(side="left", padx=(0, 8))
        styled_label(col_pres, "Presentación", FONT_LABEL, TEXT_MUTED, BG_CARD).pack(anchor="w")
        self.presentacion = ttk.Combobox(
            col_pres, font=FONT_POS, style="Zyntra.TCombobox", width=12, state="readonly"
        )
        self.presentacion.pack(pady=(2, 0), ipady=1)
        self.presentacion.bind("<<ComboboxSelected>>", lambda _e: setattr(self, "_pres_forzada", None))
        self._pres_opciones = []

        plus_wrap = tk.Frame(fields, bg=BG_CARD)
        plus_wrap.pack(side="left", padx=(0, 8))
        styled_label(plus_wrap, " ", FONT_LABEL, TEXT_MUTED, BG_CARD).pack()
        self.btn_agregar = plus_button(plus_wrap, self.agregar_lista_venta)
        self.btn_agregar.pack(pady=(2, 0))

        cli = tk.Frame(fields, bg=BG_CARD)
        cli.pack(side="left", fill="y", padx=(4, 0))
        styled_label(cli, "Cliente", FONT_LABEL, TEXT_MUTED, BG_CARD).pack(anchor="w")
        cli_row = tk.Frame(cli, bg=BG_CARD)
        cli_row.pack(fill="x", pady=(2, 0))
        self.lbl_cliente = styled_label(cli_row, "Cliente: mostrador", FONT_BODY, TEXT, BG_CARD)
        self.lbl_cliente.pack(side="left")
        self.lbl_iva_producto = styled_label(cli_row, "IVA: —", FONT_SMALL, TEXT_DIM, BG_CARD)
        self.lbl_iva_producto.pack(side="left", padx=(8, 0))
        secondary_button(
            cli_row, "Asociar", self._asociar_cliente, width=9, height=1, font=FONT_POS_BTN
        ).pack(side="left", padx=(8, 4))
        secondary_button(
            cli_row, "Quitar", self._quitar_cliente, width=7, height=1, font=FONT_POS_BTN
        ).pack(side="left")

        self.suggest_card = card_frame(self, padx=8, pady=4)
        self.suggest_card.configure(highlightthickness=1, highlightbackground=ACCENT)
        styled_label(
            self.suggest_card,
            "Seleccione un producto  ·  Enter o doble clic",
            FONT_SMALL,
            TEXT_DIM,
            BG_CARD,
        ).pack(anchor="w")
        self.suggest_wrap, self.tree_sugerencias = scrollable_tree(
            self.suggest_card,
            columns=("Codigo", "Nombre", "Precio", "PrecioTarj", "Iva", "Stock", "Marca"),
            headings=("Cód.", "Nombre", "P. desc.", "P. +%", "IVA", "Stock", "Marca"),
            height=3,
            widths={
                "Codigo": 60,
                "Nombre": 220,
                "Precio": 95,
                "PrecioTarj": 95,
                "Iva": 70,
                "Stock": 60,
                "Marca": 90,
            },
        )
        self.tree_sugerencias.column("Nombre", anchor="w")
        self.tree_sugerencias.tag_configure("con_iva", foreground=CYAN)
        self.tree_sugerencias.tag_configure("sin_iva", foreground=TEXT_DIM)
        self.suggest_wrap.pack(fill="x", pady=(2, 0))
        self.tree_sugerencias.bind("<Double-1>", lambda _e: self._usar_sugerencia(agregar=False))
        self.tree_sugerencias.bind("<Return>", lambda _e: self._usar_sugerencia(agregar=False))
        self.tree_sugerencias.bind("<KP_Enter>", lambda _e: self._usar_sugerencia(agregar=False))
        self.tree_sugerencias.bind("<Tab>", lambda _e: self._usar_sugerencia(agregar=False))
        self.tree_sugerencias.bind("<Escape>", lambda _e: self._ocultar_sugerencias())

        # --- Carrito: todo el espacio restante ---
        cart_frame = card_frame(self, padx=2, pady=2)
        cart_frame.pack(fill="both", expand=True)
        head = tk.Frame(cart_frame, bg=BG_CARD)
        head.pack(fill="x", padx=6, pady=(2, 0))
        styled_label(head, "Productos en la venta", FONT_LABEL, CYAN, BG_CARD).pack(side="left")
        styled_label(head, "doble clic edita cantidad  ·  Supr quita", FONT_SMALL, TEXT_DIM, BG_CARD).pack(
            side="right"
        )

        self.tree_wrap, self.tree_venta = scrollable_tree(
            cart_frame,
            columns=(
                "N.Producto", "Codigo", "Producto", "Presentacion", "Cantidad",
                "Precio U", "PrecioTarj", "Subtotal", "SubTarj", "Factor", "PresId", "CantBase", "Iva",
            ),
            headings=(
                "N.°", "Código", "Producto", "Present.", "Cant.",
                "P. desc.", "P. +%", "Subt. desc.", "Subt. +%", "F", "Pid", "Base", "IVA",
            ),
            height=18,
            widths={
                "N.Producto": 52,
                "Codigo": 78,
                "Producto": 240,
                "Presentacion": 90,
                "Cantidad": 70,
                "Precio U": 110,
                "PrecioTarj": 110,
                "Subtotal": 120,
                "SubTarj": 120,
                "Iva": 80,
                "Factor": 1,
                "PresId": 1,
                "CantBase": 1,
            },
        )
        self.tree_venta.column("Producto", anchor="w")
        self.tree_venta["displaycolumns"] = (
            "N.Producto",
            "Codigo",
            "Producto",
            "Presentacion",
            "Cantidad",
            "Precio U",
            "PrecioTarj",
            "Subtotal",
            "SubTarj",
            "Iva",
        )
        self.tree_venta.tag_configure("con_iva", foreground=CYAN)
        self.tree_venta.tag_configure("sin_iva", foreground=TEXT)
        self.tree_wrap.pack(fill="both", expand=True, padx=4, pady=4)
        self.tree_venta.bind("<Delete>", lambda _e: self.cancelar_producto())
        self.tree_venta.bind("<Double-1>", self._editar_cantidad_item)
        self.tree_venta.bind("<F2>", self._editar_cantidad_item)
        self._ocultar_sugerencias()
        self.buscar_magico.focus_set()

    def _pct_recargo_actual(self):
        try:
            return float(pct_recargo_tarjeta())
        except (TypeError, ValueError):
            return 6.0

    def _montos_linea(self, precio_real, cantidad):
        try:
            precio_raw = float(precio_real or 0)
        except (TypeError, ValueError):
            precio_raw = 0.0
        try:
            cant = float(cantidad or 0)
        except (TypeError, ValueError):
            cant = 0.0
        pct = self._pct_recargo_actual()
        # Desc. y +% se calculan desde el precio real y ambos se llevan a centena.
        precio = float(redondear_centena(precio_raw))
        precio_tarj = float(precio_con_recargo(precio_raw, pct))
        return (
            precio,
            precio_tarj,
            float(redondear_centena(precio * cant)),
            float(redondear_centena(precio_tarj * cant)),
        )

    def _actualizar_encabezados_recargo(self):
        pct = self._pct_recargo_actual()
        try:
            self.tree_venta.heading("PrecioTarj", text="P. +{:.0f}%".format(pct))
            self.tree_venta.heading("SubTarj", text="Subt. +{:.0f}%".format(pct))
        except tk.TclError:
            pass

    def _parse_fila_venta(self, vals):
        """Lee una fila del carrito (layout nuevo o cuentas en espera antiguas)."""
        v = list(vals or [])
        if len(v) >= 12:
            cant_pres = float(v[4] or 0)
            cant_base = v[11] if len(v) > 11 and v[11] not in ("", None) else cant_pres
            return {
                "codigo": v[1],
                "nombre": v[2],
                "presentacion": v[3] if len(v) > 3 else "Unidad",
                "cantidad_pres": cant_pres,
                "precio": parse_dinero(v[5] if len(v) > 5 else 0),
                "precio_tarj": parse_dinero(v[6] if len(v) > 6 else 0),
                "subtotal": parse_dinero(v[7] if len(v) > 7 else 0),
                "sub_tarj": parse_dinero(v[8] if len(v) > 8 else 0),
                "factor": float(v[9] or 1) if len(v) > 9 else 1.0,
                "pres_id": v[10] if len(v) > 10 else None,
                "cant_base": float(cant_base or 0),
                "iva": v[12] if len(v) > 12 else "",
            }
        cant_pres = float(v[4] or 0) if len(v) > 4 else 0.0
        cant_base = v[9] if len(v) > 9 and v[9] not in ("", None) else cant_pres
        return {
            "codigo": v[1] if len(v) > 1 else "",
            "nombre": v[2] if len(v) > 2 else "",
            "presentacion": v[3] if len(v) > 3 else "Unidad",
            "cantidad_pres": cant_pres,
            "precio": parse_dinero(v[5] if len(v) > 5 else 0),
            "precio_tarj": 0.0,
            "subtotal": parse_dinero(v[6] if len(v) > 6 else 0),
            "sub_tarj": 0.0,
            "factor": float(v[7] or 1) if len(v) > 7 else 1.0,
            "pres_id": v[8] if len(v) > 8 else None,
            "cant_base": float(cant_base or 0),
            "iva": v[10] if len(v) > 10 else "",
        }

    def on_show(self):
        self._reset_cantidad()
        self._actualizar_encabezados_recargo()
        self.actualizar_total()
        self.buscar_magico.focus_set()
        if getattr(self, "_warmed", False):
            return
        self._warmed = True

        def ok(data):
            self._pres_map = (data or {}).get("pres") or {}

        def fetch():
            from Consultas import catalogo_productos, mapa_presentaciones
            catalogo_productos()
            return {"pres": mapa_presentaciones()}

        load_async(self, fetch, ok)

    def _fmt_cant(self, valor):
        try:
            numero = float(valor)
        except (TypeError, ValueError):
            return valor
        if abs(numero - round(numero)) < 1e-9:
            return int(round(numero))
        return round(numero, 4)

    def _texto_iva(self, iva):
        pct = iva_a_porcentaje(iva)
        if pct <= 0:
            return "Sin IVA"
        return "IVA {}".format(iva_a_texto(pct))

    def _mostrar_iva_producto(self, iva=None, encontrado=False):
        if not encontrado:
            self.lbl_iva_producto.config(text="IVA: —", fg=TEXT_DIM)
            return
        pct = iva_a_porcentaje(iva)
        if pct <= 0:
            self.lbl_iva_producto.config(text="IVA: no aplica (exento)", fg=TEXT_DIM)
        else:
            self.lbl_iva_producto.config(
                text="IVA: sí aplica  ·  {}%".format(iva_para_editar(pct)),
                fg=CYAN,
            )

    def _set_nombre_buscador(self, nombre):
        job = getattr(self, "_magic_job", None)
        if job:
            try:
                self.after_cancel(job)
            except Exception:
                pass
            self._magic_job = None
        self._silenciar_buscador = True
        self.buscar_magico.delete(0, tk.END)
        if nombre:
            self.buscar_magico.insert(0, nombre)
            self._nombre_autollenado = True
        else:
            self._nombre_autollenado = False
        self._silenciar_buscador = False
        self._ocultar_sugerencias()

    def _limpiar_entrada_producto(self):
        self._codigo_sel = ""
        self._pres_forzada = None
        self._set_nombre_buscador("")
        self._reset_cantidad()
        self._mostrar_iva_producto()
        self.buscar_magico.focus_set()

    def _enfocar_cantidad(self):
        self._asegurar_cantidad()
        self.cantidad_producto.focus_set()
        self.cantidad_producto.select_range(0, tk.END)
        try:
            self.cantidad_producto.icursor(tk.END)
        except tk.TclError:
            pass
        return "break"

    def _enter_cantidad(self, event=None):
        self.agregar_lista_venta()
        return "break"

    def _pres_por_barras(self, codigo):
        codigo = str(codigo or "").strip()
        if not codigo:
            return None
        for filas in (self._pres_map or {}).values():
            for pres in filas or []:
                if str(pres.get("codigo_barras") or "").strip() != codigo:
                    continue
                if not pres.get("activo", True) or not pres.get("permite_venta", True):
                    continue
                return pres
        return buscar_por_codigo_barras(codigo)

    def _producto_catalogo(self, pid):
        if catalogo_listo():
            for row in catalogo_productos() or []:
                datos = parse_producto(row)
                if datos and str(datos["id"]) == str(pid):
                    return datos
        producto = obtener_producto(pid)
        return parse_producto(producto) if producto else None

    def _parece_codigo_barras(self, texto):
        t = str(texto or "").strip()
        if len(t) < 6:
            return False
        compacto = t.replace("-", "").replace(" ", "")
        return compacto.isalnum() and any(ch.isdigit() for ch in compacto)

    def _buscar_producto_entrada(self, codigo):
        codigo = str(codigo or "").strip()
        if not codigo:
            return None, None
        if self._parece_codigo_barras(codigo):
            pres_scan = self._pres_por_barras(codigo)
            if pres_scan:
                datos = self._producto_catalogo(pres_scan["producto_id"])
                if datos:
                    return datos, pres_scan
        if codigo.isdigit():
            datos = self._producto_catalogo(int(codigo))
            if datos:
                return datos, None
            pres_scan = self._pres_por_barras(codigo)
            if pres_scan:
                datos = self._producto_catalogo(pres_scan["producto_id"])
                if datos:
                    return datos, pres_scan
        t = codigo.lower()
        if catalogo_listo():
            for row in catalogo_productos() or []:
                datos = parse_producto(row)
                if datos and str(datos.get("nombre") or "").strip().lower() == t:
                    return datos, None
        return None, None

    def _pintar_sugerencias(self, resultados):
        self.tree_sugerencias.delete(*self.tree_sugerencias.get_children())
        pct = self._pct_recargo_actual()
        try:
            self.tree_sugerencias.heading("PrecioTarj", text="P. +{:.0f}%".format(pct))
        except tk.TclError:
            pass
        for row in resultados or []:
            datos = parse_producto(row)
            if not datos:
                continue
            precio = float(redondear_centena(datos["precio_venta"] or 0))
            self.tree_sugerencias.insert(
                "",
                "end",
                values=(
                    datos["id"],
                    datos["nombre"],
                    formato_dinero(precio),
                    formato_dinero(precio_con_recargo(datos["precio_venta"] or 0, pct)),
                    self._texto_iva(datos.get("iva")),
                    datos["cantidad"],
                    datos["marca"],
                ),
                tags=("con_iva",) if iva_a_porcentaje(datos.get("iva")) > 0 else ("sin_iva",),
            )
        if self.tree_sugerencias.get_children():
            self._mostrar_sugerencias()
            first = self.tree_sugerencias.get_children()[0]
            self.tree_sugerencias.selection_set(first)
            self.tree_sugerencias.focus(first)
        else:
            self._ocultar_sugerencias()

    def _aplicar_filtro_magico(self):
        if getattr(self, "_silenciar_buscador", False):
            return
        texto = self.buscar_magico.get().strip()
        if not texto:
            self._ocultar_sugerencias()
            return
        resultados = list(buscar_productos_rapido(texto) if catalogo_listo() else [])
        exacto, _pres = self._buscar_producto_entrada(texto)
        if exacto:
            filas = []
            for row in catalogo_productos() or []:
                datos = parse_producto(row)
                if datos and str(datos["id"]) == str(exacto["id"]):
                    filas.append(row)
                    break
            if filas:
                ids = {str(exacto["id"])}
                extra = []
                for row in resultados:
                    datos = parse_producto(row)
                    if datos and str(datos["id"]) not in ids:
                        extra.append(row)
                resultados = filas + extra
        if resultados:
            self._pintar_sugerencias(resultados)
            return
        t = texto
        load_async(self, lambda: buscar_productos_rapido(t), self._pintar_sugerencias)

    def _reset_cantidad(self):
        self.cantidad_producto.delete(0, tk.END)
        self.cantidad_producto.insert(0, "1")

    def _asegurar_cantidad(self):
        if not self.cantidad_producto.get().strip():
            self._reset_cantidad()

    def _cantidad_valida(self):
        self._asegurar_cantidad()
        texto = self.cantidad_producto.get().strip().replace(",", ".")
        try:
            valor = float(texto)
        except ValueError:
            return None
        if valor <= 0:
            return None
        return valor

    def validar_numero(self, texto):
        return texto == "" or texto.isdigit()

    def validar_cantidad(self, texto):
        if texto == "":
            return True
        if not texto.isdigit():
            return False
        return True

    def _ocultar_sugerencias(self, event=None):
        self.tree_sugerencias.delete(*self.tree_sugerencias.get_children())
        self.suggest_card.pack_forget()
        return "break"

    def _mostrar_sugerencias(self):
        if not self.suggest_card.winfo_ismapped():
            self.suggest_card.pack(fill="x", pady=(0, 4), after=self.scan)

    def _filtrar_magico(self, event=None):
        if getattr(self, "_silenciar_buscador", False):
            return
        if event and event.keysym in ("Return", "Tab", "Up", "Down", "Escape", "KP_Enter"):
            return
        self._nombre_autollenado = False
        debounce(self, "_magic_job", 140, self._aplicar_filtro_magico)

    def _enfocar_sugerencias(self, event=None):
        if not self.tree_sugerencias.get_children():
            self._aplicar_filtro_magico()
        if self.tree_sugerencias.get_children():
            self._mostrar_sugerencias()
            self.tree_sugerencias.focus_set()
            item = self.tree_sugerencias.selection() or self.tree_sugerencias.get_children()[:1]
            if item:
                self.tree_sugerencias.selection_set(item[0])
                self.tree_sugerencias.focus(item[0])
        return "break"

    def _enter_magico(self, event=None):
        texto = self.buscar_magico.get().strip()
        if not texto:
            return "break"
        if self._resolver_desde_texto(texto):
            return self._enfocar_cantidad()
        if not self.tree_sugerencias.get_children():
            self._aplicar_filtro_magico()
        if self.tree_sugerencias.get_children():
            self._usar_sugerencia(agregar=False)
        return "break"

    def _resolver_desde_texto(self, texto):
        datos, pres_scan = self._buscar_producto_entrada(texto)
        if not datos:
            return False
        self._codigo_sel = str(datos["id"])
        self._pres_forzada = pres_scan
        self._set_nombre_buscador(datos["nombre"])
        self._cargar_presentaciones(datos["id"], pres_scan)
        self._mostrar_iva_producto(datos.get("iva"), encontrado=True)
        return True

    def _usar_sugerencia(self, agregar=False):
        sel = self.tree_sugerencias.selection() or self.tree_sugerencias.get_children()[:1]
        if not sel:
            return "break"
        valores = self.tree_sugerencias.item(sel[0], "values")
        codigo = valores[0]
        nombre = valores[1] if len(valores) > 1 else ""
        self._codigo_sel = str(codigo)
        self._pres_forzada = None
        self._cargar_presentaciones(codigo)
        self._set_nombre_buscador(nombre)
        self._asegurar_cantidad()
        iva = None
        if catalogo_listo():
            for row in catalogo_productos() or []:
                datos = parse_producto(row)
                if datos and str(datos["id"]) == str(codigo):
                    iva = datos.get("iva")
                    break
        if iva is None:
            producto = obtener_producto(codigo)
            datos = parse_producto(producto) if producto else None
            iva = (datos or {}).get("iva")
        self._mostrar_iva_producto(iva, encontrado=True)
        if agregar:
            self.agregar_lista_venta()
        else:
            self._enfocar_cantidad()
        return "break"

    def abrir_cobrar(self, event=None):
        if self.shell.cobro_overlay is not None:
            return
        self.calcular_total_articulos()
        productos_comprado = []
        for fila in self.tree_venta.get_children():
            f = self._parse_fila_venta(self.tree_venta.item(fila, "values"))
            productos_comprado.append(
                {
                    "codigo": f["codigo"],
                    "cantidad": f["cant_base"],
                    "cantidad_presentacion": f["cantidad_pres"],
                    "subtotal": f["subtotal"],
                    "subtotal_tarjeta": f["sub_tarj"],
                    "nombre": f["nombre"],
                    "precio": f["precio"],
                    "precio_tarjeta": f["precio_tarj"],
                    "presentacion": f["presentacion"],
                    "factor": f["factor"],
                    "presentacion_id": f["pres_id"],
                }
            )
        if not productos_comprado:
            mb.showerror("Error", "Tiene que haber un producto ingresado en la lista", parent=self)
            return
        from cobrar import CobrarOverlay
        overlay = CobrarOverlay(
            self.shell,
            self.total_ventas,
            self.total_articulos,
            self.id_empleado,
            productos_comprado,
            on_success=self._despues_cobro,
            on_close=lambda: self.shell.set_cobro_overlay(None),
            cliente=self.cliente,
            usuario=self.usuario,
            total_tarjeta=getattr(self, "total_tarjeta", None),
        )
        self.shell.set_cobro_overlay(overlay)

    def _despues_cobro(self, info=None):
        if info:
            app = self.shell.app
            if not hasattr(app, "ventas_turno") or app.ventas_turno is None:
                app.ventas_turno = []
            app.ventas_turno.append(info)
            if mb.askyesno("Ticket", "¿Desea imprimir el ticket térmico?", parent=self):
                try:
                    from ticket import imprimir_ticket_venta
                    path, _texto = imprimir_ticket_venta(
                        info,
                        cajero=self.empleado,
                        ancho_mm=info.get("ancho_mm", 80),
                    )
                    mb.showinfo("Ticket", f"Ticket enviado a impresión.\n{path}", parent=self)
                except Exception as error:
                    mb.showerror("Error", f"No se pudo imprimir el ticket: {error}", parent=self)
        self.limpiar_treeview()
        self.actualizar_total()
        self._quitar_cliente()
        self._limpiar_entrada_producto()
        self.shell.set_cobro_overlay(None)

    def _presentacion_elegida(self):
        nombre = (self.presentacion.get() or "").strip()
        for item in self._pres_opciones:
            if item.get("nombre") == nombre:
                return item
        return self._pres_opciones[0] if self._pres_opciones else None

    def _cargar_presentaciones(self, producto_id, pres_forzada=None):
        pid = None
        try:
            pid = int(producto_id)
        except (TypeError, ValueError):
            pid = producto_id
        cached = (self._pres_map or {}).get(pid)
        if cached:
            self._pres_opciones = [p for p in cached if p.get("activo") and p.get("permite_venta")]
        else:
            self._pres_opciones = listar_presentaciones(producto_id, solo_venta=True) or []
        nombres = [p["nombre"] for p in self._pres_opciones]
        self.presentacion["values"] = nombres
        if pres_forzada and pres_forzada.get("nombre") in nombres:
            self.presentacion.set(pres_forzada["nombre"])
        elif nombres:
            def_p = None
            for fila in self._pres_opciones:
                if fila.get("es_default"):
                    def_p = fila
                    break
            if def_p is None:
                for fila in self._pres_opciones:
                    if abs(float(fila.get("factor") or 1) - 1) < 0.0000001:
                        def_p = fila
                        break
            self.presentacion.set((def_p or self._pres_opciones[0])["nombre"])
        else:
            self.presentacion.set("Unidad")
            self._pres_opciones = [{"id": None, "nombre": "Unidad", "factor": 1, "precio_venta": 0, "utilidad_pct": 0}]

    def agregar_lista_venta(self):
        Codigo = str(self._codigo_sel or "").strip()
        if not Codigo:
            texto = self.buscar_magico.get().strip()
            if texto and self._resolver_desde_texto(texto):
                Codigo = str(self._codigo_sel or "").strip()
        Cantidad = self._cantidad_valida()

        if not Codigo:
            mb.showerror("Error", "Ingrese o seleccione un producto.", parent=self)
            self.buscar_magico.focus_set()
            return

        if Cantidad is None:
            mb.showerror("Error", "La cantidad debe ser un número mayor a 0.", parent=self)
            self._reset_cantidad()
            self.cantidad_producto.focus_set()
            return

        pres_scan = self._pres_forzada
        producto = None
        if Codigo.isdigit():
            producto = obtener_producto(int(Codigo))
        if not producto:
            pres_scan = pres_scan or buscar_por_codigo_barras(Codigo)
            if pres_scan:
                producto = obtener_producto(pres_scan["producto_id"])
                Codigo = str(pres_scan["producto_id"])
        if not producto:
            mb.showerror("Error", "El producto no existe. Revise el código o el código de barras.", parent=self)
            self._limpiar_entrada_producto()
            return

        Codigo = int(parse_producto(producto)["id"])
        self._cargar_presentaciones(Codigo, pres_scan)
        pres = pres_scan if pres_scan and pres_scan.get("permite_venta", True) else self._presentacion_elegida()
        if not pres:
            mb.showerror("Presentación", "Este producto no tiene una presentación habilitada para venta.", parent=self)
            return
        if not pres.get("permite_venta", True):
            mb.showerror("Presentación", "Esa presentación no está habilitada para venta.", parent=self)
            return
        factor = float(pres.get("factor") or 1) or 1
        cantidad_base = a_unidades_base(Cantidad, factor)
        cantidad_disponible = cantidad_producto(Codigo)
        receta = obtener_receta(Codigo)
        datos = parse_producto(producto)
        nombre_producto = datos["nombre"]
        Precio_Unitario = float(pres.get("precio_venta") or datos["precio_venta"] or 0)
        stock_min = datos["stock_minimo"]
        pres_id = pres.get("id")
        pres_nombre = pres.get("nombre") or "Unidad"

        for item in self.tree_venta.get_children():
            vals = self.tree_venta.item(item, "values")
            f = self._parse_fila_venta(vals)
            mismo_prod = str(f["codigo"]) == str(Codigo)
            misma_pres = str(f["pres_id"] or "") == str(pres_id or "")
            if mismo_prod and misma_pres:
                try:
                    actual = float(f["cantidad_pres"] or 0)
                except (TypeError, ValueError):
                    actual = 0
                if self._aplicar_cantidad_item(item, actual + Cantidad):
                    self._limpiar_entrada_producto()
                return

        if receta:
            faltantes = validar_insumos(Codigo, cantidad_base)
            if faltantes:
                mb.showwarning(
                    "Insumos insuficientes",
                    "No hay insumos para armar este producto:\n- " + "\n- ".join(faltantes),
                    parent=self,
                )
                self.cantidad_producto.focus_set()
                return
        elif cantidad_disponible is None or (
            self._base_producto_en_carrito(Codigo) + cantidad_base
        ) > float(cantidad_disponible or 0) + 0.0001:
            mb.showwarning(
                "Advertencia",
                "Stock insuficiente. Pide {:.4g} {} ({:.4g} unidades base) y hay {}.".format(
                    Cantidad, pres.get("nombre"), cantidad_base, cantidad_disponible
                ),
                parent=self,
            )
            self.cantidad_producto.focus_set()
            return

        subtotal = Precio_Unitario * Cantidad
        _p, precio_tarj, _s, sub_tarj = self._montos_linea(Precio_Unitario, Cantidad)

        if len(self.tree_venta.get_children()) == 0:
            numero_producto = 1
        else:
            ultimo_item = self.tree_venta.get_children()[-1]
            ultimo_numero = int(self.tree_venta.item(ultimo_item, "values")[0])
            numero_producto = ultimo_numero + 1

        iva_txt = self._texto_iva(datos.get("iva"))
        iva_tag = ("con_iva",) if iva_a_porcentaje(datos.get("iva")) > 0 else ("sin_iva",)

        self.tree_venta.insert(
            "",
            tk.END,
            values=(
                numero_producto,
                Codigo,
                nombre_producto,
                pres_nombre,
                self._fmt_cant(Cantidad),
                formato_dinero(Precio_Unitario),
                formato_dinero(precio_tarj),
                formato_dinero(subtotal),
                formato_dinero(sub_tarj),
                factor,
                pres_id or "",
                cantidad_base,
                iva_txt,
            ),
            tags=iva_tag,
        )
        self._limpiar_entrada_producto()
        self.actualizar_total()

        if not receta and cantidad_disponible is not None:
            try:
                if float(cantidad_disponible) - cantidad_base <= float(stock_min or 0):
                    mb.showinfo(
                        "Reabastecimiento necesario",
                        "El stock de '{}' está bajo (restan {} unidades base; mínimo {}).".format(
                            nombre_producto, float(cantidad_disponible) - cantidad_base, stock_min
                        ),
                        parent=self,
                    )
            except (TypeError, ValueError):
                pass

    def _base_producto_en_carrito(self, codigo, except_item=None):
        total = 0.0
        for item in self.tree_venta.get_children():
            if except_item and item == except_item:
                continue
            f = self._parse_fila_venta(self.tree_venta.item(item, "values"))
            if str(f["codigo"]) != str(codigo):
                continue
            total += float(f["cant_base"] or 0)
        return total

    def _editar_cantidad_item(self, event=None):
        self._cerrar_editor_cantidad(commit=False)
        item = None
        if event is not None and getattr(event, "y", None) is not None:
            item = self.tree_venta.identify_row(event.y)
        if not item:
            sel = self.tree_venta.selection()
            item = sel[0] if sel else None
        if not item:
            return "break"
        self.tree_venta.selection_set(item)
        self.tree_venta.see(item)
        bbox = self.tree_venta.bbox(item, "Cantidad")
        if not bbox:
            return "break"
        x, y, w, h = bbox
        valores = self.tree_venta.item(item, "values")
        actual = str(valores[4] if len(valores) > 4 else "1")
        editor = tk.Entry(
            self.tree_venta,
            font=FONT_BODY,
            bg=BG_INPUT,
            fg=TEXT,
            insertbackground=TEXT,
            relief="solid",
            bd=1,
            highlightthickness=1,
            highlightbackground=ACCENT,
            highlightcolor=ACCENT,
        )
        editor.place(x=x, y=y, width=max(int(w), 58), height=h)
        editor.insert(0, actual)
        editor.select_range(0, tk.END)
        editor.focus_set()
        self._qty_editor = editor
        self._qty_item = item

        def confirmar(_e=None):
            self._cerrar_editor_cantidad(commit=True)
            return "break"

        def cancelar(_e=None):
            self._cerrar_editor_cantidad(commit=False)
            return "break"

        editor.bind("<Return>", confirmar)
        editor.bind("<KP_Enter>", confirmar)
        editor.bind("<Tab>", confirmar)
        editor.bind("<Escape>", cancelar)
        editor.bind("<FocusOut>", lambda _e: self._cerrar_editor_cantidad(commit=True))
        return "break"

    def _cerrar_editor_cantidad(self, commit=False):
        if getattr(self, "_cerrando_qty", False):
            return
        editor = getattr(self, "_qty_editor", None)
        item = getattr(self, "_qty_item", None)
        if editor is None:
            return
        self._cerrando_qty = True
        texto = ""
        try:
            texto = editor.get()
        except tk.TclError:
            texto = ""
        try:
            editor.place_forget()
            editor.destroy()
        except tk.TclError:
            pass
        self._qty_editor = None
        self._qty_item = None
        self._cerrando_qty = False
        if commit and item and self.tree_venta.exists(item):
            self._aplicar_cantidad_item(item, texto)

    def _aplicar_cantidad_item(self, item, texto):
        if not item or not self.tree_venta.exists(item):
            return False
        bruto = str(texto or "").strip().replace(",", ".")
        try:
            nueva = float(bruto)
        except (TypeError, ValueError):
            mb.showerror("Cantidad", "La cantidad debe ser un número mayor a 0.", parent=self)
            return False
        if nueva <= 0:
            mb.showerror("Cantidad", "La cantidad debe ser un número mayor a 0.", parent=self)
            return False
        vals = list(self.tree_venta.item(item, "values"))
        f = self._parse_fila_venta(vals)
        try:
            codigo = int(f["codigo"])
        except (TypeError, ValueError):
            return False
        factor = float(f["factor"] or 1) or 1
        precio = float(f["precio"] or 0)
        nueva_base = a_unidades_base(nueva, factor)
        receta = obtener_receta(codigo)
        if receta:
            faltantes = validar_insumos(codigo, nueva_base)
            if faltantes:
                mb.showwarning(
                    "Insumos insuficientes",
                    "No hay insumos para armar este producto:\n- " + "\n- ".join(faltantes),
                    parent=self,
                )
                return False
        else:
            disponible = cantidad_producto(codigo)
            pedida = self._base_producto_en_carrito(codigo, except_item=item) + nueva_base
            if disponible is None or pedida > float(disponible or 0) + 0.0001:
                mb.showwarning(
                    "Advertencia",
                    "Stock insuficiente. Pide {:.4g} y hay {} unidades base.".format(
                        nueva_base, disponible
                    ),
                    parent=self,
                )
                return False
        _p, precio_tarj, subtotal, sub_tarj = self._montos_linea(precio, nueva)
        self.tree_venta.item(
            item,
            values=(
                vals[0] if vals else 1,
                f["codigo"],
                f["nombre"],
                f["presentacion"],
                self._fmt_cant(nueva),
                formato_dinero(precio),
                formato_dinero(precio_tarj),
                formato_dinero(subtotal),
                formato_dinero(sub_tarj),
                factor,
                f["pres_id"] or "",
                nueva_base,
                f.get("iva") or "",
            ),
        )
        self.actualizar_total()
        return True

    def actualizar_total(self):
        total = 0.00
        total_tarj = 0.00
        pct = self._pct_recargo_actual()
        for fila in self.tree_venta.get_children():
            f = self._parse_fila_venta(self.tree_venta.item(fila, "values"))
            total += float(f["subtotal"] or 0)
            sub_t = float(f["sub_tarj"] or 0)
            if sub_t <= 0 and f["subtotal"]:
                sub_t = float(precio_con_recargo(f["subtotal"], pct))
            total_tarj += sub_t
        total = float(redondear_centena(total))
        total_tarj = float(redondear_centena(total_tarj))
        self.cobro.config(text=formato_dinero(total))
        if hasattr(self, "cobro_tarj"):
            self.cobro_tarj.config(
                text="Tarjeta (+{:.0f}%) {}".format(pct, formato_dinero(total_tarj))
            )
        self.total_ventas = total
        self.total_tarjeta = total_tarj
        self._actualizar_encabezados_recargo()

    def _asociar_cliente(self):
        from clientes_cxc import SelectorCliente
        SelectorCliente(self.winfo_toplevel(), self._set_cliente)

    def _set_cliente(self, cliente):
        self.cliente = cliente
        self.lbl_cliente.config(
            text=f"Cliente: {cliente['nombre']}  ·  saldo {formato_dinero(cliente['saldo'])}  ·  {cliente['puntos']} pts",
            fg=CYAN,
        )

    def _quitar_cliente(self):
        self.cliente = None
        self.lbl_cliente.config(text="Cliente: mostrador", fg=TEXT_MUTED)

    def cancelar_producto(self, event=None):
        from auditoria import log_accion
        producto_seleccionado = self.tree_venta.selection()
        if not producto_seleccionado:
            return
        for item in producto_seleccionado:
            valores = self.tree_venta.item(item, "values")
            log_accion(
                self.usuario,
                "Canceló producto del carrito",
                f"Código {valores[1]} {valores[2]} x{valores[3]}",
            )
            self.tree_venta.delete(item)
        self.actualizar_total()
        self.buscar_magico.focus_set()

    def cancelar_venta(self):
        from auditoria import log_accion
        productos = self.tree_venta.get_children()
        if mb.askyesno("Confirmar", "¿Desea cancelar la venta?", parent=self):
            log_accion(self.usuario, "Canceló venta", f"{len(productos)} ítems por {formato_dinero(self.total_ventas)}")
            for items in productos:
                self.tree_venta.delete(items)
            self.actualizar_total()
            self._limpiar_entrada_producto()

    def calcular_total_articulos(self):
        self.total_articulos = 0
        for fila in self.tree_venta.get_children():
            try:
                self.total_articulos += float(
                    self._parse_fila_venta(self.tree_venta.item(fila, "values"))["cantidad_pres"] or 0
                )
            except (TypeError, ValueError):
                pass

    def limpiar_treeview(self):
        for item in self.tree_venta.get_children():
            self.tree_venta.delete(item)

    def _snapshot(self):
        return [self.tree_venta.item(item, "values") for item in self.tree_venta.get_children()]

    def _normalizar_item_carrito(self, item):
        f = self._parse_fila_venta(item)
        precio, precio_tarj, subtotal, sub_tarj = self._montos_linea(f["precio"], f["cantidad_pres"])
        if float(f["subtotal"] or 0) > 0:
            subtotal = float(f["subtotal"])
            if float(f["sub_tarj"] or 0) > 0:
                sub_tarj = float(f["sub_tarj"])
            else:
                sub_tarj = float(precio_con_recargo(subtotal, self._pct_recargo_actual()))
        numero = item[0] if item else 1
        return (
            numero,
            f["codigo"],
            f["nombre"],
            f["presentacion"],
            self._fmt_cant(f["cantidad_pres"]),
            formato_dinero(precio),
            formato_dinero(precio_tarj),
            formato_dinero(subtotal),
            formato_dinero(sub_tarj),
            f["factor"],
            f["pres_id"] or "",
            f["cant_base"],
            f.get("iva") or "",
        )

    def _cargar_items(self, items):
        self.limpiar_treeview()
        for item in items:
            self.tree_venta.insert("", tk.END, values=self._normalizar_item_carrito(item))
        self.actualizar_total()

    def _actualizar_boton_espera(self):
        self.btn_recuperar.config(text=f"Recuperar ({len(self.cuentas_espera)})")

    def poner_en_espera(self, silent=False):
        items = self._snapshot()
        if not items:
            if not silent:
                mb.showwarning("En espera", "No hay productos en la cuenta actual.", parent=self)
            return False
        self.calcular_total_articulos()
        self.cuentas_espera.append(
            {
                "id": len(self.cuentas_espera) + 1,
                "hora": datetime.now().strftime("%H:%M"),
                "items": items,
                "total": self.total_ventas,
                "articulos": self.total_articulos,
                "cliente": self.cliente,
            }
        )
        self.limpiar_treeview()
        self.actualizar_total()
        self._actualizar_boton_espera()
        self.buscar_magico.focus_set()
        if not silent:
            mb.showinfo("En espera", "La cuenta quedó congelada. Puede atender a otro cliente.", parent=self)
        return True

    def recuperar_cuenta(self):
        if not self.cuentas_espera:
            mb.showinfo("En espera", "No hay cuentas congeladas.", parent=self)
            return
        if self.tree_venta.get_children():
            if not mb.askyesno(
                "Cuenta actual",
                "Hay una venta en curso. ¿Enviarla a espera y recuperar otra?",
                parent=self,
            ):
                return
            self.poner_en_espera(silent=True)
        self._abrir_lista_espera()

    def _abrir_lista_espera(self):
        dlg = tk.Toplevel(self)
        prepare_modal(dlg, self, "Cuentas en espera", 460, 360)
        card = card_frame(dlg, padx=20, pady=18)
        card.pack(fill="both", expand=True)
        styled_label(card, "Seleccione una cuenta", FONT_HEADING, TEXT, BG_CARD).pack(anchor="w", pady=(0, 10))
        lista = tk.Listbox(
            card,
            bg=BG_INPUT,
            fg=TEXT,
            selectbackground=ACCENT,
            font=FONT_BODY,
            relief="flat",
            highlightthickness=0,
        )
        lista.pack(fill="both", expand=True)
        for i, cuenta in enumerate(self.cuentas_espera):
            lista.insert("end", f"#{cuenta['id']}  {cuenta['hora']}  ·  {cuenta['articulos']} art.  ·  {formato_dinero(cuenta['total'])}")

        def cargar():
            seleccion = lista.curselection()
            if not seleccion:
                mb.showwarning("En espera", "Seleccione una cuenta.", parent=dlg)
                return
            cuenta = self.cuentas_espera.pop(seleccion[0])
            self._cargar_items(cuenta["items"])
            if cuenta.get("cliente"):
                self._set_cliente(cuenta["cliente"])
            else:
                self._quitar_cliente()
            self._actualizar_boton_espera()
            dlg.destroy()
            self.buscar_magico.focus_set()

        primary_button(card, "Recuperar", cargar, width=18).pack(pady=(12, 0))
        lista.bind("<Double-1>", lambda _e: cargar())
        lista.bind("<Return>", lambda _e: cargar())
        if self.cuentas_espera:
            lista.selection_set(0)
            lista.focus_set()
