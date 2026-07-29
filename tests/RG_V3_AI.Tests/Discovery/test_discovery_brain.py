import unittest
from datetime import datetime, timedelta
from src.Data.MarketData.Models.models import MarketDataPoint
from src.Research.MarketAnalysis.Discovery.models import (
    MarketObservation,
    MarketSequence,
    MarketEvent,
    PatternMemory,
    ExperienceMemory,
    VirtualTrade,
    SimulationResult,
    LearningRecord,
    AnalysisReport,
    DynamicTimeScale,
    MultiScaleRelationship,
    AIView,
    HumanView,
    ConceptMemory,
    Hypothesis,
    JudgeReport,
    MemoryAssociation,
    CuriosityQuestion,
    LearningEpisode
)
from src.Research.MarketAnalysis.Discovery.brain import (
    DataRealityLayer,
    ObservationBrain,
    MultiTimeframePerceptionLayer,
    MemorySystem,
    PatternDiscoveryEngine,
    QualityControlBrain,
    SimulationBrain,
    VirtualTradingEngine,
    OutcomeEvaluationEngine,
    LearningMemoryUpdate,
    LiveAnalysisBrain,
    DynamicTimeStructureDiscoveryEngine,
    MultiScaleMarketPerception,
    MemoryAssociationEngine,
    CuriosityEngine,
    HypothesisEngine,
    ScientificTestingEngine,
    MarketUnderstandingModel,
    ConfidenceEngine,
    IndependentJudgeBrain,
    AntiSelfDeceptionLayer
)


class TestNewbornMarketDiscoveryBrain(unittest.TestCase):
    """
    Automated unit and integration test suite verifying the Newborn Market
    Discovery Brain architecture, memory system, simulation replay, and safety boundaries.
    """

    def setUp(self) -> None:
        self.now = datetime(2026, 7, 29, 10, 0, 0)
        self.asset = "XAUUSD"
        self.timeframe = "H1"

        # Construct dummy historical data sequence
        self.dummy_data = []
        for i in range(10):
            # i = 0 to 4: rising price, i = 5 to 9: falling price
            close_price = 1800.0 + (i * 10.0 if i < 5 else (80.0 - i * 10.0))
            dp = MarketDataPoint(
                AssetId=self.asset,
                Timestamp=self.now + timedelta(hours=i),
                Open=close_price - 5.0,
                High=close_price + 8.0,
                Low=close_price - 7.0,
                Close=close_price,
                Volume=250.0 + i * 50
            )
            self.dummy_data.append(dp)

    # 1. Data Ingestion & Reality Layer Tests
    def test_reality_layer_ingestion_and_gaps(self) -> None:
        layer = DataRealityLayer()
        observations = layer.receive_data(self.dummy_data, self.timeframe)

        self.assertEqual(len(observations), 10)
        self.assertTrue(layer.validate_timestamps(observations))

        # Test duplicate timestamp validation failure
        bad_data = list(self.dummy_data)
        bad_data[1] = MarketDataPoint(
            AssetId=self.asset,
            Timestamp=self.now,  # duplicate
            Open=1795.0, High=1805.0, Low=1790.0, Close=1800.0, Volume=100.0
        )
        bad_obs = layer.receive_data(bad_data, self.timeframe)
        self.assertFalse(layer.validate_timestamps(bad_obs))

        # Test gap/missing candles detection
        gap_data = [self.dummy_data[0], self.dummy_data[2]]  # missing hour 1
        gap_obs = layer.receive_data(gap_data, self.timeframe)
        gaps = layer.detect_missing_candles(gap_obs, expected_interval_minutes=60)
        self.assertEqual(len(gaps), 1)
        self.assertEqual(gaps[0], self.now + timedelta(hours=1))

    # 2. Observation Brain Event Extraction Tests
    def test_observation_brain_runs_and_retracements(self) -> None:
        layer = DataRealityLayer()
        brain = ObservationBrain()

        obs_list = layer.receive_data(self.dummy_data, self.timeframe)
        seq = MarketSequence(Asset=self.asset, Timeframe=self.timeframe, Observations=obs_list)

        events = brain.observe_sequence(seq)
        self.assertGreaterEqual(len(events), 1)

        # Confirm behavior is observed cleanly in Points/Duration/Reactions with zero indicator terms
        for ev in events:
            self.assertEqual(ev.Asset, self.asset)
            self.assertEqual(ev.Timeframe, self.timeframe)
            self.assertGreater(ev.DurationCandles, 0)
            self.assertIn(ev.Direction, ["upward", "downward", "neutral"])

    # 3. Multi-Timeframe Perception Tests
    def test_multi_timeframe_perception_fractals(self) -> None:
        layer = MultiTimeframePerceptionLayer()
        parent_event = MarketEvent(
            EventId="parent_h4", Asset=self.asset, Timeframe="H4",
            StartTime=self.now, EndTime=self.now + timedelta(hours=4),
            PriceMovementPoints=40.0, DurationCandles=1, ConsecutiveCandlesCount=1, Direction="upward"
        )

        # Child H1 sequence
        child_obs = [
            MarketObservation(self.asset, self.now, 1800.0, 1810.0, 1795.0, 1805.0, 100, "H1"),
            MarketObservation(self.asset, self.now + timedelta(hours=1), 1805.0, 1815.0, 1800.0, 1812.0, 100, "H1")
        ]
        child_seq = MarketSequence(Asset=self.asset, Timeframe="H1", Observations=child_obs)

        layer.associate_timeframes(parent_event, child_seq)
        retrieved = layer.get_child_sequences("parent_h4")
        self.assertEqual(len(retrieved), 1)
        self.assertEqual(retrieved[0].Timeframe, "H1")

    # 4. Memory System & Jaccard Similarity Search Tests
    def test_memory_system_similarity(self) -> None:
        memory = MemorySystem()

        p1 = PatternMemory(PatternId="pat1", Signature="upward_12_retraced_4", Occurrences=10, ContinuationCount=7, ReversalCount=3)
        p2 = PatternMemory(PatternId="pat2", Signature="downward_5_retraced_2", Occurrences=15, ContinuationCount=2, ReversalCount=13)

        memory.save_pattern(p1)
        memory.save_pattern(p2)

        # Exact match
        matches = memory.find_similar_patterns("upward_12_retraced_4")
        self.assertGreater(len(matches), 0)
        self.assertEqual(matches[0][0].PatternId, "pat1")
        self.assertEqual(matches[0][1], 1.0)

        # Partial match
        partial_matches = memory.find_similar_patterns("upward_8_retraced_4", threshold=0.3)
        self.assertGreater(len(partial_matches), 0)
        self.assertEqual(partial_matches[0][0].PatternId, "pat1")

    # 5. Pattern Discovery and Quality Control Reasoning Tests
    def test_pattern_discovery_and_qc(self) -> None:
        memory = MemorySystem()
        engine = PatternDiscoveryEngine()
        qc = QualityControlBrain()

        p = PatternMemory(PatternId="pat_gold", Signature="upward_12", Occurrences=20, ContinuationCount=15, ReversalCount=5)
        memory.save_pattern(p)

        discovery = engine.discover_similarities("upward_12", memory)
        self.assertEqual(discovery["total_occurrences"], 20)
        self.assertEqual(discovery["continuation_probability"], 0.75)

        # Evaluate reasoning under high occurrences
        score, explanation = qc.evaluate_reasoning(discovery["raw_matches"])
        self.assertGreaterEqual(score, 0.8)
        self.assertIn("Strong evidence base", explanation)

        # Evaluate reasoning under low occurrences
        weak_p = PatternMemory(PatternId="pat_weak", Signature="weak_run", Occurrences=2, ContinuationCount=1, ReversalCount=1)
        score_weak, explanation_weak = qc.evaluate_reasoning([(weak_p, 1.0)])
        self.assertLess(score_weak, 0.5)
        self.assertIn("Low sample warning", explanation_weak)

    # 6. Virtual Trading & Simulation Engine Tests
    def test_virtual_trading_and_replay_simulation(self) -> None:
        layer = DataRealityLayer()
        sim_brain = SimulationBrain()
        memory = MemorySystem()

        obs_list = layer.receive_data(self.dummy_data, self.timeframe)
        seq = MarketSequence(Asset=self.asset, Timeframe=self.timeframe, Observations=obs_list)

        # Simulating BUY direction with 5.0 pt stop loss and 30.0 pt target
        results = sim_brain.simulate_replay(seq, memory, direction="BUY", stop_loss_pts=5.0, target_pts=30.0)

        self.assertEqual(len(results), 1)
        res = results[0]
        self.assertTrue(isinstance(res, SimulationResult))
        self.assertGreaterEqual(res.MaxFavorableMovementPoints, 0.0)
        self.assertGreaterEqual(res.MaxAdverseMovementPoints, 0.0)

    # 7. Learning Update & Episodic Experience Logging Tests
    def test_learning_updates_and_episodes(self) -> None:
        memory = MemorySystem()
        engine = VirtualTradingEngine()
        learner = LearningMemoryUpdate()

        trade = engine.create_virtual_trade(
            asset=self.asset, timeframe=self.timeframe, direction="BUY",
            entry_price=1800.0, stop_loss=1795.0, target_price=1830.0,
            expected_scenario="upward_H1_test", entry_time=self.now
        )

        sim_res = SimulationResult(
            TradeId=trade.TradeId, IsSuccess=True,
            MaxFavorableMovementPoints=30.0, MaxAdverseMovementPoints=2.0,
            FinalResult="WIN"
        )

        record = learner.update_memory_with_outcome(trade, sim_res, memory)
        self.assertTrue(isinstance(record, LearningRecord))
        self.assertEqual(len(memory.experience_memory), 1)

        exp = memory.experience_memory[0]
        self.assertEqual(exp.Decision, "BUY")
        self.assertEqual(exp.FinalResult, "WIN")

    # 8. Live Analysis Brain & Strict Read-Only Safety Tests
    def test_live_analysis_and_read_only_safety(self) -> None:
        memory = MemorySystem()
        live_brain = LiveAnalysisBrain()

        # Build active pattern for match (expected signature will be "downward_6")
        p = PatternMemory(PatternId="pat_live", Signature="downward_6", Occurrences=10, ContinuationCount=8, ReversalCount=2)
        memory.save_pattern(p)

        report, ai_view, human_view, spread_data = live_brain.analyze_live_market(self.dummy_data, self.timeframe, memory)
        self.assertTrue(isinstance(report, AnalysisReport))
        self.assertEqual(report.Asset, self.asset)
        self.assertGreater(report.QCScore, 0.0)

        # Strict safety assertion: verify absolutely no orders or trade methods were invoked
        self.assertFalse(hasattr(live_brain, "order_send"))
        self.assertFalse(hasattr(live_brain, "trade_send"))

    # 9. Dynamic Time Scale Discovery Engine Tests
    def test_new_9_dynamic_time_scale_discovery(self) -> None:
        layer = DataRealityLayer()
        engine = DynamicTimeStructureDiscoveryEngine()

        observations = layer.receive_data(self.dummy_data, self.timeframe)

        # Test scale discovery with a threshold of 15.0 points
        scales = engine.discover_scales(observations, price_threshold=15.0)
        self.assertGreater(len(scales), 0)

        first_scale = scales[0]
        self.assertTrue(isinstance(first_scale, DynamicTimeScale))
        self.assertGreater(first_scale.DurationMinutes, 0.0)
        self.assertGreater(first_scale.TotalVolume, 0.0)
        self.assertNotEqual(first_scale.PriceChangePoints, 0.0)

    # 10. Multi-Scale Hypothesis Recurrence Tests
    def test_new_10_multi_scale_hypothesis_recurrence(self) -> None:
        perception = MultiScaleMarketPerception()

        parent = DynamicTimeScale("p_scale", 120.0, 5000.0, 20.0, 5)
        child_confirmed = DynamicTimeScale("c_scale_1", 30.0, 1000.0, 19.5, 4)
        child_insufficient = DynamicTimeScale("c_scale_2", 15.0, 400.0, 2.0, 2) # creation count < 3

        # Test CONFIRMED state
        rel1 = perception.test_scale_hypothesis(parent, child_confirmed)
        self.assertEqual(rel1.HypothesisState, "CONFIRMED")
        self.assertGreaterEqual(rel1.SimilarityScore, 0.8)

        # Test INSUFFICIENT_EVIDENCE state
        rel2 = perception.test_scale_hypothesis(parent, child_insufficient)
        self.assertEqual(rel2.HypothesisState, "INSUFFICIENT_EVIDENCE")

    # 11. Dual Human/AI Views Mapping Tests
    def test_new_11_dual_human_ai_views(self) -> None:
        layer = DataRealityLayer()
        brain = ObservationBrain()

        observations = layer.receive_data(self.dummy_data, self.timeframe)
        seq = MarketSequence(Asset=self.asset, Timeframe=self.timeframe, Observations=observations)
        events = brain.observe_sequence(seq)

        # AI-View checking (structural)
        ai_view = brain.generate_ai_view(seq, events)
        self.assertTrue(isinstance(ai_view, AIView))
        self.assertEqual(len(ai_view.PriceSequence), 10)
        self.assertGreater(len(ai_view.MovementStructure), 0)

        # Human-View checking (candles, timelines)
        human_view = brain.generate_human_view(seq)
        self.assertTrue(isinstance(human_view, HumanView))
        self.assertEqual(human_view.Symbol, self.asset)
        self.assertEqual(human_view.CandlesCount, 10)
        self.assertEqual(len(human_view.Timeline), 10)
        self.assertEqual(len(human_view.OhlcData), 10)

    # =========================================================================
    # COGNITIVE LEARNING SYSTEM PHASE 2 TESTS
    # =========================================================================

    # 12. Memory Association Engine Tests
    def test_cognitive_1_memory_association_engine(self) -> None:
        assoc_engine = MemoryAssociationEngine()
        obs1 = MarketObservation(self.asset, self.now, 1800.0, 1810.0, 1790.0, 1805.0, 100, self.timeframe)
        obs2 = MarketObservation(self.asset, self.now + timedelta(days=30), 1820.0, 1830.0, 1815.0, 1825.0, 150, self.timeframe)

        assoc = assoc_engine.associate_episodes(obs1, obs2, correlation_score=0.88)
        self.assertTrue(isinstance(assoc, MemoryAssociation))
        self.assertEqual(assoc.RegimeCorrelationScore, 0.88)
        self.assertEqual(len(assoc_engine.associations), 1)

    # 13. Curiosity Engine Question Formulation
    def test_cognitive_2_curiosity_engine(self) -> None:
        cur_engine = CuriosityEngine()
        q = cur_engine.ask_question(
            target_behavior="Gold multi-day downward runs",
            gap_desc="Why does point reaction expand on US market session opening?"
        )
        self.assertTrue(isinstance(q, CuriosityQuestion))
        self.assertEqual(q.TargetBehavior, "Gold multi-day downward runs")
        self.assertEqual(len(cur_engine.questions), 1)

    # 14. Hypothesis Lifecycle & Status Transition Checks
    def test_cognitive_3_hypothesis_lifecycle_and_testing(self) -> None:
        hyp_engine = HypothesisEngine()
        testing_engine = ScientificTestingEngine()

        hyp = hyp_engine.formulate_hypothesis(
            description="Consecutive downward runs under H1 repeat on H4",
            evidence_ids=["obs_1", "obs_2"],
            prior_confidence=0.5
        )
        self.assertEqual(hyp.Status, "PENDING")

        # Replay hypothesis against OOS data
        layer = DataRealityLayer()
        oos_obs = layer.receive_data(self.dummy_data, self.timeframe)
        oos_seq = MarketSequence(Asset=self.asset, Timeframe=self.timeframe, Observations=oos_obs)

        status, score = testing_engine.test_hypothesis(hyp, oos_seq)
        hyp_engine.transition_status(hyp.HypothesisId, status, score)

        updated_hyp = hyp_engine.hypotheses[hyp.HypothesisId]
        self.assertEqual(updated_hyp.Status, status)
        self.assertEqual(updated_hyp.Confidence, score)

    # 15. Market Understanding and Concept Memory Expansion
    def test_cognitive_4_market_understanding_concepts(self) -> None:
        memory = MemorySystem()
        model = MarketUnderstandingModel(memory)

        # Empty report state default
        report = model.get_understanding_report()
        self.assertTrue(report["unknown_state_active"])

        # Add validated concept
        concept = model.build_concept("Long-range point run correlation on gold metals", sample_count=124, confidence=0.78)
        self.assertTrue(isinstance(concept, ConceptMemory))
        self.assertEqual(concept.Confidence, 0.78)

        report_new = model.get_understanding_report()
        self.assertFalse(report_new["unknown_state_active"])
        self.assertEqual(report_new["verified_concepts_count"], 1)

    # 16. Evidence-Based Confidence Engine Calibration
    def test_cognitive_5_confidence_calibration(self) -> None:
        engine = ConfidenceEngine()

        # Default/Unknown state when zero samples
        score_unknown = engine.calibrate_confidence(sample_count=0, judge_score=1.0, contradiction_count=0)
        self.assertEqual(score_unknown, 0.5)

        # Confidence increases with more samples and judge approval
        score_strong = engine.calibrate_confidence(sample_count=5, judge_score=0.9, contradiction_count=0)

        # Confidence decreases on contradiction
        score_contradict = engine.calibrate_confidence(sample_count=5, judge_score=0.9, contradiction_count=2)
        self.assertLess(score_contradict, score_strong)

    # 17. Independent Judge Brain & Safeguards
    def test_cognitive_6_independent_judge_brain_approval(self) -> None:
        judge = IndependentJudgeBrain()
        v_engine = VirtualTradingEngine()

        trade = v_engine.create_virtual_trade(
            asset=self.asset, timeframe=self.timeframe, direction="BUY",
            entry_price=1800.0, stop_loss=1790.0, target_price=1830.0,
            expected_scenario="upward_H1", entry_time=self.now
        )
        sim_res = SimulationResult(
            TradeId=trade.TradeId, IsSuccess=True,
            MaxFavorableMovementPoints=30.0, MaxAdverseMovementPoints=1.0, FinalResult="WIN"
        )

        # Disapproved due to insufficient sample count (< 3)
        rep_fail = judge.evaluate_virtual_trade(trade, sim_res, sample_count=2)
        self.assertEqual(rep_fail.Verdict, "DISAPPROVED")
        self.assertFalse(rep_fail.IsScientificallyValid)

        # Approved under sufficient samples
        rep_ok = judge.evaluate_virtual_trade(trade, sim_res, sample_count=10)
        self.assertEqual(rep_ok.Verdict, "APPROVED")
        self.assertTrue(rep_ok.IsScientificallyValid)

    # 18. Anti Self-Deception Future Leakage Checks
    def test_cognitive_7_anti_self_deception_leakage(self) -> None:
        deception_layer = AntiSelfDeceptionLayer()
        current_time = self.now + timedelta(hours=3)

        # Candidate observations - observation 3 is at current_time (boundary), observation 5 is in future
        layer = DataRealityLayer()
        candidate_obs = layer.receive_data(self.dummy_data, self.timeframe)

        # Verify look-ahead error is raised when future leakage occurs
        with self.assertRaises(ValueError):
            deception_layer.verify_no_future_leakage(current_time, candidate_obs)

        # Verify it passes cleanly if all candidates are within current boundary
        clean_obs = candidate_obs[:3]
        deception_layer.verify_no_future_leakage(current_time, clean_obs)
