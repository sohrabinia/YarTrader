import unittest

from src.Execution.Services.autonomous_demo_trader import calculate_demo_volume_by_risk


class FakeMT5:
    ORDER_TYPE_BUY = 0
    ORDER_TYPE_SELL = 1

    def order_calc_profit(self, order_type, symbol, volume, entry, stop_loss):
        # Simulate broker contract conventions: standard FX lot=100,000 units,
        # while the gold fixture uses a 100-unit contract.
        contract_size = 100000.0 if symbol.upper() == "EURUSD" else 100.0
        return -abs(float(entry) - float(stop_loss)) * contract_size * float(volume)


class TestDynamicDemoRiskSizing(unittest.TestCase):
    def setUp(self):
        self.mt5 = FakeMT5()
        self.symbol_info = {"volume_min": 0.1, "volume_max": 100.0, "volume_step": 0.1}

    def test_volume_is_sized_against_one_percent_wallet_budget(self):
        result = calculate_demo_volume_by_risk(
            self.mt5, "XAUUSD", "BUY", 4184.17, 4173.04,
            self.symbol_info, balance=30000.0, equity=30000.0, risk_pct=1.0,
        )
        self.assertTrue(result["allowed"])
        self.assertAlmostEqual(result["risk_budget_usd"], 300.0, places=4)
        self.assertAlmostEqual(result["minimum_lot_risk_usd"], 111.30, places=2)

    def test_volume_scales_with_current_wallet_and_never_rounds_up(self):
        low = calculate_demo_volume_by_risk(
            self.mt5, "XAUUSD", "BUY", 4184.17, 4173.04,
            self.symbol_info, balance=50000.0, equity=60000.0, risk_pct=1.0,
        )
        high = calculate_demo_volume_by_risk(
            self.mt5, "XAUUSD", "BUY", 4184.17, 4173.04,
            self.symbol_info, balance=100000.0, equity=100000.0, risk_pct=1.0,
        )
        self.assertTrue(low["allowed"])
        self.assertTrue(high["allowed"])
        self.assertEqual(low["volume"], 0.4)
        self.assertEqual(high["volume"], 0.8)
        self.assertLessEqual(low["estimated_risk_usd"], low["risk_budget_usd"])
        self.assertLessEqual(high["estimated_risk_usd"], high["risk_budget_usd"])

    def test_eurusd_uses_broker_contract_profit_and_same_one_percent_policy(self):
        eurusd_contract = {"volume_min": 0.01, "volume_max": 100.0, "volume_step": 0.01}
        result = calculate_demo_volume_by_risk(
            self.mt5, "EURUSD", "BUY", 1.1000, 1.0950,
            eurusd_contract, balance=3000.0, equity=2900.0, risk_pct=1.0,
        )
        self.assertTrue(result["allowed"])
        self.assertAlmostEqual(result["risk_basis_usd"], 2900.0, places=2)
        self.assertAlmostEqual(result["risk_budget_usd"], 29.0, places=4)
        self.assertLessEqual(result["estimated_risk_usd"], result["risk_budget_usd"])
        self.assertAlmostEqual(result["volume"], 0.05, places=6)

    def test_enabled_demo_symbol_universe_includes_gold_and_eurusd(self):
        from unittest.mock import patch
        from src.Execution.Services.autonomous_demo_trader import _enabled_demo_symbols

        registry = type("FakeRegistry", (), {})()
        registry.get_active_matrix = lambda: [
            ("EURUSD", "H1", "Forex", "MT5"),
            ("XAUUSD", "H1", "Commodities", "MT5"),
        ]
        registry.get_all_registered = lambda: {
            "EURUSD": {"provider": "MT5"},
            "XAUUSD": {"provider": "MT5"},
        }
        with patch("src.Market.Universe.symbol_registry.SymbolRegistry.get_instance", return_value=registry):
            self.assertEqual(_enabled_demo_symbols(), ["XAUUSD", "EURUSD"])

    def test_allows_adaptive_risk_above_one_percent_but_rejects_above_safety_ceiling(self):
        result = calculate_demo_volume_by_risk(
            self.mt5, "XAUUSD", "BUY", 4184.17, 4173.04,
            self.symbol_info, balance=100000.0, equity=100000.0, risk_pct=2.0,
        )
        self.assertTrue(result["allowed"])
        self.assertAlmostEqual(result["risk_budget_usd"], 2000.0, places=2)
        with self.assertRaises(Exception):
            calculate_demo_volume_by_risk(
                self.mt5, "XAUUSD", "BUY", 4184.17, 4173.04,
                self.symbol_info, balance=100000.0, equity=100000.0, risk_pct=3.01,
            )

    def test_rejects_legacy_lower_risk_override(self):
        with self.assertRaises(Exception):
            calculate_demo_volume_by_risk(
                self.mt5, "EURUSD", "BUY", 1.1, 1.095,
                {"volume_min": 0.01, "volume_max": 100.0, "volume_step": 0.01},
                balance=100000.0, equity=100000.0, risk_pct=1.0 / 20.0,
            )


class TestStructuralStop(unittest.TestCase):
    def setUp(self):
        from src.Execution.Services.autonomous_demo_trader import AutonomousDemoTrader
        self.derive = AutonomousDemoTrader._derive_structural_stop
        self.candles = []
        price = 100.0
        for i in range(30):
            self.candles.append({"open": price, "high": price + 1.0,
                                 "low": price - 1.0, "close": price + 0.2})
            price += 0.1

    def test_buy_stop_is_below_entry_and_uses_swing_buffer(self):
        stop = self.derive(self.candles, "BUY", 103.0)
        self.assertIsNotNone(stop)
        self.assertLess(stop, 103.0)
        self.assertLess(stop, min(c["low"] for c in self.candles[-12:]))

    def test_sell_stop_is_above_entry_and_uses_swing_buffer(self):
        stop = self.derive(self.candles, "SELL", 101.0)
        self.assertIsNotNone(stop)
        self.assertGreater(stop, 101.0)
        self.assertGreater(stop, max(c["high"] for c in self.candles[-12:]))

    def test_rejects_insufficient_history_and_overwide_stop(self):
        self.assertIsNone(self.derive(self.candles[:10], "BUY", 103.0))
        self.assertIsNone(self.derive(self.candles, "BUY", 200.0))


if __name__ == "__main__":
    unittest.main()
