import unittest
from unittest.mock import MagicMock

from src.Execution.Services.autonomous_demo_trader import AutonomousDemoTrader


class TestAutonomousDemoReversalConfirmation(unittest.TestCase):
    def setUp(self):
        self.adapter = MagicMock()
        self.trader = AutonomousDemoTrader(adapter=self.adapter)

    def test_opposite_entry_may_be_reassessed_only_after_broker_confirms_flat(self):
        self.adapter.get_positions.return_value = []
        result = self.trader._confirm_position_flat("XAUUSD", 12345)
        self.assertTrue(result["confirmed"])

    def test_existing_position_blocks_opposite_entry_even_after_successful_close_response(self):
        self.adapter.get_positions.return_value = [{"ticket": 12345, "symbol": "XAUUSD"}]
        result = self.trader._confirm_position_flat("XAUUSD", 12345)
        self.assertFalse(result["confirmed"])
        self.assertIn("still open", result["reason"])

    def test_unknown_broker_state_blocks_opposite_entry(self):
        self.adapter.get_positions.return_value = None
        result = self.trader._confirm_position_flat("XAUUSD", 12345)
        self.assertFalse(result["confirmed"])
        self.assertIn("unknown", result["reason"])

    def test_broker_query_exception_blocks_opposite_entry(self):
        self.adapter.get_positions.side_effect = RuntimeError("connection lost")
        result = self.trader._confirm_position_flat("XAUUSD", 12345)
        self.assertFalse(result["confirmed"])
        self.assertIn("re-query failed", result["reason"])


if __name__ == "__main__":
    unittest.main()
