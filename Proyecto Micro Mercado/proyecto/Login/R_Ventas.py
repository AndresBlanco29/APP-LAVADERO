import tkinter as tk
import mensaje as mb
from tkinter import ttk
from tkcalendar import DateEntry
from datetime import datetime, timedelta
from Consultas import *
from zyntra_ui import *
from exportes import exportar_xlsx, exportar_pdf


class R_Ventas(tk.Frame):
    def __init__(self, parent, usuario=None, app=None):
        super().__init__(parent, bg=BG)
        self.R_Venta = self
        self.usuario = usuario
        self.app = app
        self.items()

    def items(self):
        toolbar = card_frame(self, padx=12, pady=8)
        toolbar.pack(fill="x", pady=(0, 8))

        row = tk.Frame(toolbar, bg=BG_CARD)
        row.pack(fill="x")
        left = tk.Frame(row, bg=BG_CARD)
        left.pack(side="left", fill="x", expand=True)
        styled_label(left, "Buscar venta", FONT_LABEL, TEXT_MUTED, BG_CARD).pack(anchor="w")
        search = tk.Frame(left, bg=BG_CARD)
        search.pack(fill="x", pady=(6, 0))
        self.buscar_venta = styled_entry(search, width=28)
        self.buscar_venta.pack(side="left", fill="x", expand=True)
        self.buscar_venta.bind("<KeyRelease>", lambda _e: debounce(self, "_venta_job", 180, self.buscar_venta_codigo))
        primary_button(search, "Buscar", self.buscar_ventas_Fecha, width=10, font=FONT_SMALL).pack(side="left", padx=(8, 0))

        dates = tk.Frame(row, bg=BG_CARD)
        dates.pack(side="right", padx=(16, 0))
        styled_label(dates, "Desde", FONT_LABEL, TEXT_MUTED, BG_CARD).grid(row=0, column=0, sticky="w")
        self.fecha_desde = DateEntry(
            dates, width=14, background=ACCENT, foreground="white", borderwidth=2,
            year=datetime.now().year, font=("Segoe UI", 11, "bold"), locale="es_ES",
        )
        self.fecha_desde.grid(row=1, column=0, padx=(0, 10))
        styled_label(dates, "Hasta", FONT_LABEL, TEXT_MUTED, BG_CARD).grid(row=0, column=1, sticky="w")
        self.fecha_hasta = DateEntry(
            dates, width=14, background=ACCENT, foreground="white", borderwidth=2,
            year=datetime.now().year, font=("Segoe UI", 11, "bold"), locale="es_ES",
        )
        self.fecha_hasta.grid(row=1, column=1)
        try:
            self.fecha_desde.set_date(datetime.now().date() - timedelta(days=30))
        except Exception:
            pass

        metrics = tk.Frame(self, bg=BG)
        metrics.pack(fill="x", pady=(0, 8))
        self.lbl_ventas = self._metric_card(metrics, "Ventas")
        self.lbl_utilidad = self._metric_card(metrics, "Utilidad neta real")
        self.lbl_margen = self._metric_card(metrics, "Margen")
        self.lbl_tickets = self._metric_card(metrics, "Tickets")

        lists = tk.Frame(self, bg=BG)
        lists.pack(fill="x", pady=(0, 8))
        top_card = card_frame(lists, padx=10, pady=8)
        top_card.pack(side="left", fill="both", expand=True, padx=(0, 6))
        styled_label(top_card, "Top 10 más vendidos", FONT_LABEL, TEXT, BG_CARD).pack(anchor="w")
        self.top_wrap, self.tree_top = scrollable_tree(
            top_card,
            columns=("Producto", "Cantidad", "Total"),
            headings=("Producto", "Cant.", "Total"),
            height=4,
            widths={"Producto": 160, "Cantidad": 60, "Total": 80},
        )
        self.tree_top.column("Producto", anchor="w")
        self.top_wrap.pack(fill="both", expand=True, pady=(6, 0))

        bone_card = card_frame(lists, padx=10, pady=8)
        bone_card.pack(side="left", fill="both", expand=True, padx=(6, 0))
        styled_label(bone_card, "Productos sin movimiento (30 días)", FONT_LABEL, TEXT, BG_CARD).pack(anchor="w")
        self.bone_wrap, self.tree_hueso = scrollable_tree(
            bone_card,
            columns=("Codigo", "Producto", "Stock", "Marca"),
            headings=("Cód.", "Producto", "Stock", "Marca"),
            height=4,
            widths={"Codigo": 50, "Producto": 140, "Stock": 60, "Marca": 80},
        )
        self.tree_hueso.column("Producto", anchor="w")
        self.bone_wrap.pack(fill="both", expand=True, pady=(6, 0))

        footer = card_frame(self, padx=12, pady=8)
        footer.pack(side="bottom", fill="x")
        styled_label(footer, "Exportar e informes", FONT_LABEL, TEXT_MUTED, BG_CARD).pack(anchor="w")
        daily = tk.Frame(footer, bg=BG_CARD)
        daily.pack(fill="x", pady=(6, 0))
        self.fecha_seleccionada = DateEntry(
            daily, width=16, background=ACCENT, foreground="white", borderwidth=2,
            year=datetime.now().year, font=("Segoe UI", 10, "bold"), locale="es_ES",
        )
        self.fecha_seleccionada.pack(side="left")
        primary_button(daily, "Excel", self.exportar_excel, width=10).pack(side="left", padx=(12, 6))
        primary_button(daily, "PDF", self.generar_reporte, width=10).pack(side="left", padx=(0, 6))
        secondary_button(daily, "Reporte diario", self.generar_reporte_diario, width=16).pack(side="left")
        danger_button(daily, "Devolver venta", self.devolver_seleccion, width=14, font=FONT_SMALL).pack(side="left", padx=(8, 0))
        secondary_button(daily, "Reimprimir ticket", self.reimprimir_ticket, width=16, font=FONT_SMALL).pack(
            side="left", padx=(8, 0)
        )
        secondary_button(daily, "Utilidad por presentación", self.reporte_presentaciones, width=22, font=FONT_SMALL).pack(side="left", padx=(8, 0))
        secondary_button(daily, "Compras", self.reporte_compras, width=10, font=FONT_SMALL).pack(side="left", padx=(6, 0))

        self.tree_wrap, self.tree_ventas = scrollable_tree(
            self,
            columns=("Id_Venta", "Fecha", "Items", "Total", "Costo", "Utilidad", "Estado"),
            headings=("ID venta", "Fecha", "Ítems", "Total", "Costo", "Utilidad", "Estado"),
            height=8,
            widths={
                "Id_Venta": 70,
                "Fecha": 130,
                "Items": 55,
                "Total": 90,
                "Costo": 90,
                "Utilidad": 90,
                "Estado": 100,
            },
        )
        try:
            self.tree_ventas.configure(show="tree headings")
            self.tree_ventas.heading("#0", text="Periodo")
            self.tree_ventas.column("#0", width=170, minwidth=120, stretch=False, anchor="w")
        except tk.TclError:
            pass
        try:
            self.tree_ventas.tag_configure("grupo", background=BG_ELEVATED, foreground=CYAN)
            self.tree_ventas.tag_configure("dia", background=BG_CARD, foreground=TEXT_MUTED)
        except tk.TclError:
            pass
        self.tree_wrap.pack(fill="both", expand=True, pady=(0, 8))
        self.tree_ventas.bind("<Double-1>", self._on_click_venta)
        self.tree_ventas.bind("<Return>", self._on_click_venta)
        hint = styled_label(
            self,
            "Historial agrupado por año → mes → día. Expanda un día, seleccione la venta y use Reimprimir ticket o doble clic para detalle/devolución.",
            FONT_SMALL,
            TEXT_DIM,
            BG,
        )
        hint.pack(anchor="w", pady=(0, 4))

    def _metric_card(self, parent, titulo):
        box = tk.Frame(parent, bg=BG_CARD, padx=14, pady=10)
        box.pack(side="left", fill="x", expand=True, padx=4)
        styled_label(box, titulo, FONT_SMALL, TEXT_DIM, BG_CARD).pack(anchor="w")
        valor = styled_label(box, "$ 0", ("Segoe UI", 16, "bold"), CYAN, BG_CARD)
        valor.pack(anchor="w")
        return valor

    def on_show(self):
        if should_refresh(self):
            self._cargar()
        self.buscar_venta.focus_set()

    def _rango(self):
        fecha_inicio = self.fecha_desde.get_date().strftime("%Y-%m-%d")
        fecha_fin = (self.fecha_hasta.get_date() + timedelta(days=1)).strftime("%Y-%m-%d")
        return fecha_inicio, fecha_fin

    def _fila_venta(self, row):
        datos = list(row or [])
        estado_db = ""
        anulada = False
        if datos:
            ultimo = datos[-1]
            es_flag = False
            try:
                if int(ultimo) in (0, 1) and (
                    not isinstance(ultimo, str) or str(ultimo).strip() in ("0", "1")
                ):
                    es_flag = True
            except (TypeError, ValueError):
                es_flag = False
            if not es_flag:
                estado_db = str(ultimo or "")
                datos = datos[:-1]
        if datos:
            try:
                flag = int(datos[-1])
            except (TypeError, ValueError):
                flag = None
            if flag in (0, 1):
                anulada = flag == 1
                datos = datos[:-1]
        while len(datos) < 6:
            datos.append("")
        est = estado_db.upper()
        if anulada or "ANULADA" in est:
            etiqueta = "ANULADA"
            tags = ("anulada",)
        elif "PENDIENTE" in est or "ESPERA" in est:
            etiqueta = "EN ESPERA"
            tags = ("espera",)
        elif "PARCIAL" in est:
            etiqueta = "PARCIAL"
            tags = ("espera",)
        else:
            etiqueta = "Activa"
            tags = ()

        def _n(valor, enteros=False):
            try:
                numero = float(valor or 0)
            except (TypeError, ValueError):
                return valor
            if enteros or abs(numero - round(numero)) < 1e-9:
                return int(round(numero))
            return round(numero, 2)

        valores = [
            datos[0],
            datos[1],
            str(_n(datos[2], True)),
            formato_dinero(_n(datos[3], True)),
            formato_dinero(_n(datos[4], True)),
            formato_dinero(_n(datos[5], True)),
            etiqueta,
        ]
        return valores, tags

    def refrescar_ahora(self):
        self._last_refresh = 0
        self._cargar()

    @staticmethod
    def _parse_fecha_venta(valor):
        if valor is None:
            return None
        if isinstance(valor, datetime):
            return valor
        texto = str(valor).strip().replace("T", " ")
        for fmt, size in (
            ("%Y-%m-%d %H:%M:%S", 19),
            ("%Y-%m-%d %H:%M", 16),
            ("%Y-%m-%d", 10),
        ):
            try:
                return datetime.strptime(texto[:size], fmt)
            except ValueError:
                continue
        return None

    def _insertar_filas(self, filas):
        tree = self.tree_ventas
        tree.delete(*tree.get_children())
        meses = (
            "",
            "Enero",
            "Febrero",
            "Marzo",
            "Abril",
            "Mayo",
            "Junio",
            "Julio",
            "Agosto",
            "Septiembre",
            "Octubre",
            "Noviembre",
            "Diciembre",
        )
        # Agrupar: año -> mes -> día -> ventas
        grupos = {}
        for row in filas or []:
            valores, tags = self._fila_venta(row)
            fecha_raw = row[1] if row is not None and len(row) > 1 else valores[1]
            dt = self._parse_fecha_venta(fecha_raw)
            if dt is None:
                anio, mes, dia = 0, 0, 0
                clave_dia = "sin-fecha"
            else:
                anio, mes, dia = dt.year, dt.month, dt.day
                clave_dia = dt.strftime("%Y-%m-%d")
            grupos.setdefault(anio, {}).setdefault(mes, {}).setdefault(clave_dia, []).append(
                (valores, tags, dt)
            )

        ahora = datetime.now()
        for anio in sorted(grupos.keys(), reverse=True):
            meses_map = grupos[anio]
            tot_a = {"items": 0, "total": 0.0, "costo": 0.0, "util": 0.0, "n": 0}
            iid_anio = "y_{}".format(anio)
            tree.insert(
                "",
                "end",
                iid=iid_anio,
                text="Año {}".format(anio if anio else "s/f"),
                values=("", "", "", "", "", "", ""),
                tags=("grupo",),
                open=(anio == ahora.year),
            )
            for mes in sorted(meses_map.keys(), reverse=True):
                dias_map = meses_map[mes]
                tot_m = {"items": 0, "total": 0.0, "costo": 0.0, "util": 0.0, "n": 0}
                nombre_mes = meses[mes] if 1 <= mes <= 12 else "Sin mes"
                iid_mes = "m_{}_{:02d}".format(anio, mes)
                tree.insert(
                    iid_anio,
                    "end",
                    iid=iid_mes,
                    text="{}".format(nombre_mes),
                    values=("", "", "", "", "", "", ""),
                    tags=("grupo",),
                    open=(anio == ahora.year and mes == ahora.month),
                )
                for clave_dia in sorted(dias_map.keys(), reverse=True):
                    ventas_dia = dias_map[clave_dia]
                    tot_d = {"items": 0, "total": 0.0, "costo": 0.0, "util": 0.0, "n": 0}
                    if ventas_dia and ventas_dia[0][2] is not None:
                        etiqueta_dia = ventas_dia[0][2].strftime("%d/%m/%Y")
                        es_hoy = ventas_dia[0][2].date() == ahora.date()
                    else:
                        etiqueta_dia = clave_dia
                        es_hoy = False
                    iid_dia = "d_{}".format(clave_dia)
                    tree.insert(
                        iid_mes,
                        "end",
                        iid=iid_dia,
                        text=etiqueta_dia,
                        values=("", "", "", "", "", "", ""),
                        tags=("dia",),
                        open=es_hoy,
                    )
                    for valores, tags, _dt in ventas_dia:
                        try:
                            items_n = int(float(str(valores[2]).replace(",", ".") or 0))
                        except (TypeError, ValueError):
                            items_n = 0
                        try:
                            total_n = parse_dinero(valores[3])
                            costo_n = parse_dinero(valores[4])
                            util_n = parse_dinero(valores[5])
                        except Exception:
                            total_n = costo_n = util_n = 0.0
                        if str(valores[6]).upper() != "ANULADA":
                            tot_d["items"] += items_n
                            tot_d["total"] += total_n
                            tot_d["costo"] += costo_n
                            tot_d["util"] += util_n
                            tot_d["n"] += 1
                        hora = ""
                        if _dt is not None:
                            hora = _dt.strftime("%H:%M:%S")
                        elif valores[1]:
                            hora = str(valores[1])[11:19] or str(valores[1])
                        leaf_tags = tuple(tags) + ("venta",)
                        tree.insert(
                            iid_dia,
                            "end",
                            iid="v_{}".format(valores[0]),
                            text="Ticket #{}".format(valores[0]),
                            values=(
                                valores[0],
                                hora,
                                str(items_n),
                                valores[3],
                                valores[4],
                                valores[5],
                                valores[6],
                            ),
                            tags=leaf_tags,
                        )
                    tree.item(
                        iid_dia,
                        values=(
                            "",
                            "{} venta(s)".format(tot_d["n"]),
                            str(tot_d["items"]),
                            formato_dinero(tot_d["total"]),
                            formato_dinero(tot_d["costo"]),
                            formato_dinero(tot_d["util"]),
                            "",
                        ),
                    )
                    for k in ("items", "total", "costo", "util", "n"):
                        tot_m[k] += tot_d[k]
                tree.item(
                    iid_mes,
                    values=(
                        "",
                        "{} venta(s)".format(tot_m["n"]),
                        str(tot_m["items"]),
                        formato_dinero(tot_m["total"]),
                        formato_dinero(tot_m["costo"]),
                        formato_dinero(tot_m["util"]),
                        "",
                    ),
                )
                for k in ("items", "total", "costo", "util", "n"):
                    tot_a[k] += tot_m[k]
            tree.item(
                iid_anio,
                values=(
                    "",
                    "{} venta(s)".format(tot_a["n"]),
                    str(tot_a["items"]),
                    formato_dinero(tot_a["total"]),
                    formato_dinero(tot_a["costo"]),
                    formato_dinero(tot_a["util"]),
                    "",
                ),
            )

    def _cargar(self):
        rango = self._rango()

        def fetch():
            fi, ff = rango
            return {
                "ventas": resumen_ventas(fi, ff),
                "resumen": utilidad_ventas(fi, ff),
                "top": top_productos_vendidos(10, fi, ff),
                "hueso": productos_sin_movimiento(30),
            }

        load_async(self, fetch, self._pintar_carga)

    def _pintar_carga(self, data):
        self._insertar_filas(data.get("ventas") or [])
        self._pintar_metricas(data.get("resumen") or {}, data.get("top") or [], data.get("hueso") or [])
        mark_refreshed(self)

    def _pintar_metricas(self, resumen, top, hueso):
        ventas = resumen.get("ventas", 0)
        utilidad = resumen.get("utilidad", 0)
        tickets = resumen.get("tickets", 0)
        margen = (utilidad / ventas * 100) if ventas else 0
        self.lbl_ventas.config(text=formato_dinero(ventas))
        self.lbl_utilidad.config(text=formato_dinero(utilidad))
        self.lbl_margen.config(text=f"{margen:.1f} %")
        self.lbl_tickets.config(text=str(tickets))
        self.tree_top.delete(*self.tree_top.get_children())
        for row in top:
            vals = list(row)
            if len(vals) >= 3:
                vals[2] = formato_dinero(vals[2])
            self.tree_top.insert("", "end", values=vals)
        self.tree_hueso.delete(*self.tree_hueso.get_children())
        for row in hueso:
            self.tree_hueso.insert("", "end", values=row)

    def _actualizar_metricas(self, fecha_inicio=None, fecha_fin=None):
        self._pintar_metricas(
            utilidad_ventas(fecha_inicio, fecha_fin),
            top_productos_vendidos(10, fecha_inicio, fecha_fin),
            productos_sin_movimiento(30),
        )

    def buscar_ventas_Fecha(self):
        self._cargar()

    def buscar_venta_codigo(self, event=None):
        venta_buscada = self.buscar_venta.get().strip()
        if not venta_buscada:
            self._cargar()
            return
        self._insertar_filas(resumen_ventas(codigo=venta_buscada))

    def _iter_filas_venta(self):
        """Recorre solo hojas (tickets), no nodos de año/mes/día."""

        def walk(parent):
            for iid in self.tree_ventas.get_children(parent):
                tags = self.tree_ventas.item(iid, "tags") or ()
                if "venta" in tags:
                    yield self.tree_ventas.item(iid, "values")
                else:
                    yield from walk(iid)

        return list(walk(""))

    def _filas_tabla(self):
        return self._iter_filas_venta()

    def _extras_reporte(self, filas):
        activas = [
            f for f in filas
            if str(f[-1] if f else "").upper() not in ("ANULADA",)
        ]
        total = 0.0
        utilidad = 0.0
        for f in activas:
            try:
                total += parse_dinero(f[3] or 0)
            except (TypeError, ValueError, IndexError):
                pass
            try:
                utilidad += parse_dinero(f[5] or 0)
            except (TypeError, ValueError, IndexError):
                pass
        extras = [
            f"Total de ventas activas: {formato_dinero(total)}",
            f"Utilidad neta real (precio venta - precio compra): {formato_dinero(utilidad)}",
        ]
        anuladas = len(filas) - len(activas)
        if anuladas:
            extras.append("Ventas anuladas en el listado: {} (no suman al total)".format(anuladas))
        return extras

    def exportar_excel(self):
        ventas = self._filas_tabla()
        if not ventas:
            mb.showinfo("Exportar", "No hay ventas para exportar.", parent=self.R_Venta)
            return
        encabezados = ["ID Venta", "Fecha", "Ítems", "Total", "Costo", "Utilidad", "Estado"]
        extras = self._extras_reporte(ventas)
        try:
            path = exportar_xlsx(encabezados, ventas, "historial_ventas.xlsx", "Historial de ventas Zyntra POS", extras)
            mb.showinfo("Excel generado", f"Archivo guardado en:\n{path}", parent=self.R_Venta)
        except Exception as error:
            mb.showerror("Error", f"No se pudo exportar a Excel: {error}", parent=self.R_Venta)

    def generar_reporte(self):
        ventas = self._filas_tabla()
        if not ventas:
            mb.showinfo("Reporte", "No hay ventas para generar el reporte.", parent=self.R_Venta)
            return
        encabezados = ["ID Venta", "Fecha", "Ítems", "Total", "Costo", "Utilidad", "Estado"]
        try:
            path = exportar_pdf(
                "Reporte de ventas",
                encabezados,
                ventas,
                "reporte_ventas.pdf",
                self._extras_reporte(ventas),
                apaisado=True,
            )
            mb.showinfo("Reporte generado", f"El PDF se guardó en:\n{path}", parent=self.R_Venta)
        except Exception as error:
            mb.showerror("Error", f"No se pudo generar el PDF: {error}", parent=self.R_Venta)

    def generar_reporte_diario(self):
        fecha_seleccionada = self.fecha_seleccionada.get_date().strftime("%Y-%m-%d")
        fecha_fin = (self.fecha_seleccionada.get_date() + timedelta(days=1)).strftime("%Y-%m-%d")
        ventas_diarias = resumen_ventas(fecha_seleccionada, fecha_fin)
        if not ventas_diarias:
            mb.showinfo("Reporte Diario", "No hay ventas registradas para la fecha seleccionada.", parent=self.R_Venta)
            return
        encabezados = ["ID Venta", "Fecha", "Ítems", "Total", "Costo", "Utilidad", "Estado"]
        filas = [self._fila_venta(r)[0] for r in ventas_diarias]
        extras = self._extras_reporte(filas)
        try:
            path_pdf = exportar_pdf(
                f"Reporte diario de ventas — {fecha_seleccionada}",
                encabezados,
                filas,
                f"reporte_diario_{fecha_seleccionada}.pdf",
                extras,
                apaisado=True,
            )
            path_xlsx = exportar_xlsx(
                encabezados,
                filas,
                f"reporte_diario_{fecha_seleccionada}.xlsx",
                f"Reporte diario {fecha_seleccionada}",
                extras,
            )
            mb.showinfo("Reporte diario", f"PDF:\n{path_pdf}\n\nExcel:\n{path_xlsx}", parent=self.R_Venta)
        except Exception as error:
            mb.showerror("Error", f"No se pudo generar el reporte diario: {error}", parent=self.R_Venta)

    def _id_venta_seleccionada(self):
        sel = self.tree_ventas.selection()
        if not sel:
            return None, ""
        iid = sel[0]
        tags = self.tree_ventas.item(iid, "tags") or ()
        if "venta" not in tags:
            return None, ""
        valores = self.tree_ventas.item(iid, "values")
        return valores[0], str(valores[-1] if valores else "").upper()

    def _on_click_venta(self, event=None):
        if event is not None:
            item = self.tree_ventas.identify_row(getattr(event, "y", 0) or 0)
            if item:
                self.tree_ventas.selection_set(item)
                tags = self.tree_ventas.item(item, "tags") or ()
                # Clic en año/mes/día solo expande/colapsa
                if "venta" not in tags:
                    try:
                        self.tree_ventas.item(item, open=not self.tree_ventas.item(item, "open"))
                    except tk.TclError:
                        pass
                    return "break"
        id_venta, _estado = self._id_venta_seleccionada()
        if not id_venta:
            return "break"
        self._abrir_detalle_venta(id_venta)
        return "break"

    def reimprimir_ticket(self):
        id_venta, estado = self._id_venta_seleccionada()
        if not id_venta:
            mb.showwarning(
                "Ticket",
                "Seleccione una venta (dentro de un día) para reimprimir el ticket.",
                parent=self.R_Venta,
            )
            return
        if estado == "ANULADA":
            if not mb.askyesno(
                "Venta anulada",
                "Esta venta está anulada. ¿Reimprimir el ticket de todas formas?",
                parent=self.R_Venta,
            ):
                return
        info = construir_info_ticket_venta(id_venta)
        if not info:
            mb.showerror("Ticket", "No se pudo armar el ticket de la venta.", parent=self.R_Venta)
            return
        cajero = info.get("cajero") or self.usuario or ""
        try:
            from ticket import imprimir_ticket_venta

            path, _ = imprimir_ticket_venta(info, cajero=cajero, ancho_mm=80, enviar_cola=True)
            mb.showinfo("Ticket", "Ticket enviado a impresión.\n{}".format(path), parent=self.R_Venta)
        except Exception as error:
            mb.showerror("Ticket", "No se pudo imprimir: {}".format(error), parent=self.R_Venta)

    def devolver_seleccion(self):
        id_venta, estado = self._id_venta_seleccionada()
        if not id_venta:
            mb.showwarning("Devolución", "Seleccione una venta para ver sus ítems y devolver.", parent=self.R_Venta)
            return
        if estado == "ANULADA":
            mb.showinfo("Devolución", "Esa venta ya está anulada.", parent=self.R_Venta)
            return
        self._abrir_detalle_venta(id_venta)

    def _abrir_detalle_venta(self, id_venta):
        lineas = detalle_lineas_venta(id_venta)
        if not lineas:
            mb.showinfo("Venta", "No hay ítems en esa venta.", parent=self.R_Venta)
            return
        dlg = tk.Toplevel(self)
        prepare_modal(dlg, self, "Venta #{}".format(id_venta), 720, 460, resizable=True)
        card = card_frame(dlg, padx=14, pady=12)
        card.pack(fill="both", expand=True)
        styled_label(card, "Detalle de la venta #{}".format(id_venta), FONT_HEADING, TEXT, BG_CARD).pack(anchor="w")
        styled_label(
            card,
            "Marque los productos a devolver. El mismo día lo aprueba el admin; días anteriores se aplican de inmediato.",
            FONT_SMALL,
            TEXT_DIM,
            BG_CARD,
        ).pack(anchor="w", pady=(0, 8))

        vars_linea = []
        lista = tk.Frame(card, bg=BG_CARD)
        lista.pack(fill="both", expand=True)
        canvas = tk.Canvas(lista, bg=BG_CARD, highlightthickness=0)
        scroll = ttk.Scrollbar(lista, orient="vertical", command=canvas.yview)
        inner = tk.Frame(canvas, bg=BG_CARD)
        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=scroll.set)
        canvas.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        for linea in lineas:
            var = tk.IntVar(value=0)
            texto = "{}  ·  {}  ·  cant. {:g}  ·  {}".format(
                linea.get("producto"),
                linea.get("presentacion") or "Unidad",
                float(linea.get("cantidad") or 0),
                formato_dinero(linea.get("subtotal") or 0),
            )
            estado_ln = "DEVUELTO" if linea.get("devuelto") else "Activo"
            fila = tk.Frame(inner, bg=BG_CARD)
            fila.pack(fill="x", pady=2)
            chk = tk.Checkbutton(
                fila,
                variable=var,
                bg=BG_CARD,
                fg=TEXT,
                selectcolor=BG_INPUT,
                activebackground=BG_CARD,
                activeforeground=TEXT,
                highlightthickness=0,
                state="disabled" if linea.get("devuelto") else "normal",
            )
            chk.pack(side="left")
            color = TEXT_DIM if linea.get("devuelto") else TEXT
            styled_label(fila, texto, FONT_BODY, color, BG_CARD).pack(side="left", fill="x", expand=True)
            styled_label(
                fila,
                estado_ln,
                FONT_SMALL,
                WARNING if linea.get("devuelto") else SUCCESS,
                BG_CARD,
            ).pack(side="right")
            vars_linea.append((var, linea))

        def seleccionadas():
            return [ln for var, ln in vars_linea if var.get() and not ln.get("devuelto")]

        def activas():
            return [ln for _var, ln in vars_linea if not ln.get("devuelto")]

        def pedir(items, toda=False):
            pendientes = activas()
            if not pendientes:
                mb.showinfo("Devolución", "Todos los ítems de esta venta ya fueron devueltos.", parent=dlg)
                return
            if not toda and not items:
                mb.showwarning("Devolución", "Marque al menos un ítem, o devuelva toda la venta.", parent=dlg)
                return
            payload = None if toda else items
            if toda:
                if not mb.askyesno(
                    "Devolución",
                    "¿Devolver toda la venta #{}?\nSi es del mismo día, el admin debe aprobarla en el celular.".format(
                        id_venta
                    ),
                    parent=dlg,
                ):
                    return
            else:
                nombres = ", ".join(it.get("producto") or "" for it in items)
                if not mb.askyesno(
                    "Devolución parcial",
                    "¿Devolver estos ítems de la venta #{}?\n{}\n\n"
                    "Si es del mismo día, el admin debe aprobarlos en el celular.".format(id_venta, nombres),
                    parent=dlg,
                ):
                    return
            ok, msg = solicitar_o_devolver_venta(id_venta, self.usuario, items=payload)
            if ok:
                if "devuelta" in (msg or "").lower() and self.app and getattr(self.app, "ventas_turno", None):
                    if toda or len(items or []) >= len(pendientes):
                        for venta in self.app.ventas_turno:
                            if str(venta.get("id_venta")) == str(id_venta):
                                venta["anulada"] = True
                mb.showinfo("Devolución", msg, parent=dlg)
                dlg.destroy()
                self._cargar()
            else:
                mb.showerror("Devolución", msg, parent=dlg)

        acciones = tk.Frame(card, bg=BG_CARD)
        acciones.pack(fill="x", pady=(10, 0))
        danger_button(
            acciones,
            "Devolver seleccionados",
            lambda: pedir(seleccionadas(), toda=False),
            width=22,
            font=FONT_SMALL,
        ).pack(side="left")
        secondary_button(
            acciones,
            "Devolver toda la venta",
            lambda: pedir(activas(), toda=True),
            width=22,
            font=FONT_SMALL,
        ).pack(side="left", padx=(8, 0))
        secondary_button(acciones, "Cerrar", dlg.destroy, width=10, font=FONT_SMALL).pack(side="right")

    def reporte_presentaciones(self):
        fecha_inicio, fecha_fin = self._rango()
        filas = utilidad_por_presentacion(fecha_inicio, fecha_fin)
        if not filas:
            mb.showinfo("Utilidad", "No hay ventas en este periodo.", parent=self.R_Venta)
            return
        dlg = tk.Toplevel(self)
        prepare_modal(dlg, self, "Utilidad por presentación", 780, 480, resizable=True)
        card = card_frame(dlg, padx=14, pady=12)
        card.pack(fill="both", expand=True)
        styled_label(card, "Rentabilidad por presentación", FONT_HEADING, TEXT, BG_CARD).pack(anchor="w")
        styled_label(card, "Del {} al {}".format(fecha_inicio, fecha_fin), FONT_SMALL, TEXT_DIM, BG_CARD).pack(anchor="w", pady=(0, 8))
        wrap, tree = scrollable_tree(
            card,
            columns=("Producto", "Presentacion", "Cantidad", "Base", "Ventas", "Utilidad"),
            headings=("Producto", "Presentación", "Cant. vendida", "Unid. base", "Ventas", "Utilidad"),
            height=12,
            widths={"Producto": 180, "Presentacion": 100, "Cantidad": 90, "Base": 80, "Ventas": 90, "Utilidad": 90},
        )
        tree.column("Producto", anchor="w")
        wrap.pack(fill="both", expand=True)
        for row in filas:
            vals = list(row)
            if len(vals) >= 6:
                vals[4] = formato_dinero(vals[4])
                vals[5] = formato_dinero(vals[5])
            tree.insert("", "end", values=vals)
        encabezados = ["Producto", "Presentación", "Cantidad", "Unidades base", "Ventas", "Utilidad"]
        btns = tk.Frame(card, bg=BG_CARD)
        btns.pack(fill="x", pady=(10, 0))

        def exportar():
            path = exportar_xlsx(encabezados, filas, "utilidad_presentaciones.xlsx", "Utilidad por presentación")
            mb.showinfo("Excel", "Archivo guardado en:\n{}".format(path), parent=dlg)

        primary_button(btns, "Excel", exportar, width=12).pack(side="left")

    def reporte_compras(self):
        fecha_inicio, fecha_fin = self._rango()
        filas = detalle_compras(fecha_inicio, fecha_fin)
        if not filas:
            mb.showinfo("Compras", "No hay compras en este periodo.", parent=self.R_Venta)
            return
        dlg = tk.Toplevel(self)
        prepare_modal(dlg, self, "Compras por presentación", 920, 500, resizable=True)
        card = card_frame(dlg, padx=14, pady=12)
        card.pack(fill="both", expand=True)
        styled_label(card, "Compras", FONT_HEADING, TEXT, BG_CARD).pack(anchor="w")
        wrap, tree = scrollable_tree(
            card,
            columns=("Fecha", "Factura", "Proveedor", "Producto", "Presentacion", "Cant", "Base", "Costo", "Iva", "Total"),
            headings=("Fecha", "Factura", "Proveedor", "Producto", "Presentación", "Cant.", "Base", "Costo", "IVA", "Total"),
            height=12,
            widths={
                "Fecha": 110, "Factura": 80, "Proveedor": 110, "Producto": 140, "Presentacion": 80,
                "Cant": 50, "Base": 50, "Costo": 70, "Iva": 60, "Total": 70,
            },
        )
        tree.column("Producto", anchor="w")
        wrap.pack(fill="both", expand=True, pady=(8, 0))
        for row in filas:
            vals = list(row)
            if len(vals) >= 10:
                vals[7] = formato_dinero(vals[7])
                vals[8] = formato_dinero(vals[8])
                vals[9] = formato_dinero(vals[9])
            tree.insert("", "end", values=vals)
        encabezados = ["Fecha", "Factura", "Proveedor", "Producto", "Presentación", "Cantidad", "Base", "Costo", "IVA", "Total"]
        btns = tk.Frame(card, bg=BG_CARD)
        btns.pack(fill="x", pady=(10, 0))

        def exportar():
            path = exportar_xlsx(encabezados, filas, "compras_periodo.xlsx", "Compras por presentación")
            mb.showinfo("Excel", "Archivo guardado en:\n{}".format(path), parent=dlg)

        primary_button(btns, "Excel", exportar, width=12).pack(side="left")
