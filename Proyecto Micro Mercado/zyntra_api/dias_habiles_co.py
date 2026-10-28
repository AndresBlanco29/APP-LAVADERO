"""Días hábiles Colombia (lun–vie, sin festivos nacionales).

Incluye festivos fijos, de Ley Emiliani (trasladados al lunes) y Semana Santa.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, time


HORA_ACREDITACION_DATAFONO = time(14, 0, 0)  # 2:00 PM


def _easter_sunday(year: int) -> date:
    """Algoritmo de Meeus/Jones/Butcher (gregoriano)."""
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    el = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * el) // 451
    month = (h + el - 7 * m + 114) // 31
    day = ((h + el - 7 * m + 114) % 31) + 1
    return date(year, month, day)


def _next_monday(d: date) -> date:
    """Si no es lunes, traslada al lunes siguiente (Ley Emiliani)."""
    if d.weekday() == 0:
        return d
    return d + timedelta(days=(7 - d.weekday()))


def festivos_colombia(year: int) -> set:
    """Conjunto de festivos nacionales para un año."""
    easter = _easter_sunday(year)
    holy_thursday = easter - timedelta(days=3)
    good_friday = easter - timedelta(days=2)
    ascension = _next_monday(easter + timedelta(days=39))
    corpus = _next_monday(easter + timedelta(days=60))
    sagrado = _next_monday(easter + timedelta(days=71))

    fixed = {
        date(year, 1, 1),
        date(year, 5, 1),
        date(year, 7, 20),
        date(year, 8, 7),
        date(year, 12, 8),
        date(year, 12, 25),
    }
    emiliani = {
        _next_monday(date(year, 1, 6)),
        _next_monday(date(year, 3, 19)),
        _next_monday(date(year, 6, 29)),
        _next_monday(date(year, 8, 15)),
        _next_monday(date(year, 10, 12)),
        _next_monday(date(year, 11, 1)),
        _next_monday(date(year, 11, 11)),
    }
    return fixed | emiliani | {holy_thursday, good_friday, ascension, corpus, sagrado}


def es_dia_habil(d: date) -> bool:
    if d.weekday() >= 5:
        return False
    return d not in festivos_colombia(d.year)


def siguiente_dia_habil(desde: date) -> date:
    d = desde + timedelta(days=1)
    while not es_dia_habil(d):
        d += timedelta(days=1)
    return d


def fecha_acreditacion_datafono(desde=None) -> datetime:
    if desde is None:
        desde = datetime.now()
    elif isinstance(desde, date) and not isinstance(desde, datetime):
        desde = datetime.combine(desde, time(0, 0, 0))
    nxt = siguiente_dia_habil(desde.date())
    return datetime.combine(nxt, HORA_ACREDITACION_DATAFONO)
