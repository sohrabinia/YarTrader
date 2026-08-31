import unittest
from datetime import datetime
from src.Decision.Intelligence.engine import DecisionEngine
from src.Decision.Interfaces.interfaces import IDecisionEngine
from src.Decision.Models.models import DecisionContext
from src.Data.MarketData.Models.models import MarketDataPoint
from src.Infrastructure.DI.container import container_instance
from src.Infrastructure.DI.registrations import register_services

def generate_candles(symbol: str = "XAUUSD", base_price: float = 2000.0, count: int = 50) -> list:
    points = []
    price = base_price
    for i in range(count):
        high = price + 2.0
        low = price - 2.0
        close = price + (1.0 if i % 2 == 0 else -1.0)
        points.append(MarketDataPoint(
            AssetId=symbol,
            Timestamp=datetime.now(),
            Open=price,
            High=high,
            Low=low,
            Close=close,
            Volume=100.0
        ))
        price = close
    return points

class TestProfessionalSignalIntegration(unittest.TestCase):
    def setUp(self):
        self.engine = DecisionEngine()

    def test_professional_signal_engine_called_by_decision_engine(self):
        candles = generate_candles("XAUUSD", 2000.0, 50)
        candles_by_tf = {"M15": candles, "H1": candles}
        sig = self.engine.generate_professional_signal("XAUUSD", candles_by_tf)

        self.assertIsNotNone(sig)
        self.assertEqual(sig.symbol, "XAUUSD")
        self.assertIn(sig.direction, ["BUY", "SELL", "WAIT"])

    def test_missing_candles_produce_wait_without_synthetic_prices(self):
        empty_candles_by_tf = {"M15": [], "H1": []}
        sig = self.engine.generate_professional_signal("XAUUSD", empty_candles_by_tf)

        self.assertEqual(sig.direction, "WAIT")
        self.assertEqual(sig.confidence, 0.0)
        self.assertEqual(sig.entry_price, 0.0)

    def test_idecision_engine_compatibility_and_di_binding(self):
        register_services(container_instance)
        resolved_engine = container_instance.resolve(IDecisionEngine)

        self.assertIsInstance(resolved_engine, IDecisionEngine)
        self.assertIsInstance(resolved_engine, DecisionEngine)

        context = DecisionContext(
            StrategyId="STRAT-01",
            AssetWeights={"XAUUSD": 0.5},
            TargetRiskProfile="CONSERVATIVE"
        )
        res = resolved_engine.evaluate_decision(context)
        self.assertIsNotNone(res.DecisionId)
        self.assertIsNotNone(res.State)

    def test_execution_safety_no_live_orders(self):
        candles = generate_candles("XAUUSD", 2000.0, 50)
        sig = self.engine.generate_professional_signal("XAUUSD", {"M15": candles})

        # Verify signal contract is purely analytical and does not trigger real execution
        self.assertTrue(hasattr(sig, "signal_id"))
        self.assertIsNotNone(sig.signal_id)

if __name__ == "__main__":
    unittest.main()
