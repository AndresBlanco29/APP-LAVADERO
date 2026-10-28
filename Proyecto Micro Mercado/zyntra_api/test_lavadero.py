"""Prueba el flujo del lavadero sin MySQL."""
import os
import tempfile

os.environ["LAVADERO_FORCE_SQLITE"] = "1"
os.environ["LAVADERO_DB"] = os.path.join(tempfile.mkdtemp(), "lavadero.db")

import lavadero as lv

lv._DB = None
lv._LISTO = False
lv.init_db()

sesion = {"usuario": "admin", "rol": "admin", "nombre": "Dueño", "branch_id": 0}
catalogo = lv.catalogo()
zona = next(z for z in catalogo["zonas"] if z["nombre"] == "Carros")
tipo = next(t for t in catalogo["tipos"] if t["codigo"] == "AUTOMOVIL" and t["zona_id"] == zona["id"])
servicio = next(s for s in catalogo["servicios"] if s["nombre"] == "Lavado básico" and s["zona_id"] == zona["id"])
assert lv.pesos(servicio["precios"][tipo["id"]]) == 25000
assert all(t["codigo"] != "CASCO" for t in catalogo["tipos"])
assert all("casco" not in s["nombre"].lower() for s in catalogo["servicios"])

carlos = lv.guardar_entidad(
    "empleado",
    {"nombre": "carlos", "apellido": "gómez", "telefono": "300111223399"},
    usuario="admin",
)
andres = lv.guardar_entidad(
    "empleado",
    {"nombre": "Andrés", "apellido": "López", "telefono": "3112223344"},
    usuario="admin",
)
guardado = lv.db().one("SELECT nombre, apellido, telefono FROM lv_empleado WHERE id=?", (carlos["id"],))
assert guardado["nombre"] == "CARLOS"
assert guardado["apellido"] == "GÓMEZ"
assert guardado["telefono"] == "3001112233"
try:
    lv.crear_orden(
        {
            "branch_id": zona["branch_id"],
            "zona_id": zona["id"],
            "tipo_id": tipo["id"],
            "servicios": [servicio["id"]],
            "placa": "abc123",
            "cliente_nombre": "Johnny Muñoz",
            "cliente_telefono": "3001112233",
        },
        sesion,
    )
    raise SystemExit("debio exigir un muchacho")
except lv.ErrorLavadero as error:
    assert error.mensaje == "Elige quién va a lavar."

orden = lv.crear_orden(
    {
        "branch_id": zona["branch_id"],
        "zona_id": zona["id"],
        "tipo_id": tipo["id"],
        "servicios": [servicio["id"]],
        "colaboradores": [
            {"empleado_id": carlos["id"], "peso": 1},
            {"empleado_id": andres["id"], "peso": 1},
        ],
        "placa": "abc123",
        "cliente_nombre": "Johnny Muñoz",
        "cliente_telefono": "3001112233",
    },
    sesion,
)
assert orden["estado"] == "EN_PROCESO"
assert orden["total"] == 25000
assert orden["placa"] == "ABC123"
assert orden["cliente_nombre"] == "JOHNNY MUÑOZ"

try:
    lv.cobrar_orden(orden["id"], {"pagos": [{"medio": "Efectivo", "monto": 25000}]}, sesion)
    raise SystemExit("no debio cobrar en proceso")
except lv.ErrorLavadero as error:
    assert error.mensaje == "Primero márcalo listo para entregar."

lista = lv.marcar_listo(orden["id"], sesion)
assert lista["estado"] == "LISTO"
assert "api.whatsapp.com" in lista["whatsapp"]["url"]
assert "3001112233" in lista["whatsapp"]["url"] or "573001112233" in lista["whatsapp"]["url"]

cobrada = lv.cobrar_orden(orden["id"], {"pagos": [{"medio": "Efectivo", "monto": 25000}]}, sesion)
assert cobrada["estado"] == "COBRADA"
comisiones = lv.db().all("SELECT * FROM lv_comision WHERE orden_id=?", (orden["id"],))
assert sorted(c["monto"] for c in comisiones) == [5000, 5000]
assert cobrada["cobrado_por"] == "Dueño"
detalle = lv._detalle_movil(cobrada)
assert detalle["placa"] == "ABC123"
assert detalle["cliente"] == "JOHNNY MUÑOZ"
assert detalle["comisiones"] == 10000
assert detalle["ganancia"] == 15000
assert detalle["cobrado_por"] == "Dueño"
assert detalle["hora"]
assert sorted(persona["nombre"] for persona in detalle["muchachos"]) == ["ANDRÉS LÓPEZ", "CARLOS GÓMEZ"]
assert sorted(persona["monto"] for persona in detalle["muchachos"]) == [5000, 5000]
assert detalle["pagos"] == [{"medio": "Efectivo", "monto": 25000}]
assert detalle["servicios"][0]["nombre"] == "Lavado básico"

resumen = lv.resumen_dia(zona["branch_id"])
assert resumen["producido"] == 25000
assert resumen["comisiones"] == 10000
assert sorted(p["comision"] for p in resumen["por_colaborador"]) == [5000, 5000]
assert resumen["por_colaborador"][0]["trabajos"][0]["servicio"] == "Lavado básico"
assert resumen["gastos"] == 11250
assert resumen["ganancia"] == 3750
assert sum(b["monto"] for b in resumen["bolsillos"]) == 25000
por_nombre = {b["nombre"]: b for b in resumen["bolsillos"]}
assert por_nombre["Para los muchachos"]["monto"] == 10000
assert por_nombre["Gastos operativos"]["monto"] == 8750
assert por_nombre["Seguridad social y provisiones"]["monto"] == 2500
assert por_nombre["Utilidad neta"]["monto"] == 3750
assert "Utilidad neta" in resumen["texto"]

lv.guardar_entidad(
    "servicio",
    {
        "zona_id": zona["id"],
        "nombre": "Lavado básico",
        "grupo": "Basico",
        "icono": "🚗",
        "duracion": "",
        "precios": {str(tipo["id"]): 30000},
    },
    servicio["id"],
    "admin",
)
vieja = lv._orden_completa(orden["id"])
assert vieja["total"] == 25000
nueva = lv.crear_orden(
    {
        "branch_id": zona["branch_id"],
        "zona_id": zona["id"],
        "tipo_id": tipo["id"],
        "servicios": [servicio["id"]],
        "colaboradores": [{"empleado_id": carlos["id"], "peso": 1}],
        "placa": "xyz987",
        "cliente_nombre": "Ana Pérez",
        "cliente_telefono": "3110001122",
    },
    sesion,
)
assert nueva["total"] == 30000
assert nueva["cliente_nombre"] == "ANA PÉREZ"
corregida = lv.actualizar_orden(
    nueva["id"],
    {
        "placa": "xyz111",
        "cliente_nombre": "pedro gómez",
        "cliente_telefono": "3201112233",
        "colaboradores": [
            {"empleado_id": carlos["id"], "peso": 1},
            {"empleado_id": andres["id"], "peso": 1},
        ],
    },
    sesion,
)
assert corregida["placa"] == "XYZ111"
assert corregida["cliente_nombre"] == "PEDRO GÓMEZ"
assert corregida["cliente_telefono"] == "3201112233"
assert len(corregida["colaboradores"]) == 2
completo = next(s for s in catalogo["servicios"] if s["nombre"] == "Lavado completo" and s["zona_id"] == zona["id"])
con_servicio = lv.actualizar_orden(
    nueva["id"],
    {"servicios": [servicio["id"], completo["id"]]},
    sesion,
)
assert con_servicio["total"] == 80000
servicios_orden = [i for i in con_servicio["items"] if i["tipo"] == "SERVICIO"]
assert sorted(i["descripcion"] for i in servicios_orden) == ["Lavado básico", "Lavado completo"]
assert next(i["precio"] for i in servicios_orden if i["descripcion"] == "Lavado básico") == 30000
cera = next(p for p in catalogo["productos"] if p["nombre"] == "Cera líquida")
con_producto = lv.actualizar_orden(
    nueva["id"],
    {"productos": [{"producto_id": cera["id"], "cantidad": 1}]},
    sesion,
)
assert con_producto["total"] == 105000
assert any(i["tipo"] == "PRODUCTO" and i["descripcion"] == "Cera líquida" for i in con_producto["items"])
try:
    lv.actualizar_orden(nueva["id"], {"servicios": []}, sesion)
    raise SystemExit("debio exigir un servicio")
except lv.ErrorLavadero as error:
    assert error.mensaje == "Elige al menos un servicio."
try:
    lv.actualizar_orden(nueva["id"], {"colaboradores": []}, sesion)
    raise SystemExit("debio exigir un muchacho")
except lv.ErrorLavadero as error:
    assert error.mensaje == "Elige quién va a lavar."
lv.anular_orden(nueva["id"], sesion)

con_nota = lv.crear_orden(
    {
        "branch_id": zona["branch_id"],
        "zona_id": zona["id"],
        "tipo_id": tipo["id"],
        "servicios": [servicio["id"]],
        "colaboradores": [{"empleado_id": carlos["id"], "peso": 1}],
        "placa": "nota01",
        "cliente_nombre": "Luz Vera",
        "cliente_telefono": "3001234567",
        "checklist": ["Rayones", "Llantas", "inventado"],
        "nota": "  Puerta derecha hundida  ",
    },
    sesion,
)
assert con_nota["checklist"] == ["Rayones", "Llantas"]
assert con_nota["nota"] == "Puerta derecha hundida"
editada = lv.actualizar_orden(con_nota["id"], {"nota": "Sin novedad", "checklist": []}, sesion)
assert editada["checklist"] == []
assert editada["nota"] == "Sin novedad"
lv.anular_orden(con_nota["id"], sesion)

recepcion = lv.db().one("SELECT rol FROM lv_usuario WHERE usuario='recepcion'")
assert recepcion["rol"] == "vendedor"
lv.db().run("UPDATE lv_usuario SET rol='cajero' WHERE usuario='recepcion'")
lv._migrar(lv.db())
assert lv.db().one("SELECT rol FROM lv_usuario WHERE usuario='recepcion'")["rol"] == "vendedor"
try:
    lv.guardar_entidad(
        "usuario",
        {
            "usuario": "venta1",
            "nombre": "Vendedor",
            "rol": "vendedor",
            "branch_id": zona["branch_id"],
            "clave": "1234",
            "correo": "venta1@lavadero.com",
            "correo_confirma": "otro@lavadero.com",
        },
        usuario="admin",
    )
    raise SystemExit("debio exigir el mismo correo")
except lv.ErrorLavadero as error:
    assert "dos veces" in error.mensaje
vendedor = lv.guardar_entidad(
    "usuario",
    {
        "usuario": "venta1",
        "nombre": "Vendedor",
        "rol": "vendedor",
        "branch_id": zona["branch_id"],
        "clave": "1234",
        "correo": "Venta1@Lavadero.com",
        "correo_confirma": "venta1@lavadero.com",
    },
    usuario="admin",
)
guardado_usuario = lv.db().one("SELECT rol, correo FROM lv_usuario WHERE id=?", (vendedor["id"],))
assert guardado_usuario["rol"] == "vendedor"
assert guardado_usuario["correo"] == "venta1@lavadero.com"
token = "token-de-prueba"
vence = (lv.datetime.now(lv.BOGOTA) + lv.timedelta(minutes=30)).strftime("%Y-%m-%d %H:%M:%S")
lv.db().run(
    "INSERT INTO lv_recupero (usuario_id, token_hash, vence_en, usado) VALUES (?,?,?,0)",
    (vendedor["id"], lv.hash_clave(token), vence),
)
lv.aplicar_recupero(token, "clave9876", "clave9876")
assert lv.db().one("SELECT clave_hash FROM lv_usuario WHERE id=?", (vendedor["id"],))["clave_hash"] == lv.hash_clave("clave9876")
try:
    lv.aplicar_recupero(token, "clave9876", "clave9876")
    raise SystemExit("el enlace ya se uso")
except lv.ErrorLavadero as error:
    assert "venció" in error.mensaje
sin_correo = lv.pedir_recupero("recepcion", "http://127.0.0.1:8765")
assert sin_correo["ok"] is True
try:
    lv.guardar_entidad(
        "usuario",
        {"usuario": "malo", "nombre": "Malo", "rol": "contador", "branch_id": 0, "clave": "1234"},
        usuario="admin",
    )
    raise SystemExit("debio rechazar el rol")
except lv.ErrorLavadero as error:
    assert "vendedor" in error.mensaje
try:
    lv.solo_dueno({"rol": "vendedor"})
    raise SystemExit("el vendedor no entra a la plata")
except lv.ErrorLavadero as error:
    assert error.status == 403
visto = lv.catalogo(completo=False)
assert visto["reglas"] == []
assert visto["usuarios"] == []
assert visto["reparto"] == []
assert "whatsapp_dueno" not in visto["negocio"]
assert "Rayones" in visto["revision"]
assert all("costo" not in p for p in visto["productos"])
assert all("telefono" not in e for e in visto["empleados"])

apagado = lv.quitar_entidad("servicio", servicio["id"], "admin")
assert apagado["modo"] == "apagado"

reporte = lv.reporte(zona["branch_id"], 0, "hoy")
assert reporte["producido"] == 25000
assert reporte["vehiculos"] == 1

cierre = lv.cerrar_dia(zona["branch_id"], sesion)
assert cierre["cerrado"] is True
assert "Utilidad neta" in cierre["texto"]
try:
    lv.guardar_bolsillos(
        {"bolsillos": [
            {"nombre": "Para los muchachos", "porcentaje": 30, "tipo": "MUCHACHOS"},
            {"nombre": "Gastos operativos", "porcentaje": 40, "tipo": "GASTO"},
            {"nombre": "Seguridad social y provisiones", "porcentaje": 10, "tipo": "GASTO"},
            {"nombre": "Utilidad neta", "porcentaje": 25, "tipo": "UTILIDAD"},
        ]},
        "admin",
    )
    raise SystemExit("debio exigir 100")
except lv.ErrorLavadero as error:
    assert "100" in error.mensaje
lv.guardar_bolsillos(
    {"bolsillos": [
        {"nombre": "Para los muchachos", "porcentaje": 30, "tipo": "MUCHACHOS"},
        {"nombre": "Gastos operativos", "porcentaje": 30, "tipo": "GASTO"},
        {"nombre": "Seguridad social y provisiones", "porcentaje": 10, "tipo": "GASTO"},
        {"nombre": "Caja menor", "porcentaje": 5, "tipo": "GASTO"},
        {"nombre": "Utilidad neta", "porcentaje": 25, "tipo": "UTILIDAD"},
    ]},
    "admin",
)
con_caja = lv.resumen_dia(zona["branch_id"])
assert any(b["nombre"] == "Caja menor" and b["monto"] == 1250 for b in con_caja["bolsillos"])
assert sum(b["porcentaje"] for b in con_caja["bolsillos"]) == 100
assert sum(b["monto"] for b in con_caja["bolsillos"]) == con_caja["producido"]

bolsa_gasto = next(b for b in lv.listar_bolsillos() if b["nombre"] == "Gastos operativos")
bolsa_utilidad = next(b for b in lv.listar_bolsillos() if b["tipo"] == "UTILIDAD")
try:
    lv.guardar_gasto({"branch_id": zona["branch_id"], "clase": "PAGO", "concepto": "Arriendo", "monto": 5000, "bolsillo_id": 0}, sesion)
    raise SystemExit("debio exigir bolsillo")
except lv.ErrorLavadero as error:
    assert "bolsillo" in error.mensaje
pago = lv.guardar_gasto(
    {"branch_id": zona["branch_id"], "clase": "pago", "concepto": "Arriendo del local", "monto": 5000, "bolsillo_id": bolsa_gasto["id"], "nota": "Mes"},
    sesion,
)
compra = lv.guardar_gasto(
    {"branch_id": zona["branch_id"], "clase": "COMPRA", "concepto": "Jabón", "monto": 2000, "bolsillo_id": bolsa_gasto["id"]},
    sesion,
)
assert pago["clase"] == "PAGO"
lista = lv.listar_gastos(zona["branch_id"], sesion, "hoy")
assert lista["total"] == 7000
assert any(b["nombre"] == "Gastos operativos" and b["pagos"] == 5000 and b["compras"] == 2000 for b in lista["por_bolsillo"])
con_gasto = lv.resumen_dia(zona["branch_id"])
bolsa_dia = next(b for b in con_gasto["bolsillos"] if b["id"] == bolsa_gasto["id"])
assert bolsa_dia["gastado"] == 7000
assert any(m["concepto"] == "Arriendo del local" and m["nota"] == "Mes" for m in bolsa_dia["movimientos"])
assert any(m["concepto"] == "Jabón" for m in bolsa_dia["movimientos"])
assert bolsa_dia["queda"] == bolsa_dia["monto"] - 7000
assert sum(b["monto"] for b in con_gasto["bolsillos"]) == con_gasto["producido"]
assert "pagos y compras" in con_gasto["texto"]
lv.guardar_gasto(
    {"branch_id": zona["branch_id"], "clase": "PAGO", "concepto": "Arriendo del local", "monto": 4000, "bolsillo_id": bolsa_utilidad["id"]},
    sesion,
    pago["id"],
)
movido = lv.listar_gastos(zona["branch_id"], sesion, "hoy")
assert any(g["id"] == pago["id"] and g["bolsillo_id"] == bolsa_utilidad["id"] and g["monto"] == 4000 for g in movido["gastos"])
lv.quitar_gasto(compra["id"], sesion)
assert all(g["id"] != compra["id"] for g in lv.listar_gastos(zona["branch_id"], sesion, "hoy")["gastos"])
muchachos = next(b for b in lv.listar_bolsillos() if b["tipo"] == "MUCHACHOS")
try:
    lv.guardar_gasto(
        {"branch_id": zona["branch_id"], "clase": "PAGO", "concepto": "A los muchachos", "monto": 1000, "bolsillo_id": muchachos["id"]},
        sesion,
    )
    raise SystemExit("el bolsillo de los muchachos no se toca")
except lv.ErrorLavadero as error:
    assert "muchachos" in error.mensaje
cera = next(p for p in lv.catalogo()["productos"] if p["nombre"] == "Cera líquida")
stock_antes = int(cera["stock"])
ingreso = lv.guardar_gasto(
    {
        "branch_id": zona["branch_id"],
        "clase": "COMPRA",
        "monto": 36000,
        "bolsillo_id": bolsa_gasto["id"],
        "productos": [{"producto_id": cera["id"], "cantidad": 3, "precio": 12000}],
    },
    sesion,
)
assert ingreso["productos"][0]["cantidad"] == 3
assert ingreso["productos"][0]["precio"] == 12000
assert ingreso["monto"] == 36000
assert int(lv.db().one("SELECT stock FROM lv_producto WHERE id=?", (cera["id"],))["stock"]) == stock_antes + 3
assert any(g["id"] == ingreso["id"] and g["productos"] for g in lv.listar_gastos(zona["branch_id"], sesion, "hoy")["gastos"])
lv.quitar_gasto(ingreso["id"], sesion)
assert int(lv.db().one("SELECT stock FROM lv_producto WHERE id=?", (cera["id"],))["stock"]) == stock_antes
lv.guardar_gasto(
    {
        "branch_id": zona["branch_id"],
        "monto": 12000,
        "bolsillo_id": bolsa_gasto["id"],
        "productos": [{"producto_id": cera["id"], "cantidad": 1, "precio": 12000}],
    },
    sesion,
)
lv.db().run("UPDATE lv_producto SET stock=0 WHERE id=?", (cera["id"],))
otro = next(g for g in lv.listar_gastos(zona["branch_id"], sesion, "hoy")["gastos"] if g["productos"])
try:
    lv.quitar_gasto(otro["id"], sesion)
    raise SystemExit("no debio bajar existencia ya vendida")
except lv.ErrorLavadero as error:
    assert "vendió" in error.mensaje
lv.db().run("UPDATE lv_producto SET stock=? WHERE id=?", (stock_antes, cera["id"]))
lv.quitar_gasto(otro["id"], sesion)
try:
    lv.listar_gastos(zona["branch_id"], {"usuario": "venta", "rol": "vendedor", "branch_id": zona["branch_id"]})
    raise SystemExit("el vendedor no ve gastos")
except lv.ErrorLavadero as error:
    assert error.status == 403
ids_antes = [b["id"] for b in lv.listar_bolsillos()]
lv.guardar_bolsillos({"bolsillos": [
    {"id": b["id"], "nombre": b["nombre"], "porcentaje": b["porcentaje"], "tipo": b["tipo"]}
    for b in lv.listar_bolsillos()
]}, "admin")
assert [b["id"] for b in lv.listar_bolsillos()] == ids_antes

otra = next(s for s in catalogo["sucursales"] if s["nombre"] == "Sucursal 2")
zona_nueva = lv.guardar_entidad(
    "zona",
    {"branch_id": otra["id"], "nombre": "Carros 2", "tipo": "CARROS"},
    usuario="admin",
)
copia = lv.copiar_zona(zona_nueva["id"], zona["id"])
assert copia["servicios"] >= 1

print("ok", resumen["texto"])
