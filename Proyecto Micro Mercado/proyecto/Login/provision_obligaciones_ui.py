"""UI Obligaciones de provisión administrativa — solo admin (Entrega 5)."""
import tkinter as tk
from tkinter import ttk
import mensaje as mb

from cierre_general_svc import es_usuario_admin
from provision_obligaciones_svc import (
    anular_obligacion_pendiente,
    crear_obligacion,
    pagar_nomina_empleados,
    pagar_obligacion,
    registrar_empleado_salario,
    resumen_obligaciones_provision,
)
from zyntra_ui import *


class ProvisionObligacionesView(tk.Frame):
    def __init__(self, parent, usuario=None, app=None):
        super().__init__(parent, bg=BG)
        self.usuario = usuario or (getattr(app, "usuario", None) if app else None)
        self.app = app
        self._data = {}
        if not es_usuario_admin(self.usuario):
            styled_label(
                self,
                "Acceso denegado: solo el administrador gestiona obligaciones de provisión.",
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
        styled_label(top, "Administrativo — provisión y obligaciones", FONT_HEADING, TEXT, BG_CARD).pack(
            anchor="w"
        )
        styled_label(
            top,
            "Todo sale del mismo bolsillo. No crean dinero. Real ≠ Comprometido ≠ Disponible.",
            FONT_SMALL,
            TEXT_DIM,
            BG_CARD,
        ).pack(anchor="w", pady=(2, 8))
        actions = tk.Frame(top, bg=BG_CARD)
        actions.pack(fill="x")
        primary_button(actions, "+ Empleado", self._add_empleado, width=12, height=1).pack(
            side="left", padx=(0, 6)
        )
        secondary_button(actions, "+ Obligación", self._add_obligacion, width=14, height=1).pack(
            side="left", padx=(0, 6)
        )
        secondary_button(actions, "Pagar nómina", self._pagar_nomina, width=12, height=1).pack(
            side="left", padx=(0, 6)
        )
        secondary_button(actions, "Pagar sel.", self._pagar_sel, width=10, height=1).pack(
            side="left", padx=(0, 6)
        )
        secondary_button(actions, "Anular sel.", self._anular_sel, width=10, height=1).pack(
            side="left", padx=(0, 6)
        )
        secondary_button(actions, "Actualizar", self._cargar, width=10, height=1).pack(side="left")

        self.saldos_box = card_frame(self, padx=12, pady=10)
        self.saldos_box.pack(fill="x", pady=(0, 8))
        self.lbl_real = styled_label(self.saldos_box, "Dinero real: —", FONT_SUB, TEXT, BG_CARD)
        self.lbl_real.pack(anchor="w")
        self.lbl_comp = styled_label(self.saldos_box, "Comprometido: —", FONT_SUB, WARNING, BG_CARD)
        self.lbl_comp.pack(anchor="w")
        self.lbl_disp = styled_label(self.saldos_box, "Disponible: —", FONT_HEADING, CYAN, BG_CARD)
        self.lbl_disp.pack(anchor="w", pady=(4, 0))
        self.lbl_emp = styled_label(self.saldos_box, "Reserva empleados: —", FONT_SMALL, TEXT_DIM, BG_CARD)
        self.lbl_emp.pack(anchor="w")

        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True)
        left = card_frame(body, padx=8, pady=8)
        left.pack(side="left", fill="both", expand=True, padx=(0, 6))
        styled_label(left, "Obligaciones", FONT_LABEL, TEXT, BG_CARD).pack(anchor="w")
        self.wrap_o, self.tree_o = scrollable_tree(
            left,
            columns=("Id", "Tipo", "Nombre", "Valor", "Estado", "Fecha", "Pago"),
            headings=("ID", "Tipo", "Nombre", "Valor", "Estado", "Obligación", "Pago"),
            height=12,
            widths={"Id": 40, "Tipo": 90, "Nombre": 140, "Valor": 90, "Estado": 80, "Fecha": 90, "Pago": 110},
        )
        self.wrap_o.pack(fill="both", expand=True, pady=(6, 0))

        right = card_frame(body, padx=8, pady=8)
        right.pack(side="left", fill="both", expand=True)
        styled_label(right, "Empleados (salario/30)", FONT_LABEL, TEXT, BG_CARD).pack(anchor="w")
        self.wrap_e, self.tree_e = scrollable_tree(
            right,
            columns=("Id", "Nombre", "Mensual", "Diaria"),
            headings=("ID", "Nombre", "Salario/mes", "Reserva/día"),
            height=6,
            widths={"Id": 40, "Nombre": 140, "Mensual": 100, "Diaria": 100},
        )
        self.wrap_e.pack(fill="both", expand=True, pady=(6, 0))
        styled_label(right, "Movimientos", FONT_LABEL, TEXT, BG_CARD).pack(anchor="w", pady=(8, 0))
        self.wrap_m, self.tree_m = scrollable_tree(
            right,
            columns=("Id", "Tipo", "Cat", "Monto", "Real", "Disp", "Fecha"),
            headings=("ID", "Tipo", "Cat", "Monto", "Real→", "Disp→", "Fecha"),
            height=6,
            widths={"Id": 40, "Tipo": 90, "Cat": 70, "Monto": 80, "Real": 80, "Disp": 80, "Fecha": 100},
        )
        self.wrap_m.pack(fill="both", expand=True, pady=(6, 0))

    def _cargar(self):
        data = resumen_obligaciones_provision(self.usuario)
        if data.get("error"):
            mb.showerror("Obligaciones", data["error"], parent=self)
            return
        self._data = data
        s = data.get("saldos") or {}
        self.lbl_real.config(text="Dinero real: {}".format(formato_dinero(s.get("dinero_real"))))
        self.lbl_comp.config(
            text="Dinero comprometido: {} (emp. {} + otras {})".format(
                formato_dinero(s.get("dinero_comprometido")),
                formato_dinero(s.get("comprometido_empleados")),
                formato_dinero(s.get("comprometido_otras")),
            )
        )
        self.lbl_disp.config(text="Disponible: {}".format(formato_dinero(s.get("disponible"))))
        emp = data.get("empleados") or {}
        self.lbl_emp.config(
            text="Reserva diaria empleados (Σ salarios/30): {}".format(
                formato_dinero(emp.get("reserva_diaria"))
            )
        )
        for tree in (self.tree_o, self.tree_e, self.tree_m):
            for i in tree.get_children():
                tree.delete(i)
        for o in data.get("obligaciones") or []:
            self.tree_o.insert(
                "",
                "end",
                values=(
                    o.get("id"),
                    o.get("tipo"),
                    (o.get("nombre") or "")[:28],
                    formato_dinero(o.get("valor")),
                    o.get("estado"),
                    str(o.get("fecha_obligacion") or "")[:10],
                    str(o.get("fecha_pago") or "")[:16],
                ),
            )
        for e in (emp.get("empleados") or []):
            self.tree_e.insert(
                "",
                "end",
                values=(
                    e.get("id"),
                    (e.get("nombre") or "")[:28],
                    formato_dinero(e.get("salario_mensual")),
                    formato_dinero(e.get("reserva_diaria")),
                ),
            )
        for m in data.get("movimientos") or []:
            self.tree_m.insert(
                "",
                "end",
                values=(
                    m.get("id"),
                    m.get("tipo"),
                    m.get("categoria"),
                    formato_dinero(m.get("monto")),
                    formato_dinero(m.get("dinero_real_nuevo")),
                    formato_dinero(m.get("disponible_nuevo")),
                    str(m.get("fecha") or "")[:16],
                ),
            )

    def _parse(self, v):
        try:
            return round(float(str(v).replace(",", "").replace("$", "").strip() or 0), 2)
        except (TypeError, ValueError):
            return 0.0

    def _add_empleado(self):
        dlg = tk.Toplevel(self)
        prepare_modal(dlg, self, "Registrar salario empleado", 420, 280, resizable=True)
        card = card_frame(dlg, padx=14, pady=12)
        card.pack(fill="both", expand=True)
        nombre = tk.StringVar()
        salario = tk.StringVar()
        for label, var in (("Nombre", nombre), ("Salario mensual", salario)):
            row = tk.Frame(card, bg=BG_CARD)
            row.pack(fill="x", pady=3)
            styled_label(row, label, FONT_SMALL, TEXT_DIM, BG_CARD).pack(side="left")
            ttk.Entry(row, textvariable=var, width=24).pack(side="right")
        styled_label(
            card, "Reserva diaria = salario / 30 (comprometido, no crea dinero)", FONT_SMALL, TEXT_DIM, BG_CARD
        ).pack(anchor="w", pady=(8, 0))

        def guardar():
            ok, msg, _ = registrar_empleado_salario(
                self.usuario, nombre.get().strip(), self._parse(salario.get())
            )
            if ok:
                mb.showinfo("Empleados", msg, parent=dlg)
                dlg.destroy()
                self._cargar()
            else:
                mb.showerror("Empleados", msg, parent=dlg)

        primary_button(card, "Guardar", guardar, width=12, height=1).pack(anchor="w", pady=(12, 0))

    def _add_obligacion(self):
        dlg = tk.Toplevel(self)
        prepare_modal(dlg, self, "Nueva obligación", 460, 420, resizable=True)
        card = card_frame(dlg, padx=14, pady=12)
        card.pack(fill="both", expand=True)
        tipo = tk.StringVar(value="SERVICIOS")
        nombre = tk.StringVar()
        valor = tk.StringVar()
        desc = tk.StringVar()
        cat = tk.StringVar()
        row = tk.Frame(card, bg=BG_CARD)
        row.pack(fill="x", pady=3)
        styled_label(row, "Tipo", FONT_SMALL, TEXT_DIM, BG_CARD).pack(side="left")
        ttk.Combobox(
            row,
            textvariable=tipo,
            values=["SERVICIOS", "SISTEMA", "ARRIENDO", "OTRAS"],
            width=22,
            state="readonly",
        ).pack(side="right")
        for label, var in (
            ("Nombre", nombre),
            ("Valor", valor),
            ("Descripción", desc),
            ("Categoría", cat),
        ):
            r = tk.Frame(card, bg=BG_CARD)
            r.pack(fill="x", pady=3)
            styled_label(r, label, FONT_SMALL, TEXT_DIM, BG_CARD).pack(side="left")
            ttk.Entry(r, textvariable=var, width=24).pack(side="right")

        def guardar():
            ok, msg, _ = crear_obligacion(
                self.usuario,
                tipo.get(),
                nombre.get().strip(),
                self._parse(valor.get()),
                descripcion=desc.get().strip(),
                categoria=cat.get().strip() or tipo.get(),
            )
            if ok:
                mb.showinfo("Obligaciones", msg, parent=dlg)
                dlg.destroy()
                self._cargar()
            else:
                mb.showerror("Obligaciones", msg, parent=dlg)

        primary_button(card, "Comprometer", guardar, width=14, height=1).pack(anchor="w", pady=(12, 0))

    def _pagar_nomina(self):
        if not mb.askyesno(
            "Nómina",
            "¿Pagar la reserva diaria (Σ salarios/30) desde el bolsillo de provisión?",
            parent=self,
        ):
            return
        ok, msg, _ = pagar_nomina_empleados(self.usuario)
        if ok:
            mb.showinfo("Nómina", msg, parent=self)
            self._cargar()
        else:
            mb.showerror("Nómina", msg, parent=self)

    def _sel_obl_id(self):
        sel = self.tree_o.selection()
        if not sel:
            return None
        vals = self.tree_o.item(sel[0], "values")
        try:
            return int(vals[0])
        except (TypeError, ValueError, IndexError):
            return None

    def _pagar_sel(self):
        oid = self._sel_obl_id()
        if not oid:
            mb.showwarning("Pago", "Seleccione una obligación", parent=self)
            return
        ok, msg, _ = pagar_obligacion(self.usuario, oid)
        if ok:
            mb.showinfo("Pago", msg, parent=self)
            self._cargar()
        else:
            mb.showerror("Pago", msg, parent=self)

    def _anular_sel(self):
        oid = self._sel_obl_id()
        if not oid:
            mb.showwarning("Anular", "Seleccione una obligación pendiente", parent=self)
            return
        ok, msg = anular_obligacion_pendiente(self.usuario, oid, "Anulada desde POS")
        if ok:
            mb.showinfo("Anular", msg, parent=self)
            self._cargar()
        else:
            mb.showerror("Anular", msg, parent=self)
