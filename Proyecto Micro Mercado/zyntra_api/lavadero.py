"""Lavadero multi-sucursal: órdenes, comisiones, cierre y reportes.

Los datos viven en SQLite local (data/lavadero.db) cuando no hay MySQL,
y en el mismo MySQL del POS cuando MYSQLPASSWORD está configurada.
Al cobrar se intenta reflejar la venta en la tabla ventas para la app Flutter.
"""
from __future__ import annotations

import asyncio
import base64
import functools
import hashlib
import hmac
import json
import os
import re
import secrets
import smtplib
import sqlite3
import threading
import traceback
from email.message import EmailMessage
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional
from urllib.parse import quote
from zoneinfo import ZoneInfo

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse

BOGOTA = ZoneInfo("America/Bogota")
RAIZ = Path(__file__).resolve().parent
ESTATICOS = RAIZ / "static" / "lavadero"
_LOOP: Optional[asyncio.AbstractEventLoop] = None
_LISTO = False
_DB: Optional["BaseDatos"] = None


class ErrorLavadero(Exception):
    def __init__(self, mensaje: str, status: int = 400):
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.status = status


REVISION_VEHICULO = (
    "Rayones",
    "Golpes",
    "Vidrios",
    "Espejos",
    "Antena",
    "Tapetes",
    "Objetos dentro",
    "Llantas",
)


def ahora() -> str:
    return datetime.now(BOGOTA).strftime("%Y-%m-%d %H:%M:%S")


def hoy() -> str:
    return datetime.now(BOGOTA).strftime("%Y-%m-%d")


def pesos(valor: Any) -> int:
    try:
        return int(round(float(valor or 0)))
    except (TypeError, ValueError):
        return 0


def formato_pesos(valor: Any) -> str:
    return "$" + f"{pesos(valor):,}".replace(",", ".")


def _secreto() -> bytes:
    carpeta = RAIZ / "data"
    carpeta.mkdir(parents=True, exist_ok=True)
    archivo = carpeta / "secret.key"
    if archivo.exists():
        return archivo.read_bytes()
    clave = os.urandom(32)
    archivo.write_bytes(clave)
    return clave


def hacer_token(usuario: str, rol: str, nombre: str, branch_id: int) -> str:
    cuerpo = json.dumps(
        {
            "u": usuario,
            "r": rol,
            "n": nombre,
            "b": int(branch_id or 0),
            "e": int(datetime.now().timestamp()) + 60 * 60 * 24 * 14,
        },
        separators=(",", ":"),
    )
    firma = hmac.new(_secreto(), cuerpo.encode(), hashlib.sha256).hexdigest()
    return base64.urlsafe_b64encode(f"{cuerpo}.{firma}".encode()).decode()


def leer_token(token: str) -> Optional[dict]:
    try:
        crudo = base64.urlsafe_b64decode(token.encode()).decode()
        cuerpo, firma = crudo.rsplit(".", 1)
        buena = hmac.new(_secreto(), cuerpo.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(firma, buena):
            return None
        data = json.loads(cuerpo)
        if int(data.get("e") or 0) < datetime.now().timestamp():
            return None
        return {
            "usuario": data["u"],
            "rol": data["r"],
            "nombre": data.get("n") or data["u"],
            "branch_id": int(data.get("b") or 0),
        }
    except Exception:
        return None


def hash_clave(clave: str) -> str:
    return hashlib.sha256(clave.encode("utf-8")).hexdigest()


class BaseDatos:
    def __init__(self) -> None:
        self.kind = "sqlite"
        self.lock = threading.RLock()
        self._en_tx = False
        self.conn = self._abrir()

    def _abrir(self):
        forzar = os.getenv("LAVADERO_FORCE_SQLITE", "").strip() in {"1", "true", "si", "sí"}
        clave = os.getenv("MYSQLPASSWORD") or os.getenv("MYSQL_PASSWORD") or os.getenv("DB_PASSWORD") or ""
        if clave and not forzar:
            try:
                import pymysql

                host = os.getenv("MYSQLHOST") or os.getenv("MYSQL_HOST") or "localhost"
                port = int(os.getenv("MYSQLPORT") or os.getenv("MYSQL_PORT") or "3306")
                user = os.getenv("MYSQLUSER") or os.getenv("MYSQL_USER") or "root"
                database = os.getenv("MYSQLDATABASE") or os.getenv("MYSQL_DATABASE") or "railway"
                self.kind = "mysql"
                return pymysql.connect(
                    host=host,
                    port=port,
                    user=user,
                    password=clave,
                    database=database,
                    charset="utf8mb4",
                    cursorclass=pymysql.cursors.DictCursor,
                    autocommit=False,
                )
            except Exception:
                traceback.print_exc()
                self.kind = "sqlite"
        ruta = os.getenv("LAVADERO_DB") or str(RAIZ / "data" / "lavadero.db")
        Path(ruta).parent.mkdir(parents=True, exist_ok=True)
        conexion = sqlite3.connect(ruta, check_same_thread=False, isolation_level=None)
        conexion.row_factory = sqlite3.Row
        return conexion

    def _sql(self, sql: str) -> str:
        if self.kind == "mysql":
            return sql.replace("?", "%s")
        return sql

    def _ddl(self, sql: str) -> str:
        if self.kind == "mysql":
            return sql.replace(
                "INTEGER PRIMARY KEY AUTOINCREMENT",
                "INT NOT NULL AUTO_INCREMENT PRIMARY KEY",
            )
        return sql

    def _filas(self, cursor) -> list[dict]:
        if self.kind == "mysql":
            return list(cursor.fetchall() or [])
        return [dict(fila) for fila in cursor.fetchall()]

    def run(self, sql: str, params: tuple = (), *, commit: bool = True) -> int:
        with self.lock:
            if self.kind == "mysql":
                cur = self.conn.cursor()
                cur.execute(self._sql(sql), params)
                ultimo = int(cur.lastrowid or 0)
                cur.close()
                if commit and not self._en_tx:
                    self.conn.commit()
                return ultimo
            cur = self.conn.execute(self._sql(sql), params)
            if commit and not self._en_tx:
                self.conn.commit()
            return int(cur.lastrowid or 0)

    def ddl(self, sql: str) -> None:
        self.run(self._ddl(sql), commit=True)

    def all(self, sql: str, params: tuple = ()) -> list[dict]:
        with self.lock:
            if self.kind == "mysql":
                cur = self.conn.cursor()
                cur.execute(self._sql(sql), params)
                filas = self._filas(cur)
                cur.close()
                return filas
            cur = self.conn.execute(self._sql(sql), params)
            return self._filas(cur)

    def one(self, sql: str, params: tuple = ()) -> Optional[dict]:
        filas = self.all(sql, params)
        return filas[0] if filas else None

    def dia(self, columna: str) -> str:
        if self.kind == "sqlite":
            return f"date({columna})"
        return f"DATE({columna})"

    def mes(self, columna: str) -> str:
        if self.kind == "sqlite":
            return f"strftime('%Y-%m', {columna})"
        return f"DATE_FORMAT({columna}, '%%Y-%%m')"

    def hora(self, columna: str) -> str:
        if self.kind == "sqlite":
            return f"strftime('%H', {columna})"
        return f"DATE_FORMAT({columna}, '%%H')"

    @contextmanager
    def tx(self):
        with self.lock:
            self._en_tx = True
            try:
                if self.kind == "mysql":
                    self.conn.begin()
                else:
                    self.conn.execute("BEGIN")
                yield
                self.conn.commit()
            except Exception:
                self.conn.rollback()
                raise
            finally:
                self._en_tx = False


def db() -> BaseDatos:
    global _DB
    if _DB is None:
        _DB = BaseDatos()
    return _DB


def asegurar() -> None:
    global _LISTO
    if not _LISTO:
        init_db()
        _LISTO = True


def init_db() -> None:
    global _LISTO
    base = db()
    tablas = [
        """
        CREATE TABLE IF NOT EXISTS lv_usuario (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT NOT NULL UNIQUE,
            nombre TEXT NOT NULL,
            clave_hash TEXT NOT NULL,
            rol TEXT NOT NULL,
            branch_id INTEGER DEFAULT 0,
            activo INTEGER DEFAULT 1
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS lv_sucursal (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            telefono TEXT DEFAULT '',
            direccion TEXT DEFAULT '',
            activo INTEGER DEFAULT 1
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS lv_zona (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            branch_id INTEGER NOT NULL,
            nombre TEXT NOT NULL,
            tipo TEXT DEFAULT 'MIXTA',
            activo INTEGER DEFAULT 1
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS lv_tipo (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            zona_id INTEGER NOT NULL,
            nombre TEXT NOT NULL,
            codigo TEXT NOT NULL,
            icono TEXT DEFAULT '🚗',
            orden INTEGER DEFAULT 0,
            activo INTEGER DEFAULT 1
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS lv_servicio (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            zona_id INTEGER NOT NULL,
            nombre TEXT NOT NULL,
            grupo TEXT DEFAULT 'Basico',
            icono TEXT DEFAULT '🚿',
            duracion TEXT DEFAULT '',
            activo INTEGER DEFAULT 1
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS lv_precio (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            servicio_id INTEGER NOT NULL,
            tipo_id INTEGER NOT NULL,
            precio INTEGER NOT NULL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS lv_producto (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            precio INTEGER NOT NULL,
            costo INTEGER DEFAULT 0,
            stock INTEGER DEFAULT 0,
            origen_id INTEGER DEFAULT 0,
            activo INTEGER DEFAULT 1
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS lv_empleado (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            apellido TEXT DEFAULT '',
            telefono TEXT DEFAULT '',
            activo INTEGER DEFAULT 1
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS lv_medio (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            orden INTEGER DEFAULT 0,
            activo INTEGER DEFAULT 1
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS lv_regla (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empleado_id INTEGER DEFAULT 0,
            servicio_id INTEGER DEFAULT 0,
            grupo TEXT DEFAULT '',
            porcentaje INTEGER NOT NULL,
            activo INTEGER DEFAULT 1
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS lv_reparto (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            branch_id INTEGER NOT NULL,
            zona_id INTEGER DEFAULT 0,
            modo TEXT NOT NULL,
            valor INTEGER NOT NULL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS lv_config (
            clave TEXT PRIMARY KEY,
            valor TEXT DEFAULT ''
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS lv_orden (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            branch_id INTEGER NOT NULL,
            zona_id INTEGER DEFAULT 0,
            tipo_id INTEGER DEFAULT 0,
            tipo_orden TEXT NOT NULL,
            placa TEXT DEFAULT '',
            cliente_nombre TEXT DEFAULT '',
            cliente_telefono TEXT DEFAULT '',
            estado TEXT NOT NULL,
            total INTEGER DEFAULT 0,
            venta_id INTEGER DEFAULT 0,
            creada_en TEXT,
            lista_en TEXT,
            cobrada_en TEXT,
            anulada_en TEXT
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS lv_item (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            orden_id INTEGER NOT NULL,
            tipo TEXT NOT NULL,
            servicio_id INTEGER DEFAULT 0,
            producto_id INTEGER DEFAULT 0,
            descripcion TEXT NOT NULL,
            grupo TEXT DEFAULT '',
            cantidad INTEGER DEFAULT 1,
            precio INTEGER NOT NULL,
            subtotal INTEGER NOT NULL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS lv_colab (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            orden_id INTEGER NOT NULL,
            empleado_id INTEGER NOT NULL,
            peso INTEGER DEFAULT 1
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS lv_comision (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            orden_id INTEGER NOT NULL,
            item_id INTEGER NOT NULL,
            empleado_id INTEGER NOT NULL,
            base INTEGER NOT NULL,
            porcentaje INTEGER NOT NULL,
            monto INTEGER NOT NULL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS lv_pago (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            orden_id INTEGER NOT NULL,
            medio TEXT NOT NULL,
            monto INTEGER NOT NULL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS lv_cierre (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            branch_id INTEGER NOT NULL,
            fecha TEXT NOT NULL,
            producido INTEGER DEFAULT 0,
            comisiones INTEGER DEFAULT 0,
            gastos INTEGER DEFAULT 0,
            ganancia INTEGER DEFAULT 0,
            vehiculos INTEGER DEFAULT 0,
            texto TEXT DEFAULT '',
            usuario TEXT DEFAULT '',
            creado_en TEXT
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS lv_auditoria (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT,
            fecha TEXT,
            accion TEXT,
            detalle TEXT
        )
        """,
    ]
    for sql in tablas:
        base.ddl(sql)
    if not _tiene_columna(base, "lv_empleado", "apellido"):
        base.ddl("ALTER TABLE lv_empleado ADD COLUMN apellido TEXT DEFAULT ''")
    for indice in (
        "CREATE INDEX IF NOT EXISTS idx_lv_orden_estado ON lv_orden (branch_id, estado)",
        "CREATE INDEX IF NOT EXISTS idx_lv_orden_cobro ON lv_orden (cobrada_en)",
        "CREATE INDEX IF NOT EXISTS idx_lv_item_orden ON lv_item (orden_id)",
        "CREATE INDEX IF NOT EXISTS idx_lv_comision_orden ON lv_comision (orden_id)",
    ):
        try:
            base.ddl(indice)
        except Exception:
            pass
    _migrar(base)
    _sembrar(base)
    _migrar(base)
    _LISTO = True


def _migrar(base: BaseDatos) -> None:
    if not _tiene_columna(base, "lv_orden", "checklist"):
        base.ddl("ALTER TABLE lv_orden ADD COLUMN checklist TEXT DEFAULT ''")
    if not _tiene_columna(base, "lv_orden", "nota"):
        base.ddl("ALTER TABLE lv_orden ADD COLUMN nota TEXT DEFAULT ''")
    base.run("UPDATE lv_usuario SET rol='vendedor' WHERE rol='cajero'")
    if not _tiene_columna(base, "lv_usuario", "correo"):
        base.ddl("ALTER TABLE lv_usuario ADD COLUMN correo TEXT DEFAULT ''")
    base.ddl(
        """
        CREATE TABLE IF NOT EXISTS lv_recupero (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL,
            token_hash TEXT NOT NULL,
            vence_en TEXT NOT NULL,
            usado INTEGER DEFAULT 0
        )
        """
    )
    _asegurar_bolsillos(base)
    _asegurar_gastos(base)
    base.run("UPDATE lv_tipo SET activo=0 WHERE upper(codigo)='CASCO' OR upper(nombre)='CASCO'")
    base.run(
        """
        UPDATE lv_servicio SET activo=0
        WHERE upper(grupo)='CASCO' OR upper(nombre) LIKE '%CASCO%'
        """
    )
    base.run(
        """
        UPDATE lv_regla SET activo=0
        WHERE upper(grupo)='CASCO' AND empleado_id=0 AND servicio_id=0
        """
    )


BOLSILLOS_INICIALES = (
    ("Para los muchachos", 30, "MUCHACHOS", 1, "👷", "#f97316", "Según el trabajo cobrado hoy"),
    ("Gastos operativos", 35, "GASTO", 2, "💡", "#3b82f6", "Arriendo, servicios e insumos"),
    ("Seguridad social y provisiones", 10, "GASTO", 3, "🛡️", "#6366f1", "Seguridad social y provisiones legales"),
    ("Utilidad neta", 25, "UTILIDAD", 4, "💰", "#1e9b45", "Lo que queda para el negocio"),
)
PALETA_GASTO = ("#3b82f6", "#6366f1", "#0ea5e9", "#7c3aed", "#0891b2", "#d97706")


def _asegurar_bolsillos(base: BaseDatos) -> None:
    base.ddl(
        """
        CREATE TABLE IF NOT EXISTS lv_bolsillo (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            porcentaje INTEGER NOT NULL,
            tipo TEXT NOT NULL,
            orden INTEGER DEFAULT 0,
            icono TEXT DEFAULT '',
            color TEXT DEFAULT '',
            detalle TEXT DEFAULT ''
        )
        """
    )
    if int(base.one("SELECT COUNT(*) AS c FROM lv_bolsillo")["c"] or 0):
        return
    for nombre, porcentaje, tipo, orden, icono, color, detalle in BOLSILLOS_INICIALES:
        base.run(
            """
            INSERT INTO lv_bolsillo (nombre, porcentaje, tipo, orden, icono, color, detalle)
            VALUES (?,?,?,?,?,?,?)
            """,
            (nombre, porcentaje, tipo, orden, icono, color, detalle),
        )


def listar_bolsillos() -> list[dict]:
    _asegurar_bolsillos(db())
    return db().all("SELECT * FROM lv_bolsillo ORDER BY orden, id")


def _icono_bolsillo(tipo: str, icono: Any) -> str:
    limpio = str(icono or "").strip()
    if limpio and len(limpio) <= 4 and "<" not in limpio:
        return limpio
    if tipo == "MUCHACHOS":
        return "👷"
    if tipo == "UTILIDAD":
        return "💰"
    return "💡"


def guardar_bolsillos(datos: dict, usuario: str = "") -> list[dict]:
    crudos = datos.get("bolsillos") if isinstance(datos, dict) else datos
    if not isinstance(crudos, list) or not crudos:
        raise ErrorLavadero("Agrega al menos un bolsillo.")
    limpios = []
    suma = 0
    for crudo in crudos:
        if not isinstance(crudo, dict):
            raise ErrorLavadero("Revisa los bolsillos.")
        nombre = " ".join(str(crudo.get("nombre") or "").split())
        if len(nombre) < 3:
            raise ErrorLavadero("Escribe el nombre de cada bolsillo.")
        porcentaje = _entero(crudo.get("porcentaje"), "El porcentaje", 0, 100)
        tipo = str(crudo.get("tipo") or "GASTO").upper()
        if tipo not in {"MUCHACHOS", "GASTO", "UTILIDAD"}:
            raise ErrorLavadero("Ese bolsillo no se reconoce.")
        suma += porcentaje
        try:
            id_pedido = int(crudo.get("id") or 0)
        except (TypeError, ValueError):
            id_pedido = 0
        detalle = {
            "MUCHACHOS": "Según el trabajo cobrado hoy",
            "UTILIDAD": "Lo que queda para el negocio",
        }.get(tipo, "Porcentaje de lo que entró")
        limpios.append(
            {
                "nombre": nombre[:60],
                "porcentaje": porcentaje,
                "tipo": tipo,
                "icono": _icono_bolsillo(tipo, crudo.get("icono")),
                "detalle": detalle,
                "id": id_pedido,
            }
        )
    tipos = [item["tipo"] for item in limpios]
    if tipos.count("MUCHACHOS") != 1:
        raise ErrorLavadero("Tiene que haber un bolsillo para los muchachos.")
    if tipos.count("UTILIDAD") != 1:
        raise ErrorLavadero("Tiene que haber un bolsillo de utilidad neta.")
    if suma != 100:
        raise ErrorLavadero(f"Los bolsillos deben sumar 100%. Ahora suman {suma}%.")
    actuales = {int(bolsa["id"]) for bolsa in listar_bolsillos()}
    with db().tx():
        vistos: set[int] = set()
        for orden, item in enumerate(limpios, start=1):
            if item["tipo"] == "MUCHACHOS":
                color = "#f97316"
            elif item["tipo"] == "UTILIDAD":
                color = "#1e9b45"
            else:
                previos = sum(1 for previo in limpios[: orden - 1] if previo["tipo"] == "GASTO")
                color = PALETA_GASTO[previos % len(PALETA_GASTO)]
            valores = (item["nombre"], item["porcentaje"], item["tipo"], orden, item["icono"], color, item["detalle"])
            if item["id"] in actuales and item["id"] not in vistos:
                db().run(
                    """
                    UPDATE lv_bolsillo
                    SET nombre=?, porcentaje=?, tipo=?, orden=?, icono=?, color=?, detalle=?
                    WHERE id=?
                    """,
                    (*valores, item["id"]),
                )
                vistos.add(item["id"])
            else:
                nuevo = db().run(
                    """
                    INSERT INTO lv_bolsillo (nombre, porcentaje, tipo, orden, icono, color, detalle)
                    VALUES (?,?,?,?,?,?,?)
                    """,
                    valores,
                )
                vistos.add(int(nuevo))
        for viejo in actuales - vistos:
            db().run("DELETE FROM lv_bolsillo WHERE id=?", (viejo,))
    auditar(usuario, "bolsillos", f"Suman 100% en {len(limpios)} bolsillos")
    return listar_bolsillos()


def _aplicar_bolsillos(producido: int, comisiones: int) -> tuple[list[dict], int, int]:
    config = listar_bolsillos()
    salida: list[dict] = []
    gastos = 0
    utilidad_i = None
    for bolsa in config:
        tipo = str(bolsa["tipo"])
        porcentaje = int(bolsa["porcentaje"] or 0)
        if tipo == "MUCHACHOS":
            monto = comisiones
        elif tipo == "UTILIDAD":
            utilidad_i = len(salida)
            monto = 0
        else:
            monto = pesos(producido * porcentaje / 100)
            gastos += monto
        salida.append(
            {
                "id": bolsa["id"],
                "nombre": bolsa["nombre"],
                "porcentaje": porcentaje,
                "tipo": tipo,
                "icono": bolsa.get("icono") or "",
                "color": bolsa.get("color") or "#3b82f6",
                "detalle": bolsa.get("detalle") or "",
                "monto": monto,
            }
        )
    ganancia = producido - comisiones - gastos
    if utilidad_i is not None:
        salida[utilidad_i]["monto"] = ganancia
    return salida, gastos, ganancia


def _asegurar_gastos(base: BaseDatos) -> None:
    base.ddl(
        """
        CREATE TABLE IF NOT EXISTS lv_gasto (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            branch_id INTEGER NOT NULL,
            bolsillo_id INTEGER NOT NULL,
            bolsillo_nombre TEXT NOT NULL,
            clase TEXT NOT NULL,
            concepto TEXT NOT NULL,
            monto INTEGER NOT NULL,
            fecha TEXT NOT NULL,
            nota TEXT DEFAULT '',
            usuario TEXT DEFAULT '',
            creado_en TEXT NOT NULL
        )
        """
    )
    base.ddl(
        """
        CREATE TABLE IF NOT EXISTS lv_ingreso (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            gasto_id INTEGER NOT NULL,
            producto_id INTEGER NOT NULL,
            nombre TEXT NOT NULL,
            cantidad INTEGER NOT NULL,
            precio INTEGER NOT NULL DEFAULT 0
        )
        """
    )
    if not _tiene_columna(base, "lv_ingreso", "precio"):
        base.ddl("ALTER TABLE lv_ingreso ADD COLUMN precio INTEGER DEFAULT 0")


def _fecha_gasto(valor: Any) -> str:
    texto = str(valor or "").strip()[:10]
    if not texto:
        return hoy()
    try:
        dia = datetime.strptime(texto, "%Y-%m-%d").date()
    except ValueError:
        raise ErrorLavadero("Escribe la fecha del gasto.")
    if dia > datetime.now(BOGOTA).date():
        raise ErrorLavadero("La fecha no puede ser de después.")
    return dia.strftime("%Y-%m-%d")


def _limpiar_gasto(datos: dict, ses: dict) -> dict:
    branch_id = _branch_efectivo(ses, int(datos.get("branch_id") or 0))
    sucursal = db().one("SELECT id FROM lv_sucursal WHERE id=? AND activo=1", (branch_id,)) if branch_id else None
    if not sucursal:
        raise ErrorLavadero("Elige la sucursal del gasto.")
    clase = str(datos.get("clase") or "").strip().upper()
    if clase not in {"PAGO", "COMPRA"}:
        raise ErrorLavadero("Elige si es un pago o una compra.")
    concepto = " ".join(str(datos.get("concepto") or "").split())
    if len(concepto) < 3:
        raise ErrorLavadero("Escribe qué se pagó o qué se compró.")
    monto = _entero(datos.get("monto"), "El valor", 1, 100000000)
    try:
        bolsillo_id = int(datos.get("bolsillo_id") or 0)
    except (TypeError, ValueError):
        bolsillo_id = 0
    bolsa = db().one("SELECT * FROM lv_bolsillo WHERE id=?", (bolsillo_id,))
    if not bolsa:
        raise ErrorLavadero("Elige el bolsillo de donde sale este gasto.")
    if str(bolsa["tipo"]) == "MUCHACHOS":
        raise ErrorLavadero("El bolsillo de los muchachos no se toca. Elige otro.")
    nota = " ".join(str(datos.get("nota") or "").split())[:160]
    return {
        "branch_id": branch_id,
        "bolsillo_id": int(bolsa["id"]),
        "bolsillo_nombre": str(bolsa["nombre"]),
        "clase": clase,
        "concepto": concepto[:80],
        "monto": monto,
        "fecha": _fecha_gasto(datos.get("fecha")),
        "nota": nota,
    }


def _gasto_publico(fila: dict, lineas: Optional[list[dict]] = None) -> dict:
    if lineas is None:
        lineas = db().all(
            "SELECT producto_id, nombre, cantidad, precio FROM lv_ingreso WHERE gasto_id=? ORDER BY id",
            (int(fila["id"]),),
        )
    return {
        "id": int(fila["id"]),
        "branch_id": int(fila["branch_id"]),
        "bolsillo_id": int(fila["bolsillo_id"]),
        "bolsillo_nombre": fila["bolsillo_nombre"],
        "clase": fila["clase"],
        "concepto": fila["concepto"],
        "monto": pesos(fila["monto"]),
        "fecha": str(fila["fecha"])[:10],
        "nota": fila.get("nota") or "",
        "usuario": fila.get("usuario") or "",
        "productos": [
            {
                "producto_id": int(linea["producto_id"]),
                "nombre": linea["nombre"],
                "cantidad": int(linea["cantidad"]),
                "precio": pesos(linea.get("precio")),
            }
            for linea in lineas
        ],
    }


def _lineas_ingreso(crudos: Any) -> list[dict]:
    if not isinstance(crudos, list):
        raise ErrorLavadero("Revisa los productos que entran.")
    salida = []
    vistos: set[int] = set()
    for crudo in crudos:
        if not isinstance(crudo, dict):
            continue
        try:
            producto_id = int(crudo.get("producto_id") or 0)
        except (TypeError, ValueError):
            producto_id = 0
        cantidad = _entero(crudo.get("cantidad"), "La cantidad", 0, 100000)
        if cantidad <= 0 or not producto_id:
            continue
        if producto_id in vistos:
            raise ErrorLavadero("Ese producto está repetido.")
        producto = db().one("SELECT * FROM lv_producto WHERE id=?", (producto_id,))
        if not producto:
            raise ErrorLavadero("Un producto ya no está disponible.")
        precio = _entero(crudo.get("precio"), "El precio", 0, 100000000)
        if precio <= 0:
            raise ErrorLavadero(f"Escribe el precio de {producto['nombre']}.")
        vistos.add(producto_id)
        salida.append(
            {
                "producto_id": producto_id,
                "nombre": str(producto["nombre"]),
                "cantidad": cantidad,
                "precio": precio,
            }
        )
    return salida


def _texto_ingreso(lineas: list[dict]) -> str:
    return ", ".join(f"{linea['nombre']} x{linea['cantidad']}" for linea in lineas)[:80]


def _aplicar_stock(deltas: dict[int, int]) -> None:
    for producto_id, delta in deltas.items():
        if not delta:
            continue
        producto = db().one("SELECT nombre, stock FROM lv_producto WHERE id=?", (int(producto_id),))
        if not producto:
            raise ErrorLavadero("Un producto ya no está.")
        nuevo = int(producto["stock"] or 0) + int(delta)
        if nuevo < 0:
            raise ErrorLavadero(f"No se puede quitar esa entrada. Ya se vendió parte de {producto['nombre']}.")
        db().run("UPDATE lv_producto SET stock=? WHERE id=?", (nuevo, int(producto_id)))


def _deltas_stock(anteriores: list[dict], nuevas: list[dict]) -> dict[int, int]:
    delta: dict[int, int] = {}
    for linea in anteriores:
        clave = int(linea["producto_id"])
        delta[clave] = delta.get(clave, 0) - int(linea["cantidad"])
    for linea in nuevas:
        clave = int(linea["producto_id"])
        delta[clave] = delta.get(clave, 0) + int(linea["cantidad"])
    return delta


def _guardar_lineas(gasto_id: int, lineas: list[dict]) -> None:
    db().run("DELETE FROM lv_ingreso WHERE gasto_id=?", (int(gasto_id),))
    for linea in lineas:
        db().run(
            "INSERT INTO lv_ingreso (gasto_id, producto_id, nombre, cantidad, precio) VALUES (?,?,?,?,?)",
            (int(gasto_id), linea["producto_id"], linea["nombre"], linea["cantidad"], linea["precio"]),
        )


def guardar_gasto(datos: dict, ses: dict, id_registro: int = 0) -> dict:
    solo_dueno(ses)
    _asegurar_gastos(db())
    lineas = None
    if isinstance(datos, dict) and "productos" in datos:
        lineas = _lineas_ingreso(datos.get("productos") or [])
        if not lineas:
            raise ErrorLavadero("Elige cuántos entran de cada producto.")
        datos = dict(datos)
        datos["clase"] = "COMPRA"
        datos["monto"] = sum(linea["cantidad"] * linea["precio"] for linea in lineas)
        if len(" ".join(str(datos.get("concepto") or "").split())) < 3:
            datos["concepto"] = _texto_ingreso(lineas)
    limpio = _limpiar_gasto(datos, ses)
    with db().tx():
        if id_registro:
            fila = db().one("SELECT * FROM lv_gasto WHERE id=?", (int(id_registro),))
            if not fila:
                raise ErrorLavadero("Ese gasto ya no está.")
            fijo = int(ses.get("branch_id") or 0)
            if fijo and int(fila["branch_id"]) != fijo:
                raise ErrorLavadero("Ese gasto es de otra sucursal.")
            anteriores = db().all("SELECT * FROM lv_ingreso WHERE gasto_id=?", (int(id_registro),))
            db().run(
                """
                UPDATE lv_gasto
                SET branch_id=?, bolsillo_id=?, bolsillo_nombre=?, clase=?, concepto=?, monto=?, fecha=?, nota=?
                WHERE id=?
                """,
                (
                    limpio["branch_id"],
                    limpio["bolsillo_id"],
                    limpio["bolsillo_nombre"],
                    limpio["clase"],
                    limpio["concepto"],
                    limpio["monto"],
                    limpio["fecha"],
                    limpio["nota"],
                    int(id_registro),
                ),
            )
            if lineas is not None:
                _aplicar_stock(_deltas_stock(anteriores, lineas))
                _guardar_lineas(int(id_registro), lineas)
            auditar(ses["usuario"], "gasto", f"Cambió {limpio['concepto']} por {formato_pesos(limpio['monto'])}")
            return _gasto_publico(db().one("SELECT * FROM lv_gasto WHERE id=?", (int(id_registro),)))
        nuevo = db().run(
            """
            INSERT INTO lv_gasto (
                branch_id, bolsillo_id, bolsillo_nombre, clase, concepto, monto, fecha, nota, usuario, creado_en
            ) VALUES (?,?,?,?,?,?,?,?,?,?)
            """,
            (
                limpio["branch_id"],
                limpio["bolsillo_id"],
                limpio["bolsillo_nombre"],
                limpio["clase"],
                limpio["concepto"],
                limpio["monto"],
                limpio["fecha"],
                limpio["nota"],
                ses["usuario"],
                ahora(),
            ),
        )
        if lineas:
            _aplicar_stock(_deltas_stock([], lineas))
            _guardar_lineas(int(nuevo), lineas)
    auditar(ses["usuario"], "gasto", f"{limpio['clase']} {limpio['concepto']} {formato_pesos(limpio['monto'])}")
    return _gasto_publico(db().one("SELECT * FROM lv_gasto WHERE id=?", (int(nuevo),)))


def quitar_gasto(id_registro: int, ses: dict) -> dict:
    solo_dueno(ses)
    _asegurar_gastos(db())
    fila = db().one("SELECT * FROM lv_gasto WHERE id=?", (int(id_registro),))
    if not fila:
        raise ErrorLavadero("Ese gasto ya no está.")
    fijo = int(ses.get("branch_id") or 0)
    if fijo and int(fila["branch_id"]) != fijo:
        raise ErrorLavadero("Ese gasto es de otra sucursal.")
    lineas = db().all("SELECT * FROM lv_ingreso WHERE gasto_id=?", (int(id_registro),))
    with db().tx():
        if lineas:
            _aplicar_stock(_deltas_stock(lineas, []))
            db().run("DELETE FROM lv_ingreso WHERE gasto_id=?", (int(id_registro),))
        db().run("DELETE FROM lv_gasto WHERE id=?", (int(id_registro),))
    auditar(ses["usuario"], "gasto", f"Quitó {fila['concepto']}")
    return {"ok": True}


def _rango_gastos(preset: str) -> tuple[str, str]:
    nombre = (preset or "hoy").lower()
    if nombre == "todo":
        return "", ""
    if nombre not in {"hoy", "semana", "mes"}:
        nombre = "hoy"
    desde, hasta, _ = _periodo(nombre)
    return desde, hasta


def listar_gastos(branch_id: int, ses: dict, preset: str = "hoy") -> dict:
    solo_dueno(ses)
    _asegurar_gastos(db())
    branch_id = _branch_efectivo(ses, branch_id)
    if not branch_id:
        raise ErrorLavadero("Elige la sucursal.")
    nombre = (preset or "hoy").lower()
    if nombre not in {"hoy", "semana", "mes", "todo"}:
        nombre = "hoy"
    desde, hasta = _rango_gastos(nombre)
    sql = "SELECT * FROM lv_gasto WHERE branch_id=?"
    params: list[Any] = [branch_id]
    if desde:
        sql += " AND fecha>=? AND fecha<=?"
        params.extend([desde, hasta])
    filas = [_gasto_publico(fila) for fila in db().all(sql + " ORDER BY fecha DESC, id DESC", tuple(params))]
    por_bolsillo: dict[int, dict] = {}
    for fila in filas:
        cubo = por_bolsillo.setdefault(
            int(fila["bolsillo_id"]),
            {
                "bolsillo_id": int(fila["bolsillo_id"]),
                "nombre": fila["bolsillo_nombre"],
                "monto": 0,
                "pagos": 0,
                "compras": 0,
            },
        )
        cubo["monto"] += fila["monto"]
        if fila["clase"] == "COMPRA":
            cubo["compras"] += fila["monto"]
        else:
            cubo["pagos"] += fila["monto"]
    return {
        "branch_id": branch_id,
        "preset": nombre,
        "desde": desde,
        "hasta": hasta,
        "total": sum(fila["monto"] for fila in filas),
        "por_bolsillo": list(por_bolsillo.values()),
        "gastos": filas,
    }


def _marcar_gastado(bolsillos: list[dict], branch_id: int, fecha: str) -> None:
    _asegurar_gastos(db())
    if branch_id:
        filas = db().all(
            "SELECT * FROM lv_gasto WHERE branch_id=? AND fecha=? ORDER BY id",
            (int(branch_id), fecha),
        )
    else:
        filas = db().all(
            "SELECT * FROM lv_gasto WHERE fecha=? ORDER BY id",
            (fecha,),
        )
    por_bolsa: dict[int, list[dict]] = {}
    for fila in filas:
        por_bolsa.setdefault(int(fila["bolsillo_id"]), []).append(_gasto_publico(fila))
    for bolsa in bolsillos:
        movimientos = por_bolsa.get(int(bolsa["id"]), [])
        gastado = sum(int(movimiento["monto"]) for movimiento in movimientos)
        bolsa["gastado"] = gastado
        bolsa["queda"] = pesos(bolsa["monto"]) - gastado
        bolsa["movimientos"] = movimientos


def _cfg(clave: str, defecto: str = "") -> str:
    fila = db().one("SELECT valor FROM lv_config WHERE clave=?", (clave,))
    return str(fila["valor"]) if fila and fila.get("valor") is not None else defecto


def _poner_cfg(clave: str, valor: str) -> None:
    existe = db().one("SELECT clave FROM lv_config WHERE clave=?", (clave,))
    if existe:
        db().run("UPDATE lv_config SET valor=? WHERE clave=?", (valor, clave))
    else:
        db().run("INSERT INTO lv_config (clave, valor) VALUES (?, ?)", (clave, valor))


def _tiene_columna(base: BaseDatos, tabla: str, columna: str) -> bool:
    if base.kind == "sqlite":
        return any(fila["name"] == columna for fila in base.all(f"PRAGMA table_info({tabla})"))
    filas = base.all(
        """
        SELECT COUNT(*) AS c FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME=? AND COLUMN_NAME=?
        """,
        (tabla, columna),
    )
    return bool(filas and int(filas[0]["c"] or 0))


def _nombre_propio(valor: Any, etiqueta: str) -> str:
    texto = " ".join(str(valor or "").upper().split())
    limpio = "".join(ch for ch in texto if ch.isalpha() or ch == " ")
    limpio = " ".join(limpio.split())
    if len(limpio) < 2:
        raise ErrorLavadero(f"Escribe {etiqueta} del empleado. Queda en mayúscula.")
    return limpio[:60]


def _sembrar(base: BaseDatos) -> None:
    if base.one("SELECT COUNT(*) AS c FROM lv_sucursal")["c"]:
        return
    base.run(
        "INSERT INTO lv_usuario (usuario, nombre, clave_hash, rol, branch_id, activo) VALUES (?,?,?,?,?,1)",
        ("admin", "Dueño", hash_clave("admin123"), "admin", 0),
    )
    base.run(
        "INSERT INTO lv_usuario (usuario, nombre, clave_hash, rol, branch_id, activo) VALUES (?,?,?,?,?,1)",
        ("recepcion", "Recepción", hash_clave("1234"), "vendedor", 1),
    )
    base.run(
        "INSERT INTO lv_sucursal (nombre, telefono, direccion, activo) VALUES (?,?,?,1)",
        ("Sucursal Principal", "3103257331", "",),
    )
    id_principal = base.one("SELECT id FROM lv_sucursal WHERE nombre=?", ("Sucursal Principal",))["id"]
    base.run(
        "INSERT INTO lv_sucursal (nombre, telefono, direccion, activo) VALUES (?,?,?,1)",
        ("Sucursal 2", "3103257331", "",),
    )
    id_dos = base.one("SELECT id FROM lv_sucursal WHERE nombre=?", ("Sucursal 2",))["id"]
    base.run(
        "INSERT INTO lv_zona (branch_id, nombre, tipo, activo) VALUES (?,?,?,1)",
        (id_principal, "Carros", "CARROS"),
    )
    base.run(
        "INSERT INTO lv_zona (branch_id, nombre, tipo, activo) VALUES (?,?,?,1)",
        (id_principal, "Motos", "MOTOS"),
    )
    zona_carros = base.one("SELECT id FROM lv_zona WHERE nombre=? AND branch_id=?", ("Carros", id_principal))["id"]
    zona_motos = base.one("SELECT id FROM lv_zona WHERE nombre=? AND branch_id=?", ("Motos", id_principal))["id"]
    tipos = [
        (zona_carros, "Automóvil", "AUTOMOVIL", "🚗", 1),
        (zona_carros, "Camioneta", "CAMIONETA", "🚙", 2),
        (zona_motos, "Moto", "MOTO", "🛵", 1),
    ]
    for zona_id, nombre, codigo, icono, orden in tipos:
        base.run(
            "INSERT INTO lv_tipo (zona_id, nombre, codigo, icono, orden, activo) VALUES (?,?,?,?,?,1)",
            (zona_id, nombre, codigo, icono, orden),
        )
    codigos = {
        fila["codigo"] + "@" + str(fila["zona_id"]): fila["id"]
        for fila in base.all("SELECT id, zona_id, codigo FROM lv_tipo")
    }

    def precio(zona_id: int, codigo: str) -> int:
        return int(codigos[f"{codigo}@{zona_id}"])

    carros = [
        ("Cerámico coating", "Premium", "✨", "", [("AUTOMOVIL", 500000), ("CAMIONETA", 600000)]),
        ("Porcelanizado de pintura", "Premium", "💎", "", [("AUTOMOVIL", 300000), ("CAMIONETA", 400000)]),
        ("Cera hidrofóbica", "Premium", "💧", "", [("AUTOMOVIL", 150000), ("CAMIONETA", 200000)]),
        ("Polichado microrayón", "Premium", "🌀", "", [("AUTOMOVIL", 200000), ("CAMIONETA", 250000)]),
        ("Polichado americano", "Premium", "🇺🇸", "", [("AUTOMOVIL", 150000), ("CAMIONETA", 200000)]),
        ("Polichado manual", "Especial", "✋", "", [("AUTOMOVIL", 100000), ("CAMIONETA", 120000)]),
        ("Encerado manual", "Especial", "🕯️", "", [("AUTOMOVIL", 70000), ("CAMIONETA", 80000)]),
        ("Shampoo pH neutro", "Basico", "🧴", "", [("AUTOMOVIL", 50000), ("CAMIONETA", 60000)]),
        ("Limpieza e hidratación mate interior", "Especial", "🪑", "", [("AUTOMOVIL", 50000), ("CAMIONETA", 60000)]),
        ("Protección contra rayos UV", "Basico", "☀️", "", [("AUTOMOVIL", 20000), ("CAMIONETA", 40000)]),
        ("Lavado de tapicería a vapor", "Especial", "♨️", "", [("AUTOMOVIL", 250000), ("CAMIONETA", 300000)]),
        ("Lavado de cojinería a vapor", "Especial", "🧽", "", [("AUTOMOVIL", 150000), ("CAMIONETA", 200000)]),
        ("Eliminación de olores en ductos", "Basico", "💨", "", [("AUTOMOVIL", 30000), ("CAMIONETA", 50000)]),
        ("Desmanchado de vinilos", "Basico", "✨", "", [("AUTOMOVIL", 30000), ("CAMIONETA", 40000)]),
        ("Descontaminante y desempañador de vidrios", "Basico", "🪟", "", [("AUTOMOVIL", 50000), ("CAMIONETA", 60000)]),
        ("Restauración de rines", "Especial", "⚙️", "", [("AUTOMOVIL", 100000), ("CAMIONETA", 130000)]),
        ("Desinfección amonio cuaternario", "Basico", "🛡️", "", [("AUTOMOVIL", 20000), ("CAMIONETA", 40000)]),
        ("Lavado completo", "Basico", "🚿", "", [("AUTOMOVIL", 50000), ("CAMIONETA", 60000)]),
        ("Lavado básico", "Basico", "🚗", "", [("AUTOMOVIL", 25000), ("CAMIONETA", 30000)]),
    ]
    motos = [
        ("Lavado básico", "Basico", "🚿", "", [("MOTO", 15000)]),
        ("Desmanchado", "Basico", "✨", "", [("MOTO", 30000)]),
        ("Pulido a máquina", "Especial", "🌀", "", [("MOTO", 40000)]),
        ("Hidratación cuero y partes negras", "Especial", "🖤", "", [("MOTO", 20000)]),
        ("Desengrase de motor y cadena", "Especial", "⛓️", "", [("MOTO", 50000)]),
        ("Descontaminación de pintura", "Especial", "🧪", "", [("MOTO", 30000)]),
        ("Porcelanizado de pintura", "Premium", "💎", "", [("MOTO", 30000)]),
        ("Blanqueamiento de faros", "Especial", "💡", "", [("MOTO", 30000)]),
        ("Proceso hidrofóbico", "Premium", "💧", "Dura 3 meses", [("MOTO", 60000)]),
        ("Proceso cerámico", "Premium", "✨", "Dura 1 año", [("MOTO", 120000)]),
    ]

    def meter_servicios(zona_id: int, lista: list) -> None:
        for nombre, grupo, icono, duracion, precios in lista:
            base.run(
                "INSERT INTO lv_servicio (zona_id, nombre, grupo, icono, duracion, activo) VALUES (?,?,?,?,?,1)",
                (zona_id, nombre, grupo, icono, duracion),
            )
            servicio_id = base.one(
                "SELECT id FROM lv_servicio WHERE zona_id=? AND nombre=? ORDER BY id DESC LIMIT 1",
                (zona_id, nombre),
            )["id"]
            for codigo, valor in precios:
                base.run(
                    "INSERT INTO lv_precio (servicio_id, tipo_id, precio) VALUES (?,?,?)",
                    (servicio_id, precio(zona_id, codigo), int(valor)),
                )

    meter_servicios(zona_carros, carros)
    meter_servicios(zona_motos, motos)
    for grupo, porcentaje in (("Basico", 40), ("Especial", 30), ("Premium", 20)):
        base.run(
            "INSERT INTO lv_regla (empleado_id, servicio_id, grupo, porcentaje, activo) VALUES (0,0,?,?,1)",
            (grupo, porcentaje),
        )
    for nombre, precio_venta, costo in (
        ("Cera líquida", 25000, 12000),
        ("Paño de microfibra", 8000, 3000),
        ("Ambientador", 12000, 5000),
    ):
        base.run(
            "INSERT INTO lv_producto (nombre, precio, costo, stock, origen_id, activo) VALUES (?,?,?,?,0,1)",
            (nombre, precio_venta, costo, 20),
        )
    for orden, nombre in ((1, "Efectivo"), (2, "Nequi"), (3, "Datáfono")):
        base.run(
            "INSERT INTO lv_medio (nombre, orden, activo) VALUES (?,?,1)",
            (nombre, orden),
        )
    for branch_id in (id_principal, id_dos):
        base.run(
            "INSERT INTO lv_reparto (branch_id, zona_id, modo, valor) VALUES (?,?,?,?)",
            (branch_id, 0, "PORCENTAJE", 10),
        )
    textos = {
        "negocio_nombre": "CAR WASH DETAILING",
        "negocio_linea": "S.O.P. soluciones operativas",
        "negocio_telefono": "3103257331",
        "whatsapp_dueno": "3103257331",
        "whatsapp_plantilla": (
            "Hola, te escribe {negocio}. Tu {vehiculo} {placa} ya está listo en {sucursal}. "
            "Te esperamos. {telefono}"
        ),
    }
    for clave, valor in textos.items():
        base.run("INSERT INTO lv_config (clave, valor) VALUES (?, ?)", (clave, valor))
    base.run(
        "INSERT INTO lv_auditoria (usuario, fecha, accion, detalle) VALUES (?,?,?,?)",
        ("sistema", ahora(), "inicio", "Catálogo inicial del lavadero"),
    )


def auditar(usuario: str, accion: str, detalle: str) -> None:
    db().run(
        "INSERT INTO lv_auditoria (usuario, fecha, accion, detalle) VALUES (?,?,?,?)",
        ((usuario or "")[:80], ahora(), accion[:80], (detalle or "")[:250]),
    )


def negocio() -> dict:
    return {
        "nombre": _cfg("negocio_nombre", "CAR WASH DETAILING"),
        "linea": _cfg("negocio_linea", "S.O.P. soluciones operativas"),
        "telefono": _cfg("negocio_telefono", "3103257331"),
        "whatsapp_dueno": _cfg("whatsapp_dueno", "3103257331"),
        "whatsapp_plantilla": _cfg(
            "whatsapp_plantilla",
            "Hola, te escribe {negocio}. Tu {vehiculo} {placa} ya está listo en {sucursal}. Te esperamos. {telefono}",
        ),
        "smtp_host": _cfg("smtp_host"),
        "smtp_port": _cfg("smtp_port", "587"),
        "smtp_usuario": _cfg("smtp_usuario"),
        "smtp_desde": _cfg("smtp_desde"),
        "smtp_listo": bool(_cfg("smtp_host") and _cfg("smtp_desde") and _cfg("smtp_clave")),
    }


def _activo_sql(alias: str = "") -> str:
    prefijo = f"{alias}." if alias else ""
    return f"{prefijo}activo=1"


def catalogo(branch_id: int = 0, completo: bool = True) -> dict:
    sucursales = db().all("SELECT * FROM lv_sucursal ORDER BY id")
    zonas = db().all("SELECT * FROM lv_zona ORDER BY id")
    tipos = db().all("SELECT * FROM lv_tipo ORDER BY orden, id")
    servicios = db().all("SELECT * FROM lv_servicio ORDER BY grupo, nombre")
    precios = db().all("SELECT * FROM lv_precio")
    por_servicio: dict[int, dict] = {}
    for precio in precios:
        por_servicio.setdefault(int(precio["servicio_id"]), {})[int(precio["tipo_id"])] = pesos(precio["precio"])
    for servicio in servicios:
        servicio["precios"] = por_servicio.get(int(servicio["id"]), {})
    datos = {
        "negocio": negocio(),
        "sucursales": sucursales,
        "zonas": zonas,
        "tipos": tipos,
        "servicios": servicios,
        "productos": db().all("SELECT * FROM lv_producto ORDER BY nombre"),
        "empleados": db().all("SELECT * FROM lv_empleado ORDER BY nombre"),
        "medios": db().all("SELECT * FROM lv_medio ORDER BY orden, id"),
        "reglas": db().all("SELECT * FROM lv_regla ORDER BY id"),
        "reparto": db().all("SELECT * FROM lv_reparto ORDER BY id"),
        "usuarios": db().all(
            "SELECT id, usuario, nombre, rol, branch_id, activo, correo FROM lv_usuario ORDER BY id"
        ),
        "revision": list(REVISION_VEHICULO),
        "bolsillos": listar_bolsillos(),
        "branch_id": branch_id,
    }
    if completo:
        return datos
    datos["negocio"] = {
        clave: valor
        for clave, valor in datos["negocio"].items()
        if clave not in {"whatsapp_dueno", "smtp_host", "smtp_port", "smtp_usuario", "smtp_desde", "smtp_listo"}
    }
    datos["productos"] = [{clave: valor for clave, valor in fila.items() if clave != "costo"} for fila in datos["productos"]]
    datos["empleados"] = [
        {clave: valor for clave, valor in fila.items() if clave != "telefono"} for fila in datos["empleados"]
    ]
    datos["reglas"] = []
    datos["reparto"] = []
    datos["usuarios"] = []
    datos["bolsillos"] = []
    return datos


def _exigir_texto(valor: Any, etiqueta: str) -> str:
    texto = str(valor or "").strip()
    if not texto:
        raise ErrorLavadero(f"Escribe el {etiqueta}.")
    return texto[:120]


def _entero(valor: Any, etiqueta: str, minimo: int = 0, maximo: int = 100000000) -> int:
    try:
        numero = int(round(float(valor)))
    except (TypeError, ValueError):
        raise ErrorLavadero(f"{etiqueta} no es un número.")
    if numero < minimo or numero > maximo:
        raise ErrorLavadero(f"{etiqueta} está fuera de rango.")
    return numero


CAMPOS = {
    "sucursal": ("lv_sucursal", ["nombre", "telefono", "direccion", "activo"]),
    "zona": ("lv_zona", ["branch_id", "nombre", "tipo", "activo"]),
    "tipo": ("lv_tipo", ["zona_id", "nombre", "codigo", "icono", "orden", "activo"]),
    "servicio": ("lv_servicio", ["zona_id", "nombre", "grupo", "icono", "duracion", "activo"]),
    "producto": ("lv_producto", ["nombre", "precio", "costo", "stock", "activo"]),
    "empleado": ("lv_empleado", ["nombre", "apellido", "telefono", "activo"]),
    "medio": ("lv_medio", ["nombre", "orden", "activo"]),
    "regla": ("lv_regla", ["empleado_id", "servicio_id", "grupo", "porcentaje", "activo"]),
    "reparto": ("lv_reparto", ["branch_id", "zona_id", "modo", "valor"]),
    "usuario": ("lv_usuario", ["usuario", "nombre", "rol", "branch_id", "activo", "correo"]),
}


def _limpiar(entidad: str, datos: dict, parcial: bool = False) -> dict:
    _, permitidos = CAMPOS[entidad]
    limpio: dict[str, Any] = {}
    for campo in permitidos:
        if parcial and campo not in datos:
            continue
        valor = datos.get(campo)
        if campo in {"nombre", "apellido", "usuario", "telefono", "direccion", "codigo", "icono", "duracion", "grupo", "tipo", "modo", "rol", "correo"}:
            limpio[campo] = str(valor or "").strip()[:120]
        elif campo == "activo":
            if valor is None or valor == "":
                limpio[campo] = 1
            else:
                limpio[campo] = 1 if valor in {1, True, "1", "true"} else 0
        elif campo in {"branch_id", "zona_id", "orden", "precio", "costo", "stock", "empleado_id", "servicio_id", "porcentaje", "valor"}:
            limpio[campo] = pesos(valor)
        else:
            limpio[campo] = valor
    if not parcial:
        if entidad in {"sucursal", "zona", "tipo", "servicio", "producto", "empleado", "medio"} and not limpio.get("nombre"):
            raise ErrorLavadero("El nombre es obligatorio.")
        if entidad == "usuario" and not limpio.get("usuario"):
            raise ErrorLavadero("El usuario es obligatorio.")
        if entidad == "zona" and not limpio.get("branch_id"):
            raise ErrorLavadero("Elige la sucursal de la zona.")
        if entidad == "tipo" and not limpio.get("zona_id"):
            raise ErrorLavadero("Elige la zona del vehículo.")
        if entidad == "servicio" and not limpio.get("zona_id"):
            raise ErrorLavadero("Elige la zona del servicio.")
        if entidad == "zona" and not limpio.get("tipo"):
            limpio["tipo"] = "MIXTA"
        if entidad == "servicio" and not limpio.get("grupo"):
            limpio["grupo"] = "Basico"
        if entidad == "servicio" and not limpio.get("icono"):
            limpio["icono"] = "🚿"
        if entidad == "tipo" and not limpio.get("icono"):
            limpio["icono"] = "🚗"
        if entidad == "producto" and pesos(limpio.get("precio")) <= 0:
            raise ErrorLavadero("Pon el precio de venta.")
        if entidad == "empleado":
            limpio["nombre"] = _nombre_propio(datos.get("nombre"), "el nombre")
            limpio["apellido"] = _nombre_propio(datos.get("apellido"), "el apellido")
            limpio["telefono"] = _telefono(datos.get("telefono"))[:10]
        if entidad == "regla":
            limpio["porcentaje"] = _entero(limpio.get("porcentaje"), "El porcentaje", 0, 100)
        if entidad == "reparto":
            modo = (limpio.get("modo") or "PORCENTAJE").upper()
            if modo not in {"PORCENTAJE", "FIJO_DIARIO"}:
                raise ErrorLavadero("El gasto se aparta en porcentaje o en un valor fijo del día.")
            limpio["modo"] = modo
            if modo == "PORCENTAJE":
                limpio["valor"] = _entero(limpio.get("valor"), "El porcentaje de gastos", 0, 100)
    if "porcentaje" in limpio:
        limpio["porcentaje"] = _entero(limpio["porcentaje"], "El porcentaje", 0, 100)
    if entidad == "usuario" and limpio.get("rol"):
        if limpio["rol"] == "cajero":
            limpio["rol"] = "vendedor"
        if limpio["rol"] not in {"admin", "vendedor"}:
            raise ErrorLavadero("El rol es administrador o vendedor.")
    return limpio


_CORREO = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _normalizar_correo(valor: Any, obligatorio: bool = False) -> str:
    texto = str(valor or "").strip().lower()
    if not texto:
        if obligatorio:
            raise ErrorLavadero("Escribe el correo del usuario.")
        return ""
    if len(texto) > 120 or not _CORREO.fullmatch(texto):
        raise ErrorLavadero("Escribe el correo bien, con @ y el dominio.")
    return texto


def _correo_de_usuario(datos: dict, id_registro: int) -> str:
    escrito = _normalizar_correo(datos.get("correo"))
    confirma = _normalizar_correo(datos.get("correo_confirma"))
    guardado = ""
    if id_registro:
        fila = db().one("SELECT correo FROM lv_usuario WHERE id=?", (int(id_registro),))
        guardado = _normalizar_correo((fila or {}).get("correo"))
    if not id_registro or not guardado or escrito != guardado:
        if not escrito:
            raise ErrorLavadero("Escribe el correo del usuario.")
        if escrito != confirma:
            raise ErrorLavadero("Escribe el correo dos veces, igual. No lo copies: los dos pueden quedar mal.")
        return escrito
    return guardado


def guardar_entidad(entidad: str, datos: dict, id_registro: int = 0, usuario: str = "") -> dict:
    if entidad not in CAMPOS:
        raise ErrorLavadero("Eso no se puede editar.")
    tabla, _ = CAMPOS[entidad]
    limpio = _limpiar(entidad, datos, parcial=False)
    if entidad == "usuario":
        clave = str(datos.get("clave") or "").strip()
        if not id_registro and len(clave) < 4:
            raise ErrorLavadero("La clave necesita al menos 4 caracteres.")
        repetido = db().one("SELECT id FROM lv_usuario WHERE lower(usuario)=lower(?)", (limpio["usuario"],))
        if repetido and int(repetido["id"]) != int(id_registro or 0):
            raise ErrorLavadero("Ese usuario ya existe.")
        limpio["correo"] = _correo_de_usuario(datos, int(id_registro or 0))
        otro = db().one(
            "SELECT id FROM lv_usuario WHERE lower(correo)=lower(?) AND correo<>''",
            (limpio["correo"],),
        )
        if otro and int(otro["id"]) != int(id_registro or 0):
            raise ErrorLavadero("Ese correo ya está en otro usuario.")
    if id_registro:
        sets = ", ".join(f"{campo}=?" for campo in limpio)
        db().run(
            f"UPDATE {tabla} SET {sets} WHERE id=?",
            tuple(limpio.values()) + (int(id_registro),),
        )
        nuevo_id = int(id_registro)
        accion = "actualizar"
    else:
        columnas = ", ".join(limpio.keys())
        marcas = ", ".join("?" for _ in limpio)
        if entidad == "usuario":
            columnas += ", clave_hash"
            marcas += ", ?"
            valores = tuple(limpio.values()) + (hash_clave(str(datos.get("clave"))),)
        else:
            valores = tuple(limpio.values())
        nuevo_id = db().run(f"INSERT INTO {tabla} ({columnas}) VALUES ({marcas})", valores)
        accion = "crear"
    if entidad == "usuario" and datos.get("clave") and id_registro:
        db().run(
            "UPDATE lv_usuario SET clave_hash=? WHERE id=?",
            (hash_clave(str(datos["clave"])), int(id_registro)),
        )
    if entidad == "servicio":
        _guardar_precios(nuevo_id, datos.get("precios") or {})
    if entidad == "zona" and datos.get("copiar_de"):
        copiar_zona(nuevo_id, int(datos["copiar_de"]))
    auditar(usuario, accion, f"{entidad} #{nuevo_id} {limpio.get('nombre') or limpio.get('usuario') or ''}")
    return {"ok": True, "id": nuevo_id}


def _guardar_precios(servicio_id: int, precios: dict) -> None:
    if not isinstance(precios, dict):
        raise ErrorLavadero("Los precios van por tipo de vehículo.")
    db().run("DELETE FROM lv_precio WHERE servicio_id=?", (int(servicio_id),))
    for tipo_id, valor in precios.items():
        monto = pesos(valor)
        if monto <= 0:
            continue
        db().run(
            "INSERT INTO lv_precio (servicio_id, tipo_id, precio) VALUES (?,?,?)",
            (int(servicio_id), int(tipo_id), monto),
        )


def copiar_zona(destino_id: int, origen_id: int) -> dict:
    destino = db().one("SELECT * FROM lv_zona WHERE id=?", (int(destino_id),))
    origen = db().one("SELECT * FROM lv_zona WHERE id=?", (int(origen_id),))
    if not destino or not origen:
        raise ErrorLavadero("No encontré la zona.")
    if int(destino_id) == int(origen_id):
        raise ErrorLavadero("Elige otra zona de origen.")
    ya = db().one("SELECT COUNT(*) AS c FROM lv_servicio WHERE zona_id=?", (int(destino_id),))["c"]
    if int(ya or 0):
        raise ErrorLavadero("Esa zona ya tiene servicios.")
    tipos_origen = db().all("SELECT * FROM lv_tipo WHERE zona_id=? AND activo=1", (int(origen_id),))
    mapa: dict[int, int] = {}
    for tipo in tipos_origen:
        existe = db().one(
            "SELECT id FROM lv_tipo WHERE zona_id=? AND codigo=?",
            (int(destino_id), tipo["codigo"]),
        )
        if existe:
            mapa[int(tipo["id"])] = int(existe["id"])
            continue
        nuevo = db().run(
            "INSERT INTO lv_tipo (zona_id, nombre, codigo, icono, orden, activo) VALUES (?,?,?,?,?,1)",
            (int(destino_id), tipo["nombre"], tipo["codigo"], tipo["icono"], tipo["orden"]),
        )
        mapa[int(tipo["id"])] = int(nuevo)
    servicios = db().all("SELECT * FROM lv_servicio WHERE zona_id=? AND activo=1", (int(origen_id),))
    for servicio in servicios:
        nuevo_servicio = db().run(
            "INSERT INTO lv_servicio (zona_id, nombre, grupo, icono, duracion, activo) VALUES (?,?,?,?,?,1)",
            (int(destino_id), servicio["nombre"], servicio["grupo"], servicio["icono"], servicio["duracion"]),
        )
        precios = db().all("SELECT * FROM lv_precio WHERE servicio_id=?", (servicio["id"],))
        for precio in precios:
            tipo_nuevo = mapa.get(int(precio["tipo_id"]))
            if not tipo_nuevo:
                continue
            db().run(
                "INSERT INTO lv_precio (servicio_id, tipo_id, precio) VALUES (?,?,?)",
                (int(nuevo_servicio), int(tipo_nuevo), pesos(precio["precio"])),
            )
    return {"ok": True, "servicios": len(servicios)}


USO = {
    "sucursal": "SELECT COUNT(*) AS c FROM lv_orden WHERE branch_id=?",
    "zona": "SELECT COUNT(*) AS c FROM lv_orden WHERE zona_id=?",
    "tipo": "SELECT COUNT(*) AS c FROM lv_orden WHERE tipo_id=?",
    "servicio": "SELECT COUNT(*) AS c FROM lv_item WHERE servicio_id=?",
    "producto": "SELECT COUNT(*) AS c FROM lv_item WHERE producto_id=?",
    "empleado": "SELECT COUNT(*) AS c FROM lv_colab WHERE empleado_id=?",
    "medio": "SELECT COUNT(*) AS c FROM lv_pago WHERE medio=(SELECT nombre FROM lv_medio WHERE id=?)",
    "regla": None,
    "reparto": None,
    "usuario": None,
}


def quitar_entidad(entidad: str, id_registro: int, usuario: str = "") -> dict:
    if entidad not in CAMPOS:
        raise ErrorLavadero("Eso no se puede quitar.")
    tabla, _ = CAMPOS[entidad]
    fila = db().one(f"SELECT * FROM {tabla} WHERE id=?", (int(id_registro),))
    if not fila:
        raise ErrorLavadero("No encontré el registro.", 404)
    if entidad == "usuario" and fila.get("usuario") == usuario:
        raise ErrorLavadero("No puedes quitarte a ti mismo.")
    if entidad == "usuario" and fila.get("rol") == "admin":
        otros = db().one(
            "SELECT COUNT(*) AS c FROM lv_usuario WHERE rol='admin' AND activo=1 AND id<>?",
            (int(id_registro),),
        )["c"]
        if int(otros or 0) == 0:
            raise ErrorLavadero("Tiene que quedar al menos un administrador activo.")
    consulta = USO.get(entidad)
    usado = 0
    if consulta:
        usado = int(db().one(consulta, (int(id_registro),))["c"] or 0)
    if usado or entidad == "usuario":
        columna = "activo"
        db().run(f"UPDATE {tabla} SET {columna}=0 WHERE id=?", (int(id_registro),))
        modo = "apagado"
    else:
        if entidad == "servicio":
            db().run("DELETE FROM lv_precio WHERE servicio_id=?", (int(id_registro),))
        db().run(f"DELETE FROM {tabla} WHERE id=?", (int(id_registro),))
        modo = "borrado"
    auditar(usuario, modo, f"{entidad} #{id_registro}")
    return {"ok": True, "modo": modo}


def guardar_config(datos: dict, usuario: str) -> dict:
    permitidas = {
        "negocio_nombre",
        "negocio_linea",
        "negocio_telefono",
        "whatsapp_dueno",
        "whatsapp_plantilla",
        "smtp_host",
        "smtp_port",
        "smtp_usuario",
        "smtp_clave",
        "smtp_desde",
    }
    for clave, valor in datos.items():
        if clave not in permitidas:
            continue
        texto = str(valor or "").strip()
        if clave == "smtp_clave" and not texto:
            continue
        if clave == "smtp_port":
            texto = str(_entero(texto or "587", "El puerto del correo", 1, 65535))
        if clave == "smtp_desde" and texto:
            texto = _normalizar_correo(texto, obligatorio=True)
        _poner_cfg(clave, texto[:500])
    auditar(usuario, "config", "Datos del negocio")
    return negocio()


def _enviar_correo(destino: str, asunto: str, texto: str) -> None:
    host = _cfg("smtp_host").strip()
    desde = _cfg("smtp_desde").strip()
    usuario = _cfg("smtp_usuario").strip()
    clave = _cfg("smtp_clave")
    puerto = int(_cfg("smtp_port") or "587")
    if not host or not desde:
        raise ErrorLavadero("Falta configurar el correo del negocio en Ajustes, Mi negocio.")
    mensaje = EmailMessage()
    mensaje["Subject"] = asunto
    mensaje["From"] = desde
    mensaje["To"] = destino
    mensaje.set_content(texto)
    try:
        with smtplib.SMTP(host, puerto, timeout=20) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.ehlo()
            if usuario and clave:
                smtp.login(usuario, clave)
            smtp.send_message(mensaje)
    except ErrorLavadero:
        raise
    except Exception:
        traceback.print_exc()
        raise ErrorLavadero("No pude enviar el correo. Revisa el servidor, el usuario y la clave en Ajustes.")


def pedir_recupero(dato: str, base_url: str) -> dict:
    asegurar()
    busqueda = str(dato or "").strip()
    if not busqueda:
        raise ErrorLavadero("Escribe el usuario o el correo.")
    fila = db().one(
        "SELECT * FROM lv_usuario WHERE lower(usuario)=lower(?) AND activo=1",
        (busqueda,),
    )
    if not fila and "@" in busqueda:
        fila = db().one(
            "SELECT * FROM lv_usuario WHERE lower(correo)=lower(?) AND activo=1",
            (busqueda,),
        )
    aviso = {"ok": True, "mensaje": "Si ese usuario tiene correo, le llega un mensaje para cambiar la clave."}
    correo = _normalizar_correo((fila or {}).get("correo"))
    if not fila or not correo:
        return aviso
    token = secrets.token_urlsafe(32)
    vence = (datetime.now(BOGOTA) + timedelta(minutes=30)).strftime("%Y-%m-%d %H:%M:%S")
    db().run(
        "INSERT INTO lv_recupero (usuario_id, token_hash, vence_en, usado) VALUES (?,?,?,0)",
        (int(fila["id"]), hash_clave(token), vence),
    )
    enlace = f"{base_url.rstrip('/')}/lavadero?recuperar={token}"
    nombre = negocio()["nombre"]
    _enviar_correo(
        correo,
        f"Cambia tu clave de {nombre}",
        (
            f"Hola {fila['nombre']}.\n\n"
            f"Alguien pidió cambiar la clave de {fila['usuario']} en {nombre}.\n\n"
            "Entra en este enlace y escribe la clave nueva. Sirve por 30 minutos:\n"
            f"{enlace}\n\n"
            "Si no fuiste tú, ignora este mensaje."
        ),
    )
    return aviso


def aplicar_recupero(token: str, nueva: str, repite: str) -> dict:
    asegurar()
    limpio = str(token or "").strip()
    if not limpio:
        raise ErrorLavadero("El enlace para cambiar la clave no sirve.")
    if nueva.strip() != repite.strip():
        raise ErrorLavadero("Escribe la clave nueva dos veces, igual.")
    if len(nueva.strip()) < 4:
        raise ErrorLavadero("La clave nueva necesita al menos 4 caracteres.")
    fila = db().one(
        "SELECT * FROM lv_recupero WHERE token_hash=? AND usado=0 ORDER BY id DESC LIMIT 1",
        (hash_clave(limpio),),
    )
    if not fila or str(fila["vence_en"]) < ahora():
        raise ErrorLavadero("Ese enlace ya venció. Pide otro desde Olvidé mi clave.")
    db().run("UPDATE lv_usuario SET clave_hash=? WHERE id=?", (hash_clave(nueva.strip()), int(fila["usuario_id"])))
    db().run("UPDATE lv_recupero SET usado=1 WHERE usuario_id=?", (int(fila["usuario_id"]),))
    auditar("recupero", "clave", f"Usuario #{fila['usuario_id']} cambió la clave por correo")
    return {"ok": True}


def cambiar_clave(ses: dict, actual: str, nueva: str) -> dict:
    fila = db().one("SELECT * FROM lv_usuario WHERE usuario=?", (ses["usuario"],))
    if not fila or fila["clave_hash"] != hash_clave(actual):
        raise ErrorLavadero("La clave actual no coincide.")
    if len(nueva.strip()) < 4:
        raise ErrorLavadero("La clave nueva necesita al menos 4 caracteres.")
    db().run("UPDATE lv_usuario SET clave_hash=? WHERE id=?", (hash_clave(nueva.strip()), fila["id"]))
    auditar(ses["usuario"], "clave", "Cambió su clave")
    return {"ok": True}


def entrar(usuario: str, clave: str) -> dict:
    asegurar()
    fila = db().one(
        "SELECT * FROM lv_usuario WHERE lower(usuario)=lower(?) AND activo=1",
        (usuario.strip(),),
    )
    if fila and fila["clave_hash"] == hash_clave(clave):
        token = hacer_token(fila["usuario"], fila["rol"], fila["nombre"], int(fila["branch_id"] or 0))
        return {
            "token": token,
            "usuario": fila["usuario"],
            "nombre": fila["nombre"],
            "rol": fila["rol"],
            "branch_id": int(fila["branch_id"] or 0),
        }
    remoto = _entrar_admin_mysql(usuario.strip(), clave)
    if remoto:
        return remoto
    raise ErrorLavadero("Usuario o clave incorrectos.", 401)


def _entrar_admin_mysql(usuario: str, clave: str) -> Optional[dict]:
    if not usuario or not clave:
        return None
    try:
        from main import query

        filas = query(
            """
            SELECT usuario, Nombre
            FROM admin
            WHERE LOWER(usuario)=LOWER(%s) AND BINARY contrasena=%s
            """,
            (usuario, clave),
        )
    except Exception:
        return None
    if not filas:
        return None
    nombre = filas[0].get("Nombre") or usuario
    return {
        "token": hacer_token(usuario, "admin", nombre, 0),
        "usuario": usuario,
        "nombre": nombre,
        "rol": "admin",
        "branch_id": 0,
    }


def sesion_de(request: Request) -> dict:
    encabezado = request.headers.get("authorization") or ""
    token = encabezado[7:].strip() if encabezado.lower().startswith("bearer ") else ""
    data = leer_token(token)
    if not data:
        raise HTTPException(401, "Inicia sesión de nuevo.")
    return data


def solo_dueno(ses: dict) -> None:
    if ses.get("rol") != "admin":
        raise ErrorLavadero("Solo el administrador puede entrar aquí.", 403)


def _branch_efectivo(ses: dict, branch_id: int) -> int:
    fijo = int(ses.get("branch_id") or 0)
    if fijo:
        return fijo
    return int(branch_id or 0)


def porcentaje_comision(empleado_id: int, servicio_id: int, grupo: str) -> int:
    fila = db().one(
        """
        SELECT porcentaje FROM lv_regla
        WHERE activo=1 AND (
            (empleado_id=? AND servicio_id=? AND servicio_id<>0)
            OR (empleado_id=0 AND servicio_id=? AND servicio_id<>0)
            OR (empleado_id=0 AND servicio_id=0 AND grupo=? AND grupo<>'')
        )
        ORDER BY CASE
            WHEN empleado_id<>0 AND servicio_id<>0 THEN 1
            WHEN servicio_id<>0 THEN 2
            ELSE 3
        END, id DESC
        LIMIT 1
        """,
        (int(empleado_id), int(servicio_id), int(servicio_id), grupo or ""),
    )
    return int(fila["porcentaje"]) if fila else 0


def _orden_completa(orden_id: int) -> dict:
    orden = db().one("SELECT * FROM lv_orden WHERE id=?", (int(orden_id),))
    if not orden:
        raise ErrorLavadero("No encontré la orden.", 404)
    orden["items"] = db().all("SELECT * FROM lv_item WHERE orden_id=? ORDER BY id", (int(orden_id),))
    cols = db().all(
        """
        SELECT c.orden_id, c.empleado_id, c.peso, e.nombre, e.apellido
        FROM lv_colab c JOIN lv_empleado e ON e.id=c.empleado_id
        WHERE c.orden_id=?
        """,
        (int(orden_id),),
    )
    for col in cols:
        col["empleado"] = " ".join(
            parte for parte in (str(col.get("nombre") or "").strip(), str(col.get("apellido") or "").strip()) if parte
        )
    orden["colaboradores"] = cols
    sucursal = db().one("SELECT nombre FROM lv_sucursal WHERE id=?", (orden["branch_id"],))
    zona = db().one("SELECT nombre, tipo FROM lv_zona WHERE id=?", (orden["zona_id"],)) if orden["zona_id"] else None
    tipo = db().one("SELECT nombre, icono FROM lv_tipo WHERE id=?", (orden["tipo_id"],)) if orden["tipo_id"] else None
    orden["sucursal"] = sucursal["nombre"] if sucursal else ""
    orden["zona"] = zona["nombre"] if zona else "Productos"
    orden["zona_tipo"] = zona["tipo"] if zona else "PRODUCTOS"
    orden["vehiculo"] = tipo["nombre"] if tipo else "Producto"
    orden["icono"] = tipo["icono"] if tipo else "🛍️"
    orden["checklist"] = _leer_revision(orden.get("checklist"))
    orden["nota"] = _nota_vehiculo(orden.get("nota"))
    return orden


def _leer_revision(valor: Any) -> list[str]:
    if isinstance(valor, list):
        crudo = valor
    else:
        try:
            crudo = json.loads(valor or "[]")
        except (TypeError, ValueError):
            crudo = []
    if not isinstance(crudo, list):
        return []
    permitidos = set(REVISION_VEHICULO)
    salida: list[str] = []
    for item in crudo:
        texto = str(item or "").strip()
        if texto in permitidos and texto not in salida:
            salida.append(texto)
    return salida


def _nota_vehiculo(valor: Any) -> str:
    lineas = []
    for linea in str(valor or "").replace("\r", "").split("\n"):
        limpia = " ".join(linea.split())
        if limpia:
            lineas.append(limpia)
    return "\n".join(lineas)[:240]


def crear_orden(datos: dict, ses: dict) -> dict:
    branch_id = _branch_efectivo(ses, int(datos.get("branch_id") or 0))
    if not branch_id:
        raise ErrorLavadero("Elige la sucursal.")
    sucursal = db().one("SELECT * FROM lv_sucursal WHERE id=? AND activo=1", (branch_id,))
    if not sucursal:
        raise ErrorLavadero("Esa sucursal no está activa.")
    zona_id = int(datos.get("zona_id") or 0)
    tipo_id = int(datos.get("tipo_id") or 0)
    zona = db().one("SELECT * FROM lv_zona WHERE id=? AND activo=1", (zona_id,)) if zona_id else None
    if not zona or int(zona["branch_id"]) != int(branch_id):
        raise ErrorLavadero("Elige la zona.")
    tipo = db().one("SELECT * FROM lv_tipo WHERE id=? AND activo=1", (tipo_id,)) if tipo_id else None
    if not tipo or int(tipo["zona_id"]) != int(zona_id):
        raise ErrorLavadero("Elige el tipo de vehículo.")
    servicios = [int(x) for x in (datos.get("servicios") or [])]
    productos = datos.get("productos") or []
    if not servicios and not productos:
        raise ErrorLavadero("Elige al menos un servicio.")
    placa, cliente_nombre, cliente_telefono = _datos_cliente(datos)
    items: list[tuple] = []
    for servicio_id in servicios:
        servicio = db().one(
            "SELECT * FROM lv_servicio WHERE id=? AND activo=1 AND zona_id=?",
            (servicio_id, zona_id),
        )
        if not servicio:
            raise ErrorLavadero("Un servicio ya no está disponible.")
        tarifa = db().one(
            "SELECT precio FROM lv_precio WHERE servicio_id=? AND tipo_id=?",
            (servicio_id, tipo_id),
        )
        if not tarifa:
            raise ErrorLavadero(f"{servicio['nombre']} no tiene precio para ese vehículo.")
        valor = pesos(tarifa["precio"])
        items.append(("SERVICIO", servicio_id, 0, servicio["nombre"], servicio["grupo"], 1, valor, valor))
    for crudo in productos:
        producto_id = int(crudo.get("producto_id") or crudo.get("id") or 0)
        cantidad = _entero(crudo.get("cantidad") or 1, "La cantidad", 1, 999)
        producto = db().one("SELECT * FROM lv_producto WHERE id=? AND activo=1", (producto_id,))
        if not producto:
            raise ErrorLavadero("Un producto ya no está disponible.")
        valor = pesos(producto["precio"])
        items.append(("PRODUCTO", 0, producto_id, producto["nombre"], "", cantidad, valor, valor * cantidad))
    total = sum(item[-1] for item in items)
    colaboradores = _normalizar_colaboradores(datos.get("colaboradores") or [])
    if not colaboradores:
        raise ErrorLavadero("Elige quién va a lavar.")
    with db().tx():
        orden_id = db().run(
            """
            INSERT INTO lv_orden (
                branch_id, zona_id, tipo_id, tipo_orden, placa, cliente_nombre,
                cliente_telefono, estado, total, venta_id, creada_en, checklist, nota
            ) VALUES (?,?,?,?,?,?,?,?,?,0,?,?,?)
            """,
            (
                branch_id,
                zona_id,
                tipo_id,
                "SERVICIO",
                placa,
                cliente_nombre,
                cliente_telefono,
                "EN_PROCESO",
                total,
                ahora(),
                json.dumps(_leer_revision(datos.get("checklist")), ensure_ascii=False),
                _nota_vehiculo(datos.get("nota")),
            ),
        )
        for item in items:
            db().run(
                """
                INSERT INTO lv_item (
                    orden_id, tipo, servicio_id, producto_id, descripcion, grupo, cantidad, precio, subtotal
                ) VALUES (?,?,?,?,?,?,?,?,?)
                """,
                (orden_id,) + item,
            )
        for colaborador in colaboradores:
            db().run(
                "INSERT INTO lv_colab (orden_id, empleado_id, peso) VALUES (?,?,?)",
                (orden_id, colaborador["empleado_id"], colaborador["peso"]),
            )
    auditar(ses["usuario"], "orden", f"Orden #{orden_id} por {formato_pesos(total)}")
    return _orden_completa(orden_id)


def vender_productos(datos: dict, ses: dict) -> dict:
    branch_id = _branch_efectivo(ses, int(datos.get("branch_id") or 0))
    if not db().one("SELECT id FROM lv_sucursal WHERE id=? AND activo=1", (branch_id,)):
        raise ErrorLavadero("Elige la sucursal.")
    productos = datos.get("productos") or []
    if not productos:
        raise ErrorLavadero("Elige un producto.")
    items = []
    for crudo in productos:
        producto_id = int(crudo.get("producto_id") or crudo.get("id") or 0)
        cantidad = _entero(crudo.get("cantidad") or 1, "La cantidad", 1, 999)
        producto = db().one("SELECT * FROM lv_producto WHERE id=? AND activo=1", (producto_id,))
        if not producto:
            raise ErrorLavadero("Un producto ya no está disponible.")
        valor = pesos(producto["precio"])
        items.append(("PRODUCTO", 0, producto_id, producto["nombre"], "", cantidad, valor, valor * cantidad))
    total = sum(item[-1] for item in items)
    pagos = _normalizar_pagos(datos.get("pagos") or [], total)
    with db().tx():
        orden_id = db().run(
            """
            INSERT INTO lv_orden (
                branch_id, zona_id, tipo_id, tipo_orden, placa, cliente_nombre,
                cliente_telefono, estado, total, venta_id, creada_en, cobrada_en
            ) VALUES (?,?,?,?,?,?,?,?,?,0,?,?)
            """,
            (
                branch_id,
                0,
                0,
                "PRODUCTO",
                "",
                str(datos.get("cliente_nombre") or "").strip()[:80],
                _telefono(datos.get("cliente_telefono")),
                "COBRADA",
                total,
                ahora(),
                ahora(),
            ),
        )
        for item in items:
            db().run(
                """
                INSERT INTO lv_item (
                    orden_id, tipo, servicio_id, producto_id, descripcion, grupo, cantidad, precio, subtotal
                ) VALUES (?,?,?,?,?,?,?,?,?)
                """,
                (orden_id,) + item,
            )
            db().run(
                "UPDATE lv_producto SET stock=stock-? WHERE id=?",
                (item[5], item[2]),
            )
        for pago in pagos:
            db().run(
                "INSERT INTO lv_pago (orden_id, medio, monto) VALUES (?,?,?)",
                (orden_id, pago["medio"], pago["monto"]),
            )
    orden = _orden_completa(orden_id)
    orden["cobrado_por"] = str(ses.get("nombre") or ses.get("usuario") or "")
    venta_id = _espejar_mysql(orden)
    if venta_id:
        db().run("UPDATE lv_orden SET venta_id=? WHERE id=?", (venta_id, orden_id))
        orden["venta_id"] = venta_id
    _avisar_caja(orden)
    return orden


def _normalizar_colaboradores(crudos: list) -> list[dict]:
    salida = []
    vistos = set()
    for crudo in crudos:
        empleado_id = int(crudo.get("empleado_id") or crudo.get("id") or 0)
        if not empleado_id or empleado_id in vistos:
            continue
        if not db().one("SELECT id FROM lv_empleado WHERE id=? AND activo=1", (empleado_id,)):
            raise ErrorLavadero("Un muchacho ya no está activo.")
        peso = _entero(crudo.get("peso") or 1, "El reparto", 1, 100)
        salida.append({"empleado_id": empleado_id, "peso": peso})
        vistos.add(empleado_id)
    return salida


def _telefono(valor: Any) -> str:
    digitos = "".join(ch for ch in str(valor or "") if ch.isdigit())
    return digitos[:15]


def _nombre_cliente(valor: Any) -> str:
    texto = " ".join(str(valor or "").upper().split())
    limpio = "".join(ch for ch in texto if ch.isalpha() or ch == " ")
    return " ".join(limpio.split())[:80]


def _datos_cliente(datos: dict) -> tuple[str, str, str]:
    placa = "".join(ch for ch in str(datos.get("placa") or "").upper() if ch.isalnum())[:8]
    nombre = _nombre_cliente(datos.get("cliente_nombre"))
    telefono = _telefono(datos.get("cliente_telefono"))
    if len(placa) < 5:
        raise ErrorLavadero("La placa es obligatoria. Escríbela así: ABC123.")
    if len(nombre) < 3:
        raise ErrorLavadero("Escribe el nombre del cliente. Queda en mayúscula.")
    if len(telefono) < 10:
        raise ErrorLavadero("Escribe el WhatsApp del cliente, con 10 números.")
    return placa, nombre, telefono


def actualizar_orden(orden_id: int, datos: dict, ses: dict) -> dict:
    orden = _orden_completa(orden_id)
    _exigir_branch(ses, int(orden["branch_id"]))
    if orden["estado"] in {"COBRADA", "ANULADA"}:
        raise ErrorLavadero("Esa orden ya se cerró.")
    if "placa" in datos or "cliente_nombre" in datos or "cliente_telefono" in datos:
        placa, cliente_nombre, cliente_telefono = _datos_cliente(
            {
                "placa": datos.get("placa", orden.get("placa")),
                "cliente_nombre": datos.get("cliente_nombre", orden.get("cliente_nombre")),
                "cliente_telefono": datos.get("cliente_telefono", orden.get("cliente_telefono")),
            }
        )
        db().run(
            "UPDATE lv_orden SET placa=?, cliente_nombre=?, cliente_telefono=? WHERE id=?",
            (placa, cliente_nombre, cliente_telefono, orden_id),
        )
    if "colaboradores" in datos:
        colaboradores = _normalizar_colaboradores(datos.get("colaboradores") or [])
        if not colaboradores and orden.get("tipo_orden") != "PRODUCTO":
            raise ErrorLavadero("Elige quién va a lavar.")
        db().run("DELETE FROM lv_colab WHERE orden_id=?", (orden_id,))
        for colaborador in colaboradores:
            db().run(
                "INSERT INTO lv_colab (orden_id, empleado_id, peso) VALUES (?,?,?)",
                (orden_id, colaborador["empleado_id"], colaborador["peso"]),
            )
    if "servicios" in datos:
        _reemplazar_servicios(orden, datos.get("servicios") or [])
    if "productos" in datos:
        _reemplazar_productos(orden, datos.get("productos") or [])
    if "checklist" in datos or "nota" in datos:
        checklist = _leer_revision(datos["checklist"]) if "checklist" in datos else _leer_revision(orden.get("checklist"))
        nota = _nota_vehiculo(datos["nota"]) if "nota" in datos else _nota_vehiculo(orden.get("nota"))
        db().run(
            "UPDATE lv_orden SET checklist=?, nota=? WHERE id=?",
            (json.dumps(checklist, ensure_ascii=False), nota, orden_id),
        )
    return _orden_completa(orden_id)


def _reemplazar_servicios(orden: dict, crudos: list) -> None:
    if orden.get("tipo_orden") == "PRODUCTO":
        raise ErrorLavadero("Esta venta no lleva servicios.")
    pedidos: list[int] = []
    vistos: set[int] = set()
    for crudo in crudos:
        if isinstance(crudo, dict):
            servicio_id = int(crudo.get("servicio_id") or crudo.get("id") or 0)
        else:
            servicio_id = int(crudo or 0)
        if not servicio_id or servicio_id in vistos:
            continue
        vistos.add(servicio_id)
        pedidos.append(servicio_id)
    if not pedidos:
        raise ErrorLavadero("Elige al menos un servicio.")
    actuales = {
        int(item["servicio_id"]): item
        for item in orden["items"]
        if item["tipo"] == "SERVICIO" and int(item["servicio_id"] or 0)
    }
    lineas: list[tuple] = []
    for servicio_id in pedidos:
        if servicio_id in actuales:
            item = actuales[servicio_id]
            valor = pesos(item["precio"])
            lineas.append((servicio_id, item["descripcion"], item["grupo"] or "", valor))
            continue
        servicio = db().one(
            "SELECT * FROM lv_servicio WHERE id=? AND activo=1 AND zona_id=?",
            (servicio_id, int(orden["zona_id"])),
        )
        if not servicio:
            raise ErrorLavadero("Un servicio ya no está disponible.")
        tarifa = db().one(
            "SELECT precio FROM lv_precio WHERE servicio_id=? AND tipo_id=?",
            (servicio_id, int(orden["tipo_id"])),
        )
        if not tarifa:
            raise ErrorLavadero(f"{servicio['nombre']} no tiene precio para ese vehículo.")
        valor = pesos(tarifa["precio"])
        lineas.append((servicio_id, servicio["nombre"], servicio["grupo"] or "", valor))
    orden_id = int(orden["id"])
    with db().tx():
        db().run("DELETE FROM lv_item WHERE orden_id=? AND tipo='SERVICIO'", (orden_id,))
        for servicio_id, nombre, grupo, valor in lineas:
            db().run(
                """
                INSERT INTO lv_item (
                    orden_id, tipo, servicio_id, producto_id, descripcion, grupo, cantidad, precio, subtotal
                ) VALUES (?,?,?,?,?,?,?,?,?)
                """,
                (orden_id, "SERVICIO", servicio_id, 0, nombre, grupo, 1, valor, valor),
            )
        _guardar_total(orden_id)


def _guardar_total(orden_id: int) -> None:
    filas = db().all("SELECT subtotal FROM lv_item WHERE orden_id=?", (int(orden_id),))
    total = sum(pesos(fila["subtotal"]) for fila in filas)
    db().run("UPDATE lv_orden SET total=? WHERE id=?", (total, int(orden_id)))


def _reemplazar_productos(orden: dict, crudos: list) -> None:
    pedidos: dict[int, int] = {}
    for crudo in crudos or []:
        if not isinstance(crudo, dict):
            continue
        producto_id = int(crudo.get("producto_id") or crudo.get("id") or 0)
        cantidad = int(crudo.get("cantidad") or 0)
        if producto_id and cantidad > 0:
            pedidos[producto_id] = cantidad
    actuales = {
        int(item["producto_id"]): item
        for item in orden["items"]
        if item["tipo"] == "PRODUCTO" and int(item["producto_id"] or 0)
    }
    lineas: list[tuple] = []
    for producto_id, cantidad in pedidos.items():
        if cantidad > 999:
            raise ErrorLavadero("La cantidad es demasiado alta.")
        if producto_id in actuales:
            item = actuales[producto_id]
            valor = pesos(item["precio"])
            nombre = item["descripcion"]
            producto = db().one("SELECT stock FROM lv_producto WHERE id=?", (producto_id,))
            stock = int(producto["stock"]) if producto else cantidad
        else:
            producto = db().one("SELECT * FROM lv_producto WHERE id=? AND activo=1", (producto_id,))
            if not producto:
                raise ErrorLavadero("Un producto ya no está disponible.")
            valor = pesos(producto["precio"])
            nombre = producto["nombre"]
            stock = int(producto["stock"])
        if cantidad > stock:
            raise ErrorLavadero(f"Solo hay {stock} de {nombre}.")
        lineas.append((producto_id, nombre, cantidad, valor, valor * cantidad))
    orden_id = int(orden["id"])
    with db().tx():
        db().run("DELETE FROM lv_item WHERE orden_id=? AND tipo='PRODUCTO'", (orden_id,))
        for producto_id, nombre, cantidad, valor, subtotal in lineas:
            db().run(
                """
                INSERT INTO lv_item (
                    orden_id, tipo, servicio_id, producto_id, descripcion, grupo, cantidad, precio, subtotal
                ) VALUES (?,?,?,?,?,?,?,?,?)
                """,
                (orden_id, "PRODUCTO", 0, producto_id, nombre, "", cantidad, valor, subtotal),
            )
        _guardar_total(orden_id)


def _exigir_branch(ses: dict, branch_id: int) -> None:
    fijo = int(ses.get("branch_id") or 0)
    if fijo and fijo != int(branch_id):
        raise ErrorLavadero("Esta orden es de otra sucursal.", 403)


def marcar_listo(orden_id: int, ses: dict) -> dict:
    orden = _orden_completa(orden_id)
    _exigir_branch(ses, int(orden["branch_id"]))
    if orden["estado"] != "EN_PROCESO":
        raise ErrorLavadero("Solo se marca listo un vehículo que está en proceso.")
    db().run("UPDATE lv_orden SET estado='LISTO', lista_en=? WHERE id=?", (ahora(), orden_id))
    orden = _orden_completa(orden_id)
    orden["whatsapp"] = enlace_whatsapp(orden)
    return orden


def anular_orden(orden_id: int, ses: dict) -> dict:
    orden = _orden_completa(orden_id)
    _exigir_branch(ses, int(orden["branch_id"]))
    if orden["estado"] == "COBRADA":
        raise ErrorLavadero("Una orden cobrada no se anula desde aquí.")
    if orden["estado"] == "ANULADA":
        return orden
    db().run("UPDATE lv_orden SET estado='ANULADA', anulada_en=? WHERE id=?", (ahora(), orden_id))
    auditar(ses["usuario"], "anular", f"Orden #{orden_id}")
    return _orden_completa(orden_id)


def enlace_whatsapp(orden: dict) -> dict:
    plantilla = negocio()["whatsapp_plantilla"]
    placa = orden.get("placa") or ""
    datos_texto = {
        "negocio": negocio()["nombre"],
        "vehiculo": orden.get("vehiculo") or "vehículo",
        "placa": placa or "",
        "sucursal": orden.get("sucursal") or "",
        "telefono": _presentar_telefono(negocio()["telefono"]),
    }
    texto = plantilla
    for clave, valor in datos_texto.items():
        texto = texto.replace("{" + clave + "}", str(valor))
    texto = " ".join(texto.split())
    telefono = _telefono(orden.get("cliente_telefono"))
    if len(telefono) == 10:
        telefono = "57" + telefono
    url = ""
    if telefono:
        url = f"https://api.whatsapp.com/send?phone={telefono}&text={quote(texto)}"
    return {"url": url, "texto": texto, "telefono": telefono}


def _presentar_telefono(valor: str) -> str:
    digitos = _telefono(valor)
    if len(digitos) == 10:
        return f"{digitos[:3]} {digitos[3:6]} {digitos[6:]}"
    return digitos


def cobrar_orden(orden_id: int, datos: dict, ses: dict) -> dict:
    orden = _orden_completa(orden_id)
    _exigir_branch(ses, int(orden["branch_id"]))
    if orden["estado"] != "LISTO":
        raise ErrorLavadero("Primero márcalo listo para entregar.")
    if "colaboradores" in datos:
        orden = actualizar_orden(orden_id, {"colaboradores": datos.get("colaboradores")}, ses)
    colaboradores = orden["colaboradores"]
    pagos = _normalizar_pagos(datos.get("pagos") or [], pesos(orden["total"]))
    lineas = _calcular_comisiones(orden, colaboradores)
    momento = ahora()
    with db().tx():
        db().run("DELETE FROM lv_comision WHERE orden_id=?", (orden_id,))
        for linea in lineas:
            db().run(
                """
                INSERT INTO lv_comision (orden_id, item_id, empleado_id, base, porcentaje, monto)
                VALUES (?,?,?,?,?,?)
                """,
                (orden_id, linea["item_id"], linea["empleado_id"], linea["base"], linea["porcentaje"], linea["monto"]),
            )
        db().run("DELETE FROM lv_pago WHERE orden_id=?", (orden_id,))
        for pago in pagos:
            db().run(
                "INSERT INTO lv_pago (orden_id, medio, monto) VALUES (?,?,?)",
                (orden_id, pago["medio"], pago["monto"]),
            )
        for item in orden["items"]:
            if item["tipo"] == "PRODUCTO" and int(item["producto_id"] or 0):
                db().run(
                    "UPDATE lv_producto SET stock=stock-? WHERE id=?",
                    (int(item["cantidad"]), int(item["producto_id"])),
                )
        db().run(
            "UPDATE lv_orden SET estado='COBRADA', cobrada_en=?, lista_en=COALESCE(lista_en, ?) WHERE id=?",
            (momento, momento, orden_id),
        )
    orden = _orden_completa(orden_id)
    orden["cobrado_por"] = str(ses.get("nombre") or ses.get("usuario") or "")
    venta_id = _espejar_mysql(orden)
    if venta_id:
        db().run("UPDATE lv_orden SET venta_id=? WHERE id=?", (venta_id, orden_id))
        orden["venta_id"] = venta_id
    auditar(ses["usuario"], "cobro", f"Orden #{orden_id} {formato_pesos(orden['total'])}")
    _avisar_caja(orden)
    return orden


def _calcular_comisiones(orden: dict, colaboradores: list[dict]) -> list[dict]:
    if not colaboradores:
        return []
    suma = sum(int(c["peso"]) for c in colaboradores) or 1
    lineas = []
    for item in orden["items"]:
        if item["tipo"] != "SERVICIO":
            continue
        for colaborador in colaboradores:
            porcentaje = porcentaje_comision(
                int(colaborador["empleado_id"]),
                int(item["servicio_id"] or 0),
                item.get("grupo") or "",
            )
            parte = pesos(pesos(item["subtotal"]) * (porcentaje / 100) * (int(colaborador["peso"]) / suma))
            if parte <= 0:
                continue
            lineas.append(
                {
                    "item_id": int(item["id"]),
                    "empleado_id": int(colaborador["empleado_id"]),
                    "base": pesos(item["subtotal"]),
                    "porcentaje": porcentaje,
                    "monto": parte,
                }
            )
    return lineas


def _normalizar_pagos(crudos: list, total: int) -> list[dict]:
    if not crudos:
        return [{"medio": "Efectivo", "monto": total}]
    pagos = []
    for crudo in crudos:
        monto = pesos(crudo.get("monto"))
        if monto <= 0:
            continue
        medio = str(crudo.get("medio") or "Efectivo").strip()[:40] or "Efectivo"
        pagos.append({"medio": medio, "monto": monto})
    if not pagos:
        return [{"medio": "Efectivo", "monto": total}]
    suma = sum(p["monto"] for p in pagos)
    if suma != total:
        raise ErrorLavadero(
            f"Los pagos suman {formato_pesos(suma)} y la orden vale {formato_pesos(total)}."
        )
    return pagos


def _nombre_persona(fila: dict) -> str:
    return " ".join(
        parte
        for parte in (str(fila.get("nombre") or "").strip(), str(fila.get("apellido") or "").strip())
        if parte
    )


def _detalle_movil(orden: dict) -> dict:
    """Lo que el celular muestra de una venta: placa, cliente, sede, servicios y ganancia."""
    servicios = []
    costo_productos = 0
    for item in orden.get("items") or []:
        cantidad = int(item.get("cantidad") or 1)
        costo = 0
        if item.get("tipo") == "PRODUCTO" and int(item.get("producto_id") or 0):
            producto = db().one("SELECT costo FROM lv_producto WHERE id=?", (int(item["producto_id"]),))
            costo = pesos(producto["costo"]) if producto else 0
            costo_productos += costo * cantidad
        servicios.append(
            {
                "tipo": item.get("tipo") or "",
                "nombre": item.get("descripcion") or "",
                "cantidad": cantidad,
                "precio": pesos(item.get("precio")),
                "subtotal": pesos(item.get("subtotal")),
            }
        )
    por_persona: dict[int, dict] = {}
    for fila in db().all(
        """
        SELECT c.empleado_id, c.monto, e.nombre, e.apellido
        FROM lv_comision c JOIN lv_empleado e ON e.id=c.empleado_id
        WHERE c.orden_id=?
        """,
        (int(orden["id"]),),
    ):
        empleado_id = int(fila["empleado_id"])
        actual = por_persona.setdefault(
            empleado_id,
            {"nombre": _nombre_persona(fila), "monto": 0},
        )
        actual["monto"] += pesos(fila["monto"])
    if not por_persona:
        for col in orden.get("colaboradores") or []:
            nombre = str(col.get("empleado") or "").strip()
            if nombre:
                por_persona[int(col.get("empleado_id") or 0)] = {"nombre": nombre, "monto": 0}
    muchachos = [por_persona[clave] for clave in sorted(por_persona)]
    comisiones = sum(pesos(persona["monto"]) for persona in muchachos)
    total = pesos(orden.get("total"))
    pagos = [
        {"medio": fila["medio"], "monto": pesos(fila["monto"])}
        for fila in db().all("SELECT medio, monto FROM lv_pago WHERE orden_id=?", (int(orden["id"]),))
    ]
    momento = str(orden.get("cobrada_en") or "")
    return {
        "placa": orden.get("placa") or "",
        "cliente": orden.get("cliente_nombre") or "",
        "telefono": orden.get("cliente_telefono") or "",
        "sucursal": orden.get("sucursal") or "",
        "zona": orden.get("zona") or "",
        "vehiculo": orden.get("vehiculo") or "",
        "fecha": momento,
        "hora": momento[11:16] if len(momento) >= 16 else "",
        "servicios": servicios,
        "muchachos": muchachos,
        "comisiones": comisiones,
        "ganancia": total - comisiones - costo_productos,
        "total": total,
        "pagos": pagos,
        "cobrado_por": orden.get("cobrado_por") or "",
        "nota": orden.get("nota") or "",
    }


def _avisar_caja(orden: dict) -> None:
    detalle = _detalle_movil(orden)
    publicar(
        {
            "tipo": "orden_cobrada",
            "orden_id": int(orden["id"]),
            "venta_id": int(orden.get("venta_id") or 0),
            "sucursal": detalle["sucursal"],
            "zona": detalle["zona"],
            "total": detalle["total"],
            "colaboradores": [persona["nombre"] for persona in detalle["muchachos"]],
            "servicios": [item["nombre"] for item in detalle["servicios"]],
            "placa": detalle["placa"],
            "cliente": detalle["cliente"],
            "ganancia": detalle["ganancia"],
            "hora": detalle["hora"],
            "cobrado_por": detalle["cobrado_por"],
            "muchachos": detalle["muchachos"],
        }
    )
    _avisar_railway(orden, detalle)


def publicar(payload: dict) -> None:
    if _LOOP is None:
        return
    try:
        from comando import HUB

        asyncio.run_coroutine_threadsafe(HUB.broadcast(payload), _LOOP)
    except Exception:
        traceback.print_exc()


def _avisar_railway(orden: dict, detalle: dict) -> None:
    """Avisa al API público para que el celular suene aunque la venta se cobró en la sede."""
    if os.getenv("RAILWAY_ENVIRONMENT") or os.getenv("RAILWAY_PROJECT_ID"):
        return
    url = os.getenv(
        "LAVADERO_AVISO_URL",
        "https://api-production-b438.up.railway.app/api/v1/caja/aviso",
    ).strip()
    token = os.getenv("LAVADERO_AVISO_TOKEN", "").strip()
    if not url or not token:
        return
    payload = {
        "tipo": "orden_cobrada",
        "orden_id": int(orden["id"]),
        "venta_id": int(orden.get("venta_id") or 0),
        "sucursal": detalle["sucursal"],
        "zona": detalle["zona"],
        "total": detalle["total"],
        "colaboradores": [persona["nombre"] for persona in detalle["muchachos"]],
        "servicios": [item["nombre"] for item in detalle["servicios"]],
        "placa": detalle["placa"],
        "cliente": detalle["cliente"],
        "ganancia": detalle["ganancia"],
        "hora": detalle["hora"],
        "cobrado_por": detalle["cobrado_por"],
        "muchachos": detalle["muchachos"],
    }

    def enviar() -> None:
        try:
            import urllib.request

            cuerpo = json.dumps(payload).encode("utf-8")
            pedido = urllib.request.Request(url, data=cuerpo, method="POST")
            pedido.add_header("Content-Type", "application/json")
            pedido.add_header("X-Aviso-Token", token)
            with urllib.request.urlopen(pedido, timeout=3) as respuesta:
                respuesta.read()
        except Exception:
            return

    threading.Thread(target=enviar, daemon=True).start()


def _espejar_mysql(orden: dict) -> int:
    if os.getenv("LAVADERO_FORCE_SQLITE", "").strip().lower() in {"1", "true", "si", "sí"}:
        return 0
    try:
        from main import _column_cache, db_config, execute, has_column, query
    except Exception:
        return 0
    try:
        if not db_config().get("password"):
            return 0
    except Exception:
        return 0
    try:
        detalle = _detalle_movil(orden)
        nombres = ", ".join(
            persona["nombre"] for persona in detalle["muchachos"] if persona.get("nombre")
        ).strip() or str(orden.get("cobrado_por") or "Lavadero")
        nombres = nombres[:90]
        empleado = 0
        try:
            filas = query("SELECT Id_Empleados FROM empleados WHERE Nombres=%s LIMIT 1", (nombres,))
            if filas:
                empleado = int(filas[0]["Id_Empleados"])
            else:
                empleado = execute(
                    "INSERT INTO empleados (Nombres, Cargo) VALUES (%s, %s)",
                    (nombres, "Lavadero"),
                )
        except Exception:
            empleado = 0
        if not empleado:
            try:
                filas = query("SELECT Id_Empleados FROM empleados ORDER BY Id_Empleados LIMIT 1")
                if filas:
                    empleado = int(filas[0]["Id_Empleados"])
            except Exception:
                empleado = 0
        if not empleado:
            return 0
        venta_id = execute(
            "INSERT INTO ventas (Fecha_Venta, Total, Empleados_Id_Empleados) VALUES (%s, %s, %s)",
            (orden.get("cobrada_en") or ahora(), pesos(orden["total"]), empleado),
        )
        if not venta_id:
            return 0
        for columna, definicion in (
            ("branch_id", "INT NULL"),
            ("zona_id", "INT NULL"),
            ("lavadero_orden_id", "INT NULL"),
            ("lavadero_detalle", "LONGTEXT NULL"),
        ):
            try:
                if not has_column("ventas", columna):
                    execute(f"ALTER TABLE ventas ADD COLUMN {columna} {definicion}")
                    _column_cache.pop(("ventas", columna), None)
            except Exception:
                pass
        try:
            execute(
                """
                UPDATE ventas
                SET branch_id=%s, zona_id=%s, lavadero_orden_id=%s, lavadero_detalle=%s
                WHERE Id_Venta=%s
                """,
                (
                    int(orden["branch_id"]),
                    int(orden["zona_id"] or 0),
                    int(orden["id"]),
                    json.dumps(detalle, ensure_ascii=False),
                    int(venta_id),
                ),
            )
        except Exception:
            try:
                execute(
                    "UPDATE ventas SET branch_id=%s, zona_id=%s, lavadero_orden_id=%s WHERE Id_Venta=%s",
                    (int(orden["branch_id"]), int(orden["zona_id"] or 0), int(orden["id"]), int(venta_id)),
                )
            except Exception:
                traceback.print_exc()
        for item in orden.get("items") or []:
            if item["tipo"] != "PRODUCTO":
                continue
            producto = db().one("SELECT * FROM lv_producto WHERE id=?", (int(item["producto_id"]),))
            origen = int(producto["origen_id"]) if producto else 0
            if not origen:
                continue
            try:
                execute(
                    """
                    INSERT INTO productos_has_ventas
                        (Ventas_Id_Factura, Productos_Id_Producto, Cantidad, Subtotal)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (int(venta_id), origen, int(item["cantidad"]), pesos(item["subtotal"])),
                )
                execute(
                    "UPDATE productos SET Cantidad = Cantidad - %s WHERE Id_Producto=%s",
                    (int(item["cantidad"]), origen),
                )
            except Exception:
                traceback.print_exc()
        for pago in db().all("SELECT * FROM lv_pago WHERE orden_id=?", (int(orden["id"]),)):
            try:
                execute(
                    "INSERT INTO venta_pagos (Venta_Id, Metodo, Monto) VALUES (%s, %s, %s)",
                    (int(venta_id), pago["medio"], pesos(pago["monto"])),
                )
            except Exception:
                pass
        return int(venta_id)
    except Exception:
        traceback.print_exc()
        return 0


def tablero(branch_id: int) -> list[dict]:
    filas = db().all(
        """
        SELECT id FROM lv_orden
        WHERE branch_id=? AND estado IN ('EN_PROCESO', 'LISTO')
        ORDER BY CASE estado WHEN 'LISTO' THEN 0 ELSE 1 END, creada_en
        """,
        (int(branch_id),),
    )
    return [_orden_completa(int(fila["id"])) for fila in filas]


def _rango_dia(fecha: str) -> tuple[str, str]:
    return f"{fecha} 00:00:00", f"{fecha} 23:59:59"


def _ordenes_cobradas(inicio: str, fin: str, branch_id: int = 0, zona_id: int = 0, solo_productos: bool = False) -> list[dict]:
    sql = "SELECT * FROM lv_orden WHERE estado='COBRADA' AND cobrada_en>=? AND cobrada_en<=?"
    params: list[Any] = [inicio, fin]
    if branch_id:
        sql += " AND branch_id=?"
        params.append(int(branch_id))
    if solo_productos:
        sql += " AND tipo_orden='PRODUCTO'"
    elif zona_id:
        sql += " AND zona_id=?"
        params.append(int(zona_id))
    sql += " ORDER BY cobrada_en"
    return db().all(sql, tuple(params))


def _items_de(ids: list[int]) -> list[dict]:
    if not ids:
        return []
    marcas = ",".join("?" for _ in ids)
    return db().all(f"SELECT * FROM lv_item WHERE orden_id IN ({marcas})", tuple(ids))


def _comisiones_de(ids: list[int]) -> list[dict]:
    if not ids:
        return []
    marcas = ",".join("?" for _ in ids)
    return db().all(
        f"""
        SELECT c.*, e.nombre, e.apellido
        FROM lv_comision c JOIN lv_empleado e ON e.id=c.empleado_id
        WHERE c.orden_id IN ({marcas})
        """,
        tuple(ids),
    )


def _pagos_de(ids: list[int]) -> list[dict]:
    if not ids:
        return []
    marcas = ",".join("?" for _ in ids)
    return db().all(f"SELECT * FROM lv_pago WHERE orden_id IN ({marcas})", tuple(ids))


def reparto_efectivo(branch_id: int, zona_id: int) -> dict:
    propio = db().one(
        "SELECT * FROM lv_reparto WHERE branch_id=? AND zona_id=?",
        (int(branch_id), int(zona_id or 0)),
    )
    if propio:
        return propio
    if zona_id:
        general = db().one(
            "SELECT * FROM lv_reparto WHERE branch_id=? AND zona_id=0",
            (int(branch_id),),
        )
        if general:
            return general
    return {"id": 0, "modo": "PORCENTAJE", "valor": 10, "branch_id": branch_id, "zona_id": 0}


def calcular_gastos(branch_id: int, rebanadas: list[tuple[int, int]], dias: int = 1) -> int:
    total = 0
    fijos: set[int] = set()
    if not rebanadas:
        rebanadas = [(0, 0)]
    for zona_id, monto in rebanadas:
        regla = reparto_efectivo(branch_id, zona_id)
        if str(regla["modo"]) == "FIJO_DIARIO":
            clave = int(regla.get("id") or 0)
            if clave in fijos:
                continue
            fijos.add(clave)
            total += pesos(regla["valor"]) * max(1, dias)
        elif monto > 0:
            total += pesos(pesos(monto) * pesos(regla["valor"]) / 100)
    return total


def _desglose(ordenes: list[dict], dias: int = 1) -> dict:
    ids = [int(o["id"]) for o in ordenes]
    items = _items_de(ids)
    comisiones = _comisiones_de(ids)
    pagos = _pagos_de(ids)
    zonas = {int(z["id"]): z for z in db().all("SELECT * FROM lv_zona")}
    tipos = {int(t["id"]): t for t in db().all("SELECT * FROM lv_tipo")}
    sucursales = {int(s["id"]): s["nombre"] for s in db().all("SELECT * FROM lv_sucursal")}
    carros = motos = productos = 0
    por_zona: dict[int, int] = {}
    por_tipo: dict[str, int] = {}
    por_servicio: dict[str, dict] = {}
    por_sucursal: dict[int, int] = {}
    vehiculos = 0
    for orden in ordenes:
        por_sucursal[int(orden["branch_id"])] = por_sucursal.get(int(orden["branch_id"]), 0) + pesos(orden["total"])
        if orden["tipo_orden"] == "SERVICIO":
            vehiculos += 1
            nombre_tipo = tipos.get(int(orden["tipo_id"] or 0), {}).get("nombre") or "Vehículo"
            por_tipo[nombre_tipo] = por_tipo.get(nombre_tipo, 0) + pesos(orden["total"])
    por_id = {int(o["id"]): o for o in ordenes}
    for item in items:
        orden = por_id[int(item["orden_id"])]
        subtotal = pesos(item["subtotal"])
        if item["tipo"] == "PRODUCTO":
            productos += subtotal
            por_zona[0] = por_zona.get(0, 0) + subtotal
        else:
            zona = zonas.get(int(orden["zona_id"] or 0))
            tipo_zona = zona["tipo"] if zona else ""
            if tipo_zona == "CARROS":
                carros += subtotal
            elif tipo_zona == "MOTOS":
                motos += subtotal
            por_zona[int(orden["zona_id"] or 0)] = por_zona.get(int(orden["zona_id"] or 0), 0) + subtotal
            nombre = item["descripcion"]
            cubo = por_servicio.setdefault(nombre, {"nombre": nombre, "cantidad": 0, "total": 0})
            cubo["cantidad"] += int(item["cantidad"] or 1)
            cubo["total"] += subtotal
    producido = sum(pesos(o["total"]) for o in ordenes)
    total_comisiones = sum(pesos(c["monto"]) for c in comisiones)
    bolsillos, gastos, _ganancia = _aplicar_bolsillos(producido, total_comisiones)
    por_medio: dict[str, int] = {}
    for pago in pagos:
        por_medio[pago["medio"]] = por_medio.get(pago["medio"], 0) + pesos(pago["monto"])
    items_por_id = {int(item["id"]): item for item in items}
    por_colab: dict[int, dict] = {}
    for comision in comisiones:
        empleado_id = int(comision["empleado_id"])
        nombre = " ".join(
            parte
            for parte in (str(comision.get("nombre") or "").strip(), str(comision.get("apellido") or "").strip())
            if parte
        ) or "Muchacho"
        cubo = por_colab.setdefault(
            empleado_id,
            {"nombre": nombre, "comision": 0, "ordenes": set(), "trabajos": []},
        )
        cubo["comision"] += pesos(comision["monto"])
        cubo["ordenes"].add(int(comision["orden_id"]))
        orden = por_id.get(int(comision["orden_id"]), {})
        item = items_por_id.get(int(comision["item_id"] or 0), {})
        cubo["trabajos"].append(
            {
                "placa": orden.get("placa") or "",
                "servicio": item.get("descripcion") or "Servicio",
                "porcentaje": int(comision["porcentaje"] or 0),
                "monto": pesos(comision["monto"]),
            }
        )
    colaboradores = [
        {
            "nombre": v["nombre"],
            "comision": v["comision"],
            "ordenes": len(v["ordenes"]),
            "trabajos": v["trabajos"],
        }
        for v in sorted(por_colab.values(), key=lambda x: -x["comision"])
    ]
    zonas_salida = []
    for zona_id, total in sorted(por_zona.items(), key=lambda x: -x[1]):
        if zona_id == 0:
            nombre = "Productos"
        else:
            nombre = zonas.get(zona_id, {}).get("nombre") or f"Zona {zona_id}"
        zonas_salida.append({"zona": nombre, "total": total})
    return {
        "producido": producido,
        "vehiculos": vehiculos,
        "ticket_promedio": pesos(producido / vehiculos) if vehiculos else 0,
        "comisiones": total_comisiones,
        "gastos": gastos,
        "ganancia": producido - total_comisiones - gastos,
        "bolsillos": bolsillos,
        "carros": carros,
        "motos": motos,
        "productos": productos,
        "por_sucursal": [
            {"sucursal": sucursales.get(k, f"Sucursal {k}"), "total": v}
            for k, v in sorted(por_sucursal.items(), key=lambda x: -x[1])
        ],
        "por_zona": zonas_salida,
        "por_tipo": [{"tipo": k, "total": v} for k, v in sorted(por_tipo.items(), key=lambda x: -x[1])],
        "por_servicio": sorted(por_servicio.values(), key=lambda x: -x["total"])[:12],
        "por_medio": [{"medio": k, "total": v} for k, v in sorted(por_medio.items(), key=lambda x: -x[1])],
        "por_colaborador": colaboradores,
        "ordenes": len(ordenes),
    }


def resumen_dia(branch_id: int, fecha: Optional[str] = None) -> dict:
    fecha = fecha or hoy()
    inicio, fin = _rango_dia(fecha)
    ordenes = _ordenes_cobradas(inicio, fin, branch_id)
    datos = _desglose(ordenes)
    _marcar_gastado(datos["bolsillos"], branch_id, fecha)
    sucursal = db().one("SELECT nombre FROM lv_sucursal WHERE id=?", (int(branch_id),)) if branch_id else None
    nombre = sucursal["nombre"] if sucursal else "todas las sucursales"
    cierre = None
    if branch_id:
        cierre = db().one("SELECT * FROM lv_cierre WHERE branch_id=? AND fecha=?", (int(branch_id), fecha))
    texto = _texto_cierre(nombre, datos)
    ultimas = []
    for orden in reversed(ordenes[-8:]):
        completa = _orden_completa(int(orden["id"]))
        ultimas.append(
            {
                "id": completa["id"],
                "placa": completa["placa"],
                "icono": completa["icono"],
                "vehiculo": completa["vehiculo"],
                "zona": completa["zona"],
                "total": pesos(completa["total"]),
                "hora": str(completa["cobrada_en"] or "")[11:16],
            }
        )
    listos = 0
    if branch_id:
        listos = int(
            db().one(
                "SELECT COUNT(*) AS c FROM lv_orden WHERE branch_id=? AND estado='LISTO'",
                (int(branch_id),),
            )["c"]
            or 0
        )
    return {
        "fecha": fecha,
        "branch_id": branch_id,
        "branch_nombre": nombre,
        "texto": texto,
        "cerrado": bool(cierre),
        "cierre": cierre,
        "listos_sin_cobrar": listos,
        "ultimas": ultimas,
        **datos,
    }


def _texto_cierre(nombre: str, datos: dict) -> str:
    n = int(datos["vehiculos"])
    palabra = "vehículo" if n == 1 else "vehículos"
    salio = sum(pesos(bolsa.get("gastado")) for bolsa in datos.get("bolsillos") or [])
    extra = f" De los bolsillos salieron {formato_pesos(salio)} en pagos y compras." if salio else ""
    return (
        f"Hoy en {nombre} atendimos {n} {palabra}. "
        f"Carros {formato_pesos(datos['carros'])}, Motos {formato_pesos(datos['motos'])}, "
        f"productos {formato_pesos(datos['productos'])}. "
        + ". ".join(
            f"{bolsa['nombre']} {formato_pesos(bolsa['monto'])}" for bolsa in datos.get("bolsillos") or []
        )
        + "."
        + extra
    )


def cerrar_dia(branch_id: int, ses: dict, confirmar: bool = False) -> dict:
    branch_id = _branch_efectivo(ses, branch_id)
    if not branch_id:
        raise ErrorLavadero("Elige la sucursal que vas a cerrar.")
    resumen = resumen_dia(branch_id, hoy())
    if resumen["cerrado"]:
        return resumen
    if resumen["ganancia"] < 0 and not confirmar:
        resumen["requiere_confirmacion"] = True
        resumen["aviso"] = "Hoy los muchachos y los gastos superan lo que entró. ¿Cierras de todas formas?"
        return resumen
    db().run(
        """
        INSERT INTO lv_cierre (
            branch_id, fecha, producido, comisiones, gastos, ganancia, vehiculos, texto, usuario, creado_en
        ) VALUES (?,?,?,?,?,?,?,?,?,?)
        """,
        (
            branch_id,
            hoy(),
            resumen["producido"],
            resumen["comisiones"],
            resumen["gastos"],
            resumen["ganancia"],
            resumen["vehiculos"],
            resumen["texto"],
            ses["usuario"],
            ahora(),
        ),
    )
    auditar(ses["usuario"], "cierre", resumen["texto"][:180])
    resumen = resumen_dia(branch_id, hoy())
    tel = _telefono(negocio()["whatsapp_dueno"] or negocio()["telefono"])
    if len(tel) == 10:
        tel = "57" + tel
    resumen["whatsapp"] = (
        f"https://api.whatsapp.com/send?phone={tel}&text={quote(resumen['texto'])}" if tel else ""
    )
    return resumen


def reabrir_dia(branch_id: int, ses: dict) -> dict:
    solo_dueno(ses)
    db().run("DELETE FROM lv_cierre WHERE branch_id=? AND fecha=?", (int(branch_id), hoy()))
    auditar(ses["usuario"], "reabrir", f"Sucursal {branch_id}")
    return resumen_dia(branch_id, hoy())


def _periodo(preset: str, desde: str = "", hasta: str = "") -> tuple[str, str, str]:
    dia = datetime.now(BOGOTA)
    preset = (preset or "mes").lower()
    if preset == "personalizado" and desde and hasta:
        return desde[:10], hasta[:10], "personalizado"
    if preset == "hoy":
        fecha = dia.strftime("%Y-%m-%d")
        return fecha, fecha, "hoy"
    if preset == "ayer":
        fecha = (dia - timedelta(days=1)).strftime("%Y-%m-%d")
        return fecha, fecha, "ayer"
    if preset == "semana":
        return (dia - timedelta(days=6)).strftime("%Y-%m-%d"), dia.strftime("%Y-%m-%d"), "semana"
    if preset in {"ano", "año"}:
        return dia.strftime("%Y-01-01"), dia.strftime("%Y-%m-%d"), "año"
    return dia.strftime("%Y-%m-01"), dia.strftime("%Y-%m-%d"), "mes"


def _periodo_anterior(d0: str, d1: str, comparar: str) -> tuple[str, str]:
    inicio = datetime.strptime(d0, "%Y-%m-%d")
    fin = datetime.strptime(d1, "%Y-%m-%d")
    if comparar == "mismo_mes_anio_pasado":
        try:
            return (
                inicio.replace(year=inicio.year - 1).strftime("%Y-%m-%d"),
                fin.replace(year=fin.year - 1).strftime("%Y-%m-%d"),
            )
        except ValueError:
            return (
                (inicio - timedelta(days=365)).strftime("%Y-%m-%d"),
                (fin - timedelta(days=365)).strftime("%Y-%m-%d"),
            )
    if comparar == "dia_anterior" or d0 == d1:
        return (
            (inicio - timedelta(days=1)).strftime("%Y-%m-%d"),
            (fin - timedelta(days=1)).strftime("%Y-%m-%d"),
        )
    if comparar == "mes_anterior":
        previo = (inicio.replace(day=1) - timedelta(days=1)).replace(day=1)
        ultimo = (previo.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
        dia_fin = min(fin.day, ultimo.day)
        return previo.strftime("%Y-%m-%d"), previo.replace(day=dia_fin).strftime("%Y-%m-%d")
    dias = (fin - inicio).days + 1
    return (
        (inicio - timedelta(days=dias)).strftime("%Y-%m-%d"),
        (inicio - timedelta(days=1)).strftime("%Y-%m-%d"),
    )


def _variacion(actual: int, anterior: int) -> Optional[float]:
    if not anterior:
        return None
    return round((actual - anterior) * 100 / anterior, 1)


def reporte(branch_id: int = 0, zona_id: int = 0, preset: str = "mes", desde: str = "", hasta: str = "", comparar: str = "mes_anterior", solo_productos: bool = False) -> dict:
    d0, d1, nombre_periodo = _periodo(preset, desde, hasta)
    inicio, fin = f"{d0} 00:00:00", f"{d1} 23:59:59"
    dias = (datetime.strptime(d1, "%Y-%m-%d") - datetime.strptime(d0, "%Y-%m-%d")).days + 1
    ordenes = _ordenes_cobradas(inicio, fin, branch_id, zona_id, solo_productos)
    actual = _desglose(ordenes, dias)
    a0, a1 = _periodo_anterior(d0, d1, comparar)
    dias_ant = (datetime.strptime(a1, "%Y-%m-%d") - datetime.strptime(a0, "%Y-%m-%d")).days + 1
    anterior_ordenes = _ordenes_cobradas(f"{a0} 00:00:00", f"{a1} 23:59:59", branch_id, zona_id, solo_productos)
    anterior = _desglose(anterior_ordenes, dias_ant)
    serie = _serie_diaria(d0, d1, ordenes)
    mensual = _serie_mensual(branch_id, zona_id, solo_productos)
    horas = _por_hora(ordenes)
    frase = _frase_comparacion(actual["producido"], anterior["producido"], nombre_periodo, a0, a1)
    listos = db().all(
        "SELECT COUNT(*) AS c FROM lv_orden WHERE estado='LISTO'"
        + (" AND branch_id=?" if branch_id else ""),
        (int(branch_id),) if branch_id else (),
    )
    anuladas = db().one(
        """
        SELECT COUNT(*) AS c FROM lv_orden
        WHERE estado='ANULADA' AND anulada_en>=? AND anulada_en<=?
        """
        + (" AND branch_id=?" if branch_id else ""),
        (inicio, fin, int(branch_id)) if branch_id else (inicio, fin),
    )
    return {
        "periodo": {"preset": nombre_periodo, "desde": d0, "hasta": d1},
        "comparado_con": {"desde": a0, "hasta": a1},
        "frase": frase,
        "variacion_pct": _variacion(actual["producido"], anterior["producido"]),
        "anterior_producido": anterior["producido"],
        "listos_sin_cobrar": int(listos[0]["c"] if listos else 0),
        "anuladas": int(anuladas["c"] if anuladas else 0),
        "serie_diaria": serie,
        "serie_mensual": mensual,
        "por_hora": horas,
        **actual,
    }


def _frase_comparacion(actual: int, anterior: int, periodo: str, a0: str, a1: str) -> str:
    if not anterior and not actual:
        return "Todavía no hay ventas en este periodo."
    if not anterior:
        return f"En este periodo entraron {formato_pesos(actual)}. El periodo anterior estaba en cero."
    cambio = _variacion(actual, anterior) or 0
    sentido = "por encima" if cambio >= 0 else "por debajo"
    return (
        f"Van {formato_pesos(actual)}, {abs(cambio)}% {sentido} "
        f"del periodo anterior ({formato_pesos(anterior)})."
    )


def _serie_diaria(d0: str, d1: str, ordenes: list[dict]) -> list[dict]:
    por_dia: dict[str, dict] = {}
    cursor = datetime.strptime(d0, "%Y-%m-%d")
    fin = datetime.strptime(d1, "%Y-%m-%d")
    while cursor <= fin and len(por_dia) < 62:
        clave = cursor.strftime("%Y-%m-%d")
        por_dia[clave] = {"fecha": clave, "total": 0, "vehiculos": 0}
        cursor += timedelta(days=1)
    for orden in ordenes:
        clave = str(orden["cobrada_en"])[:10]
        if clave not in por_dia:
            continue
        por_dia[clave]["total"] += pesos(orden["total"])
        if orden["tipo_orden"] == "SERVICIO":
            por_dia[clave]["vehiculos"] += 1
    return list(por_dia.values())


def _serie_mensual(branch_id: int, zona_id: int, solo_productos: bool) -> list[dict]:
    inicio = (datetime.now(BOGOTA).replace(day=1) - timedelta(days=340)).strftime("%Y-%m-01 00:00:00")
    ordenes = _ordenes_cobradas(inicio, ahora(), branch_id, zona_id, solo_productos)
    cubos: dict[str, dict] = {}
    cursor = datetime.now(BOGOTA).replace(day=1)
    for _ in range(12):
        clave = cursor.strftime("%Y-%m")
        cubos[clave] = {"mes": clave, "total": 0, "vehiculos": 0, "ganancia": 0}
        cursor = (cursor.replace(day=1) - timedelta(days=1)).replace(day=1)
    for orden in ordenes:
        clave = str(orden["cobrada_en"])[:7]
        if clave not in cubos:
            continue
        cubos[clave]["total"] += pesos(orden["total"])
        if orden["tipo_orden"] == "SERVICIO":
            cubos[clave]["vehiculos"] += 1
    # Ganancia mensual con el mismo desglose, mes a mes.
    for clave, cubo in cubos.items():
        del cubo["ganancia"]
    return [cubos[k] for k in sorted(cubos.keys())]


def _por_hora(ordenes: list[dict]) -> list[dict]:
    horas = {f"{h:02d}": 0 for h in range(7, 20)}
    for orden in ordenes:
        hora = str(orden["cobrada_en"] or "")[11:13]
        if hora in horas:
            horas[hora] += pesos(orden["total"])
        elif hora:
            horas[hora] = horas.get(hora, 0) + pesos(orden["total"])
    return [{"hora": k, "total": v} for k, v in sorted(horas.items())]


def proteger(funcion):
    def atender(error: Exception):
        if isinstance(error, ErrorLavadero):
            raise HTTPException(error.status, error.mensaje) from error
        if isinstance(error, HTTPException):
            raise error
        traceback.print_exc()
        raise HTTPException(500, "Ocurrió un problema. Intenta de nuevo.") from error

    if asyncio.iscoroutinefunction(funcion):

        @functools.wraps(funcion)
        async def interna(*args, **kwargs):
            try:
                asegurar()
                return await funcion(*args, **kwargs)
            except Exception as error:
                atender(error)

        return interna

    @functools.wraps(funcion)
    def interna(*args, **kwargs):
        try:
            asegurar()
            return funcion(*args, **kwargs)
        except Exception as error:
            atender(error)

    return interna


def register(app: FastAPI) -> None:
    @app.on_event("startup")
    async def _al_iniciar() -> None:
        global _LOOP
        _LOOP = asyncio.get_running_loop()
        try:
            asegurar()
        except Exception:
            traceback.print_exc()

    @app.get("/lavadero")
    @app.get("/lavadero/")
    def pagina():
        return FileResponse(ESTATICOS / "index.html", headers={"Cache-Control": "no-store"})

    @app.get("/lavadero/app.css")
    def css():
        return FileResponse(ESTATICOS / "app.css", media_type="text/css", headers={"Cache-Control": "no-store"})

    @app.get("/lavadero/app.js")
    def javascript():
        return FileResponse(
            ESTATICOS / "app.js",
            media_type="application/javascript",
            headers={"Cache-Control": "no-store"},
        )

    @app.get("/api/lavadero/salud")
    @proteger
    def salud():
        asegurar()
        return {"ok": True, "motor": db().kind, "negocio": negocio()["nombre"]}

    @app.post("/api/lavadero/olvide")
    async def olvide(request: Request):
        try:
            cuerpo = await request.json()
            return pedir_recupero(str(cuerpo.get("dato") or ""), str(request.base_url))
        except ErrorLavadero as error:
            raise HTTPException(error.status, error.mensaje) from error

    @app.post("/api/lavadero/recuperar")
    async def recuperar(request: Request):
        try:
            cuerpo = await request.json()
            return aplicar_recupero(
                str(cuerpo.get("token") or ""),
                str(cuerpo.get("nueva") or ""),
                str(cuerpo.get("repite") or ""),
            )
        except ErrorLavadero as error:
            raise HTTPException(error.status, error.mensaje) from error

    @app.post("/api/lavadero/login")
    async def login(request: Request):
        try:
            cuerpo = await request.json()
            return entrar(str(cuerpo.get("usuario") or ""), str(cuerpo.get("clave") or cuerpo.get("contrasena") or ""))
        except ErrorLavadero as error:
            raise HTTPException(error.status, error.mensaje) from error

    @app.get("/api/lavadero/catalogo")
    @proteger
    def obtener_catalogo(request: Request):
        ses = sesion_de(request)
        return catalogo(int(ses.get("branch_id") or 0), completo=ses.get("rol") == "admin")

    @app.put("/api/lavadero/bolsillos")
    @proteger
    async def actualizar_bolsillos(request: Request):
        ses = sesion_de(request)
        solo_dueno(ses)
        return {"bolsillos": guardar_bolsillos(await request.json(), ses["usuario"])}

    @app.get("/api/lavadero/gastos")
    @proteger
    def obtener_gastos(request: Request, branch_id: int = 0, preset: str = "hoy"):
        ses = sesion_de(request)
        solo_dueno(ses)
        return listar_gastos(branch_id, ses, preset)

    @app.post("/api/lavadero/gastos")
    @proteger
    async def crear_gasto(request: Request):
        ses = sesion_de(request)
        solo_dueno(ses)
        return guardar_gasto(await request.json(), ses)

    @app.patch("/api/lavadero/gastos/{id_registro}")
    @proteger
    async def editar_gasto(id_registro: int, request: Request):
        ses = sesion_de(request)
        solo_dueno(ses)
        return guardar_gasto(await request.json(), ses, id_registro)

    @app.delete("/api/lavadero/gastos/{id_registro}")
    @proteger
    def borrar_gasto(id_registro: int, request: Request):
        ses = sesion_de(request)
        solo_dueno(ses)
        return quitar_gasto(id_registro, ses)

    @app.put("/api/lavadero/config")
    @proteger
    async def actualizar_config(request: Request):
        ses = sesion_de(request)
        solo_dueno(ses)
        return guardar_config(await request.json(), ses["usuario"])

    @app.post("/api/lavadero/clave")
    @proteger
    async def clave(request: Request):
        ses = sesion_de(request)
        cuerpo = await request.json()
        return cambiar_clave(ses, str(cuerpo.get("actual") or ""), str(cuerpo.get("nueva") or ""))

    @app.post("/api/lavadero/ajustes/{entidad}")
    @proteger
    async def crear_ajuste(entidad: str, request: Request):
        ses = sesion_de(request)
        solo_dueno(ses)
        return guardar_entidad(entidad, await request.json(), 0, ses["usuario"])

    @app.put("/api/lavadero/ajustes/{entidad}/{id_registro}")
    @proteger
    async def editar_ajuste(entidad: str, id_registro: int, request: Request):
        ses = sesion_de(request)
        solo_dueno(ses)
        return guardar_entidad(entidad, await request.json(), id_registro, ses["usuario"])

    @app.delete("/api/lavadero/ajustes/{entidad}/{id_registro}")
    @proteger
    def borrar_ajuste(entidad: str, id_registro: int, request: Request):
        ses = sesion_de(request)
        solo_dueno(ses)
        return quitar_entidad(entidad, id_registro, ses["usuario"])

    @app.post("/api/lavadero/zonas/{destino_id}/copiar/{origen_id}")
    @proteger
    def copiar(destino_id: int, origen_id: int, request: Request):
        ses = sesion_de(request)
        solo_dueno(ses)
        return copiar_zona(destino_id, origen_id)

    @app.get("/api/lavadero/ordenes")
    @proteger
    def listar_ordenes(request: Request, branch_id: int = 0):
        ses = sesion_de(request)
        branch_id = _branch_efectivo(ses, branch_id)
        if not branch_id:
            raise ErrorLavadero("Elige la sucursal.")
        return tablero(branch_id)

    @app.post("/api/lavadero/ordenes")
    @proteger
    async def nueva_orden(request: Request):
        ses = sesion_de(request)
        return crear_orden(await request.json(), ses)

    @app.patch("/api/lavadero/ordenes/{orden_id}")
    @proteger
    async def editar_orden(orden_id: int, request: Request):
        ses = sesion_de(request)
        return actualizar_orden(orden_id, await request.json(), ses)

    @app.post("/api/lavadero/ordenes/{orden_id}/listo")
    @proteger
    def listo(orden_id: int, request: Request):
        ses = sesion_de(request)
        return marcar_listo(orden_id, ses)

    @app.post("/api/lavadero/ordenes/{orden_id}/anular")
    @proteger
    def anular(orden_id: int, request: Request):
        ses = sesion_de(request)
        return anular_orden(orden_id, ses)

    @app.get("/api/lavadero/ordenes/{orden_id}/whatsapp")
    @proteger
    def whatsapp(orden_id: int, request: Request):
        ses = sesion_de(request)
        orden = _orden_completa(orden_id)
        _exigir_branch(ses, int(orden["branch_id"]))
        return enlace_whatsapp(orden)

    @app.post("/api/lavadero/ordenes/{orden_id}/cobrar")
    @proteger
    async def cobrar(orden_id: int, request: Request):
        ses = sesion_de(request)
        return cobrar_orden(orden_id, await request.json(), ses)

    @app.post("/api/lavadero/venta-productos")
    @proteger
    async def venta_productos(request: Request):
        ses = sesion_de(request)
        return vender_productos(await request.json(), ses)

    @app.get("/api/lavadero/resumen-dia")
    @proteger
    def dia(request: Request, branch_id: int = 0):
        ses = sesion_de(request)
        solo_dueno(ses)
        branch_id = _branch_efectivo(ses, branch_id)
        return resumen_dia(branch_id)

    @app.post("/api/lavadero/cerrar-dia")
    @proteger
    async def cierre(request: Request):
        ses = sesion_de(request)
        solo_dueno(ses)
        cuerpo = await request.json()
        return cerrar_dia(int(cuerpo.get("branch_id") or 0), ses, bool(cuerpo.get("confirmar")))

    @app.post("/api/lavadero/reabrir-dia")
    @proteger
    async def reabrir(request: Request):
        ses = sesion_de(request)
        solo_dueno(ses)
        cuerpo = await request.json()
        return reabrir_dia(int(cuerpo.get("branch_id") or 0), ses)

    @app.get("/api/lavadero/reportes")
    @proteger
    def reportes(
        request: Request,
        branch_id: int = 0,
        zona_id: int = 0,
        preset: str = "mes",
        desde: str = "",
        hasta: str = "",
        comparar: str = "mes_anterior",
        productos: int = 0,
    ):
        ses = sesion_de(request)
        solo_dueno(ses)
        branch_id = _branch_efectivo(ses, branch_id)
        return reporte(branch_id, zona_id, preset, desde, hasta, comparar, bool(productos))
