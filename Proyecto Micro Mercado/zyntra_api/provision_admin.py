"""API provisión administrativa (Entrega 3). Solo admin. Autocontenido para Railway."""
from __future__ import annotations

import math
from datetime import datetime
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, Query


PCT = 0.30
MULTIPLO = 10000.0


def _money(v: Any) -> float:
    try:
        return round(float(v or 0), 2)
    except (TypeError, ValueError):
        return 0.0


def redondear_arriba(valor: float) -> float:
    v = _money(valor)
    if v <= 0:
        return 0.0
    return float(math.ceil(v / MULTIPLO) * MULTIPLO)


def calcular(
    ventas_generales: float,
    saldo_pendiente_anterior: float,
    efectivo_disponible: float,
    efectivo_provisionado: Optional[float] = None,
) -> dict:
    ventas = max(0.0, _money(ventas_generales))
    treinta = _money(ventas * PCT)
    objetivo = redondear_arriba(treinta)
    pendiente_ant = max(0.0, _money(saldo_pendiente_anterior))
    objetivo_total = _money(objetivo + pendiente_ant)
    efectivo = max(0.0, _money(efectivo_disponible))
    tope = min(objetivo_total, efectivo)
    if efectivo_provisionado is None:
        provisionado = tope
    else:
        provisionado = max(0.0, min(_money(efectivo_provisionado), tope))
    return {
        "ventas_generales": ventas,
        "porcentaje": 30.0,
        "treinta_porciento": treinta,
        "provision_objetivo": objetivo,
        "saldo_pendiente_anterior": pendiente_ant,
        "objetivo_total": objetivo_total,
        "efectivo_disponible": efectivo,
        "efectivo_provisionado": provisionado,
        "nuevo_saldo_pendiente": _money(objetivo_total - provisionado),
    }


def register(app: FastAPI) -> None:
    from main import execute, json_safe, query

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
            CREATE TABLE IF NOT EXISTS provision_admin_estado (
                Id INT PRIMARY KEY,
                Saldo_Pendiente DECIMAL(14,2) NOT NULL DEFAULT 0,
                Fecha_Actualizacion DATETIME NULL
            )
            """
        )
        execute(
            "INSERT IGNORE INTO provision_admin_estado (Id, Saldo_Pendiente, Fecha_Actualizacion) VALUES (1, 0, NULL)"
        )
        execute(
            """
            CREATE TABLE IF NOT EXISTS provision_admin (
                Id INT AUTO_INCREMENT PRIMARY KEY,
                Cierre_General_Id INT NOT NULL,
                Estado VARCHAR(40) NOT NULL DEFAULT 'APLICADA',
                Fecha DATETIME,
                Admin_Usuario VARCHAR(80) DEFAULT '',
                Ventas_Generales DECIMAL(14,2) DEFAULT 0,
                Porcentaje DECIMAL(5,2) DEFAULT 30,
                Treinta_Porciento DECIMAL(14,2) DEFAULT 0,
                Provision_Objetivo DECIMAL(14,2) DEFAULT 0,
                Saldo_Pendiente_Anterior DECIMAL(14,2) DEFAULT 0,
                Objetivo_Total DECIMAL(14,2) DEFAULT 0,
                Efectivo_Disponible DECIMAL(14,2) DEFAULT 0,
                Efectivo_Provisionado DECIMAL(14,2) DEFAULT 0,
                Nuevo_Saldo_Pendiente DECIMAL(14,2) DEFAULT 0,
                Observacion TEXT NULL,
                UNIQUE KEY uq_prov_cierre_general (Cierre_General_Id),
                INDEX idx_prov_fecha (Fecha),
                INDEX idx_prov_estado (Estado)
            )
            """
        )

    def is_admin(usuario: str) -> bool:
        if not usuario:
            return False
        rows = query(
            "SELECT COUNT(*) AS c FROM admin WHERE LOWER(usuario)=LOWER(%s)",
            (usuario.strip(),),
        )
        return bool(rows and int(rows[0]["c"]) > 0)

    def require_admin(usuario: str) -> None:
        if not is_admin(usuario):
            raise HTTPException(403, "Solo administrador")

    def saldo_actual() -> float:
        ensure()
        rows = query("SELECT Saldo_Pendiente FROM provision_admin_estado WHERE Id=1")
        return _money(rows[0]["Saldo_Pendiente"] if rows else 0)

    def map_row(r: dict) -> dict:
        return {
            "id": int(r["Id"]),
            "cierre_general_id": int(r["Cierre_General_Id"]),
            "estado": r.get("Estado") or "APLICADA",
            "fecha": r.get("Fecha"),
            "admin_usuario": r.get("Admin_Usuario") or "",
            "ventas_generales": _money(r.get("Ventas_Generales")),
            "porcentaje": _money(r.get("Porcentaje")),
            "treinta_porciento": _money(r.get("Treinta_Porciento")),
            "provision_objetivo": _money(r.get("Provision_Objetivo")),
            "saldo_pendiente_anterior": _money(r.get("Saldo_Pendiente_Anterior")),
            "objetivo_total": _money(r.get("Objetivo_Total")),
            "efectivo_disponible": _money(r.get("Efectivo_Disponible")),
            "efectivo_provisionado": _money(r.get("Efectivo_Provisionado")),
            "nuevo_saldo_pendiente": _money(r.get("Nuevo_Saldo_Pendiente")),
            "observacion": r.get("Observacion") or "",
        }

    def por_cierre(cierre_general_id: int) -> Optional[dict]:
        if not has_table("provision_admin"):
            return None
        rows = query(
            "SELECT * FROM provision_admin WHERE Cierre_General_Id=%s LIMIT 1",
            (cierre_general_id,),
        )
        return map_row(rows[0]) if rows else None

    def resumen(usuario: str = Query(...)):
        ensure()
        require_admin(usuario)
        rows = query("SELECT * FROM provision_admin ORDER BY Id DESC LIMIT 50")
        return json_safe(
            {
                "saldo_pendiente": saldo_actual(),
                "porcentaje": 30.0,
                "multiplo_redondeo": int(MULTIPLO),
                "historial": [map_row(r) for r in rows],
            }
        )

    def detalle(cierre_general_id: int, usuario: str = Query(...)):
        ensure()
        require_admin(usuario)
        data = por_cierre(cierre_general_id)
        if not data:
            raise HTTPException(404, "Provisión no encontrada")
        return json_safe(data)

    # Helpers exportados para cierre_general.register
    app.state.provision_admin_helpers = {
        "ensure": ensure,
        "calcular": calcular,
        "saldo_actual": saldo_actual,
        "por_cierre": por_cierre,
        "map_row": map_row,
        "require_admin": require_admin,
        "is_admin": is_admin,
        "money": _money,
    }

    for path, fn, methods in (
        ("/provision-admin/", resumen, ["GET"]),
        ("/provision-admin/{cierre_general_id}/", detalle, ["GET"]),
    ):
        app.add_api_route(path, fn, methods=methods, name=f"pa_{fn.__name__}_{methods[0]}")
        app.add_api_route(
            "/api/v1" + path,
            fn,
            methods=methods,
            name=f"pa_{fn.__name__}_{methods[0]}_v1",
        )


def aplicar_provision_api(app: FastAPI, usuario: str, cierre_id: int, cierre_data: dict) -> dict:
    """Usada desde consolidar cierre general."""
    helpers = getattr(app.state, "provision_admin_helpers", None)
    if not helpers:
        # Lazy self-register path
        raise HTTPException(500, "Módulo provisión no inicializado")
    from main import execute, query

    helpers["ensure"]()
    helpers["require_admin"](usuario)
    existente = helpers["por_cierre"](cierre_id)
    if existente and existente.get("estado") == "APLICADA":
        return existente

    pendiente_ant = helpers["saldo_actual"]()
    calc = helpers["calcular"](
        cierre_data.get("total_ventas") or 0,
        pendiente_ant,
        cierre_data.get("total_efectivo") or 0,
    )
    if calc["efectivo_provisionado"] - calc["efectivo_disponible"] > 0.009:
        raise HTTPException(400, "No se puede provisionar más efectivo del disponible")

    ahora = datetime.now()
    if existente and existente.get("estado") == "ANULADA":
        execute(
            """
            UPDATE provision_admin SET
                Estado='APLICADA', Fecha=%s, Admin_Usuario=%s,
                Ventas_Generales=%s, Porcentaje=%s, Treinta_Porciento=%s,
                Provision_Objetivo=%s, Saldo_Pendiente_Anterior=%s, Objetivo_Total=%s,
                Efectivo_Disponible=%s, Efectivo_Provisionado=%s, Nuevo_Saldo_Pendiente=%s,
                Observacion=%s
            WHERE Cierre_General_Id=%s
            """,
            (
                ahora,
                (usuario or "")[:80],
                calc["ventas_generales"],
                calc["porcentaje"],
                calc["treinta_porciento"],
                calc["provision_objetivo"],
                calc["saldo_pendiente_anterior"],
                calc["objetivo_total"],
                calc["efectivo_disponible"],
                calc["efectivo_provisionado"],
                calc["nuevo_saldo_pendiente"],
                "Reaplicada al consolidar",
                cierre_id,
            ),
        )
        pid = existente["id"]
    else:
        pid = execute(
            """
            INSERT INTO provision_admin
                (Cierre_General_Id, Estado, Fecha, Admin_Usuario,
                 Ventas_Generales, Porcentaje, Treinta_Porciento, Provision_Objetivo,
                 Saldo_Pendiente_Anterior, Objetivo_Total, Efectivo_Disponible,
                 Efectivo_Provisionado, Nuevo_Saldo_Pendiente, Observacion)
            VALUES (%s,'APLICADA',%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """,
            (
                cierre_id,
                ahora,
                (usuario or "")[:80],
                calc["ventas_generales"],
                calc["porcentaje"],
                calc["treinta_porciento"],
                calc["provision_objetivo"],
                calc["saldo_pendiente_anterior"],
                calc["objetivo_total"],
                calc["efectivo_disponible"],
                calc["efectivo_provisionado"],
                calc["nuevo_saldo_pendiente"],
                "Calculada al consolidar cierre general",
            ),
        )
    execute(
        "UPDATE provision_admin_estado SET Saldo_Pendiente=%s, Fecha_Actualizacion=%s WHERE Id=1",
        (calc["nuevo_saldo_pendiente"], ahora),
    )
    out = dict(calc)
    out.update(
        {
            "id": int(pid or 0),
            "cierre_general_id": cierre_id,
            "estado": "APLICADA",
            "fecha": ahora,
            "admin_usuario": usuario,
        }
    )
    from provision_obligaciones import acreditar_provision_bolsillo_api

    acreditar_provision_bolsillo_api(app, usuario, cierre_id, out)
    return out


def revertir_provision_api(app: FastAPI, usuario: str, cierre_id: int) -> None:
    helpers = getattr(app.state, "provision_admin_helpers", None)
    if not helpers:
        return
    from main import execute, query
    from provision_obligaciones import revertir_provision_bolsillo_api

    revertir_provision_bolsillo_api(app, usuario, cierre_id)
    helpers["ensure"]()
    helpers["require_admin"](usuario)
    prov = helpers["por_cierre"](cierre_id)
    if not prov or prov.get("estado") != "APLICADA":
        return
    rows = query(
        "SELECT Id, Cierre_General_Id FROM provision_admin WHERE Estado='APLICADA' ORDER BY Id DESC LIMIT 1"
    )
    if not rows or int(rows[0]["Cierre_General_Id"]) != int(cierre_id):
        raise HTTPException(
            400,
            "No se puede anular: hay provisiones posteriores. Anule primero los cierres generales más recientes.",
        )
    execute(
        "UPDATE provision_admin SET Estado='ANULADA', Observacion=CONCAT(COALESCE(Observacion,''), ' | ANULADA') WHERE Id=%s",
        (prov["id"],),
    )
    execute(
        "UPDATE provision_admin_estado SET Saldo_Pendiente=%s, Fecha_Actualizacion=%s WHERE Id=1",
        (prov["saldo_pendiente_anterior"], datetime.now()),
    )
