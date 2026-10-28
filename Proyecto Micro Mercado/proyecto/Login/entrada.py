import tkinter as tk
import mensaje as mb
from Consultas import *
import usuarios
from datetime import datetime
from zyntra_ui import *


class entrada_dinero:
    def __init__(self, usuario, parent=None):
        self.usuario = usuario
        self.entrada_dinero = tk.Toplevel(parent) if parent else tk.Toplevel()
        prepare_modal(self.entrada_dinero, parent, "Entrada de dinero", 560, 360)
        self.items()

    def items(self):
        self.ancho_ventana = 633
        self.alto_ventana = 380
        self.canvas1 = draw_background(self.entrada_dinero, self.ancho_ventana, self.alto_ventana)
        draw_header(self.canvas1, self.ancho_ventana, "Registrar entrada")

        rounded_rect(self.canvas1, 24, 110, 430, 340, radius=16, fill=BG_CARD)
        canvas_label(self.canvas1, 48, 145, "Cantidad", FONT_LABEL, TEXT_MUTED)
        canvas_label(self.canvas1, 48, 230, "Comentarios", FONT_LABEL, TEXT_MUTED)

        self.cantidad_dinero = styled_entry(self.entrada_dinero, width=18)
        self.cantidad_dinero.place(x=48, y=162)
        bind_money_entry(self.cantidad_dinero)
        self.cantidad_dinero.focus()

        self.comentarios = styled_entry(self.entrada_dinero, width=34)
        self.comentarios.place(x=48, y=248)

        self.btn_guardar = primary_button(self.entrada_dinero, "Guardar", self.guardar_entrada, width=12)
        self.btn_guardar.place(x=460, y=140)

        self.btn_cancelar = secondary_button(self.entrada_dinero, "Cancelar", self.cancelar, width=12)
        self.btn_cancelar.place(x=460, y=210)

    def validar_numero(self, texto):
        if texto == "" or texto.isdigit():
            return True
        else:
            return False

    def guardar_entrada(self):
        nombre_usuario = usuarios.usuarios.Obtener_Nombre_Empleado(self.usuario)
        cantidad = parse_dinero(self.cantidad_dinero.get())
        comentarios = self.comentarios.get().strip()
        fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if cantidad <= 0 or not comentarios:
            mb.showerror("Error", "Por favor, llene los campos", parent=self.entrada_dinero)
        else:
            mb.showinfo("Éxito", "Entrada de dinero guardada correctamente.", parent=self.entrada_dinero)
            Agregar_entrada_dinero(cantidad, comentarios, nombre_usuario, fecha_actual)
            self.cantidad_dinero.delete(0, tk.END)
            self.comentarios.delete(0, tk.END)

    def cancelar(self):
        self.entrada_dinero.destroy()
