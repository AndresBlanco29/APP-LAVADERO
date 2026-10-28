"""API cierre general administrativo (Entrega 2). Solo admin. Autocontenido para Railway."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field


CHECKLIST = (
    ("chk_efectivo", "Chk_Efectivo", "Efectivo verificado"),
    ("chk_nequi", "Chk_Nequi", "Nequi verificado"),
    ("chk_datafono", "Chk_Datafono", "Datafono verificado"),
    ("chk_ventas", "Chk_Ventas", "Ventas conciliadas"),
    ("chk_correcciones", "Chk_Correcciones", "Correcciones revisadas"),
    ("chk_descuadres", "Chk_Descuadres", "Descuadres revisados"),
    ("chk_observaciones", "Chk_Observaciones", "Observaciones revisadas"),
    ("chk_validado", "Chk_Validado", "Cierre validado"),
)


class CrearGeneralIn(BaseModel):
    usuario: str
    ids_cierres: list[int] = Field(default_factory=list)
    titulo: str = ""
    observacion: str = ""


class ChecklistIn(BaseModel):
    usuario: str
    cierre_turno_id: int
    checklist: dict[str, Any] = Field(default_factory=dict)
    nota_admin: str = ""


class AccionGeneralIn(BaseModel):
    usuario: str
    motivo: str = ""


def _money(v: Any) -> float:
    try:
        return round(float(v or 0), 2)
    except (TypeError, ValueError):
        return 0.0


def register(app: FastAPI) -> None:
    from main import execute, has_column, json_safe, now_bogota, query

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
            CREATE TABLE IF NOT EXISTS cierre_general (
                Id INT AUTO_INCREMENT PRIMARY KEY,
                Estado VARCHAR(40) NOT NULL DEFAULT 'BORRADOR',
                Titulo VARCHAR(120) DEFAULT '',
                Fecha_Creacion DATETIME,
                Fecha_Actualizacion DATETIME NULL,
                Fecha_Consolidacion DATETIME NULL,
                Admin_Usuario VARCHAR(80) DEFAULT '',
                Admin_Id INT NULL,
                Observacion TEXT NULL,
                Total_Ventas DECIMAL(14,2) DEFAULT 0,
                Total_Efectivo DECIMAL(14,2) DEFAULT 0,
                Total_Nequi DECIMAL(14,2) DEFAULT 0,
                Total_Datafono DECIMAL(14,2) DEFAULT 0,
                Total_Diferencia DECIMAL(14,2) DEFAULT 0,
                INDEX idx_cg_estado (Estado)
            )
            """
        )
        execute(
            """
            CREATE TABLE IF NOT EXISTS cierre_general_dias (
                Id INT AUTO_INCREMENT PRIMARY KEY,
                Cierre_General_Id INT NOT NULL,
                Cierre_Turno_Id INT NOT NULL,
                Estado_Dia VARCHAR(40) DEFAULT 'PENDIENTE',
                Chk_Efectivo TINYINT DEFAULT 0,
                Chk_Nequi TINYINT DEFAULT 0,
                Chk_Datafono TINYINT DEFAULT 0,
                Chk_Ventas TINYINT DEFAULT 0,
                Chk_Correcciones TINYINT DEFAULT 0,
                Chk_Descuadres TINYINT DEFAULT 0,
                Chk_Observaciones TINYINT DEFAULT 0,
                Chk_Validado TINYINT DEFAULT 0,
                Nota_Admin TEXT NULL,
                INDEX idx_cgd_general (Cierre_General_Id),
                INDEX idx_cgd_turno (Cierre_Turno_Id),
                UNIQUE KEY uq_cgd_general_turno (Cierre_General_Id, Cierre_Turno_Id)
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

    def admin_id(usuario: str) -> Optional[int]:
        for col in ("Id_admin", "id_admin", "Id_Admin", "id"):
            if has_column("admin", col):
                rows = query(
                    f"SELECT `{col}` AS id FROM admin WHERE LOWER(usuario)=LOWER(%s) LIMIT 1",
                    (usuario.strip(),),
                )
                if rows:
                    return int(rows[0]["id"])
        return None

    def medios_turno(cid: int, ct: dict) -> dict:
        efectivo = nequi = datafono = diferencia = 0.0
        if has_table("cierre_turno_medios"):
            for r in query(
                "SELECT Metodo, Etiqueta, Sistema, Declarado, Diferencia FROM cierre_turno_medios WHERE Cierre_Id=%s",
                (cid,),
            ):
                m = str(r.get("Metodo") or "")
                e = str(r.get("Etiqueta") or "").upper()
                decl = _money(r.get("Declarado") if r.get("Declarado") is not None else r.get("Sistema"))
                if m == "Efectivo" or e == "EFECTIVO":
                    efectivo = decl
                    diferencia = _money(r.get("Diferencia"))
                elif m in ("Nequi", "Transferencia") or e == "NEQUI":
                    nequi += decl
                elif m == "Tarjeta" or e == "DATAFONO":
                    datafono = decl
        if efectivo == 0:
            efectivo = _money(ct.get("Efectivo"))
        if nequi == 0:
            nequi = _money(ct.get("Nequi")) + _money(ct.get("Transferencia"))
        if datafono == 0:
            datafono = _money(ct.get("Tarjeta"))
        if abs(diferencia) < 0.009:
            diferencia = _money(ct.get("Descuadre"))
        return {
            "efectivo": _money(efectivo),
            "nequi": _money(nequi),
            "datafono": _money(datafono),
            "diferencia": _money(diferencia),
        }

    def resumen_diario(cid: int) -> Optional[dict]:
        rows = query("SELECT * FROM cierre_turno WHERE Id=%s", (cid,))
        if not rows:
            return None
        ct = rows[0]
        m = medios_turno(cid, ct)
        corr = []
        if has_table("venta_pago_correcciones"):
            corr = query(
                "SELECT * FROM venta_pago_correcciones WHERE Cierre_Id=%s ORDER BY Id DESC LIMIT 100",
                (cid,),
            )
        medios_lista = []
        if has_table("cierre_turno_medios"):
            medios_lista = query(
                "SELECT Metodo, Etiqueta, Sistema, Declarado, Diferencia FROM cierre_turno_medios WHERE Cierre_Id=%s",
                (cid,),
            )
        return json_safe(
            {
                "id": cid,
                "fecha": ct.get("Fecha"),
                "vendedor": ct.get("Cajero") or ct.get("Usuario") or "",
                "ventas": _money(ct.get("Total_Ventas")),
                **m,
                "estado": ct.get("Estado") or "",
                "correcciones_count": int(ct.get("Correcciones") or 0),
                "observaciones": ct.get("Observacion") or "",
                "usuario": ct.get("Usuario") or "",
                "medios": medios_lista,
                "correcciones": corr,
            }
        )

    def diarios_disponibles(
        usuario: str = Query(...),
        incluir_en_general_id: Optional[int] = None,
    ):
        ensure()
        require_admin(usuario)
        if not has_table("cierre_turno"):
            return []
        if incluir_en_general_id:
            rows = query(
                """
                SELECT * FROM cierre_turno ct
                WHERE COALESCE(ct.Tipo,'definitivo') <> 'temporal'
                  AND (
                    ct.Id NOT IN (
                      SELECT d.Cierre_Turno_Id FROM cierre_general_dias d
                      JOIN cierre_general g ON g.Id=d.Cierre_General_Id
                      WHERE g.Estado='CONSOLIDADO'
                    )
                    OR ct.Id IN (
                      SELECT d2.Cierre_Turno_Id FROM cierre_general_dias d2
                      WHERE d2.Cierre_General_Id=%s
                    )
                  )
                ORDER BY ct.Fecha DESC LIMIT 200
                """,
                (incluir_en_general_id,),
            )
        else:
            rows = query(
                """
                SELECT * FROM cierre_turno ct
                WHERE COALESCE(ct.Tipo,'definitivo') <> 'temporal'
                  AND ct.Id NOT IN (
                      SELECT d.Cierre_Turno_Id FROM cierre_general_dias d
                      JOIN cierre_general g ON g.Id=d.Cierre_General_Id
                      WHERE g.Estado='CONSOLIDADO'
                  )
                ORDER BY ct.Fecha DESC LIMIT 200
                """
            )
        out = []
        for ct in rows:
            m = medios_turno(int(ct["Id"]), ct)
            out.append(
                {
                    "id": int(ct["Id"]),
                    "fecha": str(ct.get("Fecha") or ""),
                    "vendedor": ct.get("Cajero") or ct.get("Usuario") or "",
                    "ventas": _money(ct.get("Total_Ventas")),
                    **m,
                    "estado": ct.get("Estado") or "",
                    "correcciones": int(ct.get("Correcciones") or 0),
                    "observaciones": ct.get("Observacion") or "",
                }
            )
        return json_safe(out)

    def diario_detalle(cierre_turno_id: int, usuario: str = Query(...)):
        ensure()
        require_admin(usuario)
        data = resumen_diario(cierre_turno_id)
        if not data:
            raise HTTPException(404, "Cierre diario no encontrado")
        return data

    def checklist_of(d: dict) -> dict:
        return {k: bool(int(d.get(col) or 0)) for k, col, _ in CHECKLIST}

    def estado_dia(chk: dict, diferencia: float) -> str:
        if abs(_money(diferencia)) >= 0.5:
            return "CON_DESCUADRE"
        if chk.get("chk_validado") and all(chk.get(k) for k, _c, _l in CHECKLIST):
            return "VERIFICADO"
        return "PENDIENTE"

    def obtener(gid: int) -> Optional[dict]:
        rows = query("SELECT * FROM cierre_general WHERE Id=%s", (gid,))
        if not rows:
            return None
        g = rows[0]
        dias_raw = query(
            "SELECT * FROM cierre_general_dias WHERE Cierre_General_Id=%s ORDER BY Id",
            (gid,),
        )
        dias = []
        for d in dias_raw:
            tid = int(d["Cierre_Turno_Id"])
            det = resumen_diario(tid) or {}
            chk = checklist_of(d)
            dias.append(
                {
                    "id": int(d["Id"]),
                    "cierre_turno_id": tid,
                    "estado_dia": d.get("Estado_Dia") or "PENDIENTE",
                    "checklist": chk,
                    "nota_admin": d.get("Nota_Admin") or "",
                    "fecha": det.get("fecha") or "",
                    "vendedor": det.get("vendedor") or "",
                    "ventas": det.get("ventas") or 0,
                    "efectivo": det.get("efectivo") or 0,
                    "nequi": det.get("nequi") or 0,
                    "datafono": det.get("datafono") or 0,
                    "diferencia": det.get("diferencia") or 0,
                    "estado_cierre": det.get("estado") or "",
                    "correcciones": det.get("correcciones_count") or 0,
                    "observaciones": det.get("observaciones") or "",
                    "detalle": det,
                }
            )
        return json_safe(
            {
                "id": int(g["Id"]),
                "estado": g.get("Estado") or "BORRADOR",
                "titulo": g.get("Titulo") or "",
                "fecha_creacion": g.get("Fecha_Creacion"),
                "fecha_consolidacion": g.get("Fecha_Consolidacion"),
                "admin_usuario": g.get("Admin_Usuario") or "",
                "observacion": g.get("Observacion") or "",
                "total_ventas": _money(g.get("Total_Ventas")),
                "total_efectivo": _money(g.get("Total_Efectivo")),
                "total_nequi": _money(g.get("Total_Nequi")),
                "total_datafono": _money(g.get("Total_Datafono")),
                "total_diferencia": _money(g.get("Total_Diferencia")),
                "dias": dias,
                "checklist_defs": [{"key": k, "label": lab} for k, _c, lab in CHECKLIST],
                "provision": (
                    getattr(app.state, "provision_admin_helpers", {})
                    .get("por_cierre", lambda _i: None)(gid)
                    if getattr(app.state, "provision_admin_helpers", None)
                    else None
                ),
            }
        )

    def generales_list(usuario: str = Query(...)):
        ensure()
        require_admin(usuario)
        rows = query(
            """
            SELECT g.*,
                   (SELECT COUNT(*) FROM cierre_general_dias d WHERE d.Cierre_General_Id=g.Id) AS dias
            FROM cierre_general g ORDER BY g.Id DESC LIMIT 50
            """
        )
        return json_safe(
            [
                {
                    "id": int(r["Id"]),
                    "estado": r.get("Estado"),
                    "titulo": r.get("Titulo"),
                    "fecha_creacion": r.get("Fecha_Creacion"),
                    "fecha_consolidacion": r.get("Fecha_Consolidacion"),
                    "admin_usuario": r.get("Admin_Usuario"),
                    "observacion": r.get("Observacion"),
                    "total_ventas": _money(r.get("Total_Ventas")),
                    "total_efectivo": _money(r.get("Total_Efectivo")),
                    "total_nequi": _money(r.get("Total_Nequi")),
                    "total_datafono": _money(r.get("Total_Datafono")),
                    "total_diferencia": _money(r.get("Total_Diferencia")),
                    "dias": int(r.get("dias") or 0),
                }
                for r in rows
            ]
        )

    def general_get(cierre_id: int, usuario: str = Query(...)):
        ensure()
        require_admin(usuario)
        data = obtener(cierre_id)
        if not data:
            raise HTTPException(404, "Cierre general no encontrado")
        return data

    def general_crear(body: CrearGeneralIn):
        ensure()
        require_admin(body.usuario)
        ids = list(dict.fromkeys(int(x) for x in body.ids_cierres))
        if not ids:
            raise HTTPException(400, "Seleccione al menos un cierre diario")
        for cid in ids:
            dup = query(
                """
                SELECT g.Id FROM cierre_general_dias d
                JOIN cierre_general g ON g.Id=d.Cierre_General_Id
                WHERE d.Cierre_Turno_Id=%s AND g.Estado='CONSOLIDADO' LIMIT 1
                """,
                (cid,),
            )
            if dup:
                raise HTTPException(400, f"El cierre diario #{cid} ya está consolidado")
        ahora = now_bogota().replace(tzinfo=None) if hasattr(now_bogota(), "replace") else datetime.now()
        gid = execute(
            """
            INSERT INTO cierre_general
                (Estado, Titulo, Fecha_Creacion, Fecha_Actualizacion, Admin_Usuario, Admin_Id, Observacion)
            VALUES ('BORRADOR', %s, %s, %s, %s, %s, %s)
            """,
            (
                (body.titulo or f"Cierre general {ahora.date()}")[:120],
                ahora,
                ahora,
                body.usuario[:80],
                admin_id(body.usuario),
                (body.observacion or "")[:2000],
            ),
        )
        tot = {"ventas": 0.0, "efectivo": 0.0, "nequi": 0.0, "datafono": 0.0, "diferencia": 0.0}
        for cid in ids:
            det = resumen_diario(cid)
            if not det:
                continue
            est = "CON_DESCUADRE" if abs(_money(det["diferencia"])) >= 0.5 else "PENDIENTE"
            execute(
                "INSERT INTO cierre_general_dias (Cierre_General_Id, Cierre_Turno_Id, Estado_Dia) VALUES (%s,%s,%s)",
                (gid, cid, est),
            )
            for k in tot:
                tot[k] += _money(det.get(k if k != "diferencia" else "diferencia"))
            tot["ventas"] = tot.get("ventas", 0)  # already
        # fix ventas key
        tot_ventas = sum(_money((resumen_diario(cid) or {}).get("ventas")) for cid in ids)
        tot_e = sum(_money((resumen_diario(cid) or {}).get("efectivo")) for cid in ids)
        tot_n = sum(_money((resumen_diario(cid) or {}).get("nequi")) for cid in ids)
        tot_d = sum(_money((resumen_diario(cid) or {}).get("datafono")) for cid in ids)
        tot_diff = sum(_money((resumen_diario(cid) or {}).get("diferencia")) for cid in ids)
        execute(
            """
            UPDATE cierre_general SET Total_Ventas=%s, Total_Efectivo=%s, Total_Nequi=%s,
                   Total_Datafono=%s, Total_Diferencia=%s WHERE Id=%s
            """,
            (_money(tot_ventas), _money(tot_e), _money(tot_n), _money(tot_d), _money(tot_diff), gid),
        )
        return {"ok": True, "id": gid, "mensaje": "Cierre general creado", "cierre": obtener(gid)}

    def general_checklist(cierre_id: int, body: ChecklistIn):
        ensure()
        require_admin(body.usuario)
        data = obtener(cierre_id)
        if not data:
            raise HTTPException(404, "Cierre general no encontrado")
        if data["estado"] in ("CONSOLIDADO", "ANULADO"):
            raise HTTPException(400, f"No se puede editar un cierre {data['estado']}")
        chk = {k: bool(body.checklist.get(k)) for k, _c, _l in CHECKLIST}
        det = resumen_diario(body.cierre_turno_id) or {}
        est_dia = estado_dia(chk, det.get("diferencia") or 0)
        sets = ", ".join(f"`{col}`=%s" for _k, col, _l in CHECKLIST)
        vals = [1 if chk[k] else 0 for k, _c, _l in CHECKLIST]
        vals.extend([(body.nota_admin or "")[:2000], est_dia, cierre_id, body.cierre_turno_id])
        execute(
            f"UPDATE cierre_general_dias SET {sets}, Nota_Admin=%s, Estado_Dia=%s "
            f"WHERE Cierre_General_Id=%s AND Cierre_Turno_Id=%s",
            tuple(vals),
        )
        nuevo = data["estado"]
        if nuevo == "BORRADOR":
            nuevo = "EN_REVISION"
        rows = query(
            "SELECT Chk_Validado FROM cierre_general_dias WHERE Cierre_General_Id=%s",
            (cierre_id,),
        )
        if rows and all(int(r.get("Chk_Validado") or 0) == 1 for r in rows):
            nuevo = "VERIFICADO"
        ahora = datetime.now()
        execute(
            "UPDATE cierre_general SET Estado=%s, Fecha_Actualizacion=%s WHERE Id=%s",
            (nuevo, ahora, cierre_id),
        )
        return {"ok": True, "mensaje": f"Checklist actualizado ({nuevo})", "cierre": obtener(cierre_id)}

    def general_consolidar(cierre_id: int, body: AccionGeneralIn):
        ensure()
        require_admin(body.usuario)
        data = obtener(cierre_id)
        if not data:
            raise HTTPException(404, "No encontrado")
        if data["estado"] == "CONSOLIDADO":
            raise HTTPException(400, "Este cierre general ya está consolidado")
        if data["estado"] == "ANULADO":
            raise HTTPException(400, "No se puede consolidar un cierre anulado")
        if not data.get("dias"):
            raise HTTPException(400, "Sin días")
        for d in data["dias"]:
            if not (d.get("checklist") or {}).get("chk_validado"):
                raise HTTPException(400, f"Falta validar el día #{d.get('cierre_turno_id')}")
            dup = query(
                """
                SELECT g.Id FROM cierre_general_dias d
                JOIN cierre_general g ON g.Id=d.Cierre_General_Id
                WHERE d.Cierre_Turno_Id=%s AND g.Estado='CONSOLIDADO' AND g.Id<>%s LIMIT 1
                """,
                (d["cierre_turno_id"], cierre_id),
            )
            if dup:
                raise HTTPException(
                    400, f"El cierre diario #{d['cierre_turno_id']} ya pertenece a otro consolidado"
                )
        ahora = datetime.now()
        execute(
            "UPDATE cierre_general SET Estado='CONSOLIDADO', Fecha_Consolidacion=%s, Fecha_Actualizacion=%s WHERE Id=%s",
            (ahora, ahora, cierre_id),
        )
        execute(
            "UPDATE cierre_general_dias SET Estado_Dia='CONSOLIDADO' WHERE Cierre_General_Id=%s",
            (cierre_id,),
        )
        cierre = obtener(cierre_id)
        from provision_admin import aplicar_provision_api

        prov = aplicar_provision_api(app, body.usuario, cierre_id, cierre or {})
        from bolsillo_proveedores import aplicar_ingreso_proveedores_api

        ingreso = aplicar_ingreso_proveedores_api(
            app, body.usuario, cierre_id, cierre or {}, prov or {}
        )
        return {
            "ok": True,
            "mensaje": "Cierre general consolidado. Provisión y bolsillo proveedores aplicados",
            "cierre": obtener(cierre_id),
            "provision": prov,
            "proveedores": ingreso,
        }

    def general_anular(cierre_id: int, body: AccionGeneralIn):
        ensure()
        require_admin(body.usuario)
        data = obtener(cierre_id)
        if not data:
            raise HTTPException(404, "No encontrado")
        if data["estado"] == "ANULADO":
            raise HTTPException(400, "Ya está anulado")
        if data["estado"] == "CONSOLIDADO":
            from bolsillo_proveedores import revertir_ingreso_proveedores_api
            from provision_admin import revertir_provision_api

            revertir_ingreso_proveedores_api(app, body.usuario, cierre_id)
            revertir_provision_api(app, body.usuario, cierre_id)
        obs = data.get("observacion") or ""
        if body.motivo:
            obs = (obs + " | ANULADO: " + body.motivo)[:2000]
        execute(
            "UPDATE cierre_general SET Estado='ANULADO', Observacion=%s, Fecha_Actualizacion=%s WHERE Id=%s",
            (obs, datetime.now(), cierre_id),
        )
        execute(
            "UPDATE cierre_general_dias SET Estado_Dia='PENDIENTE' WHERE Cierre_General_Id=%s AND Estado_Dia='CONSOLIDADO'",
            (cierre_id,),
        )
        return {"ok": True, "mensaje": "Cierre general anulado"}

    # Orden: rutas fijas antes de {id}
    rutas = [
        ("/cierre-general/diarios/", diarios_disponibles, ["GET"]),
        ("/cierre-general/diarios/{cierre_turno_id}/", diario_detalle, ["GET"]),
        ("/cierre-general/", generales_list, ["GET"]),
        ("/cierre-general/", general_crear, ["POST"]),
        ("/cierre-general/{cierre_id}/checklist/", general_checklist, ["POST"]),
        ("/cierre-general/{cierre_id}/consolidar/", general_consolidar, ["POST"]),
        ("/cierre-general/{cierre_id}/anular/", general_anular, ["POST"]),
        ("/cierre-general/{cierre_id}/", general_get, ["GET"]),
    ]
    for path, fn, methods in rutas:
        app.add_api_route(path, fn, methods=methods, name=f"cg_{fn.__name__}_{methods[0]}")
        app.add_api_route(
            "/api/v1" + path,
            fn,
            methods=methods,
            name=f"cg_{fn.__name__}_{methods[0]}_v1",
        )
