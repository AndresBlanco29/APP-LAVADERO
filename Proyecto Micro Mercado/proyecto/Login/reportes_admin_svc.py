"""Reportes administrativos (Entrega 6). Solo administrador.

Regla: Datafono NO es bolsillo independiente; es medio de pago
destinado al bolsillo de proveedores.
TOTAL PROVEEDORES = EFECTIVO + NEQUI + DATAFONO (sin duplicar).
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Optional

from conexionLogin import FormularioLogin


def _round2(valor):
    try:
        return round(float(valor or 0), 2)
    except (TypeError, ValueError):
        return 0.0


def _es_admin(usuario):
    from cierre_general_svc import es_usuario_admin

    return es_usuario_admin(usuario)


def _ahora():
    try:
        import pytz

        return datetime.now(pytz.timezone("America/Bogota")).replace(tzinfo=None)
    except Exception:
        return datetime.now()


def resolver_periodo(preset="mes", desde=None, hasta=None):
    """Presets: hoy, ayer, semana, mes, año, personalizado."""
    ahora = _ahora()
    hoy0 = ahora.replace(hour=0, minute=0, second=0, microsecond=0)
    fin_dia = ahora.replace(hour=23, minute=59, second=59, microsecond=0)
    p = str(preset or "mes").strip().lower()

    if p == "personalizado" or (desde and hasta):
        d0 = _parse_dt(desde, hoy0)
        d1 = _parse_dt(hasta, fin_dia)
        if d1.hour == 0 and d1.minute == 0 and d1.second == 0:
            d1 = d1.replace(hour=23, minute=59, second=59)
        return {"preset": "personalizado", "desde": d0, "hasta": d1}

    if p == "hoy":
        return {"preset": "hoy", "desde": hoy0, "hasta": fin_dia}
    if p == "ayer":
        ay0 = hoy0 - timedelta(days=1)
        ay1 = hoy0 - timedelta(seconds=1)
        return {"preset": "ayer", "desde": ay0, "hasta": ay1}
    if p == "semana":
        return {"preset": "semana", "desde": hoy0 - timedelta(days=6), "hasta": fin_dia}
    if p == "año" or p == "anio":
        return {
            "preset": "año",
            "desde": hoy0.replace(month=1, day=1),
            "hasta": fin_dia,
        }
    # mes (default)
    return {
        "preset": "mes",
        "desde": hoy0.replace(day=1),
        "hasta": fin_dia,
    }


def _parse_dt(raw, default):
    if raw is None or raw == "":
        return default
    if isinstance(raw, datetime):
        return raw
    s = str(raw).strip().replace("T", " ")
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(s[:19] if len(s) >= 19 else s, fmt)
            return dt
        except ValueError:
            continue
    return default


def _norm_medio_report(metodo):
    """Mapea a Efectivo / Nequi / Datafono / Otros (UI). Tarjeta→Datafono."""
    t = str(metodo or "").strip().lower()
    if "efect" in t or t == "cash":
        return "Efectivo"
    if "nequi" in t or "trans" in t or "davi" in t or "bre" in t:
        return "Nequi"
    if "data" in t or "tarj" in t or "bold" in t:
        return "Datafono"
    if t in ("crédito", "credito", "fiado"):
        return "Otros"
    if not t:
        return "Otros"
    return "Otros"


def _medio_filtro_sql(medio_filtro):
    """Retorna lista de Metodo BD a incluir, o None = todos."""
    if not medio_filtro:
        return None
    m = _norm_medio_report(medio_filtro)
    if m == "Efectivo":
        return ["Efectivo"]
    if m == "Nequi":
        return ["Nequi", "Transferencia"]
    if m == "Datafono":
        return ["Tarjeta"]
    return None  # Otros: se filtra en app o con NOT IN


def dashboard_reportes_admin(
    usuario,
    preset="mes",
    desde=None,
    hasta=None,
    vendedor_id=None,
    vendedor=None,
    producto_id=None,
    categoria=None,
    proveedor=None,
    medio_pago=None,
):
    if not _es_admin(usuario):
        return {"error": "Solo administrador"}

    periodo = resolver_periodo(preset, desde, hasta)
    d0, d1 = periodo["desde"], periodo["hasta"]
    filtros = {
        "vendedor_id": vendedor_id,
        "vendedor": (vendedor or "").strip() or None,
        "producto_id": producto_id,
        "categoria": (categoria or "").strip() or None,
        "proveedor": (proveedor or "").strip() or None,
        "medio_pago": (medio_pago or "").strip() or None,
    }

    ventas = _reporte_ventas(d0, d1, filtros)
    rent = _reporte_rentabilidad(d0, d1, filtros)
    prov = _reporte_proveedores_pagos(d0, d1, filtros)
    bolsillos = _reporte_bolsillos()
    cierres = _reporte_cierres(d0, d1)
    movs = bolsillos.get("proveedores", {}).get("movimientos") or []
    valid = _validaciones(ventas, bolsillos)
    alertas = _alertas(ventas, bolsillos, valid)

    return {
        "periodo": {
            "preset": periodo["preset"],
            "desde": d0.strftime("%Y-%m-%d %H:%M:%S"),
            "hasta": d1.strftime("%Y-%m-%d %H:%M:%S"),
        },
        "filtros": filtros,
        "ventas": ventas,
        "rentabilidad": rent,
        "proveedores": prov,
        "bolsillos": bolsillos,
        "movimientos_proveedores": movs[:80],
        "cierres": cierres,
        "validaciones": valid,
        "alertas": alertas,
        "catalogos": _catalogos_filtros(),
        "nota_datafono": (
            "Datafono es un medio de pago destinado al bolsillo de proveedores. "
            "No es un bolsillo independiente ni forma parte del bolsillo administrativo."
        ),
    }


def _ventas_where(alias_v="v", filtros=None, d0=None, d1=None):
    filtros = filtros or {}
    clauses = [
        "COALESCE({a}.Anulada, 0) = 0".format(a=alias_v),
        "{a}.Fecha_Venta >= %s".format(a=alias_v),
        "{a}.Fecha_Venta <= %s".format(a=alias_v),
    ]
    params = [d0, d1]
    if filtros.get("vendedor_id"):
        clauses.append("{a}.Empleados_Id_Empleados = %s".format(a=alias_v))
        params.append(int(filtros["vendedor_id"]))
    return " AND ".join(clauses), params


def _reporte_ventas(d0, d1, filtros):
    cone = FormularioLogin.conexion_base_de_datos()
    cursor = cone.cursor()
    where, params = _ventas_where("v", filtros, d0, d1)

    # KPIs
    cursor.execute(
        """
        SELECT COALESCE(SUM(v.Total), 0), COUNT(*)
        FROM ventas v WHERE {w}
        """.format(
            w=where
        ),
        tuple(params),
    )
    row = cursor.fetchone() or (0, 0)
    total = _round2(row[0])
    tickets = int(row[1] or 0)
    ticket_prom = _round2(total / tickets) if tickets else 0.0

    # Serie diaria
    cursor.execute(
        """
        SELECT DATE(v.Fecha_Venta) AS dia, COALESCE(SUM(v.Total), 0), COUNT(*)
        FROM ventas v WHERE {w}
        GROUP BY DATE(v.Fecha_Venta)
        ORDER BY dia
        """.format(
            w=where
        ),
        tuple(params),
    )
    serie = [
        {
            "fecha": str(r[0]),
            "ventas": _round2(r[1]),
            "tickets": int(r[2] or 0),
        }
        for r in (cursor.fetchall() or [])
    ]

    # Por vendedor
    cursor.execute(
        """
        SELECT COALESCE(e.Nombres, CONCAT('Emp#', v.Empleados_Id_Empleados), 'Sin asignar') AS vend,
               COALESCE(SUM(v.Total), 0), COUNT(*)
        FROM ventas v
        LEFT JOIN empleados e ON e.Id_Empleados = v.Empleados_Id_Empleados
        WHERE {w}
        GROUP BY v.Empleados_Id_Empleados, e.Nombres
        ORDER BY 2 DESC
        LIMIT 30
        """.format(
            w=where
        ),
        tuple(params),
    )
    por_vendedor = [
        {"vendedor": r[0] or "Sin asignar", "ventas": _round2(r[1]), "tickets": int(r[2] or 0)}
        for r in (cursor.fetchall() or [])
    ]
    if filtros.get("vendedor"):
        q = filtros["vendedor"].lower()
        por_vendedor = [x for x in por_vendedor if q in (x["vendedor"] or "").lower()]

    # Por medio de pago (venta_pagos) — agregación en BD
    medios_sql = """
        SELECT vp.Metodo, COALESCE(SUM(vp.Monto), 0)
        FROM venta_pagos vp
        JOIN ventas v ON v.Id_Venta = vp.Venta_Id
        WHERE {w}
    """.format(
        w=where
    )
    mparams = list(params)
    medios_list = _medio_filtro_sql(filtros.get("medio_pago"))
    if medios_list:
        placeholders = ",".join(["%s"] * len(medios_list))
        medios_sql += " AND vp.Metodo IN ({})".format(placeholders)
        mparams.extend(medios_list)
    elif filtros.get("medio_pago") and _norm_medio_report(filtros["medio_pago"]) == "Otros":
        medios_sql += " AND vp.Metodo NOT IN ('Efectivo','Nequi','Transferencia','Tarjeta')"
    medios_sql += " GROUP BY vp.Metodo"
    cursor.execute(medios_sql, tuple(mparams))
    bruto = {}
    for metodo, monto in cursor.fetchall() or []:
        clave = _norm_medio_report(metodo)
        bruto[clave] = _round2(bruto.get(clave, 0) + _round2(monto))

    por_medio = {
        "efectivo": _round2(bruto.get("Efectivo", 0)),
        "nequi": _round2(bruto.get("Nequi", 0)),
        "datafono": _round2(bruto.get("Datafono", 0)),
        "otros": _round2(bruto.get("Otros", 0)),
        "detalle": [{"medio": k, "monto": v} for k, v in bruto.items()],
        "nota": "Datafono = medio de pago (Tarjeta), no bolsillo independiente",
    }

    # Productos / categorías con filtros opcionales
    prod_sql = """
        SELECT p.Id_Producto, p.Nombre, p.Categoria, COALESCE(p.Proveedor, '') AS Prov,
               COALESCE(SUM(vp.Cantidad), 0), COALESCE(SUM(vp.Subtotal), 0)
        FROM productos_has_ventas vp
        JOIN productos p ON p.Id_Producto = vp.Productos_Id_Producto
        JOIN ventas v ON v.Id_Venta = vp.Ventas_Id_Factura
        WHERE {w}
          AND COALESCE(vp.Devuelto, 0) = 0
    """.format(
        w=where
    )
    pparams = list(params)
    if filtros.get("producto_id"):
        prod_sql += " AND p.Id_Producto = %s"
        pparams.append(int(filtros["producto_id"]))
    if filtros.get("categoria"):
        prod_sql += " AND p.Categoria LIKE %s"
        pparams.append("%" + filtros["categoria"] + "%")
    if filtros.get("proveedor"):
        prod_sql += " AND COALESCE(p.Proveedor,'') LIKE %s"
        pparams.append("%" + filtros["proveedor"] + "%")
    prod_sql += " GROUP BY p.Id_Producto, p.Nombre, p.Categoria, p.Proveedor ORDER BY 6 DESC LIMIT 40"
    try:
        cursor.execute(prod_sql, tuple(pparams))
    except Exception:
        cursor.execute(prod_sql.replace("AND COALESCE(vp.Devuelto, 0) = 0", ""), tuple(pparams))
    por_producto = [
        {
            "id": int(r[0]),
            "nombre": r[1] or "",
            "categoria": r[2] or "",
            "proveedor": r[3] or "",
            "cantidad": _round2(r[4]),
            "ventas": _round2(r[5]),
        }
        for r in (cursor.fetchall() or [])
    ]

    cat_map = {}
    for p in por_producto:
        c = p["categoria"] or "Sin categoría"
        cat_map[c] = _round2(cat_map.get(c, 0) + p["ventas"])
    por_categoria = [
        {"categoria": k, "ventas": v} for k, v in sorted(cat_map.items(), key=lambda x: -x[1])
    ]

    # Productos sin movimiento (agregado liviano)
    sin_mov = []
    try:
        cursor.execute(
            """
            SELECT p.Id_Producto, p.Nombre, p.Cantidad
            FROM productos p
            WHERE p.Id_Producto NOT IN (
                SELECT DISTINCT vp.Productos_Id_Producto
                FROM productos_has_ventas vp
                JOIN ventas v ON v.Id_Venta = vp.Ventas_Id_Factura
                WHERE v.Fecha_Venta >= %s AND COALESCE(v.Anulada,0)=0
            )
            ORDER BY p.Nombre LIMIT 15
            """,
            (d0,),
        )
        sin_mov = [
            {"id": int(r[0]), "nombre": r[1] or "", "stock": _round2(r[2])}
            for r in (cursor.fetchall() or [])
        ]
    except Exception:
        pass

    cone.close()
    return {
        "total": total,
        "tickets": tickets,
        "ticket_promedio": ticket_prom,
        "serie_diaria": serie,
        "por_vendedor": por_vendedor,
        "por_medio": por_medio,
        "por_producto": por_producto,
        "por_categoria": por_categoria,
        "productos_sin_movimiento": sin_mov,
        "datafono_vendido": por_medio["datafono"],
        "datafono_es_bolsillo": False,
    }


def _reporte_rentabilidad(d0, d1, filtros):
    cone = FormularioLogin.conexion_base_de_datos()
    cursor = cone.cursor()
    where, params = _ventas_where("v", filtros, d0, d1)
    sql = """
        SELECT
            COALESCE(SUM(vp.Subtotal), 0),
            COALESCE(SUM(p.Precio_Compra * vp.Cantidad), 0),
            COALESCE(SUM(vp.Subtotal - (p.Precio_Compra * vp.Cantidad)), 0)
        FROM productos_has_ventas vp
        JOIN productos p ON p.Id_Producto = vp.Productos_Id_Producto
        JOIN ventas v ON v.Id_Venta = vp.Ventas_Id_Factura
        WHERE {w} AND COALESCE(vp.Devuelto, 0) = 0
    """.format(
        w=where
    )
    if filtros.get("categoria"):
        sql += " AND p.Categoria LIKE %s"
        params = list(params) + ["%" + filtros["categoria"] + "%"]
    if filtros.get("producto_id"):
        sql += " AND p.Id_Producto = %s"
        params = list(params) + [int(filtros["producto_id"])]
    try:
        cursor.execute(sql, tuple(params))
    except Exception:
        cursor.execute(sql.replace("AND COALESCE(vp.Devuelto, 0) = 0", ""), tuple(params))
    row = cursor.fetchone() or (0, 0, 0)
    cone.close()
    ventas = _round2(row[0])
    costo = _round2(row[1])
    utilidad = _round2(row[2])
    margen = _round2((utilidad / ventas) * 100) if ventas else 0.0
    return {
        "ventas": ventas,
        "costo": costo,
        "utilidad_bruta": utilidad,
        "margen_pct": margen,
        "utilidad_neta": utilidad,  # sin gastos operativos en este corte
        "nota": "La rentabilidad no altera ni duplica saldos de bolsillos",
    }


def _reporte_proveedores_pagos(d0, d1, filtros):
    """Pagos/obligaciones del bolsillo proveedores en el periodo."""
    out = {"pagos": [], "deudas": [], "resumen_medios": {"efectivo": 0, "nequi": 0, "datafono": 0, "total": 0}}
    try:
        from bolsillo_proveedores_svc import listar_movimientos_proveedores, obtener_saldos_proveedores

        movs = listar_movimientos_proveedores(200)
        for m in movs:
            fecha = str(m.get("fecha") or "")
            if fecha and (fecha < str(d0)[:10] or fecha[:19] > str(d1)):
                # filtro suave por string fecha
                try:
                    fd = datetime.strptime(fecha[:19], "%Y-%m-%d %H:%M:%S")
                    if fd < d0 or fd > d1:
                        continue
                except Exception:
                    pass
            if m.get("tipo") == "PAGO":
                item = {
                    "id": m.get("id"),
                    "fecha": fecha,
                    "proveedor": m.get("proveedor_nombre") or "",
                    "valor": m.get("monto"),
                    "medio": m.get("metodo") or "",
                    "efectivo": m.get("efectivo"),
                    "nequi": m.get("nequi"),
                    "datafono": m.get("datafono"),
                    "mixto": (m.get("metodo") or "") == "MIXTO"
                    or sum(
                        1
                        for x in (m.get("efectivo"), m.get("nequi"), m.get("datafono"))
                        if _round2(x) > 0
                    )
                    > 1,
                    "usuario": m.get("usuario"),
                    "referencia": m.get("referencia"),
                    "observacion": m.get("observacion"),
                    "bolsillo": "PROVEEDORES",
                }
                if filtros.get("medio_pago"):
                    want = _norm_medio_report(filtros["medio_pago"])
                    if want == "Efectivo" and _round2(item["efectivo"]) <= 0:
                        continue
                    if want == "Nequi" and _round2(item["nequi"]) <= 0:
                        continue
                    if want == "Datafono" and _round2(item["datafono"]) <= 0:
                        continue
                if filtros.get("proveedor") and filtros["proveedor"].lower() not in (
                    item["proveedor"] or ""
                ).lower():
                    continue
                out["pagos"].append(item)
                out["resumen_medios"]["efectivo"] = _round2(
                    out["resumen_medios"]["efectivo"] + _round2(item["efectivo"])
                )
                out["resumen_medios"]["nequi"] = _round2(
                    out["resumen_medios"]["nequi"] + _round2(item["nequi"])
                )
                out["resumen_medios"]["datafono"] = _round2(
                    out["resumen_medios"]["datafono"] + _round2(item["datafono"])
                )
            elif m.get("tipo") == "OBLIGACION":
                out["deudas"].append(
                    {
                        "id": m.get("id"),
                        "fecha": fecha,
                        "proveedor": m.get("proveedor_nombre"),
                        "valor": m.get("monto"),
                        "usuario": m.get("usuario"),
                        "observacion": m.get("observacion"),
                        "es_dinero": False,
                    }
                )
        out["resumen_medios"]["total"] = _round2(
            out["resumen_medios"]["efectivo"]
            + out["resumen_medios"]["nequi"]
            + out["resumen_medios"]["datafono"]
        )
        out["saldos_actuales"] = obtener_saldos_proveedores()
        out["nota"] = (
            "Pagos pueden ser efectivo, Nequi, Datafono o mixtos. "
            "Datafono aparece como medio, no como bolsillo."
        )
    except Exception as error:
        out["error"] = str(error)
    return out


def _reporte_bolsillos():
    """Solo bolsillos reales: Administrativo + Proveedores (con Datafono interno)."""
    admin = {
        "nombre": "Provisión administrativa",
        "objetivo": 0.0,
        "provisionado": 0.0,
        "pendiente": 0.0,
        "obligaciones": 0.0,
        "disponible": 0.0,
        "incluye_datafono": False,
        "nota": "Se financia solo con efectivo. Datafono no entra aquí.",
    }
    try:
        from provision_admin_svc import resumen_provision_admin
        from provision_obligaciones_svc import resumen_saldos

        # resumen_provision needs usuario - call estado directly
        cone = FormularioLogin.conexion_base_de_datos()
        cursor = cone.cursor()
        cursor.execute("SELECT Saldo_Pendiente FROM provision_admin_estado WHERE Id=1")
        admin["pendiente"] = _round2((cursor.fetchone() or [0])[0])
        cursor.execute(
            """
            SELECT COALESCE(SUM(Efectivo_Provisionado),0), COALESCE(SUM(Provision_Objetivo),0)
            FROM provision_admin WHERE Estado='APLICADA'
            """
        )
        row = cursor.fetchone() or (0, 0)
        admin["provisionado"] = _round2(row[0])
        admin["objetivo"] = _round2(row[1])
        cone.close()
        s = resumen_saldos()
        admin["disponible"] = s.get("disponible", 0)
        admin["obligaciones"] = s.get("dinero_comprometido", 0)
        admin["dinero_real"] = s.get("dinero_real", 0)
    except Exception as error:
        admin["error"] = str(error)

    proveedores = {
        "nombre": "Bolsillo de proveedores",
        "efectivo": 0.0,
        "nequi": 0.0,
        "datafono": 0.0,
        "total": 0.0,
        "formula": "TOTAL = EFECTIVO + NEQUI + DATAFONO",
        "datafono_es_desglose": True,
        "datafono_es_bolsillo_independiente": False,
        "movimientos": [],
    }
    try:
        from bolsillo_proveedores_svc import (
            listar_movimientos_proveedores,
            obtener_saldos_proveedores,
            resumen_bolsillo_proveedores,
        )

        s = obtener_saldos_proveedores()
        proveedores.update(
            {
                "efectivo": s["efectivo"],
                "nequi": s["nequi"],
                "datafono": s["datafono"],
                "total": s["total"],
                "composicion": [
                    {"medio": "Efectivo", "monto": s["efectivo"]},
                    {"medio": "Nequi", "monto": s["nequi"]},
                    {"medio": "Datafono", "monto": s["datafono"]},
                ],
                "integridad_ok": abs(s["total"] - (s["efectivo"] + s["nequi"] + s["datafono"]))
                < 0.02,
            }
        )
        movs = listar_movimientos_proveedores(60)
        for m in movs:
            proveedores["movimientos"].append(
                {
                    "fecha": m.get("fecha"),
                    "tipo": m.get("tipo"),
                    "valor": m.get("monto"),
                    "medio_pago": m.get("metodo"),
                    "efectivo": m.get("efectivo"),
                    "nequi": m.get("nequi"),
                    "datafono": m.get("datafono"),
                    "bolsillo_afectado": "PROVEEDORES",
                    "proveedor": m.get("proveedor_nombre"),
                    "usuario": m.get("usuario"),
                    "referencia": m.get("referencia"),
                    "observacion": m.get("observacion"),
                }
            )
    except Exception as error:
        proveedores["error"] = str(error)

    return {
        "administrativo": admin,
        "proveedores": proveedores,
        "bolsillos_reales": ["administrativo", "proveedores"],
        "excluidos": [
            {
                "nombre": "Datafono",
                "razon": "Es medio de pago dentro de proveedores, no bolsillo independiente",
            }
        ],
    }


def _reporte_cierres(d0, d1):
    diarios = []
    generales = []
    try:
        cone = FormularioLogin.conexion_base_de_datos()
        cursor = cone.cursor()
        cursor.execute(
            """
            SELECT Id, Cajero, Fecha, Total_Ventas, Efectivo, Nequi, Tarjeta, Transferencia,
                   Descuadre, COALESCE(Estado, '')
            FROM cierre_turno
            WHERE Fecha >= %s AND Fecha <= %s
            ORDER BY Id DESC
            LIMIT 80
            """,
            (d0, d1),
        )
        for r in cursor.fetchall() or []:
            ef = _round2(r[4])
            nq = _round2(_round2(r[5]) + _round2(r[7]))  # Nequi + Transferencia
            df = _round2(r[6])  # Tarjeta = Datafono
            diarios.append(
                {
                    "id": int(r[0]),
                    "vendedor": r[1] or "",
                    "fecha": str(r[2] or ""),
                    "ventas": _round2(r[3]),
                    "efectivo": ef,
                    "nequi": nq,
                    "datafono": df,
                    "diferencia": _round2(r[8]),
                    "estado": r[9] or "",
                    "trazabilidad": "venta → cierre diario → (CG) → proveedores",
                }
            )
        try:
            cursor.execute(
                """
                SELECT Id, Estado, Titulo, Fecha_Creacion, Fecha_Consolidacion, Admin_Usuario,
                       Total_Ventas, Total_Efectivo, Total_Nequi, Total_Datafono, Total_Diferencia
                FROM cierre_general
                WHERE COALESCE(Fecha_Consolidacion, Fecha_Creacion) >= %s
                  AND COALESCE(Fecha_Consolidacion, Fecha_Creacion) <= %s
                ORDER BY Id DESC
                LIMIT 40
                """,
                (d0, d1),
            )
            for r in cursor.fetchall() or []:
                generales.append(
                    {
                        "id": int(r[0]),
                        "estado": r[1] or "",
                        "titulo": r[2] or "",
                        "fecha_creacion": str(r[3] or ""),
                        "fecha_consolidacion": str(r[4] or ""),
                        "admin": r[5] or "",
                        "ventas": _round2(r[6]),
                        "efectivo": _round2(r[7]),
                        "nequi": _round2(r[8]),
                        "datafono": _round2(r[9]),
                        "diferencia": _round2(r[10]),
                    }
                )
        except Exception:
            pass
        # Correcciones en periodo
        correcciones = 0
        try:
            cursor.execute(
                """
                SELECT COUNT(*) FROM venta_pago_correcciones
                WHERE Fecha >= %s AND Fecha <= %s
                """,
                (d0, d1),
            )
            correcciones = int((cursor.fetchone() or [0])[0] or 0)
        except Exception:
            pass
        cone.close()
        return {
            "diarios": diarios,
            "generales": generales,
            "correcciones": correcciones,
        }
    except Exception as error:
        return {"diarios": [], "generales": [], "correcciones": 0, "error": str(error)}


def _validaciones(ventas, bolsillos):
    datafono_ventas = _round2((ventas.get("por_medio") or {}).get("datafono"))
    prov = bolsillos.get("proveedores") or {}
    datafono_prov = _round2(prov.get("datafono"))
    total = _round2(prov.get("total"))
    suma = _round2(
        _round2(prov.get("efectivo")) + _round2(prov.get("nequi")) + datafono_prov
    )
    return {
        "datafono_registrado_en_ventas": datafono_ventas,
        "datafono_en_detalle_proveedores": datafono_prov,
        "total_proveedores": total,
        "suma_medios_proveedores": suma,
        "total_proveedores_ok": abs(total - suma) < 0.02,
        "datafono_no_es_bolsillo_independiente": True,
        "datafono_no_en_administrativo": True,
        "sin_duplicacion_declarada": True,
        "nota": (
            "DATAFONO en ventas (periodo filtrado) es flujo; "
            "DATAFONO en proveedores es saldo acumulado del bolsillo (no deben igualarse necesariamente)."
        ),
    }


def _alertas(ventas, bolsillos, valid):
    alertas = []
    if not valid.get("total_proveedores_ok"):
        alertas.append(
            {
                "nivel": "danger",
                "mensaje": "Integridad proveedores: TOTAL ≠ EFECTIVO+NEQUI+DATAFONO",
            }
        )
    admin = bolsillos.get("administrativo") or {}
    if _round2(admin.get("disponible")) < 0:
        alertas.append({"nivel": "warning", "mensaje": "Disponible administrativo negativo"})
    if (ventas.get("tickets") or 0) == 0:
        alertas.append({"nivel": "info", "mensaje": "Sin ventas en el periodo seleccionado"})
    disp = _round2((bolsillos.get("proveedores") or {}).get("total"))
    if disp <= 0:
        alertas.append({"nivel": "info", "mensaje": "Bolsillo proveedores sin saldo"})
    return alertas


def _catalogos_filtros():
    out = {"vendedores": [], "categorias": [], "proveedores": [], "medios": ["Efectivo", "Nequi", "Datafono", "Otros"]}
    try:
        cone = FormularioLogin.conexion_base_de_datos()
        cursor = cone.cursor()
        cursor.execute(
            """
            SELECT DISTINCT e.Id_Empleados, e.Nombres
            FROM empleados e
            JOIN ventas v ON v.Empleados_Id_Empleados = e.Id_Empleados
            ORDER BY e.Nombres LIMIT 80
            """
        )
        out["vendedores"] = [
            {"id": int(r[0]), "nombre": r[1] or ""} for r in (cursor.fetchall() or [])
        ]
        cursor.execute(
            "SELECT DISTINCT Categoria FROM productos WHERE Categoria IS NOT NULL AND Categoria<>'' ORDER BY Categoria LIMIT 80"
        )
        out["categorias"] = [r[0] for r in (cursor.fetchall() or [])]
        cursor.execute(
            "SELECT DISTINCT Proveedor FROM productos WHERE Proveedor IS NOT NULL AND Proveedor<>'' ORDER BY Proveedor LIMIT 80"
        )
        out["proveedores"] = [r[0] for r in (cursor.fetchall() or [])]
        cone.close()
    except Exception:
        pass
    return out
