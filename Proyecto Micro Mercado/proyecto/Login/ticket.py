import os
from datetime import datetime

from Consultas import datos_negocio


ANCHO_80MM = 42
ANCHO_58MM = 32


def _linea(ancho, char="-"):
    return char * ancho


def _centrar(texto, ancho):
    texto = str(texto or "")
    if len(texto) >= ancho:
        return texto[:ancho]
    return texto.center(ancho)


def _pares(izquierda, derecha, ancho):
    izquierda = str(izquierda or "")
    derecha = str(derecha or "")
    espacio = ancho - len(izquierda) - len(derecha)
    if espacio < 1:
        recorte = max(0, ancho - len(derecha) - 1)
        return f"{izquierda[:recorte]} {derecha}"[-ancho:]
    return f"{izquierda}{' ' * espacio}{derecha}"


from dinero import formato_dinero as _dinero


def formatear_ticket(info, cajero="", ancho_mm=80):
    ancho = ANCHO_58MM if int(ancho_mm) == 58 else ANCHO_80MM
    negocio = info.get("negocio") or datos_negocio()
    ahora = datetime.now().strftime("%d/%m/%Y %H:%M")
    # Preferir fecha de la venta si viene de reimpresión
    if info.get("fecha"):
        try:
            raw = str(info["fecha"])
            ahora = raw[:16].replace("T", " ") if len(raw) >= 16 else raw
        except Exception:
            pass
    lineas = [
        _linea(ancho, "="),
        _centrar("ZYNTRA POS", ancho),
        _centrar(negocio.get("nombre") or "Zyntra POS", ancho),
    ]
    if negocio.get("direccion"):
        lineas.append(_centrar(negocio["direccion"], ancho))
    lineas.extend(
        [
            _linea(ancho),
            _pares("Ticket", str(info.get("id_venta") or "-"), ancho),
            _pares("Fecha", ahora, ancho),
            _pares("Cajero", cajero or "-", ancho),
            _linea(ancho),
        ]
    )
    if info.get("cliente"):
        cli = info["cliente"]
        nombre_cli = cli.get("nombre", "") if isinstance(cli, dict) else str(cli or "")
        if nombre_cli:
            lineas.append(_pares("Cliente", nombre_cli, ancho))
    lineas.extend(
        [
            _pares("Producto / Cant", "Valor", ancho),
            _linea(ancho),
        ]
    )

    for item in info.get("productos") or []:
        nombre = str(item.get("nombre") or f"Cod {item.get('codigo')}")
        if item.get("presentacion"):
            nombre = "{} ({})".format(nombre, item.get("presentacion"))
        cantidad = item.get("cantidad_presentacion") or item.get("cantidad", 1)
        subtotal = item.get("subtotal", 0)
        try:
            cant_f = float(cantidad or 0)
        except (TypeError, ValueError):
            cant_f = 0.0
        precio = item.get("precio", 0)
        try:
            precio_f = float(precio or 0)
        except (TypeError, ValueError):
            precio_f = 0.0
        if precio_f <= 0 and cant_f > 0:
            try:
                precio_f = float(subtotal or 0) / cant_f
            except (TypeError, ValueError, ZeroDivisionError):
                precio_f = 0.0
        lineas.append(nombre[:ancho])
        # Etiqueta neutra para el cliente (sin "precio real" ni recargos internos)
        detalle = f"{cantidad} x {_dinero(precio_f)}"
        lineas.append(_pares(detalle, _dinero(subtotal), ancho))

    lineas.append(_linea(ancho))
    lineas.append(_pares("TOTAL", _dinero(info.get("total", 0)), ancho))
    # No mostrar gestiones internas (recargo datafono, precio real, etc.)
    for metodo, monto in (info.get("pagos_ticket") or info.get("pagos") or {}).items():
        if float(monto or 0) > 0:
            etiqueta = str(metodo or "")
            # Evitar nombres internos administrativos en el ticket
            low = etiqueta.lower()
            if "real" in low or "recargo" in low or "desc." in low or "+6" in low:
                continue
            lineas.append(_pares(etiqueta, _dinero(monto), ancho))
    if info.get("puntos_ganados"):
        lineas.append(_pares("Puntos ganados", str(info.get("puntos_ganados")), ancho))
    if info.get("puntos_canjeados"):
        lineas.append(_pares("Puntos canjeados", str(info.get("puntos_canjeados")), ancho))
    cambio = info.get("cambio", 0)
    try:
        if float(cambio or 0) > 0.009:
            lineas.append(_pares("CAMBIO", _dinero(cambio), ancho))
    except (TypeError, ValueError):
        pass
    lineas.extend(
        [
            _linea(ancho, "="),
            _centrar("Gracias por su compra", ancho),
            _centrar("Conserve este ticket", ancho),
            _linea(ancho, "="),
            "",
            "",
            "",
        ]
    )
    return "\n".join(lineas)


def carpeta_tickets():
    path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "reportes"))
    os.makedirs(path, exist_ok=True)
    return path


def guardar_ticket(texto, id_venta=None):
    nombre = f"ticket_{id_venta or datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    path = os.path.join(carpeta_tickets(), nombre)
    with open(path, "w", encoding="utf-8") as archivo:
        archivo.write(texto)
    return path


def enviar_a_impresora(path):
    try:
        os.startfile(path, "print")
        return True
    except OSError:
        try:
            os.startfile(path)
        except OSError:
            return False
        return False


def imprimir_ticket_venta(info, cajero="", ancho_mm=80, enviar_cola=True):
    texto = formatear_ticket(info, cajero=cajero, ancho_mm=ancho_mm)
    path = guardar_ticket(texto, info.get("id_venta"))
    if enviar_cola:
        enviar_a_impresora(path)
    return path, texto


def formatear_ticket_cierre(datos, ancho_mm=80):
    """Ticket resumido para adjuntar al dinero en caja fuerte."""
    ancho = ANCHO_58MM if int(ancho_mm) == 58 else ANCHO_80MM
    negocio = datos.get("negocio") or datos_negocio()
    tipo = str(datos.get("tipo") or "definitivo").lower()
    titulo = "CIERRE DE TURNO" if tipo != "temporal" else "ARQUEO TEMPORAL"
    fecha = str(datos.get("fecha") or datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    cajero = datos.get("cajero") or datos.get("usuario") or "-"
    cierre_id = datos.get("cierre_id") or datos.get("id") or "-"
    lineas = [
        _linea(ancho, "="),
        _centrar("ZYNTRA POS", ancho),
        _centrar(negocio.get("nombre") or "Zyntra POS", ancho),
        _centrar(titulo, ancho),
        _linea(ancho),
        _pares("Cierre #", str(cierre_id), ancho),
        _pares("Fecha", fecha[:16], ancho),
        _pares("Vendedor", str(cajero)[:ancho - 12], ancho),
        _pares("Usuario", str(datos.get("usuario") or cajero)[:ancho - 12], ancho),
        _linea(ancho),
        _centrar("HORARIOS", ancho),
        _linea(ancho),
    ]
    eventos = datos.get("linea_tiempo") or []
    if eventos:
        for ev in eventos:
            etiq = str(ev.get("etiqueta") or ev.get("tipo") or "Evento")
            hora = str(ev.get("fecha") or "")[:16]
            lineas.append(_pares(etiq[:18], hora, ancho))
    else:
        if datos.get("inicio") or datos.get("hora_apertura"):
            lineas.append(
                _pares("Apertura", str(datos.get("inicio") or datos.get("hora_apertura"))[:16], ancho)
            )
        if datos.get("hora_cierre_temporal"):
            lineas.append(
                _pares("Cierre temporal", str(datos.get("hora_cierre_temporal"))[:16], ancho)
            )
        if datos.get("hora_reapertura"):
            lineas.append(
                _pares("Ini. post-temp.", str(datos.get("hora_reapertura"))[:16], ancho)
            )
        lineas.append(_pares("Cierre", fecha[:16], ancho))
    lineas.extend(
        [
            _linea(ancho),
            _pares("Transacciones", str(int(datos.get("tickets") or 0)), ancho),
            _pares("Total ventas", _dinero(datos.get("total_ventas")), ancho),
            _pares("Estado", str(datos.get("estado") or "-")[:ancho - 10], ancho),
            _linea(ancho),
            _centrar("MEDIOS DE PAGO", ancho),
            _linea(ancho),
        ]
    )
    medios = datos.get("medios_conciliacion") or []
    if medios:
        for m in medios:
            etiq = str(m.get("etiqueta") or m.get("metodo") or "?")
            lineas.append(_centrar(etiq, ancho))
            lineas.append(_pares("  Sistema", _dinero(m.get("sistema")), ancho))
            lineas.append(_pares("  Declarado", _dinero(m.get("declarado")), ancho))
            diff = float(m.get("diferencia") or 0)
            if abs(diff) >= 0.01:
                lineas.append(_pares("  Diff", _dinero(diff), ancho))
            lineas.append(_linea(ancho, "."))
    else:
        lineas.append(_pares("Efectivo", _dinero(datos.get("Efectivo") or datos.get("efectivo")), ancho))
        lineas.append(_pares("Nequi", _dinero(datos.get("Nequi") or datos.get("nequi")), ancho))
        lineas.append(
            _pares("Datafono", _dinero(datos.get("Tarjeta") or datos.get("datafono")), ancho)
        )
        lineas.append(_linea(ancho, "."))

    corr = int(datos.get("correcciones") or 0)
    lineas.append(_pares("Reclasificaciones", str(corr), ancho))
    if corr > 0:
        for c in (datos.get("lista_correcciones") or [])[:8]:
            ant = c.get("metodo_anterior") or "?"
            nue = c.get("metodo_nuevo") or "?"
            mon = _dinero(c.get("monto"))
            lineas.append(_pares(" {}->{}".format(ant[:6], nue[:6]), mon, ancho))
        if corr > 8:
            lineas.append(_centrar("(+{} mas)".format(corr - 8), ancho))

    if datos.get("observacion"):
        lineas.append(_linea(ancho))
        lineas.append(_centrar("OBSERVACION", ancho))
        obs = str(datos.get("observacion") or "").strip()
        while obs:
            lineas.append(obs[:ancho])
            obs = obs[ancho:]

    lineas.extend(
        [
            _linea(ancho),
            _centrar("Adjuntar al dinero", ancho),
            _centrar("en caja fuerte", ancho),
            _centrar("Vendedor: {}".format(str(cajero)[:28]), ancho),
            _linea(ancho, "="),
            "",
            "",
            "",
        ]
    )
    return "\n".join(lineas)


def imprimir_ticket_cierre(datos, ancho_mm=80, enviar_cola=True):
    texto = formatear_ticket_cierre(datos, ancho_mm=ancho_mm)
    cid = datos.get("cierre_id") or datos.get("id") or "cierre"
    path = guardar_ticket(texto, "cierre_{}".format(cid))
    ok_print = True
    if enviar_cola:
        ok_print = bool(enviar_a_impresora(path))
    return path, texto, ok_print
