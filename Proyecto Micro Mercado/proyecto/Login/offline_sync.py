import json
import os
import sqlite3
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "offline_queue.db")


def _connect():
    cone = sqlite3.connect(DB_PATH)
    cone.execute(
        """CREATE TABLE IF NOT EXISTS cola_ventas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            payload TEXT NOT NULL,
            creado TEXT NOT NULL,
            synced INTEGER NOT NULL DEFAULT 0,
            error TEXT
        )"""
    )
    cone.commit()
    return cone


def encolar_venta(payload):
    cone = _connect()
    cursor = cone.cursor()
    cursor.execute(
        "INSERT INTO cola_ventas (payload, creado, synced) VALUES (?, ?, 0)",
        (json.dumps(payload, default=str), datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
    )
    local_id = cursor.lastrowid
    cone.commit()
    cone.close()
    return local_id


def pendientes():
    cone = _connect()
    rows = cone.execute(
        "SELECT id, payload FROM cola_ventas WHERE synced=0 ORDER BY id"
    ).fetchall()
    cone.close()
    return rows


def contar_pendientes():
    cone = _connect()
    n = cone.execute("SELECT COUNT(*) FROM cola_ventas WHERE synced=0").fetchone()[0]
    cone.close()
    return int(n or 0)


def marcar_sincronizada(local_id):
    cone = _connect()
    cone.execute("UPDATE cola_ventas SET synced=1, error=NULL WHERE id=?", (local_id,))
    cone.commit()
    cone.close()


def marcar_error(local_id, error):
    cone = _connect()
    cone.execute("UPDATE cola_ventas SET error=? WHERE id=?", (str(error)[:220], local_id))
    cone.commit()
    cone.close()


def sincronizar_pendientes():
    from Consultas import hay_conexion
    from venta_servicio import registrar_venta_online

    if not hay_conexion():
        return 0, contar_pendientes()
    ok = 0
    for local_id, raw in pendientes():
        try:
            payload = json.loads(raw)
            registrar_venta_online(payload)
            marcar_sincronizada(local_id)
            ok += 1
        except Exception as error:
            marcar_error(local_id, error)
            break
    return ok, contar_pendientes()
