import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from src.Learning.Services.autonomous_strategy_discovery import AutonomousStrategyDiscovery


class TestAutonomousStrategyDiscovery(unittest.TestCase):
    def test_deals_are_idempotent_and_partial_closes_aggregate_to_one_position(self):
        with tempfile.TemporaryDirectory() as temp:
            store = AutonomousStrategyDiscovery(Path(temp))
            mt5 = SimpleNamespace(DEAL_ENTRY_IN=0, DEAL_ENTRY_OUT=1, DEAL_ENTRY_OUT_BY=3)
            deals = [
                {"ticket": 100, "position_id": 77, "entry": 0, "symbol": "XAUUSD",
                 "order": 100, "price": 2000.0, "volume": 0.02, "profit": 0.0,
                 "commission": 0.0, "swap": 0.0, "fee": 0.0, "time": 100,
                 "time_msc": 100000, "comment": "YarBase:SCALP", "reason": 0},
                {"ticket": 101, "position_id": 77, "entry": 1, "symbol": "XAUUSD",
                 "order": 101, "price": 2001.0, "volume": 0.01, "profit": 1.0,
                 "commission": -0.1, "swap": 0.0, "fee": 0.0, "time": 200,
                 "time_msc": 200000, "comment": "", "reason": 5},
                {"ticket": 102, "position_id": 77, "entry": 1, "symbol": "XAUUSD",
                 "order": 102, "price": 2000.5, "volume": 0.01, "profit": 0.5,
                 "commission": -0.1, "swap": 0.0, "fee": 0.0, "time": 210,
                 "time_msc": 210000, "comment": "", "reason": 4},
            ]
            first = store.sync_history(deals, mt5, symbol="XAUUSD")
            second = store.sync_history(deals, mt5, symbol="XAUUSD")
            self.assertEqual(first["new_deals_recorded"], 3)
            self.assertEqual(second["new_deals_recorded"], 0)
            report = store.build_discovery_report()
            self.assertEqual(report["closed_deal_records"], 2)
            self.assertEqual(report["closed_position_count"], 1)
            cohort = report["cohorts"][0]
            self.assertEqual(cohort["cohort"], "XAUUSD|SCALP")
            self.assertEqual(cohort["closed_position_count"], 1)
            self.assertEqual(cohort["closed_deal_count"], 2)
            self.assertAlmostEqual(cohort["net_expectancy_per_position"], 1.3)
            self.assertFalse(cohort["activation_allowed"])
            self.assertFalse(report["auto_promotion_enabled"])

    def test_position_snapshot_is_atomic_and_authoritative(self):
        with tempfile.TemporaryDirectory() as temp:
            store = AutonomousStrategyDiscovery(Path(temp))
            store.snapshot_positions([{"ticket": 12, "identifier": 12, "symbol": "EURUSD",
                                       "comment": "YarBase:RTM", "magic": 100001, "type": 1,
                                       "volume": 0.01, "price_open": 1.1, "price_current": 1.09,
                                       "sl": 1.12, "tp": 0.0, "profit": 1.0, "time": 123}],
                                      now_utc="2026-10-14T00:00:00+00:00")
            payload = json.loads(store.positions_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["open_positions_count"], 1)
            self.assertEqual(payload["positions"][0]["strategy"], "RTM")
            self.assertEqual(payload["positions"][0]["stop_loss"], 1.12)


if __name__ == "__main__":
    unittest.main()
