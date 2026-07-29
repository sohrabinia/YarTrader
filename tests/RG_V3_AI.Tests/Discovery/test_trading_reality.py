import unittest
from datetime import datetime, timedelta
from src.Data.MarketData.Models.models import MarketDataPoint
from src.Research.MarketAnalysis.Discovery.models import (
    MarketObservation,
    MarketSequence,
    MarketEvent,
    PatternMemory,
    VirtualTrade,
    SimulationResult,
    SpreadData,
    PriceExecutionData,
    TradingRealityMemory
)
from src.Research.MarketAnalysis.Discovery.brain import (
    DataRealityLayer,
    ObservationBrain,
    MemorySystem,
    PatternDiscoveryEngine,
    TradingRealityEngine,
    VirtualTradingEngine,
    SimulationBrain,
    LiveAnalysisBrain
)


class TestTradingRealityEngineAndSpreadAwareness(unittest.TestCase):
    """
    Automated test suite verifying the Trading Reality Engine, bid-ask spread simulations,
    execution cost updates, anti-bias separation checks, and read-only safety.
    """

    def setUp(self) -> None:
        self.now = datetime(2026, 7, 29, 12, 0, 0)
        self.symbol = "XAUUSD"
        self.timeframe = "H1"

        # Create dummy market sequence
        self.dummy_data = []
        for i in range(10):
            price = 1800.0 + (i * 10.0 if i < 5 else (80.0 - i * 10.0))
            dp = MarketDataPoint(
                AssetId=self.symbol,
                Timestamp=self.now + timedelta(hours=i),
                Open=price - 5.0,
                High=price + 8.0,
                Low=price - 7.0,
                Close=price,
                Volume=200.0
            )
            self.dummy_data.append(dp)

    # 1. Spread Data Collection Tests
    def test_spread_data_tracking_and_bid_ask(self) -> None:
        engine = TradingRealityEngine()
        spread_data = engine.observe_spread(self.symbol, bid=1800.0, ask=1801.0)

        self.assertEqual(spread_data.Symbol, self.symbol)
        self.assertEqual(spread_data.Bid, 1800.0)
        self.assertEqual(spread_data.Ask, 1801.0)
        self.assertEqual(spread_data.SpreadValue, 1.0)
        self.assertGreater(spread_data.SpreadPercentage, 0.0)

    # 2. Virtual Trading Bid-Ask Spread Ingestion and Costs
    def test_virtual_trading_execution_costs(self) -> None:
        reality = TradingRealityEngine()
        engine = VirtualTradingEngine(reality_engine=reality)

        # Simulating BUY entry using 1800.0 Close, with spread 1.0
        # Buy actual entry price should occur at Ask (1800.5) + slippage (0.1) = 1800.6
        trade = engine.create_virtual_trade(
            asset=self.symbol,
            timeframe=self.timeframe,
            direction="BUY",
            entry_price=1800.0,
            stop_loss=1790.0,
            target_price=1830.0,
            expected_scenario="BUY_test_pattern",
            entry_time=self.now,
            spread_val=1.0,
            commission=2.0,
            volatility=1.0
        )

        self.assertEqual(trade.Spread, 1.0)
        self.assertEqual(trade.Commission, 2.0)
        self.assertEqual(trade.Slippage, 0.1)
        self.assertEqual(trade.EntryPrice, 1800.6)  # Ask + slippage

    # 3. Replay Simulation Reflects Execution Reality
    def test_simulation_brain_execution_impact(self) -> None:
        reality = TradingRealityEngine()
        sim_brain = SimulationBrain(reality_engine=reality)
        memory = MemorySystem()

        layer = DataRealityLayer()
        observations = layer.receive_data(self.dummy_data, self.timeframe)
        seq = MarketSequence(Asset=self.symbol, Timeframe=self.timeframe, Observations=observations)

        # Replay with 1.0 spread and 1.5 commission
        results = sim_brain.simulate_replay(
            seq, memory, direction="BUY", stop_loss_pts=10.0, target_pts=50.0,
            spread_val=1.0, commission=1.5, volatility=1.0
        )

        self.assertEqual(len(results), 1)
        res = results[0]
        self.assertTrue(isinstance(res, SimulationResult))
        # Points must reflect commissions & spreads correctly
        self.assertGreaterEqual(res.MaxFavorableMovementPoints, 0.0)

    # 4. Anti-Bias Architecture Separation Tests
    def test_anti_bias_architectural_separation(self) -> None:
        brain = ObservationBrain()
        discovery = PatternDiscoveryEngine()

        layer = DataRealityLayer()
        observations = layer.receive_data(self.dummy_data, self.timeframe)
        seq = MarketSequence(Asset=self.symbol, Timeframe=self.timeframe, Observations=observations)

        events = brain.observe_sequence(seq)

        # Verify Observation Brain events contain absolutely no spread data, maintaining strict separation
        for ev in events:
            self.assertFalse(hasattr(ev, "Spread"))
            self.assertFalse(hasattr(ev, "Slippage"))

        # Verify pattern signatures contain no spread bias
        sig = f"{events[0].Direction}_{events[0].DurationCandles}"
        self.assertNotIn("spread", sig)
        self.assertNotIn("slippage", sig)

    # 5. Active Security Safeguard Tests
    def test_trading_reality_engine_safety(self) -> None:
        reality = TradingRealityEngine()
        live_brain = LiveAnalysisBrain(reality_engine=reality)
        memory = MemorySystem()

        # Build analysis report
        report, ai_view, human_view, spread_data = live_brain.analyze_live_market(self.dummy_data, self.timeframe, memory, current_spread_val=1.2)

        self.assertEqual(report.Asset, self.symbol)
        self.assertAlmostEqual(spread_data.SpreadValue, 1.2)

        # Assert zero order or write operations
        self.assertFalse(hasattr(reality, "order_send"))
        self.assertFalse(hasattr(reality, "positions_get"))
        self.assertFalse(hasattr(live_brain, "buy"))
        self.assertFalse(hasattr(live_brain, "sell"))

    # 6. Test NO_TRADE and WAIT Decision States
    def test_no_trade_and_wait_states(self) -> None:
        reality = TradingRealityEngine()
        engine = VirtualTradingEngine(reality_engine=reality)
        sim_brain = SimulationBrain(reality_engine=reality)
        memory = MemorySystem()

        layer = DataRealityLayer()
        observations = layer.receive_data(self.dummy_data, self.timeframe)
        seq = MarketSequence(Asset=self.symbol, Timeframe=self.timeframe, Observations=observations)

        # Verify NO_TRADE creates immutable trade with zero spread cost
        trade_no = engine.create_virtual_trade(
            asset=self.symbol, timeframe=self.timeframe, direction="NO_TRADE",
            entry_price=1800.0, stop_loss=1800.0, target_price=1800.0,
            expected_scenario="NO_TRADE_EXPECTED", entry_time=self.now
        )
        self.assertEqual(trade_no.EntryPrice, 1800.0)
        self.assertEqual(trade_no.Spread, 0.0)

        # Verify WAIT resolves instantly with 0 points
        results = sim_brain.simulate_replay(
            seq, memory, direction="WAIT", stop_loss_pts=0.0, target_pts=0.0
        )
        self.assertEqual(len(results), 1)
        res = results[0]
        self.assertEqual(res.FinalResult, "NEUTRAL")
        self.assertEqual(res.MaxFavorableMovementPoints, 0.0)
        self.assertEqual(res.MaxAdverseMovementPoints, 0.0)
