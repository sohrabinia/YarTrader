import unittest
from datetime import datetime
from src.Intelligence.Execution.narrative import MarketNarrativeEngine
from src.Intelligence.Execution.liquidity import LiquidityIntelligenceEngine
from src.Intelligence.Execution.zones import InstitutionalZoneEngine
from src.Intelligence.Execution.alignment import MultiTimeframeAlignmentEngine
from src.Intelligence.Execution.similarity import PatternSimilarityIntelligenceEngine
from src.Intelligence.Execution.portfolio import PortfolioRiskIntelligenceEngine
from src.Intelligence.Execution.execution_planner import ExecutionIntelligencePlanner
from src.Intelligence.Execution.core import ExecutionIntelligenceCore

class TestExecutionIntelligenceUnit(unittest.TestCase):
    """
    Unit testing suite for the Institutional Execution Intelligence Platform components.
    Ensures mathematical accuracy and compliance with passive-only advisory constraints.
    """

    def setUp(self) -> None:
        # Generate 15 sample candles forming a swing high and displacement
        self.candles = []
        for i in range(15):
            o = 100.0 + i
            h = o + 2.0
            l = o - 1.0
            c = o + 1.0
            # form a swing high at index 7
            if i == 7:
                h = 130.0
                c = 120.0
            # form a strong displacement (OB & FVG) at index 11
            if i == 11:
                o = 111.0
                c = 125.0
                h = 126.0
                l = 110.0
            self.candles.append({
                "time": 1700000000 + i * 3600,
                "open": o,
                "high": h,
                "low": l,
                "close": c,
                "tick_volume": 1000
            })

    def test_market_narrative_detection(self) -> None:
        engine = MarketNarrativeEngine(swing_window=1)
        res = engine.analyze_narrative(self.candles)

        self.assertIn("state", res)
        self.assertIn("trend", res)
        self.assertGreater(len(res["swings"]), 0)
        self.assertGreater(len(res["structure_nodes"]), 0)

    def test_liquidity_detection(self) -> None:
        narrative_engine = MarketNarrativeEngine(swing_window=1)
        narrative_res = narrative_engine.analyze_narrative(self.candles)

        liq_engine = LiquidityIntelligenceEngine(tolerance_pct=1.0)
        liq_res = liq_engine.analyze_liquidity(self.candles, narrative_res["swings"])

        self.assertIn("equal_highs", liq_res)
        self.assertIn("resting_bsl", liq_res)
        self.assertIn("voids", liq_res)

    def test_institutional_zones_detection(self) -> None:
        narrative_engine = MarketNarrativeEngine(swing_window=1)
        narrative_res = narrative_engine.analyze_narrative(self.candles)

        zone_engine = InstitutionalZoneEngine(fvg_min_pct=0.01)
        zones_res = zone_engine.analyze_zones(self.candles, narrative_res["swings"])

        self.assertIn("order_blocks", zones_res)
        self.assertIn("fair_value_gaps", zones_res)
        self.assertIn("equilibrium", zones_res)

    def test_multi_timeframe_alignment(self) -> None:
        engine = MultiTimeframeAlignmentEngine()
        h4_narrative = {"trend": "BULLISH", "state": "EXPANSION_UP"}
        h1_narrative = {"trend": "BULLISH", "state": "EXPANSION_UP"}

        narratives = {"H4": h4_narrative, "H1": h1_narrative}
        res = engine.align_structures("XAUUSD", narratives)

        self.assertEqual(res["alignment"], "FULLY_ALIGNED_BULLISH")
        self.assertEqual(res["confidence"], 88)

    def test_pattern_similarity_search(self) -> None:
        engine = PatternSimilarityIntelligenceEngine()
        current_sig = [1.0, 2.0, 1.5, 3.0]
        history = [
            {"pattern_id": "pat-1", "signature": [1.1, 2.1, 1.4, 2.9], "occurrences_count": 5, "success_rate": 75.0}
        ]
        res = engine.find_similar_structures(current_sig, history)

        self.assertTrue(res["similar_pattern_found"])
        self.assertGreater(res["average_similarity_score"], 90.0)

    def test_portfolio_risk_budgeting(self) -> None:
        engine = PortfolioRiskIntelligenceEngine(max_heat_pct=6.0)
        active_trades = [
            {"symbol": "XAUUSD", "entry": 2000.0, "stop": 1990.0, "volume": 1.0, "status": "RUNNING"}
        ]
        res = engine.calculate_portfolio_risk(active_trades, virtual_balance=10000.0)

        self.assertFalse(res["approved"])
        self.assertEqual(res["portfolio_heat_pct"], 10.0) # Risk = (2000-1990)*100*1 = 1000. Heat = 1000/10000 * 100 = 10%. So heat is 10%, which is > 6.0%.
        self.assertIn("Portfolio Heat (10.00%) exceeds system budget (6.0%)", res["violations"])

    def test_execution_intelligence_core_isolation(self) -> None:
        core = ExecutionIntelligenceCore.get_instance()
        # Evaluate for XAUUSD_H1
        res1 = core.evaluate_context("XAUUSD", "H1", self.candles)
        # Evaluate for EURUSD_M15
        res2 = core.evaluate_context("EURUSD", "M15", self.candles)

        # Confirm both contexts are fully isolated and distinct
        state1 = core.get_context_state("XAUUSD", "H1")
        state2 = core.get_context_state("EURUSD", "M15")

        self.assertEqual(state1["symbol"], "XAUUSD")
        self.assertEqual(state2["symbol"], "EURUSD")
        self.assertEqual(state1["timeframe"], "H1")
        self.assertEqual(state2["timeframe"], "M15")
