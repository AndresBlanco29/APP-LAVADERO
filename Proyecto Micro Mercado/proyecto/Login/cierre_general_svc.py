"""Cierre general administrativo (Entrega 2). Solo administrador."""
from __future__ import annotations

from datetime import datetime

from conexionLogin import FormularioLogin


CHECKLIST_CIERRE_GENERAL = (
    ("chk_efectivo", "Chk_Efectivo", "Efectivo verificado"),
    ("chk_nequi", "Chk_Nequi", "Nequi verificado"),
    ("chk_datafono", "Chk_Datafono", "Datafono verificado"),
    ("chk_ventas", "Chk_Ventas", "Ventas conciliadas"),
    ("chk_correcciones", "Chk_Correcciones", "Correcciones revisadas"),
    ("chk_descuadres", "Chk_Descuadres", "Descuadres revisados"),
    ("chk_observaciones", "Chk_Observaciones", "Observaciones revisadas"),
    ("chk_validado", "Chk_Validado", "Cierre validado"),
)

ESTADOS_CIERRE_GENERAL = ("BORRADOR", "EN_REVISION", "VERIFICADO", "CONSOLIDADO", "ANULADO")


def _round2(valor):
    try:
        return round(float(valor or 0), 2)
    except (TypeError, ValueError):
        return 0.0


def es_usuario_admin(usuario):
    if not usuario:
        return False
    try:
        cone = FormularioLogin.conexion_base_de_datos()
        cursor = cone.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM admin WHERE LOWER(usuario) = LOWER(%s)",
            (str(usuario).strip(),),
        )
        n = int((cursor.fetchone() or [0])[0] or 0)
        cone.close()
        return n > 0
    except Exception as error:
        print("Error al validar admin: {}".format(error))
        return False


def id_admin_por_usuario(usuario):
    try:
        cone = FormularioLogin.conexion_base_de_datos()
        cursor = cone.cursor()
        for col in ("Id_admin", "id_admin", "Id_Admin", "id"):
            try:
                cursor.execute(
                    "SELECT `{}` FROM admin WHERE LOWER(usuario)=LOWER(%s) LIMIT 1".format(col),
                    (str(usuario).strip(),),
                )
                row = cursor.fetchone()
                if row:
                    cone.close()
                    return int(row[0])
            except Exception:
                continue
        cone.close()
    except Exception:
        pass
    return None


def _auditoria(usuario, accion, detalle):
    try:
        from Consultas import registrar_auditoria

        registrar_auditoria(usuario, accion, detalle)
    except Exception:
        pass


def _listar_correcciones(cierre_id, limite=200):
    try:
        from Consultas import listar_correcciones_cierre

        return listar_correcciones_cierre(cierre_id=cierre_id, limite=limite)
    except Exception:
        return []


def _medios_de_cierre_turno(cursor, cierre_id, row_ct=None):
    efectivo = nequi = datafono = diferencia = 0.0
    try:
        cursor.execute(
            """
            SELECT Metodo, Etiqueta, Sistema, Declarado, Diferencia
            FROM cierre_turno_medios WHERE Cierre_Id=%s
            """,
            (cierre_id,),
        )
        for metodo, etiqueta, sistema, declarado, diff in cursor.fetchall() or []:
            m = str(metodo or "").strip()
            e = str(etiqueta or "").upper()
            decl = _round2(declarado if declarado is not None else sistema)
            d = _round2(diff)
            if m == "Efectivo" or e == "EFECTIVO":
                efectivo = decl
                diferencia = d
            elif m in ("Nequi", "Transferencia") or e == "NEQUI":
                nequi += decl
            elif m == "Tarjeta" or e == "DATAFONO":
                datafono = decl
    except Exception:
        pass
    if row_ct:
        if efectivo == 0:
            efectivo = _round2(row_ct.get("Efectivo") or 0)
        if nequi == 0:
            nequi = _round2(row_ct.get("Nequi") or 0) + _round2(row_ct.get("Transferencia") or 0)
        if datafono == 0:
            datafono = _round2(row_ct.get("Tarjeta") or 0)
        if abs(diferencia) < 0.009:
            diferencia = _round2(row_ct.get("Descuadre") or 0)
    return {
        "efectivo": _round2(efectivo),
        "nequi": _round2(nequi),
        "datafono": _round2(datafono),
        "diferencia": _round2(diferencia),
    }


def _row_dict(cursor, table, row):
    if row is None:
        return None
    if isinstance(row, dict):
        return row
    cursor.execute("SHOW COLUMNS FROM `{}`".format(table))
    cols = [c[0] for c in cursor.fetchall() or []]
    return {cols[i]: row[i] for i in range(min(len(cols), len(row)))}


def listar_cierres_diarios_disponibles(incluir_en_general_id=None, limite=200):
    out = []
    try:
        cone = FormularioLogin.conexion_base_de_datos()
        cursor = cone.cursor()
        vals = []
        if incluir_en_general_id:
            sql = """
                SELECT ct.Id, ct.Cajero, ct.Fecha, ct.Total_Ventas, ct.Efectivo, ct.Nequi,
                       ct.Tarjeta, ct.Transferencia, ct.Descuadre,
                       COALESCE(ct.Estado,''), COALESCE(ct.Observacion,''),
                       COALESCE(ct.Correcciones,0), COALESCE(ct.Usuario,''), COALESCE(ct.Tipo,'definitivo')
                FROM cierre_turno ct
                WHERE COALESCE(ct.Tipo, 'definitivo') <> 'temporal'
                  AND (
                    ct.Id NOT IN (
                      SELECT d.Cierre_Turno_Id FROM cierre_general_dias d
                      JOIN cierre_general g ON g.Id = d.Cierre_General_Id
                      WHERE g.Estado = 'CONSOLIDADO'
                    )
                    OR ct.Id IN (
                      SELECT d2.Cierre_Turno_Id FROM cierre_general_dias d2
                      WHERE d2.Cierre_General_Id = %s
                    )
                  )
                ORDER BY ct.Fecha DESC LIMIT %s
            """
            vals = [incluir_en_general_id, int(limite)]
        else:
            sql = """
                SELECT ct.Id, ct.Cajero, ct.Fecha, ct.Total_Ventas, ct.Efectivo, ct.Nequi,
                       ct.Tarjeta, ct.Transferencia, ct.Descuadre,
                       COALESCE(ct.Estado,''), COALESCE(ct.Observacion,''),
                       COALESCE(ct.Correcciones,0), COALESCE(ct.Usuario,''), COALESCE(ct.Tipo,'definitivo')
                FROM cierre_turno ct
                WHERE COALESCE(ct.Tipo, 'definitivo') <> 'temporal'
                  AND ct.Id NOT IN (
                      SELECT d.Cierre_Turno_Id FROM cierre_general_dias d
                      JOIN cierre_general g ON g.Id = d.Cierre_General_Id
                      WHERE g.Estado = 'CONSOLIDADO'
                  )
                ORDER BY ct.Fecha DESC LIMIT %s
            """
            vals = [int(limite)]
        try:
            cursor.execute(sql, tuple(vals))
        except Exception:
            cursor.execute(
                """
                SELECT Id, Cajero, Fecha, Total_Ventas, Efectivo, Nequi, Tarjeta, Transferencia,
                       Descuadre, '', '', 0, '', COALESCE(Tipo,'definitivo')
                FROM cierre_turno
                WHERE COALESCE(Tipo,'definitivo') <> 'temporal'
                ORDER BY Fecha DESC LIMIT %s
                """,
                (int(limite),),
            )
        for row in cursor.fetchall() or []:
            ct = {
                "Efectivo": row[4],
                "Nequi": row[5],
                "Tarjeta": row[6],
                "Transferencia": row[7],
                "Descuadre": row[8],
            }
            medios = _medios_de_cierre_turno(cursor, row[0], ct)
            out.append(
                {
                    "id": int(row[0]),
                    "fecha": str(row[2]),
                    "vendedor": row[1] or row[12] or "",
                    "ventas": _round2(row[3]),
                    "efectivo": medios["efectivo"],
                    "nequi": medios["nequi"],
                    "datafono": medios["datafono"],
                    "diferencia": medios["diferencia"],
                    "estado": row[9] or "",
                    "correcciones": int(row[11] or 0),
                    "observaciones": row[10] or "",
                }
            )
        cone.close()
    except Exception as error:
        print("Error listar cierres diarios: {}".format(error))
    return out


def _checklist_from_row(row_dict):
    return {
        key: bool(int(row_dict.get(col) or 0))
        for key, col, _lab in CHECKLIST_CIERRE_GENERAL
    }


def _estado_dia_desde_checklist_y_descuadre(checklist, diferencia):
    if abs(_round2(diferencia)) >= 0.5:
        return "CON_DESCUADRE"
    if checklist.get("chk_validado") and all(
        checklist.get(k) for k, _c, _l in CHECKLIST_CIERRE_GENERAL
    ):
        return "VERIFICADO"
    return "PENDIENTE"


def detalle_cierre_diario_admin(cierre_turno_id):
    try:
        cone = FormularioLogin.conexion_base_de_datos()
        cursor = cone.cursor()
        cursor.execute("SELECT * FROM cierre_turno WHERE Id=%s", (cierre_turno_id,))
        ct = _row_dict(cursor, "cierre_turno", cursor.fetchone())
        if not ct:
            cone.close()
            return None
        medios = _medios_de_cierre_turno(cursor, cierre_turno_id, ct)
        medios_lista = []
        try:
            cursor.execute(
                "SELECT Metodo, Etiqueta, Sistema, Declarado, Diferencia FROM cierre_turno_medios WHERE Cierre_Id=%s",
                (cierre_turno_id,),
            )
            for m, e, s, d, diff in cursor.fetchall() or []:
                medios_lista.append(
                    {
                        "metodo": m,
                        "etiqueta": e or m,
                        "sistema": _round2(s),
                        "declarado": _round2(d),
                        "diferencia": _round2(diff),
                    }
                )
        except Exception:
            pass
        cone.close()
        return {
            "id": int(cierre_turno_id),
            "fecha": str(ct.get("Fecha") or ""),
            "vendedor": ct.get("Cajero") or ct.get("Usuario") or "",
            "ventas": _round2(ct.get("Total_Ventas")),
            "efectivo": medios["efectivo"],
            "nequi": medios["nequi"],
            "datafono": medios["datafono"],
            "diferencia": medios["diferencia"],
            "estado": ct.get("Estado") or "",
            "correcciones_count": int(ct.get("Correcciones") or 0),
            "observaciones": ct.get("Observacion") or "",
            "usuario": ct.get("Usuario") or "",
            "medios": medios_lista,
            "correcciones": _listar_correcciones(cierre_turno_id),
            "esperado": _round2(ct.get("Esperado")),
            "conteo_fisico": _round2(ct.get("Conteo_Fisico")),
        }
    except Exception as error:
        print("Error detalle cierre diario: {}".format(error))
        return None


def crear_cierre_general(usuario_admin, ids_cierres_turno, titulo="", observacion=""):
    if not es_usuario_admin(usuario_admin):
        return False, "Solo el administrador puede crear un cierre general", None
    ids = []
    for x in ids_cierres_turno or []:
        try:
            ids.append(int(x))
        except (TypeError, ValueError):
            continue
    ids = list(dict.fromkeys(ids))
    if not ids:
        return False, "Seleccione al menos un cierre diario", None
    # Prefetch before pooled cursor: close() closes sibling cursors on the shared socket.
    admin_id = id_admin_por_usuario(usuario_admin)
    detalles = {}
    for cid in ids:
        det = detalle_cierre_diario_admin(cid)
        if not det:
            return False, "Cierre diario #{} no encontrado".format(cid), None
        detalles[cid] = det
    try:
        cone = FormularioLogin.conexion_base_de_datos()
        cursor = cone.cursor()
        for cid in ids:
            cursor.execute(
                """
                SELECT g.Id FROM cierre_general_dias d
                JOIN cierre_general g ON g.Id = d.Cierre_General_Id
                WHERE d.Cierre_Turno_Id=%s AND g.Estado='CONSOLIDADO' LIMIT 1
                """,
                (cid,),
            )
            if cursor.fetchone():
                cone.close()
                return False, "El cierre diario #{} ya está consolidado".format(cid), None
        ahora = datetime.now()
        cursor.execute(
            """
            INSERT INTO cierre_general
                (Estado, Titulo, Fecha_Creacion, Fecha_Actualizacion, Admin_Usuario, Admin_Id, Observacion)
            VALUES ('BORRADOR', %s, %s, %s, %s, %s, %s)
            """,
            (
                (titulo or "Cierre general {}".format(ahora.strftime("%Y-%m-%d")))[:120],
                ahora,
                ahora,
                (usuario_admin or "")[:80],
                admin_id,
                (observacion or "")[:2000],
            ),
        )
        gid = cursor.lastrowid
        tot = {"ventas": 0.0, "efectivo": 0.0, "nequi": 0.0, "datafono": 0.0, "diferencia": 0.0}
        for cid in ids:
            det = detalles[cid]
            estado_dia = "CON_DESCUADRE" if abs(det["diferencia"]) >= 0.5 else "PENDIENTE"
            cursor.execute(
                """
                INSERT INTO cierre_general_dias
                    (Cierre_General_Id, Cierre_Turno_Id, Estado_Dia)
                VALUES (%s, %s, %s)
                """,
                (gid, cid, estado_dia),
            )
            tot["ventas"] += det["ventas"]
            tot["efectivo"] += det["efectivo"]
            tot["nequi"] += det["nequi"]
            tot["datafono"] += det["datafono"]
            tot["diferencia"] += det["diferencia"]
        cursor.execute(
            """
            UPDATE cierre_general SET
                Total_Ventas=%s, Total_Efectivo=%s, Total_Nequi=%s,
                Total_Datafono=%s, Total_Diferencia=%s WHERE Id=%s
            """,
            (
                _round2(tot["ventas"]),
                _round2(tot["efectivo"]),
                _round2(tot["nequi"]),
                _round2(tot["datafono"]),
                _round2(tot["diferencia"]),
                gid,
            ),
        )
        cone.commit()
        cone.close()
        _auditoria(usuario_admin, "Cierre general", "Creó cierre general #{}".format(gid))
        return True, "Cierre general creado", gid
    except Exception as error:
        print("Error crear cierre general: {}".format(error))
        return False, "Error: {}".format(error), None


def listar_cierres_generales(limite=50):
    out = []
    try:
        cone = FormularioLogin.conexion_base_de_datos()
        cursor = cone.cursor()
        cursor.execute(
            """
            SELECT Id, Estado, Titulo, Fecha_Creacion, Fecha_Consolidacion, Admin_Usuario,
                   Observacion, Total_Ventas, Total_Efectivo, Total_Nequi, Total_Datafono, Total_Diferencia
            FROM cierre_general ORDER BY Id DESC LIMIT %s
            """,
            (int(limite),),
        )
        for row in cursor.fetchall() or []:
            cursor.execute(
                "SELECT COUNT(*) FROM cierre_general_dias WHERE Cierre_General_Id=%s",
                (row[0],),
            )
            n_dias = int((cursor.fetchone() or [0])[0] or 0)
            out.append(
                {
                    "id": int(row[0]),
                    "estado": row[1] or "BORRADOR",
                    "titulo": row[2] or "",
                    "fecha_creacion": str(row[3] or ""),
                    "fecha_consolidacion": str(row[4] or "") if row[4] else "",
                    "admin_usuario": row[5] or "",
                    "observacion": row[6] or "",
                    "total_ventas": _round2(row[7]),
                    "total_efectivo": _round2(row[8]),
                    "total_nequi": _round2(row[9]),
                    "total_datafono": _round2(row[10]),
                    "total_diferencia": _round2(row[11]),
                    "dias": n_dias,
                }
            )
        cone.close()
    except Exception as error:
        print("Error listar cierres generales: {}".format(error))
    return out


def obtener_cierre_general(cierre_general_id):
    try:
        cone = FormularioLogin.conexion_base_de_datos()
        cursor = cone.cursor()
        cursor.execute("SELECT * FROM cierre_general WHERE Id=%s", (cierre_general_id,))
        row = _row_dict(cursor, "cierre_general", cursor.fetchone())
        if not row:
            cone.close()
            return None
        cursor.execute(
            "SELECT * FROM cierre_general_dias WHERE Cierre_General_Id=%s ORDER BY Id",
            (cierre_general_id,),
        )
        raw = cursor.fetchall() or []
        dias_rows = [_row_dict(cursor, "cierre_general_dias", r) for r in raw]
        cone.close()
        dias = []
        for d in dias_rows:
            tid = int(d.get("Cierre_Turno_Id") or 0)
            det = detalle_cierre_diario_admin(tid) or {}
            checklist = _checklist_from_row(d)
            dias.append(
                {
                    "id": int(d.get("Id") or 0),
                    "cierre_turno_id": tid,
                    "estado_dia": d.get("Estado_Dia") or "PENDIENTE",
                    "checklist": checklist,
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
        result = {
            "id": int(row.get("Id") or cierre_general_id),
            "estado": row.get("Estado") or "BORRADOR",
            "titulo": row.get("Titulo") or "",
            "fecha_creacion": str(row.get("Fecha_Creacion") or ""),
            "fecha_consolidacion": str(row.get("Fecha_Consolidacion") or "")
            if row.get("Fecha_Consolidacion")
            else "",
            "admin_usuario": row.get("Admin_Usuario") or "",
            "observacion": row.get("Observacion") or "",
            "total_ventas": _round2(row.get("Total_Ventas")),
            "total_efectivo": _round2(row.get("Total_Efectivo")),
            "total_nequi": _round2(row.get("Total_Nequi")),
            "total_datafono": _round2(row.get("Total_Datafono")),
            "total_diferencia": _round2(row.get("Total_Diferencia")),
            "dias": dias,
            "checklist_defs": [
                {"key": k, "label": lab} for k, _c, lab in CHECKLIST_CIERRE_GENERAL
            ],
        }
        try:
            from provision_admin_svc import obtener_provision_por_cierre_general

            result["provision"] = obtener_provision_por_cierre_general(cierre_general_id)
        except Exception:
            result["provision"] = None
        return result
    except Exception as error:
        print("Error obtener cierre general: {}".format(error))
        return None


def actualizar_checklist_dia(
    usuario_admin, cierre_general_id, cierre_turno_id, checklist, nota_admin=""
):
    if not es_usuario_admin(usuario_admin):
        return False, "Solo el administrador puede modificar el checklist"
    data = obtener_cierre_general(cierre_general_id)
    if not data:
        return False, "Cierre general no encontrado"
    if data["estado"] in ("CONSOLIDADO", "ANULADO"):
        return False, "No se puede editar un cierre {}".format(data["estado"])
    chk = checklist or {}
    det = detalle_cierre_diario_admin(cierre_turno_id) or {}
    estado_dia = _estado_dia_desde_checklist_y_descuadre(chk, det.get("diferencia") or 0)
    try:
        cone = FormularioLogin.conexion_base_de_datos()
        cursor = cone.cursor()
        sets = []
        vals = []
        for key, col, _lab in CHECKLIST_CIERRE_GENERAL:
            sets.append("`{}`=%s".format(col))
            vals.append(1 if chk.get(key) else 0)
        sets.append("Nota_Admin=%s")
        vals.append((nota_admin or "")[:2000])
        sets.append("Estado_Dia=%s")
        vals.append(estado_dia)
        vals.extend([cierre_general_id, cierre_turno_id])
        cursor.execute(
            "UPDATE cierre_general_dias SET {} WHERE Cierre_General_Id=%s AND Cierre_Turno_Id=%s".format(
                ", ".join(sets)
            ),
            tuple(vals),
        )
        nuevo_estado = data["estado"]
        if nuevo_estado == "BORRADOR":
            nuevo_estado = "EN_REVISION"
        cursor.execute(
            "SELECT Chk_Validado FROM cierre_general_dias WHERE Cierre_General_Id=%s",
            (cierre_general_id,),
        )
        rows = cursor.fetchall() or []
        if rows and all(int((r[0] if not isinstance(r, dict) else r.get("Chk_Validado")) or 0) == 1 for r in rows):
            nuevo_estado = "VERIFICADO"
        cursor.execute(
            "UPDATE cierre_general SET Estado=%s, Fecha_Actualizacion=%s WHERE Id=%s",
            (nuevo_estado, datetime.now(), cierre_general_id),
        )
        cone.commit()
        cone.close()
        _auditoria(
            usuario_admin,
            "Cierre general",
            "Checklist día #{} en general #{}".format(cierre_turno_id, cierre_general_id),
        )
        return True, "Checklist actualizado ({})".format(nuevo_estado)
    except Exception as error:
        return False, "Error: {}".format(error)


def consolidar_cierre_general(usuario_admin, cierre_general_id):
    if not es_usuario_admin(usuario_admin):
        return False, "Solo el administrador puede consolidar", None
    data = obtener_cierre_general(cierre_general_id)
    if not data:
        return False, "Cierre general no encontrado", None
    if data["estado"] == "CONSOLIDADO":
        return False, "Este cierre general ya está consolidado", None
    if data["estado"] == "ANULADO":
        return False, "No se puede consolidar un cierre anulado", None
    if not data.get("dias"):
        return False, "El cierre general no tiene días", None
    for d in data["dias"]:
        if not (d.get("checklist") or {}).get("chk_validado"):
            return False, "Falta validar el día del cierre #{}".format(d.get("cierre_turno_id")), None
        tid = d["cierre_turno_id"]
        cone = FormularioLogin.conexion_base_de_datos()
        cursor = cone.cursor()
        cursor.execute(
            """
            SELECT g.Id FROM cierre_general_dias d
            JOIN cierre_general g ON g.Id = d.Cierre_General_Id
            WHERE d.Cierre_Turno_Id=%s AND g.Estado='CONSOLIDADO' AND g.Id<>%s LIMIT 1
            """,
            (tid, cierre_general_id),
        )
        if cursor.fetchone():
            cone.close()
            return False, "El cierre diario #{} ya pertenece a otro consolidado".format(tid), None
        cone.close()
    try:
        cone = FormularioLogin.conexion_base_de_datos()
        cursor = cone.cursor()
        ahora = datetime.now()
        cursor.execute(
            """
            UPDATE cierre_general
            SET Estado='CONSOLIDADO', Fecha_Consolidacion=%s, Fecha_Actualizacion=%s
            WHERE Id=%s
            """,
            (ahora, ahora, cierre_general_id),
        )
        cursor.execute(
            "UPDATE cierre_general_dias SET Estado_Dia='CONSOLIDADO' WHERE Cierre_General_Id=%s",
            (cierre_general_id,),
        )
        cone.commit()
        cone.close()
        _auditoria(
            usuario_admin,
            "Cierre general",
            "Consolidó cierre general #{}".format(cierre_general_id),
        )
        # Entrega 3: provisión administrativa (30% ventas, solo efectivo)
        from provision_admin_svc import aplicar_provision_al_consolidar

        data_refresco = obtener_cierre_general(cierre_general_id)
        ok_p, msg_p, prov = aplicar_provision_al_consolidar(
            usuario_admin, cierre_general_id, data_refresco
        )
        if not ok_p:
            return False, "Consolidado, pero falló la provisión: {}".format(msg_p), None
        # Entrega 4: bolsillo proveedores = Nequi + Datafono + efectivo sobrante
        from bolsillo_proveedores_svc import aplicar_ingreso_proveedores_al_consolidar

        ok_bp, msg_bp, ingreso = aplicar_ingreso_proveedores_al_consolidar(
            usuario_admin, cierre_general_id, data_refresco, prov or {}
        )
        if not ok_bp:
            return False, "Consolidado y provisión OK, pero falló proveedores: {}".format(msg_bp), None
        out = {"provision": prov, "proveedores": ingreso}
        return (
            True,
            "Cierre general consolidado. {}. {}".format(msg_p, msg_bp),
            out,
        )
    except Exception as error:
        return False, "Error: {}".format(error), None


def anular_cierre_general(usuario_admin, cierre_general_id, motivo=""):
    if not es_usuario_admin(usuario_admin):
        return False, "Solo el administrador puede anular"
    data = obtener_cierre_general(cierre_general_id)
    if not data:
        return False, "Cierre general no encontrado"
    if data["estado"] == "ANULADO":
        return False, "Ya está anulado"
    if data["estado"] == "CONSOLIDADO":
        from bolsillo_proveedores_svc import revertir_ingreso_proveedores_por_anulacion
        from provision_admin_svc import revertir_provision_por_anulacion

        ok_bp, msg_bp = revertir_ingreso_proveedores_por_anulacion(
            usuario_admin, cierre_general_id
        )
        if not ok_bp:
            return False, msg_bp
        ok_r, msg_r = revertir_provision_por_anulacion(usuario_admin, cierre_general_id)
        if not ok_r:
            return False, msg_r
    try:
        cone = FormularioLogin.conexion_base_de_datos()
        cursor = cone.cursor()
        obs = data.get("observacion") or ""
        if motivo:
            obs = (obs + " | ANULADO: " + motivo)[:2000]
        cursor.execute(
            """
            UPDATE cierre_general
            SET Estado='ANULADO', Observacion=%s, Fecha_Actualizacion=%s WHERE Id=%s
            """,
            (obs, datetime.now(), cierre_general_id),
        )
        cursor.execute(
            """
            UPDATE cierre_general_dias SET Estado_Dia='PENDIENTE'
            WHERE Cierre_General_Id=%s AND Estado_Dia='CONSOLIDADO'
            """,
            (cierre_general_id,),
        )
        cone.commit()
        cone.close()
        _auditoria(
            usuario_admin,
            "Cierre general",
            "Anuló cierre general #{} {}".format(cierre_general_id, motivo or ""),
        )
        return True, "Cierre general anulado"
    except Exception as error:
        return False, "Error: {}".format(error)
