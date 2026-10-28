"""API de cierre diario y conciliación de medios (Entrega 1)."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field


class ReclasificarIn(BaseModel):
    venta_id: int
    metodo_origen: str
    metodo_destino: str
    monto: float = Field(gt=0)
    motivo: str = Field(min_length=3)
    usuario: str = ""
    cierre_id: Optional[int] = None


class MedioConciliacionIn(BaseModel):
    metodo: str
    etiqueta: str = ""
    sistema: float = 0
    declarado: float = 0
    diferencia: float = 0


class CierreDiarioIn(BaseModel):
    cajero: str = ""
    usuario: str = ""
    fecha_desde: str
    monto_inicial: float = 0
    conteo_fisico: float = 0
    esperado: float = 0
    descuadre: float = 0
    total_ventas: float = 0
    efectivo: float = 0
    nequi: float = 0
    tarjeta: float = 0
    transferencia: float = 0
    credito: float = 0
    entradas: float = 0
    salidas: float = 0
    abonos: float = 0
    tickets: int = 0
    articulos: int = 0
    tipo: str = "definitivo"
    estado: str = ""
    observacion: str = ""
    correcciones: int = 0
    medios: list[MedioConciliacionIn] = Field(default_factory=list)


def _money(v: Any) -> float:
    try:
        return round(float(v or 0), 2)
    except (TypeError, ValueError):
        return 0.0


def register(app: FastAPI) -> None:
    from main import col, execute, has_column, json_safe, now_bogota, query

    def has_table(name: str) -> bool:
        rows = query(
            """
            SELECT COUNT(*) AS c FROM information_schema.TABLES
            WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s
            """,
            (name,),
        )
        return bool(rows and int(rows[0]["c"]))

    def ensure() -> None:
        execute(
            """
            CREATE TABLE IF NOT EXISTS cierre_turno_medios (
                Id INT AUTO_INCREMENT PRIMARY KEY,
                Cierre_Id INT NOT NULL,
                Metodo VARCHAR(40) NOT NULL,
                Etiqueta VARCHAR(60) DEFAULT '',
                Sistema DECIMAL(12,2) DEFAULT 0,
                Declarado DECIMAL(12,2) DEFAULT 0,
                Diferencia DECIMAL(12,2) DEFAULT 0,
                INDEX idx_cierre_medios (Cierre_Id)
            )
            """
        )
        execute(
            """
            CREATE TABLE IF NOT EXISTS venta_pago_correcciones (
                Id INT AUTO_INCREMENT PRIMARY KEY,
                Venta_Id INT NOT NULL,
                Metodo_Anterior VARCHAR(40) NOT NULL,
                Metodo_Nuevo VARCHAR(40) NOT NULL,
                Monto DECIMAL(12,2) NOT NULL,
                Motivo VARCHAR(255) DEFAULT '',
                Usuario VARCHAR(80) DEFAULT '',
                Fecha DATETIME,
                Cierre_Id INT NULL,
                INDEX idx_vpc_venta (Venta_Id),
                INDEX idx_vpc_cierre (Cierre_Id),
                INDEX idx_vpc_fecha (Fecha)
            )
            """
        )
        for column, defn in (
            ("Estado", "VARCHAR(40) DEFAULT ''"),
            ("Observacion", "TEXT NULL"),
            ("Correcciones", "INT DEFAULT 0"),
            ("Fecha_Desde", "DATETIME NULL"),
            ("Usuario", "VARCHAR(80) DEFAULT ''"),
        ):
            if has_table("cierre_turno") and not has_column("cierre_turno", column):
                try:
                    execute(f"ALTER TABLE cierre_turno ADD COLUMN `{column}` {defn}")
                    try:
                        from main import _column_cache

                        _column_cache.pop(("cierre_turno", column), None)
                    except Exception:
                        pass
                except Exception:
                    pass

    def _totales_medios(fecha_desde: str, id_empleado: Optional[int] = None) -> dict:
        if not has_table("venta_pagos"):
            return {"Efectivo": 0.0, "Nequi": 0.0, "Tarjeta": 0.0, "Transferencia": 0.0, "Crédito": 0.0}
        sql = """
            SELECT vp.Metodo AS metodo, COALESCE(SUM(vp.Monto), 0) AS monto
            FROM venta_pagos vp
            JOIN ventas v ON v.Id_Venta = vp.Venta_Id
            WHERE v.Fecha_Venta >= %s AND COALESCE(v.Anulada, 0) = 0
        """
        params: list[Any] = [fecha_desde]
        if id_empleado is not None:
            sql += " AND v.Empleados_Id_Empleados = %s"
            params.append(id_empleado)
        sql += " GROUP BY vp.Metodo"
        raw = {r["metodo"]: _money(r["monto"]) for r in query(sql, tuple(params))}
        return {
            "Efectivo": _money(raw.get("Efectivo")),
            "Nequi": _money(raw.get("Nequi")),
            "Tarjeta": _money(raw.get("Tarjeta")),
            "Transferencia": _money(raw.get("Transferencia")),
            "Crédito": _money(raw.get("Crédito")),
            "_raw": raw,
        }

    def resumen_get(
        fecha_desde: str = Query(...),
        id_empleado: Optional[int] = None,
    ):
        ensure()
        medios = _totales_medios(fecha_desde, id_empleado)
        nequi_grupo = _money(medios["Nequi"] + medios["Transferencia"])
        ventas = query(
            """
            SELECT COALESCE(SUM(Total), 0) AS total, COUNT(*) AS tickets
            FROM ventas
            WHERE Fecha_Venta >= %s AND COALESCE(Anulada, 0) = 0
            """
            + (" AND Empleados_Id_Empleados = %s" if id_empleado is not None else ""),
            (fecha_desde,) if id_empleado is None else (fecha_desde, id_empleado),
        )
        total = _money(ventas[0]["total"] if ventas else 0)
        tickets = int(ventas[0]["tickets"] if ventas else 0)
        correcciones = 0
        if has_table("venta_pago_correcciones"):
            cr = query(
                "SELECT COUNT(*) AS c FROM venta_pago_correcciones WHERE Fecha >= %s",
                (fecha_desde,),
            )
            correcciones = int(cr[0]["c"] if cr else 0)
        return {
            "fecha_desde": fecha_desde,
            "total_ventas": total,
            "tickets": tickets,
            "correcciones": correcciones,
            "medios": [
                {"metodo": "Efectivo", "etiqueta": "EFECTIVO", "sistema": medios["Efectivo"]},
                {"metodo": "Nequi", "etiqueta": "NEQUI", "sistema": nequi_grupo},
                {"metodo": "Tarjeta", "etiqueta": "DATAFONO", "sistema": medios["Tarjeta"]},
            ],
            "otros": {
                "Transferencia": medios["Transferencia"],
                "Nequi_solo": medios["Nequi"],
                "Credito": medios["Crédito"],
            },
        }

    def reclasificar(body: ReclasificarIn):
        ensure()
        if not has_table("venta_pagos"):
            raise HTTPException(400, "No existe tabla venta_pagos")
        origen = body.metodo_origen.strip()
        destino = body.metodo_destino.strip()
        if origen == destino:
            raise HTTPException(400, "Origen y destino iguales")
        motivo = body.motivo.strip()
        if len(motivo) < 3:
            raise HTTPException(400, "Motivo obligatorio")

        from main import db_config
        import pymysql

        cfg = db_config()
        cfg = {**cfg, "autocommit": False}
        conn = pymysql.connect(**cfg)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT Id_Venta, Total, COALESCE(Anulada, 0) AS Anulada FROM ventas WHERE Id_Venta=%s",
                    (body.venta_id,),
                )
                venta = cur.fetchone()
                if not venta:
                    raise HTTPException(404, "Venta no encontrada")
                if int(venta.get("Anulada") or 0) == 1:
                    raise HTTPException(400, "Venta anulada")
                total = _money(venta.get("Total"))
                monto = _money(body.monto)

                cur.execute(
                    "SELECT Id, Metodo, Monto FROM venta_pagos WHERE Venta_Id=%s ORDER BY Id",
                    (body.venta_id,),
                )
                filas = list(cur.fetchall() or [])
                disponible = _money(
                    sum(_money(f["Monto"]) for f in filas if str(f["Metodo"]) == origen)
                )
                if disponible + 0.009 < monto:
                    raise HTTPException(400, f"El medio {origen} solo tiene {disponible}")

                restante = monto
                for f in filas:
                    if str(f["Metodo"]) != origen or restante <= 0:
                        continue
                    mon = _money(f["Monto"])
                    if mon <= restante + 0.009:
                        cur.execute("DELETE FROM venta_pagos WHERE Id=%s", (f["Id"],))
                        restante = _money(restante - mon)
                    else:
                        cur.execute(
                            "UPDATE venta_pagos SET Monto=%s WHERE Id=%s",
                            (_money(mon - restante), f["Id"]),
                        )
                        restante = 0.0

                cur.execute(
                    "SELECT Id, Monto FROM venta_pagos WHERE Venta_Id=%s AND Metodo=%s ORDER BY Id LIMIT 1",
                    (body.venta_id, destino),
                )
                dest = cur.fetchone()
                if dest:
                    cur.execute(
                        "UPDATE venta_pagos SET Monto=%s WHERE Id=%s",
                        (_money(_money(dest["Monto"]) + monto), dest["Id"]),
                    )
                else:
                    cur.execute(
                        "INSERT INTO venta_pagos (Venta_Id, Metodo, Monto) VALUES (%s, %s, %s)",
                        (body.venta_id, destino, monto),
                    )

                cur.execute(
                    "SELECT COALESCE(SUM(Monto), 0) AS s FROM venta_pagos WHERE Venta_Id=%s",
                    (body.venta_id,),
                )
                suma = _money((cur.fetchone() or {}).get("s"))
                if abs(suma - total) > 0.05:
                    conn.rollback()
                    raise HTTPException(
                        409,
                        f"Validación falló: suma pagos {suma} != total venta {total}",
                    )

                # Nunca modificar ventas.Total
                cur.execute(
                    """
                    INSERT INTO venta_pago_correcciones
                        (Venta_Id, Metodo_Anterior, Metodo_Nuevo, Monto, Motivo, Usuario, Fecha, Cierre_Id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        body.venta_id,
                        origen,
                        destino,
                        monto,
                        motivo[:250],
                        (body.usuario or "")[:80],
                        datetime.now(),
                        body.cierre_id,
                    ),
                )
            conn.commit()
            return {
                "ok": True,
                "venta_id": body.venta_id,
                "total_venta": total,
                "suma_pagos": suma,
                "metodo_anterior": origen,
                "metodo_nuevo": destino,
                "monto": monto,
            }
        except HTTPException:
            try:
                conn.rollback()
            except Exception:
                pass
            raise
        except Exception as error:
            try:
                conn.rollback()
            except Exception:
                pass
            raise HTTPException(500, f"Error al reclasificar: {error}")
        finally:
            conn.close()

    def _calc_estado(medios: list[MedioConciliacionIn], correcciones: int) -> str:
        hay = any(abs(_money(m.diferencia)) >= 0.5 for m in medios)
        if hay:
            return "CON_DESCUADRE"
        if correcciones > 0:
            return "CUADRADO_CON_CORRECCIONES"
        return "CUADRADO"

    def guardar_cierre(body: CierreDiarioIn):
        ensure()
        if not has_table("cierre_turno"):
            raise HTTPException(500, "No existe cierre_turno")
        medios = list(body.medios or [])
        for m in medios:
            m.diferencia = _money(m.declarado - m.sistema)
        estado = body.estado or _calc_estado(medios, body.correcciones)
        if estado not in ("CUADRADO", "CUADRADO_CON_CORRECCIONES", "CON_DESCUADRE"):
            raise HTTPException(400, "Estado inválido")
        if estado == "CON_DESCUADRE" and len((body.observacion or "").strip()) < 5:
            raise HTTPException(400, "Observación obligatoria cuando hay descuadre")

        # Validar que no se intente alterar totales de ventas vía este endpoint
        # (solo se registran montos de recaudo del turno)
        cols_extra = col("cierre_turno", "Estado")
        if cols_extra:
            cierre_id = execute(
                """
                INSERT INTO cierre_turno
                    (Cajero, Fecha, Monto_Inicial, Conteo_Fisico, Esperado, Descuadre,
                     Total_Ventas, Efectivo, Nequi, Tarjeta, Transferencia, Entradas, Salidas,
                     Tipo, Estado, Observacion, Correcciones, Fecha_Desde, Usuario)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    body.cajero,
                    now_bogota().replace(tzinfo=None) if hasattr(now_bogota(), "tzinfo") else datetime.now(),
                    body.monto_inicial,
                    body.conteo_fisico,
                    body.esperado,
                    body.descuadre,
                    body.total_ventas,
                    body.efectivo,
                    body.nequi,
                    body.tarjeta,
                    body.transferencia,
                    body.entradas + body.abonos,
                    body.salidas,
                    body.tipo[:20],
                    estado,
                    (body.observacion or "")[:2000],
                    body.correcciones,
                    body.fecha_desde,
                    body.usuario,
                ),
            )
        else:
            cierre_id = execute(
                """
                INSERT INTO cierre_turno
                    (Cajero, Fecha, Monto_Inicial, Conteo_Fisico, Esperado, Descuadre,
                     Total_Ventas, Efectivo, Nequi, Tarjeta, Transferencia, Entradas, Salidas)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    body.cajero,
                    datetime.now(),
                    body.monto_inicial,
                    body.conteo_fisico,
                    body.esperado,
                    body.descuadre,
                    body.total_ventas,
                    body.efectivo,
                    body.nequi,
                    body.tarjeta,
                    body.transferencia,
                    body.entradas + body.abonos,
                    body.salidas,
                ),
            )

        for m in medios:
            execute(
                """
                INSERT INTO cierre_turno_medios
                    (Cierre_Id, Metodo, Etiqueta, Sistema, Declarado, Diferencia)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    cierre_id,
                    m.metodo[:40],
                    (m.etiqueta or m.metodo)[:60],
                    _money(m.sistema),
                    _money(m.declarado),
                    _money(m.diferencia),
                ),
            )

        if has_table("venta_pago_correcciones"):
            execute(
                """
                UPDATE venta_pago_correcciones
                SET Cierre_Id=%s
                WHERE Cierre_Id IS NULL AND Fecha >= %s
                """
                + (" AND Usuario=%s" if body.usuario else ""),
                (cierre_id, body.fecha_desde, body.usuario)
                if body.usuario
                else (cierre_id, body.fecha_desde),
            )

        return {"ok": True, "id": cierre_id, "estado": estado}

    def detalle_cierre(cierre_id: int):
        ensure()
        rows = query("SELECT * FROM cierre_turno WHERE Id=%s", (cierre_id,))
        if not rows:
            raise HTTPException(404, "Cierre no encontrado")
        medios = []
        if has_table("cierre_turno_medios"):
            medios = query(
                "SELECT * FROM cierre_turno_medios WHERE Cierre_Id=%s ORDER BY Id",
                (cierre_id,),
            )
        return {"cierre": json_safe(rows[0]), "medios": json_safe(medios)}

    def auditoria_cierre(
        cierre_id: Optional[int] = None,
        fecha_desde: Optional[str] = None,
        limit: int = Query(100, ge=1, le=500),
    ):
        ensure()
        if not has_table("venta_pago_correcciones"):
            return []
        sql = "SELECT * FROM venta_pago_correcciones WHERE 1=1"
        params: list[Any] = []
        if cierre_id:
            sql += " AND Cierre_Id=%s"
            params.append(cierre_id)
        if fecha_desde:
            sql += " AND Fecha >= %s"
            params.append(fecha_desde)
        sql += " ORDER BY Fecha DESC, Id DESC LIMIT %s"
        params.append(limit)
        return json_safe(query(sql, tuple(params)))

    rutas = [
        ("/cierre-diario/resumen/", resumen_get, ["GET"]),
        ("/cierre-diario/reclasificar/", reclasificar, ["POST"]),
        ("/cierre-diario/auditoria/", auditoria_cierre, ["GET"]),
        ("/cierre-diario/", guardar_cierre, ["POST"]),
        ("/cierre-diario/{cierre_id}/", detalle_cierre, ["GET"]),
    ]
    for path, fn, methods in rutas:
        app.add_api_route(path, fn, methods=methods, name=f"cd_{fn.__name__}_{methods[0]}")
        app.add_api_route(
            "/api/v1" + path,
            fn,
            methods=methods,
            name=f"cd_{fn.__name__}_{methods[0]}_v1",
        )
