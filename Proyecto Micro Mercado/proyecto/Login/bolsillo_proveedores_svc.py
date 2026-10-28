"""Bolsillo de proveedores.

Al consolidar (después de provisión admin — deuda pendiente primero):
  Inmediato: EFECTIVO_SOBRANTE + BILLETERA (ventas Nequi/otras)
  Diferido: DATAFONO → Billetera digital el siguiente día hábil (CO) a las 14:00

Columna DB `Nequi` = Billetera digital (Nequi, Bancolombia, Daviplata, etc.).
Pagos: Efectivo y Billetera separados; permite saldo negativo + crédito por faltante.
Solo administrador.
"""
from __future__ import annotations

from datetime import datetime

from conexionLogin import FormularioLogin
from dias_habiles_co import fecha_acreditacion_datafono


# Códigos internos DB. UI: Nequi → "Billetera digital"
MEDIOS_PROV = ("Efectivo", "Nequi", "Datafono")
MEDIOS_PAGO = ("Efectivo", "Nequi")
LABEL_BILLETERA = "Billetera digital"


def _round2(valor):
    try:
        return round(float(valor or 0), 2)
    except (TypeError, ValueError):
        return 0.0


def _es_admin(usuario):
    from cierre_general_svc import es_usuario_admin

    return es_usuario_admin(usuario)


def _auditoria(usuario, detalle):
    try:
        from Consultas import registrar_auditoria

        registrar_auditoria(usuario, "Bolsillo proveedores", detalle)
    except Exception:
        pass


def label_medio_prov(codigo):
    c = str(codigo or "")
    if c == "Nequi":
        return LABEL_BILLETERA
    return c or ""


def normalizar_metodo_prov(raw):
    t = str(raw or "").strip().lower()
    if "efect" in t or t == "cash":
        return "Efectivo"
    if (
        "nequi" in t
        or "billetera" in t
        or "digital" in t
        or "trans" in t
        or "davi" in t
        or "bancolombia" in t
        or "bre-b" in t
        or "breb" in t
    ):
        return "Nequi"
    if "data" in t or "tarj" in t or "bold" in t:
        return "Datafono"
    if t in {"efectivo", "nequi", "datafono"}:
        return t.capitalize() if t != "datafono" else "Datafono"
    return None


def ensure_bolsillo_proveedores_schema(cursor=None):
    own = cursor is None
    cone = None
    if own:
        cone = FormularioLogin.conexion_base_de_datos()
        cursor = cone.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS bolsillo_proveedores_saldo (
            Id INT PRIMARY KEY,
            Efectivo DECIMAL(14,2) NOT NULL DEFAULT 0,
            Nequi DECIMAL(14,2) NOT NULL DEFAULT 0,
            Datafono DECIMAL(14,2) NOT NULL DEFAULT 0,
            Fecha_Actualizacion DATETIME NULL
        )
        """
    )
    cursor.execute(
        """
        INSERT IGNORE INTO bolsillo_proveedores_saldo (Id, Efectivo, Nequi, Datafono, Fecha_Actualizacion)
        VALUES (1, 0, 0, 0, NULL)
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS bolsillo_proveedores_mov (
            Id INT AUTO_INCREMENT PRIMARY KEY,
            Tipo VARCHAR(40) NOT NULL,
            Metodo VARCHAR(40) DEFAULT '',
            Monto DECIMAL(14,2) NOT NULL DEFAULT 0,
            Efectivo DECIMAL(14,2) NOT NULL DEFAULT 0,
            Nequi DECIMAL(14,2) NOT NULL DEFAULT 0,
            Datafono DECIMAL(14,2) NOT NULL DEFAULT 0,
            Saldo_Ef_Ant DECIMAL(14,2) DEFAULT 0,
            Saldo_Neq_Ant DECIMAL(14,2) DEFAULT 0,
            Saldo_Dat_Ant DECIMAL(14,2) DEFAULT 0,
            Saldo_Ef_Nuevo DECIMAL(14,2) DEFAULT 0,
            Saldo_Neq_Nuevo DECIMAL(14,2) DEFAULT 0,
            Saldo_Dat_Nuevo DECIMAL(14,2) DEFAULT 0,
            Proveedor_Id INT NULL,
            Proveedor_Nombre VARCHAR(160) DEFAULT '',
            Referencia VARCHAR(120) DEFAULT '',
            Observacion TEXT NULL,
            Usuario VARCHAR(80) DEFAULT '',
            Cierre_General_Id INT NULL,
            Provision_Id INT NULL,
            Estado VARCHAR(20) DEFAULT 'ACTIVO',
            Fecha DATETIME,
            INDEX idx_bpm_fecha (Fecha),
            INDEX idx_bpm_tipo (Tipo),
            INDEX idx_bpm_cg (Cierre_General_Id),
            INDEX idx_bpm_estado (Estado)
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS bolsillo_proveedores_pendiente_datafono (
            Id INT AUTO_INCREMENT PRIMARY KEY,
            Cierre_General_Id INT NOT NULL,
            Monto DECIMAL(14,2) NOT NULL DEFAULT 0,
            Fecha_Origen DATETIME NOT NULL,
            Fecha_Disponible DATETIME NOT NULL,
            Estado VARCHAR(20) NOT NULL DEFAULT 'PENDIENTE',
            Mov_Ingreso_Id INT NULL,
            Mov_Acreditacion_Id INT NULL,
            Fecha_Acreditacion DATETIME NULL,
            Usuario VARCHAR(80) DEFAULT '',
            Observacion VARCHAR(255) DEFAULT '',
            UNIQUE KEY uq_bpd_cg (Cierre_General_Id),
            INDEX idx_bpd_estado_disp (Estado, Fecha_Disponible)
        )
        """
    )
    # Saldo legacy Datafono disponible → Billetera (columna Nequi)
    try:
        cursor.execute(
            "SELECT Efectivo, Nequi, Datafono FROM bolsillo_proveedores_saldo WHERE Id=1"
        )
        row = cursor.fetchone()
        if row and _round2(row[2]) > 0.009:
            ef, nq, dt = _round2(row[0]), _round2(row[1]), _round2(row[2])
            _set_saldos(cursor, ef, _round2(nq + dt), 0.0, datetime.now())
    except Exception as error:
        print("Aviso migración Datafono→Billetera: {}".format(error))
    if own:
        cone.commit()
        cone.close()


def _pendiente_datafono_total(cursor=None):
    own = cursor is None
    cone = None
    if own:
        cone = FormularioLogin.conexion_base_de_datos()
        cursor = cone.cursor()
    cursor.execute(
        """
        SELECT COALESCE(SUM(Monto), 0) FROM bolsillo_proveedores_pendiente_datafono
        WHERE Estado='PENDIENTE'
        """
    )
    row = cursor.fetchone()
    total = _round2(row[0] if row else 0)
    if own:
        cone.close()
    return total


def listar_pendientes_datafono(limite=40):
    ensure_bolsillo_proveedores_schema()
    cone = FormularioLogin.conexion_base_de_datos()
    cursor = cone.cursor()
    cursor.execute(
        """
        SELECT Id, Cierre_General_Id, Monto, Fecha_Origen, Fecha_Disponible, Estado,
               Fecha_Acreditacion, Observacion
        FROM bolsillo_proveedores_pendiente_datafono
        ORDER BY FIELD(Estado, 'PENDIENTE', 'ACREDITADO', 'ANULADO'), Fecha_Disponible ASC
        LIMIT %s
        """,
        (int(limite),),
    )
    out = []
    for row in cursor.fetchall() or []:
        out.append(
            {
                "id": int(row[0]),
                "cierre_general_id": int(row[1]) if row[1] is not None else None,
                "monto": _round2(row[2]),
                "fecha_origen": str(row[3] or ""),
                "fecha_disponible": str(row[4] or ""),
                "estado": row[5] or "",
                "fecha_acreditacion": str(row[6] or ""),
                "observacion": row[7] or "",
            }
        )
    cone.close()
    return out


def obtener_saldos_proveedores():
    ensure_bolsillo_proveedores_schema()
    cone = FormularioLogin.conexion_base_de_datos()
    cursor = cone.cursor()
    cursor.execute(
        "SELECT Efectivo, Nequi, Datafono FROM bolsillo_proveedores_saldo WHERE Id=1"
    )
    row = cursor.fetchone() or (0, 0, 0)
    pendiente = _pendiente_datafono_total(cursor)
    cone.close()
    ef, nq, dt = _round2(row[0]), _round2(row[1]), _round2(row[2])
    disponible = _round2(ef + nq + dt)
    return {
        "efectivo": ef,
        "nequi": nq,
        "billetera_digital": nq,
        "datafono": dt,
        "datafono_pendiente": pendiente,
        "disponible": disponible,
        "total": _round2(disponible + pendiente),
        "label_nequi": LABEL_BILLETERA,
    }


def _set_saldos(cursor, ef, nq, dt, ahora=None):
    cursor.execute(
        """
        UPDATE bolsillo_proveedores_saldo
        SET Efectivo=%s, Nequi=%s, Datafono=%s, Fecha_Actualizacion=%s WHERE Id=1
        """,
        (_round2(ef), _round2(nq), _round2(dt), ahora or datetime.now()),
    )


def _row_mov(row):
    if not row:
        return None
    return {
        "id": int(row[0]),
        "tipo": row[1] or "",
        "metodo": row[2] or "",
        "monto": _round2(row[3]),
        "efectivo": _round2(row[4]),
        "nequi": _round2(row[5]),
        "datafono": _round2(row[6]),
        "saldo_ef_ant": _round2(row[7]),
        "saldo_neq_ant": _round2(row[8]),
        "saldo_dat_ant": _round2(row[9]),
        "saldo_ef_nuevo": _round2(row[10]),
        "saldo_neq_nuevo": _round2(row[11]),
        "saldo_dat_nuevo": _round2(row[12]),
        "proveedor_id": row[13],
        "proveedor_nombre": row[14] or "",
        "referencia": row[15] or "",
        "observacion": row[16] or "",
        "usuario": row[17] or "",
        "cierre_general_id": row[18],
        "provision_id": row[19],
        "estado": row[20] or "ACTIVO",
        "fecha": str(row[21] or ""),
        "total_nuevo": _round2(_round2(row[10]) + _round2(row[11]) + _round2(row[12])),
    }


def listar_movimientos_proveedores(limite=80, incluir_anulados=False):
    ensure_bolsillo_proveedores_schema()
    out = []
    cone = FormularioLogin.conexion_base_de_datos()
    cursor = cone.cursor()
    sql = """
        SELECT Id, Tipo, Metodo, Monto, Efectivo, Nequi, Datafono,
               Saldo_Ef_Ant, Saldo_Neq_Ant, Saldo_Dat_Ant,
               Saldo_Ef_Nuevo, Saldo_Neq_Nuevo, Saldo_Dat_Nuevo,
               Proveedor_Id, Proveedor_Nombre, Referencia, Observacion,
               Usuario, Cierre_General_Id, Provision_Id, Estado, Fecha
        FROM bolsillo_proveedores_mov
    """
    if not incluir_anulados:
        sql += " WHERE Estado='ACTIVO'"
    sql += " ORDER BY Id DESC LIMIT %s"
    cursor.execute(sql, (int(limite),))
    for row in cursor.fetchall() or []:
        out.append(_row_mov(row))
    cone.close()
    return out


def resumen_bolsillo_proveedores(usuario=None):
    if not _es_admin(usuario or ""):
        return {
            "error": "Solo administrador",
            "saldos": {
                "efectivo": 0,
                "nequi": 0,
                "billetera_digital": 0,
                "datafono": 0,
                "datafono_pendiente": 0,
                "disponible": 0,
                "total": 0,
            },
        }
    # Acredita Datafono T+1 14:00 si ya venció
    try:
        acreditar_datafono_pendientes(usuario_admin=usuario or "sistema")
    except Exception as error:
        print("Aviso acreditación datafono en resumen: {}".format(error))
    saldos = obtener_saldos_proveedores()
    movs = listar_movimientos_proveedores(60)
    ingresos = [m for m in movs if str(m.get("tipo") or "").startswith("INGRESO") or m.get("tipo") == "ACREDITACION_DATAFONO"]
    pagos = [m for m in movs if m.get("tipo") == "PAGO"]
    obligaciones = [m for m in movs if m.get("tipo") == "OBLIGACION"]
    disponible = _round2(saldos["efectivo"] + saldos["nequi"] + saldos["datafono"])
    return {
        "saldos": saldos,
        "movimientos": movs,
        "pendientes_datafono": listar_pendientes_datafono(30),
        "ingresos": ingresos,
        "pagos": pagos,
        "obligaciones": obligaciones,
        "integridad_ok": abs(saldos.get("disponible", disponible) - disponible) < 0.02,
        "regla_ingreso": (
            "Disponible = efectivo sobrante (post-provisión, deuda admin primero) "
            "+ billetera digital. Datafono → billetera el siguiente día hábil a las 14:00."
        ),
    }


def _ingreso_ya_aplicado(cierre_general_id):
    cone = FormularioLogin.conexion_base_de_datos()
    cursor = cone.cursor()
    cursor.execute(
        """
        SELECT Id FROM bolsillo_proveedores_mov
        WHERE Cierre_General_Id=%s AND Tipo='INGRESO_CONSOLIDADO' AND Estado='ACTIVO'
        LIMIT 1
        """,
        (int(cierre_general_id),),
    )
    row = cursor.fetchone()
    cone.close()
    return int(row[0]) if row else None


def calcular_ingreso_proveedores(data_cierre, provision, fecha_origen=None):
    """
    Opción A: proveedores = total medios − lo realmente provisionado al admin.
    Inmediato: efectivo sobrante + billetera (Nequi).
    Diferido: datafono (pendiente hasta siguiente día hábil 14:00 → billetera).
    """
    nequi = max(0.0, _round2((data_cierre or {}).get("total_nequi")))
    datafono = max(0.0, _round2((data_cierre or {}).get("total_datafono")))
    efectivo = max(0.0, _round2((data_cierre or {}).get("total_efectivo")))
    provisionado = max(0.0, _round2((provision or {}).get("efectivo_provisionado")))
    pendiente_prov = max(0.0, _round2((provision or {}).get("nuevo_saldo_pendiente")))
    sobrante = max(0.0, _round2(efectivo - provisionado))
    total_medios = _round2(efectivo + nequi + datafono)
    total_a_proveedores = _round2(total_medios - provisionado)
    fecha_disp = fecha_acreditacion_datafono(fecha_origen or datetime.now())
    return {
        "efectivo": sobrante,
        "nequi": nequi,
        "billetera_digital": nequi,
        "datafono": 0.0,  # no disponible el mismo día
        "datafono_pendiente": datafono,
        "datafono_fecha_disponible": fecha_disp.isoformat(sep=" ", timespec="seconds"),
        "total_inmediato": _round2(sobrante + nequi),
        "total": total_a_proveedores,
        "efectivo_disponible_cierre": efectivo,
        "efectivo_provisionado": provisionado,
        "provision_pendiente": pendiente_prov,
        "total_medios_cierre": total_medios,
    }


def aplicar_ingreso_proveedores_al_consolidar(usuario_admin, cierre_general_id, data_cierre, provision):
    if not _es_admin(usuario_admin):
        return False, "Solo el administrador puede distribuir proveedores", None
    ensure_bolsillo_proveedores_schema()
    existente = _ingreso_ya_aplicado(cierre_general_id)
    if existente:
        return True, "Ingreso proveedores ya aplicado", {"id": existente, "idempotente": True}

    ahora = datetime.now()
    calc = calcular_ingreso_proveedores(data_cierre, provision, fecha_origen=ahora)
    if calc["total"] <= 0 and calc.get("datafono_pendiente", 0) <= 0:
        return True, "Sin monto a proveedores en este consolidado", calc

    try:
        cone = FormularioLogin.conexion_base_de_datos()
        cursor = cone.cursor()
        cursor.execute(
            "SELECT Efectivo, Nequi, Datafono FROM bolsillo_proveedores_saldo WHERE Id=1"
        )
        row = cursor.fetchone() or (0, 0, 0)
        ant_ef, ant_nq, ant_dt = _round2(row[0]), _round2(row[1]), _round2(row[2])
        # Solo acredita inmediato: efectivo + billetera. Datafono queda pendiente.
        nuevo_ef = _round2(ant_ef + calc["efectivo"])
        nuevo_nq = _round2(ant_nq + calc["nequi"])
        nuevo_dt = ant_dt  # no suma datafono al saldo disponible
        _set_saldos(cursor, nuevo_ef, nuevo_nq, nuevo_dt, ahora)
        obs = (
            "Inmediato: efectivo sobrante + billetera digital. "
            "Datafono pendiente hasta {} (día hábil 14:00). "
            "Provisión admin (deuda primero) provisionado={}."
        ).format(
            calc.get("datafono_fecha_disponible") or "—",
            calc.get("efectivo_provisionado"),
        )
        cursor.execute(
            """
            INSERT INTO bolsillo_proveedores_mov
                (Tipo, Metodo, Monto, Efectivo, Nequi, Datafono,
                 Saldo_Ef_Ant, Saldo_Neq_Ant, Saldo_Dat_Ant,
                 Saldo_Ef_Nuevo, Saldo_Neq_Nuevo, Saldo_Dat_Nuevo,
                 Proveedor_Nombre, Referencia, Observacion, Usuario,
                 Cierre_General_Id, Provision_Id, Estado, Fecha)
            VALUES
                ('INGRESO_CONSOLIDADO', 'MIXTO', %s, %s, %s, %s,
                 %s, %s, %s, %s, %s, %s,
                 '', %s, %s, %s, %s, %s, 'ACTIVO', %s)
            """,
            (
                calc["total"],
                calc["efectivo"],
                calc["nequi"],
                calc.get("datafono_pendiente") or 0.0,
                ant_ef,
                ant_nq,
                ant_dt,
                nuevo_ef,
                nuevo_nq,
                nuevo_dt,
                "CG#{}".format(cierre_general_id),
                obs[:2000],
                (usuario_admin or "")[:80],
                int(cierre_general_id),
                (provision or {}).get("id"),
                ahora,
            ),
        )
        mid = cursor.lastrowid
        pend = _round2(calc.get("datafono_pendiente") or 0)
        if pend > 0.009:
            fecha_disp = fecha_acreditacion_datafono(ahora)
            cursor.execute(
                """
                INSERT INTO bolsillo_proveedores_pendiente_datafono
                    (Cierre_General_Id, Monto, Fecha_Origen, Fecha_Disponible, Estado,
                     Mov_Ingreso_Id, Usuario, Observacion)
                VALUES (%s, %s, %s, %s, 'PENDIENTE', %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    Monto=VALUES(Monto),
                    Fecha_Origen=VALUES(Fecha_Origen),
                    Fecha_Disponible=VALUES(Fecha_Disponible),
                    Estado='PENDIENTE',
                    Mov_Ingreso_Id=VALUES(Mov_Ingreso_Id),
                    Usuario=VALUES(Usuario),
                    Observacion=VALUES(Observacion),
                    Mov_Acreditacion_Id=NULL,
                    Fecha_Acreditacion=NULL
                """,
                (
                    int(cierre_general_id),
                    pend,
                    ahora,
                    fecha_disp,
                    int(mid),
                    (usuario_admin or "")[:80],
                    "Datafono→billetera {}".format(fecha_disp)[:255],
                ),
            )
        try:
            cursor.execute(
                "SELECT Id FROM bolsillos WHERE UPPER(Codigo)='PROVEEDORES' AND Activo=1 LIMIT 1"
            )
            bid = cursor.fetchone()
            if bid:
                for metodo, monto in (
                    ("Efectivo", calc["efectivo"]),
                    ("Nequi", calc["nequi"]),
                ):
                    if monto <= 0:
                        continue
                    cursor.execute(
                        """
                        INSERT INTO bolsillo_movimientos
                            (Bolsillo_Id, Tipo, Monto, Nota, Fecha, Metodo, Categoria, Usuario, Cierre_Id)
                        VALUES (%s, 'INGRESO', %s, %s, %s, %s, 'CONSOLIDADO', %s, %s)
                        """,
                        (
                            int(bid[0]),
                            monto,
                            "Proveedores CG#{}".format(cierre_general_id)[:220],
                            ahora,
                            metodo,
                            (usuario_admin or "")[:80],
                            int(cierre_general_id),
                        ),
                    )
        except Exception as error:
            print("Aviso espejo bolsillo_movimientos: {}".format(error))
        cone.commit()
        cone.close()
        result = dict(calc)
        result.update(
            {
                "id": int(mid),
                "cierre_general_id": int(cierre_general_id),
                "saldos": {
                    "efectivo": nuevo_ef,
                    "nequi": nuevo_nq,
                    "billetera_digital": nuevo_nq,
                    "datafono": nuevo_dt,
                    "datafono_pendiente": _pendiente_datafono_total(),
                    "disponible": _round2(nuevo_ef + nuevo_nq + nuevo_dt),
                    "total": _round2(nuevo_ef + nuevo_nq + nuevo_dt + _pendiente_datafono_total()),
                },
            }
        )
        _auditoria(
            usuario_admin,
            "INGRESO CG#{} ef={} billetera={} data_pend={} total={}".format(
                cierre_general_id,
                calc["efectivo"],
                calc["nequi"],
                calc.get("datafono_pendiente"),
                calc["total"],
            ),
        )
        return True, "Ingreso a bolsillo proveedores aplicado", result
    except Exception as error:
        print("Error ingreso proveedores: {}".format(error))
        return False, "Error al acreditar proveedores: {}".format(error), None


def acreditar_datafono_pendientes(usuario_admin="sistema", ahora=None):
    """Acredita a billetera digital los Datafono con Fecha_Disponible <= ahora (14:00 hábil)."""
    ensure_bolsillo_proveedores_schema()
    ahora = ahora or datetime.now()
    try:
        cone = FormularioLogin.conexion_base_de_datos()
        cursor = cone.cursor()
        cursor.execute(
            """
            SELECT Id, Cierre_General_Id, Monto FROM bolsillo_proveedores_pendiente_datafono
            WHERE Estado='PENDIENTE' AND Fecha_Disponible <= %s
            ORDER BY Fecha_Disponible ASC, Id ASC
            """,
            (ahora,),
        )
        rows = list(cursor.fetchall() or [])
        if not rows:
            cone.close()
            return True, "Sin datafono pendiente a acreditar", {"acreditados": 0, "monto": 0.0}

        cursor.execute(
            "SELECT Efectivo, Nequi, Datafono FROM bolsillo_proveedores_saldo WHERE Id=1"
        )
        s = cursor.fetchone() or (0, 0, 0)
        ant_ef, ant_nq, ant_dt = _round2(s[0]), _round2(s[1]), _round2(s[2])
        total_acred = 0.0
        ids = []
        for row in rows:
            pid, cg_id, monto = int(row[0]), int(row[1]), _round2(row[2])
            if monto <= 0:
                cursor.execute(
                    "UPDATE bolsillo_proveedores_pendiente_datafono SET Estado='ACREDITADO', Fecha_Acreditacion=%s WHERE Id=%s",
                    (ahora, pid),
                )
                continue
            nuevo_nq = _round2(ant_nq + monto)
            cursor.execute(
                """
                INSERT INTO bolsillo_proveedores_mov
                    (Tipo, Metodo, Monto, Efectivo, Nequi, Datafono,
                     Saldo_Ef_Ant, Saldo_Neq_Ant, Saldo_Dat_Ant,
                     Saldo_Ef_Nuevo, Saldo_Neq_Nuevo, Saldo_Dat_Nuevo,
                     Referencia, Observacion, Usuario, Cierre_General_Id, Estado, Fecha)
                VALUES
                    ('ACREDITACION_DATAFONO', %s, %s, 0, %s, 0,
                     %s, %s, %s, %s, %s, %s,
                     %s, %s, %s, %s, 'ACTIVO', %s)
                """,
                (
                    LABEL_BILLETERA,
                    monto,
                    monto,
                    ant_ef,
                    ant_nq,
                    ant_dt,
                    ant_ef,
                    nuevo_nq,
                    ant_dt,
                    "CG#{}".format(cg_id),
                    "Datafono acreditado a billetera digital (T+1 hábil 14:00)",
                    (usuario_admin or "sistema")[:80],
                    cg_id,
                    ahora,
                ),
            )
            mov_id = cursor.lastrowid
            cursor.execute(
                """
                UPDATE bolsillo_proveedores_pendiente_datafono
                SET Estado='ACREDITADO', Mov_Acreditacion_Id=%s, Fecha_Acreditacion=%s
                WHERE Id=%s
                """,
                (int(mov_id), ahora, pid),
            )
            ant_nq = nuevo_nq
            total_acred = _round2(total_acred + monto)
            ids.append(pid)
        _set_saldos(cursor, ant_ef, ant_nq, ant_dt, ahora)
        cone.commit()
        cone.close()
        if total_acred > 0:
            _auditoria(
                usuario_admin,
                "ACREDITACION_DATAFONO monto={} ids={}".format(total_acred, ids),
            )
        return True, "Datafono acreditado a billetera", {
            "acreditados": len(ids),
            "monto": total_acred,
            "ids": ids,
        }
    except Exception as error:
        return False, "Error acreditando datafono: {}".format(error), None

def revertir_ingreso_proveedores_por_anulacion(usuario_admin, cierre_general_id):
    if not _es_admin(usuario_admin):
        return False, "Solo el administrador puede revertir proveedores"
    ensure_bolsillo_proveedores_schema()
    try:
        cone = FormularioLogin.conexion_base_de_datos()
        cursor = cone.cursor()
        cursor.execute(
            """
            SELECT Id, Efectivo, Nequi, Datafono FROM bolsillo_proveedores_mov
            WHERE Cierre_General_Id=%s AND Tipo='INGRESO_CONSOLIDADO' AND Estado='ACTIVO'
            ORDER BY Id DESC LIMIT 1
            """,
            (int(cierre_general_id),),
        )
        row = cursor.fetchone()
        if not row:
            cone.close()
            return True, "Sin ingreso proveedores activo"
        mid, ef, nq, dt_mov = int(row[0]), _round2(row[1]), _round2(row[2]), _round2(row[3])
        # Solo si es el último INGRESO_CONSOLIDADO activo (protege cadena)
        cursor.execute(
            """
            SELECT Id, Cierre_General_Id FROM bolsillo_proveedores_mov
            WHERE Tipo='INGRESO_CONSOLIDADO' AND Estado='ACTIVO'
            ORDER BY Id DESC LIMIT 1
            """
        )
        ult = cursor.fetchone()
        if not ult or int(ult[1]) != int(cierre_general_id):
            cone.close()
            return (
                False,
                "No se puede anular: hay ingresos a proveedores posteriores. Anule consolidaciones más recientes primero.",
            )
        # Pendiente datafono: anular si aún no acreditado; si ya acreditado, restar de billetera
        cursor.execute(
            """
            SELECT Id, Monto, Estado FROM bolsillo_proveedores_pendiente_datafono
            WHERE Cierre_General_Id=%s LIMIT 1
            """,
            (int(cierre_general_id),),
        )
        pend_row = cursor.fetchone()
        datafono_ya_en_billetera = 0.0
        if pend_row:
            if str(pend_row[2] or "") == "PENDIENTE":
                cursor.execute(
                    "UPDATE bolsillo_proveedores_pendiente_datafono SET Estado='ANULADO' WHERE Id=%s",
                    (int(pend_row[0]),),
                )
            elif str(pend_row[2] or "") == "ACREDITADO":
                datafono_ya_en_billetera = _round2(pend_row[1])
                cursor.execute(
                    "UPDATE bolsillo_proveedores_pendiente_datafono SET Estado='ANULADO' WHERE Id=%s",
                    (int(pend_row[0]),),
                )
        # En el movimiento, Datafono era pendiente (no estaba en saldo). Solo restar ef+nequi inmediatos
        # + datafono ya acreditado a billetera.
        reverso_nq = _round2(nq + datafono_ya_en_billetera)
        cursor.execute(
            "SELECT Efectivo, Nequi, Datafono FROM bolsillo_proveedores_saldo WHERE Id=1"
        )
        s = cursor.fetchone() or (0, 0, 0)
        ant_ef, ant_nq, ant_dt = _round2(s[0]), _round2(s[1]), _round2(s[2])
        if ant_ef + 0.009 < ef or ant_nq + 0.009 < reverso_nq:
            cone.close()
            return False, "No se puede revertir: el saldo ya fue usado en pagos"
        nuevo_ef = _round2(ant_ef - ef)
        nuevo_nq = _round2(ant_nq - reverso_nq)
        nuevo_dt = ant_dt
        ahora = datetime.now()
        _set_saldos(cursor, nuevo_ef, nuevo_nq, nuevo_dt, ahora)
        cursor.execute(
            "UPDATE bolsillo_proveedores_mov SET Estado='ANULADO' WHERE Id=%s",
            (mid,),
        )
        # Anular también acreditaciones de datafono de este CG
        cursor.execute(
            """
            UPDATE bolsillo_proveedores_mov SET Estado='ANULADO'
            WHERE Cierre_General_Id=%s AND Tipo='ACREDITACION_DATAFONO' AND Estado='ACTIVO'
            """,
            (int(cierre_general_id),),
        )
        cursor.execute(
            """
            INSERT INTO bolsillo_proveedores_mov
                (Tipo, Metodo, Monto, Efectivo, Nequi, Datafono,
                 Saldo_Ef_Ant, Saldo_Neq_Ant, Saldo_Dat_Ant,
                 Saldo_Ef_Nuevo, Saldo_Neq_Nuevo, Saldo_Dat_Nuevo,
                 Referencia, Observacion, Usuario, Cierre_General_Id, Estado, Fecha)
            VALUES
                ('ANULACION_INGRESO', 'MIXTO', %s, %s, %s, %s,
                 %s, %s, %s, %s, %s, %s,
                 %s, 'Reverso por anulación de consolidado', %s, %s, 'ACTIVO', %s)
            """,
            (
                _round2(ef + reverso_nq + (0 if datafono_ya_en_billetera else dt_mov)),
                -ef,
                -reverso_nq,
                0.0,
                ant_ef,
                ant_nq,
                ant_dt,
                nuevo_ef,
                nuevo_nq,
                nuevo_dt,
                "CG#{}".format(cierre_general_id),
                (usuario_admin or "")[:80],
                int(cierre_general_id),
                ahora,
            ),
        )
        cone.commit()
        cone.close()
        _auditoria(usuario_admin, "REVERSO ingreso proveedores CG#{}".format(cierre_general_id))
        return True, "Ingreso proveedores revertido"
    except Exception as error:
        return False, "Error al revertir proveedores: {}".format(error)


def registrar_pago_proveedor(
    usuario_admin,
    proveedor_nombre,
    total,
    origenes,
    referencia="",
    observacion="",
    proveedor_id=None,
    a_credito=False,
):
    """
    origenes: [{metodo, monto}, ...] — solo Efectivo y Billetera digital (Nequi).
    Si la suma de medios < total, el faltante se registra como OBLIGACION (crédito).
    Permite saldos negativos (la compra no se bloquea).
    a_credito=True: solo OBLIGACION por el total.
    """
    if not _es_admin(usuario_admin):
        return False, "Solo el administrador puede pagar proveedores", None
    try:
        acreditar_datafono_pendientes(usuario_admin=usuario_admin or "sistema")
    except Exception:
        pass
    ensure_bolsillo_proveedores_schema()
    total = _round2(total)
    if total <= 0:
        return False, "El valor del pago debe ser mayor a 0", None
    nombre = str(proveedor_nombre or "").strip()
    if not nombre:
        return False, "Indique el proveedor", None

    componentes = {"Efectivo": 0.0, "Nequi": 0.0}
    for o in origenes or []:
        m = normalizar_metodo_prov((o or {}).get("metodo"))
        if not m:
            return False, "Medio de pago inválido: {}".format((o or {}).get("metodo")), None
        if m == "Datafono":
            return (
                False,
                "Datafono no es medio de pago del bolsillo: use Efectivo o Billetera digital "
                "(el Datafono se acredita solo a billetera al día hábil siguiente 14:00).",
                None,
            )
        if m not in MEDIOS_PAGO:
            return False, "Medio no permitido para pago: {}".format(m), None
        componentes[m] = _round2(componentes[m] + _round2((o or {}).get("monto")))
    suma = _round2(sum(componentes.values()))

    if a_credito:
        try:
            saldos = obtener_saldos_proveedores()
            cone = FormularioLogin.conexion_base_de_datos()
            cursor = cone.cursor()
            ahora = datetime.now()
            cursor.execute(
                """
                INSERT INTO bolsillo_proveedores_mov
                    (Tipo, Metodo, Monto, Efectivo, Nequi, Datafono,
                     Saldo_Ef_Ant, Saldo_Neq_Ant, Saldo_Dat_Ant,
                     Saldo_Ef_Nuevo, Saldo_Neq_Nuevo, Saldo_Dat_Nuevo,
                     Proveedor_Id, Proveedor_Nombre, Referencia, Observacion,
                     Usuario, Estado, Fecha)
                VALUES
                    ('OBLIGACION', 'CREDITO', %s, 0, 0, 0,
                     %s, %s, %s, %s, %s, %s,
                     %s, %s, %s, %s, %s, 'ACTIVO', %s)
                """,
                (
                    total,
                    saldos["efectivo"],
                    saldos["nequi"],
                    saldos["datafono"],
                    saldos["efectivo"],
                    saldos["nequi"],
                    saldos["datafono"],
                    proveedor_id,
                    nombre[:160],
                    (referencia or "")[:120],
                    (observacion or "Compra/pago a crédito — no afecta dinero disponible")[:2000],
                    (usuario_admin or "")[:80],
                    ahora,
                ),
            )
            mid = cursor.lastrowid
            cone.commit()
            cone.close()
            _auditoria(usuario_admin, "OBLIGACION {} total={}".format(nombre, total))
            return True, "Obligación registrada (no afecta saldos de dinero)", {
                "id": mid,
                "tipo": "OBLIGACION",
                "saldos": saldos,
            }
        except Exception as error:
            return False, "Error: {}".format(error), None

    if suma - total > 0.02:
        return False, "La suma de medios ({}) supera el total ({})".format(suma, total), None

    credito = _round2(total - suma)
    if suma <= 0.009 and credito <= 0.009:
        return False, "Indique montos en Efectivo y/o Billetera digital, o use obligación a crédito", None

    saldos = obtener_saldos_proveedores()
    # Permite negativo: no se bloquea por saldo insuficiente

    try:
        cone = FormularioLogin.conexion_base_de_datos()
        cursor = cone.cursor()
        ant_ef, ant_nq, ant_dt = saldos["efectivo"], saldos["nequi"], saldos["datafono"]
        nuevo_ef = ant_ef
        nuevo_nq = ant_nq
        nuevo_dt = ant_dt
        mid_pago = None
        ahora = datetime.now()

        if suma > 0.009:
            nuevo_ef = _round2(ant_ef - componentes["Efectivo"])
            nuevo_nq = _round2(ant_nq - componentes["Nequi"])
            _set_saldos(cursor, nuevo_ef, nuevo_nq, nuevo_dt, ahora)
            activos = [k for k, v in componentes.items() if v > 0.009]
            if len(activos) > 1:
                metodo_lbl = "MIXTO"
            elif activos and activos[0] == "Nequi":
                metodo_lbl = LABEL_BILLETERA
            else:
                metodo_lbl = activos[0] if activos else "Efectivo"
            obs_pago = observacion or ""
            if credito > 0.009:
                obs_pago = (
                    (obs_pago + " | " if obs_pago else "")
                    + "Pago parcial; crédito automático por {}".format(credito)
                )
            if nuevo_ef < -0.009 or nuevo_nq < -0.009:
                obs_pago = (obs_pago + " | " if obs_pago else "") + "Saldo en negativo permitido"
            cursor.execute(
                """
                INSERT INTO bolsillo_proveedores_mov
                    (Tipo, Metodo, Monto, Efectivo, Nequi, Datafono,
                     Saldo_Ef_Ant, Saldo_Neq_Ant, Saldo_Dat_Ant,
                     Saldo_Ef_Nuevo, Saldo_Neq_Nuevo, Saldo_Dat_Nuevo,
                     Proveedor_Id, Proveedor_Nombre, Referencia, Observacion,
                     Usuario, Estado, Fecha)
                VALUES
                    ('PAGO', %s, %s, %s, %s, 0,
                     %s, %s, %s, %s, %s, %s,
                     %s, %s, %s, %s, %s, 'ACTIVO', %s)
                """,
                (
                    metodo_lbl,
                    suma,
                    componentes["Efectivo"],
                    componentes["Nequi"],
                    ant_ef,
                    ant_nq,
                    ant_dt,
                    nuevo_ef,
                    nuevo_nq,
                    nuevo_dt,
                    proveedor_id,
                    nombre[:160],
                    (referencia or "")[:120],
                    obs_pago[:2000],
                    (usuario_admin or "")[:80],
                    ahora,
                ),
            )
            mid_pago = cursor.lastrowid
            try:
                cursor.execute(
                    "SELECT Id FROM bolsillos WHERE UPPER(Codigo)='PROVEEDORES' AND Activo=1 LIMIT 1"
                )
                bid = cursor.fetchone()
                if bid:
                    for metodo, monto in (
                        ("Efectivo", componentes["Efectivo"]),
                        ("Nequi", componentes["Nequi"]),
                    ):
                        if monto <= 0:
                            continue
                        cursor.execute(
                            """
                            INSERT INTO bolsillo_movimientos
                                (Bolsillo_Id, Tipo, Monto, Nota, Fecha, Metodo, Categoria, Usuario, Comprobante)
                            VALUES (%s, 'EGRESO', %s, %s, %s, %s, 'PROVEEDOR', %s, %s)
                            """,
                            (
                                int(bid[0]),
                                monto,
                                "Pago {} {}".format(nombre, referencia or "")[:220],
                                ahora,
                                metodo,
                                (usuario_admin or "")[:80],
                                (referencia or "")[:100],
                            ),
                        )
            except Exception as error:
                print("Aviso espejo egreso proveedores: {}".format(error))

        mid_cred = None
        if credito > 0.009:
            cursor.execute(
                """
                INSERT INTO bolsillo_proveedores_mov
                    (Tipo, Metodo, Monto, Efectivo, Nequi, Datafono,
                     Saldo_Ef_Ant, Saldo_Neq_Ant, Saldo_Dat_Ant,
                     Saldo_Ef_Nuevo, Saldo_Neq_Nuevo, Saldo_Dat_Nuevo,
                     Proveedor_Id, Proveedor_Nombre, Referencia, Observacion,
                     Usuario, Estado, Fecha)
                VALUES
                    ('OBLIGACION', 'CREDITO', %s, 0, 0, 0,
                     %s, %s, %s, %s, %s, %s,
                     %s, %s, %s, %s, %s, 'ACTIVO', %s)
                """,
                (
                    credito,
                    nuevo_ef,
                    nuevo_nq,
                    nuevo_dt,
                    nuevo_ef,
                    nuevo_nq,
                    nuevo_dt,
                    proveedor_id,
                    nombre[:160],
                    (referencia or "")[:120],
                    (
                        observacion
                        or "Crédito por faltante de dinero en compra (total {} − pagado {})".format(
                            total, suma
                        )
                    )[:2000],
                    (usuario_admin or "")[:80],
                    ahora,
                ),
            )
            mid_cred = cursor.lastrowid

        cone.commit()
        cone.close()
        nuevos = {
            "efectivo": nuevo_ef,
            "nequi": nuevo_nq,
            "billetera_digital": nuevo_nq,
            "datafono": nuevo_dt,
            "datafono_pendiente": _pendiente_datafono_total(),
            "disponible": _round2(nuevo_ef + nuevo_nq + nuevo_dt),
            "total": _round2(nuevo_ef + nuevo_nq + nuevo_dt + _pendiente_datafono_total()),
        }
        _auditoria(
            usuario_admin,
            "PAGO/CRED {} total={} ef={} billetera={} credito={}".format(
                nombre, total, componentes["Efectivo"], componentes["Nequi"], credito
            ),
        )
        msg = "Pago registrado"
        if credito > 0.009 and suma > 0.009:
            msg = "Pago parcial + crédito {} registrado".format(credito)
        elif credito > 0.009:
            msg = "Compra a crédito registrada"
        return True, msg, {
            "id": mid_pago or mid_cred,
            "id_pago": mid_pago,
            "id_credito": mid_cred,
            "tipo": "PAGO" if mid_pago else "OBLIGACION",
            "credito": credito,
            "saldos": nuevos,
            "componentes": componentes,
        }
    except Exception as error:
        return False, "Error al registrar pago: {}".format(error), None


def reclasificar_medio_bolsillo(
    usuario_admin,
    metodo_origen,
    metodo_destino,
    monto,
    referencia="",
    observacion="",
    cierre_general_id=None,
):
    """Mueve saldo entre medios del bolsillo sin cambiar el total (corrección auditada)."""
    if not _es_admin(usuario_admin):
        return False, "Solo el administrador puede corregir medios en proveedores", None
    ensure_bolsillo_proveedores_schema()
    origen = normalizar_metodo_prov(metodo_origen)
    destino = normalizar_metodo_prov(metodo_destino)
    monto = _round2(monto)
    if not origen or not destino:
        return False, "Medios de pago inválidos", None
    if origen == destino:
        return False, "Origen y destino son iguales", None
    if monto <= 0:
        return False, "El monto debe ser mayor a 0", None

    saldos = obtener_saldos_proveedores()
    key_o = origen.lower()
    key_d = destino.lower()
    if saldos[key_o] + 0.009 < monto:
        return (
            False,
            "Saldo insuficiente en {} para reclasificar (disp. {})".format(origen, saldos[key_o]),
            None,
        )

    try:
        cone = FormularioLogin.conexion_base_de_datos()
        cursor = cone.cursor()
        ant_ef, ant_nq, ant_dt = saldos["efectivo"], saldos["nequi"], saldos["datafono"]
        deltas = {"efectivo": 0.0, "nequi": 0.0, "datafono": 0.0}
        deltas[key_o] -= monto
        deltas[key_d] += monto
        nuevo_ef = _round2(ant_ef + deltas["efectivo"])
        nuevo_nq = _round2(ant_nq + deltas["nequi"])
        nuevo_dt = _round2(ant_dt + deltas["datafono"])
        ahora = datetime.now()
        _set_saldos(cursor, nuevo_ef, nuevo_nq, nuevo_dt, ahora)
        cursor.execute(
            """
            INSERT INTO bolsillo_proveedores_mov
                (Tipo, Metodo, Monto, Efectivo, Nequi, Datafono,
                 Saldo_Ef_Ant, Saldo_Neq_Ant, Saldo_Dat_Ant,
                 Saldo_Ef_Nuevo, Saldo_Neq_Nuevo, Saldo_Dat_Nuevo,
                 Referencia, Observacion, Usuario, Cierre_General_Id, Estado, Fecha)
            VALUES
                ('CORRECCION_MEDIO', %s, %s, %s, %s, %s,
                 %s, %s, %s, %s, %s, %s,
                 %s, %s, %s, %s, 'ACTIVO', %s)
            """,
            (
                "{}→{}".format(origen, destino),
                monto,
                deltas["efectivo"],
                deltas["nequi"],
                deltas["datafono"],
                ant_ef,
                ant_nq,
                ant_dt,
                nuevo_ef,
                nuevo_nq,
                nuevo_dt,
                (referencia or "")[:120],
                (observacion or "Corrección auditada de medio de pago")[:2000],
                (usuario_admin or "")[:80],
                cierre_general_id,
                ahora,
            ),
        )
        mid = cursor.lastrowid
        cone.commit()
        cone.close()
        nuevos = {
            "efectivo": nuevo_ef,
            "nequi": nuevo_nq,
            "datafono": nuevo_dt,
            "total": _round2(nuevo_ef + nuevo_nq + nuevo_dt),
        }
        _auditoria(
            usuario_admin,
            "CORRECCION {}→{} monto={} total_bolsillo={}".format(
                origen, destino, monto, nuevos["total"]
            ),
        )
        return True, "Medio reclasificado en bolsillo proveedores", {
            "id": mid,
            "saldos": nuevos,
            "origen": origen,
            "destino": destino,
            "monto": monto,
        }
    except Exception as error:
        return False, "Error al reclasificar: {}".format(error), None


def sincronizar_correccion_venta_si_consolidado(
    id_venta, metodo_origen, metodo_destino, monto, usuario, motivo=""
):
    """Si la venta ya alimentó proveedores vía CG consolidado, ajusta saldos del bolsillo."""
    ensure_bolsillo_proveedores_schema()
    origen = normalizar_metodo_prov(metodo_origen)
    destino = normalizar_metodo_prov(metodo_destino)
    monto = _round2(monto)
    if not origen or not destino or origen == destino or monto <= 0:
        return False, "Sin ajuste"
    try:
        cone = FormularioLogin.conexion_base_de_datos()
        cursor = cone.cursor()
        # Preferir vínculo por Cierre_Id de la corrección / último cierre del cajero
        cursor.execute(
            """
            SELECT g.Id
            FROM venta_pago_correcciones c
            JOIN cierre_general_dias d ON d.Cierre_Turno_Id = c.Cierre_Id
            JOIN cierre_general g ON g.Id = d.Cierre_General_Id AND g.Estado='CONSOLIDADO'
            JOIN bolsillo_proveedores_mov m
              ON m.Cierre_General_Id = g.Id
             AND m.Tipo='INGRESO_CONSOLIDADO' AND m.Estado='ACTIVO'
            WHERE c.Venta_Id=%s AND c.Cierre_Id IS NOT NULL
            ORDER BY c.Id DESC LIMIT 1
            """,
            (int(id_venta),),
        )
        row = cursor.fetchone()
        if not row:
            cursor.execute(
                """
                SELECT g.Id
                FROM ventas v
                JOIN cierre_turno ct ON (ct.Cajero = v.Usuario OR ct.Cajero = %s)
                  AND ct.Fecha <= v.Fecha
                JOIN cierre_general_dias d ON d.Cierre_Turno_Id = ct.Id
                JOIN cierre_general g ON g.Id = d.Cierre_General_Id AND g.Estado='CONSOLIDADO'
                JOIN bolsillo_proveedores_mov m
                  ON m.Cierre_General_Id = g.Id
                 AND m.Tipo='INGRESO_CONSOLIDADO' AND m.Estado='ACTIVO'
                WHERE v.Id=%s
                ORDER BY ct.Id DESC, g.Id DESC
                LIMIT 1
                """,
                ((usuario or "")[:80], int(id_venta)),
            )
            row = cursor.fetchone()
        cone.close()
        if not row:
            return False, "Venta no ligada a consolidado con ingreso proveedores"
        cg_id = int(row[0])
        return reclasificar_medio_bolsillo(
            usuario,
            origen,
            destino,
            monto,
            referencia="Venta#{}".format(id_venta),
            observacion=motivo or "Sync corrección venta post-consolidado",
            cierre_general_id=cg_id,
        )
    except Exception as error:
        print("Aviso sync corrección proveedores: {}".format(error))
        return False, str(error)
