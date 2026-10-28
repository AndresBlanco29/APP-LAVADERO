import tkinter as tk
import mensaje as mb
from tkcalendar import DateEntry
from datetime import datetime, timedelta
from Consultas import *
from zyntra_ui import *


class His_entr_sali:
    def __init__(self, parent=None):
        self.His_entr_sali = tk.Toplevel(parent) if parent else tk.Toplevel()
        prepare_modal(self.His_entr_sali, parent, "Historial de entrada y salida", 1050, 720, resizable=True)
        self.items()

    def items(self):
        self.ancho_ventana = 1050
        self.alto_ventana = 720
        self.canvas1 = draw_background(self.His_entr_sali, self.ancho_ventana, self.alto_ventana)
        draw_header(self.canvas1, self.ancho_ventana, "Historial de caja")

        self.desde = styled_label(self.His_entr_sali, "Buscar del", FONT_SUB, TEXT_MUTED, BG)
        self.desde.place(x=30, y=108)

        self.fecha_desde = DateEntry(
            self.His_entr_sali,
            width=12,
            background=ACCENT,
            foreground="white",
            borderwidth=2,
            year=datetime.now().year,
            font=("Segoe UI", 11, "bold"),
            locale="es_ES",
        )
        self.fecha_desde.place(x=140, y=108)

        self.al = styled_label(self.His_entr_sali, "al", FONT_SUB, TEXT_MUTED, BG)
        self.al.place(x=300, y=108)

        self.fecha_hasta = DateEntry(
            self.His_entr_sali,
            width=12,
            background=ACCENT,
            foreground="white",
            borderwidth=2,
            year=datetime.now().year,
            font=("Segoe UI", 11, "bold"),
            locale="es_ES",
        )
        self.fecha_hasta.place(x=340, y=108)

        self.buscar_btn = primary_button(self.His_entr_sali, "Buscar", self.buscar_movimientos_Fecha, width=10)
        self.buscar_btn.place(x=500, y=100)

        self.Entrada = styled_label(self.His_entr_sali, "Entradas", FONT_HEADING, TEXT, BG)
        self.Entrada.place(x=30, y=160)

        self.Salida = styled_label(self.His_entr_sali, "Salidas", FONT_HEADING, TEXT, BG)
        self.Salida.place(x=540, y=160)

        self.tree_his_entr = themed_treeview(
            self.His_entr_sali,
            columns=("Id_Entrada", "Asunto", "Cantidad", "Cajero", "Fecha"),
            headings=("ID", "Asunto", "Cantidad", "Cajero", "Fecha"),
            height=10,
        )
        self.tree_his_entr.column("Id_Entrada", anchor="center", width=60)
        self.tree_his_entr.column("Asunto", anchor="w", width=140)
        self.tree_his_entr.column("Cantidad", anchor="center", width=80)
        self.tree_his_entr.column("Cajero", anchor="center", width=110)
        self.tree_his_entr.column("Fecha", anchor="center", width=100)
        self.tree_his_entr.place(x=20, y=200, height=280)

        for row in mostrar_entrada_dinero() or []:
            vals = list(row)
            if len(vals) > 2:
                vals[2] = formato_dinero(vals[2])
            self.tree_his_entr.insert("", "end", values=vals)

        self.tree_his_sal = themed_treeview(
            self.His_entr_sali,
            columns=("Id_Salida", "Asunto", "Cantidad", "Cajero", "Fecha"),
            headings=("ID", "Asunto", "Cantidad", "Cajero", "Fecha"),
            height=10,
        )
        self.tree_his_sal.column("Id_Salida", anchor="center", width=60)
        self.tree_his_sal.column("Asunto", anchor="w", width=140)
        self.tree_his_sal.column("Cantidad", anchor="center", width=80)
        self.tree_his_sal.column("Cajero", anchor="center", width=110)
        self.tree_his_sal.column("Fecha", anchor="center", width=100)
        self.tree_his_sal.place(x=540, y=200, height=280)

        for row in mostrar_salida_dinero() or []:
            vals = list(row)
            if len(vals) > 2:
                vals[2] = formato_dinero(vals[2])
            self.tree_his_sal.insert("", "end", values=vals)

        self.total_entrada = styled_label(self.His_entr_sali, "Total en entradas", FONT_LABEL, TEXT_MUTED, BG)
        self.total_entrada.place(x=20, y=510)
        self.en_total_entrada = styled_entry(self.His_entr_sali, width=16)
        self.en_total_entrada.place(x=170, y=505)

        self.total_salida = styled_label(self.His_entr_sali, "Total en salidas", FONT_LABEL, TEXT_MUTED, BG)
        self.total_salida.place(x=540, y=510)
        self.en_total_salida = styled_entry(self.His_entr_sali, width=16)
        self.en_total_salida.place(x=680, y=505)

        self.actualizar = primary_button(self.His_entr_sali, "Actualizar tablas", self.actualizar_tabla, width=22)
        self.actualizar.place(relx=0.5, rely=1.0, y=-18, anchor="s")

        self.actualizar_tabla()

    def buscar_ventas_Fecha(self):
        pass

    def actualizar_tabla(self):
        try:
            self.tree_his_entr.delete(*self.tree_his_entr.get_children())
            resultado_entrada = mostrar_entrada_dinero()
            total_entrada = 0
            total_salida = 0

            for row in resultado_entrada:
                vals = list(row)
                if len(vals) > 2:
                    vals[2] = formato_dinero(vals[2])
                self.tree_his_entr.insert("", tk.END, values=vals)
                total_entrada += parse_dinero(row[2])

            self.en_total_entrada.delete(0, tk.END)
            self.en_total_entrada.insert(0, formato_dinero(total_entrada))

            self.tree_his_sal.delete(*self.tree_his_sal.get_children())
            resultado_salida = mostrar_salida_dinero()
            total_salida = 0

            for row in resultado_salida:
                vals = list(row)
                if len(vals) > 2:
                    vals[2] = formato_dinero(vals[2])
                self.tree_his_sal.insert("", tk.END, values=vals)
                total_salida += parse_dinero(row[2])

            self.en_total_salida.delete(0, tk.END)
            self.en_total_salida.insert(0, formato_dinero(total_salida))
        except ValueError as error:
            mb.showerror("Error", "Error al actualizar la tabla {}".format(error), parent=self.His_entr_sali)

    def buscar_movimientos_Fecha(self):
        fecha_inicio = self.fecha_desde.get_date().strftime("%Y-%m-%d")
        fecha_fin = self.fecha_hasta.get_date().strftime("%Y-%m-%d")

        if fecha_inicio == fecha_fin:
            fecha_fin = (self.fecha_hasta.get_date() + timedelta(days=1)).strftime("%Y-%m-%d")

        busqueda = mostrar_movimientos_por_fecha(fecha_inicio, fecha_fin)

        if not busqueda:
            mb.showinfo("Resultado", "No se encontraron movimientos en este periodo.", parent=self.His_entr_sali)
            return

        for item in self.tree_his_entr.get_children():
            self.tree_his_entr.delete(item)

        for movimiento in busqueda:
            vals = list(movimiento)
            if len(vals) > 2:
                vals[2] = formato_dinero(vals[2])
            self.tree_his_entr.insert("", "end", values=vals)
