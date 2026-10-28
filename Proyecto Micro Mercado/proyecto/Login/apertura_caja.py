import tkinter as tk
import mensaje as mb
import Consultas
from zyntra_ui import *
from datetime import datetime
import usuarios


class AperturaView(tk.Frame):
    def __init__(self, parent, app, nombre):
        super().__init__(parent, bg=BG)
        self.app = app
        self.nombre_usuario = nombre
        self.pack(fill="both", expand=True)
        self._last_w = 0
        self._last_h = 0

        self.holder = tk.Frame(self, bg=BG)
        self.holder.place(relx=0.5, rely=0.5, anchor="center")

        self.card = card_frame(self.holder, padx=56, pady=48)
        self.card.pack(fill="both", expand=True)

        self.logo = tk.Canvas(self.card, width=64, height=64, bg=BG_CARD, highlightthickness=0)
        self.logo.pack()

        self.brand = tk.Canvas(self.card, width=360, height=52, bg=BG_CARD, highlightthickness=0)
        self.brand.pack(pady=(16, 6))

        self.lbl_titulo = styled_label(self.card, "Apertura de caja", ("Segoe UI", 14), TEXT_MUTED, BG_CARD)
        self.lbl_titulo.pack(pady=(2, 6))
        self.lbl_turno = styled_label(
            self.card, f"Turno de {self.nombre_usuario}", ("Segoe UI", 13), TEXT, BG_CARD
        )
        self.lbl_turno.pack(pady=(0, 28))

        self.box_fecha, self.caja_fecha = labeled_field(self.card, "Fecha")
        self.box_fecha.pack(fill="x", pady=(0, 18))
        self.caja_fecha.configure(font=("Segoe UI", 14), width=1)
        self.caja_fecha.insert(0, datetime.now().strftime("%Y-%m-%d"))

        self.box_monto, self.monto_inicial = labeled_field(self.card, "Registre base inicial $")
        self.box_monto.pack(fill="x")
        self.monto_inicial.configure(font=("Segoe UI", 14), width=1)
        bind_money_entry(self.monto_inicial)
        try:
            base_cfg = int(round(float(Consultas.base_gabinete_config() or 0)))
        except Exception:
            base_cfg = 0
        if base_cfg > 0:
            self.monto_inicial.insert(0, formato_entrada(str(base_cfg)))
        self.lbl_base_hint = styled_label(
            self.card,
            "Base definida por admin. Debe quedar en el gabinete.",
            ("Segoe UI", 10),
            TEXT_DIM,
            BG_CARD,
        )
        self.lbl_base_hint.pack(anchor="w", pady=(8, 0))
        self.monto_inicial.focus()
        self.monto_inicial.bind("<Return>", lambda _e: self.aceptar())

        self.btn_aceptar = primary_button(
            self.card, "Aceptar", self.aceptar, width=1, height=2, font=("Segoe UI", 13, "bold")
        )
        self.btn_aceptar.pack(fill="x", pady=(28, 0))

        self.bind("<Configure>", self._on_resize)
        self.after_idle(self._aplicar_tamano)

    def _medir_ventana(self):
        w = self.winfo_width()
        h = self.winfo_height()
        if w < 80 or h < 80:
            try:
                top = self.winfo_toplevel()
                w = max(w, top.winfo_width())
                h = max(h, top.winfo_height())
            except tk.TclError:
                pass
        return max(w, 320), max(h, 240)

    def _aplicar_tamano(self):
        w, h = self._medir_ventana()
        if abs(w - self._last_w) < 8 and abs(h - self._last_h) < 8:
            return
        self._last_w = w
        self._last_h = h

        card_w = int(w * 0.42)
        card_w = max(440, min(card_w, 680, w - 48))
        if w < 520:
            card_w = max(300, w - 32)

        scale = max(0.9, min(1.25, card_w / 520))
        title_size = max(24, int(28 * scale))
        sub_size = max(12, int(14 * scale))
        turno_size = max(12, int(13 * scale))
        field_size = max(13, int(15 * scale))
        btn_size = max(12, int(14 * scale))
        logo_size = max(52, int(68 * scale))
        brand_h = max(44, int(56 * scale))
        pad_x = max(36, int(56 * scale))
        pad_y = max(32, int(48 * scale))
        label_size = max(11, int(12 * scale))

        self.holder.place_configure(width=card_w)
        self.card.configure(padx=pad_x, pady=pad_y)

        self.logo.configure(width=logo_size, height=logo_size)
        self.logo.delete("all")
        mark = max(40, logo_size - 12)
        draw_logo_mark(self.logo, (logo_size - mark) // 2, (logo_size - mark) // 2, mark)

        brand_w = max(240, card_w - pad_x * 2)
        self.brand.configure(width=brand_w, height=brand_h)
        self.brand.delete("all")
        draw_gradient_text(
            self.brand,
            brand_w // 2,
            brand_h // 2,
            APP_NAME,
            ("Segoe UI", title_size, "bold"),
            anchor="center",
        )

        self.lbl_titulo.configure(font=("Segoe UI", sub_size))
        self.lbl_turno.configure(font=("Segoe UI", turno_size))
        if hasattr(self, "lbl_base_hint"):
            self.lbl_base_hint.configure(font=("Segoe UI", max(9, int(10 * scale))))
        for box in (self.box_fecha, self.box_monto):
            for child in box.winfo_children():
                if isinstance(child, tk.Label):
                    child.configure(font=("Segoe UI", label_size))
        self.caja_fecha.configure(font=("Segoe UI", field_size))
        self.monto_inicial.configure(font=("Segoe UI", field_size))
        self.btn_aceptar.configure(font=("Segoe UI", btn_size, "bold"), height=2 if scale >= 1 else 1)

    def _on_resize(self, event=None):
        if event is not None and event.widget is not self:
            return
        self.after_idle(self._aplicar_tamano)

    def aceptar(self):
        fecha = self.caja_fecha.get()
        monto_texto = self.monto_inicial.get().strip()
        if not monto_texto:
            mb.showerror("Error", "Ingrese el monto inicial de caja.", parent=self)
            return
        monto_valor = parse_dinero(monto_texto)
        if monto_valor < 0:
            mb.showerror("Error", "El monto inicial debe ser numérico.", parent=self)
            return
        if Consultas.apertura_caja(fecha, monto_valor):
            id_empleado = usuarios.usuarios.Obtener_Id_Empleado(self.nombre_usuario)
            if id_empleado is None:
                mb.showerror("Error", "No se encontró el ID del empleado. Por favor, verifique los datos.", parent=self)
                return
            self.app.id_empleado = id_empleado
            self.app.monto_inicial = monto_valor
            self.app.turno_inicio = datetime.now()
            self.app.ventas_turno = []
            try:
                from turno_linea_tiempo import (
                    sembrar_linea_tiempo_desde_bd,
                    registrar_evento_turno,
                )

                sembrar_linea_tiempo_desde_bd(self.app)
                registrar_evento_turno(self.app, "apertura", self.app.turno_inicio)
            except Exception as error:
                print("Aviso línea tiempo apertura: {}".format(error))
            mb.showinfo("Éxito", "Apertura de caja registrada con éxito.", parent=self)
            self.app.show_shell()
        else:
            mb.showerror(
                "Error",
                "No se pudo registrar la apertura de caja. Verifique los datos e intente nuevamente.",
                parent=self,
            )


class apertura_caja:
    def __init__(self, nombre):
        from app_shell import ZyntraApp
        app = ZyntraApp.__new__(ZyntraApp)
        app.root = tk.Tk()
        setup_app_root(app.root)
        app.usuario = nombre
        app.id_empleado = None
        app.container = tk.Frame(app.root, bg=BG)
        app.container.pack(fill="both", expand=True)
        app.shell = None
        app.show_apertura(nombre)
        app.root.mainloop()
