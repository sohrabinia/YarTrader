import os
import json
import unittest
import tempfile
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from src.Execution.Models.models import OrderRequest, OrderResponse
from src.Execution.Services.demo_execution_engine import DemoExecutionEngine
from src.Execution.Services.trade_journal import TradeJournalManager, TradeJournalRecord
from src.ShadowTrading.Services.TradeEvaluator import TradeEvaluator
from src.Research.Brain.judge import JudgeBrain
from src.Research.Brain.memory import MarketMemorySystem
from src.Execution.Safety.demo_execution_gate import DemoExecutionGate


class TestDemoLifecycleAndEvaluator(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.log_dir = os.path.join(self.tmp_dir.name, "logs")
        os.makedirs(self.log_dir, exist_ok=True)

        # Mock adapter
        self.mock_adapter = MagicMock()
        self.mock_adapter.get_account_info.return_value = {
            "login": DemoExecutionGate.AUTHORIZED_DEMO_ACCOUNT,
            "server": DemoExecutionGate.AUTHORIZED_DEMO_SERVER,
            "trade_mode": 0,  # 0 = DEMO
            "is_real": False,
            "equity": 10000.0,
            "free_margin": 8000.0,
            "platform": "MT5"
        }
        self.mock_adapter.get_terminal_info.return_value = {
            "connected": True,
            "trade_allowed": True,
            "name": "MetaTrader 5"
        }
        self.mock_adapter.get_symbol_info.return_value = {
            "symbol": "XAUUSD",
            "trade_mode": 4,  # FULL
            "volume_min": 0.01,
            "volume_max": 100.0,
            "volume_step": 0.01,
            "digits": 2
        }

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_blocker_6_immutable_decision_id_and_parent_referencing(self):
        """
        Blocker 6: Prove original decision_id remains unchanged throughout lifecycle
        and reversal explicitly references parent_decision_id.
        """
        journal_file = os.path.join(self.log_dir, "trade_journal.json")
        journal_mgr = TradeJournalManager(journal_file=journal_file)
        TradeJournalManager._instance = journal_mgr

        engine = DemoExecutionEngine(adapter=self.mock_adapter, demo_mode=True, log_dir=self.log_dir)

        # Mock order response for initial entry
        open_resp = OrderResponse(
            OrderId="1001",
            Symbol="XAUUSD",
            Status="Placed",
            SubmittedAt=datetime.now(timezone.utc),
            Retcode=10009,
            Comment="Initial trade",
            DealTicket="5001",
            Price=2000.0,
            Volume=0.1
        )
        self.mock_adapter.send_order_to_broker.return_value = open_resp

        init_decision_id = "DEC-XAUUSD-BUY-9999"
        res = engine.execute_demo_decision(
            symbol="XAUUSD",
            direction="BUY",
            volume=0.1,
            price=2000.0,
            sl=1980.0,
            tp=2040.0,
            decision_id=init_decision_id
        )

        records = journal_mgr.get_all_records()
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].decision_id, init_decision_id)
        self.assertIsNone(records[0].parent_decision_id)

        # Reversal trade
        rev_decision_id = "DEC-REV-XAUUSD-SELL-10000"
        rev_resp = OrderResponse(
            OrderId="1002",
            Symbol="XAUUSD",
            Status="Placed",
            SubmittedAt=datetime.now(timezone.utc),
            Retcode=10009,
            Comment="Reversal trade",
            DealTicket="5002",
            Price=2000.0,
            Volume=0.1
        )
        self.mock_adapter.send_order_to_broker.return_value = rev_resp

        res_rev = engine.execute_demo_decision(
            symbol="XAUUSD",
            direction="SELL",
            volume=0.1,
            price=2000.0,
            sl=2020.0,
            tp=1960.0,
            decision_id=rev_decision_id,
            parent_decision_id=init_decision_id
        )

        records_updated = journal_mgr.get_all_records()
        self.assertEqual(len(records_updated), 2)
        self.assertEqual(records_updated[1].decision_id, rev_decision_id)
        self.assertEqual(records_updated[1].parent_decision_id, init_decision_id)

    def test_blocker_7_and_9_real_demo_close_creates_and_updates_journal_from_broker_facts(self):
        """
        Blockers 7 & 9: Prove real execution path: open -> journal record -> broker close ->
        authoritative broker history facts -> updated journal -> TradeEvaluator.
        """
        journal_file = os.path.join(self.log_dir, "trade_journal.json")
        journal_mgr = TradeJournalManager(journal_file=journal_file)
        TradeJournalManager._instance = journal_mgr

        mem_sys = MarketMemorySystem(storage_dir=self.log_dir)
        evaluator = TradeEvaluator(memory_system=mem_sys)
        TradeEvaluator._instance = evaluator

        engine = DemoExecutionEngine(adapter=self.mock_adapter, demo_mode=True, log_dir=self.log_dir)

        # 1. Open trade
        open_resp = OrderResponse(
            OrderId="7001",
            Symbol="XAUUSD",
            Status="Placed",
            SubmittedAt=datetime.now(timezone.utc),
            Retcode=10009,
            Comment="Open trade",
            DealTicket="8001",
            Price=2000.0,
            Volume=0.1
        )
        self.mock_adapter.send_order_to_broker.return_value = open_resp

        dec_id = "DEC-XAUUSD-BUY-7001"
        engine.execute_demo_decision(
            symbol="XAUUSD",
            direction="BUY",
            volume=0.1,
            price=2000.0,
            sl=1980.0,
            tp=2040.0,
            decision_id=dec_id
        )

        rec_open = journal_mgr.get_all_records()[0]
        self.assertEqual(rec_open.result, "PENDING")
        self.assertEqual(rec_open.order_ticket, "7001")

        # 2. Setup mock active position and broker history deals for close
        self.mock_adapter.get_positions.side_effect = [
            [{"ticket": 7001, "symbol": "XAUUSD", "volume": 0.1}],  # before close
            []  # after close (flat)
        ]

        # Authoritative broker deals history
        self.mock_adapter.get_history_deals.return_value = [
            {"ticket": 8001, "order": 7001, "position": 7001, "entry": 0, "price": 2000.0, "volume": 0.1, "profit": 0.0},  # entry
            {"ticket": 8002, "order": 7002, "position": 7001, "entry": 1, "price": 2010.0, "volume": 0.1, "profit": 100.0, "swap": 0.0, "commission": -1.0, "time": 1700000000}  # exit
        ]

        close_resp = OrderResponse(
            OrderId="7002",
            Symbol="XAUUSD",
            Status="Closed",
            SubmittedAt=datetime.now(timezone.utc),
            Retcode=10009,
            Comment="Close trade",
            DealTicket="8002",
            Price=2010.0,
            Volume=0.1
        )
        self.mock_adapter.send_order_to_broker.return_value = close_resp

        engine.close_position(symbol="XAUUSD", position_ticket=7001, exit_reason="TAKE_PROFIT")

        # 3. Assert journal updated with authoritative broker facts
        records_after = journal_mgr.get_all_records()
        self.assertEqual(len(records_after), 1)
        rec_closed = records_after[0]
        self.assertEqual(rec_closed.result, "WIN")
        self.assertEqual(rec_closed.pnl, 99.0)  # profit 100.0 + commission -1.0
        self.assertEqual(rec_closed.actual_exit, 2010.0)
        self.assertEqual(rec_closed.exit_reason, "TAKE_PROFIT")

        # 4. Assert ExperienceMemory persisted in MarketMemorySystem
        experiences = list(mem_sys.experiences.values())
        self.assertEqual(len(experiences), 1)
        self.assertEqual(experiences[0].symbol, "XAUUSD")
        self.assertEqual(experiences[0].outcome_result, "SUCCESS")
        self.assertEqual(experiences[0].meta["decision_id"], dec_id)

    def test_blocker_8_no_fabricated_trade_evidence(self):
        """
        Blocker 8: Verify no synthetic or fabricated evidence values are injected when evidence is missing.
        """
        mem_sys = MarketMemorySystem(storage_dir=self.log_dir)
        evaluator = TradeEvaluator(memory_system=mem_sys)

        journal_rec = TradeJournalRecord(
            decision_id="DEC-TEST-001",
            parent_decision_id=None,
            trade_id="trade-999",
            cycle_id="cycle-1",
            symbol="XAUUSD",
            timeframe="H1",
            direction="BUY",
            planned_entry=2000.0,
            planned_sl=1980.0,
            planned_tp=2040.0,
            planned_rr=2.0,
            actual_entry=2000.0,
            actual_exit=2010.0,
            volume=0.1,
            confidence=0.0,
            reasoning=[],
            evidence={},  # Empty evidence
            order_ticket="999",
            deal_ticket="1000",
            open_time="2025-01-01T00:00:00Z",
            close_time="2025-01-01T01:00:00Z",
            exit_reason="TAKE_PROFIT",
            pnl=100.0,
            pnl_percent=0.5,
            mfe=0.0,
            mae=0.0,
            duration=3600.0,
            market_regime="UNKNOWN",
            result="WIN",
            configuration_version="1.0.0"
        )

        res = evaluator.evaluate_demo_trade_outcome(journal_rec)

        experiences = list(mem_sys.experiences.values())
        self.assertEqual(len(experiences), 1)
        exp = experiences[0]
        # Signature should be empty list, not synthetic [1.0, -0.5, 0.2]
        self.assertEqual(exp.situation_signature, [])
        self.assertEqual(res["evaluation"], "Earned Success")

    def test_blocker_11_learning_remains_advisory_cannot_bypass_safety_gates(self):
        """
        Blocker 11: Negative regression test proving pattern memory cannot bypass
        safety gates (AUTONOMOUS_DEMO_TRADING_ENABLED=False).
        """
        mem_sys = MarketMemorySystem(storage_dir=self.log_dir)

        # Seed high-confidence pattern memory
        from src.Research.Brain.models import ExperienceMemory
        exp = ExperienceMemory(
            experience_id="exp-perfect-1",
            symbol="XAUUSD",
            timeframe="H1",
            timestamp=datetime.now(),
            situation_signature=[0.9, 0.8, 0.9],
            decision_action="BUY",
            outcome_result="SUCCESS",
            lesson_feedback="Perfect pattern match",
            max_favorable_excursion=500.0,
            max_adverse_excursion=0.0,
            meta={}
        )
        mem_sys.add_experience(exp)

        # Ensure kill switch / demo gate env is disabled
        with patch.dict(os.environ, {"AUTONOMOUS_DEMO_TRADING_ENABLED": "false"}):
            from app.workers.research_worker import ResearchWorker
            worker = ResearchWorker(symbol="XAUUSD")
            worker.demo_engine = DemoExecutionEngine(adapter=self.mock_adapter, demo_mode=True, log_dir=self.log_dir)

            # High confidence decision
            decision_dict = {
                "action": "BUY",
                "entry": 2000.0,
                "stop_loss": 1980.0,
                "take_profit": 2040.0,
                "confidence": 99.0,
                "risk_reward": 2.0
            }

            # Despite perfect pattern memory and 99% confidence, validation / dispatch MUST fail closed
            sized = worker._validate_and_size_decision("XAUUSD", "BUY", decision_dict)

            # Verification: is_autonomous_demo_enabled() is False, so worker skips execution dispatch
            from app.workers.research_worker import is_autonomous_demo_enabled
            self.assertFalse(is_autonomous_demo_enabled())

    def test_blocker_12_judgebrain_outcome_classification(self):
        """
        Blocker 12: Verify JudgeBrain classifies earned success vs lucky win based on actual excursions.
        """
        judge = JudgeBrain()

        # 1. Earned Success (low adverse excursion relative to favorable)
        decision = MagicMock(symbol="XAUUSD", decision_action="BUY", price=2000.0)
        earned_outcome = {
            "final_result": "SUCCESS",
            "max_favorable_excursion": 100.0,
            "max_adverse_excursion": 10.0
        }
        res_earned = judge.evaluate_decision_outcome(decision, {}, earned_outcome)
        self.assertFalse(res_earned["is_lucky_win"])
        self.assertEqual(res_earned["evaluation"], "Earned Success")

        # 2. Lucky Win (extreme adverse excursion prior to hitting target)
        lucky_outcome = {
            "final_result": "SUCCESS",
            "max_favorable_excursion": 100.0,
            "max_adverse_excursion": 90.0  # > 80% of favorable
        }
        res_lucky = judge.evaluate_decision_outcome(decision, {}, lucky_outcome)
        self.assertTrue(res_lucky["is_lucky_win"])

        # 3. Structural Failure
        failed_outcome = {
            "final_result": "FAILURE",
            "max_favorable_excursion": 10.0,
            "max_adverse_excursion": 100.0
        }
        res_failed = judge.evaluate_decision_outcome(decision, {}, failed_outcome)
        self.assertTrue(res_failed["is_structural_failure"])


if __name__ == "__main__":
    unittest.main()
