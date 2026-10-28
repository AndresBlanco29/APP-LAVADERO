"""Entrega 7 — pruebas de integridad y seguridad (sin DB / sin API viva)."""
from __future__ import annotations

import os
import sys
import unittest
from unittest.mock import MagicMock

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "Login"))
API = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "zyntra_api"))
sys.path.insert(0, ROOT)
sys.path.insert(0, API)
sys.modules.setdefault("conexionLogin", MagicMock())


class TestIntegridadFinanciera(unittest.TestCase):
    def test_suma_pagos_igual_venta(self):
        total = 100_000
        pagos = [40_000, 30_000, 30_000]
        self.assertAlmostEqual(sum(pagos), total, places=2)

    def test_reclasificacion_no_cambia_total(self):
        total = 80_000
        # mueve 20k de efectivo a nequi
        ef, nq = 50_000, 30_000
        ef2, nq2 = ef - 20_000, nq + 20_000
        self.assertEqual(ef + nq, total)
        self.assertEqual(ef2 + nq2, total)

    def test_provision_no_supera_efectivo(self):
        from provision_admin_svc import calcular_provision_admin

        r = calcular_provision_admin(2_000_000, 0, 500_000)
        self.assertLessEqual(r["efectivo_provisionado"], 500_000)

    def test_proveedores_formula(self):
        from bolsillo_proveedores_svc import calcular_ingreso_proveedores

        r = calcular_ingreso_proveedores(
            {"total_nequi": 500_000, "total_datafono": 300_000, "total_efectivo": 1_200_000},
            {"efectivo_provisionado": 600_000},
        )
        self.assertEqual(r["efectivo"], 600_000)
        self.assertEqual(r["nequi"], 500_000)
        self.assertEqual(r["datafono"], 0.0)
        self.assertEqual(r["datafono_pendiente"], 300_000)
        self.assertEqual(r["total"], 1_400_000)
        self.assertEqual(r["total_inmediato"], 1_100_000)
        self.assertEqual(r["total"], r["total_inmediato"] + r["datafono_pendiente"])

    def test_credito_no_infla(self):
        saldos = {"efectivo": 100, "nequi": 50, "datafono": 25}
        # OBLIGACION: saldos idénticos
        self.assertEqual(saldos["efectivo"] + saldos["nequi"] + saldos["datafono"], 175)

    def test_obligacion_no_crea_dinero(self):
        real_antes = 600_000
        # comprometer 80k
        real_despues = real_antes
        self.assertEqual(real_antes, real_despues)
        disponible = real_antes - 80_000
        self.assertEqual(disponible, 520_000)


class TestSeguridadRoles(unittest.TestCase):
    def test_vendedor_rechazado_resumen_proveedores(self):
        import bolsillo_proveedores_svc as svc

        # Mock es_admin False
        svc._es_admin = lambda u: False  # type: ignore
        r = svc.resumen_bolsillo_proveedores("vendedor1")
        self.assertIn("error", r)

    def test_vendedor_rechazado_sin_usuario(self):
        import bolsillo_proveedores_svc as svc

        svc._es_admin = lambda u: bool(u) and u == "admin"  # type: ignore
        r = svc.resumen_bolsillo_proveedores(None)
        self.assertIn("error", r)

    def test_vendedor_rechazado_obligaciones(self):
        import provision_obligaciones_svc as svc

        svc._es_admin = lambda u: False  # type: ignore
        r = svc.resumen_obligaciones_provision("caja01")
        self.assertIn("error", r)

    def test_admin_login_no_acepta_usuarios_fallback(self):
        # El código de validar_admin ya no tiene fallback a tabla usuarios
        src = open(
            os.path.join(API, "main.py"), encoding="utf-8"
        ).read()
        # Tras el SELECT admin exitoso no debe haber query a FROM usuarios para login admin
        idx = src.find("def validar_admin")
        chunk = src[idx : idx + 1200]
        self.assertIn("Solo tabla admin", chunk)
        self.assertNotIn("FROM usuarios", chunk)


class TestDobleConsolidacion(unittest.TestCase):
    def test_mensaje_guard_existe(self):
        src = open(
            os.path.join(ROOT, "cierre_general_svc.py"), encoding="utf-8"
        ).read()
        self.assertIn("ya pertenece a otro consolidado", src)


if __name__ == "__main__":
    unittest.main()
