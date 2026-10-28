"""API bolsillo de proveedores (Entrega 4). Solo admin. Autocontenido para Railway."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field


MEDIOS = ("Efectivo", "Nequi", "Datafono")
MEDIOS_PAGO = ("Efectivo", "Nequi")
LABEL_BILLETERA = "Billetera digital"


class PagoIn(BaseModel):
    usuario: str
    proveedor: str = ""
    proveedor_nombre: str = ""
    proveedor_id: Optional[int] = None
    total: float = 0
    origenes: list[dict[str, Any]] = Field(default_factory=list)
    referencia: str = ""
    observacion: str = ""
    a_credito: bool = False


class ObligacionIn(BaseModel):
    usuario: str
    proveedor: str = ""
    proveedor_nombre: str = ""
    proveedor_id: Optional[int] = None
    total: float = 0
    referencia: str = ""
    observacion: str = ""


class ReclasificarIn(BaseModel):
    usuario: str
    metodo_origen: str
    metodo_destino: str
    monto: float
    referencia: str = ""
    observacion: str = ""
    cierre_general_id: Optional[int] = None


def _money(v: Any) -> float:
    try:
        return round(float(v or 0), 2)
    except (TypeError, ValueError):
        return 0.0


def _norm_metodo(raw: Any) -> Optional[str]:
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
    ):
        return "Nequi"
    if "data" in t or "tarj" in t or "bold" in t:
        return "Datafono"
    return None


def register(app: FastAPI) -> None:
    from main import execute, json_safe, query

    def has_table(name: str) -> bool:
        rows = query(
            """
            SELECT COUNT(*) AS c FROM information_schema.TABLES
            WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s
            """,
            (name,),
        )
        return bool(rows and int(rows[0]["c"]))

    def ensure() -> None:
        execute(
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
        execute(
            """
            INSERT IGNORE INTO bolsillo_proveedores_saldo (Id, Efectivo, Nequi, Datafono, Fecha_Actualizacion)
            VALUES (1, 0, 0, 0, NULL)
            """
        )
        execute(
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
        execute(
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
        # Legacy Datafono disponible → billetera (Nequi)
        rows = query("SELECT Efectivo, Nequi, Datafono FROM bolsillo_proveedores_saldo WHERE Id=1")
        if rows and _money(rows[0].get("Datafono")) > 0.009:
            ef = _money(rows[0]["Efectivo"])
            nq = _money(rows[0]["Nequi"])
            dt = _money(rows[0]["Datafono"])
            set_saldos(ef, _money(nq + dt), 0.0)

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

    def saldos() -> dict:
        ensure()
        rows = query("SELECT Efectivo, Nequi, Datafono FROM bolsillo_proveedores_saldo WHERE Id=1")
        ef = _money(rows[0]["Efectivo"] if rows else 0)
        nq = _money(rows[0]["Nequi"] if rows else 0)
        dt = _money(rows[0]["Datafono"] if rows else 0)
        pend_rows = query(
            """
            SELECT COALESCE(SUM(Monto), 0) AS t FROM bolsillo_proveedores_pendiente_datafono
            WHERE Estado='PENDIENTE'
            """
        )
        pendiente = _money(pend_rows[0]["t"] if pend_rows else 0)
        disponible = _money(ef + nq + dt)
        return {
            "efectivo": ef,
            "nequi": nq,
            "billetera_digital": nq,
            "datafono": dt,
            "datafono_pendiente": pendiente,
            "disponible": disponible,
            "total": _money(disponible + pendiente),
            "label_nequi": LABEL_BILLETERA,
        }

    def acreditar_datafono_pendientes(usuario: str = "sistema", ahora=None) -> dict:
        ensure()
        ahora = ahora or datetime.now()
        rows = query(
            """
            SELECT Id, Cierre_General_Id, Monto FROM bolsillo_proveedores_pendiente_datafono
            WHERE Estado='PENDIENTE' AND Fecha_Disponible <= %s
            ORDER BY Fecha_Disponible ASC, Id ASC
            """,
            (ahora,),
        )
        if not rows:
            return {"acreditados": 0, "monto": 0.0}
        s = saldos()
        ant_ef, ant_nq, ant_dt = s["efectivo"], s["nequi"], s["datafono"]
        total_acred = 0.0
        ids = []
        for r in rows:
            pid, cg_id, monto = int(r["Id"]), int(r["Cierre_General_Id"]), _money(r["Monto"])
            if monto <= 0:
                execute(
                    "UPDATE bolsillo_proveedores_pendiente_datafono SET Estado='ACREDITADO', Fecha_Acreditacion=%s WHERE Id=%s",
                    (ahora, pid),
                )
                continue
            nuevo_nq = _money(ant_nq + monto)
            mid = execute(
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
                    f"CG#{cg_id}",
                    "Datafono acreditado a billetera digital (T+1 hábil 14:00)",
                    (usuario or "sistema")[:80],
                    cg_id,
                    ahora,
                ),
            )
            execute(
                """
                UPDATE bolsillo_proveedores_pendiente_datafono
                SET Estado='ACREDITADO', Mov_Acreditacion_Id=%s, Fecha_Acreditacion=%s
                WHERE Id=%s
                """,
                (int(mid or 0), ahora, pid),
            )
            ant_nq = nuevo_nq
            total_acred = _money(total_acred + monto)
            ids.append(pid)
        set_saldos(ant_ef, ant_nq, ant_dt, ahora)
        return {"acreditados": len(ids), "monto": total_acred, "ids": ids}

    def set_saldos(ef: float, nq: float, dt: float, ahora=None) -> None:
        execute(
            """
            UPDATE bolsillo_proveedores_saldo
            SET Efectivo=%s, Nequi=%s, Datafono=%s, Fecha_Actualizacion=%s WHERE Id=1
            """,
            (_money(ef), _money(nq), _money(dt), ahora or datetime.now()),
        )

    def map_mov(r: dict) -> dict:
        ef_n = _money(r.get("Saldo_Ef_Nuevo"))
        nq_n = _money(r.get("Saldo_Neq_Nuevo"))
        dt_n = _money(r.get("Saldo_Dat_Nuevo"))
        return {
            "id": int(r["Id"]),
            "tipo": r.get("Tipo") or "",
            "metodo": r.get("Metodo") or "",
            "monto": _money(r.get("Monto")),
            "efectivo": _money(r.get("Efectivo")),
            "nequi": _money(r.get("Nequi")),
            "datafono": _money(r.get("Datafono")),
            "saldo_ef_ant": _money(r.get("Saldo_Ef_Ant")),
            "saldo_neq_ant": _money(r.get("Saldo_Neq_Ant")),
            "saldo_dat_ant": _money(r.get("Saldo_Dat_Ant")),
            "saldo_ef_nuevo": ef_n,
            "saldo_neq_nuevo": nq_n,
            "saldo_dat_nuevo": dt_n,
            "proveedor_id": r.get("Proveedor_Id"),
            "proveedor_nombre": r.get("Proveedor_Nombre") or "",
            "referencia": r.get("Referencia") or "",
            "observacion": r.get("Observacion") or "",
            "usuario": r.get("Usuario") or "",
            "cierre_general_id": r.get("Cierre_General_Id"),
            "provision_id": r.get("Provision_Id"),
            "estado": r.get("Estado") or "ACTIVO",
            "fecha": r.get("Fecha"),
            "total_nuevo": _money(ef_n + nq_n + dt_n),
        }

    def listar_movs(limite: int = 80) -> list:
        if not has_table("bolsillo_proveedores_mov"):
            return []
        rows = query(
            """
            SELECT * FROM bolsillo_proveedores_mov
            WHERE Estado='ACTIVO'
            ORDER BY Id DESC LIMIT %s
            """,
            (int(limite),),
        )
        return [map_mov(r) for r in rows]

    def resumen(usuario: str = Query(...)):
        ensure()
        require_admin(usuario)
        try:
            acreditar_datafono_pendientes(usuario)
        except Exception:
            pass
        s = saldos()
        movs = listar_movs(60)
        pend = query(
            """
            SELECT Id, Cierre_General_Id, Monto, Fecha_Origen, Fecha_Disponible, Estado
            FROM bolsillo_proveedores_pendiente_datafono
            ORDER BY FIELD(Estado, 'PENDIENTE', 'ACREDITADO', 'ANULADO'), Fecha_Disponible ASC
            LIMIT 30
            """
        )
        return json_safe(
            {
                "saldos": s,
                "movimientos": movs,
                "pendientes_datafono": pend or [],
                "ingresos": [
                    m
                    for m in movs
                    if str(m.get("tipo") or "").startswith("INGRESO")
                    or m.get("tipo") == "ACREDITACION_DATAFONO"
                ],
                "pagos": [m for m in movs if m.get("tipo") == "PAGO"],
                "obligaciones": [m for m in movs if m.get("tipo") == "OBLIGACION"],
                "integridad_ok": abs(
                    s.get("disponible", 0) - (s["efectivo"] + s["nequi"] + s["datafono"])
                )
                < 0.02,
                "regla_ingreso": (
                    "Disponible = efectivo sobrante (post-provisión) + billetera digital. "
                    "Datafono → billetera el siguiente día hábil a las 14:00."
                ),
            }
        )

    def registrar_pago(body: PagoIn):
        ensure()
        require_admin(body.usuario)
        nombre = (body.proveedor_nombre or body.proveedor or "").strip()
        if not nombre:
            raise HTTPException(400, "Indique el proveedor")
        total = _money(body.total)
        if body.a_credito:
            if total <= 0:
                raise HTTPException(400, "El valor de la obligación debe ser mayor a 0")
            s = saldos()
            ahora = datetime.now()
            mid = execute(
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
                    s["efectivo"],
                    s["nequi"],
                    s["datafono"],
                    s["efectivo"],
                    s["nequi"],
                    s["datafono"],
                    body.proveedor_id,
                    nombre[:160],
                    (body.referencia or "")[:120],
                    (body.observacion or "Compra/pago a crédito — no afecta dinero disponible")[:2000],
                    (body.usuario or "")[:80],
                    ahora,
                ),
            )
            return json_safe(
                {
                    "ok": True,
                    "mensaje": "Obligación registrada (no afecta saldos de dinero)",
                    "id": mid,
                    "tipo": "OBLIGACION",
                    "saldos": s,
                }
            )

        if total <= 0:
            raise HTTPException(400, "El valor del pago debe ser mayor a 0")
        try:
            acreditar_datafono_pendientes(body.usuario)
        except Exception:
            pass
        componentes = {"Efectivo": 0.0, "Nequi": 0.0}
        for o in body.origenes or []:
            m = _norm_metodo((o or {}).get("metodo"))
            if not m:
                raise HTTPException(400, f"Medio inválido: {(o or {}).get('metodo')}")
            if m == "Datafono":
                raise HTTPException(
                    400,
                    "Use Efectivo o Billetera digital (Datafono se acredita T+1 hábil 14:00)",
                )
            if m not in MEDIOS_PAGO:
                raise HTTPException(400, f"Medio no permitido: {m}")
            componentes[m] = _money(componentes[m] + _money((o or {}).get("monto")))
        suma = _money(sum(componentes.values()))
        if suma - total > 0.02:
            raise HTTPException(400, f"La suma de medios ({suma}) supera el total ({total})")
        credito = _money(total - suma)
        if suma <= 0.009 and credito <= 0.009:
            raise HTTPException(400, "Indique montos en Efectivo y/o Billetera digital")
        s = saldos()
        ant_ef, ant_nq, ant_dt = s["efectivo"], s["nequi"], s["datafono"]
        nuevo_ef, nuevo_nq, nuevo_dt = ant_ef, ant_nq, ant_dt
        ahora = datetime.now()
        mid_pago = None
        if suma > 0.009:
            nuevo_ef = _money(ant_ef - componentes["Efectivo"])
            nuevo_nq = _money(ant_nq - componentes["Nequi"])
            set_saldos(nuevo_ef, nuevo_nq, nuevo_dt, ahora)
            activos = [k for k, v in componentes.items() if v > 0.009]
            if len(activos) > 1:
                metodo_lbl = "MIXTO"
            elif activos and activos[0] == "Nequi":
                metodo_lbl = LABEL_BILLETERA
            else:
                metodo_lbl = activos[0] if activos else "Efectivo"
            obs = body.observacion or ""
            if credito > 0.009:
                obs = (obs + " | " if obs else "") + f"Pago parcial; crédito automático por {credito}"
            mid_pago = execute(
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
                    body.proveedor_id,
                    nombre[:160],
                    (body.referencia or "")[:120],
                    obs[:2000],
                    (body.usuario or "")[:80],
                    ahora,
                ),
            )
            try:
                bolsa = query(
                    "SELECT Id FROM bolsillos WHERE UPPER(Codigo)='PROVEEDORES' AND Activo=1 LIMIT 1"
                )
                if bolsa:
                    bid = int(bolsa[0]["Id"])
                    for metodo, monto in (
                        ("Efectivo", componentes["Efectivo"]),
                        ("Nequi", componentes["Nequi"]),
                    ):
                        if monto <= 0:
                            continue
                        execute(
                            """
                            INSERT INTO bolsillo_movimientos
                                (Bolsillo_Id, Tipo, Monto, Nota, Fecha, Metodo, Categoria, Usuario, Comprobante)
                            VALUES (%s, 'EGRESO', %s, %s, %s, %s, 'PROVEEDOR', %s, %s)
                            """,
                            (
                                bid,
                                monto,
                                f"Pago {nombre} {body.referencia or ''}"[:220],
                                ahora,
                                metodo,
                                (body.usuario or "")[:80],
                                (body.referencia or "")[:100],
                            ),
                        )
            except Exception:
                pass
        mid_cred = None
        if credito > 0.009:
            mid_cred = execute(
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
                    body.proveedor_id,
                    nombre[:160],
                    (body.referencia or "")[:120],
                    (
                        body.observacion
                        or f"Crédito por faltante (total {total} − pagado {suma})"
                    )[:2000],
                    (body.usuario or "")[:80],
                    ahora,
                ),
            )
        nuevos = saldos()
        msg = "Pago registrado"
        if credito > 0.009 and suma > 0.009:
            msg = f"Pago parcial + crédito {credito} registrado"
        elif credito > 0.009:
            msg = "Compra a crédito registrada"
        return json_safe(
            {
                "ok": True,
                "mensaje": msg,
                "id": mid_pago or mid_cred,
                "id_pago": mid_pago,
                "id_credito": mid_cred,
                "tipo": "PAGO" if mid_pago else "OBLIGACION",
                "credito": credito,
                "saldos": nuevos,
                "componentes": componentes,
            }
        )

    def registrar_obligacion(body: ObligacionIn):
        pago = PagoIn(
            usuario=body.usuario,
            proveedor=body.proveedor,
            proveedor_nombre=body.proveedor_nombre,
            proveedor_id=body.proveedor_id,
            total=body.total,
            referencia=body.referencia,
            observacion=body.observacion,
            a_credito=True,
        )
        return registrar_pago(pago)

    def reclasificar(body: ReclasificarIn):
        ensure()
        require_admin(body.usuario)
        origen = _norm_metodo(body.metodo_origen)
        destino = _norm_metodo(body.metodo_destino)
        monto = _money(body.monto)
        if not origen or not destino:
            raise HTTPException(400, "Medios inválidos")
        if origen == destino:
            raise HTTPException(400, "Origen y destino son iguales")
        if monto <= 0:
            raise HTTPException(400, "Monto inválido")
        s = saldos()
        if s[origen.lower()] + 0.009 < monto:
            raise HTTPException(400, f"Saldo insuficiente en {origen}")
        ant_ef, ant_nq, ant_dt = s["efectivo"], s["nequi"], s["datafono"]
        deltas = {"efectivo": 0.0, "nequi": 0.0, "datafono": 0.0}
        deltas[origen.lower()] -= monto
        deltas[destino.lower()] += monto
        nuevo_ef = _money(ant_ef + deltas["efectivo"])
        nuevo_nq = _money(ant_nq + deltas["nequi"])
        nuevo_dt = _money(ant_dt + deltas["datafono"])
        ahora = datetime.now()
        set_saldos(nuevo_ef, nuevo_nq, nuevo_dt, ahora)
        mid = execute(
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
                f"{origen}→{destino}",
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
                (body.referencia or "")[:120],
                (body.observacion or "Corrección auditada de medio de pago")[:2000],
                (body.usuario or "")[:80],
                body.cierre_general_id,
                ahora,
            ),
        )
        return json_safe(
            {
                "ok": True,
                "mensaje": "Medio reclasificado",
                "id": mid,
                "saldos": {
                    "efectivo": nuevo_ef,
                    "nequi": nuevo_nq,
                    "datafono": nuevo_dt,
                    "total": _money(nuevo_ef + nuevo_nq + nuevo_dt),
                },
            }
        )

    app.state.bolsillo_proveedores_helpers = {
        "ensure": ensure,
        "saldos": saldos,
        "set_saldos": set_saldos,
        "require_admin": require_admin,
        "is_admin": is_admin,
        "money": _money,
        "norm_metodo": _norm_metodo,
        "has_table": has_table,
        "acreditar_datafono": acreditar_datafono_pendientes,
    }

    for path, fn, methods in (
        ("/bolsillo-proveedores/", resumen, ["GET"]),
        ("/bolsillo-proveedores/pago/", registrar_pago, ["POST"]),
        ("/bolsillo-proveedores/obligacion/", registrar_obligacion, ["POST"]),
        ("/bolsillo-proveedores/reclasificar/", reclasificar, ["POST"]),
    ):
        app.add_api_route(path, fn, methods=methods, name=f"bp_{fn.__name__}_{methods[0]}")
        app.add_api_route(
            "/api/v1" + path,
            fn,
            methods=methods,
            name=f"bp_{fn.__name__}_{methods[0]}_v1",
        )


def calcular_ingreso_proveedores(data_cierre: dict, provision: dict, fecha_origen=None) -> dict:
    from dias_habiles_co import fecha_acreditacion_datafono

    nequi = max(0.0, _money((data_cierre or {}).get("total_nequi")))
    datafono = max(0.0, _money((data_cierre or {}).get("total_datafono")))
    efectivo = max(0.0, _money((data_cierre or {}).get("total_efectivo")))
    provisionado = max(0.0, _money((provision or {}).get("efectivo_provisionado")))
    pendiente_prov = max(0.0, _money((provision or {}).get("nuevo_saldo_pendiente")))
    sobrante = max(0.0, _money(efectivo - provisionado))
    total_medios = _money(efectivo + nequi + datafono)
    fecha_disp = fecha_acreditacion_datafono(fecha_origen or datetime.now())
    return {
        "efectivo": sobrante,
        "nequi": nequi,
        "billetera_digital": nequi,
        "datafono": 0.0,
        "datafono_pendiente": datafono,
        "datafono_fecha_disponible": fecha_disp.isoformat(sep=" ", timespec="seconds"),
        "total_inmediato": _money(sobrante + nequi),
        "total": _money(total_medios - provisionado),
        "efectivo_disponible_cierre": efectivo,
        "efectivo_provisionado": provisionado,
        "provision_pendiente": pendiente_prov,
        "total_medios_cierre": total_medios,
    }


def aplicar_ingreso_proveedores_api(
    app: FastAPI, usuario: str, cierre_id: int, cierre_data: dict, provision: dict
) -> dict:
    helpers = getattr(app.state, "bolsillo_proveedores_helpers", None)
    if not helpers:
        raise HTTPException(500, "Módulo bolsillo proveedores no inicializado")
    from dias_habiles_co import fecha_acreditacion_datafono
    from main import execute, query

    helpers["ensure"]()
    helpers["require_admin"](usuario)
    existente = query(
        """
        SELECT Id FROM bolsillo_proveedores_mov
        WHERE Cierre_General_Id=%s AND Tipo='INGRESO_CONSOLIDADO' AND Estado='ACTIVO'
        LIMIT 1
        """,
        (int(cierre_id),),
    )
    ahora = datetime.now()
    if existente:
        return {
            "id": int(existente[0]["Id"]),
            "idempotente": True,
            **calcular_ingreso_proveedores(cierre_data, provision, ahora),
        }

    calc = calcular_ingreso_proveedores(cierre_data, provision, ahora)
    if calc["total"] <= 0 and calc.get("datafono_pendiente", 0) <= 0:
        return calc

    s = helpers["saldos"]()
    ant_ef, ant_nq, ant_dt = s["efectivo"], s["nequi"], s["datafono"]
    nuevo_ef = _money(ant_ef + calc["efectivo"])
    nuevo_nq = _money(ant_nq + calc["nequi"])
    nuevo_dt = ant_dt
    helpers["set_saldos"](nuevo_ef, nuevo_nq, nuevo_dt, ahora)
    obs = (
        "Inmediato: efectivo sobrante + billetera digital. "
        f"Datafono pendiente hasta {calc.get('datafono_fecha_disponible')}. "
        f"Provisión admin provisionado={calc.get('efectivo_provisionado')}."
    )
    mid = execute(
        """
        INSERT INTO bolsillo_proveedores_mov
            (Tipo, Metodo, Monto, Efectivo, Nequi, Datafono,
             Saldo_Ef_Ant, Saldo_Neq_Ant, Saldo_Dat_Ant,
             Saldo_Ef_Nuevo, Saldo_Neq_Nuevo, Saldo_Dat_Nuevo,
             Referencia, Observacion, Usuario, Cierre_General_Id, Provision_Id, Estado, Fecha)
        VALUES
            ('INGRESO_CONSOLIDADO', 'MIXTO', %s, %s, %s, %s,
             %s, %s, %s, %s, %s, %s,
             %s, %s, %s, %s, %s, 'ACTIVO', %s)
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
            f"CG#{cierre_id}",
            obs[:2000],
            (usuario or "")[:80],
            int(cierre_id),
            (provision or {}).get("id"),
            ahora,
        ),
    )
    pend = _money(calc.get("datafono_pendiente") or 0)
    if pend > 0.009:
        fecha_disp = fecha_acreditacion_datafono(ahora)
        execute(
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
                int(cierre_id),
                pend,
                ahora,
                fecha_disp,
                int(mid or 0),
                (usuario or "")[:80],
                f"Datafono→billetera {fecha_disp}"[:255],
            ),
        )
    try:
        bolsa = query(
            "SELECT Id FROM bolsillos WHERE UPPER(Codigo)='PROVEEDORES' AND Activo=1 LIMIT 1"
        )
        if bolsa:
            bid = int(bolsa[0]["Id"])
            for metodo, monto in (
                ("Efectivo", calc["efectivo"]),
                ("Nequi", calc["nequi"]),
            ):
                if monto <= 0:
                    continue
                execute(
                    """
                    INSERT INTO bolsillo_movimientos
                        (Bolsillo_Id, Tipo, Monto, Nota, Fecha, Metodo, Categoria, Usuario, Cierre_Id)
                    VALUES (%s, 'INGRESO', %s, %s, %s, %s, 'CONSOLIDADO', %s, %s)
                    """,
                    (
                        bid,
                        monto,
                        f"Proveedores CG#{cierre_id}"[:220],
                        ahora,
                        metodo,
                        (usuario or "")[:80],
                        int(cierre_id),
                    ),
                )
    except Exception:
        pass
    out = dict(calc)
    out.update(
        {
            "id": int(mid or 0),
            "cierre_general_id": int(cierre_id),
            "saldos": helpers["saldos"](),
        }
    )
    return out


def revertir_ingreso_proveedores_api(app: FastAPI, usuario: str, cierre_id: int) -> None:
    helpers = getattr(app.state, "bolsillo_proveedores_helpers", None)
    if not helpers:
        return
    from main import execute, query

    helpers["ensure"]()
    helpers["require_admin"](usuario)
    rows = query(
        """
        SELECT Id, Efectivo, Nequi, Datafono FROM bolsillo_proveedores_mov
        WHERE Cierre_General_Id=%s AND Tipo='INGRESO_CONSOLIDADO' AND Estado='ACTIVO'
        ORDER BY Id DESC LIMIT 1
        """,
        (int(cierre_id),),
    )
    if not rows:
        return
    mid = int(rows[0]["Id"])
    ef, nq, dt = _money(rows[0]["Efectivo"]), _money(rows[0]["Nequi"]), _money(rows[0]["Datafono"])
    ult = query(
        """
        SELECT Id, Cierre_General_Id FROM bolsillo_proveedores_mov
        WHERE Tipo='INGRESO_CONSOLIDADO' AND Estado='ACTIVO'
        ORDER BY Id DESC LIMIT 1
        """
    )
    if not ult or int(ult[0]["Cierre_General_Id"]) != int(cierre_id):
        raise HTTPException(
            400,
            "No se puede anular: hay ingresos a proveedores posteriores. Anule consolidaciones más recientes primero.",
        )
    s = helpers["saldos"]()
    if s["efectivo"] + 0.009 < ef or s["nequi"] + 0.009 < nq or s["datafono"] + 0.009 < dt:
        raise HTTPException(400, "No se puede revertir: el saldo ya fue usado en pagos")
    ant_ef, ant_nq, ant_dt = s["efectivo"], s["nequi"], s["datafono"]
    nuevo_ef = _money(ant_ef - ef)
    nuevo_nq = _money(ant_nq - nq)
    nuevo_dt = _money(ant_dt - dt)
    ahora = datetime.now()
    helpers["set_saldos"](nuevo_ef, nuevo_nq, nuevo_dt, ahora)
    execute("UPDATE bolsillo_proveedores_mov SET Estado='ANULADO' WHERE Id=%s", (mid,))
    execute(
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
            _money(ef + nq + dt),
            -ef,
            -nq,
            -dt,
            ant_ef,
            ant_nq,
            ant_dt,
            nuevo_ef,
            nuevo_nq,
            nuevo_dt,
            f"CG#{cierre_id}",
            (usuario or "")[:80],
            int(cierre_id),
            ahora,
        ),
    )
