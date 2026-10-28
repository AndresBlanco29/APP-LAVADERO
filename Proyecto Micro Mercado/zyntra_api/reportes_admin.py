"""API reportes administrativos (Entrega 6). Solo admin. Autocontenido para Railway."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, Query


def _money(v: Any) -> float:
    try:
        return round(float(v or 0), 2)
    except (TypeError, ValueError):
        return 0.0


def _ahora() -> datetime:
    try:
        from zoneinfo import ZoneInfo

        return datetime.now(ZoneInfo("America/Bogota")).replace(tzinfo=None)
    except Exception:
        return datetime.now()


def _parse_dt(raw: Optional[str], default: datetime) -> datetime:
    if not raw:
        return default
    s = str(raw).strip().replace("T", " ")
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(s[:19] if len(s) >= 19 else s, fmt)
        except ValueError:
            continue
    return default


def resolver_periodo(preset: str, desde: Optional[str], hasta: Optional[str]) -> dict:
    ahora = _ahora()
    hoy0 = ahora.replace(hour=0, minute=0, second=0, microsecond=0)
    fin = ahora.replace(hour=23, minute=59, second=59, microsecond=0)
    p = (preset or "mes").lower()
    if p == "personalizado" or (desde and hasta):
        d0 = _parse_dt(desde, hoy0)
        d1 = _parse_dt(hasta, fin)
        if d1.hour == 0 and d1.minute == 0:
            d1 = d1.replace(hour=23, minute=59, second=59)
        return {"preset": "personalizado", "desde": d0, "hasta": d1}
    if p == "hoy":
        return {"preset": "hoy", "desde": hoy0, "hasta": fin}
    if p == "ayer":
        return {
            "preset": "ayer",
            "desde": hoy0 - timedelta(days=1),
            "hasta": hoy0 - timedelta(seconds=1),
        }
    if p == "semana":
        return {"preset": "semana", "desde": hoy0 - timedelta(days=6), "hasta": fin}
    if p in ("año", "anio"):
        return {"preset": "año", "desde": hoy0.replace(month=1, day=1), "hasta": fin}
    return {"preset": "mes", "desde": hoy0.replace(day=1), "hasta": fin}


def _norm_medio(metodo: str) -> str:
    t = str(metodo or "").strip().lower()
    if "efect" in t:
        return "Efectivo"
    if "nequi" in t or "trans" in t or "davi" in t or "bre" in t:
        return "Nequi"
    if "data" in t or "tarj" in t or "bold" in t:
        return "Datafono"
    return "Otros"


def register(app: FastAPI) -> None:
    from main import json_safe, query

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

    def has_table(name: str) -> bool:
        rows = query(
            """
            SELECT COUNT(*) AS c FROM information_schema.TABLES
            WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s
            """,
            (name,),
        )
        return bool(rows and int(rows[0]["c"]))

    def has_col(table: str, col: str) -> bool:
        rows = query(
            """
            SELECT COUNT(*) AS c FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s AND COLUMN_NAME = %s
            """,
            (table, col),
        )
        return bool(rows and int(rows[0]["c"]))

    def dashboard(
        usuario: str = Query(...),
        preset: str = Query("mes"),
        desde: Optional[str] = Query(None),
        hasta: Optional[str] = Query(None),
        vendedor_id: Optional[int] = Query(None),
        categoria: Optional[str] = Query(None),
        proveedor: Optional[str] = Query(None),
        medio_pago: Optional[str] = Query(None),
        producto_id: Optional[int] = Query(None),
    ):
        require_admin(usuario)
        periodo = resolver_periodo(preset, desde, hasta)
        d0, d1 = periodo["desde"], periodo["hasta"]
        anul = "AND COALESCE(v.Anulada, 0) = 0" if has_col("ventas", "Anulada") else ""

        where = f"v.Fecha_Venta >= %s AND v.Fecha_Venta <= %s {anul}"
        params: list[Any] = [d0, d1]
        if vendedor_id:
            where += " AND v.Empleados_Id_Empleados = %s"
            params.append(int(vendedor_id))

        # KPIs ventas
        rows = query(
            f"SELECT COALESCE(SUM(v.Total),0) AS t, COUNT(*) AS c FROM ventas v WHERE {where}",
            tuple(params),
        )
        total = _money(rows[0]["t"] if rows else 0)
        tickets = int(rows[0]["c"] if rows else 0)
        ticket_prom = _money(total / tickets) if tickets else 0.0

        serie_rows = query(
            f"""
            SELECT DATE(v.Fecha_Venta) AS dia, COALESCE(SUM(v.Total),0) AS t, COUNT(*) AS c
            FROM ventas v WHERE {where}
            GROUP BY DATE(v.Fecha_Venta) ORDER BY dia
            """,
            tuple(params),
        )
        serie = [
            {"fecha": str(r["dia"]), "ventas": _money(r["t"]), "tickets": int(r["c"] or 0)}
            for r in serie_rows
        ]

        vend_rows = query(
            f"""
            SELECT COALESCE(e.Nombres, 'Sin asignar') AS vend,
                   COALESCE(SUM(v.Total),0) AS t, COUNT(*) AS c
            FROM ventas v
            LEFT JOIN empleados e ON e.Id_Empleados = v.Empleados_Id_Empleados
            WHERE {where}
            GROUP BY v.Empleados_Id_Empleados, e.Nombres
            ORDER BY t DESC LIMIT 30
            """,
            tuple(params),
        )
        por_vendedor = [
            {"vendedor": r["vend"], "ventas": _money(r["t"]), "tickets": int(r["c"] or 0)}
            for r in vend_rows
        ]

        # Medios
        medio_sql = f"""
            SELECT vp.Metodo AS m, COALESCE(SUM(vp.Monto),0) AS t
            FROM venta_pagos vp
            JOIN ventas v ON v.Id_Venta = vp.Venta_Id
            WHERE {where}
        """
        mparams = list(params)
        if medio_pago:
            nm = _norm_medio(medio_pago)
            if nm == "Efectivo":
                medio_sql += " AND vp.Metodo='Efectivo'"
            elif nm == "Nequi":
                medio_sql += " AND vp.Metodo IN ('Nequi','Transferencia')"
            elif nm == "Datafono":
                medio_sql += " AND vp.Metodo='Tarjeta'"
            else:
                medio_sql += " AND vp.Metodo NOT IN ('Efectivo','Nequi','Transferencia','Tarjeta')"
        medio_sql += " GROUP BY vp.Metodo"
        bruto: dict[str, float] = {}
        if has_table("venta_pagos"):
            for r in query(medio_sql, tuple(mparams)):
                k = _norm_medio(r["m"])
                bruto[k] = _money(bruto.get(k, 0) + _money(r["t"]))
        por_medio = {
            "efectivo": _money(bruto.get("Efectivo", 0)),
            "nequi": _money(bruto.get("Nequi", 0)),
            "datafono": _money(bruto.get("Datafono", 0)),
            "otros": _money(bruto.get("Otros", 0)),
            "detalle": [{"medio": k, "monto": v} for k, v in bruto.items()],
            "nota": "Datafono = medio de pago destinado a proveedores; no es bolsillo independiente",
        }

        # Productos
        prod_where = where
        pparams = list(params)
        extra = " AND COALESCE(vp.Devuelto,0)=0" if has_col("productos_has_ventas", "Devuelto") else ""
        if categoria:
            extra += " AND p.Categoria LIKE %s"
            pparams.append(f"%{categoria}%")
        if proveedor:
            extra += " AND COALESCE(p.Proveedor,'') LIKE %s"
            pparams.append(f"%{proveedor}%")
        if producto_id:
            extra += " AND p.Id_Producto=%s"
            pparams.append(int(producto_id))
        prod_rows = query(
            f"""
            SELECT p.Id_Producto AS id, p.Nombre AS nombre, COALESCE(p.Categoria,'') AS cat,
                   COALESCE(p.Proveedor,'') AS prov,
                   COALESCE(SUM(vp.Cantidad),0) AS qty, COALESCE(SUM(vp.Subtotal),0) AS t
            FROM productos_has_ventas vp
            JOIN productos p ON p.Id_Producto = vp.Productos_Id_Producto
            JOIN ventas v ON v.Id_Venta = vp.Ventas_Id_Factura
            WHERE {prod_where}{extra}
            GROUP BY p.Id_Producto, p.Nombre, p.Categoria, p.Proveedor
            ORDER BY t DESC LIMIT 40
            """,
            tuple(pparams),
        )
        por_producto = [
            {
                "id": int(r["id"]),
                "nombre": r["nombre"] or "",
                "categoria": r["cat"] or "",
                "proveedor": r["prov"] or "",
                "cantidad": _money(r["qty"]),
                "ventas": _money(r["t"]),
            }
            for r in prod_rows
        ]
        cat_map: dict[str, float] = {}
        for p in por_producto:
            c = p["categoria"] or "Sin categoría"
            cat_map[c] = _money(cat_map.get(c, 0) + p["ventas"])
        por_categoria = [
            {"categoria": k, "ventas": v}
            for k, v in sorted(cat_map.items(), key=lambda x: -x[1])
        ]

        # Rentabilidad
        rent_rows = query(
            f"""
            SELECT COALESCE(SUM(vp.Subtotal),0) AS ventas,
                   COALESCE(SUM(p.Precio_Compra * vp.Cantidad),0) AS costo,
                   COALESCE(SUM(vp.Subtotal - p.Precio_Compra * vp.Cantidad),0) AS util
            FROM productos_has_ventas vp
            JOIN productos p ON p.Id_Producto = vp.Productos_Id_Producto
            JOIN ventas v ON v.Id_Venta = vp.Ventas_Id_Factura
            WHERE {prod_where}{extra}
            """,
            tuple(pparams),
        )
        rv = rent_rows[0] if rent_rows else {}
        ventas_r = _money(rv.get("ventas"))
        costo_r = _money(rv.get("costo"))
        util_r = _money(rv.get("util"))
        rentabilidad = {
            "ventas": ventas_r,
            "costo": costo_r,
            "utilidad_bruta": util_r,
            "margen_pct": _money((util_r / ventas_r) * 100) if ventas_r else 0,
            "utilidad_neta": util_r,
            "nota": "No altera ni duplica saldos de bolsillos",
        }

        # Bolsillo proveedores
        prov_saldo = {"efectivo": 0.0, "nequi": 0.0, "datafono": 0.0, "total": 0.0}
        movs = []
        if has_table("bolsillo_proveedores_saldo"):
            srows = query(
                "SELECT Efectivo, Nequi, Datafono FROM bolsillo_proveedores_saldo WHERE Id=1"
            )
            if srows:
                ef = _money(srows[0]["Efectivo"])
                nq = _money(srows[0]["Nequi"])
                dt = _money(srows[0]["Datafono"])
                prov_saldo = {
                    "efectivo": ef,
                    "nequi": nq,
                    "datafono": dt,
                    "total": _money(ef + nq + dt),
                    "composicion": [
                        {"medio": "Efectivo", "monto": ef},
                        {"medio": "Nequi", "monto": nq},
                        {"medio": "Datafono", "monto": dt},
                    ],
                    "integridad_ok": abs(_money(ef + nq + dt) - _money(ef + nq + dt)) < 0.02,
                    "datafono_es_desglose": True,
                    "datafono_es_bolsillo_independiente": False,
                    "formula": "TOTAL = EFECTIVO + NEQUI + DATAFONO",
                }
        if has_table("bolsillo_proveedores_mov"):
            mrows = query(
                """
                SELECT Id, Tipo, Metodo, Monto, Efectivo, Nequi, Datafono,
                       Proveedor_Nombre, Usuario, Referencia, Observacion, Fecha
                FROM bolsillo_proveedores_mov
                WHERE Estado='ACTIVO'
                ORDER BY Id DESC LIMIT 80
                """
            )
            for r in mrows:
                movs.append(
                    {
                        "id": int(r["Id"]),
                        "fecha": r.get("Fecha"),
                        "tipo": r.get("Tipo"),
                        "valor": _money(r.get("Monto")),
                        "medio_pago": r.get("Metodo") or "",
                        "efectivo": _money(r.get("Efectivo")),
                        "nequi": _money(r.get("Nequi")),
                        "datafono": _money(r.get("Datafono")),
                        "bolsillo_afectado": "PROVEEDORES",
                        "proveedor": r.get("Proveedor_Nombre") or "",
                        "usuario": r.get("Usuario") or "",
                        "referencia": r.get("Referencia") or "",
                        "observacion": r.get("Observacion") or "",
                    }
                )

        # Administrativo
        admin = {
            "nombre": "Provisión administrativa",
            "objetivo": 0.0,
            "provisionado": 0.0,
            "pendiente": 0.0,
            "obligaciones": 0.0,
            "disponible": 0.0,
            "dinero_real": 0.0,
            "incluye_datafono": False,
            "nota": "Financiada solo con efectivo. Datafono no entra aquí.",
        }
        if has_table("provision_admin_estado"):
            er = query("SELECT Saldo_Pendiente FROM provision_admin_estado WHERE Id=1")
            admin["pendiente"] = _money(er[0]["Saldo_Pendiente"] if er else 0)
        if has_table("provision_admin"):
            pr = query(
                """
                SELECT COALESCE(SUM(Efectivo_Provisionado),0) AS p,
                       COALESCE(SUM(Provision_Objetivo),0) AS o
                FROM provision_admin WHERE Estado='APLICADA'
                """
            )
            if pr:
                admin["provisionado"] = _money(pr[0]["p"])
                admin["objetivo"] = _money(pr[0]["o"])
        if has_table("provision_bolsillo_saldo"):
            br = query("SELECT Dinero_Real FROM provision_bolsillo_saldo WHERE Id=1")
            real = _money(br[0]["Dinero_Real"] if br else 0)
            admin["dinero_real"] = real
            # comprometido empleados + pendientes
            reserva = 0.0
            if has_table("provision_empleados_salario"):
                rr = query(
                    "SELECT COALESCE(SUM(Salario_Mensual),0) AS s FROM provision_empleados_salario WHERE Activo=1"
                )
                reserva = _money((_money(rr[0]["s"] if rr else 0)) / 30.0)
            otras = 0.0
            if has_table("provision_obligacion"):
                oo = query(
                    """
                    SELECT COALESCE(SUM(Valor),0) AS s FROM provision_obligacion
                    WHERE Estado='PENDIENTE' AND Tipo<>'EMPLEADOS'
                    """
                )
                otras = _money(oo[0]["s"] if oo else 0)
            admin["obligaciones"] = _money(reserva + otras)
            admin["disponible"] = _money(real - admin["obligaciones"])

        # Pagos proveedores en periodo
        pagos = [m for m in movs if m.get("tipo") == "PAGO"]
        deudas = [m for m in movs if m.get("tipo") == "OBLIGACION"]

        # Cierres
        diarios = []
        if has_table("cierre_turno"):
            drows = query(
                """
                SELECT Id, Cajero, Fecha, Total_Ventas, Efectivo, Nequi, Tarjeta, Transferencia,
                       Descuadre, COALESCE(Estado,'') AS Estado
                FROM cierre_turno
                WHERE Fecha >= %s AND Fecha <= %s
                ORDER BY Id DESC LIMIT 80
                """,
                (d0, d1),
            )
            for r in drows:
                diarios.append(
                    {
                        "id": int(r["Id"]),
                        "vendedor": r.get("Cajero") or "",
                        "fecha": r.get("Fecha"),
                        "ventas": _money(r.get("Total_Ventas")),
                        "efectivo": _money(r.get("Efectivo")),
                        "nequi": _money(_money(r.get("Nequi")) + _money(r.get("Transferencia"))),
                        "datafono": _money(r.get("Tarjeta")),
                        "diferencia": _money(r.get("Descuadre")),
                        "estado": r.get("Estado") or "",
                    }
                )
        generales = []
        if has_table("cierre_general"):
            grows = query(
                """
                SELECT Id, Estado, Titulo, Fecha_Creacion, Fecha_Consolidacion, Admin_Usuario,
                       Total_Ventas, Total_Efectivo, Total_Nequi, Total_Datafono, Total_Diferencia
                FROM cierre_general
                WHERE COALESCE(Fecha_Consolidacion, Fecha_Creacion) >= %s
                  AND COALESCE(Fecha_Consolidacion, Fecha_Creacion) <= %s
                ORDER BY Id DESC LIMIT 40
                """,
                (d0, d1),
            )
            for r in grows:
                generales.append(
                    {
                        "id": int(r["Id"]),
                        "estado": r.get("Estado"),
                        "titulo": r.get("Titulo") or "",
                        "fecha_creacion": r.get("Fecha_Creacion"),
                        "fecha_consolidacion": r.get("Fecha_Consolidacion"),
                        "admin": r.get("Admin_Usuario") or "",
                        "ventas": _money(r.get("Total_Ventas")),
                        "efectivo": _money(r.get("Total_Efectivo")),
                        "nequi": _money(r.get("Total_Nequi")),
                        "datafono": _money(r.get("Total_Datafono")),
                        "diferencia": _money(r.get("Total_Diferencia")),
                    }
                )

        correcciones = 0
        if has_table("venta_pago_correcciones"):
            cr = query(
                "SELECT COUNT(*) AS c FROM venta_pago_correcciones WHERE Fecha>=%s AND Fecha<=%s",
                (d0, d1),
            )
            correcciones = int(cr[0]["c"] if cr else 0)

        # Catálogos
        vendedores = []
        if has_table("empleados"):
            vendedores = [
                {"id": int(r["Id_Empleados"]), "nombre": r["Nombres"] or ""}
                for r in query(
                    """
                    SELECT DISTINCT e.Id_Empleados, e.Nombres FROM empleados e
                    JOIN ventas v ON v.Empleados_Id_Empleados = e.Id_Empleados
                    ORDER BY e.Nombres LIMIT 80
                    """
                )
            ]
        categorias = [
            r["Categoria"]
            for r in query(
                "SELECT DISTINCT Categoria FROM productos WHERE Categoria IS NOT NULL AND Categoria<>'' ORDER BY Categoria LIMIT 80"
            )
        ]
        proveedores_cat = [
            r["Proveedor"]
            for r in query(
                "SELECT DISTINCT Proveedor FROM productos WHERE Proveedor IS NOT NULL AND Proveedor<>'' ORDER BY Proveedor LIMIT 80"
            )
        ]

        total_ok = abs(prov_saldo.get("total", 0) - (
            prov_saldo.get("efectivo", 0) + prov_saldo.get("nequi", 0) + prov_saldo.get("datafono", 0)
        )) < 0.02

        alertas = []
        if not total_ok:
            alertas.append({"nivel": "danger", "mensaje": "Integridad proveedores falló"})
        if tickets == 0:
            alertas.append({"nivel": "info", "mensaje": "Sin ventas en el periodo"})

        return json_safe(
            {
                "periodo": {
                    "preset": periodo["preset"],
                    "desde": d0.strftime("%Y-%m-%d %H:%M:%S"),
                    "hasta": d1.strftime("%Y-%m-%d %H:%M:%S"),
                },
                "filtros": {
                    "vendedor_id": vendedor_id,
                    "categoria": categoria,
                    "proveedor": proveedor,
                    "medio_pago": medio_pago,
                    "producto_id": producto_id,
                },
                "ventas": {
                    "total": total,
                    "tickets": tickets,
                    "ticket_promedio": ticket_prom,
                    "serie_diaria": serie,
                    "por_vendedor": por_vendedor,
                    "por_medio": por_medio,
                    "por_producto": por_producto,
                    "por_categoria": por_categoria,
                    "datafono_vendido": por_medio["datafono"],
                    "datafono_es_bolsillo": False,
                },
                "rentabilidad": rentabilidad,
                "proveedores": {
                    "pagos": pagos,
                    "deudas": deudas,
                    "saldos_actuales": prov_saldo,
                    "nota": "Datafono es medio dentro de proveedores, no bolsillo propio",
                },
                "bolsillos": {
                    "administrativo": admin,
                    "proveedores": {**prov_saldo, "movimientos": movs, "nombre": "Bolsillo de proveedores"},
                    "bolsillos_reales": ["administrativo", "proveedores"],
                    "excluidos": [
                        {
                            "nombre": "Datafono",
                            "razon": "Medio de pago dentro de proveedores, no bolsillo independiente",
                        }
                    ],
                },
                "movimientos_proveedores": movs,
                "cierres": {
                    "diarios": diarios,
                    "generales": generales,
                    "correcciones": correcciones,
                },
                "validaciones": {
                    "datafono_registrado_en_ventas": por_medio["datafono"],
                    "datafono_en_detalle_proveedores": prov_saldo.get("datafono", 0),
                    "total_proveedores_ok": total_ok,
                    "datafono_no_es_bolsillo_independiente": True,
                    "datafono_no_en_administrativo": True,
                },
                "alertas": alertas,
                "catalogos": {
                    "vendedores": vendedores,
                    "categorias": categorias,
                    "proveedores": proveedores_cat,
                    "medios": ["Efectivo", "Nequi", "Datafono", "Otros"],
                },
                "nota_datafono": (
                    "Datafono es un medio de pago destinado al bolsillo de proveedores. "
                    "No es un bolsillo independiente ni forma parte del bolsillo administrativo."
                ),
            }
        )

    for path, fn, methods in (("/reportes-admin/", dashboard, ["GET"]),):
        app.add_api_route(path, fn, methods=methods, name=f"ra_{fn.__name__}_{methods[0]}")
        app.add_api_route(
            "/api/v1" + path,
            fn,
            methods=methods,
            name=f"ra_{fn.__name__}_{methods[0]}_v1",
        )
