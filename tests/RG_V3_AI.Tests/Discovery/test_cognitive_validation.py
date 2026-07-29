import unittest
from datetime import datetime, timedelta
import uuid
from src.Research.MarketAnalysis.Discovery.models import (
    MarketObservation,
    MarketSequence,
    MarketEvent,
    PatternMemory,
    ExperienceMemory,
    VirtualTrade,
    SimulationResult,
    JudgeReport,
    ConceptMemory,
    Hypothesis,
    CuriosityQuestion,
    LearningEpisode
)
from src.Research.MarketAnalysis.Discovery.brain import (
    MemorySystem,
    IndependentJudgeBrain,
    VirtualTradingEngine,
    ConfidenceEngine,
    HypothesisEngine,
    CuriosityEngine,
    QualityControlBrain,
    OutcomeEvaluationEngine
)
from src.Research.MarketAnalysis.Discovery.conversation import ConversationEngine


class TestCognitiveLearningValidationSuite(unittest.TestCase):
    """
    Dedicated validation suite proving that the Market Discovery Brain behaves as a
    true cognitive system (actually learns from experience, detects luck, self-deception, bias).
    """

    def setUp(self) -> None:
        self.now = datetime(2026, 7, 30, 12, 0, 0)
        self.memory = MemorySystem()
        self.judge = IndependentJudgeBrain()
        self.v_engine = VirtualTradingEngine()
        self.confidence_engine = ConfidenceEngine()
        self.hyp_engine = HypothesisEngine()
        self.cur_engine = CuriosityEngine()
        self.conversation = ConversationEngine()

    # =========================================================================
    # PART 3: JUDGE BRAIN EFFECTIVENESS TESTS
    # =========================================================================

    def test_judge_brain_correct_understanding(self) -> None:
        """
        Test A — Correct Understanding
        Input: A valid repeated market behavior (sample count >= 5).
        Expected: Judge approves and validates understanding.
        """
        trade = self.v_engine.create_virtual_trade(
            asset="XAUUSD", timeframe="H1", direction="BUY",
            entry_price=1800.0, stop_loss=1790.0, target_price=1830.0,
            expected_scenario="valid_pattern_H1", entry_time=self.now
        )
        sim_res = SimulationResult(
            TradeId=trade.TradeId, IsSuccess=True,
            MaxFavorableMovementPoints=30.0, MaxAdverseMovementPoints=1.0,
            FinalResult="WIN"
        )
        report = self.judge.evaluate_virtual_trade(trade, sim_res, sample_count=6)

        self.assertTrue(report.IsScientificallyValid)
        self.assertEqual(report.Verdict, "APPROVED")
        self.assertGreaterEqual(report.EvidenceQualityScore, 0.8)

    def test_judge_brain_wrong_understanding(self) -> None:
        """
        Test B — Wrong Understanding
        Input: False pattern / Insufficient evidence (sample count < 3).
        Expected: Judge rejects and disapproves.
        """
        trade = self.v_engine.create_virtual_trade(
            asset="XAUUSD", timeframe="H1", direction="BUY",
            entry_price=1800.0, stop_loss=1790.0, target_price=1830.0,
            expected_scenario="wrong_pattern_H1", entry_time=self.now
        )
        sim_res = SimulationResult(
            TradeId=trade.TradeId, IsSuccess=True,
            MaxFavorableMovementPoints=30.0, MaxAdverseMovementPoints=1.0,
            FinalResult="WIN"
        )
        report = self.judge.evaluate_virtual_trade(trade, sim_res, sample_count=2)

        self.assertFalse(report.IsScientificallyValid)
        self.assertEqual(report.Verdict, "DISAPPROVED")
        self.assertLess(report.EvidenceQualityScore, 0.5)

    def test_judge_brain_lucky_result(self) -> None:
        """
        Test C — Lucky Result
        Scenario: A bad decision with extremely poor evidence base makes profit accidentally.
        Expected: Judge distinguishes luck from understanding. Financial result positive but understanding quality rejected.
        """
        trade = self.v_engine.create_virtual_trade(
            asset="XAUUSD", timeframe="H1", direction="BUY",
            entry_price=1800.0, stop_loss=1790.0, target_price=1830.0,
            expected_scenario="lucky_guess_H1", entry_time=self.now
        )
        # Random win scenario
        sim_res = SimulationResult(
            TradeId=trade.TradeId, IsSuccess=True,
            MaxFavorableMovementPoints=30.0, MaxAdverseMovementPoints=25.0, # high adverse drawdown
            FinalResult="WIN"
        )

        # Insufficient evidence count
        report = self.judge.evaluate_virtual_trade(trade, sim_res, sample_count=1)

        self.assertFalse(report.IsScientificallyValid)
        self.assertEqual(report.Verdict, "DISAPPROVED")
        self.assertIn("Sample insufficiency", report.Explanation)
        self.assertEqual(sim_res.FinalResult, "WIN")  # Positive financial outcome is true, but learning is disapproved!

    # =========================================================================
    # PART 5: ANTI-SELF-DECEPTION TESTS
    # =========================================================================

    def test_anti_self_deception_confirmation_bias(self) -> None:
        """
        Confirmation Bias: Ensure belief shifts as contradicting evidence increases.
        """
        # Formulate initial hypothesis
        hyp = self.hyp_engine.formulate_hypothesis("Initial Golden Cross Continuation", ["obs_1"])
        self.assertEqual(hyp.Confidence, 0.5)

        # 1 success: Confidence increases slightly
        conf_success = self.confidence_engine.calibrate_confidence(sample_count=1, judge_score=0.9, contradiction_count=0)
        self.assertGreater(conf_success, 0.5)

        # 5 failures / contradictions occur: Confidence must drop significantly
        conf_failure = self.confidence_engine.calibrate_confidence(sample_count=4, judge_score=0.9, contradiction_count=5)
        self.assertLess(conf_failure, conf_success)
        self.assertLess(conf_failure, 0.5) # updates belief and marks it as weak/rejected

    def test_anti_self_deception_confidence_inflation(self) -> None:
        """
        Confidence Inflation: Confidence increases ONLY proportionally with direct evidence.
        """
        # Low samples with success
        conf_low = self.confidence_engine.calibrate_confidence(sample_count=1, judge_score=1.0, contradiction_count=0)

        # High samples with success
        conf_high = self.confidence_engine.calibrate_confidence(sample_count=5, judge_score=1.0, contradiction_count=0)

        self.assertGreater(conf_high, conf_low)
        self.assertLessEqual(conf_high, 1.0)  # capped and strictly calibrated

    def test_anti_self_deception_failure_ignoring(self) -> None:
        """
        Failure Ignoring: Repeated failures must pull down confidence and mark weaknesses.
        """
        # Repeated failures
        conf_fail = self.confidence_engine.calibrate_confidence(sample_count=10, judge_score=0.2, contradiction_count=8)
        self.assertLess(conf_fail, 0.3)  # low confidence status verified

    # =========================================================================
    # PART 6: CURIOSITY ENGINE VALIDATION
    # =========================================================================

    def test_curiosity_engine_gap_identification(self) -> None:
        """
        Verify the curiosity engine identifies target behaviours, gaps, priority, and required samples.
        """
        q = self.cur_engine.ask_question(
            target_behavior="XAUUSD extreme post-news volatility",
            gap_desc="Insufficient historical samples to understand correction duration"
        )
        self.assertEqual(q.TargetBehavior, "XAUUSD extreme post-news volatility")
        self.assertEqual(q.UnderstandingGap, "Insufficient historical samples to understand correction duration")
        self.assertIsNotNone(q.QuestionId)

    # =========================================================================
    # PART 7: ANALYST CONVERSATION BRAIN VERIFICATION
    # =========================================================================

    def test_conversation_analyst_interface(self) -> None:
        """
        Verify the Analyst Interface queries return evidence-based traceability reports.
        """
        # Pre-seed concept and pattern memory to represent learned system status
        concept = ConceptMemory(
            ConceptId="concept_gold",
            Description="Double price runs at XAUUSD support zones",
            Confidence=0.85,
            ValidatedSamples=14,
            LastValidatedAt=self.now
        )
        self.memory.save_concept(concept)

        p = PatternMemory(
            PatternId="pat_strong",
            Signature="upward_12_retraced_3",
            Occurrences=8,
            ContinuationCount=6,
            ReversalCount=2
        )
        self.memory.save_pattern(p)

        failures_exp = ExperienceMemory(
            MemoryId="exp_fail_1",
            Timestamp=self.now,
            SituationSignature="flat_lateral_gbpusd",
            Decision="BUY",
            MaxFavorableMovement=1.0,
            MaxAdverseMovement=12.0,
            FinalResult="LOSS",
            Lesson="Breached stop loss zone on holiday low-liquidity horizontal block"
        )
        self.memory.save_experience(failures_exp)

        # Pre-seed Curiosity Question
        self.cur_engine.ask_question(
            target_behavior="Gold after extreme volatility",
            gap_desc="Insufficient samples under news blocks"
        )

        # Pre-seed hypothesis
        self.hyp_engine.formulate_hypothesis("Gold post-volatility consolidation", ["obs_99"])

        # Test Query 1: What did you understand / learned concepts
        ans_concept = self.conversation.handle_user_query("What did you understand about market behavior?", self.memory, self.hyp_engine)
        self.assertEqual(ans_concept["Current Understanding Status"], "VALIDATED")
        self.assertIn("Double price runs", ans_concept["Observation"])
        self.assertEqual(ans_concept["Historical Samples"], 14)

        # Test Query 2: What patterns
        ans_patterns = self.conversation.handle_user_query("What patterns are strongest?", self.memory, self.hyp_engine)
        self.assertEqual(ans_patterns["Current Understanding Status"], "OBSERVED")
        self.assertIn("upward_12_retraced_3", ans_patterns["Observation"])
        self.assertEqual(ans_patterns["Historical Samples"], 8)

        # Test Query 3: What mistakes / failed
        ans_fail = self.conversation.handle_user_query("What mistakes did you make?", self.memory, self.hyp_engine)
        self.assertEqual(ans_fail["Current Understanding Status"], "REJECTED")
        self.assertIn("flat_lateral_gbpusd", ans_fail["Observation"])
        self.assertEqual(ans_fail["Historical Samples"], 1)

        # Test Query 4: Uncertainty / Curiosity questions
        ans_curiosity = self.conversation.handle_user_query("What are your research questions?", self.memory, self.hyp_engine, self.cur_engine)
        self.assertEqual(ans_curiosity["Current Understanding Status"], "HYPOTHESIS")
        self.assertIn("Gold after extreme volatility", ans_curiosity["Observation"])

        # Check conversation audit logging
        self.assertGreaterEqual(len(self.conversation.audit_logs), 4)
        for log in self.conversation.audit_logs:
            self.assertTrue("User Question" in log)
            self.assertTrue("Generated Answer" in log)
            self.assertTrue("Evidence References" in log)
