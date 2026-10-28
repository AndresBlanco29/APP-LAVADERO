import tkinter as tk
from datetime import datetime
import mensaje as mb
from zyntra_ui import *


class PosShell(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=BG)
        self.app = app
        self.pack(fill="both", expand=True)
        self.views = {}
        self.active = None
        self.cobro_overlay = None
        self.nav_buttons = {}
        self._clock_job = None

        self.header = HeaderBar(self, "Punto de venta")
        self.header.pack(fill="x")
        apply_ttk_styles(force=True)

        nav = tk.Frame(self, bg=BG_NAV, highlightthickness=1, highlightbackground=BORDER)
        nav.pack(fill="x")
        inner_nav = tk.Frame(nav, bg=BG_NAV)
        inner_nav.pack(fill="x", padx=10, pady=8)

        items = [
            ("venta", "Venta"),
            ("productos", "Productos"),
            ("proveedores", "Proveed."),
            ("reportes", "R.Ventas"),
            ("caja", "Caja"),
            ("cxc", "CxC"),
        ]
        try:
            from cierre_general_svc import es_usuario_admin

            self.app.es_admin = bool(es_usuario_admin(getattr(self.app, "usuario", None)))
        except Exception:
            self.app.es_admin = False
        if getattr(self.app, "es_admin", False):
            # Personal / usuarios: solo administrador (Entrega 7)
            items.insert(2, ("personal", "Personal"))
            items.append(("cierre_general", "C.General"))
            items.append(("bolsillos", "Bolsillos"))
            items.append(("reportes_admin", "D.Admin"))
        for key, label in items:
            btn = nav_button(inner_nav, label, lambda k=key: self.show_view(k), width=11, active=(key == "venta"))
            btn.pack(side="left", padx=4)
            self.nav_buttons[key] = btn

        self.btn_cerrar_turno = warning_button(
            inner_nav, "Cerrar Turno", self.cerrar_turno, width=13, height=2, font=FONT_NAV
        )
        self.btn_cerrar_turno.pack(side="right", padx=4)
        self.btn_arqueo_temp = secondary_button(
            inner_nav, "Arqueo temporal", self.arqueo_temporal, width=15, height=2, font=FONT_NAV
        )
        self.btn_arqueo_temp.pack(side="right", padx=4)
        self.btn_ticket_cierre = secondary_button(
            inner_nav, "Ticket cierre", self.reimprimir_ticket_cierre, width=13, height=2, font=FONT_NAV
        )
        self.btn_ticket_cierre.pack(side="right", padx=4)
        self.lbl_sync = styled_label(inner_nav, "", FONT_SMALL, TEXT_DIM, BG_NAV)
        self.lbl_sync.pack(side="right", padx=10)

        self.content = tk.Frame(self, bg=BG)
        self.content.pack(fill="both", expand=True, padx=10, pady=8)

        self.root = app.root
        self.root.bind("<F12>", self._on_f12)
        self.root.bind("<Delete>", self._on_delete)

        self._factories = {
            "venta": self._make_venta,
            "productos": self._make_productos,
            "personal": self._make_personal,
            "proveedores": self._make_proveedores,
            "reportes": self._make_reportes,
            "caja": self._make_caja,
            "cxc": self._make_cxc,
            "cierre_general": self._make_cierre_general,
            "bolsillos": self._make_bolsillos,
            "reportes_admin": self._make_reportes_admin,
        }
        self.show_view("venta")
        self.actualizar_fecha_hora()
        self._sincronizar_offline()
        self.after(2500, self._vigilar_devoluciones)
        self.after(700, self._precargar_vistas)
        self.after(5000, self._acreditar_datafono_pendiente)

    def _precargar_vistas(self, pendientes=None):
        pendientes = list(pendientes or ("productos", "reportes", "cxc", "proveedores", "personal", "caja"))
        if not pendientes or self.cobro_overlay is not None:
            return
        name = pendientes.pop(0)
        if name not in self.views:
            try:
                self.views[name] = self._factories[name]()
            except Exception:
                pass
        if pendientes:
            self.after(220, lambda: self._precargar_vistas(pendientes))

    def _make_venta(self):
        from ventas import VentaView
        return VentaView(self.content, self)

    def _make_productos(self):
        from inventario import Frm_inventario
        return Frm_inventario(self.content, self.app.usuario)

    def _make_personal(self):
        from personal import Personal
        return Personal(self.content, self.app.usuario)

    def _make_proveedores(self):
        from proveedores import Proveedores
        return Proveedores(self.content, self.app.usuario)

    def _make_reportes(self):
        from R_Ventas import R_Ventas
        return R_Ventas(self.content, self.app.usuario, app=self.app)

    def _make_caja(self):
        from entr_sald import entra_sali
        return entra_sali(self.content, self.app.usuario)

    def _make_cxc(self):
        from clientes_cxc import CuentasPorCobrar
        return CuentasPorCobrar(self.content, self.app.usuario)

    def _make_cierre_general(self):
        from cierre_general_ui import CierreGeneralView
        return CierreGeneralView(self.content, usuario=self.app.usuario, app=self.app)

    def _make_bolsillos(self):
        from bolsillos_ui import BolsillosView
        return BolsillosView(self.content, usuario=self.app.usuario, app=self.app)

    def _make_reportes_admin(self):
        from reportes_admin_ui import ReportesAdminView
        return ReportesAdminView(self.content, usuario=self.app.usuario, app=self.app)

    def show_view(self, name):
        if self.cobro_overlay is not None:
            return
        if name in (
            "cierre_general",
            "bolsillos",
            "reportes_admin",
            "personal",
        ) and not getattr(self.app, "es_admin", False):
            return
        for view in self.views.values():
            view.pack_forget()
        if name not in self.views:
            self.views[name] = self._factories[name]()
        view = self.views[name]
        view.pack(fill="both", expand=True)
        self.active = name
        self._set_nav(name)
        titles = {
            "venta": "Punto de venta",
            "productos": "Productos e inventario",
            "personal": "Usuarios y personal",
            "proveedores": "Proveedores",
            "reportes": "Historial de ventas",
            "caja": "Movimientos de caja",
            "cxc": "Cuentas por cobrar",
            "cierre_general": "Cierre general administrativo",
            "bolsillos": "Bolsillos financieros",
            "reportes_admin": "Dashboard reportes admin",
        }
        self.header.set_subtitle(titles.get(name, APP_NAME))
        if hasattr(view, "on_show"):
            self.after_idle(view.on_show)

    def _set_nav(self, name):
        for key, btn in self.nav_buttons.items():
            active = key == name
            bg = ACCENT if active else BG_ELEVATED
            hover = ACCENT_HOVER if active else "#3A4560"
            btn.config(
                bg=bg,
                activebackground=hover,
                highlightbackground=ACCENT if active else BORDER,
                highlightthickness=1,
            )
            bind_hover(btn, bg, hover)

    def venta(self):
        return self.views.get("venta")

    def _on_f12(self, event=None):
        venta = self.venta()
        if venta and self.active == "venta":
            venta.abrir_cobrar()

    def _on_delete(self, event=None):
        if self.cobro_overlay is not None or self.active != "venta":
            return
        venta = self.venta()
        if venta:
            venta.cancelar_producto()
            return "break"

    def set_cobro_overlay(self, overlay):
        self.cobro_overlay = overlay

    def actualizar_fecha_hora(self):
        now = datetime.now()
        hora = now.hour % 12 or 12
        am_pm = "a.m." if now.hour < 12 else "p.m."
        self.header.set_datetime(
            f"{now.day:02d}/{now.month:02d}/{now.year}",
            f"{hora:02d}:{now.minute:02d}:{now.second:02d} {am_pm}",
        )
        self._clock_job = self.after(1000, self.actualizar_fecha_hora)

    def _sincronizar_offline(self):
        try:
            from offline_sync import sincronizar_pendientes, contar_pendientes
            sincronizados, pendientes = sincronizar_pendientes()
            if pendientes:
                self.lbl_sync.config(text=f"Cola offline: {pendientes}", fg=WARNING)
            elif sincronizados:
                self.lbl_sync.config(text=f"Sincronizadas {sincronizados}", fg=SUCCESS)
            else:
                self.lbl_sync.config(text="", fg=TEXT_DIM)
        except Exception:
            pass
        self.after(40000, self._sincronizar_offline)

    def _acreditar_datafono_pendiente(self):
        """A las 14:00 del día hábil siguiente acredita Datafono → billetera digital."""
        try:
            if getattr(self.app, "es_admin", False):
                from bolsillo_proveedores_svc import acreditar_datafono_pendientes

                ok, msg, data = acreditar_datafono_pendientes(
                    usuario_admin=getattr(self.app, "usuario", None) or "sistema"
                )
                monto = 0.0
                try:
                    monto = round(float((data or {}).get("monto") or 0), 2)
                except (TypeError, ValueError):
                    monto = 0.0
                if ok and monto > 0:
                    print("Datafono→billetera: {}".format(msg))
        except Exception as error:
            print("Aviso acreditación datafono: {}".format(error))
        try:
            self.after(60000, self._acreditar_datafono_pendiente)
        except tk.TclError:
            pass

    def _vigilar_devoluciones(self):
        try:
            self._procesar_avisos_devolucion()
        except Exception as error:
            print("Error al vigilar devoluciones: {}".format(error))
        try:
            self.after(5000, self._vigilar_devoluciones)
        except tk.TclError:
            pass

    def _procesar_avisos_devolucion(self):
        from Consultas import (
            aplicar_resolucion_devolucion,
            devoluciones_resueltas_pendientes_aviso,
            marcar_devoluciones_avisadas,
        )

        avisos = devoluciones_resueltas_pendientes_aviso()
        if not avisos:
            return
        usuario = getattr(self.app, "usuario", "") or "caja"
        for aviso in avisos:
            if "APROB" in str(aviso.get("estado") or "").upper():
                aplicar_resolucion_devolucion(
                    aviso.get("venta_id"),
                    aviso.get("estado"),
                    usuario,
                    items=aviso.get("items") or None,
                )
                if not aviso.get("items"):
                    self._marcar_venta_turno_anulada(aviso.get("venta_id"))
        self._forzar_refresco_tras_devolucion()
        if self.cobro_overlay is not None:
            return
        marcar_devoluciones_avisadas([aviso.get("id") for aviso in avisos])
        for aviso in avisos:
            venta_id = aviso.get("venta_id")
            estado = str(aviso.get("estado") or "").upper()
            if "APROB" in estado:
                if aviso.get("items"):
                    mb.showinfo(
                        "Devolución atendida",
                        "La devolución parcial de la venta #{} ya fue atendida por el admin.".format(
                            venta_id
                        ),
                        parent=self,
                    )
                else:
                    mb.showinfo(
                        "Devolución atendida",
                        "La venta #{} anulada ya fue atendida por el admin.".format(venta_id),
                        parent=self,
                    )
            else:
                mb.showinfo(
                    "Devolución rechazada",
                    "El administrador rechazó la devolución de la venta #{}. "
                    "La venta sigue activa.".format(venta_id),
                    parent=self,
                )

    def _marcar_venta_turno_anulada(self, id_venta):
        for venta in getattr(self.app, "ventas_turno", None) or []:
            if str(venta.get("id_venta")) == str(id_venta):
                venta["anulada"] = True

    def _forzar_refresco_tras_devolucion(self):
        reportes = self.views.get("reportes")
        if reportes is not None:
            if hasattr(reportes, "refrescar_ahora"):
                reportes.refrescar_ahora()
            else:
                setattr(reportes, "_last_refresh", 0)
        productos = self.views.get("productos")
        if productos is not None:
            setattr(productos, "_last_refresh", 0)
            if self.active == "productos" and hasattr(productos, "actualizar_tabla"):
                try:
                    productos.actualizar_tabla()
                except Exception:
                    pass

    def cerrar_turno(self):
        if self.cobro_overlay is not None:
            return
        venta = self.venta()
        if venta and venta.tree_venta.get_children():
            if not mb.askyesno(
                "Venta en curso",
                "Hay productos en el carrito. ¿Cerrar el turno de todas formas?",
                parent=self,
            ):
                return
        from cierre_turno import CierreTurnoOverlay
        overlay = CierreTurnoOverlay(self, self.app, on_close=lambda: self.set_cobro_overlay(None), modo="definitivo")
        self.set_cobro_overlay(overlay)

    def arqueo_temporal(self):
        if self.cobro_overlay is not None:
            return
        venta = self.venta()
        if venta and venta.tree_venta.get_children():
            if not mb.askyesno(
                "Venta en curso",
                "Hay productos en el carrito. ¿Hacer arqueo temporal de todas formas?",
                parent=self,
            ):
                return
        if not mb.askyesno(
            "Arqueo temporal",
            "Esto cierra su responsabilidad, deja la base en el gabinete y permite que otro cajero inicie sesión.\n\n"
            "¿Continuar?",
            parent=self,
        ):
            return
        from cierre_turno import CierreTurnoOverlay
        overlay = CierreTurnoOverlay(self, self.app, on_close=lambda: self.set_cobro_overlay(None), modo="temporal")
        self.set_cobro_overlay(overlay)

    def reimprimir_ticket_cierre(self):
        if self.cobro_overlay is not None:
            return
        from reimpresion_cierre import mostrar_reimpresion_cierres

        mostrar_reimpresion_cierres(self, getattr(self.app, "usuario", None), forzar=True)


class ZyntraApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.zyntra_app = self
        setup_app_root(self.root)
        self.usuario = None
        self.es_admin = False
        self.id_empleado = None
        self.monto_inicial = 0.0
        self.turno_inicio = None
        self.ventas_turno = []
        try:
            from Consultas import ensure_schema
            ensure_schema()
        except Exception as error:
            print("No se pudo actualizar el esquema: {}".format(error))
        self.container = tk.Frame(self.root, bg=BG)
        self.container.pack(fill="both", expand=True)
        self.shell = None
        self._permitir_salida = False
        self.root.protocol("WM_DELETE_WINDOW", self._on_cerrar_ventana)
        self.show_login()
        self.root.mainloop()

    def _on_cerrar_ventana(self):
        if self._permitir_salida:
            try:
                from conexionLogin import FormularioLogin
                FormularioLogin.cerrar_conexion()
            except Exception:
                pass
            self.root.destroy()
            return
        if self.shell is None:
            if mb.askyesno("Salir", "¿Salir de Zyntra POS?", parent=self.root):
                self._permitir_salida = True
                try:
                    from conexionLogin import FormularioLogin
                    FormularioLogin.cerrar_conexion()
                except Exception:
                    pass
                self.root.destroy()
            return
        overlay = getattr(self.shell, "cobro_overlay", None)
        if overlay is not None:
            from cierre_turno import CierreTurnoOverlay
            if isinstance(overlay, CierreTurnoOverlay):
                mb.showinfo(
                    "Cierre de turno",
                    "El turno sigue abierto. Termine el arqueo de caja para salir.",
                    parent=self.root,
                )
                return
            mb.showwarning(
                "Operación en curso",
                "Termine o cancele el cobro antes de cerrar el turno.",
                parent=self.root,
            )
            return
        mb.showwarning(
            "Turno abierto",
            "No se puede salir con la X: hay un turno de caja abierto.\n\n"
            "Debe hacer el cierre de turno (conteo de efectivo y arqueo) para que cuadre la caja.",
            parent=self.root,
        )
        self.shell.cerrar_turno()

    def show_login(self):
        from login import LoginView
        clear_container(self.container)
        LoginView(self.container, self)

    def show_apertura(self, usuario):
        from apertura_caja import AperturaView
        self.usuario = usuario
        try:
            from cierre_general_svc import es_usuario_admin

            self.es_admin = bool(es_usuario_admin(usuario))
        except Exception:
            self.es_admin = False
        clear_container(self.container)
        AperturaView(self.container, self, usuario)

    def show_shell(self):
        clear_container(self.container)
        self.shell = PosShell(self.container, self)
        self.root.after(800, self._alerta_vencimientos)
        self.root.after(1200, self._alerta_tickets_cierre)

    def _alerta_tickets_cierre(self):
        try:
            from reimpresion_cierre import avisar_tickets_pendientes

            if self.shell is not None:
                avisar_tickets_pendientes(self.shell, self.usuario)
        except Exception as error:
            print("No se pudo avisar tickets de cierre: {}".format(error))

    def _alerta_vencimientos(self):
        try:
            from inventario import avisar_vencimientos
            avisar_vencimientos(self.root, self)
        except Exception as error:
            print("No se pudo mostrar la alerta de vencimientos: {}".format(error))


def run_app():
    ZyntraApp()
