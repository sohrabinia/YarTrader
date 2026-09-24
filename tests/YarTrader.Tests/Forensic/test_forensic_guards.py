import sys
import os
import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
import pytest

from src.Application.Runtime.research_runtime import ResearchRuntime
from src.Research.MarketAnalysis.Services.services import PrimitiveMarketResearchEngine, FeatureExtractionResearchEngine
from src.Data.MarketData.Models.models import MarketDataResponse, MarketDataPoint
from app.workers.research_worker import ResearchWorker


class ControlledDataProvider:
    """Deterministic, offline market data provider fixture for forensic runtime tests."""
    def __init__(self, base_price: float = 2000.0, count: int = 100) -> None:
        self.base_price = base_price
        self.count = count

    def retrieve_market_data(self, request) -> MarketDataResponse:
        now = datetime.now()
        asset = getattr(request, "Asset", "XAUUSD")
        data_points = []
        for i in range(self.count):
            t = now - timedelta(minutes=(self.count - i) * 15)
            # Pure price movement without indicators
            p = self.base_price + (i * 0.1)
            dp = MarketDataPoint(
                AssetId=asset,
                Timestamp=t,
                Open=p,
                High=p + 0.5,
                Low=p - 0.5,
                Close=p + 0.2,
                Volume=100.0
            )
            data_points.append(dp)
        return MarketDataResponse(
            Request=request,
            DataPoints=data_points,
            RetrievedAt=now
        )


@pytest.mark.forensic_guard
class TestIndicatorForensicGuard(unittest.TestCase):
    """
    CTO Mandatory Forensic Guard 1: Forbidden Indicator Execution Guard.
    Interprets and intercepts indicator execution across top-level and local/lazy imports.
    Proves whether the canonical production decision path executes forbidden technical indicators.
    """

    def test_forbidden_indicator_execution_guard(self):
        """
        Drives the canonical production decision path (ResearchWorker -> ResearchRuntime -> PrimitiveMarketResearchEngine -> ExecutionIntelligenceCore)
        under controlled deterministic fixtures and asserts zero forbidden indicator execution.
        """
        forbidden_indicators = ["RSI", "ATR", "SMA", "EMA", "MACD", "Bollinger", "ADX", "Stochastic", "CCI"]
        executed_indicators = []

        # Intercept functions in src.Research.analysis_pipeline and calculators
        from src.Research import analysis_pipeline

        def indicator_interceptor(indicator_name):
            def mock_func(*args, **kwargs):
                err_msg = f"FORBIDDEN_INDICATOR_EXECUTED: {indicator_name}"
                executed_indicators.append(indicator_name)
                raise AssertionError(err_msg)
            return mock_func

        # Patch indicator computation methods in analysis_pipeline
        patches = [
            patch.object(analysis_pipeline.TechnicalAnalysisEngine, "analyze", side_effect=indicator_interceptor("TechnicalAnalysisEngine")),
        ]

        if hasattr(analysis_pipeline, "MomentumAnalysisEngine"):
            patches.append(patch.object(analysis_pipeline.MomentumAnalysisEngine, "analyze", side_effect=indicator_interceptor("MomentumAnalysisEngine")))

        # Intercept any function in calculators or indicators if present
        try:
            from src.Research.Features import calculators
            for calc_name in ["RSI", "ATR", "SMA", "EMA", "MACD", "BollingerBands", "ADX", "Stochastic", "CCI"]:
                if hasattr(calculators, calc_name):
                    patches.append(patch.object(calculators, calc_name, side_effect=indicator_interceptor(calc_name)))
        except ImportError:
            pass

        for p in patches:
            p.start()

        try:
            # Drive Canonical Production Decision Path
            provider = ControlledDataProvider(base_price=2000.0, count=100)
            runtime = ResearchRuntime(provider=provider, symbol="XAUUSD", timeframe="H1")

            # Execute one research cycle
            result = runtime.run_once()

            # Verify decision structure produced
            self.assertIsNotNone(result)
            self.assertIn("autonomous_decision", result.Findings)

            # If cycle completes with zero indicator execution, classification is PASS
            classification = "PASS"
            print(f"\n[FORENSIC_GUARD_1_RESULT]: {classification} - Canonical production decision path executed indicator-free.")

        except AssertionError as ae:
            if "FORBIDDEN_INDICATOR_EXECUTED" in str(ae):
                classification = "FAIL — EXPECTED BASELINE ARCHITECTURAL FINDING"
                print(f"\n[FORENSIC_GUARD_1_RESULT]: {classification} - {ae}")
                raise
            else:
                raise
        finally:
            for p in patches:
                p.stop()


@pytest.mark.forensic_guard
class TestBrainExecutionAuthorityGuard(unittest.TestCase):
    """
    CTO Mandatory Forensic Guard 2: Brain Execution Authority Guard.
    Detects if any Brain component direct-connects or bypasses safety boundaries to execute broker orders.
    """

    def test_brain_execution_authority_guard(self):
        """
        Monitors execution boundaries (order_send, send_order_to_broker, execute_demo_decision, place_order)
        and verifies that Brain components do NOT possess direct broker execution authority.
        """
        boundary_violations = []

        def execution_boundary_interceptor(method_name):
            def mock_exec(*args, **kwargs):
                # Inspect caller stack frame to verify caller identity
                import traceback
                stack = traceback.format_stack()
                caller_is_brain = any("/Research/Brain/" in frame or "\\Research\\Brain\\" in frame for frame in stack)

                if caller_is_brain:
                    err_msg = f"BRAIN_EXECUTION_AUTHORITY_DETECTED: {method_name}"
                    boundary_violations.append(err_msg)
                    raise AssertionError(err_msg)
                return MagicMock(Status="OK", OrderId=12345)
            return mock_exec

        # Patch execution methods across DemoExecutionEngine and broker adapters
        from src.Execution.Services.demo_execution_engine import DemoExecutionEngine
        from src.Execution.Adapters.mt5_adapter import RealMT5BrokerAdapter

        patches = [
            patch.object(DemoExecutionEngine, "execute_demo_decision", side_effect=execution_boundary_interceptor("execute_demo_decision")),
            patch.object(DemoExecutionEngine, "close_position", side_effect=execution_boundary_interceptor("close_position")),
            patch.object(RealMT5BrokerAdapter, "send_order_to_broker", side_effect=execution_boundary_interceptor("send_order_to_broker")),
        ]

        for p in patches:
            p.start()

        try:
            # Exercise Brain components and verify decision proposals
            from src.Research.Brain.cognitive_loop import CognitiveReplayLoop
            from src.Research.Brain.models import MarketObservation

            # Create mock observations for CognitiveReplayLoop (at least 30 observations for multi-step replay)
            obs_list = []
            now = datetime.now()
            for i in range(30):
                obs = MarketObservation(
                    symbol="XAUUSD",
                    timeframe="H1",
                    timestamp=now - timedelta(hours=30 - i),
                    open_price=2000.0 + i,
                    high=2005.0 + i,
                    low=1995.0 + i,
                    close_price=2002.0 + i,
                    volume=100.0
                )
                obs_list.append(obs)

            replay_loop = CognitiveReplayLoop(symbol="XAUUSD", timeframe="H1", observations=obs_list)
            episodes = replay_loop.execute_replay_session(steps_count=10, scale="hours")

            # Replay loop generates episodes and hypotheses without directly calling broker/execution engine
            self.assertTrue(len(episodes) > 0)
            self.assertEqual(len(boundary_violations), 0)

            classification = "PASS"
            print(f"\n[FORENSIC_GUARD_2_RESULT]: {classification} - Brain components generate decision proposals without direct execution authority.")

        except AssertionError as ae:
            if "BRAIN_EXECUTION_AUTHORITY_DETECTED" in str(ae):
                classification = "FAIL — EXPECTED BASELINE ARCHITECTURAL FINDING"
                print(f"\n[FORENSIC_GUARD_2_RESULT]: {classification} - {ae}")
                raise
            else:
                raise
        finally:
            for p in patches:
                p.stop()
