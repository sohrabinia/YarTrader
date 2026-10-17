import unittest

import pytest

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

    def test_rejects_adaptive_risk_above_one_percent_safety_ceiling(self):
        for risk_pct in (1.01, 2.0, 3.01):
            with self.subTest(risk_pct=risk_pct), self.assertRaises(Exception):
                calculate_demo_volume_by_risk(
                    self.mt5, "XAUUSD", "BUY", 4184.17, 4173.04,
                    self.symbol_info, balance=100000.0, equity=100000.0, risk_pct=risk_pct,
                )

    def test_rejects_legacy_lower_risk_override(self):
        with self.assertRaises(Exception):
            calculate_demo_volume_by_risk(
                self.mt5, "EURUSD", "BUY", 1.1, 1.095,
                {"volume_min": 0.01, "volume_max": 100.0, "volume_step": 0.01},
                balance=100000.0, equity=100000.0, risk_pct=1.0 / 20.0,
            )


class TestLegacyIndicatorStopRemoved(unittest.TestCase):
    def test_atr_derived_stop_helper_is_not_available(self):
        from src.Execution.Services.autonomous_demo_trader import AutonomousDemoTrader
        self.assertFalse(hasattr(AutonomousDemoTrader, "_derive_structural_stop"))


if __name__ == "__main__":
    unittest.main()
if __name__ == "__main__":
    unittest.main()


def test_gold_minimum_lot_with_eight_dollar_stop_fits_one_percent_of_2726_wallet():
    # Broker minimum 0.01 XAUUSD lot risks about $8 with an $8 price stop
    # under this broker's 100-unit contract. 1% of $2,726.52 is $27.2652;
    # the old three-slot allocator incorrectly passed only about $9.09.
    result = calculate_demo_volume_by_risk(
        FakeMT5(), "XAUUSD", "SELL", 4161.0, 4169.0,
        {"volume_min": 0.01, "volume_max": 100.0, "volume_step": 0.01},
        balance=2726.52, equity=2726.52, risk_pct=1.0,
    )
    assert result["allowed"] is True
    assert result["risk_budget_usd"] == pytest.approx(27.2652)
    assert result["minimum_lot_risk_usd"] == pytest.approx(8.0)
    assert result["volume"] >= 0.01
    assert result["estimated_risk_usd"] <= result["risk_budget_usd"]


def test_gold_tp_promotes_to_nearest_confirmed_structural_base_when_stop_widening_breaks_rr():
    from src.Execution.Services.autonomous_demo_trader import AutonomousDemoTrader

    # Entry 2350, final structural stop 2340 => $10 risk distance.
    # The nearest target at 2355 only pays 0.5R and must be skipped; the next
    # confirmed base at 2365 pays 1.5R before costs. A future/unconfirmed target
    # and a target on the wrong side must never be used.
    candidates = [
        {"price": 2355.0, "timeframe": "M15", "event_id": "near", "confirmation_time": 100},
        {"price": 2365.0, "timeframe": "H1", "event_id": "next", "confirmation_time": 100},
        {"price": 2400.0, "timeframe": "H4", "event_id": "future", "confirmation_time": 9999},
        {"price": 2300.0, "timeframe": "H4", "event_id": "wrong-side", "confirmation_time": 100},
    ]
    selected = AutonomousDemoTrader._best_structural_target_for_net_rr(
        candidates, "BUY", entry=2350.0, risk_distance=10.0,
        cost_allowance=0.5, min_net_rr=1.0, decision_time=200,
    )
    assert selected is not None
    price, evidence, net_rr = selected
    assert price == 2365.0
    assert evidence["event_id"] == "next"
    assert evidence["timeframe"] == "H1"
    assert net_rr > 1.0


def test_gold_tp_does_not_invent_target_when_no_confirmed_structure_clears_net_rr():
    from src.Execution.Services.autonomous_demo_trader import AutonomousDemoTrader

    selected = AutonomousDemoTrader._best_structural_target_for_net_rr(
        [{"price": 2355.0, "timeframe": "M15", "event_id": "near", "confirmation_time": 100}],
        "BUY", entry=2350.0, risk_distance=10.0,
        cost_allowance=0.5, min_net_rr=1.0, decision_time=200,
    )
    assert selected is None
