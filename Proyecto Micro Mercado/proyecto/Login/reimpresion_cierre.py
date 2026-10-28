"""Reimpresión de ticket de cierre (caja fuerte). Vendedor dueño o administrador."""
import tkinter as tk
from tkinter import ttk
import mensaje as mb

from Consultas import (
    construir_datos_ticket_cierre,
    listar_cierres_ticket_pendiente,
    marcar_ticket_cierre_impreso,
)
from ticket import imprimir_ticket_cierre
from zyntra_ui import *


def _es_admin(usuario):
    try:
        from cierre_general_svc import es_usuario_admin

        return bool(es_usuario_admin(usuario))
    except Exception:
        return False


def mostrar_reimpresion_cierres(parent, usuario, forzar=False):
    """
    Diálogo para reimprimir tickets de cierre.
    forzar=True: abre también últimos cierres (reimpresión manual).
    """
    admin = _es_admin(usuario)
    pendientes = listar_cierres_ticket_pendiente(usuario=usuario, es_admin=admin, limite=50)
    if forzar:
        # Incluir recientes ya impresos para reimpresión manual
        vistos = {p["id"] for p in pendientes}
        for p in _listar_cierres_reimprimibles(usuario, admin, limite=30):
            if p["id"] not in vistos:
                pendientes.append(p)
    if not pendientes and not forzar:
        return False

    dlg = tk.Toplevel(parent)
    prepare_modal(dlg, parent, "Tickets de cierre", 720, 480, resizable=True)
    shell = tk.Frame(dlg, bg=BG, padx=14, pady=12)
    shell.pack(fill="both", expand=True)

    styled_label(shell, "Reimprimir ticket de cierre", FONT_HEADING, TEXT, BG).pack(anchor="w")
    styled_label(
        shell,
        "Use este ticket para identificar el dinero en la caja fuerte. "
        + ("Admin: todos los pendientes." if admin else "Solo sus cierres."),
        FONT_SMALL,
        TEXT_DIM,
        BG,
    ).pack(anchor="w", pady=(2, 10))

    if not pendientes:
        styled_label(shell, "No hay tickets pendientes de impresión.", FONT_BODY, TEXT, BG).pack(
            anchor="w"
        )
        secondary_button(shell, "Cerrar", dlg.destroy, width=12, height=1).pack(anchor="w", pady=12)
        return True

    wrap, tree = scrollable_tree(
        shell,
        columns=("Id", "Fecha", "Vendedor", "Ventas", "Estado", "Tx", "Impreso"),
        headings=("ID", "Fecha", "Vendedor", "Ventas", "Estado", "Tx", "Impreso"),
        height=12,
        widths={
            "Id": 50,
            "Fecha": 120,
            "Vendedor": 120,
            "Ventas": 90,
            "Estado": 120,
            "Tx": 50,
            "Impreso": 70,
        },
    )
    wrap.pack(fill="both", expand=True)
    for p in pendientes:
        tree.insert(
            "",
            "end",
            iid=str(p["id"]),
            values=(
                p["id"],
                str(p.get("fecha") or "")[:16],
                p.get("cajero") or p.get("usuario") or "",
                formato_dinero(p.get("total_ventas")),
                p.get("estado") or "-",
                p.get("tickets") or 0,
                "Sí" if p.get("ticket_impreso") else "NO",
            ),
        )

    def _reimprimir():
        sel = tree.selection()
        if not sel:
            mb.showwarning("Ticket", "Seleccione un cierre.", parent=dlg)
            return
        cid = int(sel[0])
        datos = construir_datos_ticket_cierre(cid)
        if not datos:
            mb.showerror("Ticket", "No se pudo cargar el cierre #{}.".format(cid), parent=dlg)
            return
        try:
            path, _t, ok = imprimir_ticket_cierre(datos, enviar_cola=True)
            if ok:
                marcar_ticket_cierre_impreso(cid, True)
                mb.showinfo(
                    "Ticket",
                    "Ticket del cierre #{} enviado a la impresora.\n{}".format(cid, path),
                    parent=dlg,
                )
                # refrescar fila
                tree.set(sel[0], "Impreso", "Sí")
            else:
                marcar_ticket_cierre_impreso(cid, False)
                mb.showwarning(
                    "Ticket",
                    "No se pudo enviar a la impresora. Verifique papel/conexión.\nArchivo: {}".format(
                        path
                    ),
                    parent=dlg,
                )
        except Exception as error:
            mb.showerror("Ticket", "Error al imprimir: {}".format(error), parent=dlg)

    bar = tk.Frame(shell, bg=BG)
    bar.pack(fill="x", pady=(10, 0))
    primary_button(bar, "Imprimir seleccionado", _reimprimir, width=20, height=1).pack(side="left")
    secondary_button(bar, "Cerrar", dlg.destroy, width=12, height=1).pack(side="left", padx=(10, 0))
    tree.bind("<Double-1>", lambda _e: _reimprimir())
    return True


def _listar_cierres_reimprimibles(usuario, es_admin, limite=30):
    """Últimos cierres definitivos (impresos o no) para reimpresión manual."""
    out = []
    try:
        from conexionLogin import FormularioLogin

        cone = FormularioLogin.conexion_base_de_datos()
        cursor = cone.cursor()
        sql = """
            SELECT Id, Cajero, Fecha, Total_Ventas, Estado, Usuario, Correcciones,
                   COALESCE(Tickets, 0), COALESCE(Ticket_Impreso, 0), COALESCE(Tipo, 'definitivo')
            FROM cierre_turno
            WHERE COALESCE(Tipo, 'definitivo') <> 'temporal'
        """
        vals = []
        if not es_admin:
            sql += " AND (LOWER(Usuario)=LOWER(%s) OR LOWER(Cajero)=LOWER(%s))"
            vals.extend([str(usuario or "").strip(), str(usuario or "").strip()])
        sql += " ORDER BY Id DESC LIMIT %s"
        vals.append(int(limite))
        cursor.execute(sql, tuple(vals))
        for row in cursor.fetchall() or []:
            out.append(
                {
                    "id": int(row[0]),
                    "cajero": row[1] or "",
                    "fecha": str(row[2] or ""),
                    "total_ventas": float(row[3] or 0),
                    "estado": row[4] or "",
                    "usuario": row[5] or "",
                    "correcciones": int(row[6] or 0),
                    "tickets": int(row[7] or 0),
                    "ticket_impreso": int(row[8] or 0),
                    "tipo": row[9] or "definitivo",
                }
            )
        cone.close()
    except Exception as error:
        print("Error listar reimprimibles: {}".format(error))
    return out


def avisar_tickets_pendientes(parent, usuario):
    admin = _es_admin(usuario)
    pendientes = listar_cierres_ticket_pendiente(usuario=usuario, es_admin=admin, limite=20)
    if not pendientes:
        return
    n = len(pendientes)
    msg = (
        "Hay {} ticket(s) de cierre sin imprimir.\n"
        "Debe imprimirlos y adjuntarlos al dinero en la caja fuerte.\n\n"
        "¿Imprimir ahora?"
    ).format(n)
    if mb.askyesno("Tickets de cierre pendientes", msg, parent=parent):
        mostrar_reimpresion_cierres(parent, usuario, forzar=True)
