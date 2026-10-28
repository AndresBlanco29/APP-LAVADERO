"""Línea de tiempo de turno: apertura, cierre temporal, reapertura y cierre definitivo."""
from __future__ import annotations

from datetime import datetime
import json


ETIQUETAS = {
    "apertura": "Apertura",
    "cierre_temporal": "Cierre temporal",
    "reapertura": "Ini. post-temp.",
    "cierre_definitivo": "Cierre definitivo",
}


def _fmt(fecha):
    if fecha is None:
        return ""
    if hasattr(fecha, "strftime"):
        return fecha.strftime("%Y-%m-%d %H:%M:%S")
    return str(fecha)[:19]


def _key_usuario(app_or_usuario):
    if hasattr(app_or_usuario, "usuario"):
        return str(getattr(app_or_usuario, "usuario", "") or "").strip().lower()
    return str(app_or_usuario or "").strip().lower()


def _hist(app):
    hist = getattr(app, "linea_tiempo_caja", None)
    if not isinstance(hist, dict):
        hist = {}
        app.linea_tiempo_caja = hist
    return hist


def obtener_linea_tiempo_turno(app):
    key = _key_usuario(app)
    return list(_hist(app).get(key) or [])


def limpiar_linea_tiempo_turno(app):
    key = _key_usuario(app)
    hist = _hist(app)
    if key in hist:
        del hist[key]


def registrar_evento_turno(app, tipo, fecha=None):
    """Registra un evento en la línea de tiempo del usuario en sesión."""
    key = _key_usuario(app)
    if not key:
        return []
    lista = list(_hist(app).get(key) or [])
    fecha = fecha or datetime.now()
    fs = _fmt(fecha)
    tipo = str(tipo or "").strip().lower()

    if tipo == "apertura":
        if lista and lista[-1].get("tipo") == "cierre_temporal":
            tipo = "reapertura"
        elif lista and lista[-1].get("tipo") in ("apertura", "reapertura"):
            # misma sesión: no duplicar
            return lista

    # Evitar duplicar el mismo tipo en el mismo minuto
    if lista:
        ult = lista[-1]
        if ult.get("tipo") == tipo and str(ult.get("fecha") or "")[:16] == fs[:16]:
            return lista

    lista.append(
        {
            "tipo": tipo,
            "fecha": fs,
            "etiqueta": ETIQUETAS.get(tipo, tipo),
        }
    )
    _hist(app)[key] = lista
    return lista


def sembrar_linea_tiempo_desde_bd(app):
    """Si no hay timeline en memoria, reconstruye la del día para el usuario."""
    key = _key_usuario(app)
    if not key:
        return
    if _hist(app).get(key):
        return
    eventos = reconstruir_linea_tiempo_dia(key)
    if eventos:
        # Quitar un cierre definitivo previo del día (nueva jornada tras cierre)
        while eventos and eventos[-1].get("tipo") == "cierre_definitivo":
            eventos.pop()
        _hist(app)[key] = eventos


def reconstruir_linea_tiempo_dia(usuario, hasta_id=None):
    """Arma eventos del día a partir de cierre_turno (aperturas vía Fecha_Desde)."""
    out = []
    try:
        from conexionLogin import FormularioLogin

        cone = FormularioLogin.conexion_base_de_datos()
        cursor = cone.cursor()
        sql = """
            SELECT Id, COALESCE(Tipo,'definitivo'), Fecha, Fecha_Desde
            FROM cierre_turno
            WHERE (LOWER(COALESCE(Usuario,''))=LOWER(%s) OR LOWER(COALESCE(Cajero,''))=LOWER(%s))
              AND DATE(Fecha)=CURDATE()
        """
        vals = [str(usuario).strip(), str(usuario).strip()]
        if hasta_id:
            sql += " AND Id<=%s"
            vals.append(int(hasta_id))
        sql += " ORDER BY Id ASC"
        cursor.execute(sql, tuple(vals))
        rows = cursor.fetchall() or []
        cone.close()
        for row in rows:
            _cid, tipo, fecha, desde = row
            tipo = str(tipo or "definitivo").lower()
            if desde:
                necesita_apertura = (not out) or (out[-1].get("tipo") == "cierre_temporal")
                if necesita_apertura:
                    ev = "apertura" if not out else "reapertura"
                    out.append(
                        {
                            "tipo": ev,
                            "fecha": _fmt(desde),
                            "etiqueta": ETIQUETAS[ev],
                        }
                    )
            if tipo.startswith("temp"):
                out.append(
                    {
                        "tipo": "cierre_temporal",
                        "fecha": _fmt(fecha),
                        "etiqueta": ETIQUETAS["cierre_temporal"],
                    }
                )
            else:
                out.append(
                    {
                        "tipo": "cierre_definitivo",
                        "fecha": _fmt(fecha),
                        "etiqueta": ETIQUETAS["cierre_definitivo"],
                    }
                )
    except Exception as error:
        print("Error reconstruir línea tiempo: {}".format(error))
    return out


def linea_tiempo_a_json(eventos):
    try:
        return json.dumps(eventos or [], ensure_ascii=False)
    except Exception:
        return "[]"


def linea_tiempo_desde_json(texto):
    try:
        data = json.loads(texto or "[]")
        return data if isinstance(data, list) else []
    except Exception:
        return []
