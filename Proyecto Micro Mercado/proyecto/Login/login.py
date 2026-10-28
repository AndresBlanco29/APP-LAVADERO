import tkinter as tk
import mensaje as mb
import usuarios
from zyntra_ui import *


class LoginView(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=BG)
        self.app = app
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

        self.lbl_tagline = styled_label(
            self.card, "Sistemas que impulsan tu crecimiento.", ("Segoe UI", 13), TEXT, BG_CARD
        )
        self.lbl_tagline.pack()
        self.lbl_hint = styled_label(
            self.card, "Inicia sesión para continuar", ("Segoe UI", 11), TEXT_DIM, BG_CARD
        )
        self.lbl_hint.pack(pady=(6, 28))

        self.box_user, self.caja_usuario = labeled_field(self.card, "Usuario")
        self.box_user.pack(fill="x", pady=(0, 18))
        self.caja_usuario.configure(font=("Segoe UI", 14), width=1)
        self.caja_usuario.focus()

        self.box_pass, self.caja_contraseña = labeled_field(self.card, "Contraseña")
        self.box_pass.pack(fill="x")
        self.caja_contraseña.configure(font=("Segoe UI", 14), width=1, show="*")
        self.caja_contraseña.bind("<Return>", lambda _e: self.validar_login())

        self.btn_entrar = primary_button(
            self.card, "Entrar", self.validar_login, width=1, height=2, font=("Segoe UI", 13, "bold")
        )
        self.btn_entrar.pack(fill="x", pady=(28, 0))

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

        # Ancho del card: ~40% de la ventana, con mínimos/máximos según pantalla.
        card_w = int(w * 0.42)
        card_w = max(440, min(card_w, 680, w - 48))
        if w < 520:
            card_w = max(300, w - 32)

        # Escala tipográfica suave según el ancho del card.
        scale = max(0.9, min(1.25, card_w / 520))
        title_size = max(24, int(28 * scale))
        tag_size = max(12, int(14 * scale))
        hint_size = max(10, int(12 * scale))
        field_size = max(13, int(15 * scale))
        btn_size = max(12, int(14 * scale))
        logo_size = max(52, int(68 * scale))
        brand_h = max(44, int(56 * scale))
        pad_x = max(36, int(56 * scale))
        pad_y = max(32, int(48 * scale))

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

        self.lbl_tagline.configure(font=("Segoe UI", tag_size))
        self.lbl_hint.configure(font=("Segoe UI", hint_size))
        label_size = max(11, int(12 * scale))
        for box in (self.box_user, self.box_pass):
            for child in box.winfo_children():
                if isinstance(child, tk.Label):
                    child.configure(font=("Segoe UI", label_size))
        self.caja_usuario.configure(font=("Segoe UI", field_size))
        self.caja_contraseña.configure(font=("Segoe UI", field_size))
        self.btn_entrar.configure(font=("Segoe UI", btn_size, "bold"), height=2 if scale >= 1 else 1)

    def _on_resize(self, event=None):
        if event is not None and event.widget is not self:
            return
        self.after_idle(self._aplicar_tamano)

    def validar_login(self):
        usuario = self.caja_usuario.get()
        contraseña = self.caja_contraseña.get()

        if usuarios.usuarios.ValidacionUsuarios(usuario, contraseña):
            mb.showinfo("Éxito", "Bienvenido", parent=self)
            self.app.show_apertura(usuario)
        else:
            mb.showerror("Error", "Usuario o contraseña incorrectos", parent=self)


class login:
    def __init__(self):
        from app_shell import run_app
        run_app()


if __name__ == "__main__":
    login()
