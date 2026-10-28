import tkinter as tk
from tkinter import ttk
import mensaje as mb
import Consultas
from zyntra_ui import *


class KardexProducto:
    """Consulta el kardex de un producto: movimientos, compras a proveedor y ventas."""

    def __init__(self, parent=None, codigo_inicial=None):
        self.win = tk.Toplevel(parent) if parent else tk.Toplevel()
        prepare_modal(self.win, parent, "Kardex de producto", 1100, 820, resizable=True)
        limit_minsize(self.win, 860, 620)
        self._producto = None
        self._resultados = []
        self.items()
        try:
            Consultas.catalogo_productos()
        except Exception:
            pass
        if codigo_inicial:
            self.codigo.insert(0, str(codigo_inicial))
            self._buscar(auto_abrir=True)
        else:
            self._buscar(auto_abrir=False)
        self.win.after(120, self._expandir_tablas)

    def items(self):
        footer = card_frame(self.win, padx=12, pady=8)
        footer.pack(side="bottom", fill="x", padx=10, pady=(0, 10))
        danger_button(footer, "Cerrar", self.win.destroy, width=14, height=1).pack(side="right")

        body = tk.Frame(self.win, bg=BG)
        body.pack(fill="both", expand=True, padx=10, pady=(10, 6))

        card = card_frame(body, padx=12, pady=8)
        card.pack(fill="both", expand=True)

        # --- Zona superior compacta (no crece) ---
        top = tk.Frame(card, bg=BG_CARD)
        top.pack(side="top", fill="x")

        styled_label(top, "Kardex de producto", FONT_HEADING, TEXT, BG_CARD).pack(anchor="w")
        styled_label(
            top,
            "Busque por código o nombre y seleccione el producto.",
            FONT_SMALL,
            TEXT_DIM,
            BG_CARD,
        ).pack(anchor="w", pady=(0, 4))

        row = tk.Frame(top, bg=BG_CARD)
        row.pack(fill="x")
        box, self.codigo = labeled_field(row, "Código o nombre")
        box.pack(side="left", fill="x", expand=True, padx=(0, 8))
        primary_button(row, "Buscar", lambda: self._buscar(auto_abrir=True), width=10, font=FONT_SMALL).pack(
            side="left", pady=(16, 0)
        )
        self.codigo.bind("<KeyRelease>", lambda _e: self._buscar(auto_abrir=False))
        self.codigo.bind("<Return>", lambda _e: self._buscar(auto_abrir=True))

        styled_label(top, "Resultados  ·  doble clic o Enter", FONT_LABEL, TEXT_MUTED, BG_CARD).pack(
            anchor="w", pady=(4, 2)
        )
        res_box = tk.Frame(top, bg=BG_CARD, height=92)
        res_box.pack(fill="x")
        res_box.pack_propagate(False)
        self.res_wrap, self.tree_res = scrollable_tree(
            res_box,
            columns=("Codigo", "Nombre", "Stock", "Proveedor", "PVenta"),
            headings=("Cód.", "Producto", "Existencia", "Proveedor", "P. venta"),
            height=2,
            widths={"Codigo": 72, "Nombre": 420, "Stock": 90, "Proveedor": 180, "PVenta": 100},
            minwidths={"Codigo": 60, "Nombre": 220, "Stock": 70, "Proveedor": 100, "PVenta": 80},
        )
        # Producto ocupa el espacio sobrante; el resto queda fijo y legible
        self.tree_res.column("Codigo", width=72, minwidth=60, stretch=False, anchor="center")
        self.tree_res.column("Nombre", width=420, minwidth=220, stretch=True, anchor="w")
        self.tree_res.column("Stock", width=90, minwidth=70, stretch=False, anchor="center")
        self.tree_res.column("Proveedor", width=180, minwidth=100, stretch=False, anchor="w")
        self.tree_res.column("PVenta", width=100, minwidth=80, stretch=False, anchor="e")
        self.tree_res.heading("Nombre", anchor="w")
        self.tree_res.heading("Proveedor", anchor="w")
        self.res_wrap.pack(fill="both", expand=True)
        self.tree_res.bind("<<TreeviewSelect>>", self._seleccion_resultado)
        self.tree_res.bind("<Double-1>", lambda _e: self._abrir_seleccion())
        self.tree_res.bind("<Return>", lambda _e: self._abrir_seleccion())
        self.res_wrap.bind("<Configure>", self._ajustar_cols_resultados)

        info = tk.Frame(top, bg=BG_ELEVATED, padx=10, pady=4)
        info.pack(fill="x", pady=(4, 2))
        self.lbl_prod = styled_label(info, "Seleccione un producto de la lista.", FONT_SUB, TEXT, BG_ELEVATED)
        self.lbl_prod.pack(anchor="w")
        self.lbl_detalle = styled_label(info, "", FONT_SMALL, TEXT_DIM, BG_ELEVATED)
        self.lbl_detalle.pack(anchor="w")
        self.lbl_proveedor = styled_label(info, "", ("Segoe UI", 11, "bold"), CYAN, BG_ELEVATED)
        self.lbl_proveedor.pack(anchor="w")

        # --- Zona inferior: movimientos / compras / ventas (ocupa el resto) ---
        self.nb = ttk.Notebook(card)
        self.nb.pack(side="top", fill="both", expand=True, pady=(2, 0))

        tab_mov = tk.Frame(self.nb, bg=BG_CARD)
        tab_com = tk.Frame(self.nb, bg=BG_CARD)
        tab_ven = tk.Frame(self.nb, bg=BG_CARD)
        self.nb.add(tab_mov, text="  Movimientos  ")
        self.nb.add(tab_com, text="  Compras / proveedor  ")
        self.nb.add(tab_ven, text="  Ventas  ")
        self._tabs = (tab_mov, tab_com, tab_ven)

        self.mov_wrap, self.tree_mov = scrollable_tree(
            tab_mov,
            columns=("Fecha", "Tipo", "Cant", "Factor", "Base", "Motivo", "Usuario"),
            headings=("Fecha", "Tipo", "Cant.", "Conv.", "Base", "Detalle", "Usuario"),
            height=22,
            widths={"Fecha": 155, "Tipo": 90, "Cant": 70, "Factor": 55, "Base": 70, "Motivo": 280, "Usuario": 90},
        )
        self.tree_mov.column("Fecha", width=155, minwidth=140, stretch=False, anchor="w")
        self.tree_mov.column("Motivo", width=280, minwidth=160, stretch=True, anchor="w")
        self.tree_mov.column("Usuario", width=90, minwidth=70, stretch=False, anchor="center")
        self.mov_wrap.pack(fill="both", expand=True, padx=2, pady=2)

        self.com_wrap, self.tree_com = scrollable_tree(
            tab_com,
            columns=("Fecha", "Factura", "Proveedor", "Present", "Cant", "Base", "Costo", "Total", "Usuario"),
            headings=("Fecha", "Factura", "Proveedor", "Present.", "Cant.", "Base", "Costo U.", "Total", "Usuario"),
            height=22,
            widths={
                "Fecha": 120,
                "Factura": 90,
                "Proveedor": 140,
                "Present": 80,
                "Cant": 55,
                "Base": 60,
                "Costo": 80,
                "Total": 90,
                "Usuario": 80,
            },
        )
        self.tree_com.column("Proveedor", anchor="w")
        self.com_wrap.pack(fill="both", expand=True, padx=2, pady=2)

        self.ven_wrap, self.tree_ven = scrollable_tree(
            tab_ven,
            columns=("Fecha", "Present", "Cant", "Precio", "Subtotal", "Usuario"),
            headings=("Fecha", "Present.", "Cant.", "P. unit.", "Subtotal", "Cajero"),
            height=22,
            widths={"Fecha": 130, "Present": 90, "Cant": 60, "Precio": 90, "Subtotal": 100, "Usuario": 100},
        )
        self.ven_wrap.pack(fill="both", expand=True, padx=2, pady=2)

        self.nb.bind("<Configure>", self._expandir_tablas)
        self.win.bind("<Configure>", self._expandir_tablas)
        self.codigo.focus_set()

    def _ajustar_cols_resultados(self, event=None):
        """Da el ancho sobrante a la columna Producto para ver el nombre completo."""
        try:
            total = int(self.res_wrap.winfo_width() or 0) - 22  # scrollbar
        except tk.TclError:
            return
        if total < 400:
            return
        fijos = 72 + 90 + 180 + 100
        nombre_w = max(220, total - fijos)
        try:
            self.tree_res.column("Nombre", width=nombre_w, stretch=True, anchor="w")
        except tk.TclError:
            pass

    def _expandir_tablas(self, event=None):
        if event is not None and event.widget not in (self.win, self.nb):
            return
        try:
            self.win.update_idletasks()
            h = int(self.nb.winfo_height() or 0)
        except tk.TclError:
            return
        if h < 140:
            return
        # Altura útil del área de pestañas (resta la franja de tabs)
        rows = max(14, min(32, (h - 52) // 34))
        for tree in (self.tree_mov, self.tree_com, self.tree_ven):
            try:
                if int(str(tree.cget("height"))) != rows:
                    tree.configure(height=rows)
            except tk.TclError:
                pass

    def _buscar_filas(self, texto):
        texto = (texto or "").strip()
        filas = []
        if not texto:
            # Catálogo completo (primeros) para que siempre se vean productos
            try:
                filas = list(Consultas.catalogo_productos() or [])[:80]
            except Exception:
                filas = []
            if not filas:
                filas = list(Consultas.mostrar_Productos() or [])[:80]
            return filas

        if texto.isdigit():
            row = Consultas.obtener_producto(texto)
            if row:
                return [row]

        try:
            filas = list(Consultas.buscar_productos_rapido(texto, limite=40) or [])
        except Exception:
            filas = []
        if not filas:
            try:
                filas = list(Consultas.buscar_productos(texto, texto, texto) or [])
            except Exception:
                filas = []
        return filas

    def _buscar(self, auto_abrir=False):
        try:
            texto = self.codigo.get().strip()
            filas = self._buscar_filas(texto)
            self._resultados = []
            self.tree_res.delete(*self.tree_res.get_children())
            for row in filas:
                datos = Consultas.parse_producto(row)
                if not datos:
                    continue
                self._resultados.append(datos)
                proveedor = str(datos.get("proveedor") or "").strip() or "-"
                self.tree_res.insert(
                    "",
                    "end",
                    values=(
                        datos["id"],
                        datos["nombre"],
                        datos.get("cantidad"),
                        proveedor,
                        formato_dinero(datos.get("precio_venta") or 0),
                    ),
                )

            if not self._resultados:
                if texto:
                    mb.showwarning(
                        "Kardex",
                        "No se encontraron productos con “{}”.".format(texto),
                        parent=self.win,
                    )
                self.lbl_prod.config(text="Seleccione un producto de la lista.")
                self.lbl_detalle.config(text="")
                self.lbl_proveedor.config(text="")
                self._producto = None
                self._pintar()
                return

            first = self.tree_res.get_children()[0]
            self.tree_res.selection_set(first)
            self.tree_res.focus(first)
            self.tree_res.see(first)
            if auto_abrir or len(self._resultados) == 1:
                self._abrir_seleccion()
            else:
                self._seleccion_resultado()
        except Exception as error:
            print("Error en búsqueda kardex: {}".format(error))
            mb.showerror("Kardex", "No se pudo buscar el producto: {}".format(error), parent=self.win)

    def _seleccion_resultado(self, event=None):
        sel = self.tree_res.selection()
        if not sel:
            return
        vals = self.tree_res.item(sel[0], "values")
        if not vals:
            return
        codigo = str(vals[0])
        for datos in self._resultados:
            if str(datos.get("id")) == codigo:
                self._mostrar_cabecera(datos)
                return

    def _abrir_seleccion(self, event=None):
        sel = self.tree_res.selection()
        if not sel and self.tree_res.get_children():
            sel = (self.tree_res.get_children()[0],)
            self.tree_res.selection_set(sel[0])
        if not sel:
            return "break"
        vals = self.tree_res.item(sel[0], "values")
        if not vals:
            return "break"
        codigo = str(vals[0])
        datos = None
        for item in self._resultados:
            if str(item.get("id")) == codigo:
                datos = item
                break
        if not datos:
            row = Consultas.obtener_producto(codigo)
            datos = Consultas.parse_producto(row) if row else None
        if not datos:
            mb.showerror("Kardex", "No se pudo cargar el producto.", parent=self.win)
            return "break"
        self._producto = datos
        self._mostrar_cabecera(datos)
        self._pintar()
        return "break"

    def _mostrar_cabecera(self, datos):
        proveedor = str(datos.get("proveedor") or "").strip() or "Sin proveedor asignado"
        self.lbl_prod.config(text="{}  ·  {}".format(datos["id"], datos["nombre"]))
        self.lbl_detalle.config(
            text="Existencia: {}  ·  P. compra {}  ·  P. venta {}  ·  IVA {}".format(
                datos.get("cantidad"),
                formato_dinero(datos.get("precio_compra") or 0),
                formato_dinero(datos.get("precio_venta") or 0),
                Consultas.iva_a_texto(datos.get("iva")),
            )
        )
        self.lbl_proveedor.config(text="Proveedor: {}".format(proveedor))

    def _pintar(self):
        self.tree_mov.delete(*self.tree_mov.get_children())
        self.tree_com.delete(*self.tree_com.get_children())
        self.tree_ven.delete(*self.tree_ven.get_children())
        if not self._producto:
            return
        pid = self._producto["id"]
        for row in Consultas.listar_movimientos_inventario(pid, limite=120):
            if not row or len(row) < 7:
                continue
            fecha, tipo, cant, factor, base, motivo, usuario = row[:7]
            self.tree_mov.insert(
                "",
                "end",
                values=(fecha, tipo, cant, factor, base, motivo, usuario),
            )
        for row in Consultas.historial_compras_producto(pid, limite=120):
            if not row or len(row) < 9:
                continue
            fecha, factura, proveedor, present, cant, base, costo, total, usuario = row[:9]
            self.tree_com.insert(
                "",
                "end",
                values=(
                    fecha,
                    factura or "-",
                    proveedor or "-",
                    present or "Unidad",
                    cant,
                    base,
                    formato_dinero(costo or 0),
                    formato_dinero(total or 0),
                    usuario or "",
                ),
            )
        for row in Consultas.historial_ventas_producto(pid, limite=120):
            if not row or len(row) < 5:
                continue
            fecha = row[0]
            present = row[1] if len(row) > 1 else "Unidad"
            cant = row[2] if len(row) > 2 else 0
            precio = row[3] if len(row) > 3 else 0
            subtotal = row[4] if len(row) > 4 else 0
            usuario = row[5] if len(row) > 5 else ""
            self.tree_ven.insert(
                "",
                "end",
                values=(
                    fecha,
                    present or "Unidad",
                    cant,
                    formato_dinero(precio or 0),
                    formato_dinero(subtotal or 0),
                    usuario or "",
                ),
            )
