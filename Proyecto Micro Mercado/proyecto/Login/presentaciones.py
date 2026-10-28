import tkinter as tk
from tkinter import ttk
import mensaje as mb
from zyntra_ui import *
import Consultas


class EditorPresentaciones(tk.Frame):
    """Tabla de presentaciones: conversión, utilidad y precio independientes."""

    def __init__(self, parent, get_costo_base=None, get_iva=None, get_unidad=None):
        super().__init__(parent, bg=BG_CARD)
        self.get_costo_base = get_costo_base or (lambda: 0)
        self.get_iva = get_iva or (lambda: 0)
        self.get_unidad = get_unidad or (lambda: "Unidad")
        self.filas = []
        styled_label(self, "Presentaciones de venta", FONT_SUB, TEXT, BG_CARD).pack(anchor="w")
        hint = styled_label(
            self,
            "El inventario se guarda en la unidad base. Cada presentación convierte automáticamente.",
            FONT_SMALL,
            TEXT_DIM,
            BG_CARD,
        )
        hint.configure(wraplength=720, justify="left")
        hint.pack(anchor="w", fill="x", pady=(0, 6))

        wrap, self.tree = scrollable_tree(
            self,
            columns=("Nombre", "Factor", "Utilidad", "Precio", "Venta", "Barras"),
            headings=("Presentación", "Conv.", "Utilidad %", "P. venta", "Vender", "Cód. barras"),
            height=5,
            widths={"Nombre": 150, "Factor": 70, "Utilidad": 90, "Precio": 100, "Venta": 70, "Barras": 130},
        )
        self.tree.column("Nombre", anchor="w")
        wrap.pack(fill="both", expand=True)

        form = tk.Frame(self, bg=BG_CARD)
        form.pack(fill="x", pady=(8, 0))
        form.grid_columnconfigure(0, weight=1)
        form.grid_columnconfigure(1, weight=1)
        form.grid_columnconfigure(2, weight=1)
        form.grid_columnconfigure(3, weight=1)

        styled_label(form, "Nombre", FONT_SMALL, TEXT_MUTED, BG_CARD).grid(row=0, column=0, sticky="w")
        styled_label(form, "Conversión a base", FONT_SMALL, TEXT_MUTED, BG_CARD).grid(row=0, column=1, sticky="w", padx=(6, 0))
        styled_label(form, "Utilidad %", FONT_SMALL, TEXT_MUTED, BG_CARD).grid(row=0, column=2, sticky="w", padx=(6, 0))
        styled_label(form, "Precio venta", FONT_SMALL, TEXT_MUTED, BG_CARD).grid(row=0, column=3, sticky="w", padx=(6, 0))
        self.nombre = styled_entry(form)
        self.nombre.grid(row=1, column=0, sticky="ew", padx=(0, 6))
        self.factor = styled_entry(form)
        self.factor.grid(row=1, column=1, sticky="ew", padx=(0, 6))
        self.utilidad = ttk.Combobox(form, font=("Segoe UI", 10), style="Zyntra.TCombobox", values=Consultas.UTILIDAD_CHOICES)
        self.utilidad.grid(row=1, column=2, sticky="ew", padx=(0, 6))
        self.utilidad.set("20%")
        self.precio = styled_entry(form)
        self.precio.grid(row=1, column=3, sticky="ew")

        row2 = tk.Frame(self, bg=BG_CARD)
        row2.pack(fill="x", pady=(6, 0))
        styled_label(row2, "Cód. barras", FONT_SMALL, TEXT_MUTED, BG_CARD).pack(side="left")
        self.barras = styled_entry(row2, width=16)
        self.barras.pack(side="left", padx=(6, 10))
        self.var_venta = tk.BooleanVar(value=True)
        tk.Checkbutton(
            row2,
            text="Permitir venta",
            variable=self.var_venta,
            bg=BG_CARD,
            fg=TEXT,
            selectcolor=BG_INPUT,
            activebackground=BG_CARD,
            activeforeground=TEXT,
            font=FONT_SMALL,
        ).pack(side="left")
        secondary_button(row2, "Agregar / actualizar", self._agregar, width=16, font=FONT_SMALL).pack(side="right")
        danger_button(row2, "Quitar", self._quitar, width=8, font=FONT_SMALL).pack(side="right", padx=(0, 6))
        self.utilidad.bind("<<ComboboxSelected>>", self._sugerir_precio)
        self.utilidad.bind("<KeyRelease>", self._sugerir_precio)
        self.factor.bind("<KeyRelease>", self._sugerir_precio)
        bind_money_entry(self.precio, on_change=self._sugerir_utilidad)
        self.precio.bind("<FocusOut>", self._redondear_precio_campo, add="+")
        self.tree.bind("<<TreeviewSelect>>", self._cargar_seleccion)

    def cargar(self, filas=None):
        self.filas = []
        for item in filas or []:
            self.filas.append(dict(item))
        if not self.filas:
            self.filas = [self._fila_unidad()]
        self._pintar()

    def valores(self):
        return [dict(x) for x in self.filas]

    def asegurar_unidad(self):
        if not self.filas:
            self.filas = [self._fila_unidad()]
            self._pintar()

    def _fila_unidad(self):
        factor = 1
        utilidad = 20
        costo = Consultas.costo_equivalente(self.get_costo_base(), factor)
        precio = Consultas.precio_venta_con_margen(costo, utilidad, self.get_iva()) or 0
        return {
            "nombre": "Unidad",
            "factor": 1,
            "unidad": self.get_unidad(),
            "codigo_barras": "",
            "precio_venta": precio,
            "utilidad_pct": utilidad,
            "permite_venta": True,
            "activo": True,
            "es_default": True,
        }

    def _pintar(self):
        self.tree.delete(*self.tree.get_children())
        for item in self.filas:
            self.tree.insert(
                "",
                "end",
                values=(
                    item.get("nombre"),
                    item.get("factor"),
                    Consultas.utilidad_a_texto(item.get("utilidad_pct")),
                    formato_dinero(item.get("precio_venta")),
                    "Sí" if item.get("permite_venta", True) else "No",
                    item.get("codigo_barras") or "",
                ),
            )

    def _indice_nombre(self, nombre):
        nombre = (nombre or "").strip().lower()
        for i, item in enumerate(self.filas):
            if str(item.get("nombre") or "").strip().lower() == nombre:
                return i
        return None

    def sincronizar_unidad(self, precio_venta, utilidad_pct):
        """Actualiza la presentación Unidad / default con precio y utilidad del producto."""
        try:
            precio = parse_dinero(precio_venta)
        except Exception:
            return
        try:
            utilidad = Consultas.utilidad_a_porcentaje(utilidad_pct)
        except Exception:
            utilidad = 0
        if precio <= 0:
            return
        precio = redondear_centena(precio)
        actualizado = False
        for item in self.filas:
            factor = float(item.get("factor") or 1)
            if item.get("es_default") or abs(factor - 1) < 0.0000001:
                item["precio_venta"] = precio
                item["utilidad_pct"] = utilidad
                actualizado = True
        if not actualizado:
            fila = self._fila_unidad()
            fila["precio_venta"] = precio
            fila["utilidad_pct"] = utilidad
            self.filas.insert(0, fila)
        self._pintar()
        # Si el formulario está sobre Unidad, refrescar campos
        nombre = (self.nombre.get() or "").strip().lower()
        if not nombre or nombre == "unidad":
            self.utilidad.set(Consultas.utilidad_a_texto(utilidad))
            self.precio.delete(0, tk.END)
            self.precio.insert(0, formato_entrada(str(int(precio))))
            if not self.nombre.get().strip():
                self.nombre.insert(0, "Unidad")
            if not self.factor.get().strip():
                self.factor.insert(0, "1")

    def _redondear_precio_campo(self, _event=None):
        bruto = parse_dinero(self.precio.get())
        if bruto > 0:
            red = redondear_centena(bruto)
            if abs(bruto - red) >= 0.5:
                self.precio.delete(0, tk.END)
                self.precio.insert(0, formato_entrada(str(int(red))))
        self._sugerir_utilidad()

    def _sugerir_precio(self, _event=None):
        try:
            factor = float(str(self.factor.get()).replace(",", ".") or 0)
        except ValueError:
            return
        if factor <= 0:
            return
        costo = Consultas.costo_equivalente(self.get_costo_base(), factor)
        venta = Consultas.precio_venta_con_margen(costo, self.utilidad.get(), self.get_iva())
        if venta is None:
            return
        self.precio.delete(0, tk.END)
        self.precio.insert(0, formato_entrada(str(int(venta))))

    def _sugerir_utilidad(self, _event=None):
        """Si el precio de la presentación se escribe a mano, recalcula la utilidad %."""
        try:
            factor = float(str(self.factor.get()).replace(",", ".") or 0)
        except ValueError:
            return
        if factor <= 0:
            return
        precio = parse_dinero(self.precio.get())
        if precio <= 0:
            return
        costo = Consultas.costo_equivalente(self.get_costo_base(), factor)
        util = Consultas.margen_desde_precios(costo, precio, self.get_iva())
        self.utilidad.set(Consultas.utilidad_a_texto(util))

    def _cargar_seleccion(self, _event=None):
        sel = self.tree.selection()
        if not sel:
            return
        vals = self.tree.item(sel[0], "values")
        self.nombre.delete(0, tk.END)
        self.nombre.insert(0, vals[0])
        self.factor.delete(0, tk.END)
        self.factor.insert(0, vals[1])
        self.utilidad.set(vals[2])
        self.precio.delete(0, tk.END)
        self.precio.insert(0, formato_entrada(str(parse_dinero(vals[3]))))
        self.var_venta.set(str(vals[4]) == "Sí")
        self.barras.delete(0, tk.END)
        self.barras.insert(0, vals[5] if len(vals) > 5 else "")

    def _agregar(self):
        nombre = self.nombre.get().strip()
        if not nombre:
            mb.showwarning("Presentación", "Indique el nombre (Caja, Blíster, Unidad…).", parent=self.winfo_toplevel())
            return
        try:
            factor = float(str(self.factor.get()).replace(",", ".") or 0)
        except ValueError:
            factor = 0
        if factor <= 0:
            mb.showerror("Presentación", "La conversión debe ser mayor a 0.", parent=self.winfo_toplevel())
            return
        try:
            precio = parse_dinero(self.precio.get())
        except ValueError:
            precio = 0
        if precio > 0:
            precio = redondear_centena(precio)
        costo = Consultas.costo_equivalente(self.get_costo_base(), factor)
        if precio > 0:
            utilidad = Consultas.margen_desde_precios(costo, precio, self.get_iva())
            self.utilidad.set(Consultas.utilidad_a_texto(utilidad))
        else:
            utilidad = Consultas.utilidad_a_porcentaje(self.utilidad.get())
            precio = Consultas.precio_venta_con_margen(costo, utilidad, self.get_iva()) or 0
            precio = redondear_centena(precio)
        fila = {
            "nombre": nombre,
            "factor": factor,
            "unidad": self.get_unidad(),
            "codigo_barras": self.barras.get().strip(),
            "precio_venta": precio,
            "utilidad_pct": utilidad,
            "permite_venta": bool(self.var_venta.get()),
            "activo": True,
            "es_default": abs(factor - 1) < 0.0000001,
        }
        idx = self._indice_nombre(nombre)
        if idx is None:
            self.filas.append(fila)
        else:
            fila["id"] = self.filas[idx].get("id")
            self.filas[idx] = fila
        self._pintar()
        self.nombre.delete(0, tk.END)
        self.factor.delete(0, tk.END)
        self.precio.delete(0, tk.END)
        self.barras.delete(0, tk.END)

    def _quitar(self):
        sel = self.tree.selection()
        if not sel:
            return
        nombre = str(self.tree.item(sel[0], "values")[0] or "").strip().lower()
        self.filas = [x for x in self.filas if str(x.get("nombre") or "").strip().lower() != nombre]
        if not self.filas:
            self.filas = [self._fila_unidad()]
        self._pintar()
