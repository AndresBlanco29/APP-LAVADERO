from exportes import exportar_cierre_pdf


def generar_resumen(empleado_o_datos, total_ventas=0, total_articulos=0):
    from datetime import datetime

    if isinstance(empleado_o_datos, dict):
        datos = empleado_o_datos
    else:
        datos = {
            "cajero": empleado_o_datos,
            "total_ventas": total_ventas,
            "articulos": total_articulos,
            "fecha": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        }
    return exportar_cierre_pdf(datos)
