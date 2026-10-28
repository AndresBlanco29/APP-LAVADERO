"""Pruebas unitarias bolsillo proveedores + días hábiles CO (sin DB)."""
from __future__ import annotations

import os
import sys
import unittest
from datetime import date, datetime
from unittest.mock import MagicMock

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "Login"))
sys.path.insert(0, ROOT)
sys.modules.setdefault("conexionLogin", MagicMock())


class TestDiasHabilesCO(unittest.TestCase):
    def test_siguiente_habil_salta_fin_de_semana(self):
        from dias_habiles_co import siguiente_dia_habil, fecha_acreditacion_datafono

        # Viernes 5-jun-2026 → lunes 8 es Corpus Christi (Emiliani) → martes 9
        nxt = siguiente_dia_habil(date(2026, 6, 5))
        self.assertEqual(nxt, date(2026, 6, 9))
        disp = fecha_acreditacion_datafono(datetime(2026, 6, 5, 18, 0))
        self.assertEqual(disp.hour, 14)
        self.assertEqual(disp.date(), date(2026, 6, 9))

        # Viernes normal sin festivo (2026-03-13) → lunes 16
        self.assertEqual(siguiente_dia_habil(date(2026, 3, 13)), date(2026, 3, 16))

    def test_festivo_ano_nuevo(self):
        from dias_habiles_co import es_dia_habil, siguiente_dia_habil

        self.assertFalse(es_dia_habil(date(2026, 1, 1)))
        # 31 dic 2025 miércoles → siguiente hábil salta 1 ene
        self.assertEqual(siguiente_dia_habil(date(2025, 12, 31)), date(2026, 1, 2))


class TestCalculoIngresoProveedores(unittest.TestCase):
    def test_inmediato_sin_datafono_en_saldo(self):
        import bolsillo_proveedores_svc as svc

        cierre = {
            "total_nequi": 500_000,
            "total_datafono": 300_000,
            "total_efectivo": 1_200_000,
        }
        provision = {"efectivo_provisionado": 600_000, "nuevo_saldo_pendiente": 0}
        r = svc.calcular_ingreso_proveedores(cierre, provision, fecha_origen=datetime(2026, 6, 5, 10, 0))
        self.assertEqual(r["efectivo"], 600_000)
        self.assertEqual(r["nequi"], 500_000)
        self.assertEqual(r["datafono"], 0.0)
        self.assertEqual(r["datafono_pendiente"], 300_000)
        self.assertEqual(r["total_inmediato"], 1_100_000)
        self.assertEqual(r["total"], 1_400_000)  # total medios − provisionado
        self.assertIn("2026-06-09", r["datafono_fecha_disponible"])
        self.assertIn("14:00", r["datafono_fecha_disponible"])

    def test_opcion_a_total_menos_provisionado(self):
        import bolsillo_proveedores_svc as svc

        r = svc.calcular_ingreso_proveedores(
            {"total_nequi": 100, "total_datafono": 50, "total_efectivo": 200},
            {"efectivo_provisionado": 80},
        )
        self.assertEqual(r["efectivo"], 120)
        self.assertEqual(r["total"], 270)  # 350 - 80
        self.assertEqual(r["datafono_pendiente"], 50)

    def test_normaliza_billetera(self):
        import bolsillo_proveedores_svc as svc

        self.assertEqual(svc.normalizar_metodo_prov("Billetera digital"), "Nequi")
        self.assertEqual(svc.normalizar_metodo_prov("Daviplata"), "Nequi")
        self.assertEqual(svc.normalizar_metodo_prov("Bancolombia"), "Nequi")
        self.assertEqual(svc.label_medio_prov("Nequi"), "Billetera digital")


if __name__ == "__main__":
    unittest.main()
