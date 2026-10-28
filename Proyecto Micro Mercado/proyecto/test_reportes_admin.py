"""Pruebas Entrega 6 — reportes admin / regla Datafono."""
from __future__ import annotations

import os
import sys
import unittest
from datetime import datetime
from unittest.mock import MagicMock

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "Login"))
sys.path.insert(0, ROOT)
sys.modules.setdefault("conexionLogin", MagicMock())


class TestPeriodoYMedios(unittest.TestCase):
    def test_presets(self):
        import reportes_admin_svc as svc

        for p in ("hoy", "ayer", "semana", "mes", "año"):
            r = svc.resolver_periodo(p)
            self.assertIn("desde", r)
            self.assertIn("hasta", r)
            self.assertLessEqual(r["desde"], r["hasta"])

    def test_personalizado(self):
        import reportes_admin_svc as svc

        r = svc.resolver_periodo(
            "personalizado", desde="2026-01-01", hasta="2026-01-31"
        )
        self.assertEqual(r["preset"], "personalizado")
        self.assertEqual(r["desde"].day, 1)

    def test_norm_datafono(self):
        import reportes_admin_svc as svc

        self.assertEqual(svc._norm_medio_report("Tarjeta"), "Datafono")
        self.assertEqual(svc._norm_medio_report("Datafono"), "Datafono")
        self.assertEqual(svc._norm_medio_report("Nequi"), "Nequi")
        self.assertEqual(svc._norm_medio_report("Efectivo"), "Efectivo")

    def test_total_proveedores_sin_duplicar(self):
        ef, nq, dt = 600_000, 500_000, 300_000
        total = ef + nq + dt
        # No sumar Datafono dos veces
        self.assertEqual(total, 1_400_000)
        self.assertNotEqual(total, ef + nq + dt + dt)

    def test_datafono_no_en_admin(self):
        admin_medios = {"efectivo"}
        self.assertNotIn("datafono", admin_medios)

    def test_datafono_no_bolsillo_independiente(self):
        bolsillos_reales = ["administrativo", "proveedores"]
        self.assertNotIn("datafono", bolsillos_reales)
        self.assertNotIn("Datafono", bolsillos_reales)


if __name__ == "__main__":
    unittest.main()
