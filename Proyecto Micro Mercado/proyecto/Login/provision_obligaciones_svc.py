"""Obligaciones internas de la provisión administrativa (Entrega 5).

Todas consumen el mismo bolsillo: PROVISIÓN ADMINISTRATIVA.
No crean dinero. Diferencian DINERO REAL vs DINERO COMPROMETIDO.

Estructura:
  Empleados | Servicios | Sistema | Arriendo | Otras
"""
from __future__ import annotations

from datetime import datetime

from conexionLogin import FormularioLogin


TIPOS = ("EMPLEADOS", "SERVICIOS", "SISTEMA", "ARRIENDO", "OTRAS")
ESTADOS_OK = ("PENDIENTE", "PAGADA", "ANULADA")


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

        registrar_auditoria(usuario, "Obligaciones provisión", detalle)
    except Exception:
        pass


def ensure_provision_obligaciones_schema(cursor=None):
    own = cursor is None
    cone = None
    if own:
        cone = FormularioLogin.conexion_base_de_datos()
        cursor = cone.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS provision_bolsillo_saldo (
            Id INT PRIMARY KEY,
            Dinero_Real DECIMAL(14,2) NOT NULL DEFAULT 0,
            Fecha_Actualizacion DATETIME NULL
        )
        """
    )
    cursor.execute(
        """
        INSERT IGNORE INTO provision_bolsillo_saldo (Id, Dinero_Real, Fecha_Actualizacion)
        VALUES (1, 0, NULL)
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS provision_empleados_salario (
            Id INT AUTO_INCREMENT PRIMARY KEY,
            Nombre VARCHAR(160) NOT NULL,
            Empleado_Id INT NULL,
            Salario_Mensual DECIMAL(14,2) NOT NULL DEFAULT 0,
            Activo TINYINT NOT NULL DEFAULT 1,
            Usuario VARCHAR(80) DEFAULT '',
            Observacion TEXT NULL,
            Fecha DATETIME,
            INDEX idx_pes_activo (Activo)
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS provision_obligacion (
            Id INT AUTO_INCREMENT PRIMARY KEY,
            Tipo VARCHAR(40) NOT NULL,
            Nombre VARCHAR(160) NOT NULL,
            Descripcion TEXT NULL,
            Categoria VARCHAR(80) DEFAULT '',
            Valor DECIMAL(14,2) NOT NULL DEFAULT 0,
            Estado VARCHAR(20) NOT NULL DEFAULT 'PENDIENTE',
            Fecha_Obligacion DATE NULL,
            Fecha_Vencimiento DATE NULL,
            Fecha_Pago DATETIME NULL,
            Empleado_Salario_Id INT NULL,
            Usuario VARCHAR(80) DEFAULT '',
            Usuario_Pago VARCHAR(80) DEFAULT '',
            Observacion TEXT NULL,
            Cierre_General_Id INT NULL,
            Fecha DATETIME,
            INDEX idx_po_tipo (Tipo),
            INDEX idx_po_estado (Estado),
            INDEX idx_po_fecha (Fecha)
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS provision_bolsillo_mov (
            Id INT AUTO_INCREMENT PRIMARY KEY,
            Tipo VARCHAR(40) NOT NULL,
            Categoria VARCHAR(40) DEFAULT '',
            Monto DECIMAL(14,2) NOT NULL DEFAULT 0,
            Dinero_Real_Ant DECIMAL(14,2) DEFAULT 0,
            Dinero_Real_Nuevo DECIMAL(14,2) DEFAULT 0,
            Comprometido_Ant DECIMAL(14,2) DEFAULT 0,
            Comprometido_Nuevo DECIMAL(14,2) DEFAULT 0,
            Disponible_Ant DECIMAL(14,2) DEFAULT 0,
            Disponible_Nuevo DECIMAL(14,2) DEFAULT 0,
            Obligacion_Id INT NULL,
            Empleado_Salario_Id INT NULL,
            Referencia VARCHAR(120) DEFAULT '',
            Observacion TEXT NULL,
            Usuario VARCHAR(80) DEFAULT '',
            Cierre_General_Id INT NULL,
            Provision_Id INT NULL,
            Estado VARCHAR(20) DEFAULT 'ACTIVO',
            Fecha DATETIME,
            INDEX idx_pbm_fecha (Fecha),
            INDEX idx_pbm_tipo (Tipo),
            INDEX idx_pbm_cg (Cierre_General_Id)
        )
        """
    )
    if own:
        cone.commit()
        cone.close()


def obtener_dinero_real():
    ensure_provision_obligaciones_schema()
    cone = FormularioLogin.conexion_base_de_datos()
    cursor = cone.cursor()
    cursor.execute("SELECT Dinero_Real FROM provision_bolsillo_saldo WHERE Id=1")
    row = cursor.fetchone()
    cone.close()
    return _round2(row[0] if row else 0)


def _set_dinero_real(cursor, valor, ahora=None):
    cursor.execute(
        """
        UPDATE provision_bolsillo_saldo
        SET Dinero_Real=%s, Fecha_Actualizacion=%s WHERE Id=1
        """,
        (_round2(valor), ahora or datetime.now()),
    )


def listar_empleados_salario(solo_activos=True):
    ensure_provision_obligaciones_schema()
    cone = FormularioLogin.conexion_base_de_datos()
    cursor = cone.cursor()
    sql = """
        SELECT Id, Nombre, Empleado_Id, Salario_Mensual, Activo, Usuario, Observacion, Fecha
        FROM provision_empleados_salario
    """
    if solo_activos:
        sql += " WHERE Activo=1"
    sql += " ORDER BY Id DESC"
    cursor.execute(sql)
    out = []
    for r in cursor.fetchall() or []:
        sal = _round2(r[3])
        out.append(
            {
                "id": int(r[0]),
                "nombre": r[1] or "",
                "empleado_id": r[2],
                "salario_mensual": sal,
                "reserva_diaria": _round2(sal / 30.0),
                "activo": int(r[4] or 0) == 1,
                "usuario": r[5] or "",
                "observacion": r[6] or "",
                "fecha": str(r[7] or ""),
            }
        )
    cone.close()
    return out


def calcular_reserva_empleados():
    """SUMA de salarios / 30."""
    total_sal = _round2(sum(e["salario_mensual"] for e in listar_empleados_salario(True)))
    return {
        "salarios_mensuales": total_sal,
        "reserva_diaria": _round2(total_sal / 30.0),
        "empleados": listar_empleados_salario(True),
    }


def calcular_comprometido():
    """Dinero comprometido = reserva diaria empleados + obligaciones PENDIENTE (no empleados)."""
    reserva = calcular_reserva_empleados()["reserva_diaria"]
    cone = FormularioLogin.conexion_base_de_datos()
    cursor = cone.cursor()
    cursor.execute(
        """
        SELECT COALESCE(SUM(Valor), 0) FROM provision_obligacion
        WHERE Estado='PENDIENTE' AND Tipo <> 'EMPLEADOS'
        """
    )
    otras = _round2((cursor.fetchone() or [0])[0])
    cone.close()
    return {
        "empleados": reserva,
        "otras": otras,
        "total": _round2(reserva + otras),
        "reserva_diaria_base": reserva,
    }


def resumen_saldos():
    real = obtener_dinero_real()
    comp = calcular_comprometido()
    disponible = _round2(real - comp["total"])
    return {
        "dinero_real": real,
        "dinero_comprometido": comp["total"],
        "comprometido_empleados": comp["empleados"],
        "comprometido_otras": comp["otras"],
        "disponible": disponible,
        "reserva_diaria_empleados": comp["reserva_diaria_base"],
    }


def listar_obligaciones(tipo=None, estado=None, limite=100):
    ensure_provision_obligaciones_schema()
    cone = FormularioLogin.conexion_base_de_datos()
    cursor = cone.cursor()
    sql = """
        SELECT Id, Tipo, Nombre, Descripcion, Categoria, Valor, Estado,
               Fecha_Obligacion, Fecha_Vencimiento, Fecha_Pago,
               Empleado_Salario_Id, Usuario, Usuario_Pago, Observacion,
               Cierre_General_Id, Fecha
        FROM provision_obligacion WHERE 1=1
    """
    params = []
    if tipo:
        sql += " AND Tipo=%s"
        params.append(tipo)
    if estado:
        sql += " AND Estado=%s"
        params.append(estado)
    sql += " ORDER BY Id DESC LIMIT %s"
    params.append(int(limite))
    cursor.execute(sql, tuple(params))
    out = []
    for r in cursor.fetchall() or []:
        out.append(
            {
                "id": int(r[0]),
                "tipo": r[1] or "",
                "nombre": r[2] or "",
                "descripcion": r[3] or "",
                "categoria": r[4] or "",
                "valor": _round2(r[5]),
                "estado": r[6] or "PENDIENTE",
                "fecha_obligacion": str(r[7] or "")[:10],
                "fecha_vencimiento": str(r[8] or "")[:10],
                "fecha_pago": str(r[9] or ""),
                "empleado_salario_id": r[10],
                "usuario": r[11] or "",
                "usuario_pago": r[12] or "",
                "observacion": r[13] or "",
                "cierre_general_id": r[14],
                "fecha": str(r[15] or ""),
            }
        )
    cone.close()
    return out


def listar_movimientos(limite=80):
    ensure_provision_obligaciones_schema()
    cone = FormularioLogin.conexion_base_de_datos()
    cursor = cone.cursor()
    cursor.execute(
        """
        SELECT Id, Tipo, Categoria, Monto,
               Dinero_Real_Ant, Dinero_Real_Nuevo,
               Comprometido_Ant, Comprometido_Nuevo,
               Disponible_Ant, Disponible_Nuevo,
               Obligacion_Id, Empleado_Salario_Id, Referencia, Observacion,
               Usuario, Cierre_General_Id, Provision_Id, Estado, Fecha
        FROM provision_bolsillo_mov
        WHERE Estado='ACTIVO'
        ORDER BY Id DESC LIMIT %s
        """,
        (int(limite),),
    )
    out = []
    for r in cursor.fetchall() or []:
        out.append(
            {
                "id": int(r[0]),
                "tipo": r[1] or "",
                "categoria": r[2] or "",
                "monto": _round2(r[3]),
                "dinero_real_ant": _round2(r[4]),
                "dinero_real_nuevo": _round2(r[5]),
                "comprometido_ant": _round2(r[6]),
                "comprometido_nuevo": _round2(r[7]),
                "disponible_ant": _round2(r[8]),
                "disponible_nuevo": _round2(r[9]),
                "obligacion_id": r[10],
                "empleado_salario_id": r[11],
                "referencia": r[12] or "",
                "observacion": r[13] or "",
                "usuario": r[14] or "",
                "cierre_general_id": r[15],
                "provision_id": r[16],
                "estado": r[17] or "ACTIVO",
                "fecha": str(r[18] or ""),
            }
        )
    cone.close()
    return out


def resumen_obligaciones_provision(usuario=None):
    if not _es_admin(usuario or ""):
        return {"error": "Solo administrador"}
    ensure_provision_obligaciones_schema()
    saldos = resumen_saldos()
    emp = calcular_reserva_empleados()
    obl = listar_obligaciones(limite=120)
    por_tipo = {t: [] for t in TIPOS}
    for o in obl:
        por_tipo.setdefault(o["tipo"], []).append(o)
    return {
        "saldos": saldos,
        "empleados": emp,
        "obligaciones": obl,
        "por_tipo": por_tipo,
        "movimientos": listar_movimientos(60),
        "desglose_ejemplo": {
            "provision": saldos["dinero_real"],
            "empleados": saldos["comprometido_empleados"],
            "servicios": _round2(
                sum(o["valor"] for o in por_tipo.get("SERVICIOS", []) if o["estado"] == "PENDIENTE")
            ),
            "sistema": _round2(
                sum(o["valor"] for o in por_tipo.get("SISTEMA", []) if o["estado"] == "PENDIENTE")
            ),
            "arriendo": _round2(
                sum(o["valor"] for o in por_tipo.get("ARRIENDO", []) if o["estado"] == "PENDIENTE")
            ),
            "otras": _round2(
                sum(o["valor"] for o in por_tipo.get("OTRAS", []) if o["estado"] == "PENDIENTE")
            ),
            "disponible": saldos["disponible"],
        },
    }


def _insert_mov(cursor, **kw):
    cursor.execute(
        """
        INSERT INTO provision_bolsillo_mov
            (Tipo, Categoria, Monto, Dinero_Real_Ant, Dinero_Real_Nuevo,
             Comprometido_Ant, Comprometido_Nuevo, Disponible_Ant, Disponible_Nuevo,
             Obligacion_Id, Empleado_Salario_Id, Referencia, Observacion,
             Usuario, Cierre_General_Id, Provision_Id, Estado, Fecha)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'ACTIVO',%s)
        """,
        (
            kw.get("tipo"),
            kw.get("categoria") or "",
            _round2(kw.get("monto")),
            _round2(kw.get("dinero_real_ant")),
            _round2(kw.get("dinero_real_nuevo")),
            _round2(kw.get("comprometido_ant")),
            _round2(kw.get("comprometido_nuevo")),
            _round2(kw.get("disponible_ant")),
            _round2(kw.get("disponible_nuevo")),
            kw.get("obligacion_id"),
            kw.get("empleado_salario_id"),
            (kw.get("referencia") or "")[:120],
            (kw.get("observacion") or "")[:2000],
            (kw.get("usuario") or "")[:80],
            kw.get("cierre_general_id"),
            kw.get("provision_id"),
            kw.get("fecha") or datetime.now(),
        ),
    )
    return cursor.lastrowid


def acreditar_provision_al_bolsillo(usuario_admin, cierre_general_id, provision):
    """Al consolidar: el efectivo provisionado entra como DINERO REAL (no crea de la nada)."""
    if not _es_admin(usuario_admin):
        return False, "Solo administrador", None
    ensure_provision_obligaciones_schema()
    monto = _round2((provision or {}).get("efectivo_provisionado"))
    if monto <= 0:
        return True, "Sin efectivo provisionado que acreditar", {"monto": 0}

    cone = FormularioLogin.conexion_base_de_datos()
    cursor = cone.cursor()
    cursor.execute(
        """
        SELECT Id FROM provision_bolsillo_mov
        WHERE Cierre_General_Id=%s AND Tipo='INGRESO_PROVISION' AND Estado='ACTIVO'
        LIMIT 1
        """,
        (int(cierre_general_id),),
    )
    if cursor.fetchone():
        cone.close()
        return True, "Ingreso a bolsillo provisión ya aplicado", {"idempotente": True}

    try:
        saldos_ant = resumen_saldos()
        real_ant = saldos_ant["dinero_real"]
        real_nuevo = _round2(real_ant + monto)
        ahora = datetime.now()
        _set_dinero_real(cursor, real_nuevo, ahora)
        # Recalcular comprometido/disponible con nuevo real
        cone.commit()
        cone.close()
        saldos_nuevos = resumen_saldos()
        cone = FormularioLogin.conexion_base_de_datos()
        cursor = cone.cursor()
        mid = _insert_mov(
            cursor,
            tipo="INGRESO_PROVISION",
            categoria="PROVISION",
            monto=monto,
            dinero_real_ant=real_ant,
            dinero_real_nuevo=real_nuevo,
            comprometido_ant=saldos_ant["dinero_comprometido"],
            comprometido_nuevo=saldos_nuevos["dinero_comprometido"],
            disponible_ant=saldos_ant["disponible"],
            disponible_nuevo=saldos_nuevos["disponible"],
            referencia="CG#{}".format(cierre_general_id),
            observacion="Efectivo provisionado al consolidar (dinero real)",
            usuario=usuario_admin,
            cierre_general_id=int(cierre_general_id),
            provision_id=(provision or {}).get("id"),
            fecha=ahora,
        )
        cone.commit()
        cone.close()
        _auditoria(usuario_admin, "INGRESO_PROVISION CG#{} monto={}".format(cierre_general_id, monto))
        return True, "Efectivo provisionado acreditado al bolsillo admin", {
            "id": mid,
            "monto": monto,
            "saldos": saldos_nuevos,
        }
    except Exception as error:
        return False, "Error al acreditar provisión: {}".format(error), None


def revertir_provision_bolsillo_por_anulacion(usuario_admin, cierre_general_id):
    if not _es_admin(usuario_admin):
        return False, "Solo administrador"
    ensure_provision_obligaciones_schema()
    try:
        cone = FormularioLogin.conexion_base_de_datos()
        cursor = cone.cursor()
        cursor.execute(
            """
            SELECT Id, Monto FROM provision_bolsillo_mov
            WHERE Cierre_General_Id=%s AND Tipo='INGRESO_PROVISION' AND Estado='ACTIVO'
            ORDER BY Id DESC LIMIT 1
            """,
            (int(cierre_general_id),),
        )
        row = cursor.fetchone()
        if not row:
            cone.close()
            return True, "Sin ingreso de provisión activo"
        mid, monto = int(row[0]), _round2(row[1])
        cursor.execute(
            """
            SELECT Id, Cierre_General_Id FROM provision_bolsillo_mov
            WHERE Tipo='INGRESO_PROVISION' AND Estado='ACTIVO'
            ORDER BY Id DESC LIMIT 1
            """
        )
        ult = cursor.fetchone()
        if not ult or int(ult[1]) != int(cierre_general_id):
            cone.close()
            return False, "No se puede anular: hay ingresos de provisión posteriores"
        real = obtener_dinero_real()
        if real + 0.009 < monto:
            cone.close()
            return False, "No se puede revertir: el dinero real ya fue usado en pagos"
        saldos_ant = resumen_saldos()
        real_nuevo = _round2(real - monto)
        ahora = datetime.now()
        _set_dinero_real(cursor, real_nuevo, ahora)
        cursor.execute(
            "UPDATE provision_bolsillo_mov SET Estado='ANULADO' WHERE Id=%s", (mid,)
        )
        cone.commit()
        cone.close()
        saldos_nuevos = resumen_saldos()
        cone = FormularioLogin.conexion_base_de_datos()
        cursor = cone.cursor()
        _insert_mov(
            cursor,
            tipo="ANULACION_INGRESO",
            categoria="PROVISION",
            monto=-monto,
            dinero_real_ant=saldos_ant["dinero_real"],
            dinero_real_nuevo=real_nuevo,
            comprometido_ant=saldos_ant["dinero_comprometido"],
            comprometido_nuevo=saldos_nuevos["dinero_comprometido"],
            disponible_ant=saldos_ant["disponible"],
            disponible_nuevo=saldos_nuevos["disponible"],
            referencia="CG#{}".format(cierre_general_id),
            observacion="Reverso por anulación de consolidado",
            usuario=usuario_admin,
            cierre_general_id=int(cierre_general_id),
            fecha=ahora,
        )
        cone.commit()
        cone.close()
        return True, "Ingreso de provisión revertido"
    except Exception as error:
        return False, "Error: {}".format(error)


def registrar_empleado_salario(usuario_admin, nombre, salario_mensual, empleado_id=None, observacion=""):
    if not _es_admin(usuario_admin):
        return False, "Solo el administrador puede registrar salarios", None
    ensure_provision_obligaciones_schema()
    nombre = str(nombre or "").strip()
    salario = _round2(salario_mensual)
    if not nombre:
        return False, "Indique el nombre del empleado", None
    if salario <= 0:
        return False, "El salario mensual debe ser mayor a 0", None
    try:
        cone = FormularioLogin.conexion_base_de_datos()
        cursor = cone.cursor()
        ahora = datetime.now()
        cursor.execute(
            """
            INSERT INTO provision_empleados_salario
                (Nombre, Empleado_Id, Salario_Mensual, Activo, Usuario, Observacion, Fecha)
            VALUES (%s,%s,%s,1,%s,%s,%s)
            """,
            (
                nombre[:160],
                empleado_id,
                salario,
                (usuario_admin or "")[:80],
                (observacion or "")[:2000],
                ahora,
            ),
        )
        eid = cursor.lastrowid
        cone.commit()
        cone.close()
        _auditoria(usuario_admin, "EMPLEADO {} salario={}".format(nombre, salario))
        return True, "Salario registrado. Reserva diaria = salario/30", {
            "id": eid,
            "reserva_diaria": _round2(salario / 30.0),
            "saldos": resumen_saldos(),
            "empleados": calcular_reserva_empleados(),
        }
    except Exception as error:
        return False, "Error: {}".format(error), None


def desactivar_empleado_salario(usuario_admin, salario_id):
    if not _es_admin(usuario_admin):
        return False, "Solo administrador"
    cone = FormularioLogin.conexion_base_de_datos()
    cursor = cone.cursor()
    cursor.execute(
        "UPDATE provision_empleados_salario SET Activo=0 WHERE Id=%s", (int(salario_id),)
    )
    cone.commit()
    cone.close()
    return True, "Empleado desactivado de la reserva"


def crear_obligacion(
    usuario_admin,
    tipo,
    nombre,
    valor,
    descripcion="",
    categoria="",
    fecha_obligacion=None,
    fecha_vencimiento=None,
    observacion="",
):
    """Crea obligación PENDIENTE. Compromete dinero; NO aumenta dinero real."""
    if not _es_admin(usuario_admin):
        return False, "Solo el administrador puede crear obligaciones", None
    ensure_provision_obligaciones_schema()
    tipo = str(tipo or "").strip().upper()
    if tipo not in ("SERVICIOS", "SISTEMA", "ARRIENDO", "OTRAS"):
        return False, "Tipo inválido. Use SERVICIOS, SISTEMA, ARRIENDO u OTRAS (empleados vía salarios)", None
    nombre = str(nombre or "").strip()
    valor = _round2(valor)
    if not nombre:
        return False, "Indique el nombre", None
    if valor <= 0:
        return False, "El valor debe ser mayor a 0", None

    saldos = resumen_saldos()
    # Al crear, el disponible debe alcanzar (no crear dinero)
    if valor - saldos["disponible"] > 0.009:
        return (
            False,
            "Saldo disponible insuficiente para comprometer. Disponible {}, solicitado {}. "
            "Las obligaciones no crean dinero.".format(saldos["disponible"], valor),
            None,
        )

    try:
        cone = FormularioLogin.conexion_base_de_datos()
        cursor = cone.cursor()
        ahora = datetime.now()
        cursor.execute(
            """
            INSERT INTO provision_obligacion
                (Tipo, Nombre, Descripcion, Categoria, Valor, Estado,
                 Fecha_Obligacion, Fecha_Vencimiento, Usuario, Observacion, Fecha)
            VALUES (%s,%s,%s,%s,%s,'PENDIENTE',%s,%s,%s,%s,%s)
            """,
            (
                tipo,
                nombre[:160],
                (descripcion or "")[:2000],
                (categoria or tipo)[:80],
                valor,
                fecha_obligacion or ahora.date(),
                fecha_vencimiento,
                (usuario_admin or "")[:80],
                (observacion or "")[:2000],
                ahora,
            ),
        )
        oid = cursor.lastrowid
        cone.commit()
        cone.close()
        saldos_nuevos = resumen_saldos()
        cone = FormularioLogin.conexion_base_de_datos()
        cursor = cone.cursor()
        _insert_mov(
            cursor,
            tipo="COMPROMISO",
            categoria=tipo,
            monto=valor,
            dinero_real_ant=saldos["dinero_real"],
            dinero_real_nuevo=saldos["dinero_real"],  # no cambia
            comprometido_ant=saldos["dinero_comprometido"],
            comprometido_nuevo=saldos_nuevos["dinero_comprometido"],
            disponible_ant=saldos["disponible"],
            disponible_nuevo=saldos_nuevos["disponible"],
            obligacion_id=oid,
            referencia=nombre[:120],
            observacion="Compromiso — no crea dinero",
            usuario=usuario_admin,
            fecha=ahora,
        )
        cone.commit()
        cone.close()
        _auditoria(usuario_admin, "COMPROMISO {} {} valor={}".format(tipo, nombre, valor))
        return True, "Obligación registrada (dinero comprometido)", {
            "id": oid,
            "saldos": saldos_nuevos,
        }
    except Exception as error:
        return False, "Error: {}".format(error), None


def pagar_obligacion(usuario_admin, obligacion_id, observacion=""):
    """Paga obligación: descuenta DINERO REAL. No permite saldo negativo."""
    if not _es_admin(usuario_admin):
        return False, "Solo el administrador puede pagar", None
    ensure_provision_obligaciones_schema()
    try:
        cone = FormularioLogin.conexion_base_de_datos()
        cursor = cone.cursor()
        cursor.execute(
            """
            SELECT Id, Tipo, Nombre, Valor, Estado FROM provision_obligacion WHERE Id=%s
            """,
            (int(obligacion_id),),
        )
        row = cursor.fetchone()
        if not row:
            cone.close()
            return False, "Obligación no encontrada", None
        oid, tipo, nombre, valor, estado = (
            int(row[0]),
            row[1],
            row[2],
            _round2(row[3]),
            row[4],
        )
        if estado != "PENDIENTE":
            cone.close()
            return False, "La obligación no está pendiente (estado={})".format(estado), None

        saldos = resumen_saldos()
        if valor - saldos["dinero_real"] > 0.009:
            cone.close()
            return (
                False,
                "Dinero real insuficiente. Real {}, pago {}. Las obligaciones no crean dinero.".format(
                    saldos["dinero_real"], valor
                ),
                None,
            )

        ahora = datetime.now()
        real_nuevo = _round2(saldos["dinero_real"] - valor)
        _set_dinero_real(cursor, real_nuevo, ahora)
        cursor.execute(
            """
            UPDATE provision_obligacion
            SET Estado='PAGADA', Fecha_Pago=%s, Usuario_Pago=%s,
                Observacion=CONCAT(COALESCE(Observacion,''), %s)
            WHERE Id=%s
            """,
            (
                ahora,
                (usuario_admin or "")[:80],
                (" | PAGO: " + observacion)[:500] if observacion else "",
                oid,
            ),
        )
        cone.commit()
        cone.close()
        saldos_nuevos = resumen_saldos()
        cone = FormularioLogin.conexion_base_de_datos()
        cursor = cone.cursor()
        mid = _insert_mov(
            cursor,
            tipo="PAGO",
            categoria=tipo,
            monto=valor,
            dinero_real_ant=saldos["dinero_real"],
            dinero_real_nuevo=real_nuevo,
            comprometido_ant=saldos["dinero_comprometido"],
            comprometido_nuevo=saldos_nuevos["dinero_comprometido"],
            disponible_ant=saldos["disponible"],
            disponible_nuevo=saldos_nuevos["disponible"],
            obligacion_id=oid,
            referencia=(nombre or "")[:120],
            observacion=observacion or "Pago desde provisión administrativa",
            usuario=usuario_admin,
            fecha=ahora,
        )
        cone.commit()
        cone.close()
        _auditoria(usuario_admin, "PAGO {} #{} valor={}".format(tipo, oid, valor))
        return True, "Pago registrado — descontado del bolsillo administrativo", {
            "id": mid,
            "obligacion_id": oid,
            "saldos": saldos_nuevos,
        }
    except Exception as error:
        return False, "Error al pagar: {}".format(error), None


def pagar_nomina_empleados(usuario_admin, observacion=""):
    """Paga la reserva diaria de empleados (suma salarios/30) desde el bolsillo."""
    if not _es_admin(usuario_admin):
        return False, "Solo administrador", None
    reserva = calcular_reserva_empleados()
    monto = reserva["reserva_diaria"]
    if monto <= 0:
        return False, "No hay empleados activos con salario", None
    return _pagar_directo_nomina(usuario_admin, monto, observacion)


def _pagar_directo_nomina(usuario_admin, monto, observacion=""):
    saldos = resumen_saldos()
    if monto - saldos["dinero_real"] > 0.009:
        return (
            False,
            "Dinero real insuficiente. Real {}, solicitado {}".format(saldos["dinero_real"], monto),
            None,
        )
    try:
        cone = FormularioLogin.conexion_base_de_datos()
        cursor = cone.cursor()
        ahora = datetime.now()
        real_nuevo = _round2(saldos["dinero_real"] - monto)
        _set_dinero_real(cursor, real_nuevo, ahora)
        cursor.execute(
            """
            INSERT INTO provision_obligacion
                (Tipo, Nombre, Descripcion, Categoria, Valor, Estado,
                 Fecha_Obligacion, Fecha_Pago, Usuario, Usuario_Pago, Observacion, Fecha)
            VALUES ('EMPLEADOS',%s,%s,'EMPLEADOS',%s,'PAGADA',%s,%s,%s,%s,%s,%s)
            """,
            (
                "Nómina diaria",
                "Suma salarios / 30",
                monto,
                ahora.date(),
                ahora,
                (usuario_admin or "")[:80],
                (usuario_admin or "")[:80],
                (observacion or "Pago nómina")[:2000],
                ahora,
            ),
        )
        oid = cursor.lastrowid
        cone.commit()
        cone.close()
        saldos_nuevos = resumen_saldos()
        cone = FormularioLogin.conexion_base_de_datos()
        cursor = cone.cursor()
        mid = _insert_mov(
            cursor,
            tipo="PAGO",
            categoria="EMPLEADOS",
            monto=monto,
            dinero_real_ant=saldos["dinero_real"],
            dinero_real_nuevo=real_nuevo,
            comprometido_ant=saldos["dinero_comprometido"],
            comprometido_nuevo=saldos_nuevos["dinero_comprometido"],
            disponible_ant=saldos["disponible"],
            disponible_nuevo=saldos_nuevos["disponible"],
            obligacion_id=oid,
            referencia="Nómina diaria",
            observacion=observacion or "Pago nómina desde provisión",
            usuario=usuario_admin,
            fecha=ahora,
        )
        cone.commit()
        cone.close()
        return True, "Nómina pagada desde provisión administrativa", {
            "id": mid,
            "obligacion_id": oid,
            "saldos": saldos_nuevos,
        }
    except Exception as error:
        return False, "Error: {}".format(error), None


def anular_obligacion_pendiente(usuario_admin, obligacion_id, motivo=""):
    if not _es_admin(usuario_admin):
        return False, "Solo administrador"
    cone = FormularioLogin.conexion_base_de_datos()
    cursor = cone.cursor()
    cursor.execute(
        "SELECT Estado, Valor, Tipo, Nombre FROM provision_obligacion WHERE Id=%s",
        (int(obligacion_id),),
    )
    row = cursor.fetchone()
    if not row:
        cone.close()
        return False, "No encontrada"
    if row[0] != "PENDIENTE":
        cone.close()
        return False, "Solo se anulan obligaciones pendientes"
    saldos = resumen_saldos()
    cursor.execute(
        """
        UPDATE provision_obligacion SET Estado='ANULADA',
            Observacion=CONCAT(COALESCE(Observacion,''), %s) WHERE Id=%s
        """,
        ((" | ANULADA: " + motivo)[:500], int(obligacion_id)),
    )
    cone.commit()
    cone.close()
    saldos_nuevos = resumen_saldos()
    cone = FormularioLogin.conexion_base_de_datos()
    cursor = cone.cursor()
    _insert_mov(
        cursor,
        tipo="ANULACION_COMPROMISO",
        categoria=row[2],
        monto=_round2(row[1]),
        dinero_real_ant=saldos["dinero_real"],
        dinero_real_nuevo=saldos["dinero_real"],
        comprometido_ant=saldos["dinero_comprometido"],
        comprometido_nuevo=saldos_nuevos["dinero_comprometido"],
        disponible_ant=saldos["disponible"],
        disponible_nuevo=saldos_nuevos["disponible"],
        obligacion_id=int(obligacion_id),
        referencia=(row[3] or "")[:120],
        observacion=motivo or "Anulación de compromiso",
        usuario=usuario_admin,
    )
    cone.commit()
    cone.close()
    return True, "Obligación anulada — se libera el compromiso"
