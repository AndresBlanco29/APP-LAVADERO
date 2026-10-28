import tkinter as tk
import mensaje as mb
from Consultas import *
from zyntra_ui import *


class nuevo_usuario:
    def __init__(self, parent=None):
        self.nuevo_usuario = tk.Toplevel(parent) if parent else tk.Toplevel()
        prepare_modal(self.nuevo_usuario, parent, "Nuevos Usuarios", 560, 560)
        self.items()

    def items(self):
        self.ancho_ventana = 652
        self.alto_ventana = 620
        self.canvas1 = draw_background(self.nuevo_usuario, self.ancho_ventana, self.alto_ventana)
        draw_header(self.canvas1, self.ancho_ventana, "Agregar usuario")

        rounded_rect(self.canvas1, 40, 110, 612, 580, radius=16, fill=BG_CARD)
        canvas_label(self.canvas1, 70, 150, "Usuario", FONT_LABEL, TEXT_MUTED)
        canvas_label(self.canvas1, 70, 220, "Contraseña", FONT_LABEL, TEXT_MUTED)
        canvas_label(self.canvas1, 70, 290, "Nombre", FONT_LABEL, TEXT_MUTED)
        canvas_label(self.canvas1, 70, 360, "Teléfono", FONT_LABEL, TEXT_MUTED)
        canvas_label(self.canvas1, 70, 430, "Correo", FONT_LABEL, TEXT_MUTED)

        self.nombre_usuario = styled_entry(self.nuevo_usuario, width=32)
        self.nombre_usuario.place(x=250, y=138)
        self.nombre_usuario.focus()

        self.contraseña_usuario = styled_entry(self.nuevo_usuario, width=32, show="*")
        self.contraseña_usuario.place(x=250, y=208)

        self.Nombre = styled_entry(self.nuevo_usuario, width=32)
        self.Nombre.place(x=250, y=278)

        self.numero = styled_entry(self.nuevo_usuario, width=32)
        self.numero.place(x=250, y=348)

        self.correo = styled_entry(self.nuevo_usuario, width=32)
        self.correo.place(x=250, y=418)

        self.guardar_usuario = primary_button(
            self.nuevo_usuario, "Agregar usuario", self.guardar_nuevo_usuario, width=24
        )
        self.guardar_usuario.place(relx=0.5, rely=1.0, y=-24, anchor="s")

    def guardar_nuevo_usuario(self):
        try:
            usuario = self.nombre_usuario.get()
            password = self.contraseña_usuario.get()
            nombre = self.nombre_usuario.get()
            telefono = self.numero.get()
            correo = self.correo.get()

            if not all([usuario, password, nombre]):
                mb.showwarning("Advertencia", "Debe llenar todos los campos", parent=self.nuevo_usuario)
                return

            Agregar_Personal(usuario, password, nombre, telefono, correo)
            mb.showinfo("Exito", "El usuario se agrego correctamente", parent=self.nuevo_usuario)
            self.limpiar_cajas()
            self.nombre_usuario.focus()
        except ValueError as error:
            mb.showerror("Error al agregar el nuevo usuario{}".format(error), parent=self.nuevo_usuario)

    def limpiar_cajas(self):
        self.nombre_usuario.delete(0, tk.END)
        self.contraseña_usuario.delete(0, tk.END)
        self.Nombre.delete(0, tk.END)
        self.numero.delete(0, tk.END)
        self.correo.delete(0, tk.END)
