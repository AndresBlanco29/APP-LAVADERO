"""Provisión administrativa (Entrega 3).

Regla: 30% de ventas generales, financiada solo con efectivo.
Redondeo: siempre hacia arriba al múltiplo de $10.000.
Saldo pendiente acumulable.
Se calcula al consolidar el cierre general. Solo administrador.
"""
from __future__ import annotations

import math
from datetime import datetime

from conexionLogin import FormularioLogin


PCT_PROVISION = 0.30
MULTIPLO_REDONDEO = 10000.0


def _round2(valor):
    try:
        return round(float(valor or 0), 2)
    except (TypeError, ValueError):
        return 0.0


def redondear_provision_arriba(valor):
    """ceil(valor / 10000) * 10000. Nunca hacia abajo."""
    v = _round2(valor)
    if v <= 0:
        return 0.0
    return float(math.ceil(v / MULTIPLO_REDONDEO) * MULTIPLO_REDONDEO)


def calcular_provision_admin(
    ventas_generales,
    saldo_pendiente_anterior,
    efectivo_disponible,
    efectivo_provisionado=None,
):
    """
    NUEVO_SALDO = PROVISIÓN_OBJETIVO + SALDO_ANTERIOR - PROVISIONADO
    provisionado <= min(objetivo_total, efectivo_disponible)
    """
    ventas = max(0.0, _round2(ventas_generales))
    treinta = _round2(ventas * PCT_PROVISION)
    objetivo = redondear_provision_arriba(treinta)
    pendiente_ant = max(0.0, _round2(saldo_pendiente_anterior))
    objetivo_total = _round2(objetivo + pendiente_ant)
    efectivo = max(0.0, _round2(efectivo_disponible))
    tope = min(objetivo_total, efectivo)
    if efectivo_provisionado is None:
        provisionado = tope
    else:
        provisionado = max(0.0, min(_round2(efectivo_provisionado), tope))
    nuevo_pendiente = _round2(objetivo_total - provisionado)
    return {
        "ventas_generales": ventas,
        "porcentaje": 30.0,
        "treinta_porciento": treinta,
        "provision_objetivo": objetivo,
        "saldo_pendiente_anterior": pendiente_ant,
        "objetivo_total": objetivo_total,
        "efectivo_disponible": efectivo,
        "efectivo_provisionado": provisionado,
        "nuevo_saldo_pendiente": nuevo_pendiente,
    }


def _auditoria(usuario, detalle):
    try:
        from Consultas import registrar_auditoria

        registrar_auditoria(usuario, "Provisión admin", detalle)
    except Exception:
        pass


def _es_admin(usuario):
    from cierre_general_svc import es_usuario_admin

    return es_usuario_admin(usuario)


def ensure_provision_schema(cursor=None):
    own = cursor is None
    cone = None
    if own:
        cone = FormularioLogin.conexion_base_de_datos()
        cursor = cone.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS provision_admin_estado (
            Id INT PRIMARY KEY,
            Saldo_Pendiente DECIMAL(14,2) NOT NULL DEFAULT 0,
            Fecha_Actualizacion DATETIME NULL
        )
        """
    )
    cursor.execute(
        """
        INSERT IGNORE INTO provision_admin_estado (Id, Saldo_Pendiente, Fecha_Actualizacion)
        VALUES (1, 0, NULL)
        """
    )
    cursor.execute(
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
    if own:
        cone.commit()
        cone.close()


def obtener_saldo_pendiente_provision():
    try:
        ensure_provision_schema()
        cone = FormularioLogin.conexion_base_de_datos()
        cursor = cone.cursor()
        cursor.execute("SELECT Saldo_Pendiente FROM provision_admin_estado WHERE Id=1")
        row = cursor.fetchone()
        cone.close()
        return _round2(row[0] if row else 0)
    except Exception as error:
        print("Error saldo pendiente provisión: {}".format(error))
        return 0.0


def _row_to_dict(row):
    if not row:
        return None
    return {
        "id": int(row[0]),
        "cierre_general_id": int(row[1]),
        "estado": row[2] or "APLICADA",
        "fecha": str(row[3] or ""),
        "admin_usuario": row[4] or "",
        "ventas_generales": _round2(row[5]),
        "porcentaje": _round2(row[6]),
        "treinta_porciento": _round2(row[7]),
        "provision_objetivo": _round2(row[8]),
        "saldo_pendiente_anterior": _round2(row[9]),
        "objetivo_total": _round2(row[10]),
        "efectivo_disponible": _round2(row[11]),
        "efectivo_provisionado": _round2(row[12]),
        "nuevo_saldo_pendiente": _round2(row[13]),
        "observacion": row[14] or "",
    }


def obtener_provision_por_cierre_general(cierre_general_id):
    try:
        ensure_provision_schema()
        cone = FormularioLogin.conexion_base_de_datos()
        cursor = cone.cursor()
        cursor.execute(
            """
            SELECT Id, Cierre_General_Id, Estado, Fecha, Admin_Usuario,
                   Ventas_Generales, Porcentaje, Treinta_Porciento, Provision_Objetivo,
                   Saldo_Pendiente_Anterior, Objetivo_Total, Efectivo_Disponible,
                   Efectivo_Provisionado, Nuevo_Saldo_Pendiente, Observacion
            FROM provision_admin WHERE Cierre_General_Id=%s LIMIT 1
            """,
            (int(cierre_general_id),),
        )
        row = cursor.fetchone()
        cone.close()
        return _row_to_dict(row)
    except Exception as error:
        print("Error obtener provisión: {}".format(error))
        return None


def listar_provisiones_admin(limite=50, usuario=None):
    if not _es_admin(usuario or ""):
        return []
    out = []
    try:
        ensure_provision_schema()
        cone = FormularioLogin.conexion_base_de_datos()
        cursor = cone.cursor()
        cursor.execute(
            """
            SELECT Id, Cierre_General_Id, Estado, Fecha, Admin_Usuario,
                   Ventas_Generales, Porcentaje, Treinta_Porciento, Provision_Objetivo,
                   Saldo_Pendiente_Anterior, Objetivo_Total, Efectivo_Disponible,
                   Efectivo_Provisionado, Nuevo_Saldo_Pendiente, Observacion
            FROM provision_admin ORDER BY Id DESC LIMIT %s
            """,
            (int(limite),),
        )
        for row in cursor.fetchall() or []:
            out.append(_row_to_dict(row))
        cone.close()
    except Exception as error:
        print("Error listar provisiones: {}".format(error))
    return out


def resumen_provision_admin(usuario=None):
    if not _es_admin(usuario or ""):
        return {"error": "Solo administrador", "saldo_pendiente": 0, "historial": []}
    saldo = obtener_saldo_pendiente_provision()
    hist = listar_provisiones_admin(30)
    return {
        "saldo_pendiente": saldo,
        "porcentaje": 30.0,
        "multiplo_redondeo": int(MULTIPLO_REDONDEO),
        "historial": hist,
    }


def previsualizar_provision_cierre_general(cierre_general_id):
    """Cálculo sin persistir (para UI antes/después)."""
    from cierre_general_svc import obtener_cierre_general

    data = obtener_cierre_general(cierre_general_id)
    if not data:
        return None
    existente = obtener_provision_por_cierre_general(cierre_general_id)
    if existente and existente.get("estado") == "APLICADA":
        return existente
    return calcular_provision_admin(
        data.get("total_ventas") or 0,
        obtener_saldo_pendiente_provision(),
        data.get("total_efectivo") or 0,
    )


def aplicar_provision_al_consolidar(usuario_admin, cierre_general_id, data_cierre=None):
    """
    Aplica provisión al consolidar. Idempotente si ya existe APLICADA.
    Retorna (ok, mensaje, dict_provision).
    """
    if not _es_admin(usuario_admin):
        return False, "Solo el administrador puede aplicar la provisión", None
    from cierre_general_svc import obtener_cierre_general

    data = data_cierre or obtener_cierre_general(cierre_general_id)
    if not data:
        return False, "Cierre general no encontrado", None

    existente = obtener_provision_por_cierre_general(cierre_general_id)
    if existente and existente.get("estado") == "APLICADA":
        return True, "Provisión ya aplicada", existente

    try:
        ensure_provision_schema()
        cone = FormularioLogin.conexion_base_de_datos()
        cursor = cone.cursor()
        cursor.execute("SELECT Saldo_Pendiente FROM provision_admin_estado WHERE Id=1")
        row = cursor.fetchone()
        pendiente_ant = _round2(row[0] if row else 0)

        calc = calcular_provision_admin(
            data.get("total_ventas") or 0,
            pendiente_ant,
            data.get("total_efectivo") or 0,
        )
        # Integridad: no superar efectivo ni objetivo
        if calc["efectivo_provisionado"] - calc["efectivo_disponible"] > 0.009:
            cone.close()
            return False, "No se puede provisionar más efectivo del disponible", None

        ahora = datetime.now()
        if existente and existente.get("estado") == "ANULADA":
            cursor.execute(
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
                    (usuario_admin or "")[:80],
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
                    int(cierre_general_id),
                ),
            )
            pid = existente["id"]
        else:
            cursor.execute(
                """
                INSERT INTO provision_admin
                    (Cierre_General_Id, Estado, Fecha, Admin_Usuario,
                     Ventas_Generales, Porcentaje, Treinta_Porciento, Provision_Objetivo,
                     Saldo_Pendiente_Anterior, Objetivo_Total, Efectivo_Disponible,
                     Efectivo_Provisionado, Nuevo_Saldo_Pendiente, Observacion)
                VALUES (%s,'APLICADA',%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """,
                (
                    int(cierre_general_id),
                    ahora,
                    (usuario_admin or "")[:80],
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
            pid = cursor.lastrowid

        cursor.execute(
            """
            UPDATE provision_admin_estado
            SET Saldo_Pendiente=%s, Fecha_Actualizacion=%s WHERE Id=1
            """,
            (calc["nuevo_saldo_pendiente"], ahora),
        )
        cone.commit()
        cone.close()

        result = dict(calc)
        result["id"] = int(pid)
        result["cierre_general_id"] = int(cierre_general_id)
        result["estado"] = "APLICADA"
        result["fecha"] = str(ahora)
        result["admin_usuario"] = usuario_admin or ""

        _auditoria(
            usuario_admin,
            "CG#{} ventas={} obj={} ef_disp={} prov={} pend {}→{}".format(
                cierre_general_id,
                calc["ventas_generales"],
                calc["provision_objetivo"],
                calc["efectivo_disponible"],
                calc["efectivo_provisionado"],
                calc["saldo_pendiente_anterior"],
                calc["nuevo_saldo_pendiente"],
            ),
        )
        # Entrega 5: acreditar efectivo provisionado como DINERO REAL del bolsillo admin
        from provision_obligaciones_svc import acreditar_provision_al_bolsillo

        ok_b, msg_b, _bolsa = acreditar_provision_al_bolsillo(
            usuario_admin, cierre_general_id, result
        )
        if not ok_b:
            return (
                False,
                "Provisión aplicada, pero falló el bolsillo admin: {}".format(msg_b),
                result,
            )
        return True, "Provisión administrativa aplicada. {}".format(msg_b), result
    except Exception as error:
        print("Error aplicar provisión: {}".format(error))
        return False, "Error al aplicar provisión: {}".format(error), None


def revertir_provision_por_anulacion(usuario_admin, cierre_general_id):
    """
    Revierte provisión al anular un consolidado.
    Solo si es la última provisión APLICADA (protege cadena de saldos).
    """
    if not _es_admin(usuario_admin):
        return False, "Solo el administrador puede revertir la provisión"
    # Entrega 5: revertir dinero real del bolsillo antes del ledger de pendiente
    from provision_obligaciones_svc import revertir_provision_bolsillo_por_anulacion

    ok_b, msg_b = revertir_provision_bolsillo_por_anulacion(usuario_admin, cierre_general_id)
    if not ok_b:
        return False, msg_b
    prov = obtener_provision_por_cierre_general(cierre_general_id)
    if not prov or prov.get("estado") != "APLICADA":
        return True, "Sin provisión activa que revertir"
    try:
        ensure_provision_schema()
        cone = FormularioLogin.conexion_base_de_datos()
        cursor = cone.cursor()
        cursor.execute(
            """
            SELECT Id, Cierre_General_Id FROM provision_admin
            WHERE Estado='APLICADA' ORDER BY Id DESC LIMIT 1
            """
        )
        ultima = cursor.fetchone()
        if not ultima or int(ultima[1]) != int(cierre_general_id):
            cone.close()
            return (
                False,
                "No se puede anular: hay provisiones posteriores. Anule primero los cierres generales más recientes.",
            )
        cursor.execute(
            """
            UPDATE provision_admin SET Estado='ANULADA',
                Observacion=CONCAT(COALESCE(Observacion,''), ' | ANULADA')
            WHERE Id=%s
            """,
            (prov["id"],),
        )
        cursor.execute(
            """
            UPDATE provision_admin_estado
            SET Saldo_Pendiente=%s, Fecha_Actualizacion=%s WHERE Id=1
            """,
            (prov["saldo_pendiente_anterior"], datetime.now()),
        )
        cone.commit()
        cone.close()
        _auditoria(
            usuario_admin,
            "Revirtió provisión CG#{} pend→{}".format(
                cierre_general_id, prov["saldo_pendiente_anterior"]
            ),
        )
        return True, "Provisión revertida"
    except Exception as error:
        return False, "Error al revertir provisión: {}".format(error)
