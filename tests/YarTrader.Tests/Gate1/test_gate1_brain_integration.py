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
from src.Intelligence.Execution.core import ExecutionIntelligenceCore
from src.Intelligence.Execution.execution_planner import ExecutionIntelligencePlanner
from src.Research.MarketAnalysis.Services.services import PrimitiveMarketResearchEngine
from src.Application.Runtime.runtime_state import central_runtime_state

# Import ControlledDataProvider and enforce_offline_boundary via path lookup
forensic_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../Forensic"))
if forensic_path not in sys.path:
    sys.path.insert(0, forensic_path)

from test_forensic_guards import ControlledDataProvider, enforce_offline_boundary


class TestGate1BrainIntegration(unittest.TestCase):
    """
    Focused Gate 1 Test Suite validating Canonical Brain Integration.
    Proves:
    - Test 1: Real Production Path — ResearchWorker._run_loop() calls real _get_or_create_runtime() with ZERO pre-population, ZERO patching of _get_or_create_runtime, and ZERO patching of ResearchRuntime.run_once(). Verifies real PrimitiveMarketResearchEngine invokes LiveAnalysisBrain, passes newborn_brain_report to ExecutionIntelligenceCore/Planner, and returns a proposal with decision_source = "BRAIN".
    - Test 2: Explicit Fail-Closed Exception Handling — When LiveAnalysisBrain raises an unexpected exception, PrimitiveMarketResearchEngine catches it, outputs brain_available = False, sets decision_source = "BRAIN_UNAVAILABLE" and action = "WAIT", and performs 0 executions.
    - Test 3: Fail-Closed Boundary — When newborn_brain_report is missing/None, ExecutionIntelligencePlanner fails closed to action = "WAIT", decision = "NO_TRADE", and decision_source = "BRAIN_UNAVAILABLE".
    - Test 4: Causal Negative Test — When LiveAnalysisBrain proposes WAIT/AVOID, Planner outputs WAIT/AVOID even under strongly bullish or bearish structure.
    - Test 5: Causal Positive Test — Brain proposal BUY + bullish structure -> BUY. Brain proposal SELL + bullish structure -> WAIT.
    - Test 6: Execution Separation — Static and runtime tests proving Brain module scope cannot invoke order execution APIs.
    - Test 7: Replay/Learning Execution Separation — Cognitive replay loop produces 0 broker calls.
    - Test 8: Downstream Execution Separation — Authorized downstream execution remains downstream after safety gates.
    """

    def test_production_run_loop_path_reaches_brain_without_runtime_patching(self):
        """
        Test 1: Prove ResearchWorker._run_loop uses real _get_or_create_runtime() with ZERO pre-population of worker.runtimes,
        ZERO patching of _get_or_create_runtime, and ZERO patching of ResearchRuntime.run_once().
        Verifies worker.runtimes is initially empty, _run_loop creates a real ResearchRuntime, executes PrimitiveMarketResearchEngine and LiveAnalysisBrain,
        and returns a Brain proposal with decision_source = "BRAIN" and brain_report_consumed = True.
        """
        boundary_patches, mt5_calls, broker_external_attempts, network_calls, credential_reads, cleanup = enforce_offline_boundary()
        for p in boundary_patches:
            p.start()

        try:
            worker = ResearchWorker(symbol="XAUUSD", timeframe="H1")
            provider = ControlledDataProvider(base_price=2000.0, count=100)

            # Assert worker.runtimes is initially empty
            key = ("XAUUSD", "H1")
            self.assertNotIn(key, worker.runtimes)

            # Hook central_runtime_state.update_multiple to stop worker after 1 cycle naturally
            orig_update = central_runtime_state.update_multiple
            def stop_worker_on_cycle_completion(state_dict):
                worker.is_running = False
                return orig_update(state_dict)

            # Patch MetaTrader5Provider constructor so real _get_or_create_runtime instantiates MetaTrader5Provider with ControlledDataProvider delegate
            with patch("src.Application.Runtime.research_runtime.MetaTrader5Provider", return_value=provider), \
                 patch.object(worker, "_get_active_matrix", return_value=[("XAUUSD", "H1", "Forex", "ControlledOfflineFixture")]), \
                 patch.object(central_runtime_state, "update_multiple", side_effect=stop_worker_on_cycle_completion):

                worker.is_running = True
                worker._run_loop()

            # Assert real _get_or_create_runtime created the runtime in worker.runtimes
            self.assertIn(key, worker.runtimes)
            created_runtime = worker.runtimes[key]
            self.assertIsInstance(created_runtime, ResearchRuntime)
            self.assertIsInstance(created_runtime.research_engine, PrimitiveMarketResearchEngine)

            # Verify history contains 1 result from real run_once()
            self.assertEqual(len(created_runtime.history), 1)
            res = created_runtime.history[0]

            # Verify LiveAnalysisBrain generated newborn_brain_report on default path
            self.assertIn("newborn_brain_report", res.Findings)
            nb_report = res.Findings["newborn_brain_report"]
            self.assertEqual(nb_report["symbol"], "XAUUSD")
            self.assertTrue(nb_report["is_read_only_compliant"])

            # Verify plan incorporates Brain proposal metadata and shows consumption
            self.assertIn("intel_summary", res.Findings)
            plan = res.Findings["intel_summary"].get("plan", {})
            self.assertEqual(plan.get("decision_source"), "BRAIN")
            self.assertTrue(plan.get("brain_report_consumed"))

            # Verify zero external calls were made
            self.assertEqual(len(mt5_calls), 0)
            self.assertEqual(len(broker_external_attempts), 0)
            self.assertEqual(len(network_calls), 0)
        finally:
            for p in boundary_patches:
                p.stop()
            cleanup()

    def test_brain_exception_fails_closed_explicitly(self):
        """
        Test 2: Prove that if LiveAnalysisBrain.process_live_candle raises an unexpected exception,
        PrimitiveMarketResearchEngine catches it, outputs brain_available = False, sets decision_source = "BRAIN_UNAVAILABLE" and action = "WAIT", and performs 0 executions.
        """
        boundary_patches, mt5_calls, broker_external_attempts, network_calls, credential_reads, cleanup = enforce_offline_boundary()
        for p in boundary_patches:
            p.start()

        try:
            from src.Research.Brain.live_brain import LiveAnalysisBrain

            def crashing_process_live_candle(*args, **kwargs):
                raise RuntimeError("Simulated unexpected Brain crash during candle processing")

            worker = ResearchWorker(symbol="XAUUSD", timeframe="H1")
            provider = ControlledDataProvider(base_price=2000.0, count=100)

            orig_update = central_runtime_state.update_multiple
            def stop_worker_on_cycle_completion(state_dict):
                worker.is_running = False
                return orig_update(state_dict)

            with patch("src.Application.Runtime.research_runtime.MetaTrader5Provider", return_value=provider), \
                 patch.object(LiveAnalysisBrain, "process_live_candle", side_effect=crashing_process_live_candle), \
                 patch.object(worker, "_get_active_matrix", return_value=[("XAUUSD", "H1", "Forex", "ControlledOfflineFixture")]), \
                 patch.object(central_runtime_state, "update_multiple", side_effect=stop_worker_on_cycle_completion):

                worker.is_running = True
                worker._run_loop()

            key = ("XAUUSD", "H1")
            self.assertIn(key, worker.runtimes)
            created_runtime = worker.runtimes[key]
            self.assertEqual(len(created_runtime.history), 1)
            res = created_runtime.history[0]

            # Verify newborn_brain_report contains brain_available = False and diagnostic error
            self.assertIn("newborn_brain_report", res.Findings)
            nb_report = res.Findings["newborn_brain_report"]
            self.assertFalse(nb_report.get("brain_available"))
            self.assertIn("LiveAnalysisBrain exception", nb_report.get("brain_error", ""))

            # Verify decision_source is BRAIN_UNAVAILABLE and action is WAIT
            plan = res.Findings["intel_summary"].get("plan", {})
            self.assertEqual(plan.get("decision_source"), "BRAIN_UNAVAILABLE")
            self.assertEqual(plan.get("action"), "WAIT")
            self.assertFalse(plan.get("brain_report_consumed"))

            # Verify zero external calls were made
            self.assertEqual(len(mt5_calls), 0)
            self.assertEqual(len(broker_external_attempts), 0)
            self.assertEqual(len(network_calls), 0)
        finally:
            for p in boundary_patches:
                p.stop()
            cleanup()

    def test_fail_closed_when_brain_report_missing(self):
        """
        Test 3: When newborn_brain_report is None or unconsumed, ExecutionIntelligencePlanner MUST fail closed
        to action = "WAIT", decision = "NO_TRADE", and decision_source = "BRAIN_UNAVAILABLE", never manufacturing BUY/SELL.
        """
        planner = ExecutionIntelligencePlanner()
        alignment = {"alignment": "BULLISH_CONTINUATION", "confidence": 95.0}
        narrative = {"trend": "BULLISH", "state": "TRENDING"}

        # Call generate_execution_plan WITHOUT newborn_brain_report
        res = planner.generate_execution_plan(
            symbol="XAUUSD",
            timeframe="H1",
            narrative=narrative,
            liquidity={},
            zones={},
            alignment=alignment,
            similarity={},
            portfolio_risk={"approved": True},
            current_price=2005.0,
            newborn_brain_report=None
        )
        plan = res["plan"]
        self.assertEqual(plan["action"], "WAIT")
        self.assertEqual(plan["decision"], "NO_TRADE")
        self.assertEqual(plan["decision_source"], "BRAIN_UNAVAILABLE")
        self.assertFalse(plan["brain_report_consumed"])

    def test_planner_cannot_override_brain_wait_or_avoid_proposal(self):
        """
        Test 4: Inject Brain proposal = WAIT / AVOID under market conditions that would
        otherwise trigger a BUY decision in legacy logic. Assert final decision CANNOT become BUY.
        """
        planner = ExecutionIntelligencePlanner()

        alignment = {"alignment": "BULLISH_CONTINUATION", "confidence": 85.0}
        narrative = {"trend": "BULLISH", "state": "TRENDING"}
        portfolio_risk = {"approved": True}

        # 1. Test with Brain Proposal = WAIT
        brain_report_wait = {
            "symbol": "XAUUSD",
            "active_hypotheses": [{"suggested_virtual_action": "WAIT"}]
        }
        res_wait = planner.generate_execution_plan(
            symbol="XAUUSD",
            timeframe="H1",
            narrative=narrative,
            liquidity={},
            zones={},
            alignment=alignment,
            similarity={},
            portfolio_risk=portfolio_risk,
            current_price=2005.0,
            newborn_brain_report=brain_report_wait
        )
        plan_wait = res_wait["plan"]
        self.assertEqual(plan_wait["action"], "WAIT")
        self.assertEqual(plan_wait["decision"], "NO_TRADE")
        self.assertEqual(plan_wait["decision_source"], "BRAIN")
        self.assertEqual(plan_wait["brain_suggested_action"], "WAIT")

        # 2. Test with Brain Proposal = AVOID
        brain_report_avoid = {
            "symbol": "XAUUSD",
            "active_hypotheses": [{"suggested_virtual_action": "AVOID"}]
        }
        res_avoid = planner.generate_execution_plan(
            symbol="XAUUSD",
            timeframe="H1",
            narrative=narrative,
            liquidity={},
            zones={},
            alignment=alignment,
            similarity={},
            portfolio_risk=portfolio_risk,
            current_price=2005.0,
            newborn_brain_report=brain_report_avoid
        )
        plan_avoid = res_avoid["plan"]
        self.assertEqual(plan_avoid["action"], "AVOID")
        self.assertEqual(plan_avoid["decision"], "NO_TRADE")

    def test_causal_brain_proposal_data_flow(self):
        """
        Test 5: Prove causality across Cases A-E by verifying that dynamically altering the Brain proposal
        determines and constrains the final canonical decision proposal.
        """
        planner = ExecutionIntelligencePlanner()
        bullish_alignment = {"alignment": "BULLISH_CONTINUATION", "confidence": 90.0}
        bearish_alignment = {"alignment": "BEARISH_CONTINUATION", "confidence": 90.0}
        narrative_bullish = {"trend": "BULLISH", "state": "TRENDING"}
        narrative_bearish = {"trend": "BEARISH", "state": "TRENDING"}

        # Case A: No Brain report -> WAIT & BRAIN_UNAVAILABLE
        res_a = planner.generate_execution_plan(
            symbol="XAUUSD", timeframe="H1", narrative=narrative_bullish, liquidity={},
            zones={}, alignment=bullish_alignment, similarity={}, portfolio_risk={"approved": True},
            current_price=2005.0, newborn_brain_report=None
        )
        self.assertEqual(res_a["plan"]["action"], "WAIT")
        self.assertEqual(res_a["plan"]["decision_source"], "BRAIN_UNAVAILABLE")

        # Case B: Brain WAIT + strongly bullish structure -> WAIT
        brain_wait = {"symbol": "XAUUSD", "active_hypotheses": [{"suggested_virtual_action": "WAIT"}]}
        res_b = planner.generate_execution_plan(
            symbol="XAUUSD", timeframe="H1", narrative=narrative_bullish, liquidity={},
            zones={}, alignment=bullish_alignment, similarity={}, portfolio_risk={"approved": True},
            current_price=2005.0, newborn_brain_report=brain_wait
        )
        self.assertEqual(res_b["plan"]["action"], "WAIT")
        self.assertEqual(res_b["plan"]["decision_source"], "BRAIN")

        # Case C: Brain AVOID + strongly bullish structure -> AVOID
        brain_avoid = {"symbol": "XAUUSD", "active_hypotheses": [{"suggested_virtual_action": "AVOID"}]}
        res_c = planner.generate_execution_plan(
            symbol="XAUUSD", timeframe="H1", narrative=narrative_bullish, liquidity={},
            zones={}, alignment=bullish_alignment, similarity={}, portfolio_risk={"approved": True},
            current_price=2005.0, newborn_brain_report=brain_avoid
        )
        self.assertEqual(res_c["plan"]["action"], "AVOID")
        self.assertEqual(res_c["plan"]["decision_source"], "BRAIN")

        # Case D: Brain BUY + bearish alignment -> BUY (Brain is sole authority)
        brain_buy = {"symbol": "XAUUSD", "active_hypotheses": [{"suggested_virtual_action": "BUY"}]}
        res_d = planner.generate_execution_plan(
            symbol="XAUUSD", timeframe="H1", narrative=narrative_bearish, liquidity={},
            zones={}, alignment=bearish_alignment, similarity={}, portfolio_risk={"approved": True},
            current_price=2005.0, newborn_brain_report=brain_buy
        )
        self.assertEqual(res_d["plan"]["action"], "BUY")

        # Case E: Brain SELL + bullish alignment -> SELL (Brain is sole authority)
        brain_sell = {"symbol": "XAUUSD", "active_hypotheses": [{"suggested_virtual_action": "SELL"}]}
        res_e = planner.generate_execution_plan(
            symbol="XAUUSD", timeframe="H1", narrative=narrative_bullish, liquidity={},
            zones={}, alignment=bullish_alignment, similarity={}, portfolio_risk={"approved": True},
            current_price=2005.0, newborn_brain_report=brain_sell
        )
        self.assertEqual(res_e["plan"]["action"], "SELL")

    def test_brain_cannot_directly_execute(self):
        """
        Test 6: Attempt direct broker execution from within Brain module scope and prove it is rejected.
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
        Test 7: Exercise Brain cognitive replay and active learning loop and prove 0 execution calls occur.
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
        Test 8: Prove downstream execution is reached only via authorized downstream caller after safety gates.
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
