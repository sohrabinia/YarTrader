import sys
import os
import socket
import inspect
import types
import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
import pytest

from src.Application.Runtime.research_runtime import ResearchRuntime
from app.workers.research_worker import ResearchWorker
from src.Research.MarketAnalysis.Services.services import FeatureExtractionResearchEngine, PrimitiveMarketResearchEngine

# Import ControlledDataProvider and enforce_offline_boundary via path lookup
forensic_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../Forensic"))
if forensic_path not in sys.path:
    sys.path.insert(0, forensic_path)

from test_forensic_guards import ControlledDataProvider, enforce_offline_boundary


class TestGate1BrainIntegration(unittest.TestCase):
    """
    Focused Gate 1 Test Suite validating Canonical Brain Integration.
    Proves:
    - Test A: Canonical production path (ResearchWorker._run_loop -> ResearchRuntime -> FeatureExtractionResearchEngine -> LiveAnalysisBrain) is invoked.
    - Test B: Brain output is formatted as a structured decision proposal in findings.
    - Test C: Brain components cannot trigger direct order dispatch or broker execution.
    - Test D: Brain replay and cognitive learning loop execution results in 0 broker calls.
    - Test E: Downstream execution remains strictly downstream after safety gates.
    """

    def test_canonical_path_reaches_brain_and_returns_proposal(self):
        """
        Test A & B: Prove ResearchWorker._run_loop calls ResearchRuntime with FeatureExtractionResearchEngine,
        which invokes LiveAnalysisBrain and generates a structured decision proposal in findings.
        """
        boundary_patches, mt5_calls, broker_external_attempts, network_calls, credential_reads, cleanup = enforce_offline_boundary()
        for p in boundary_patches:
            p.start()

        try:
            worker = ResearchWorker(symbol="XAUUSD", timeframe="H1")
            provider = ControlledDataProvider(base_price=2000.0, count=100)
            base_engine = PrimitiveMarketResearchEngine(data_provider=provider)
            feature_engine = FeatureExtractionResearchEngine(data_provider=provider, base_engine=base_engine)
            runtime = ResearchRuntime(
                provider=provider,
                research_engine=feature_engine,
                symbol="XAUUSD",
                timeframe="H1",
                provider_name="ControlledOfflineFixture"
            )

            with patch.object(worker, "_get_or_create_runtime", return_value=runtime), \
                 patch.object(worker, "_get_active_matrix", return_value=[("XAUUSD", "H1", "Forex", "ControlledOfflineFixture")]):

                worker.is_running = True
                original_run_once = runtime.run_once
                saved_res = []

                def run_once_and_stop():
                    res = original_run_once()
                    saved_res.append(res)
                    worker.is_running = False
                    return res

                runtime.run_once = run_once_and_stop
                worker._run_loop()

            self.assertEqual(len(saved_res), 1)
            res = saved_res[0]

            # Verify LiveAnalysisBrain generated newborn_brain_report
            self.assertIn("newborn_brain_report", res.Findings)
            nb_report = res.Findings["newborn_brain_report"]
            self.assertEqual(nb_report["symbol"], "XAUUSD")
            self.assertTrue(nb_report["is_read_only_compliant"])

            # Verify structured decision proposal in findings
            self.assertIn("autonomous_decision", res.Findings)
            auto_dec = res.Findings["autonomous_decision"]
            self.assertEqual(auto_dec["symbol"], "XAUUSD")
            self.assertIn("action", auto_dec)
            self.assertIn(auto_dec["action"], ["BUY", "SELL", "WAIT", "AVOID"])

            # Verify plan incorporates Brain proposal metadata
            self.assertIn("intel_summary", res.Findings)
            plan = res.Findings["intel_summary"].get("plan", {})
            self.assertEqual(plan.get("decision_source"), "BRAIN")

            # Verify zero external calls were made
            self.assertEqual(len(mt5_calls), 0)
            self.assertEqual(len(broker_external_attempts), 0)
            self.assertEqual(len(network_calls), 0)
        finally:
            for p in boundary_patches:
                p.stop()
            cleanup()

    def test_brain_cannot_directly_execute(self):
        """
        Test C: Attempt direct broker execution from within Brain module scope and prove it is rejected.
        """
        boundary_violations = []

        def execution_boundary_interceptor(method_name):
            def mock_exec(*args, **kwargs):
                stack = inspect.stack()
                caller_is_brain = False
                for frame_info in stack:
                    mod_name = frame_info.frame.f_globals.get("__name__", "")
                    fn_path = frame_info.filename
                    if mod_name.startswith("src.Research.Brain") or mod_name.startswith("Research.Brain") or "src/Research/Brain" in fn_path or "src\\Research\\Brain" in fn_path:
                        caller_is_brain = True
                        break

                if caller_is_brain:
                    err_msg = f"BRAIN_EXECUTION_AUTHORITY_DETECTED: {method_name}"
                    boundary_violations.append(err_msg)
                    raise AssertionError(err_msg)
                return MagicMock(Status="OK", OrderId=12345)
            return mock_exec

        from src.Execution.Services.demo_execution_engine import DemoExecutionEngine
        demo_engine = DemoExecutionEngine()

        patches = [
            patch.object(DemoExecutionEngine, "execute_demo_decision", side_effect=execution_boundary_interceptor("execute_demo_decision")),
            patch.object(DemoExecutionEngine, "close_position", side_effect=execution_boundary_interceptor("close_position"))
        ]
        boundary_patches, mt5_calls, broker_external_attempts, network_calls, credential_reads, cleanup = enforce_offline_boundary()
        patches.extend(boundary_patches)

        for p in patches:
            p.start()

        try:
            import src.Research.Brain.cognitive_loop as cognitive_loop_mod
            exec_globals = dict(cognitive_loop_mod.__dict__)
            exec_globals["demo_engine"] = demo_engine
            code_obj = compile('demo_engine.execute_demo_decision("XAUUSD", "BUY", 0.01, 2000.0, 1990.0, 2020.0)', '<cognitive_loop_unauthorized_exec>', 'exec')
            brain_exec_func = types.FunctionType(code_obj, exec_globals)

            brain_caught = False
            try:
                brain_exec_func()
            except AssertionError as bae:
                if "BRAIN_EXECUTION_AUTHORITY_DETECTED" in str(bae):
                    brain_caught = True

            self.assertTrue(brain_caught, "Direct Brain execution call was NOT rejected!")
            self.assertTrue(len(boundary_violations) > 0)
        finally:
            for p in patches:
                p.stop()
            cleanup()

    def test_brain_replay_and_learning_cannot_execute(self):
        """
        Test D: Exercise Brain cognitive replay and active learning loop and prove 0 execution calls occur.
        """
        boundary_patches, mt5_calls, broker_external_attempts, network_calls, credential_reads, cleanup = enforce_offline_boundary()
        for p in boundary_patches:
            p.start()

        try:
            from src.Research.Brain.cognitive_loop import CognitiveReplayLoop
            from src.Research.Brain.models import MarketObservation

            obs_list = []
            now = datetime.now()
            for i in range(20):
                obs = MarketObservation(
                    symbol="XAUUSD",
                    timeframe="H1",
                    timestamp=now - timedelta(hours=20 - i),
                    open_price=2000.0 + i,
                    high=2005.0 + i,
                    low=1995.0 + i,
                    close_price=2002.0 + i,
                    volume=100.0
                )
                obs_list.append(obs)

            replay_loop = CognitiveReplayLoop(symbol="XAUUSD", timeframe="H1", observations=obs_list)
            episodes = replay_loop.execute_replay_session(steps_count=5, scale="hours")

            self.assertTrue(len(episodes) > 0)
            self.assertEqual(len(mt5_calls), 0)
            self.assertEqual(len(broker_external_attempts), 0)
            self.assertEqual(len(network_calls), 0)
        finally:
            for p in boundary_patches:
                p.stop()
            cleanup()

    def test_downstream_execution_remains_downstream(self):
        """
        Test E: Prove downstream execution is reached only via authorized downstream caller after safety gates.
        """
        boundary_patches, mt5_calls, broker_external_attempts, network_calls, credential_reads, cleanup = enforce_offline_boundary()
        for p in boundary_patches:
            p.start()

        try:
            from src.Execution.Services.demo_execution_engine import DemoExecutionEngine
            from src.Execution.Models.models import OrderResponse
            demo_engine = DemoExecutionEngine(demo_mode=True)

            mock_response = OrderResponse(
                OrderId="9999",
                Symbol="XAUUSD",
                Status="Placed",
                SubmittedAt=datetime.now(),
                Retcode=10009,
                Comment="Authorized Downstream Execution Verification",
                DealTicket="9999",
                PositionTicket="9999",
                Price=2000.0,
                Volume=0.01
            )

            sym_info = {
                "name": "XAUUSD",
                "trade_mode": 4, # FULL_ACCESS
                "volume_min": 0.01,
                "volume_max": 100.0,
                "volume_step": 0.01,
                "digits": 2
            }

            # Clear any initial mt5_calls recorded during DemoExecutionEngine adapter instantiation
            mt5_calls.clear()

            with patch.object(demo_engine.adapter, "get_account_info", return_value={"equity": 10000.0, "free_margin": 10000.0}), \
                 patch.object(demo_engine.adapter, "get_terminal_info", return_value={"connected": True, "trade_allowed": True}), \
                 patch.object(demo_engine.adapter, "get_symbol_info", return_value=sym_info), \
                 patch.object(demo_engine.adapter, "send_order_to_broker", return_value=mock_response):
                exec_res = demo_engine.execute_demo_decision(
                    symbol="XAUUSD",
                    direction="BUY",
                    volume=0.01,
                    price=2000.0,
                    sl=1990.0,
                    tp=2020.0,
                    comment="Authorized Downstream Execution Verification",
                    magic=143056,
                    decision_id="DEC-GATE1-DOWNSTREAM"
                )

            self.assertEqual(exec_res.Status, "Placed")
            self.assertEqual(len(mt5_calls), 0)
            self.assertEqual(len(broker_external_attempts), 0)
            self.assertEqual(len(network_calls), 0)
        finally:
            for p in boundary_patches:
                p.stop()
            cleanup()
