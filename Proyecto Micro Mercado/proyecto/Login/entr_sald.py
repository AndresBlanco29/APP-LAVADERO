import tkinter as tk
import historial_entr
import entrada
import salida
from zyntra_ui import *


class entra_sali(tk.Frame):
    def __init__(self, parent, usuario):
        super().__init__(parent, bg=BG)
        self.usuario = usuario
        self.entra_sali = self
        self.items()

    def items(self):
        holder = tk.Frame(self, bg=BG)
        holder.place(relx=0.5, rely=0.45, anchor="center")
        card = card_frame(holder, padx=36, pady=32)
        card.pack()
        styled_label(card, "Movimientos de caja", FONT_HEADING, TEXT, BG_CARD).pack(pady=(0, 6))
        styled_label(card, "Selecciona un movimiento", FONT_SUB, TEXT_MUTED, BG_CARD).pack(pady=(0, 22))
        btns = tk.Frame(card, bg=BG_CARD)
        btns.pack()
        primary_button(btns, "Entrada de dinero", self.abrir_entr_dine, width=18).pack(side="left", padx=6)
        danger_button(btns, "Salida de dinero", self.abrir_sali_dine, width=18).pack(side="left", padx=6)
        secondary_button(btns, "Historial entr/sali", self.abrir_hist_sali_dine, width=18).pack(side="left", padx=6)

    def abrir_entr_dine(self):
        entrada.entrada_dinero(self.usuario, self.winfo_toplevel())

    def abrir_sali_dine(self):
        salida.salida_dinero(self.usuario, self.winfo_toplevel())

    def abrir_hist_sali_dine(self):
        historial_entr.His_entr_sali(self.winfo_toplevel())
