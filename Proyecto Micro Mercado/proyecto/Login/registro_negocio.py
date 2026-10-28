import tkinter as tk
import mensaje as mb
from usuarios import *
import Consultas
import cuenta_admin
from zyntra_ui import *


class RegistroNegocio:
    def __init__(self):
        self.registro = tk.Tk()
        setup_window(self.registro, "Registro de Negocio", 754, 483)
        self.items()
        self.registro.mainloop()

    def items(self):
        self.ancho_ventana = 754
        self.alto_ventana = 483
        self.canvas1 = draw_background(self.registro, self.ancho_ventana, self.alto_ventana)
        draw_header(self.canvas1, self.ancho_ventana, "Configuración inicial")

        rounded_rect(self.canvas1, 70, 120, 684, 430, radius=16, fill=BG_CARD)
        canvas_label(self.canvas1, 377, 160, "Registra tu negocio", FONT_HEADING, TEXT, "center")
        canvas_label(self.canvas1, 110, 210, "Nombre del negocio", FONT_LABEL, TEXT_MUTED)
        canvas_label(self.canvas1, 110, 290, "Dirección", FONT_LABEL, TEXT_MUTED)

        self.caja_nombre_negocio = styled_entry(self.registro, width=46)
        self.caja_nombre_negocio.place(x=110, y=230)

        self.caja_direccion = styled_entry(self.registro, width=46)
        self.caja_direccion.place(x=110, y=310)

        self.boton_registrar = primary_button(self.registro, "Registrar Negocio", self.registrar_negocio, width=22)
        self.boton_registrar.place(x=250, y=370)

    def registrar_negocio(self):
        nombre_negocio = self.caja_nombre_negocio.get()
        direccion = self.caja_direccion.get()

        if Consultas.registrar_negocio(nombre_negocio, direccion) == True:
            mb.showinfo("Éxito", "Negocio registrado exitosamente.")
            self.registro.destroy()
            cuenta_admin.CuentaAdmin()
        elif nombre_negocio == "" or direccion == "":
            mb.showerror("Error", "Por favor, complete todos los campos.")
        else:
            mb.showerror("Error", "No se pudo registrar el negocio. Verifique los datos e intente nuevamente.")
            self.caja_nombre_negocio.delete(0, tk.END)
            self.caja_direccion.delete(0, tk.END)


RegistroNegocio()
