"""Bolsillos multi-medio, egresos por categoría y cierre mensual."""
from __future__ import annotations

from calendar import monthrange
from datetime import datetime, timedelta
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field


MEDIOS = ("Efectivo", "Nequi", "Tarjeta", "Transferencia")
CATEGORIAS = [
    {"id": "NOMINA", "nombre": "Nómina de empleados"},
    {"id": "REGENTE", "nombre": "Honorarios regente de farmacia"},
    {"id": "ARRIENDO", "nombre": "Arriendo / alquiler"},
    {"id": "SERVICIOS", "nombre": "Servicios públicos (luz, agua, internet)"},
    {"id": "OTROS", "nombre": "Mantenimiento / otros"},
    {"id": "PROVEEDOR", "nombre": "Pago a proveedor"},
]


class OrigenPago(BaseModel):
    metodo: str = "Efectivo"
    monto: float = Field(ge=0)


class BolsilloEgresoIn(BaseModel):
    monto: float = 0
    nota: str = ""
    metodo: str = "Efectivo"
    categoria: str = ""
    usuario: str = ""
    comprobante: str = ""
    origenes: list[OrigenPago] = []
    admin_id: Optional[int] = None


class CierreMensualIn(BaseModel):
    mes: int = Field(ge=1, le=12)
    anio: int = Field(ge=2020, le=2100)
    usuario: str = ""


def _money(value: Any) -> float:
    try:
        return round(float(value or 0), 2)
    except (TypeError, ValueError):
        return 0.0


def normalizar_metodo(raw: Any) -> str:
    texto = str(raw or "").strip().lower()
    if texto in {m.lower() for m in MEDIOS}:
        for medio in MEDIOS:
            if medio.lower() == texto:
                return medio
    if "efect" in texto or "caja" in texto:
        return "Efectivo"
    if "nequi" in texto or "davi" in texto:
        return "Nequi"
    if "tarj" in texto or "bold" in texto or "datafono" in texto or "datáfono" in texto:
        return "Tarjeta"
    if "trans" in texto or "banc" in texto:
        return "Transferencia"
    return "Efectivo"


def _add_col(execute, has_column, table: str, columna: str, defn: str) -> None:
    if has_column(table, columna):
        return
    try:
        execute(f"ALTER TABLE `{table}` ADD COLUMN `{columna}` {defn}")
    except Exception:
        pass


def ensure_finanzas(query, execute, has_column, has_table) -> None:
    if has_table("bolsillos"):
        _add_col(execute, has_column, "bolsillos", "Codigo", "VARCHAR(40) DEFAULT ''")
    if has_table("bolsillo_movimientos"):
        _add_col(execute, has_column, "bolsillo_movimientos", "Metodo", "VARCHAR(40) DEFAULT ''")
        _add_col(execute, has_column, "bolsillo_movimientos", "Categoria", "VARCHAR(40) DEFAULT ''")
        _add_col(execute, has_column, "bolsillo_movimientos", "Usuario", "VARCHAR(80) DEFAULT ''")
        _add_col(execute, has_column, "bolsillo_movimientos", "Comprobante", "VARCHAR(100) DEFAULT ''")
        _add_col(execute, has_column, "bolsillo_movimientos", "Cierre_Id", "INT NULL")
    execute(
        """
        CREATE TABLE IF NOT EXISTS cierre_diario_asignacion (
            Id INT AUTO_INCREMENT PRIMARY KEY,
            Cierre_Turno_Id INT NULL,
            Fecha DATETIME,
            Cajero VARCHAR(80) DEFAULT '',
            Pct_Proveedores DECIMAL(7,2) DEFAULT 0,
            Pct_Provisiones DECIMAL(7,2) DEFAULT 0,
            Pct_Utilidad DECIMAL(7,2) DEFAULT 0,
            Recaudo_Efectivo DECIMAL(12,2) DEFAULT 0,
            Recaudo_Nequi DECIMAL(12,2) DEFAULT 0,
            Recaudo_Tarjeta DECIMAL(12,2) DEFAULT 0,
            Recaudo_Transferencia DECIMAL(12,2) DEFAULT 0,
            Monto_Proveedores DECIMAL(12,2) DEFAULT 0,
            Monto_Provisiones DECIMAL(12,2) DEFAULT 0,
            Monto_Utilidad DECIMAL(12,2) DEFAULT 0,
            INDEX idx_cierre_asig_fecha (Fecha)
        )
        """
    )
    execute(
        """
        CREATE TABLE IF NOT EXISTS cierre_mensual (
            Id INT AUTO_INCREMENT PRIMARY KEY,
            Mes INT NOT NULL,
            Anio INT NOT NULL,
            Total_Ventas DECIMAL(12,2) DEFAULT 0,
            Costo_Ventas DECIMAL(12,2) DEFAULT 0,
            Utilidad_Bruta DECIMAL(12,2) DEFAULT 0,
            Total_Gastos_Operativos DECIMAL(12,2) DEFAULT 0,
            Utilidad_Neta DECIMAL(12,2) DEFAULT 0,
            Recaudo_Proveedores DECIMAL(12,2) DEFAULT 0,
            Recaudo_Provisiones DECIMAL(12,2) DEFAULT 0,
            Recaudo_Utilidad DECIMAL(12,2) DEFAULT 0,
            Fecha_Cierre DATETIME,
            Usuario VARCHAR(80) DEFAULT '',
            UNIQUE KEY uq_cierre_mes (Mes, Anio)
        )
        """
    )
    if not has_table("bolsillos"):
        return
    reglas = (
        ("PROVEEDORES", "%proveedor%"),
        ("UTILIDAD", "%utilidad%"),
        ("PROVISIONES", "%operativ%"),
        ("PROVISIONES", "%provisi%"),
        ("IMPUESTOS", "%impuesto%"),
    )
    for codigo, like in reglas:
        execute(
            """
            UPDATE bolsillos SET Codigo=%s
            WHERE (Codigo IS NULL OR Codigo='') AND LOWER(Nombre) LIKE %s
            """,
            (codigo, like),
        )
    existentes = {
        str(r.get("Codigo") or "").upper(): r
        for r in query("SELECT Id, Codigo FROM bolsillos")
        if r.get("Codigo")
    }
    faltantes = [
        ("PROVEEDORES", "Caja Proveedores", 65, "#3077FF", "truck", 1),
        ("UTILIDAD", "Utilidad neta", 18, "#22C55E", "crown", 2),
        ("PROVISIONES", "Provisiones / operación", 17, "#A084E8", "building", 3),
    ]
    for codigo, nombre, pct, color, icono, orden in faltantes:
        if codigo in existentes:
            continue
        execute(
            """
            INSERT INTO bolsillos
                (Nombre, Porcentaje, Color, Icono, Meta_Mensual, Activo, Orden, Codigo)
            VALUES (%s, %s, %s, %s, 0, 1, %s, %s)
            """,
            (nombre, pct, color, icono, orden, codigo),
        )


def recaudo_medios(query, has_table, col, inicio, fin=None) -> dict[str, float]:
    out = {m: 0.0 for m in MEDIOS}
    if not has_table("venta_pagos"):
        return out
    anulada = "AND COALESCE(v.Anulada, 0) = 0" if col("ventas", "Anulada") else ""
    sql = f"""
        SELECT vp.Metodo, COALESCE(SUM(vp.Monto), 0) AS t
        FROM venta_pagos vp
        JOIN ventas v ON v.Id_Venta = vp.Venta_Id
        WHERE v.Fecha_Venta >= %s {anulada}
    """
    params: list[Any] = [inicio]
    if fin:
        sql += " AND v.Fecha_Venta < %s"
        params.append(fin)
    sql += " GROUP BY vp.Metodo"
    try:
        rows = query(sql, tuple(params))
    except Exception:
        return out
    for row in rows:
        medio = normalizar_metodo(row.get("Metodo"))
        out[medio] = _money(out.get(medio, 0) + _money(row.get("t")))
    return out


def _movimientos(query, has_column, bolsillo_id: int, inicio, fin=None, tipo: str = "") -> list[dict]:
    sql = """
        SELECT * FROM bolsillo_movimientos
        WHERE Bolsillo_Id=%s AND Fecha >= %s
    """
    params: list[Any] = [bolsillo_id, inicio]
    if fin:
        sql += " AND Fecha < %s"
        params.append(fin)
    if tipo:
        sql += " AND Tipo=%s"
        params.append(tipo)
    try:
        return query(sql, tuple(params))
    except Exception:
        return []


def _sum_mov(rows: list[dict], metodo: str = "") -> float:
    total = 0.0
    for row in rows:
        if metodo and normalizar_metodo(row.get("Metodo") or "Efectivo") != metodo:
            continue
        total += _money(row.get("Monto"))
    return _money(total)


def snapshot_bolsillos(query, execute, has_column, has_table, col, inicio_dia, inicio_mes, ventas_rango) -> dict:
    ensure_finanzas(query, execute, has_column, has_table)
    hoy = ventas_rango(inicio_dia())
    mes = ventas_rango(inicio_mes())
    recaudo_hoy = recaudo_medios(query, has_table, col, inicio_dia())
    recaudo_mes = recaudo_medios(query, has_table, col, inicio_mes())
    total_hoy = _money(sum(recaudo_hoy.values())) or _money(hoy.get("venta"))
    total_mes = _money(sum(recaudo_mes.values())) or _money(mes.get("venta"))
    bolsas = query("SELECT * FROM bolsillos WHERE Activo=1 ORDER BY Orden, Id")
    out = []
    for b in bolsas:
        pct = _money(b.get("Porcentaje"))
        bid = int(b["Id"])
        mov_hoy = _movimientos(query, has_column, bid, inicio_dia())
        mov_mes = _movimientos(query, has_column, bid, inicio_mes())
        egresos_hoy = [m for m in mov_hoy if str(m.get("Tipo") or "").upper() == "EGRESO"]
        egresos_mes = [m for m in mov_mes if str(m.get("Tipo") or "").upper() == "EGRESO"]
        ingresos_hoy = [m for m in mov_hoy if str(m.get("Tipo") or "").upper() == "INGRESO"]
        ingresos_mes = [m for m in mov_mes if str(m.get("Tipo") or "").upper() == "INGRESO"]
        asignado_hoy = _sum_mov(ingresos_hoy) if ingresos_hoy else _money(total_hoy * pct / 100.0)
        asignado_mes = _sum_mov(ingresos_mes) if ingresos_mes else _money(total_mes * pct / 100.0)
        eh = _sum_mov(egresos_hoy)
        em = _sum_mov(egresos_mes)
        por_medio = []
        for medio in MEDIOS:
            asg_h = (
                _sum_mov(ingresos_hoy, medio)
                if ingresos_hoy
                else _money(recaudo_hoy.get(medio, 0) * pct / 100.0)
            )
            asg_m = (
                _sum_mov(ingresos_mes, medio)
                if ingresos_mes
                else _money(recaudo_mes.get(medio, 0) * pct / 100.0)
            )
            eg_h = _sum_mov(egresos_hoy, medio)
            eg_m = _sum_mov(egresos_mes, medio)
            por_medio.append(
                {
                    "metodo": medio,
                    "asignado_hoy": asg_h,
                    "asignado_mes": asg_m,
                    "egresos_hoy": eg_h,
                    "egresos_mes": eg_m,
                    "saldo_hoy": _money(asg_h - eg_h),
                    "saldo_mes": _money(asg_m - eg_m),
                }
            )
        out.append(
            {
                "id": bid,
                "nombre": b.get("Nombre"),
                "codigo": (b.get("Codigo") or "").upper(),
                "porcentaje": pct,
                "color": b.get("Color") or "#3077FF",
                "icono": b.get("Icono") or "wallet",
                "meta_mensual": _money(b.get("Meta_Mensual")),
                "asignado_hoy": asignado_hoy,
                "asignado_mes": asignado_mes,
                "egresos_hoy": eh,
                "egresos_mes": em,
                "saldo_hoy": _money(asignado_hoy - eh),
                "saldo_mes": _money(asignado_mes - em),
                "por_medio": por_medio,
            }
        )
    return {
        "venta_hoy": hoy.get("venta", 0),
        "venta_mes": mes.get("venta", 0),
        "utilidad_hoy": hoy.get("utilidad", 0),
        "utilidad_mes": mes.get("utilidad", 0),
        "recaudo_hoy": recaudo_hoy,
        "recaudo_mes": recaudo_mes,
        "medios": list(MEDIOS),
        "categorias": CATEGORIAS,
        "bolsillos": out,
    }


def registrar_egresos(query, execute, has_column, now_fn, bolsillo_id: int, body: BolsilloEgresoIn) -> None:
    found = query("SELECT Id, Codigo FROM bolsillos WHERE Id=%s", (bolsillo_id,))
    if not found:
        raise HTTPException(status_code=404, detail="Bolsillo no encontrado")
    origenes = [o for o in (body.origenes or []) if _money(o.monto) > 0]
    if not origenes and _money(body.monto) > 0:
        origenes = [OrigenPago(metodo=body.metodo, monto=body.monto)]
    if not origenes:
        raise HTTPException(status_code=400, detail="Indica un monto y un medio de pago")
    codigo = str(found[0].get("Codigo") or "").upper()
    categoria = (body.categoria or "").upper()
    if codigo == "PROVISIONES" and not categoria:
        categoria = "OTROS"
    if codigo == "PROVEEDORES":
        categoria = categoria or "PROVEEDOR"
    usuario = body.usuario or (f"admin:{body.admin_id}" if body.admin_id else "")
    for origen in origenes:
        execute(
            """
            INSERT INTO bolsillo_movimientos
                (Bolsillo_Id, Tipo, Monto, Nota, Fecha, Metodo, Categoria, Usuario, Comprobante)
            VALUES (%s, 'EGRESO', %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                bolsillo_id,
                _money(origen.monto),
                (body.nota or "")[:220],
                now_fn(),
                normalizar_metodo(origen.metodo),
                categoria[:40],
                usuario[:80],
                (body.comprobante or "")[:100],
            ),
        )


def _bolsillo_por_codigo(query, codigo: str) -> Optional[dict]:
    rows = query(
        "SELECT * FROM bolsillos WHERE UPPER(Codigo)=%s AND Activo=1 ORDER BY Id LIMIT 1",
        (codigo.upper(),),
    )
    return rows[0] if rows else None


def reporte_mensual(query, execute, has_column, has_table, col, ventas_rango, now_fn, anio: int, mes: int) -> dict:
    ensure_finanzas(query, execute, has_column, has_table)
    inicio = datetime(anio, mes, 1)
    ultimo = monthrange(anio, mes)[1]
    fin = inicio + timedelta(days=ultimo)
    if fin.tzinfo or getattr(inicio, "tzinfo", None):
        pass
    rango = ventas_rango(inicio, fin)
    venta = _money(rango.get("venta"))
    costo = _money(rango.get("costo"))
    if costo <= 0:
        costo = max(venta - _money(rango.get("utilidad")), 0)
    utilidad_bruta = _money(venta - costo)
    recaudo = recaudo_medios(query, has_table, col, inicio, fin)
    virtual = _money(recaudo["Nequi"] + recaudo["Tarjeta"] + recaudo["Transferencia"])

    bolsas = query("SELECT * FROM bolsillos WHERE Activo=1")
    ids = {str(b.get("Codigo") or "").upper(): int(b["Id"]) for b in bolsas if b.get("Codigo")}
    def egresos_codigo(codigo: str) -> float:
        bid = ids.get(codigo)
        if not bid:
            return 0.0
        mov = _movimientos(query, has_column, bid, inicio, fin, "EGRESO")
        return _sum_mov(mov)

    gastos = egresos_codigo("PROVISIONES")
    pagos_prov = egresos_codigo("PROVEEDORES")
    utilidad_neta = _money(utilidad_bruta - gastos)

    asignaciones = []
    if has_table("cierre_diario_asignacion"):
        try:
            asignaciones = query(
                """
                SELECT * FROM cierre_diario_asignacion
                WHERE Fecha >= %s AND Fecha < %s
                ORDER BY Fecha
                """,
                (inicio, fin),
            )
        except Exception:
            asignaciones = []

    pct_prov = next((_money(b.get("Porcentaje")) for b in bolsas if str(b.get("Codigo") or "").upper() == "PROVEEDORES"), 65)
    pct_provi = next((_money(b.get("Porcentaje")) for b in bolsas if str(b.get("Codigo") or "").upper() == "PROVISIONES"), 17)
    pct_util = next((_money(b.get("Porcentaje")) for b in bolsas if str(b.get("Codigo") or "").upper() == "UTILIDAD"), 18)
    if asignaciones:
        rec_prov = _money(sum(_money(a.get("Monto_Proveedores")) for a in asignaciones))
        rec_provi = _money(sum(_money(a.get("Monto_Provisiones")) for a in asignaciones))
        rec_util = _money(sum(_money(a.get("Monto_Utilidad")) for a in asignaciones))
    else:
        total_rec = _money(sum(recaudo.values())) or venta
        rec_prov = _money(total_rec * pct_prov / 100)
        rec_provi = _money(total_rec * pct_provi / 100)
        rec_util = _money(total_rec * pct_util / 100)

    dias = []
    for d in range(1, ultimo + 1):
        dia = datetime(anio, mes, d)
        sig = dia + timedelta(days=1)
        vr = ventas_rango(dia, sig)
        rm = recaudo_medios(query, has_table, col, dia, sig)
        asg = [
            a
            for a in asignaciones
            if str(a.get("Fecha") or "")[:10] == dia.strftime("%Y-%m-%d")
        ]
        if asg:
            ent_p = _money(sum(_money(a.get("Monto_Proveedores")) for a in asg))
            ent_r = _money(sum(_money(a.get("Monto_Provisiones")) for a in asg))
            ent_u = _money(sum(_money(a.get("Monto_Utilidad")) for a in asg))
        else:
            tot = _money(sum(rm.values())) or _money(vr.get("venta"))
            ent_p = _money(tot * pct_prov / 100)
            ent_r = _money(tot * pct_provi / 100)
            ent_u = _money(tot * pct_util / 100)
        eg_dia = 0.0
        bid_r = ids.get("PROVISIONES")
        if bid_r:
            eg_dia = _sum_mov(_movimientos(query, has_column, bid_r, dia, sig, "EGRESO"))
        dias.append(
            {
                "fecha": dia.strftime("%Y-%m-%d"),
                "venta": _money(vr.get("venta")),
                "efectivo": _money(rm.get("Efectivo")),
                "virtual": _money(rm.get("Nequi") + rm.get("Tarjeta") + rm.get("Transferencia")),
                "nequi": _money(rm.get("Nequi")),
                "tarjeta": _money(rm.get("Tarjeta")),
                "transferencia": _money(rm.get("Transferencia")),
                "entrada_proveedores": ent_p,
                "entrada_provisiones": ent_r,
                "entrada_utilidad": ent_u,
                "egresos": eg_dia,
            }
        )

    cerrado = None
    if has_table("cierre_mensual"):
        try:
            rows = query(
                "SELECT * FROM cierre_mensual WHERE Mes=%s AND Anio=%s LIMIT 1",
                (mes, anio),
            )
            if rows:
                cerrado = rows[0]
        except Exception:
            cerrado = None

    return {
        "mes": mes,
        "anio": anio,
        "cerrado": bool(cerrado),
        "pl": {
            "venta_total": venta,
            "cogs": costo,
            "utilidad_bruta": utilidad_bruta,
            "gastos_operativos": gastos,
            "utilidad_neta": utilidad_neta,
            "pagos_proveedores": pagos_prov,
        },
        "recaudo": {
            **recaudo,
            "virtual": virtual,
            "total": _money(sum(recaudo.values())),
        },
        "bolsillos": {
            "proveedores": {
                "entradas": rec_prov,
                "egresos": pagos_prov,
                "saldo": _money(rec_prov - pagos_prov),
            },
            "provisiones": {
                "entradas": rec_provi,
                "egresos": gastos,
                "saldo": _money(rec_provi - gastos),
            },
            "utilidad": {
                "entradas": rec_util,
                "egresos": egresos_codigo("UTILIDAD"),
                "saldo": _money(rec_util - egresos_codigo("UTILIDAD")),
            },
        },
        "dias": dias,
        "categorias": CATEGORIAS,
        "medios": list(MEDIOS),
    }


def persistir_cierre_mensual(query, execute, has_column, has_table, col, ventas_rango, now_fn, body: CierreMensualIn) -> dict:
    data = reporte_mensual(
        query, execute, has_column, has_table, col, ventas_rango, now_fn, body.anio, body.mes
    )
    pl = data["pl"]
    bol = data["bolsillos"]
    execute(
        """
        INSERT INTO cierre_mensual
            (Mes, Anio, Total_Ventas, Costo_Ventas, Utilidad_Bruta, Total_Gastos_Operativos,
             Utilidad_Neta, Recaudo_Proveedores, Recaudo_Provisiones, Recaudo_Utilidad,
             Fecha_Cierre, Usuario)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            Total_Ventas=VALUES(Total_Ventas),
            Costo_Ventas=VALUES(Costo_Ventas),
            Utilidad_Bruta=VALUES(Utilidad_Bruta),
            Total_Gastos_Operativos=VALUES(Total_Gastos_Operativos),
            Utilidad_Neta=VALUES(Utilidad_Neta),
            Recaudo_Proveedores=VALUES(Recaudo_Proveedores),
            Recaudo_Provisiones=VALUES(Recaudo_Provisiones),
            Recaudo_Utilidad=VALUES(Recaudo_Utilidad),
            Fecha_Cierre=VALUES(Fecha_Cierre),
            Usuario=VALUES(Usuario)
        """,
        (
            body.mes,
            body.anio,
            pl["venta_total"],
            pl["cogs"],
            pl["utilidad_bruta"],
            pl["gastos_operativos"],
            pl["utilidad_neta"],
            bol["proveedores"]["entradas"],
            bol["provisiones"]["entradas"],
            bol["utilidad"]["entradas"],
            now_fn(),
            (body.usuario or "")[:80],
        ),
    )
    data["cerrado"] = True
    return data


def attach_routes(app: FastAPI, ctx: dict) -> None:
    query = ctx["query"]
    execute = ctx["execute"]
    has_column = ctx["has_column"]
    has_table = ctx["has_table"]
    col = ctx["col"]
    inicio_dia = ctx["inicio_dia"]
    inicio_mes = ctx["inicio_mes"]
    now_bogota = ctx["now_bogota"]
    ventas_rango = ctx["ventas_rango"]
    snapshot_fn = ctx["snapshot_fn"]

    def pago_proveedor(body: BolsilloEgresoIn):
        """Entrega 4: pagos con validación por medio en bolsillo_proveedores (solo admin)."""
        from main import app as fastapi_app

        helpers = getattr(fastapi_app.state, "bolsillo_proveedores_helpers", None)
        if not helpers:
            raise HTTPException(500, "Módulo bolsillo proveedores no inicializado")
        helpers["ensure"]()
        usuario = (body.usuario or "").strip()
        if not usuario and body.admin_id:
            rows = query("SELECT usuario FROM admin WHERE Id=%s LIMIT 1", (int(body.admin_id),))
            usuario = (rows[0].get("usuario") if rows else "") or ""
        helpers["require_admin"](usuario)

        origenes = [{"metodo": o.metodo, "monto": o.monto} for o in (body.origenes or [])]
        total = _money(body.monto)
        if not origenes and total > 0:
            origenes = [{"metodo": body.metodo or "Efectivo", "monto": total}]
        if total <= 0:
            total = _money(sum(_money(o.get("monto")) for o in origenes))

        componentes = {"Efectivo": 0.0, "Nequi": 0.0, "Datafono": 0.0}
        for o in origenes:
            m = helpers["norm_metodo"](o.get("metodo"))
            if not m:
                raise HTTPException(400, f"Medio inválido: {o.get('metodo')}")
            componentes[m] = _money(componentes[m] + _money(o.get("monto")))
        suma = _money(sum(componentes.values()))
        if abs(suma - total) > 0.02:
            raise HTTPException(400, f"La suma de medios ({suma}) debe ser igual al total ({total})")

        s = helpers["saldos"]()
        for m in ("Efectivo", "Nequi", "Datafono"):
            if componentes[m] - s[m.lower()] > 0.009:
                raise HTTPException(
                    400,
                    f"Saldo insuficiente en {m}: disponible {s[m.lower()]}, solicitado {componentes[m]}",
                )

        ahora = now_bogota()
        ant_ef, ant_nq, ant_dt = s["efectivo"], s["nequi"], s["datafono"]
        nuevo_ef = _money(ant_ef - componentes["Efectivo"])
        nuevo_nq = _money(ant_nq - componentes["Nequi"])
        nuevo_dt = _money(ant_dt - componentes["Datafono"])
        helpers["set_saldos"](nuevo_ef, nuevo_nq, nuevo_dt, ahora)
        metodo_lbl = (
            "MIXTO"
            if sum(1 for v in componentes.values() if v > 0) > 1
            else next((k for k, v in componentes.items() if v > 0), "Efectivo")
        )
        execute(
            """
            INSERT INTO bolsillo_proveedores_mov
                (Tipo, Metodo, Monto, Efectivo, Nequi, Datafono,
                 Saldo_Ef_Ant, Saldo_Neq_Ant, Saldo_Dat_Ant,
                 Saldo_Ef_Nuevo, Saldo_Neq_Nuevo, Saldo_Dat_Nuevo,
                 Proveedor_Nombre, Referencia, Observacion, Usuario, Estado, Fecha)
            VALUES
                ('PAGO', %s, %s, %s, %s, %s,
                 %s, %s, %s, %s, %s, %s,
                 %s, %s, %s, %s, 'ACTIVO', %s)
            """,
            (
                metodo_lbl,
                total,
                componentes["Efectivo"],
                componentes["Nequi"],
                componentes["Datafono"],
                ant_ef,
                ant_nq,
                ant_dt,
                nuevo_ef,
                nuevo_nq,
                nuevo_dt,
                (body.nota or "Proveedor")[:160],
                (body.comprobante or "")[:120],
                (body.nota or "")[:2000],
                usuario[:80],
                ahora,
            ),
        )
        return snapshot_fn()

    def cierre_mensual_get(mes: int = Query(0), anio: int = Query(0)):
        ahora = now_bogota()
        mes = mes or ahora.month
        anio = anio or ahora.year
        return reporte_mensual(
            query, execute, has_column, has_table, col, ventas_rango, now_bogota, anio, mes
        )

    def cierre_mensual_post(body: CierreMensualIn):
        # Entrega 7: solo admin puede persistir cierre mensual
        usuario = (body.usuario or "").strip()
        if not usuario:
            raise HTTPException(403, "Solo administrador")
        rows = query(
            "SELECT COUNT(*) AS c FROM admin WHERE LOWER(usuario)=LOWER(%s)",
            (usuario,),
        )
        if not (rows and int(rows[0]["c"]) > 0):
            raise HTTPException(403, "Solo administrador")
        return persistir_cierre_mensual(
            query, execute, has_column, has_table, col, ventas_rango, now_bogota, body
        )

    rutas = [
        ("/bolsillos/pago-proveedor/", pago_proveedor, ["POST"]),
        ("/comando/cierre-mensual/", cierre_mensual_get, ["GET"]),
        ("/comando/cierre-mensual/", cierre_mensual_post, ["POST"]),
    ]
    for path, fn, methods in rutas:
        app.add_api_route(path, fn, methods=methods, name=f"fin_{fn.__name__}_{methods[0]}")
        app.add_api_route(
            "/api/v1" + path,
            fn,
            methods=methods,
            name=f"fin_{fn.__name__}_{methods[0]}_v1",
        )
