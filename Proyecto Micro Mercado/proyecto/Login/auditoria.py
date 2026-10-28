from Consultas import registrar_auditoria


def log_accion(usuario, accion, detalle=""):
    try:
        registrar_auditoria(usuario, accion, detalle)
    except Exception as error:
        print("No se pudo guardar el log de auditoría: {}".format(error))
