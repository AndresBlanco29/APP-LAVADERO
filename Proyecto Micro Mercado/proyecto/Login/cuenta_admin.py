import tkinter as tk
import mensaje as mb
from usuarios import *
import Consultas
import login
from zyntra_ui import *


class CuentaAdmin:
    def __init__(self):
        self.cuenta_admin = tk.Tk()
        setup_window(self.cuenta_admin, "Cuenta de Administrador", 704, 560)
        self.items()
        self.cuenta_admin.mainloop()

    def items(self):
        self.ancho_ventana = 704
        self.alto_ventana = 560
        self.canvas1 = draw_background(self.cuenta_admin, self.ancho_ventana, self.alto_ventana)
        draw_header(self.canvas1, self.ancho_ventana, "Crear administrador")

        rounded_rect(self.canvas1, 70, 110, 634, 520, radius=16, fill=BG_CARD)
        canvas_label(self.canvas1, 110, 145, "Usuario", FONT_LABEL, TEXT_MUTED)
        canvas_label(self.canvas1, 110, 210, "Contraseña", FONT_LABEL, TEXT_MUTED)
        canvas_label(self.canvas1, 110, 275, "Nombre completo", FONT_LABEL, TEXT_MUTED)
        canvas_label(self.canvas1, 110, 340, "Teléfono", FONT_LABEL, TEXT_MUTED)
        canvas_label(self.canvas1, 110, 405, "Correo", FONT_LABEL, TEXT_MUTED)

        self.caja_usuario = styled_entry(self.cuenta_admin, width=42)
        self.caja_usuario.place(x=110, y=162)

        self.caja_contrasena = styled_entry(self.cuenta_admin, width=42, show="*")
        self.caja_contrasena.place(x=110, y=227)

        self.caja_nombre_completo = styled_entry(self.cuenta_admin, width=42)
        self.caja_nombre_completo.place(x=110, y=292)

        self.caja_telefono = styled_entry(self.cuenta_admin, width=42)
        self.caja_telefono.place(x=110, y=357)

        self.caja_correo = styled_entry(self.cuenta_admin, width=42)
        self.caja_correo.place(x=110, y=422)

        self.boton_registrar_admin = primary_button(
            self.cuenta_admin, "Registrar Admin", self.registrar_admin, width=22
        )
        self.boton_registrar_admin.place(x=220, y=470)

    def registrar_admin(self):
        usuario = self.caja_usuario.get()
        contraseña = self.caja_contrasena.get()
        nombre_completo = self.caja_nombre_completo.get()
        telefono = self.caja_telefono.get()
        correo = self.caja_correo.get()

        if not usuario or not contraseña or not nombre_completo or not telefono or not correo:
            mb.showerror("Error", "Por favor, completa todos los campos.")
            return

        if Consultas.registrar_admin(usuario, contraseña, nombre_completo, telefono, correo):
            mb.showinfo("Éxito", "Administrador registrado exitosamente.")
            self.cuenta_admin.destroy()
            login.login()
        else:
            mb.showerror("Error", "Error al registrar el administrador.")
