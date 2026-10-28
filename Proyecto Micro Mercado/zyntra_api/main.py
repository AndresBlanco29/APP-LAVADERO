"""
Zyntra POS HTTP API for the boss Flutter app.
Compatible with api-production-b438.up.railway.app plus Anulada / Estado / Ganancia.
"""
from __future__ import annotations

import hmac
import json
import os
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional
from urllib.parse import unquote, urlparse
from zoneinfo import ZoneInfo

import pymysql
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

load_dotenv()

BOGOTA = ZoneInfo("America/Bogota")


def _env(*names: str, default: str = "") -> str:
    for name in names:
        value = os.getenv(name)
        if value:
            return value
    return default


def db_config() -> dict:
    url = _env("MYSQL_URL", "MYSQL_PUBLIC_URL", "DATABASE_URL")
    host = _env("MYSQLHOST", "MYSQL_HOST", "DB_HOST", default="hopper.proxy.rlwy.net")
    port = _env("MYSQLPORT", "MYSQL_PORT", "DB_PORT", default="3306")
    user = _env("MYSQLUSER", "MYSQL_USER", "DB_USER", default="root")
    password = _env("MYSQLPASSWORD", "MYSQL_PASSWORD", "MYSQL_ROOT_PASSWORD", "DB_PASSWORD")
    database = _env("MYSQLDATABASE", "MYSQL_DATABASE", "DB_NAME", default="railway")
    if url and ("mysql" in url or "mariadb" in url):
        parsed = urlparse(url)
        host = parsed.hostname or host
        port = str(parsed.port or port)
        user = unquote(parsed.username or user)
        password = unquote(parsed.password or password)
        database = (parsed.path or "/railway").lstrip("/") or database
    return {
        "host": host,
        "port": int(port or 3306),
        "user": user,
        "password": password,
        "database": database,
        "charset": "utf8mb4",
        "cursorclass": pymysql.cursors.DictCursor,
        "autocommit": True,
        "connect_timeout": 5,
        "read_timeout": 20,
        "write_timeout": 20,
    }


def json_safe(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="ignore")
    if isinstance(value, dict):
        return {k: json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [json_safe(v) for v in value]
    return value


def query(sql: str, params: tuple = ()) -> list[dict]:
    cfg = db_config()
    if not cfg["password"]:
        raise HTTPException(
            status_code=500,
            detail="Falta MYSQLPASSWORD. En Railway conéctala al MySQL del proyecto.",
        )
    conn = pymysql.connect(**cfg)
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall() or []
        return [json_safe(dict(row)) for row in rows]
    finally:
        conn.close()


def execute(sql: str, params: tuple = ()) -> int:
    cfg = db_config()
    if not cfg["password"]:
        raise HTTPException(status_code=500, detail="Falta MYSQLPASSWORD.")
    conn = pymysql.connect(**cfg)
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            conn.commit()
            return int(cur.lastrowid or 0)
    finally:
        conn.close()


def has_column(table: str, column: str) -> bool:
    rows = query(
        """
        SELECT COUNT(*) AS c
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = %s
          AND COLUMN_NAME = %s
        """,
        (table, column),
    )
    return bool(rows and int(rows[0]["c"]))


_column_cache: dict[tuple[str, str], bool] = {}


def col(table: str, column: str) -> bool:
    key = (table, column)
    if key not in _column_cache:
        _column_cache[key] = has_column(table, column)
    return _column_cache[key]


def pk_alias(table: str, wanted: str, fallbacks: tuple[str, ...]) -> str:
    for name in (wanted,) + fallbacks:
        if col(table, name):
            return f"`{name}` AS `{wanted}`"
    return f"NULL AS `{wanted}`"


def now_bogota() -> datetime:
    return datetime.now(BOGOTA)


def inicio_dia() -> datetime:
    n = now_bogota()
    return n.replace(hour=0, minute=0, second=0, microsecond=0)


def inicio_mes() -> datetime:
    n = now_bogota()
    return n.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def marcar_estado(venta: dict) -> dict:
    raw = venta.get("Anulada") if venta.get("Anulada") is not None else venta.get("anulada")
    anulada = str(raw).strip().lower() in {"1", "true", "si", "sí"} or raw == 1
    estado = str(venta.get("Estado") or venta.get("estado") or "")
    if estado.upper().find("ANUL") >= 0:
        anulada = True
    venta["Anulada"] = 1 if anulada else 0
    venta["anulada"] = anulada
    venta["Estado"] = "ANULADA" if anulada else "ACTIVA"
    venta["estado"] = venta["Estado"]
    return venta


app = FastAPI(title="Zyntra POS API", version="1.2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def raiz():
    return {"ok": True, "app": "Zyntra POS API", "docs": "/docs", "comando": True}


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/admin")
def validar_admin(
    usuario: Optional[str] = Query(None),
    contrasena: Optional[str] = Query(None),
):
    """Solo tabla admin. Vendedores (usuarios) NO autenticar como administrador (Entrega 7)."""
    if not usuario or not contrasena:
        return []
    try:
        id_sql = pk_alias("admin", "id_admin", ("id_admin", "Id_admin", "Id_Admin", "id"))
        rows = query(
            f"""
            SELECT {id_sql}, usuario, Nombre, telefono, correo_electronico
            FROM admin
            WHERE LOWER(usuario) = LOWER(%s) AND BINARY contrasena = %s
            """,
            (usuario, contrasena),
        )
        if rows:
            return [_normalizar_admin(rows[0], usuario)]
    except Exception:
        pass
    return []


def _normalizar_admin(row: dict, usuario: str) -> dict:
    lower = {str(k).lower(): v for k, v in row.items()}
    return {
        "id_admin": int(lower.get("id_admin") or lower.get("id") or 0),
        "usuario": str(lower.get("usuario") or usuario),
        "Nombre": row.get("Nombre") or row.get("nombre") or usuario,
        "telefono": row.get("telefono") or "",
        "correo_electronico": row.get("correo_electronico") or "",
        "es_admin": True,
    }


@app.get("/admin/{id_admin}")
def obtener_admin(id_admin: int):
    id_col = "Id_admin" if col("admin", "Id_admin") else (
        "id_admin" if col("admin", "id_admin") else "id"
    )
    rows = query(
        f"""
        SELECT `{id_col}` AS id_admin, usuario, Nombre, telefono, correo_electronico
        FROM admin
        WHERE `{id_col}` = %s
        """,
        (id_admin,),
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Admin no encontrado")
    return rows[0]


@app.get("/empleados")
def obtener_empleados():
    return query(
        """
        SELECT Id_Empleados, Nombres, Telefono, Correo,
               Fecha_nacimiento, Fecha_ingreso, Cargo
        FROM empleados
        ORDER BY Id_Empleados
        """
    )


@app.get("/productos")
def obtener_productos():
    img = ", url_imagen" if col("productos", "url_imagen") else (
        ", Url_Imagen AS url_imagen" if col("productos", "Url_Imagen") else ", NULL AS url_imagen"
    )
    proveedor_join = ""
    proveedor_select = "NULL AS proveedor"
    if col("productos", "Proveedor_ID") and has_column("proveedores", "Nombre"):
        proveedor_join = "LEFT JOIN proveedores pr ON pr.Id_Proveedor = p.Proveedor_ID"
        proveedor_select = "pr.Nombre AS proveedor"
    elif col("productos", "Proveedor"):
        proveedor_select = "p.Proveedor AS proveedor"

    categoria = "p.Categoria" if col("productos", "Categoria") else "NULL"
    ubic_est = "p.Ubicacion_Estante" if col("productos", "Ubicacion_Estante") else (
        "p.Ubicacion" if col("productos", "Ubicacion") else "NULL"
    )
    ubic_pas = "p.ubicacion_pasillo" if col("productos", "ubicacion_pasillo") else "NULL"
    desc = "p.Descripcion" if col("productos", "Descripcion") else "NULL"
    und = "p.Unidad_Medida" if col("productos", "Unidad_Medida") else "NULL"
    fent = "p.Fecha_Entrada" if col("productos", "Fecha_Entrada") else "NULL"
    fven = "p.Fecha_Vencimiento" if col("productos", "Fecha_Vencimiento") else "NULL"
    marca = "p.Marca" if col("productos", "Marca") else "NULL"
    barras = "p.Codigo_Barras" if col("productos", "Codigo_Barras") else "NULL"

    rows = query(
        f"""
        SELECT
            p.Id_Producto AS id,
            p.Nombre AS nombre,
            p.Precio_Venta AS precio_venta,
            p.Precio_Compra AS precio_compra,
            p.Cantidad AS cantidad,
            {marca} AS marca,
            {desc} AS descripcion,
            {categoria} AS categoria,
            {fent} AS fecha_entrada,
            {fven} AS fecha_vencimiento,
            {und} AS unidad_medida,
            {proveedor_select},
            {ubic_est} AS ubicacion_estante,
            {ubic_pas} AS ubicacion_pasillo,
            {barras} AS codigo_barras
            {img}
        FROM productos p
        {proveedor_join}
        ORDER BY p.Id_Producto
        """
    )
    for row in rows:
        if row.get("fecha_entrada"):
            row["fecha_entrada"] = str(row["fecha_entrada"])[:10]
        if row.get("fecha_vencimiento"):
            row["fecha_vencimiento"] = str(row["fecha_vencimiento"])[:10]
    return rows


def _ventas_base() -> list[dict]:
    anulada_sql = "COALESCE(v.Anulada, 0) AS Anulada" if col("ventas", "Anulada") else "0 AS Anulada"
    estado_sql = "v.Estado" if col("ventas", "Estado") else "NULL AS Estado"
    extra_group = []
    if col("ventas", "Anulada"):
        extra_group.append("v.Anulada")
    if col("ventas", "Estado"):
        extra_group.append("v.Estado")
    group_sql = "GROUP BY v.Id_Venta, v.Fecha_Venta, v.Total, e.Nombres"
    if extra_group:
        group_sql += ", " + ", ".join(extra_group)
    cab = query(
        f"""
        SELECT
            v.Id_Venta,
            v.Fecha_Venta,
            v.Total,
            {anulada_sql},
            {estado_sql},
            e.Nombres AS empleado_nombre,
            COALESCE(SUM(vp.Subtotal - (p.Precio_Compra * vp.Cantidad)), 0) AS Ganancia
        FROM ventas v
        LEFT JOIN empleados e ON e.Id_Empleados = v.Empleados_Id_Empleados
        LEFT JOIN productos_has_ventas vp ON vp.Ventas_Id_Factura = v.Id_Venta
        LEFT JOIN productos p ON p.Id_Producto = vp.Productos_Id_Producto
        {group_sql}
        ORDER BY v.Fecha_Venta DESC, v.Id_Venta DESC
        """
    )
    detalles = query(
        """
        SELECT
            vp.Ventas_Id_Factura AS Id_Venta,
            p.Nombre AS Nombre_Producto,
            vp.Cantidad,
            CASE
                WHEN vp.Cantidad IS NULL OR vp.Cantidad = 0 THEN p.Precio_Venta
                ELSE vp.Subtotal / vp.Cantidad
            END AS Precio
        FROM productos_has_ventas vp
        JOIN productos p ON p.Id_Producto = vp.Productos_Id_Producto
        """
    )
    por_venta: dict[int, list] = {}
    for item in detalles:
        por_venta.setdefault(int(item["Id_Venta"]), []).append(
            {
                "Nombre_Producto": item.get("Nombre_Producto") or "Producto",
                "Cantidad": item.get("Cantidad") or 0,
                "Precio": float(item.get("Precio") or 0),
            }
        )
    ventas = []
    for row in cab:
        venta = marcar_estado(
            {
                "Id_Venta": row["Id_Venta"],
                "Fecha_Venta": row["Fecha_Venta"],
                "Total": float(row.get("Total") or 0),
                "Anulada": row.get("Anulada") or 0,
                "Estado": row.get("Estado"),
                "Ganancia": float(row.get("Ganancia") or 0),
                "empleados": {"Nombres": row.get("empleado_nombre") or ""},
                "productos_vendidos": por_venta.get(int(row["Id_Venta"]), []),
            }
        )
        if venta["anulada"]:
            venta["Ganancia"] = 0.0
        ventas.append(venta)
    _mezclar_lavadero(ventas)
    return ventas


def _mezclar_lavadero(ventas: list[dict]) -> None:
    """Pega placa, cliente, sede, servicios, muchachos y ganancia del lavadero."""
    if not ventas:
        return
    try:
        if not col("ventas", "lavadero_detalle"):
            return
        filas = query(
            """
            SELECT Id_Venta, lavadero_detalle
            FROM ventas
            WHERE lavadero_detalle IS NOT NULL AND lavadero_detalle <> ''
            """
        )
    except Exception:
        return
    por_id: dict[int, dict] = {}
    for fila in filas:
        texto = fila.get("lavadero_detalle") or ""
        if not texto:
            continue
        try:
            detalle = json.loads(texto)
        except (TypeError, ValueError):
            continue
        if isinstance(detalle, dict):
            por_id[int(fila["Id_Venta"])] = detalle
    for venta in ventas:
        detalle = por_id.get(int(venta["Id_Venta"]))
        if not detalle:
            continue
        venta["Lavadero"] = 1
        venta["Placa"] = detalle.get("placa") or ""
        venta["Cliente"] = detalle.get("cliente") or ""
        venta["Telefono"] = detalle.get("telefono") or ""
        venta["Sucursal"] = detalle.get("sucursal") or ""
        venta["Zona"] = detalle.get("zona") or ""
        venta["Vehiculo"] = detalle.get("vehiculo") or ""
        venta["Hora"] = detalle.get("hora") or ""
        venta["Cobrado_por"] = detalle.get("cobrado_por") or ""
        venta["Nota"] = detalle.get("nota") or ""
        venta["Comisiones"] = float(detalle.get("comisiones") or 0)
        venta["Muchachos"] = detalle.get("muchachos") or []
        venta["Pagos"] = detalle.get("pagos") or []
        if not venta.get("anulada"):
            venta["Ganancia"] = float(detalle.get("ganancia") or 0)
        servicios = detalle.get("servicios") or []
        if servicios:
            venta["productos_vendidos"] = [
                {
                    "Nombre_Producto": item.get("nombre") or "Servicio",
                    "Cantidad": item.get("cantidad") or 1,
                    "Precio": float(item.get("precio") or 0),
                }
                for item in servicios
            ]
        nombres = [
            str(persona.get("nombre") or "").strip()
            for persona in (detalle.get("muchachos") or [])
            if str(persona.get("nombre") or "").strip()
        ]
        if nombres:
            venta["empleados"] = {"Nombres": ", ".join(nombres)}


@app.get("/ventas")
def obtener_ventas():
    return _ventas_base()


@app.get("/ventas-fechas")
def obtener_fechas_ventas():
    filas = query("SELECT Fecha_Venta FROM ventas ORDER BY Fecha_Venta ASC")
    out = []
    for row in filas:
        raw = row.get("Fecha_Venta")
        if not raw:
            continue
        texto = str(raw).replace(" ", "T")
        out.append({"fecha": texto})
    return out


@app.get("/finanzas")
def obtener_entrada_salida_dinero():
    id_ent = pk_alias("entrada_dinero", "Id_Entrada", ("Id_Entrada", "id_entrada", "id"))
    id_sal = pk_alias("salida_dinero", "Id_Salida", ("Id_Salida", "id_salida", "id"))
    entradas = query(
        f"""
        SELECT {id_ent}, Asunto, Fecha, Cantidad, Cajero
        FROM entrada_dinero
        ORDER BY Fecha DESC
        """
    )
    salidas = query(
        f"""
        SELECT {id_sal}, Cajero, Fecha, Asunto, Cantidad
        FROM salida_dinero
        ORDER BY Fecha DESC
        """
    )
    return {"entradas": entradas, "salidas": salidas}


@app.get("/start-updating")
def start_updating():
    return {"ok": True}


def _rango_rotacion(periodo: str) -> datetime:
    periodo = (periodo or "dia").lower()
    if periodo in {"mes", "month"}:
        return inicio_mes()
    return inicio_dia()


def _rotacion(periodo: str, orden: str = "desc", todos: bool = False) -> list[dict]:
    desde = _rango_rotacion(periodo)
    order = "ASC" if str(orden).lower() == "asc" else "DESC"
    limit_sql = "" if todos else "LIMIT 10"
    anulada_filter = "AND COALESCE(v.Anulada, 0) = 0" if col("ventas", "Anulada") else ""
    return query(
        f"""
        SELECT
            p.Id_Producto AS id,
            p.Nombre AS nombre,
            p.Marca AS marca,
            p.Precio_Venta AS precio,
            p.Precio_Compra AS costo,
            p.Codigo_Barras AS codigo_barras,
            COALESCE(SUM(CASE WHEN v.Id_Venta IS NULL THEN 0 ELSE vp.Cantidad END), 0) AS cantidad,
            COALESCE(SUM(CASE WHEN v.Id_Venta IS NULL THEN 0 ELSE vp.Subtotal END), 0) AS total,
            COALESCE(SUM(CASE WHEN v.Id_Venta IS NULL THEN 0 ELSE p.Precio_Compra * vp.Cantidad END), 0) AS costo_total,
            COALESCE(SUM(CASE WHEN v.Id_Venta IS NULL THEN 0 ELSE vp.Subtotal - (p.Precio_Compra * vp.Cantidad) END), 0) AS ganancia
        FROM productos p
        LEFT JOIN productos_has_ventas vp ON vp.Productos_Id_Producto = p.Id_Producto
        LEFT JOIN ventas v
            ON v.Id_Venta = vp.Ventas_Id_Factura
           AND v.Fecha_Venta >= %s
           {anulada_filter}
        GROUP BY p.Id_Producto, p.Nombre, p.Marca, p.Precio_Venta, p.Precio_Compra, p.Codigo_Barras
        ORDER BY cantidad {order}, total {order}
        {limit_sql}
        """,
        (desde.strftime("%Y-%m-%d %H:%M:%S"),),
    )


@app.get("/rotacion/dia")
def productos_mas_vendidos_dia(orden: str = "desc"):
    return _rotacion("dia", orden, todos=False)


@app.get("/rotacion/mes")
def productos_mas_vendidos_mes(orden: str = "desc"):
    return _rotacion("mes", orden, todos=False)


@app.get("/rotacion/masVendidos/dia")
def productos_mas_vendidos_dia_mas(orden: str = "desc"):
    return _rotacion("dia", orden, todos=False)


@app.get("/rotacion/masVendidos/mes")
def productos_mas_vendidos_mes_mas(orden: str = "desc"):
    return _rotacion("mes", orden, todos=False)


@app.get("/rotacion/todos/{periodo}")
def productos_todos_rotacion(
    periodo: str,
    orden: str = "desc",
    todos: bool = Query(True, alias="all"),
):
    return _rotacion(periodo, orden, todos=todos)


@app.get("/sales")
def sales_data(
    start: str = Query(...),
    end: str = Query(...),
    aggregation: str = Query("Diario"),
):
    anulada_sql = "AND COALESCE(Anulada, 0) = 0" if col("ventas", "Anulada") else ""
    rows = query(
        f"""
        SELECT Fecha_Venta, Total, Id_Venta
        FROM ventas
        WHERE Fecha_Venta >= %s AND Fecha_Venta < %s
        {anulada_sql}
        ORDER BY Fecha_Venta
        """,
        (start.replace("T", " ")[:19], end.replace("T", " ")[:19]),
    )
    return [
        {
            "Fecha_Venta": row["Fecha_Venta"],
            "Total": float(row.get("Total") or 0),
            "Id_Venta": row["Id_Venta"],
            "aggregation": aggregation,
        }
        for row in rows
    ]


from comando import register as register_comando
from cierre_diario import register as register_cierre_diario
from provision_admin import register as register_provision_admin
from cierre_general import register as register_cierre_general
from bolsillo_proveedores import register as register_bolsillo_proveedores
from provision_obligaciones import register as register_provision_obligaciones
from reportes_admin import register as register_reportes_admin

register_comando(app)
register_cierre_diario(app)
register_provision_admin(app)
register_cierre_general(app)
register_bolsillo_proveedores(app)
register_provision_obligaciones(app)
register_reportes_admin(app)

@app.post("/api/v1/caja/aviso")
async def aviso_caja(request: Request):
    """La sede avisa al celular de que entró una venta. El token evita avisos falsos."""
    esperado = os.getenv("LAVADERO_AVISO_TOKEN", "")
    recibido = request.headers.get("x-aviso-token") or ""
    autorizado = bool(esperado) and len(recibido) == len(esperado) and hmac.compare_digest(recibido, esperado)
    if not autorizado:
        raise HTTPException(status_code=403, detail="Aviso no autorizado.")
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Aviso inválido.")
    if not isinstance(data, dict) or data.get("tipo") != "orden_cobrada":
        raise HTTPException(status_code=400, detail="Aviso inválido.")
    from comando import HUB

    await HUB.broadcast(data)
    return {"ok": True}


from lavadero import register as register_lavadero

register_lavadero(app)


if __name__ == "__main__":
    import asyncio

    raw_port = os.environ.get("PORT", "8000")
    try:
        port = int(raw_port)
    except ValueError:
        port = 8000

    on_railway = bool(
        os.environ.get("RAILWAY_ENVIRONMENT") or os.environ.get("RAILWAY_PROJECT_ID")
    )
    if on_railway:
        from hypercorn.asyncio import serve
        from hypercorn.config import Config

        config = Config()
        config.bind = [f"[::]:{port}"]
        asyncio.run(serve(app, config))
    else:
        import uvicorn

        uvicorn.run(app, host="0.0.0.0", port=port)
