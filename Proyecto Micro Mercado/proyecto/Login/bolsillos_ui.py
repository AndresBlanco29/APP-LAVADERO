"""Módulo unificado de bolsillos financieros — solo admin.

Dos apartados separados en el mismo módulo:
  - Proveedores
  - Administrativo (provisión / obligaciones)
"""
import tkinter as tk
from tkinter import ttk

from cierre_general_svc import es_usuario_admin
from bolsillo_proveedores_ui import BolsilloProveedoresView
from provision_obligaciones_ui import ProvisionObligacionesView
from zyntra_ui import *


class BolsillosView(tk.Frame):
    """Contenedor con pestañas: Proveedores | Administrativo."""

    def __init__(self, parent, usuario=None, app=None):
        super().__init__(parent, bg=BG)
        self.usuario = usuario or (getattr(app, "usuario", None) if app else None)
        self.app = app
        self._tab_prov = None
        self._tab_admin = None
        if not es_usuario_admin(self.usuario):
            styled_label(
                self,
                "Acceso denegado: solo el administrador gestiona los bolsillos financieros.",
                FONT_HEADING,
                DANGER,
                BG,
            ).pack(expand=True)
            return
        self._build()

    def _build(self):
        top = card_frame(self, padx=12, pady=10)
        top.pack(fill="x", pady=(0, 8))
        styled_label(top, "Bolsillos financieros", FONT_HEADING, TEXT, BG_CARD).pack(anchor="w")
        styled_label(
            top,
            "Proveedores y Administrativo en el mismo módulo, con saldos y reglas separados.",
            FONT_SMALL,
            TEXT_DIM,
            BG_CARD,
        ).pack(anchor="w", pady=(2, 0))

        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True)

        frame_prov = tk.Frame(self.nb, bg=BG)
        frame_admin = tk.Frame(self.nb, bg=BG)
        self.nb.add(frame_prov, text="  Proveedores  ")
        self.nb.add(frame_admin, text="  Administrativo  ")

        self._tab_prov = BolsilloProveedoresView(
            frame_prov, usuario=self.usuario, app=self.app
        )
        self._tab_prov.pack(fill="both", expand=True)

        self._tab_admin = ProvisionObligacionesView(
            frame_admin, usuario=self.usuario, app=self.app
        )
        self._tab_admin.pack(fill="both", expand=True)

        self.nb.bind("<<NotebookTabChanged>>", self._on_tab)

    def _on_tab(self, _event=None):
        self.on_show()

    def on_show(self):
        if not es_usuario_admin(self.usuario):
            return
        try:
            idx = self.nb.index(self.nb.select())
        except Exception:
            idx = 0
        if idx == 0 and self._tab_prov and hasattr(self._tab_prov, "on_show"):
            self._tab_prov.on_show()
        elif idx == 1 and self._tab_admin and hasattr(self._tab_admin, "on_show"):
            self._tab_admin.on_show()
