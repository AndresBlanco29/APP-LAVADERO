"""Centro de comando: devoluciones remotas, bolsillos, utilidad y FEFO."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Optional
import json

from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field


from finanzas import (
    BolsilloEgresoIn,
    attach_routes,
    ensure_finanzas,
    registrar_egresos,
    snapshot_bolsillos,
)


class DevolucionSolicitar(BaseModel):
    venta_id: int
    motivo: str = ""
    cajero: str = ""
    cliente: str = ""
    items: list[dict] = Field(default_factory=list)


class DevolucionResponder(BaseModel):
    estado: str
    nota: str = ""
    admin_id: Optional[int] = None
    usuario: str = ""


class BolsilloIn(BaseModel):
    nombre: str
    porcentaje: float = Field(ge=0, le=100)
    color: str = "#3077FF"
    icono: str = "wallet"
    meta_mensual: float = 0
    activo: int = 1
    orden: int = 0
    codigo: str = ""
    usuario: str = ""
    admin_id: Optional[int] = None


class WsHub:
    def __init__(self) -> None:
        self.clients: list[WebSocket] = []

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self.clients.append(ws)

    def disconnect(self, ws: WebSocket) -> None:
        if ws in self.clients:
            self.clients.remove(ws)

    async def broadcast(self, payload: dict) -> None:
        muertos = []
        for ws in self.clients:
            try:
                await ws.send_json(payload)
            except Exception:
                muertos.append(ws)
        for ws in muertos:
            self.disconnect(ws)


HUB = WsHub()
_READY = False


def _money(value: Any) -> float:
    try:
        return round(float(value or 0), 2)
    except (TypeError, ValueError):
        return 0.0


def register(app: FastAPI) -> None:
    from main import col, execute, has_column, inicio_dia, inicio_mes, now_bogota, query

    def has_table(name: str) -> bool:
        rows = query(
            """
            SELECT COUNT(*) AS c
            FROM information_schema.TABLES
            WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s
            """,
            (name,),
        )
        return bool(rows and int(rows[0]["c"]))

    def is_admin_usuario(usuario: str) -> bool:
        if not usuario:
            return False
        rows = query(
            "SELECT COUNT(*) AS c FROM admin WHERE LOWER(usuario)=LOWER(%s)",
            (usuario.strip(),),
        )
        return bool(rows and int(rows[0]["c"]) > 0)

    def is_admin_id(admin_id: Optional[int]) -> bool:
        if not admin_id:
            return False
        # Resolver columna PK de admin
        id_col = "Id_admin" if has_column("admin", "Id_admin") else (
            "id_admin" if has_column("admin", "id_admin") else "id"
        )
        rows = query(
            f"SELECT COUNT(*) AS c FROM admin WHERE `{id_col}`=%s",
            (int(admin_id),),
        )
        return bool(rows and int(rows[0]["c"]) > 0)

    def require_admin_actor(usuario: str = "", admin_id: Optional[int] = None) -> None:
        """Entrega 7: mutaciones financieras/admin solo con admin real."""
        if is_admin_usuario(usuario or "") or is_admin_id(admin_id):
            return
        raise HTTPException(403, "Solo administrador")

    def ensure() -> None:
        global _READY
        if _READY:
            return
        execute(
            """
            CREATE TABLE IF NOT EXISTS devolucion_solicitudes (
                Id INT AUTO_INCREMENT PRIMARY KEY,
                Venta_Id INT NOT NULL,
                Estado VARCHAR(32) NOT NULL DEFAULT 'PENDIENTE',
                Motivo VARCHAR(255) DEFAULT '',
                Nota_Respuesta VARCHAR(255) DEFAULT '',
                Cajero VARCHAR(80) DEFAULT '',
                Cliente VARCHAR(120) DEFAULT '',
                Total DECIMAL(12,2) DEFAULT 0,
                Admin_Id INT NULL,
                Fecha DATETIME,
                Fecha_Respuesta DATETIME NULL,
                Avisado_Caja TINYINT DEFAULT 0,
                INDEX idx_dev_estado (Estado),
                INDEX idx_dev_venta (Venta_Id)
            )
            """
        )
        if not has_column("devolucion_solicitudes", "Avisado_Caja"):
            try:
                execute(
                    "ALTER TABLE devolucion_solicitudes ADD COLUMN Avisado_Caja TINYINT DEFAULT 0"
                )
            except Exception:
                pass
        if not has_column("devolucion_solicitudes", "Items"):
            try:
                execute("ALTER TABLE devolucion_solicitudes ADD COLUMN Items TEXT NULL")
            except Exception:
                pass
        if not has_column("productos_has_ventas", "Devuelto"):
            try:
                execute(
                    "ALTER TABLE productos_has_ventas ADD COLUMN Devuelto TINYINT DEFAULT 0"
                )
            except Exception:
                pass
        execute(
            """
            CREATE TABLE IF NOT EXISTS bolsillos (
                Id INT AUTO_INCREMENT PRIMARY KEY,
                Nombre VARCHAR(80) NOT NULL,
                Porcentaje DECIMAL(7,2) NOT NULL DEFAULT 0,
                Color VARCHAR(16) DEFAULT '#3077FF',
                Icono VARCHAR(40) DEFAULT 'wallet',
                Meta_Mensual DECIMAL(12,2) DEFAULT 0,
                Activo TINYINT DEFAULT 1,
                Orden INT DEFAULT 0
            )
            """
        )
        execute(
            """
            CREATE TABLE IF NOT EXISTS bolsillo_movimientos (
                Id INT AUTO_INCREMENT PRIMARY KEY,
                Bolsillo_Id INT NOT NULL,
                Tipo VARCHAR(20) NOT NULL,
                Monto DECIMAL(12,2) NOT NULL,
                Nota VARCHAR(220) DEFAULT '',
                Fecha DATETIME,
                Venta_Id INT NULL,
                INDEX idx_bols_mov (Bolsillo_Id, Fecha)
            )
            """
        )
        existentes = query("SELECT COUNT(*) AS c FROM bolsillos")
        if existentes and int(existentes[0]["c"] or 0) == 0:
            semillas = [
                ("Caja Proveedores", 65, "#3077FF", "truck", 0, 1),
                ("Utilidad neta", 18, "#22C55E", "crown", 0, 2),
                ("Gastos operativos", 12, "#A084E8", "building", 0, 3),
                ("Reserva de impuestos", 5, "#F59E0B", "receipt", 0, 4),
            ]
            for nombre, pct, color, icono, meta, orden in semillas:
                execute(
                    """
                    INSERT INTO bolsillos
                        (Nombre, Porcentaje, Color, Icono, Meta_Mensual, Activo, Orden)
                    VALUES (%s, %s, %s, %s, %s, 1, %s)
                    """,
                    (nombre, pct, color, icono, meta, orden),
                )
        try:
            ensure_finanzas(query, execute, has_column, has_table)
        except Exception:
            pass
        _READY = True

    def ventas_rango(inicio: datetime, fin: Optional[datetime] = None) -> dict:
        anulada = "AND COALESCE(Anulada, 0) = 0" if col("ventas", "Anulada") else ""
        sql = f"""
            SELECT COALESCE(SUM(Total), 0) AS venta,
                   COUNT(*) AS tickets
            FROM ventas
            WHERE Fecha_Venta >= %s
            {anulada}
        """
        params: list[Any] = [inicio]
        if fin:
            sql += " AND Fecha_Venta < %s"
            params.append(fin)
        rows = query(sql, tuple(params))
        venta = _money(rows[0]["venta"] if rows else 0)
        tickets = int((rows[0]["tickets"] if rows else 0) or 0)
        utilidad_sql = """
            SELECT COALESCE(SUM(
                COALESCE(NULLIF(vp.Utilidad, 0), vp.Subtotal - (p.Precio_Compra * vp.Cantidad))
            ), 0) AS utilidad,
            COALESCE(SUM(
                CASE
                    WHEN vp.Costo_Unitario IS NOT NULL AND vp.Costo_Unitario > 0
                    THEN vp.Costo_Unitario * COALESCE(NULLIF(vp.Cantidad_Presentacion, 0), vp.Cantidad)
                    ELSE p.Precio_Compra * vp.Cantidad
                END
            ), 0) AS costo
            FROM ventas v
            JOIN productos_has_ventas vp ON vp.Ventas_Id_Factura = v.Id_Venta
            JOIN productos p ON p.Id_Producto = vp.Productos_Id_Producto
            WHERE v.Fecha_Venta >= %s
        """
        u_params: list[Any] = [inicio]
        if col("ventas", "Anulada"):
            utilidad_sql += " AND COALESCE(v.Anulada, 0) = 0"
        if fin:
            utilidad_sql += " AND v.Fecha_Venta < %s"
            u_params.append(fin)
        try:
            urows = query(utilidad_sql, tuple(u_params))
            utilidad = _money(urows[0]["utilidad"] if urows else 0)
            costo = _money(urows[0]["costo"] if urows else 0)
        except Exception:
            utilidad = 0.0
            costo = max(venta - utilidad, 0)
        if costo <= 0:
            costo = max(venta - utilidad, 0)
        margen = round((utilidad / venta) * 100, 2) if venta else 0.0
        return {
            "venta": venta,
            "costo": costo,
            "utilidad": utilidad,
            "margen_pct": margen,
            "tickets": tickets,
        }

    def _items_json(row: dict) -> list:
        raw = row.get("Items") if row else None
        if not raw:
            return []
        if isinstance(raw, list):
            return raw
        try:
            data = json.loads(raw)
            return data if isinstance(data, list) else []
        except Exception:
            return []

    def _linea_pedida(linea: dict, items: list) -> bool:
        if not items:
            return True
        pid = int(linea.get("Productos_Id_Producto") or 0)
        pres = int(linea.get("Presentacion_Id") or 0)
        for item in items:
            try:
                ip = int(item.get("producto_id") or 0)
            except (TypeError, ValueError):
                continue
            if ip != pid:
                continue
            try:
                ipres = int(item.get("presentacion_id") or 0)
            except (TypeError, ValueError):
                ipres = 0
            if ipres == 0 or ipres == pres:
                return True
        return False

    def items_venta(venta_id: int) -> list[dict]:
        pres = col("productos_has_ventas", "Presentacion_Nombre")
        extra = ""
        if pres:
            extra = """
                , COALESCE(NULLIF(vp.Presentacion_Nombre, ''), 'Unidad') AS presentacion,
                  COALESCE(NULLIF(vp.Cantidad_Presentacion, 0), vp.Cantidad) AS cantidad_presentacion,
                  COALESCE(vp.Factor, 1) AS factor,
                  COALESCE(vp.Presentacion_Id, 0) AS presentacion_id
            """
        else:
            extra = ", 'Unidad' AS presentacion, vp.Cantidad AS cantidad_presentacion, 1 AS factor, 0 AS presentacion_id"
        rows = query(
            f"""
            SELECT p.Nombre AS producto, vp.Cantidad AS cantidad_base, vp.Subtotal
                   {extra}
            FROM productos_has_ventas vp
            JOIN productos p ON p.Id_Producto = vp.Productos_Id_Producto
            WHERE vp.Ventas_Id_Factura = %s
            """,
            (venta_id,),
        )
        out = []
        for row in rows:
            out.append(
                {
                    "producto": row.get("producto") or "Producto",
                    "presentacion": row.get("presentacion") or "Unidad",
                    "cantidad": _money(row.get("cantidad_presentacion") or row.get("cantidad_base")),
                    "cantidad_base": _money(row.get("cantidad_base")),
                    "factor": _money(row.get("factor") or 1),
                    "presentacion_id": int(row.get("presentacion_id") or 0),
                    "subtotal": _money(row.get("Subtotal") or row.get("subtotal")),
                }
            )
        return out

    def enriquecer_solicitud(row: dict) -> dict:
        venta_id = int(row.get("Venta_Id") or 0)
        pedidos = _items_json(row)
        items = pedidos or (items_venta(venta_id) if venta_id else [])
        return {
            "id": int(row.get("Id") or 0),
            "venta_id": venta_id,
            "estado": row.get("Estado") or "PENDIENTE",
            "motivo": row.get("Motivo") or "",
            "nota": row.get("Nota_Respuesta") or "",
            "cajero": row.get("Cajero") or "",
            "cliente": row.get("Cliente") or "",
            "total": _money(row.get("Total")),
            "fecha": row.get("Fecha"),
            "fecha_respuesta": row.get("Fecha_Respuesta"),
            "parcial": bool(pedidos),
            "items": items,
        }

    def restaurar_inventario(venta_id: int, usuario: str, items: Optional[list] = None) -> None:
        pres = col("productos_has_ventas", "Presentacion_Id")
        if pres:
            lineas = query(
                """
                SELECT Productos_Id_Producto, Cantidad, Presentacion_Id, Factor,
                       COALESCE(NULLIF(Cantidad_Presentacion, 0), Cantidad) AS cant_pres,
                       COALESCE(Devuelto, 0) AS Devuelto, Subtotal
                FROM productos_has_ventas
                WHERE Ventas_Id_Factura = %s
                """,
                (venta_id,),
            )
        else:
            lineas = query(
                """
                SELECT Productos_Id_Producto, Cantidad, NULL AS Presentacion_Id,
                       1 AS Factor, Cantidad AS cant_pres, 0 AS Devuelto, Subtotal
                FROM productos_has_ventas
                WHERE Ventas_Id_Factura = %s
                """,
                (venta_id,),
            )
        items = items or []
        filtradas = []
        for linea in lineas:
            if int(linea.get("Devuelto") or 0) == 1:
                continue
            if not _linea_pedida(linea, items):
                continue
            filtradas.append(linea)
        if not filtradas:
            return
        returned_sub = 0.0
        for linea in filtradas:
            pid = int(linea["Productos_Id_Producto"])
            base = _money(linea.get("Cantidad"))
            execute(
                "UPDATE productos SET Cantidad = Cantidad + %s WHERE Id_Producto = %s",
                (base, pid),
            )
            if has_table("lotes"):
                lotes = query(
                    """
                    SELECT Id FROM lotes WHERE Producto_Id=%s
                    ORDER BY Fecha_Vencimiento IS NULL, Fecha_Vencimiento ASC, Id DESC
                    LIMIT 1
                    """,
                    (pid,),
                )
                if lotes:
                    execute(
                        "UPDATE lotes SET Cantidad = Cantidad + %s WHERE Id=%s",
                        (base, lotes[0]["Id"]),
                    )
                else:
                    execute(
                        """
                        INSERT INTO lotes (Producto_Id, Cantidad, Fecha_Ingreso, Lote, Proveedor)
                        VALUES (%s, %s, %s, %s, %s)
                        """,
                        (pid, base, now_bogota(), "DEVOLUCION", ""),
                    )
            if has_table("inventario_movimientos"):
                try:
                    execute(
                        """
                        INSERT INTO inventario_movimientos
                            (Producto_Id, Presentacion_Id, Tipo, Cantidad_Presentacion, Factor,
                             Cantidad_Base, Motivo, Usuario, Fecha)
                        VALUES (%s, %s, 'DEVOLUCION', %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            pid,
                            linea.get("Presentacion_Id"),
                            _money(linea.get("cant_pres")),
                            _money(linea.get("Factor") or 1),
                            base,
                            f"Devolución venta {venta_id}",
                            usuario or "admin",
                            now_bogota(),
                        ),
                    )
                except Exception:
                    pass
            returned_sub += _money(linea.get("Subtotal"))
            if col("productos_has_ventas", "Devuelto"):
                try:
                    execute(
                        """UPDATE productos_has_ventas SET Devuelto=1
                           WHERE Ventas_Id_Factura=%s AND Productos_Id_Producto=%s
                             AND COALESCE(Presentacion_Id,0)=COALESCE(%s,0)""",
                        (venta_id, pid, linea.get("Presentacion_Id")),
                    )
                except Exception:
                    pass

        restantes = 0
        if col("productos_has_ventas", "Devuelto"):
            try:
                cnt = query(
                    """SELECT COUNT(*) AS c FROM productos_has_ventas
                       WHERE Ventas_Id_Factura=%s AND COALESCE(Devuelto,0)=0""",
                    (venta_id,),
                )
                restantes = int((cnt[0].get("c") if cnt else 0) or 0)
            except Exception:
                restantes = 0

        try:
            if has_table("cliente_movimientos") and col("ventas", "Cliente_Id"):
                vrows = query(
                    "SELECT Cliente_Id FROM ventas WHERE Id_Venta=%s",
                    (venta_id,),
                )
                id_cliente = (vrows[0].get("Cliente_Id") if vrows else None)
                if id_cliente:
                    if restantes <= 0:
                        movs = query(
                            "SELECT Tipo, Monto, Puntos FROM cliente_movimientos WHERE Venta_Id=%s",
                            (venta_id,),
                        )
                        for mov in movs:
                            tipo = str(mov.get("Tipo") or "")
                            if tipo == "CREDITO":
                                execute(
                                    "UPDATE clientes SET Saldo_Pendiente = GREATEST(Saldo_Pendiente - %s, 0) WHERE Id_Cliente=%s",
                                    (_money(mov.get("Monto")), id_cliente),
                                )
                            elif tipo in ("PUNTOS", "CANJE"):
                                execute(
                                    "UPDATE clientes SET Puntos = GREATEST(Puntos - %s, 0) WHERE Id_Cliente=%s",
                                    (int(mov.get("Puntos") or 0), id_cliente),
                                )
                    elif returned_sub > 0:
                        execute(
                            "UPDATE clientes SET Saldo_Pendiente = GREATEST(Saldo_Pendiente - %s, 0) WHERE Id_Cliente=%s",
                            (returned_sub, id_cliente),
                        )
        except Exception:
            pass

        if restantes <= 0:
            if col("ventas", "Estado"):
                execute(
                    "UPDATE ventas SET Anulada=1, Estado='ANULADA' WHERE Id_Venta=%s",
                    (venta_id,),
                )
            else:
                execute("UPDATE ventas SET Anulada=1 WHERE Id_Venta=%s", (venta_id,))
        elif col("ventas", "Estado"):
            execute(
                "UPDATE ventas SET Anulada=0, Estado='PARCIAL' WHERE Id_Venta=%s",
                (venta_id,),
            )

    def fefo_resumen(laboratorio: str = "") -> dict:
        if not has_table("lotes"):
            return {"vencidos": 0, "d30": 0, "d60": 0, "d90": 0, "items": []}
        hoy = now_bogota().date()
        lab_sql = ""
        params: list[Any] = []
        marca = "p.Marca" if col("productos", "Marca") else "NULL"
        proveedor = "l.Proveedor"
        if laboratorio:
            lab_sql = " AND (COALESCE(p.Marca,'') LIKE %s OR COALESCE(l.Proveedor,'') LIKE %s)"
            like = f"%{laboratorio}%"
            params.extend([like, like])
        try:
            rows = query(
                f"""
                SELECT l.Id, l.Producto_Id, p.Nombre AS producto, l.Cantidad,
                       l.Fecha_Vencimiento, l.Lote, l.Proveedor, {marca} AS laboratorio
                FROM lotes l
                JOIN productos p ON p.Id_Producto = l.Producto_Id
                WHERE l.Cantidad > 0 AND l.Fecha_Vencimiento IS NOT NULL
                {lab_sql}
                ORDER BY l.Fecha_Vencimiento ASC
                """,
                tuple(params),
            )
        except Exception:
            rows = []
        vencidos = d30 = d60 = d90 = 0
        items = []
        for row in rows:
            fv = row.get("Fecha_Vencimiento")
            if isinstance(fv, str):
                try:
                    fv = datetime.strptime(fv[:10], "%Y-%m-%d").date()
                except ValueError:
                    continue
            elif hasattr(fv, "date"):
                fv = fv.date()
            if not fv:
                continue
            dias = (fv - hoy).days
            if dias < 0:
                nivel = "vencido"
                vencidos += 1
            elif dias <= 30:
                nivel = "d30"
                d30 += 1
            elif dias <= 60:
                nivel = "d60"
                d60 += 1
            elif dias <= 90:
                nivel = "d90"
                d90 += 1
            else:
                continue
            items.append(
                {
                    "id": row.get("Id"),
                    "producto": row.get("producto"),
                    "lote": row.get("Lote") or "",
                    "cantidad": _money(row.get("Cantidad")),
                    "vence": str(fv),
                    "dias": dias,
                    "nivel": nivel,
                    "laboratorio": row.get("laboratorio") or "",
                    "proveedor": row.get("Proveedor") or "",
                }
            )
        return {
            "vencidos": vencidos,
            "d30": d30,
            "d60": d60,
            "d90": d90,
            "items": items,
        }

    def bolsillos_snapshot() -> dict:
        return snapshot_bolsillos(
            query,
            execute,
            has_column,
            has_table,
            col,
            inicio_dia,
            inicio_mes,
            ventas_rango,
        )

    def live_sales(limit: int = 25) -> list[dict]:
        anulada = "AND COALESCE(v.Anulada, 0) = 0" if col("ventas", "Anulada") else ""
        util_expr = (
            "COALESCE(NULLIF(vp.Utilidad, 0), vp.Subtotal - (p.Precio_Compra * vp.Cantidad))"
            if col("productos_has_ventas", "Utilidad")
            else "vp.Subtotal - (p.Precio_Compra * vp.Cantidad)"
        )
        rows = query(
            f"""
            SELECT v.Id_Venta, v.Fecha_Venta, v.Total, e.Nombres AS cajero,
                   COALESCE(SUM({util_expr}), 0) AS utilidad
            FROM ventas v
            LEFT JOIN empleados e ON e.Id_Empleados = v.Empleados_Id_Empleados
            LEFT JOIN productos_has_ventas vp ON vp.Ventas_Id_Factura = v.Id_Venta
            LEFT JOIN productos p ON p.Id_Producto = vp.Productos_Id_Producto
            WHERE 1=1 {anulada}
            GROUP BY v.Id_Venta, v.Fecha_Venta, v.Total, e.Nombres
            ORDER BY v.Fecha_Venta DESC, v.Id_Venta DESC
            LIMIT %s
            """,
            (int(limit),),
        )
        pagos: dict[int, str] = {}
        if has_table("venta_pagos") and rows:
            ids = tuple(int(r["Id_Venta"]) for r in rows)
            if len(ids) == 1:
                pay_rows = query(
                    "SELECT Venta_Id, Metodo FROM venta_pagos WHERE Venta_Id=%s",
                    ids,
                )
            else:
                placeholders = ",".join(["%s"] * len(ids))
                pay_rows = query(
                    f"SELECT Venta_Id, Metodo FROM venta_pagos WHERE Venta_Id IN ({placeholders})",
                    ids,
                )
            for pr in pay_rows:
                vid = int(pr["Venta_Id"])
                metodo = pr.get("Metodo") or "Efectivo"
                pagos[vid] = metodo if vid not in pagos else f"{pagos[vid]}, {metodo}"
        feed = []
        for row in rows:
            vid = int(row["Id_Venta"])
            feed.append(
                {
                    "id": vid,
                    "fecha": row.get("Fecha_Venta"),
                    "total": _money(row.get("Total")),
                    "utilidad": _money(row.get("utilidad")),
                    "cajero": row.get("cajero") or "Caja",
                    "pago": pagos.get(vid, "Efectivo"),
                }
            )
        return feed

    def utilidad_presentacion(dias: int = 30) -> dict:
        inicio = now_bogota() - timedelta(days=max(1, dias))
        has_pres = col("productos_has_ventas", "Presentacion_Nombre")
        pres_expr = (
            "COALESCE(NULLIF(vp.Presentacion_Nombre, ''), 'Unidad')"
            if has_pres
            else "'Unidad'"
        )
        util_expr = (
            "COALESCE(NULLIF(vp.Utilidad, 0), vp.Subtotal - (p.Precio_Compra * vp.Cantidad))"
            if col("productos_has_ventas", "Utilidad")
            else "vp.Subtotal - (p.Precio_Compra * vp.Cantidad)"
        )
        cat = "p.Categoria" if col("productos", "Categoria") else "NULL"
        anulada = "AND COALESCE(v.Anulada, 0) = 0" if col("ventas", "Anulada") else ""
        por_pres = query(
            f"""
            SELECT {pres_expr} AS presentacion,
                   SUM(vp.Subtotal) AS venta,
                   SUM({util_expr}) AS utilidad,
                   SUM(vp.Cantidad) AS unidades
            FROM productos_has_ventas vp
            JOIN productos p ON p.Id_Producto = vp.Productos_Id_Producto
            JOIN ventas v ON v.Id_Venta = vp.Ventas_Id_Factura
            WHERE v.Fecha_Venta >= %s {anulada}
            GROUP BY {pres_expr}
            ORDER BY utilidad DESC
            """,
            (inicio,),
        )
        por_cat = query(
            f"""
            SELECT COALESCE({cat}, 'Sin categoría') AS categoria,
                   SUM(vp.Subtotal) AS venta,
                   SUM({util_expr}) AS utilidad
            FROM productos_has_ventas vp
            JOIN productos p ON p.Id_Producto = vp.Productos_Id_Producto
            JOIN ventas v ON v.Id_Venta = vp.Ventas_Id_Factura
            WHERE v.Fecha_Venta >= %s {anulada}
            GROUP BY COALESCE({cat}, 'Sin categoría')
            ORDER BY utilidad DESC
            LIMIT 12
            """,
            (inicio,),
        )
        top = query(
            f"""
            SELECT p.Nombre AS producto, {pres_expr} AS presentacion,
                   SUM(vp.Subtotal) AS venta, SUM({util_expr}) AS utilidad
            FROM productos_has_ventas vp
            JOIN productos p ON p.Id_Producto = vp.Productos_Id_Producto
            JOIN ventas v ON v.Id_Venta = vp.Ventas_Id_Factura
            WHERE v.Fecha_Venta >= %s {anulada}
            GROUP BY p.Id_Producto, p.Nombre, {pres_expr}
            ORDER BY utilidad DESC
            LIMIT 15
            """,
            (inicio,),
        )
        return {
            "dias": dias,
            "por_presentacion": [
                {
                    "presentacion": r.get("presentacion") or "Unidad",
                    "venta": _money(r.get("venta")),
                    "utilidad": _money(r.get("utilidad")),
                    "unidades": _money(r.get("unidades")),
                }
                for r in por_pres
            ],
            "por_categoria": [
                {
                    "categoria": r.get("categoria") or "Sin categoría",
                    "venta": _money(r.get("venta")),
                    "utilidad": _money(r.get("utilidad")),
                }
                for r in por_cat
            ],
            "top_productos": [
                {
                    "producto": r.get("producto"),
                    "presentacion": r.get("presentacion") or "Unidad",
                    "venta": _money(r.get("venta")),
                    "utilidad": _money(r.get("utilidad")),
                }
                for r in top
            ],
        }

    # ---- rutas ----
    async def solicitar_devolucion(body: DevolucionSolicitar):
        ensure()
        anulada_sql = "Anulada" if col("ventas", "Anulada") else "0 AS Anulada"
        ventas = query(
            f"SELECT Id_Venta, Total, Fecha_Venta, {anulada_sql} FROM ventas WHERE Id_Venta=%s",
            (body.venta_id,),
        )
        if not ventas:
            raise HTTPException(status_code=404, detail="Venta no encontrada")
        venta = ventas[0]
        if int(venta.get("Anulada") or 0) == 1:
            raise HTTPException(status_code=400, detail="La venta ya fue anulada")
        existentes = query(
            """
            SELECT * FROM devolucion_solicitudes
            WHERE Venta_Id=%s AND Estado='PENDIENTE'
            ORDER BY Id DESC LIMIT 1
            """,
            (body.venta_id,),
        )
        if existentes:
            return enriquecer_solicitud(existentes[0])
        cajero = body.cajero
        cliente = body.cliente
        items = list(body.items or [])
        total = _money(venta.get("Total"))
        if items:
            total = round(sum(_money(it.get("subtotal")) for it in items), 2) or total
        if not cajero:
            try:
                emp = query(
                    """
                    SELECT e.Nombres AS cajero
                    FROM ventas v
                    LEFT JOIN empleados e ON e.Id_Empleados = v.Empleados_Id_Empleados
                    WHERE v.Id_Venta=%s
                    """,
                    (body.venta_id,),
                )
                cajero = (emp[0].get("cajero") if emp else "") or ""
            except Exception:
                cajero = ""
        items_txt = json.dumps(items, ensure_ascii=False) if items else None
        try:
            new_id = execute(
                """
                INSERT INTO devolucion_solicitudes
                    (Venta_Id, Estado, Motivo, Cajero, Cliente, Total, Fecha, Items)
                VALUES (%s, 'PENDIENTE', %s, %s, %s, %s, %s, %s)
                """,
                (
                    body.venta_id,
                    body.motivo[:250],
                    (cajero or "")[:80],
                    (cliente or "")[:120],
                    total,
                    now_bogota(),
                    items_txt,
                ),
            )
        except Exception:
            new_id = execute(
                """
                INSERT INTO devolucion_solicitudes
                    (Venta_Id, Estado, Motivo, Cajero, Cliente, Total, Fecha)
                VALUES (%s, 'PENDIENTE', %s, %s, %s, %s, %s)
                """,
                (
                    body.venta_id,
                    body.motivo[:250],
                    (cajero or "")[:80],
                    (cliente or "")[:120],
                    total,
                    now_bogota(),
                ),
            )
        if col("ventas", "Estado"):
            try:
                execute(
                    "UPDATE ventas SET Estado='PENDIENTE_APROBACION' WHERE Id_Venta=%s",
                    (body.venta_id,),
                )
            except Exception:
                pass
        rows = query("SELECT * FROM devolucion_solicitudes WHERE Id=%s", (new_id,))
        payload = enriquecer_solicitud(rows[0] if rows else {"Id": new_id, "Venta_Id": body.venta_id})
        await HUB.broadcast({"tipo": "devolucion_nueva", "solicitud": payload})
        return payload

    def pendientes():
        ensure()
        rows = query(
            """
            SELECT * FROM devolucion_solicitudes
            WHERE Estado='PENDIENTE'
            ORDER BY Fecha DESC, Id DESC
            """
        )
        return [enriquecer_solicitud(r) for r in rows]

    def detalle_devolucion(id: int):
        ensure()
        rows = query("SELECT * FROM devolucion_solicitudes WHERE Id=%s", (id,))
        if not rows:
            raise HTTPException(status_code=404, detail="Solicitud no encontrada")
        return enriquecer_solicitud(rows[0])

    async def responder_devolucion(id: int, body: DevolucionResponder):
        ensure()
        require_admin_actor(body.usuario or "", body.admin_id)
        estado = (body.estado or "").strip().upper()
        if estado not in {"APROBADO", "RECHAZADO"}:
            raise HTTPException(status_code=400, detail="estado debe ser APROBADO o RECHAZADO")
        rows = query("SELECT * FROM devolucion_solicitudes WHERE Id=%s", (id,))
        if not rows:
            raise HTTPException(status_code=404, detail="Solicitud no encontrada")
        sol = rows[0]
        if (sol.get("Estado") or "") != "PENDIENTE":
            raise HTTPException(status_code=400, detail="La solicitud ya fue resuelta")
        venta_id = int(sol["Venta_Id"])
        pedidos = _items_json(sol)
        if estado == "APROBADO":
            restaurar_inventario(venta_id, f"admin:{body.admin_id or 0}", pedidos)
        elif col("ventas", "Estado"):
            try:
                resto = 0
                if col("productos_has_ventas", "Devuelto"):
                    cnt = query(
                        """SELECT COUNT(*) AS c FROM productos_has_ventas
                           WHERE Ventas_Id_Factura=%s AND COALESCE(Devuelto,0)=1""",
                        (venta_id,),
                    )
                    resto = int((cnt[0].get("c") if cnt else 0) or 0)
                nuevo = "PARCIAL" if resto else "ACTIVA"
                execute(
                    "UPDATE ventas SET Estado=%s WHERE Id_Venta=%s AND COALESCE(Anulada,0)=0",
                    (nuevo, venta_id),
                )
            except Exception:
                pass
        execute(
            """
            UPDATE devolucion_solicitudes
            SET Estado=%s, Nota_Respuesta=%s, Admin_Id=%s, Fecha_Respuesta=%s
            WHERE Id=%s
            """,
            (estado, (body.nota or "")[:250], body.admin_id, now_bogota(), id),
        )
        actualizada = enriquecer_solicitud(
            query("SELECT * FROM devolucion_solicitudes WHERE Id=%s", (id,))[0]
        )
        await HUB.broadcast({"tipo": "devolucion_resuelta", "solicitud": actualizada})
        return actualizada

    def listar_bolsillos():
        return bolsillos_snapshot()

    def crear_bolsillo(body: BolsilloIn):
        ensure()
        require_admin_actor(body.usuario or "", body.admin_id)
        new_id = execute(
            """
            INSERT INTO bolsillos (Nombre, Porcentaje, Color, Icono, Meta_Mensual, Activo, Orden, Codigo)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                body.nombre[:80],
                body.porcentaje,
                body.color[:16],
                body.icono[:40],
                body.meta_mensual,
                1 if body.activo else 0,
                body.orden,
                (body.codigo or "")[:40],
            ),
        )
        return {"ok": True, "id": new_id}

    def actualizar_bolsillo(id: int, body: BolsilloIn):
        ensure()
        require_admin_actor(body.usuario or "", body.admin_id)
        execute(
            """
            UPDATE bolsillos
            SET Nombre=%s, Porcentaje=%s, Color=%s, Icono=%s, Meta_Mensual=%s, Activo=%s, Orden=%s, Codigo=%s
            WHERE Id=%s
            """,
            (
                body.nombre[:80],
                body.porcentaje,
                body.color[:16],
                body.icono[:40],
                body.meta_mensual,
                1 if body.activo else 0,
                body.orden,
                (body.codigo or "")[:40],
                id,
            ),
        )
        return {"ok": True, "id": id}

    def egreso_bolsillo(id: int, body: BolsilloEgresoIn):
        ensure()
        require_admin_actor(body.usuario or "", body.admin_id)
        registrar_egresos(query, execute, has_column, now_bogota, id, body)
        return bolsillos_snapshot()

    def resumen_comando():
        try:
            ensure()
        except Exception as error:
            return {
                "hoy": {"venta": 0, "costo": 0, "utilidad": 0, "margen_pct": 0, "tickets": 0},
                "mes": {"venta": 0, "costo": 0, "utilidad": 0, "margen_pct": 0, "tickets": 0},
                "pendientes": 0,
                "fefo": {"vencidos": 0, "d30": 0, "d60": 0, "d90": 0},
                "stock_bajo": 0,
                "cierres_hoy": 0,
                "bolsillos": {"bolsillos": []},
                "live_sales": [],
                "error": str(error)[:180],
            }
        try:
            hoy = ventas_rango(inicio_dia())
        except Exception:
            hoy = {"venta": 0, "costo": 0, "utilidad": 0, "margen_pct": 0, "tickets": 0}
        try:
            mes = ventas_rango(inicio_mes())
        except Exception:
            mes = {"venta": 0, "costo": 0, "utilidad": 0, "margen_pct": 0, "tickets": 0}
        pendientes = 0
        try:
            pend = query(
                "SELECT COUNT(*) AS c FROM devolucion_solicitudes WHERE Estado='PENDIENTE'"
            )
            pendientes = int(pend[0]["c"] if pend else 0)
        except Exception:
            pendientes = 0
        try:
            fefo = fefo_resumen()
        except Exception:
            fefo = {"vencidos": 0, "d30": 0, "d60": 0, "d90": 0}
        stock_bajo = 0
        if col("productos", "Stock_Minimo"):
            try:
                sb = query(
                    """
                    SELECT COUNT(*) AS c FROM productos
                    WHERE Cantidad <= COALESCE(Stock_Minimo, 10)
                    """
                )
                stock_bajo = int(sb[0]["c"] if sb else 0)
            except Exception:
                stock_bajo = 0
        cierres_hoy = 0
        if has_table("cierre_turno"):
            try:
                cr = query(
                    "SELECT COUNT(*) AS c FROM cierre_turno WHERE Fecha >= %s",
                    (inicio_dia(),),
                )
                cierres_hoy = int(cr[0]["c"] if cr else 0)
            except Exception:
                cierres_hoy = 0
        try:
            bolsas = bolsillos_snapshot()
        except Exception:
            bolsas = {"bolsillos": []}
        try:
            live = live_sales(8)
        except Exception:
            live = []
        return {
            "hoy": hoy,
            "mes": mes,
            "pendientes": pendientes,
            "fefo": {
                "vencidos": fefo.get("vencidos", 0),
                "d30": fefo.get("d30", 0),
                "d60": fefo.get("d60", 0),
                "d90": fefo.get("d90", 0),
            },
            "stock_bajo": stock_bajo,
            "cierres_hoy": cierres_hoy,
            "bolsillos": bolsas,
            "live_sales": live,
        }

    def rentabilidad(dias: int = Query(30, ge=1, le=365)):
        return utilidad_presentacion(dias)

    def fefo(laboratorio: str = Query("")):
        return fefo_resumen(laboratorio)

    def feed(limit: int = Query(25, ge=1, le=100)):
        return live_sales(limit)

    rutas = [
        ("/devoluciones/solicitar/", solicitar_devolucion, ["POST"]),
        ("/devoluciones/pendientes/", pendientes, ["GET"]),
        ("/devoluciones/{id}/", detalle_devolucion, ["GET"]),
        ("/devoluciones/{id}/responder/", responder_devolucion, ["POST"]),
        ("/bolsillos/", listar_bolsillos, ["GET"]),
        ("/bolsillos/", crear_bolsillo, ["POST"]),
        ("/bolsillos/{id}/", actualizar_bolsillo, ["PUT"]),
        ("/bolsillos/{id}/egreso/", egreso_bolsillo, ["POST"]),
        ("/comando/resumen/", resumen_comando, ["GET"]),
        ("/comando/rentabilidad/", rentabilidad, ["GET"]),
        ("/comando/fefo/", fefo, ["GET"]),
        ("/comando/live-sales/", feed, ["GET"]),
    ]
    for path, fn, methods in rutas:
        app.add_api_route(
            path, fn, methods=methods, name=f"{fn.__name__}_{methods[0]}"
        )
        app.add_api_route(
            "/api/v1" + path,
            fn,
            methods=methods,
            name=f"{fn.__name__}_{methods[0]}_v1",
        )

    @app.websocket("/ws/devoluciones/admin/{admin_id}/")
    async def ws_devoluciones(websocket: WebSocket, admin_id: int):
        await HUB.connect(websocket)
        try:
            await websocket.send_json({"tipo": "hello", "admin_id": admin_id})
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            HUB.disconnect(websocket)
        except Exception:
            HUB.disconnect(websocket)

    @app.websocket("/api/v1/ws/devoluciones/admin/{admin_id}/")
    async def ws_devoluciones_v1(websocket: WebSocket, admin_id: int):
        await ws_devoluciones(websocket, admin_id)

    attach_routes(
        app,
        {
            "query": query,
            "execute": execute,
            "has_column": has_column,
            "has_table": has_table,
            "col": col,
            "inicio_dia": inicio_dia,
            "inicio_mes": inicio_mes,
            "now_bogota": now_bogota,
            "ventas_rango": ventas_rango,
            "snapshot_fn": bolsillos_snapshot,
        },
    )
