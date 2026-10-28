import tkinter as tk
import mensaje as mb
from Consultas import *
from zyntra_ui import *


class modificar_usuarios:
    def __init__(self, usuario_data, parent=None):
        self.usuario_data = usuario_data
        self.modi_usuarios = tk.Toplevel(parent) if parent else tk.Toplevel()
        prepare_modal(self.modi_usuarios, parent, "Modificar Usuarios", 560, 560)
        self.items()

    def items(self):
        self.ancho_ventana = 652
        self.alto_ventana = 620
        self.canvas1 = draw_background(self.modi_usuarios, self.ancho_ventana, self.alto_ventana)
        draw_header(self.canvas1, self.ancho_ventana, "Modificar usuario")

        rounded_rect(self.canvas1, 40, 110, 612, 580, radius=16, fill=BG_CARD)
        canvas_label(self.canvas1, 70, 165, "Usuario", FONT_LABEL, TEXT_MUTED)
        canvas_label(self.canvas1, 70, 245, "Contraseña", FONT_LABEL, TEXT_MUTED)
        canvas_label(self.canvas1, 70, 325, "Nombre", FONT_LABEL, TEXT_MUTED)
        canvas_label(self.canvas1, 70, 405, "Teléfono", FONT_LABEL, TEXT_MUTED)

        self.modi_Id = styled_entry(self.modi_usuarios, width=32)
        self.modi_Id.place_forget()
        self.modi_Id.insert(0, self.usuario_data[0])

        self.modi_nombre_usuario = styled_entry(self.modi_usuarios, width=32)
        self.modi_nombre_usuario.place(x=250, y=152)
        self.modi_nombre_usuario.insert(0, self.usuario_data[1])

        self.modi_contraseña_usuario = styled_entry(self.modi_usuarios, width=32)
        self.modi_contraseña_usuario.place(x=250, y=232)
        self.modi_contraseña_usuario.insert(0, self.usuario_data[2])

        self.modi_Nombre = styled_entry(self.modi_usuarios, width=32)
        self.modi_Nombre.place(x=250, y=312)
        self.modi_Nombre.insert(0, self.usuario_data[3])

        self.modi_numero = styled_entry(self.modi_usuarios, width=32)
        self.modi_numero.place(x=250, y=392)
        self.modi_numero.insert(0, self.usuario_data[4])

        self.modi_usuario = primary_button(self.modi_usuarios, "Modificar usuario", self.modificar_usuario, width=24)
        self.modi_usuario.place(relx=0.5, rely=1.0, y=-24, anchor="s")

    def modificar_usuario(self):
        try:
            codigo = self.modi_Id.get()
            usuario = self.modi_nombre_usuario.get()
            password = self.modi_contraseña_usuario.get()
            nombre_empleado = self.modi_Nombre.get()
            telefono = self.modi_numero.get()

            if not all([codigo, usuario, password, nombre_empleado, telefono]):
                mb.showwarning("Advertencia", "Todos los campos son obligatorios", parent=self.modi_usuarios)
                return

            personal_modi = modificar_personal(usuario, password, nombre_empleado, telefono, codigo)
            if personal_modi:
                mb.showinfo("Exito", "Los datos han sido modificado correctamente", parent=self.modi_usuarios)
                self.limpiar_cajas()
        except ValueError as error:
            mb.showerror("Error", "Error al modificar los datos {}".format(error), parent=self.modi_usuarios)

    def limpiar_cajas(self):
        self.modi_Id.delete(0, tk.END)
        self.modi_nombre_usuario.delete(0, tk.END)
        self.modi_contraseña_usuario.delete(0, tk.END)
        self.modi_Nombre.delete(0, tk.END)
        self.modi_numero.delete(0, tk.END)
