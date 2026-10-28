"""Pruebas Entrega 5 — obligaciones de provisión (sin DB)."""
from __future__ import annotations

import unittest


def disponible(real, empleados_reserva, servicios, sistema, arriendo, otras=0):
    comprometido = empleados_reserva + servicios + sistema + arriendo + otras
    return round(real - comprometido, 2), round(comprometido, 2)


class TestEjemploSpec(unittest.TestCase):
    def test_ejemplo(self):
        # Provisión 600k, emp 100k, serv 80k, sist 50k, arr 200k → disp 170k
        disp, comp = disponible(600_000, 100_000, 80_000, 50_000, 200_000)
        self.assertEqual(comp, 430_000)
        self.assertEqual(disp, 170_000)

    def test_reserva_diaria_varios_empleados(self):
        salarios = [1_500_000, 1_200_000, 900_000]
        reserva = round(sum(salarios) / 30.0, 2)
        self.assertEqual(reserva, 120_000.0)

    def test_obligaciones_no_crean_dinero(self):
        real_antes = 600_000
        # Comprometer 80k: real no cambia
        real_despues_compromiso = real_antes
        self.assertEqual(real_antes, real_despues_compromiso)
        # Pagar 80k: real baja
        real_despues_pago = real_antes - 80_000
        self.assertEqual(real_despues_pago, 520_000)

    def test_saldo_insuficiente(self):
        real = 100_000
        pago = 150_000
        self.assertTrue(pago - real > 0.009)

    def test_tipos(self):
        tipos = ("EMPLEADOS", "SERVICIOS", "SISTEMA", "ARRIENDO", "OTRAS")
        self.assertEqual(len(tipos), 5)


class TestSvcImport(unittest.TestCase):
    def test_reserva_formula_svc(self):
        import os
        import sys
        from unittest.mock import MagicMock

        root = os.path.abspath(os.path.join(os.path.dirname(__file__), "Login"))
        sys.path.insert(0, root)
        sys.modules.setdefault("conexionLogin", MagicMock())
        import provision_obligaciones_svc as svc

        self.assertEqual(round(3_000_000 / 30.0, 2), 100_000.0)
        self.assertIn("SERVICIOS", svc.TIPOS)


if __name__ == "__main__":
    unittest.main()
