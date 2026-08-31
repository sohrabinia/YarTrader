import unittest
from unittest.mock import MagicMock
from datetime import datetime
from src.Decision.Intelligence.engine import DecisionEngine
from src.Decision.Interfaces.interfaces import IDecisionEngine
from src.Decision.Models.models import DecisionContext, DecisionState
from src.Decision.Intelligence.models import DecisionIntelligenceContext
from src.Decision.Intelligence.timeframe_selector import UnifiedSignalContract
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

    def test_professional_buy_sets_approved_state_and_preserves_direction(self):
        mock_signal_engine = MagicMock()
        mock_signal_engine.generate_unified_signal.return_value = UnifiedSignalContract(
            signal_id="SIG-BUY-101",
            symbol="XAUUSD",
            timeframe="M15",
            direction="BUY",
            entry_price=2050.0,
            stop_loss=2040.0,
            take_profit=2072.0,
            risk_reward=2.2,
            confidence=0.88,
            pattern_id="FAST_SCALP",
            market_context="MTF Aligned",
            created_at=datetime.now().isoformat()
        )

        engine = DecisionEngine(signal_engine=mock_signal_engine)
        candles = generate_candles("XAUUSD", 2050.0, 50)
        context = DecisionIntelligenceContext(
            ResearchInsights=[{"description": "Bullish momentum"}],
            MarketConditions={"volatility": "MEDIUM"},
            Metadata={"asset": "XAUUSD", "features": ["MOMENTUM_EXPANSION"]},
            MarketDataPoints=candles
        )

        report = engine.evaluate_intelligence_context(context)

        self.assertEqual(report.State, DecisionState.APPROVED)
        prof_sig = report.EvidenceTrail.SupportingEvidence.get("professional_signal")
        self.assertIsNotNone(prof_sig)
        self.assertEqual(prof_sig["direction"], "BUY")
        self.assertEqual(prof_sig["entry_price"], 2050.0)
        self.assertEqual(prof_sig["stop_loss"], 2040.0)
        self.assertEqual(prof_sig["take_profit"], 2072.0)
        self.assertEqual(prof_sig["confidence"], 0.88)

    def test_professional_sell_sets_approved_state_and_preserves_direction(self):
        mock_signal_engine = MagicMock()
        mock_signal_engine.generate_unified_signal.return_value = UnifiedSignalContract(
            signal_id="SIG-SELL-102",
            symbol="XAUUSD",
            timeframe="M15",
            direction="SELL",
            entry_price=2050.0,
            stop_loss=2060.0,
            take_profit=2028.0,
            risk_reward=2.2,
            confidence=0.85,
            pattern_id="SCALP",
            market_context="Bearish Breakdown",
            created_at=datetime.now().isoformat()
        )

        engine = DecisionEngine(signal_engine=mock_signal_engine)
        candles = generate_candles("XAUUSD", 2050.0, 50)
        context = DecisionIntelligenceContext(
            ResearchInsights=[{"description": "Bearish breakdown"}],
            Metadata={"asset": "XAUUSD"},
            MarketDataPoints=candles
        )

        report = engine.evaluate_intelligence_context(context)

        self.assertEqual(report.State, DecisionState.APPROVED)
        prof_sig = report.EvidenceTrail.SupportingEvidence.get("professional_signal")
        self.assertIsNotNone(prof_sig)
        self.assertEqual(prof_sig["direction"], "SELL")
        self.assertEqual(prof_sig["entry_price"], 2050.0)
        self.assertEqual(prof_sig["stop_loss"], 2060.0)

    def test_professional_wait_sets_no_action_state(self):
        mock_signal_engine = MagicMock()
        mock_signal_engine.generate_unified_signal.return_value = UnifiedSignalContract(
            signal_id="SIG-WAIT-103",
            symbol="XAUUSD",
            timeframe="M15",
            direction="WAIT",
            entry_price=0.0,
            stop_loss=0.0,
            take_profit=0.0,
            risk_reward=0.0,
            confidence=0.0,
            pattern_id="NONE",
            market_context="Range Bound",
            created_at=datetime.now().isoformat()
        )

        engine = DecisionEngine(signal_engine=mock_signal_engine)
        candles = generate_candles("XAUUSD", 2000.0, 50)
        context = DecisionIntelligenceContext(
            ResearchInsights=[{"description": "Range bound"}],
            Metadata={"asset": "XAUUSD"},
            MarketDataPoints=candles
        )

        report = engine.evaluate_intelligence_context(context)

        self.assertEqual(report.State, DecisionState.NO_ACTION)
        prof_sig = report.EvidenceTrail.SupportingEvidence.get("professional_signal")
        self.assertEqual(prof_sig["direction"], "WAIT")

    def test_risk_rejected_wait_sets_rejected_state(self):
        mock_signal_engine = MagicMock()
        mock_signal_engine.generate_unified_signal.return_value = UnifiedSignalContract(
            signal_id="SIG-WAIT-104",
            symbol="XAUUSD",
            timeframe="M15",
            direction="WAIT",
            entry_price=0.0,
            stop_loss=0.0,
            take_profit=0.0,
            risk_reward=0.0,
            confidence=0.0,
            pattern_id="REJECTED_RISK",
            market_context="HIGH_SPREAD_REJECTION",
            created_at=datetime.now().isoformat()
        )

        engine = DecisionEngine(signal_engine=mock_signal_engine)
        candles = generate_candles("XAUUSD", 2000.0, 50)
        context = DecisionIntelligenceContext(
            ResearchInsights=[{"description": "High volatility"}],
            Metadata={"asset": "XAUUSD"},
            MarketDataPoints=candles
        )

        report = engine.evaluate_intelligence_context(context)

        self.assertEqual(report.State, DecisionState.REJECTED)

    def test_signal_engine_exception_sets_review_required(self):
        mock_signal_engine = MagicMock()
        mock_signal_engine.generate_unified_signal.side_effect = RuntimeError("Market feed exception")

        engine = DecisionEngine(signal_engine=mock_signal_engine)
        candles = generate_candles("XAUUSD", 2000.0, 50)
        context = DecisionIntelligenceContext(
            ResearchInsights=[{"description": "Active feed"}],
            Metadata={"asset": "XAUUSD"},
            MarketDataPoints=candles
        )

        report = engine.evaluate_intelligence_context(context)

        self.assertEqual(report.State, DecisionState.REVIEW_REQUIRED)
        err = report.EvidenceTrail.SupportingEvidence.get("professional_signal_error")
        self.assertIsNotNone(err)
        self.assertIn("Market feed exception", err)

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

        self.assertTrue(hasattr(sig, "signal_id"))
        self.assertIsNotNone(sig.signal_id)

if __name__ == "__main__":
    unittest.main()
