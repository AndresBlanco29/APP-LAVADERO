"""API obligaciones de provisión administrativa (Entrega 5). Solo admin. Autocontenido."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field


TIPOS = ("SERVICIOS", "SISTEMA", "ARRIENDO", "OTRAS")


class EmpleadoIn(BaseModel):
    usuario: str
    nombre: str
    salario_mensual: float
    empleado_id: Optional[int] = None
    observacion: str = ""


class ObligacionIn(BaseModel):
    usuario: str
    tipo: str
    nombre: str
    valor: float
    descripcion: str = ""
    categoria: str = ""
    fecha_obligacion: Optional[str] = None
    fecha_vencimiento: Optional[str] = None
    observacion: str = ""


class PagoObligacionIn(BaseModel):
    usuario: str
    observacion: str = ""


class NominaIn(BaseModel):
    usuario: str
    observacion: str = ""


class AnularObligacionIn(BaseModel):
    usuario: str
    motivo: str = ""


def _money(v: Any) -> float:
    try:
        return round(float(v or 0), 2)
    except (TypeError, ValueError):
        return 0.0


def register(app: FastAPI) -> None:
    from main import execute, json_safe, query

    def ensure() -> None:
        execute(
            """
            CREATE TABLE IF NOT EXISTS provision_bolsillo_saldo (
                Id INT PRIMARY KEY,
                Dinero_Real DECIMAL(14,2) NOT NULL DEFAULT 0,
                Fecha_Actualizacion DATETIME NULL
            )
            """
        )
        execute(
            "INSERT IGNORE INTO provision_bolsillo_saldo (Id, Dinero_Real, Fecha_Actualizacion) VALUES (1, 0, NULL)"
        )
        execute(
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
        execute(
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
        execute(
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

    def dinero_real() -> float:
        ensure()
        rows = query("SELECT Dinero_Real FROM provision_bolsillo_saldo WHERE Id=1")
        return _money(rows[0]["Dinero_Real"] if rows else 0)

    def set_dinero_real(valor: float, ahora=None) -> None:
        execute(
            "UPDATE provision_bolsillo_saldo SET Dinero_Real=%s, Fecha_Actualizacion=%s WHERE Id=1",
            (_money(valor), ahora or datetime.now()),
        )

    def empleados(solo_activos: bool = True) -> list:
        ensure()
        sql = "SELECT * FROM provision_empleados_salario"
        if solo_activos:
            sql += " WHERE Activo=1"
        sql += " ORDER BY Id DESC"
        rows = query(sql)
        out = []
        for r in rows:
            sal = _money(r.get("Salario_Mensual"))
            out.append(
                {
                    "id": int(r["Id"]),
                    "nombre": r.get("Nombre") or "",
                    "empleado_id": r.get("Empleado_Id"),
                    "salario_mensual": sal,
                    "reserva_diaria": _money(sal / 30.0),
                    "activo": int(r.get("Activo") or 0) == 1,
                    "usuario": r.get("Usuario") or "",
                    "observacion": r.get("Observacion") or "",
                    "fecha": r.get("Fecha"),
                }
            )
        return out

    def reserva_empleados() -> dict:
        lista = empleados(True)
        total = _money(sum(e["salario_mensual"] for e in lista))
        return {
            "salarios_mensuales": total,
            "reserva_diaria": _money(total / 30.0),
            "empleados": lista,
        }

    def comprometido() -> dict:
        reserva = reserva_empleados()["reserva_diaria"]
        rows = query(
            """
            SELECT COALESCE(SUM(Valor), 0) AS s FROM provision_obligacion
            WHERE Estado='PENDIENTE' AND Tipo <> 'EMPLEADOS'
            """
        )
        otras = _money(rows[0]["s"] if rows else 0)
        return {
            "empleados": reserva,
            "otras": otras,
            "total": _money(reserva + otras),
            "reserva_diaria_base": reserva,
        }

    def saldos() -> dict:
        real = dinero_real()
        comp = comprometido()
        return {
            "dinero_real": real,
            "dinero_comprometido": comp["total"],
            "comprometido_empleados": comp["empleados"],
            "comprometido_otras": comp["otras"],
            "disponible": _money(real - comp["total"]),
            "reserva_diaria_empleados": comp["reserva_diaria_base"],
        }

    def map_obl(r: dict) -> dict:
        return {
            "id": int(r["Id"]),
            "tipo": r.get("Tipo") or "",
            "nombre": r.get("Nombre") or "",
            "descripcion": r.get("Descripcion") or "",
            "categoria": r.get("Categoria") or "",
            "valor": _money(r.get("Valor")),
            "estado": r.get("Estado") or "PENDIENTE",
            "fecha_obligacion": str(r.get("Fecha_Obligacion") or "")[:10],
            "fecha_vencimiento": str(r.get("Fecha_Vencimiento") or "")[:10],
            "fecha_pago": r.get("Fecha_Pago"),
            "usuario": r.get("Usuario") or "",
            "usuario_pago": r.get("Usuario_Pago") or "",
            "observacion": r.get("Observacion") or "",
            "fecha": r.get("Fecha"),
        }

    def listar_obl(limite: int = 120) -> list:
        rows = query(
            "SELECT * FROM provision_obligacion ORDER BY Id DESC LIMIT %s", (int(limite),)
        )
        return [map_obl(r) for r in rows]

    def listar_mov(limite: int = 60) -> list:
        rows = query(
            """
            SELECT * FROM provision_bolsillo_mov WHERE Estado='ACTIVO'
            ORDER BY Id DESC LIMIT %s
            """,
            (int(limite),),
        )
        out = []
        for r in rows:
            out.append(
                {
                    "id": int(r["Id"]),
                    "tipo": r.get("Tipo") or "",
                    "categoria": r.get("Categoria") or "",
                    "monto": _money(r.get("Monto")),
                    "dinero_real_ant": _money(r.get("Dinero_Real_Ant")),
                    "dinero_real_nuevo": _money(r.get("Dinero_Real_Nuevo")),
                    "comprometido_ant": _money(r.get("Comprometido_Ant")),
                    "comprometido_nuevo": _money(r.get("Comprometido_Nuevo")),
                    "disponible_ant": _money(r.get("Disponible_Ant")),
                    "disponible_nuevo": _money(r.get("Disponible_Nuevo")),
                    "obligacion_id": r.get("Obligacion_Id"),
                    "referencia": r.get("Referencia") or "",
                    "observacion": r.get("Observacion") or "",
                    "usuario": r.get("Usuario") or "",
                    "cierre_general_id": r.get("Cierre_General_Id"),
                    "fecha": r.get("Fecha"),
                }
            )
        return out

    def insert_mov(**kw) -> int:
        return execute(
            """
            INSERT INTO provision_bolsillo_mov
                (Tipo, Categoria, Monto, Dinero_Real_Ant, Dinero_Real_Nuevo,
                 Comprometido_Ant, Comprometido_Nuevo, Disponible_Ant, Disponible_Nuevo,
                 Obligacion_Id, Referencia, Observacion, Usuario, Cierre_General_Id,
                 Provision_Id, Estado, Fecha)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'ACTIVO',%s)
            """,
            (
                kw.get("tipo"),
                kw.get("categoria") or "",
                _money(kw.get("monto")),
                _money(kw.get("dinero_real_ant")),
                _money(kw.get("dinero_real_nuevo")),
                _money(kw.get("comprometido_ant")),
                _money(kw.get("comprometido_nuevo")),
                _money(kw.get("disponible_ant")),
                _money(kw.get("disponible_nuevo")),
                kw.get("obligacion_id"),
                (kw.get("referencia") or "")[:120],
                (kw.get("observacion") or "")[:2000],
                (kw.get("usuario") or "")[:80],
                kw.get("cierre_general_id"),
                kw.get("provision_id"),
                kw.get("fecha") or datetime.now(),
            ),
        )

    def resumen(usuario: str = Query(...)):
        ensure()
        require_admin(usuario)
        s = saldos()
        emp = reserva_empleados()
        obl = listar_obl()
        por_tipo: dict = {t: [] for t in ("EMPLEADOS", "SERVICIOS", "SISTEMA", "ARRIENDO", "OTRAS")}
        for o in obl:
            por_tipo.setdefault(o["tipo"], []).append(o)
        return json_safe(
            {
                "saldos": s,
                "empleados": emp,
                "obligaciones": obl,
                "por_tipo": por_tipo,
                "movimientos": listar_mov(),
                "desglose_ejemplo": {
                    "provision": s["dinero_real"],
                    "empleados": s["comprometido_empleados"],
                    "servicios": _money(
                        sum(o["valor"] for o in por_tipo.get("SERVICIOS", []) if o["estado"] == "PENDIENTE")
                    ),
                    "sistema": _money(
                        sum(o["valor"] for o in por_tipo.get("SISTEMA", []) if o["estado"] == "PENDIENTE")
                    ),
                    "arriendo": _money(
                        sum(o["valor"] for o in por_tipo.get("ARRIENDO", []) if o["estado"] == "PENDIENTE")
                    ),
                    "otras": _money(
                        sum(o["valor"] for o in por_tipo.get("OTRAS", []) if o["estado"] == "PENDIENTE")
                    ),
                    "disponible": s["disponible"],
                },
            }
        )

    def post_empleado(body: EmpleadoIn):
        ensure()
        require_admin(body.usuario)
        nombre = (body.nombre or "").strip()
        sal = _money(body.salario_mensual)
        if not nombre:
            raise HTTPException(400, "Indique el nombre")
        if sal <= 0:
            raise HTTPException(400, "Salario mensual debe ser mayor a 0")
        eid = execute(
            """
            INSERT INTO provision_empleados_salario
                (Nombre, Empleado_Id, Salario_Mensual, Activo, Usuario, Observacion, Fecha)
            VALUES (%s,%s,%s,1,%s,%s,%s)
            """,
            (
                nombre[:160],
                body.empleado_id,
                sal,
                (body.usuario or "")[:80],
                (body.observacion or "")[:2000],
                datetime.now(),
            ),
        )
        return json_safe(
            {
                "ok": True,
                "mensaje": "Salario registrado. Reserva diaria = salario/30",
                "id": eid,
                "reserva_diaria": _money(sal / 30.0),
                "saldos": saldos(),
                "empleados": reserva_empleados(),
            }
        )

    def post_obligacion(body: ObligacionIn):
        ensure()
        require_admin(body.usuario)
        tipo = (body.tipo or "").strip().upper()
        if tipo not in TIPOS:
            raise HTTPException(400, "Tipo inválido")
        nombre = (body.nombre or "").strip()
        valor = _money(body.valor)
        if not nombre:
            raise HTTPException(400, "Indique el nombre")
        if valor <= 0:
            raise HTTPException(400, "Valor inválido")
        s = saldos()
        if valor - s["disponible"] > 0.009:
            raise HTTPException(
                400,
                f"Disponible insuficiente ({s['disponible']}). Las obligaciones no crean dinero.",
            )
        ahora = datetime.now()
        oid = execute(
            """
            INSERT INTO provision_obligacion
                (Tipo, Nombre, Descripcion, Categoria, Valor, Estado,
                 Fecha_Obligacion, Fecha_Vencimiento, Usuario, Observacion, Fecha)
            VALUES (%s,%s,%s,%s,%s,'PENDIENTE',%s,%s,%s,%s,%s)
            """,
            (
                tipo,
                nombre[:160],
                (body.descripcion or "")[:2000],
                (body.categoria or tipo)[:80],
                valor,
                body.fecha_obligacion or ahora.date(),
                body.fecha_vencimiento,
                (body.usuario or "")[:80],
                (body.observacion or "")[:2000],
                ahora,
            ),
        )
        s2 = saldos()
        insert_mov(
            tipo="COMPROMISO",
            categoria=tipo,
            monto=valor,
            dinero_real_ant=s["dinero_real"],
            dinero_real_nuevo=s["dinero_real"],
            comprometido_ant=s["dinero_comprometido"],
            comprometido_nuevo=s2["dinero_comprometido"],
            disponible_ant=s["disponible"],
            disponible_nuevo=s2["disponible"],
            obligacion_id=oid,
            referencia=nombre[:120],
            observacion="Compromiso — no crea dinero",
            usuario=body.usuario,
            fecha=ahora,
        )
        return json_safe({"ok": True, "mensaje": "Obligación registrada", "id": oid, "saldos": s2})

    def post_pago(obligacion_id: int, body: PagoObligacionIn):
        ensure()
        require_admin(body.usuario)
        rows = query("SELECT * FROM provision_obligacion WHERE Id=%s", (int(obligacion_id),))
        if not rows:
            raise HTTPException(404, "Obligación no encontrada")
        r = rows[0]
        if (r.get("Estado") or "") != "PENDIENTE":
            raise HTTPException(400, f"No está pendiente ({r.get('Estado')})")
        valor = _money(r.get("Valor"))
        s = saldos()
        if valor - s["dinero_real"] > 0.009:
            raise HTTPException(
                400,
                f"Dinero real insuficiente ({s['dinero_real']}). Las obligaciones no crean dinero.",
            )
        ahora = datetime.now()
        real_nuevo = _money(s["dinero_real"] - valor)
        set_dinero_real(real_nuevo, ahora)
        execute(
            """
            UPDATE provision_obligacion
            SET Estado='PAGADA', Fecha_Pago=%s, Usuario_Pago=%s WHERE Id=%s
            """,
            (ahora, (body.usuario or "")[:80], int(obligacion_id)),
        )
        s2 = saldos()
        mid = insert_mov(
            tipo="PAGO",
            categoria=r.get("Tipo") or "",
            monto=valor,
            dinero_real_ant=s["dinero_real"],
            dinero_real_nuevo=real_nuevo,
            comprometido_ant=s["dinero_comprometido"],
            comprometido_nuevo=s2["dinero_comprometido"],
            disponible_ant=s["disponible"],
            disponible_nuevo=s2["disponible"],
            obligacion_id=int(obligacion_id),
            referencia=(r.get("Nombre") or "")[:120],
            observacion=body.observacion or "Pago desde provisión administrativa",
            usuario=body.usuario,
            fecha=ahora,
        )
        return json_safe({"ok": True, "mensaje": "Pago registrado", "id": mid, "saldos": s2})

    def post_nomina(body: NominaIn):
        ensure()
        require_admin(body.usuario)
        emp = reserva_empleados()
        monto = emp["reserva_diaria"]
        if monto <= 0:
            raise HTTPException(400, "No hay empleados activos con salario")
        s = saldos()
        if monto - s["dinero_real"] > 0.009:
            raise HTTPException(400, f"Dinero real insuficiente ({s['dinero_real']})")
        ahora = datetime.now()
        real_nuevo = _money(s["dinero_real"] - monto)
        set_dinero_real(real_nuevo, ahora)
        oid = execute(
            """
            INSERT INTO provision_obligacion
                (Tipo, Nombre, Descripcion, Categoria, Valor, Estado,
                 Fecha_Obligacion, Fecha_Pago, Usuario, Usuario_Pago, Observacion, Fecha)
            VALUES ('EMPLEADOS','Nómina diaria','Suma salarios / 30','EMPLEADOS',%s,'PAGADA',
                    %s,%s,%s,%s,%s,%s)
            """,
            (
                monto,
                ahora.date(),
                ahora,
                (body.usuario or "")[:80],
                (body.usuario or "")[:80],
                (body.observacion or "Pago nómina")[:2000],
                ahora,
            ),
        )
        s2 = saldos()
        mid = insert_mov(
            tipo="PAGO",
            categoria="EMPLEADOS",
            monto=monto,
            dinero_real_ant=s["dinero_real"],
            dinero_real_nuevo=real_nuevo,
            comprometido_ant=s["dinero_comprometido"],
            comprometido_nuevo=s2["dinero_comprometido"],
            disponible_ant=s["disponible"],
            disponible_nuevo=s2["disponible"],
            obligacion_id=oid,
            referencia="Nómina diaria",
            observacion=body.observacion or "Pago nómina",
            usuario=body.usuario,
            fecha=ahora,
        )
        return json_safe({"ok": True, "mensaje": "Nómina pagada", "id": mid, "saldos": s2})

    def post_anular(obligacion_id: int, body: AnularObligacionIn):
        ensure()
        require_admin(body.usuario)
        rows = query("SELECT * FROM provision_obligacion WHERE Id=%s", (int(obligacion_id),))
        if not rows:
            raise HTTPException(404, "No encontrada")
        if (rows[0].get("Estado") or "") != "PENDIENTE":
            raise HTTPException(400, "Solo pendientes")
        s = saldos()
        execute(
            "UPDATE provision_obligacion SET Estado='ANULADA' WHERE Id=%s",
            (int(obligacion_id),),
        )
        s2 = saldos()
        insert_mov(
            tipo="ANULACION_COMPROMISO",
            categoria=rows[0].get("Tipo") or "",
            monto=_money(rows[0].get("Valor")),
            dinero_real_ant=s["dinero_real"],
            dinero_real_nuevo=s["dinero_real"],
            comprometido_ant=s["dinero_comprometido"],
            comprometido_nuevo=s2["dinero_comprometido"],
            disponible_ant=s["disponible"],
            disponible_nuevo=s2["disponible"],
            obligacion_id=int(obligacion_id),
            referencia=(rows[0].get("Nombre") or "")[:120],
            observacion=body.motivo or "Anulación",
            usuario=body.usuario,
        )
        return json_safe({"ok": True, "mensaje": "Obligación anulada", "saldos": s2})

    app.state.provision_obligaciones_helpers = {
        "ensure": ensure,
        "saldos": saldos,
        "dinero_real": dinero_real,
        "set_dinero_real": set_dinero_real,
        "require_admin": require_admin,
        "is_admin": is_admin,
        "money": _money,
        "insert_mov": insert_mov,
    }

    for path, fn, methods in (
        ("/provision-obligaciones/", resumen, ["GET"]),
        ("/provision-obligaciones/empleado/", post_empleado, ["POST"]),
        ("/provision-obligaciones/obligacion/", post_obligacion, ["POST"]),
        ("/provision-obligaciones/obligacion/{obligacion_id}/pagar/", post_pago, ["POST"]),
        ("/provision-obligaciones/obligacion/{obligacion_id}/anular/", post_anular, ["POST"]),
        ("/provision-obligaciones/nomina/", post_nomina, ["POST"]),
    ):
        app.add_api_route(path, fn, methods=methods, name=f"po_{fn.__name__}_{methods[0]}")
        app.add_api_route(
            "/api/v1" + path,
            fn,
            methods=methods,
            name=f"po_{fn.__name__}_{methods[0]}_v1",
        )


def acreditar_provision_bolsillo_api(app: FastAPI, usuario: str, cierre_id: int, provision: dict) -> dict:
    helpers = getattr(app.state, "provision_obligaciones_helpers", None)
    if not helpers:
        # Módulo no registrado aún: no fallar consolidación de Entrega 3
        return {"monto": 0, "omitido": True}
    from main import execute, query

    helpers["ensure"]()
    helpers["require_admin"](usuario)
    monto = helpers["money"]((provision or {}).get("efectivo_provisionado"))
    if monto <= 0:
        return {"monto": 0}
    existe = query(
        """
        SELECT Id FROM provision_bolsillo_mov
        WHERE Cierre_General_Id=%s AND Tipo='INGRESO_PROVISION' AND Estado='ACTIVO' LIMIT 1
        """,
        (int(cierre_id),),
    )
    if existe:
        return {"id": int(existe[0]["Id"]), "idempotente": True, "monto": monto}
    s = helpers["saldos"]()
    real_nuevo = helpers["money"](s["dinero_real"] + monto)
    ahora = datetime.now()
    helpers["set_dinero_real"](real_nuevo, ahora)
    s2 = helpers["saldos"]()
    mid = helpers["insert_mov"](
        tipo="INGRESO_PROVISION",
        categoria="PROVISION",
        monto=monto,
        dinero_real_ant=s["dinero_real"],
        dinero_real_nuevo=real_nuevo,
        comprometido_ant=s["dinero_comprometido"],
        comprometido_nuevo=s2["dinero_comprometido"],
        disponible_ant=s["disponible"],
        disponible_nuevo=s2["disponible"],
        referencia=f"CG#{cierre_id}",
        observacion="Efectivo provisionado al consolidar (dinero real)",
        usuario=usuario,
        cierre_general_id=int(cierre_id),
        provision_id=(provision or {}).get("id"),
        fecha=ahora,
    )
    return {"id": mid, "monto": monto, "saldos": s2}


def revertir_provision_bolsillo_api(app: FastAPI, usuario: str, cierre_id: int) -> None:
    helpers = getattr(app.state, "provision_obligaciones_helpers", None)
    if not helpers:
        return
    from main import execute, query

    helpers["ensure"]()
    helpers["require_admin"](usuario)
    rows = query(
        """
        SELECT Id, Monto FROM provision_bolsillo_mov
        WHERE Cierre_General_Id=%s AND Tipo='INGRESO_PROVISION' AND Estado='ACTIVO'
        ORDER BY Id DESC LIMIT 1
        """,
        (int(cierre_id),),
    )
    if not rows:
        return
    mid, monto = int(rows[0]["Id"]), helpers["money"](rows[0]["Monto"])
    ult = query(
        """
        SELECT Id, Cierre_General_Id FROM provision_bolsillo_mov
        WHERE Tipo='INGRESO_PROVISION' AND Estado='ACTIVO'
        ORDER BY Id DESC LIMIT 1
        """
    )
    if not ult or int(ult[0]["Cierre_General_Id"]) != int(cierre_id):
        raise HTTPException(400, "No se puede anular: hay ingresos de provisión posteriores")
    s = helpers["saldos"]()
    if s["dinero_real"] + 0.009 < monto:
        raise HTTPException(400, "No se puede revertir: el dinero real ya fue usado en pagos")
    real_nuevo = helpers["money"](s["dinero_real"] - monto)
    ahora = datetime.now()
    helpers["set_dinero_real"](real_nuevo, ahora)
    execute("UPDATE provision_bolsillo_mov SET Estado='ANULADO' WHERE Id=%s", (mid,))
    s2 = helpers["saldos"]()
    helpers["insert_mov"](
        tipo="ANULACION_INGRESO",
        categoria="PROVISION",
        monto=-monto,
        dinero_real_ant=s["dinero_real"],
        dinero_real_nuevo=real_nuevo,
        comprometido_ant=s["dinero_comprometido"],
        comprometido_nuevo=s2["dinero_comprometido"],
        disponible_ant=s["disponible"],
        disponible_nuevo=s2["disponible"],
        referencia=f"CG#{cierre_id}",
        observacion="Reverso por anulación de consolidado",
        usuario=usuario,
        cierre_general_id=int(cierre_id),
        fecha=ahora,
    )
