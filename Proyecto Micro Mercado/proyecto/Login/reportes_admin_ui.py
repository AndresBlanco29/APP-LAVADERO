"""UI Dashboard reportes administrativos — solo admin (Entrega 6)."""
import tkinter as tk
from tkinter import ttk
import mensaje as mb

from cierre_general_svc import es_usuario_admin
from reportes_admin_svc import dashboard_reportes_admin
from zyntra_ui import *


class ReportesAdminView(tk.Frame):
    def __init__(self, parent, usuario=None, app=None):
        super().__init__(parent, bg=BG)
        self.usuario = usuario or (getattr(app, "usuario", None) if app else None)
        self.app = app
        self._data = {}
        self._preset = tk.StringVar(value="mes")
        self._medio = tk.StringVar(value="")
        self._vendedor = tk.StringVar(value="")
        self._categoria = tk.StringVar(value="")
        if not es_usuario_admin(self.usuario):
            styled_label(
                self,
                "Acceso denegado: solo el administrador consulta reportes administrativos.",
                FONT_HEADING,
                DANGER,
                BG,
            ).pack(expand=True)
            return
        self._build()
        self._cargar()

    def on_show(self):
        if es_usuario_admin(self.usuario):
            self._cargar()

    def _build(self):
        top = card_frame(self, padx=12, pady=10)
        top.pack(fill="x", pady=(0, 8))
        styled_label(top, "Dashboard administrativo", FONT_HEADING, TEXT, BG_CARD).pack(anchor="w")
        styled_label(
            top,
            "Datafono = medio de pago dentro de proveedores · No es bolsillo independiente",
            FONT_SMALL,
            TEXT_DIM,
            BG_CARD,
        ).pack(anchor="w", pady=(2, 8))

        filt = tk.Frame(top, bg=BG_CARD)
        filt.pack(fill="x")
        styled_label(filt, "Periodo", FONT_SMALL, TEXT_DIM, BG_CARD).pack(side="left")
        ttk.Combobox(
            filt,
            textvariable=self._preset,
            values=["hoy", "ayer", "semana", "mes", "año"],
            width=10,
            state="readonly",
        ).pack(side="left", padx=6)
        styled_label(filt, "Medio", FONT_SMALL, TEXT_DIM, BG_CARD).pack(side="left", padx=(10, 0))
        ttk.Combobox(
            filt,
            textvariable=self._medio,
            values=["", "Efectivo", "Nequi", "Datafono", "Otros"],
            width=12,
            state="readonly",
        ).pack(side="left", padx=6)
        primary_button(filt, "Actualizar", self._cargar, width=12, height=1).pack(side="left", padx=8)

        self.kpi = card_frame(self, padx=12, pady=10)
        self.kpi.pack(fill="x", pady=(0, 8))
        self.lbl_kpi = styled_label(self.kpi, "—", FONT_SUB, TEXT, BG_CARD)
        self.lbl_kpi.pack(anchor="w")
        self.lbl_alert = styled_label(self.kpi, "", FONT_SMALL, WARNING, BG_CARD)
        self.lbl_alert.pack(anchor="w")

        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True)
        self.tab_ventas = tk.Frame(nb, bg=BG)
        self.tab_rent = tk.Frame(nb, bg=BG)
        self.tab_bolsa = tk.Frame(nb, bg=BG)
        self.tab_prov = tk.Frame(nb, bg=BG)
        self.tab_cierres = tk.Frame(nb, bg=BG)
        nb.add(self.tab_ventas, text="Ventas")
        nb.add(self.tab_rent, text="Rentabilidad")
        nb.add(self.tab_bolsa, text="Bolsillos")
        nb.add(self.tab_prov, text="Proveedores")
        nb.add(self.tab_cierres, text="Cierres")

        self.wrap_v, self.tree_v = scrollable_tree(
            self.tab_ventas,
            columns=("Dia", "Ventas", "Tickets"),
            headings=("Día", "Ventas", "Tickets"),
            height=8,
            widths={"Dia": 110, "Ventas": 120, "Tickets": 80},
        )
        self.wrap_v.pack(fill="both", expand=True, padx=8, pady=8)
        self.wrap_med, self.tree_med = scrollable_tree(
            self.tab_ventas,
            columns=("Medio", "Monto"),
            headings=("Medio de pago", "Monto"),
            height=5,
            widths={"Medio": 140, "Monto": 120},
        )
        self.wrap_med.pack(fill="x", padx=8, pady=(0, 8))
        self.lbl_datafono = styled_label(
            self.tab_ventas, "", FONT_SMALL, TEXT_DIM, BG
        )
        self.lbl_datafono.pack(anchor="w", padx=12, pady=(0, 8))

        self.lbl_rent = styled_label(self.tab_rent, "—", FONT_SUB, TEXT, BG)
        self.lbl_rent.pack(anchor="w", padx=12, pady=12)

        self.lbl_admin = styled_label(self.tab_bolsa, "—", FONT_SUB, TEXT, BG)
        self.lbl_admin.pack(anchor="w", padx=12, pady=(12, 4))
        self.lbl_prov_b = styled_label(self.tab_bolsa, "—", FONT_SUB, TEXT, BG)
        self.lbl_prov_b.pack(anchor="w", padx=12, pady=4)
        self.lbl_excl = styled_label(self.tab_bolsa, "", FONT_SMALL, WARNING, BG)
        self.lbl_excl.pack(anchor="w", padx=12, pady=(4, 12))

        self.wrap_p, self.tree_p = scrollable_tree(
            self.tab_prov,
            columns=("Fecha", "Prov", "Valor", "Medio", "User"),
            headings=("Fecha", "Proveedor", "Valor", "Medio", "Usuario"),
            height=12,
            widths={"Fecha": 120, "Prov": 140, "Valor": 100, "Medio": 90, "User": 90},
        )
        self.wrap_p.pack(fill="both", expand=True, padx=8, pady=8)

        self.wrap_c, self.tree_c = scrollable_tree(
            self.tab_cierres,
            columns=("Id", "Fecha", "Vend", "Ef", "Nq", "Dt", "Diff", "Est"),
            headings=("ID", "Fecha", "Vendedor", "Efectivo", "Nequi", "Datafono", "Diff", "Estado"),
            height=12,
            widths={
                "Id": 40,
                "Fecha": 110,
                "Vend": 90,
                "Ef": 80,
                "Nq": 80,
                "Dt": 80,
                "Diff": 70,
                "Est": 90,
            },
        )
        self.wrap_c.pack(fill="both", expand=True, padx=8, pady=8)

    def _cargar(self):
        data = dashboard_reportes_admin(
            self.usuario,
            preset=self._preset.get(),
            medio_pago=self._medio.get() or None,
        )
        if data.get("error"):
            mb.showerror("Reportes", data["error"], parent=self)
            return
        self._data = data
        v = data.get("ventas") or {}
        self.lbl_kpi.config(
            text="Ventas {} · Tickets {} · Promedio {} · Periodo {}".format(
                formato_dinero(v.get("total")),
                v.get("tickets"),
                formato_dinero(v.get("ticket_promedio")),
                (data.get("periodo") or {}).get("preset"),
            )
        )
        alerts = data.get("alertas") or []
        self.lbl_alert.config(
            text=" · ".join(a.get("mensaje", "") for a in alerts) if alerts else "Sin alertas"
        )

        for tree in (self.tree_v, self.tree_med, self.tree_p, self.tree_c):
            for i in tree.get_children():
                tree.delete(i)
        for s in v.get("serie_diaria") or []:
            self.tree_v.insert(
                "",
                "end",
                values=(s.get("fecha"), formato_dinero(s.get("ventas")), s.get("tickets")),
            )
        pm = v.get("por_medio") or {}
        for label, key in (
            ("Efectivo", "efectivo"),
            ("Nequi", "nequi"),
            ("Datafono (medio)", "datafono"),
            ("Otros", "otros"),
        ):
            self.tree_med.insert("", "end", values=(label, formato_dinero(pm.get(key))))
        self.lbl_datafono.config(
            text="Datafono vendido (periodo): {} — NO es bolsillo. Destino: proveedores.".format(
                formato_dinero(v.get("datafono_vendido"))
            )
        )

        r = data.get("rentabilidad") or {}
        self.lbl_rent.config(
            text=(
                "Ventas {v}\nCosto {c}\nUtilidad bruta {u}\nMargen {m}%\n"
                "(No altera bolsillos)"
            ).format(
                v=formato_dinero(r.get("ventas")),
                c=formato_dinero(r.get("costo")),
                u=formato_dinero(r.get("utilidad_bruta")),
                m=r.get("margen_pct"),
            )
        )

        b = data.get("bolsillos") or {}
        ad = b.get("administrativo") or {}
        self.lbl_admin.config(
            text=(
                "ADMINISTRATIVO (solo efectivo)\n"
                "Objetivo {} · Provisionado {} · Pendiente {}\n"
                "Obligaciones {} · Disponible {} · Datafono: NO incluido"
            ).format(
                formato_dinero(ad.get("objetivo")),
                formato_dinero(ad.get("provisionado")),
                formato_dinero(ad.get("pendiente")),
                formato_dinero(ad.get("obligaciones")),
                formato_dinero(ad.get("disponible")),
            )
        )
        pr = b.get("proveedores") or {}
        self.lbl_prov_b.config(
            text=(
                "PROVEEDORES = Efectivo + Nequi + Datafono\n"
                "Efectivo {} · Nequi {} · Datafono {} · TOTAL {}"
            ).format(
                formato_dinero(pr.get("efectivo")),
                formato_dinero(pr.get("nequi")),
                formato_dinero(pr.get("datafono")),
                formato_dinero(pr.get("total")),
            )
        )
        self.lbl_excl.config(
            text="No existe bolsillo independiente «Datafono». Es desglose dentro de proveedores."
        )

        for p in (data.get("proveedores") or {}).get("pagos") or []:
            medio = p.get("medio") or ""
            if p.get("mixto"):
                medio = "MIXTO ef/nq/dt"
            self.tree_p.insert(
                "",
                "end",
                values=(
                    str(p.get("fecha") or "")[:16],
                    (p.get("proveedor") or "")[:24],
                    formato_dinero(p.get("valor")),
                    medio,
                    (p.get("usuario") or "")[:14],
                ),
            )

        for c in (data.get("cierres") or {}).get("diarios") or []:
            self.tree_c.insert(
                "",
                "end",
                values=(
                    c.get("id"),
                    str(c.get("fecha") or "")[:16],
                    (c.get("vendedor") or "")[:14],
                    formato_dinero(c.get("efectivo")),
                    formato_dinero(c.get("nequi")),
                    formato_dinero(c.get("datafono")),
                    formato_dinero(c.get("diferencia")),
                    c.get("estado"),
                ),
            )
