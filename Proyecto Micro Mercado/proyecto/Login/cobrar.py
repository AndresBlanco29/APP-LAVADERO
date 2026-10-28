import tkinter as tk
import mensaje as mb
from Consultas import *
from zyntra_ui import *


# Clave interna (reportes/BD) → etiqueta en pantalla
METODOS_UI = (
    ("Efectivo", "Efectivo"),
    ("Transferencia", "Bre-b / Nequi / Transferencia"),
    ("Tarjeta", "Tarjeta Débito / Crédito"),
    ("Crédito", "Crédito / Fiado"),
)
METODOS = tuple(clave for clave, _etiqueta in METODOS_UI)
ETIQUETA_METODO = {clave: etiqueta for clave, etiqueta in METODOS_UI}


def _solo_digitos(texto):
    return "".join(c for c in str(texto or "") if c.isdigit())


def _a_float(texto):
    return parse_dinero(texto)


def _miles(texto):
    return formato_entrada(texto)


def _cursor_tras_digitos(formateado, cuantos):
    return cursor_tras_digitos(formateado, cuantos)


def _monto(montos, clave):
    try:
        return float((montos or {}).get(clave) or 0)
    except (TypeError, ValueError):
        return 0.0


def _suma_no_efectivo(montos):
    return sum(_monto(montos, m) for m in METODOS if m != "Efectivo")


class CobrarOverlay(tk.Frame):
    def __init__(
        self,
        parent,
        total_ventas,
        total_articulos,
        id_empleado,
        productos_comprados,
        on_success,
        on_close,
        cliente=None,
        usuario=None,
        total_tarjeta=None,
    ):
        super().__init__(parent, bg="#07090F")
        self.total_base = float(redondear_centena(total_ventas or 0))
        self.total_venta_valor = self.total_base
        self.total_art = total_articulos
        self.id_empleado = id_empleado
        self.productos_comprados = list(productos_comprados or [])
        self.on_success = on_success
        self.on_close = on_close
        self.usuario = usuario
        self.cliente = dict(cliente) if cliente else None
        self.cobrar = self
        self.pagos_vars = {}
        self.ancho_ticket = tk.StringVar(value="80")
        self.puntos_valor = 0.0
        self.puntos_usados = 0
        self.cfg = obtener_config_pos()
        self.pct_recargo = float(self.cfg.get("pct_recargo_tarjeta") or 6)
        self.aplica_recargo = False
        self.total_tarjeta = self._resolver_total_tarjeta(total_tarjeta)
        self.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.lift()
        self.items()
        self.bind("<Escape>", lambda _e: self.cancelar_venta())

    def _resolver_total_tarjeta(self, total_tarjeta):
        """Usa el mismo total +% de la ventana de venta (por línea), no % sobre el gran total."""
        if total_tarjeta is not None:
            try:
                return float(redondear_centena(total_tarjeta))
            except (TypeError, ValueError):
                pass
        suma = 0.0
        for producto in self.productos_comprados:
            if not isinstance(producto, dict):
                continue
            sub_t = producto.get("subtotal_tarjeta")
            if sub_t not in (None, ""):
                try:
                    suma += float(sub_t or 0)
                    continue
                except (TypeError, ValueError):
                    pass
            try:
                precio = float(producto.get("precio") or 0)
                cant = float(producto.get("cantidad_presentacion") or 0)
                if cant <= 0:
                    factor = float(producto.get("factor") or 1) or 1
                    cant = float(producto.get("cantidad") or 0) / factor
                precio_t = float(producto.get("precio_tarjeta") or 0)
                if precio_t <= 0:
                    precio_t = float(precio_con_recargo(precio, self.pct_recargo))
                suma += float(redondear_centena(precio_t * cant))
            except (TypeError, ValueError):
                try:
                    suma += float(precio_con_recargo(producto.get("subtotal") or 0, self.pct_recargo))
                except (TypeError, ValueError):
                    pass
        if suma > 0:
            return float(redondear_centena(suma))
        return float(precio_con_recargo(self.total_base, self.pct_recargo))

    def items(self):
        card = card_frame(self, padx=24, pady=16)
        card.place(relx=0.5, rely=0.5, anchor="center")

        styled_label(card, "Cobro de venta", FONT_HEADING, TEXT, BG_CARD).pack(anchor="w")

        cliente_bar = tk.Frame(card, bg=BG_ELEVATED, padx=10, pady=8)
        cliente_bar.pack(fill="x", pady=(8, 10))
        self.lbl_cliente = styled_label(cliente_bar, self._texto_cliente(), FONT_SMALL, TEXT, BG_ELEVATED)
        self.lbl_cliente.pack(side="left", fill="x", expand=True)
        secondary_button(cliente_bar, "Cliente", self._buscar_cliente, width=10, font=FONT_SMALL).pack(side="right")

        resumen = tk.Frame(card, bg=BG_CARD)
        resumen.pack(fill="x", pady=(0, 8))
        art = tk.Frame(resumen, bg=BG_ELEVATED, padx=14, pady=8)
        art.pack(side="left", fill="y", padx=(0, 8))
        styled_label(art, "Artículos", FONT_LABEL, TEXT_DIM, BG_ELEVATED).pack(anchor="w")
        styled_label(art, f"{self.total_art}", ("Segoe UI", 22, "bold"), TEXT, BG_ELEVATED).pack(anchor="w")

        precios = tk.Frame(resumen, bg=BG_ELEVATED, padx=14, pady=8)
        precios.pack(side="left", fill="both", expand=True, padx=(0, 8))
        styled_label(precios, "Precios para el cliente", FONT_LABEL, TEXT_DIM, BG_ELEVATED).pack(anchor="w")
        precios_row = tk.Frame(precios, bg=BG_ELEVATED)
        precios_row.pack(fill="x", pady=(2, 0))

        col_desc = tk.Frame(precios_row, bg=BG_ELEVATED)
        col_desc.pack(side="left", fill="x", expand=True, padx=(0, 12))
        styled_label(col_desc, "Desc. (efectivo / Bre-b)", FONT_SMALL, TEXT_MUTED, BG_ELEVATED).pack(anchor="w")
        self.lbl_total_desc = money_label(
            col_desc,
            formato_dinero(self.total_base),
            ("Segoe UI", 22, "bold"),
            CYAN,
            BG_ELEVATED,
        )
        self.lbl_total_desc.pack(anchor="w")

        sep = tk.Frame(precios_row, bg=BORDER, width=1)
        sep.pack(side="left", fill="y", padx=(0, 12), pady=2)

        col_tarj = tk.Frame(precios_row, bg=BG_ELEVATED)
        col_tarj.pack(side="left", fill="x", expand=True)
        styled_label(
            col_tarj,
            "Tarjeta (+{:.0f}%)".format(self.pct_recargo),
            FONT_SMALL,
            TEXT_MUTED,
            BG_ELEVATED,
        ).pack(anchor="w")
        self.lbl_total_tarj = money_label(
            col_tarj,
            formato_dinero(self.total_tarjeta),
            ("Segoe UI", 22, "bold"),
            WARNING,
            BG_ELEVATED,
        )
        self.lbl_total_tarj.pack(anchor="w")

        tot = tk.Frame(resumen, bg=BG_ELEVATED, padx=14, pady=8)
        tot.pack(side="left", fill="both", expand=True)
        styled_label(tot, "Total a cobrar ahora", FONT_LABEL, TEXT_DIM, BG_ELEVATED).pack(anchor="w")
        self.lbl_total = money_label(tot, formato_dinero(self.total_venta_valor), ("Segoe UI", 22, "bold"), CYAN, BG_ELEVATED)
        self.lbl_total.pack(anchor="w")
        self.lbl_precio_hint = styled_label(
            tot,
            "Según el medio de pago",
            FONT_SMALL,
            TEXT_DIM,
            BG_ELEVATED,
        )
        self.lbl_precio_hint.pack(anchor="w")

        metodos = tk.Frame(card, bg=BG_CARD)
        metodos.pack(fill="x")
        for clave, etiqueta in METODOS_UI:
            fila = tk.Frame(metodos, bg=BG_CARD)
            fila.pack(fill="x", pady=2)
            styled_label(fila, etiqueta, FONT_LABEL, TEXT_MUTED, BG_CARD).pack(side="left")
            entry = styled_entry(fila, width=14, font=("Segoe UI", 12), justify="right")
            entry.pack(side="right")
            entry.bind("<KeyRelease>", self._on_pago_keyup)
            entry.bind("<FocusOut>", lambda e, w=entry: self._formatear_entry(w))
            entry.bind("<Return>", lambda _e: self.cobrar_total())
            entry.bind("<Escape>", lambda _e: self.cancelar_venta())
            if clave != "Efectivo":
                secondary_button(fila, "Resto", lambda m=clave: self._completar(m), width=7, font=FONT_SMALL).pack(
                    side="right", padx=(0, 6)
                )
            self.pagos_vars[clave] = entry

        puntos_row = tk.Frame(card, bg=BG_CARD)
        puntos_row.pack(fill="x", pady=(6, 4))
        self.lbl_puntos = styled_label(puntos_row, self._texto_puntos(), FONT_SMALL, CYAN, BG_CARD)
        self.lbl_puntos.pack(side="left")
        secondary_button(puntos_row, "Canjear puntos", self._canjear_puntos, width=14, font=FONT_SMALL).pack(side="right")

        primary_button(card, "Todo en efectivo", self._todo_efectivo, width=20, font=FONT_SMALL).pack(anchor="e", pady=(4, 6))
        self.pagos_vars["Efectivo"].focus_set()

        estado = tk.Frame(card, bg=BG_ELEVATED, padx=12, pady=8)
        estado.pack(fill="x", pady=(2, 8))
        self.lbl_cubierto = styled_label(estado, "Cubierto: $ 0", FONT_LABEL, TEXT, BG_ELEVATED)
        self.lbl_cubierto.pack(anchor="w")
        self.lbl_faltante = styled_label(estado, f"Faltante: {formato_dinero(self.total_venta_valor)}", FONT_LABEL, WARNING, BG_ELEVATED)
        self.lbl_faltante.pack(anchor="w")
        self.vueltos = money_label(estado, "Cambio  $ 0", ("Segoe UI", 16, "bold"), SUCCESS, BG_ELEVATED)
        self.vueltos.pack(anchor="w", pady=(2, 0))

        ticket_row = tk.Frame(card, bg=BG_CARD)
        ticket_row.pack(fill="x", pady=(0, 8))
        styled_label(ticket_row, "Ticket", FONT_LABEL, TEXT_MUTED, BG_CARD).pack(side="left")
        tk.Radiobutton(
            ticket_row, text="80 mm", variable=self.ancho_ticket, value="80",
            bg=BG_CARD, fg=TEXT, selectcolor=BG_INPUT, activebackground=BG_CARD, activeforeground=TEXT,
        ).pack(side="left", padx=(10, 4))
        tk.Radiobutton(
            ticket_row, text="58 mm", variable=self.ancho_ticket, value="58",
            bg=BG_CARD, fg=TEXT, selectcolor=BG_INPUT, activebackground=BG_CARD, activeforeground=TEXT,
        ).pack(side="left")

        actions = tk.Frame(card, bg=BG_CARD)
        actions.pack(fill="x")
        primary_button(actions, "Cobrar", self.cobrar_total, width=14).pack(side="left", padx=(0, 8))
        secondary_button(actions, "Cancelar", self.cancelar_venta, width=14).pack(side="left")
        self._recalcular()

    def _total_con_recargo(self):
        return float(self.total_tarjeta)

    def _actualizar_total_segun_pagos(self, montos=None):
        montos = montos if montos is not None else self._montos()
        self.aplica_recargo = venta_aplica_recargo(montos)
        if self.aplica_recargo:
            self.total_venta_valor = self._total_con_recargo()
            self.lbl_precio_hint.config(
                text="Cobrando con recargo +{:.0f}% (hay tarjeta)".format(self.pct_recargo),
                fg=WARNING,
            )
            self.lbl_total.config(fg=WARNING)
        else:
            self.total_venta_valor = float(redondear_centena(self.total_base))
            self.lbl_precio_hint.config(
                text="Cobrando precio desc. (efectivo / Bre-b / Nequi / Transferencia)",
                fg=TEXT_DIM,
            )
            self.lbl_total.config(fg=CYAN)
        self.lbl_total.config(text=formato_dinero(self.total_venta_valor))
        if hasattr(self, "lbl_total_desc"):
            self.lbl_total_desc.config(text=formato_dinero(self.total_base))
        if hasattr(self, "lbl_total_tarj"):
            self.lbl_total_tarj.config(text=formato_dinero(self.total_tarjeta))

    def _texto_cliente(self):
        if not self.cliente:
            return "Sin cliente  ·  asocie uno para fiado o puntos"
        return (
            f"{self.cliente['nombre']}  ·  saldo {formato_dinero(self.cliente['saldo'])}  ·  "
            f"cupo {formato_dinero(max(self.cliente['limite'] - self.cliente['saldo'], 0))}  ·  {self.cliente['puntos']} pts"
        )

    def _texto_puntos(self):
        if self.puntos_valor > 0:
            return f"Canje: {self.puntos_usados} pts = {formato_dinero(self.puntos_valor)}"
        if not self.cliente:
            return "Canje de puntos: asocie un cliente"
        valor = self.cfg.get("valor_punto", 50)
        return f"{self.cliente['puntos']} pts disponibles ({formato_dinero(self.cliente['puntos'] * valor)})"

    def _buscar_cliente(self):
        from clientes_cxc import SelectorCliente
        SelectorCliente(self, self._set_cliente)

    def _set_cliente(self, cliente):
        self.cliente = cliente
        self.puntos_valor = 0.0
        self.puntos_usados = 0
        self.lbl_cliente.config(text=self._texto_cliente())
        self.lbl_puntos.config(text=self._texto_puntos())
        self._recalcular()

    def _canjear_puntos(self):
        if not self.cliente:
            mb.showwarning("Puntos", "Asocie un cliente para canjear puntos.", parent=self)
            return
        valor_punto = float(self.cfg.get("valor_punto") or 0)
        if valor_punto <= 0 or self.cliente["puntos"] <= 0:
            mb.showinfo("Puntos", "El cliente no tiene puntos para canjear.", parent=self)
            return
        self._actualizar_total_segun_pagos()
        max_valor = min(self.cliente["puntos"] * valor_punto, self.total_venta_valor)
        self.puntos_valor = max_valor
        self.puntos_usados = int(max_valor // valor_punto)
        self.lbl_puntos.config(text=self._texto_puntos())
        self._recalcular()

    def _montos(self):
        return {metodo: _a_float(entry.get()) for metodo, entry in self.pagos_vars.items()}

    def _formatear_entry(self, entry, event=None):
        bruto = entry.get()
        try:
            pos = entry.index(tk.INSERT)
        except tk.TclError:
            pos = len(bruto)
        digitos_antes = sum(1 for c in bruto[:pos] if c.isdigit())
        formateado = _miles(bruto)
        if formateado == bruto:
            return
        entry.delete(0, tk.END)
        if formateado:
            entry.insert(0, formateado)
        try:
            entry.icursor(_cursor_tras_digitos(formateado, digitos_antes))
        except tk.TclError:
            pass

    def _on_pago_keyup(self, event=None):
        if event is not None and event.keysym in (
            "Left", "Right", "Up", "Down", "Home", "End",
            "Shift_L", "Shift_R", "Control_L", "Control_R",
            "Alt_L", "Alt_R", "Tab",
        ):
            self._recalcular()
            return
        if event is not None and event.widget in self.pagos_vars.values():
            self._formatear_entry(event.widget, event)
        self._recalcular()

    def _recalcular(self, event=None):
        montos = self._montos()
        self._actualizar_total_segun_pagos(montos)
        total_neto = max(self.total_venta_valor - self.puntos_valor, 0)
        otros = _suma_no_efectivo(montos)
        efectivo = _monto(montos, "Efectivo")
        faltante = max(total_neto - otros, 0)
        cubierto = min(self.puntos_valor + otros + min(efectivo, faltante), self.total_venta_valor)
        cambio = max(efectivo - faltante, 0) if otros <= total_neto else 0
        self.lbl_cubierto.config(text=f"Cubierto: {formato_dinero(cubierto)}")
        self.lbl_faltante.config(text=f"Faltante: {formato_dinero(max(self.total_venta_valor - cubierto, 0))}")
        self.vueltos.config(text=f"Cambio  {formato_dinero(cambio)}")

    def _completar(self, metodo):
        montos = self._montos()
        prueba = dict(montos)
        if float(prueba.get(metodo) or 0) <= 0:
            prueba[metodo] = 1
        self._actualizar_total_segun_pagos(prueba)
        montos = self._montos()
        usados = sum(v for k, v in montos.items() if k != metodo) + self.puntos_valor
        resto = max(self.total_venta_valor - usados, 0)
        entry = self.pagos_vars[metodo]
        entry.delete(0, tk.END)
        if resto:
            entry.insert(0, formato_entrada(str(int(resto))))
        self._recalcular()

    def _todo_efectivo(self):
        for metodo, entry in self.pagos_vars.items():
            entry.delete(0, tk.END)
            if metodo == "Efectivo":
                self.aplica_recargo = False
                self.total_venta_valor = float(redondear_centena(self.total_base))
                resto = max(self.total_venta_valor - self.puntos_valor, 0)
                entry.insert(0, formato_entrada(str(int(resto))))
        self._recalcular()

    def _productos_para_ticket(self):
        items = []
        for producto in self.productos_comprados:
            if isinstance(producto, dict):
                item = dict(producto)
                if self.aplica_recargo:
                    try:
                        if item.get("precio_tarjeta") not in (None, ""):
                            item["precio"] = float(redondear_centena(item.get("precio_tarjeta") or 0))
                        if item.get("subtotal_tarjeta") not in (None, ""):
                            item["subtotal"] = float(redondear_centena(item.get("subtotal_tarjeta") or 0))
                        elif self.total_base > 0:
                            factor = self.total_venta_valor / self.total_base
                            item["precio"] = round(float(item.get("precio") or 0) * factor)
                            item["subtotal"] = round(float(item.get("subtotal") or 0) * factor)
                    except (TypeError, ValueError):
                        pass
                items.append(item)
                continue
            factor = (self.total_venta_valor / self.total_base) if self.total_base > 0 else 1.0
            codigo = producto[0]
            cantidad = producto[1]
            subtotal = producto[2]
            nombre = producto[3] if len(producto) > 3 else f"Producto {codigo}"
            precio = producto[4] if len(producto) > 4 else (float(subtotal) / max(float(cantidad), 1))
            items.append(
                {
                    "codigo": codigo,
                    "cantidad": cantidad,
                    "subtotal": round(float(subtotal) * factor),
                    "nombre": nombre,
                    "precio": round(float(precio) * factor),
                }
            )
        return items

    def cobrar_total(self):
        montos = self._montos()
        self._actualizar_total_segun_pagos(montos)
        total_neto = round(max(self.total_venta_valor - self.puntos_valor, 0), 2)
        credito = _monto(montos, "Crédito")
        otros = _suma_no_efectivo(montos)
        efectivo = _monto(montos, "Efectivo")
        if otros > total_neto + 0.01:
            mb.showerror("Error", "Los pagos (sin efectivo) superan el total.", parent=self)
            return
        faltante = round(total_neto - otros, 2)
        if efectivo < faltante:
            mb.showwarning("Advertencia", "El dinero ingresado no cubre el total.", parent=self)
            return
        if (credito > 0 or self.puntos_usados > 0) and not self.cliente:
            mb.showerror("Cliente", "Asocie un cliente para fiado o canje de puntos.", parent=self)
            return
        if credito > 0:
            disponible = self.cliente["limite"] - self.cliente["saldo"]
            if credito > disponible + 0.01:
                mb.showerror("Cupo", f"El fiado supera el cupo disponible ({formato_dinero(disponible)}).", parent=self)
                return

        pagos = {}
        if faltante > 0:
            pagos["Efectivo"] = faltante
        for clave in ("Transferencia", "Tarjeta", "Crédito"):
            monto = _monto(montos, clave)
            if monto > 0:
                pagos[clave] = monto
        if self.puntos_valor > 0:
            pagos["Puntos"] = self.puntos_valor
        if not pagos:
            mb.showerror("Error", "Ingrese al menos un método de pago.", parent=self)
            return

        # Revalidar recargo con los pagos finales (sin puntos)
        self.aplica_recargo = venta_aplica_recargo(pagos)
        if self.aplica_recargo:
            self.total_venta_valor = self._total_con_recargo()
        else:
            self.total_venta_valor = float(redondear_centena(self.total_base))
        # Reajustar efectivo cobrado al total final si solo efectivo
        if list(pagos.keys()) == ["Efectivo"] or (set(pagos.keys()) <= {"Efectivo", "Puntos"} and "Efectivo" in pagos):
            pagos["Efectivo"] = round(max(self.total_venta_valor - self.puntos_valor, 0), 2)

        # Claves internas para BD/cierre; el ticket muestra etiquetas amigables.
        pagos_ticket = {}
        for clave, monto in pagos.items():
            if clave == "Puntos":
                pagos_ticket["Puntos"] = monto
            else:
                pagos_ticket[ETIQUETA_METODO.get(clave, clave)] = monto

        cambio = round(efectivo - faltante, 2) if not self.aplica_recargo or "Efectivo" in pagos else round(max(efectivo - faltante, 0), 2)

        lineas_pago = []
        for etiqueta, monto in pagos_ticket.items():
            lineas_pago.append(f"  • {etiqueta}: {formato_dinero(monto)}")
        detalle_pagos = "\n".join(lineas_pago) if lineas_pago else "  (sin pagos)"
        aviso_recargo = ""
        if self.aplica_recargo:
            aviso_recargo = f"\nIncluye recargo +{self.pct_recargo:.0f}% por tarjeta."
        msg_confirmar = (
            f"¿Confirmar venta?\n\n"
            f"Total a cobrar: {formato_dinero(self.total_venta_valor)}\n"
            f"Forma(s) de pago:\n{detalle_pagos}"
        )
        if cambio > 0.01:
            msg_confirmar += f"\nCambio: {formato_dinero(cambio)}"
        msg_confirmar += aviso_recargo
        msg_confirmar += "\n\nRevise que el medio de pago sea el correcto\n(ej. efectivo vs Bre-b / Nequi)."
        if not mb.askyesno("Confirmar venta", msg_confirmar, parent=self):
            return

        productos_ticket = self._productos_para_ticket()
        payload = {
            "total": self.total_venta_valor,
            "total_base": self.total_base,
            "total_tarjeta": self.total_tarjeta,
            "aplica_recargo": self.aplica_recargo,
            "pct_recargo": self.pct_recargo if self.aplica_recargo else 0,
            "id_empleado": self.id_empleado,
            "productos": productos_ticket,
            "pagos": pagos,
            "cliente": self.cliente,
            "credito": credito,
            "puntos_usados": self.puntos_usados,
            "puntos_ganados": 0,
            "usuario": self.usuario,
        }
        if self.cliente:
            pagado_dinero = (
                _monto(pagos, "Efectivo")
                + _monto(pagos, "Transferencia")
                + _monto(pagos, "Tarjeta")
            )
            pesos = max(int(self.cfg.get("pesos_por_punto") or 1000), 1)
            payload["puntos_ganados"] = int(pagado_dinero // pesos)

        from venta_servicio import procesar_cobro
        resultado = procesar_cobro(payload)
        id_venta = resultado.get("id_venta")
        offline = resultado.get("offline")
        if not id_venta:
            mb.showerror("Error", "No se pudo registrar la venta. Revise la conexión.", parent=self)
            return

        puntos_ganados = payload.get("puntos_ganados") or 0
        info = {
            "id_venta": id_venta,
            "total": self.total_venta_valor,
            "total_base": self.total_base,
            "aplica_recargo": self.aplica_recargo,
            "pct_recargo": self.pct_recargo if self.aplica_recargo else 0,
            "pagos": pagos,
            "pagos_ticket": pagos_ticket,
            "cambio": cambio,
            "articulos": self.total_art,
            "productos": productos_ticket,
            "ancho_mm": int(self.ancho_ticket.get() or 80),
            "cliente": self.cliente,
            "puntos_ganados": puntos_ganados,
            "puntos_canjeados": self.puntos_usados,
            "offline": offline,
        }
        if offline:
            mb.showwarning(
                "Modo offline",
                "No hay conexión con MySQL. La venta se guardó en la cola local y se sincronizará al reconectar.",
                parent=self,
            )
        else:
            mb.showinfo("Información", "Se ha realizado correctamente la venta", parent=self)
        callback = self.on_success
        self._cerrar()
        if callback:
            callback(info)

    def _items_ticket(self):
        return self._productos_para_ticket()

    def cancelar_venta(self, event=None):
        if mb.askyesno("Confirmar", "¿Desea cancelar el cobro?", parent=self):
            callback = self.on_close
            self._cerrar()
            if callback:
                callback()

    def _cerrar(self):
        self.destroy()
