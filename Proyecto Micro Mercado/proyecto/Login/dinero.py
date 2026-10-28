"""Formato contable de pesos: $ 1'234.567 (miles con . y millones con ')."""


def redondear_centena(valor):
    """Ajusta pesos a la centena más cercana (ej. 3675→3700, 3896→3900)."""
    try:
        n = float(valor or 0)
    except (TypeError, ValueError):
        return 0
    if n == 0:
        return 0
    sign = -1 if n < 0 else 1
    return int(sign * (int(abs(n) / 100.0 + 0.5) * 100))


def formato_dinero(valor, con_simbolo=True):
    try:
        n = float(valor or 0)
    except (TypeError, ValueError):
        n = 0.0
    neg = n < 0
    digitos = f"{int(round(abs(n)))}"
    grupos = []
    while digitos:
        grupos.append(digitos[-3:])
        digitos = digitos[:-3]
    grupos.reverse()
    if not grupos:
        grupos = ["0"]
    cuerpo = grupos[0]
    for i, grupo in enumerate(grupos[1:], start=1):
        sep_desde_derecha = len(grupos) - 1 - i
        sep = "'" if (sep_desde_derecha % 2 == 1) else "."
        cuerpo = f"{cuerpo}{sep}{grupo}"
    if neg:
        return f"-$ {cuerpo}" if con_simbolo else f"-{cuerpo}"
    return f"$ {cuerpo}" if con_simbolo else cuerpo


def parse_dinero(texto, default=0.0):
    if texto is None:
        return default
    if isinstance(texto, (int, float)):
        try:
            return float(texto)
        except (TypeError, ValueError):
            return default
    t = str(texto).strip()
    if not t:
        return default
    core = t.replace("$", "").replace(" ", "").replace("'", "")
    neg = core.startswith("-")
    limpio = core.lstrip("-")
    if limpio.count(",") == 1 and limpio.count(".") == 0:
        izq, der = limpio.split(",")
        if izq.isdigit() and der.isdigit() and 0 < len(der) <= 2:
            try:
                n = float(f"{izq}.{der}")
                return -n if neg else n
            except ValueError:
                pass
    if limpio.count(".") == 1 and limpio.count(",") == 0:
        izq, der = limpio.split(".")
        if izq.isdigit() and der.isdigit() and 0 < len(der) <= 2:
            try:
                n = float(limpio)
                return -n if neg else n
            except ValueError:
                pass
    digits = "".join(c for c in limpio if c.isdigit())
    if not digits:
        return default
    n = float(digits)
    return -n if neg else n


def parse_dinero_o_none(texto):
    if texto is None or str(texto).strip() == "":
        return None
    if not any(c.isdigit() for c in str(texto)):
        return None
    return parse_dinero(texto)


def formato_entrada(texto):
    digits = "".join(c for c in str(texto or "") if c.isdigit())
    if not digits:
        return ""
    return formato_dinero(int(digits), con_simbolo=False)


def cursor_tras_digitos(formateado, cuantos):
    if cuantos <= 0:
        return 0
    vistos = 0
    for i, ch in enumerate(formateado):
        if ch.isdigit():
            vistos += 1
            if vistos >= cuantos:
                return i + 1
    return len(formateado)
