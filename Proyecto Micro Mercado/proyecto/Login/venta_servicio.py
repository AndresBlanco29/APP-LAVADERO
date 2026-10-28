from Consultas import (
    aplicar_credito_cliente,
    asociar_cliente_venta,
    actualizar_stock,
    ajustar_puntos_cliente,
    costo_equivalente,
    descontar_insumos,
    descontar_lotes,
    guardar_pagos_venta,
    hay_conexion,
    insertar_producto_has_venta,
    obtener_producto,
    obtener_receta,
    parse_producto,
    realizar_venta,
    registrar_movimiento_inventario,
)


def _items(payload):
    items = []
    for producto in payload.get("productos") or []:
        if isinstance(producto, dict):
            items.append(producto)
        else:
            items.append(
                {
                    "codigo": producto[0],
                    "cantidad": producto[1],
                    "subtotal": producto[2],
                    "nombre": producto[3] if len(producto) > 3 else "",
                    "precio": producto[4] if len(producto) > 4 else 0,
                    "factor": 1,
                    "cantidad_presentacion": producto[1],
                }
            )
    return items


def registrar_venta_online(payload):
    id_venta = realizar_venta(payload.get("total"), payload.get("id_empleado"))
    if not id_venta:
        raise RuntimeError("Sin conexión al registrar la venta")

    usuario = payload.get("usuario")
    for item in _items(payload):
        codigo = item.get("codigo")
        cantidad_base = float(item.get("cantidad") or 0)
        subtotal = item.get("subtotal")
        factor = float(item.get("factor") or 1) or 1
        cant_pres = float(item.get("cantidad_presentacion") or cantidad_base)
        producto = obtener_producto(codigo)
        datos = parse_producto(producto) if producto else {}
        costo_base = float(datos.get("precio_compra") or 0)
        costo_linea = costo_equivalente(costo_base, cantidad_base)
        try:
            utilidad = float(subtotal or 0) - costo_linea
        except (TypeError, ValueError):
            utilidad = 0
        insertar_producto_has_venta(
            id_venta,
            codigo,
            cantidad_base,
            subtotal,
            extra={
                "presentacion_id": item.get("presentacion_id"),
                "presentacion_nombre": item.get("presentacion") or "",
                "factor": factor,
                "cantidad_presentacion": cant_pres,
                "costo_unitario": costo_equivalente(costo_base, factor),
                "utilidad": utilidad,
            },
        )
        receta = obtener_receta(codigo)
        if receta:
            descontar_insumos(codigo, cantidad_base)
        else:
            actualizar_stock(codigo, cantidad_base)
            descontar_lotes(codigo, cantidad_base)
        registrar_movimiento_inventario(
            codigo,
            "VENTA",
            cant_pres,
            factor,
            "Venta {}".format(id_venta),
            usuario or "",
            item.get("presentacion_id"),
        )

    guardar_pagos_venta(id_venta, payload.get("pagos") or {})

    cliente = payload.get("cliente") or {}
    cliente_id = cliente.get("id") if isinstance(cliente, dict) else None
    usuario = payload.get("usuario")
    if cliente_id:
        asociar_cliente_venta(id_venta, cliente_id)
        credito = float(payload.get("credito") or 0)
        if credito > 0:
            aplicar_credito_cliente(cliente_id, credito, id_venta, usuario)
        puntos_usados = int(payload.get("puntos_usados") or 0)
        if puntos_usados:
            ajustar_puntos_cliente(cliente_id, -puntos_usados, id_venta, usuario, "CANJE", "Canje en cobro")
        puntos_ganados = int(payload.get("puntos_ganados") or 0)
        if puntos_ganados:
            ajustar_puntos_cliente(cliente_id, puntos_ganados, id_venta, usuario, "PUNTOS", "Acumulación por compra")
    return id_venta


def procesar_cobro(payload):
    from offline_sync import encolar_venta

    try:
        if not hay_conexion():
            raise RuntimeError("offline")
        id_venta = registrar_venta_online(payload)
        return {"id_venta": id_venta, "offline": False}
    except Exception:
        local_id = encolar_venta(payload)
        return {"id_venta": f"OFF-{local_id}", "offline": True}
