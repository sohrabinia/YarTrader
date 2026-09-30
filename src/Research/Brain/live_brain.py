import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from src.Research.Brain.models import MarketObservation, AnalysisReport, PatternMemory
from src.Research.Brain.data_reality import DataRealityLayer
from src.Research.Brain.observation import ObservationBrain
from src.Research.Brain.discovery import PatternDiscoveryEngine
from src.Research.Brain.simulation import SimulationBrain
from src.Research.Brain.quality_control import QualityControlBrain
from src.Research.Brain.memory import MarketMemorySystem
from src.Research.Brain.hypothesis import HypothesisEngine
from src.Research.Brain.judge import JudgeBrain
from src.Research.Brain.active_learning import ActiveLearningEngine

class LiveAnalysisBrain:
    """
    Live Analysis Brain coordinating the Newborn Market Discovery Brain pipeline.
    Connects DataRealityLayer, ObservationBrain, PatternDiscoveryEngine,
    SimulationBrain, and QualityControlBrain.
    Keeps systems strictly read-only with zero transaction execution pathways.
    """
    def __init__(self, symbol: str, timeframe: str, memory_system: Optional[MarketMemorySystem] = None) -> None:
        self.symbol = symbol
        self.timeframe = timeframe
        self.memory_system = memory_system or MarketMemorySystem()

        # Instantiate subcomponents
        self.data_layer = DataRealityLayer(symbol)
        self.observation_brain = ObservationBrain(symbol, timeframe)
        self.discovery_engine = PatternDiscoveryEngine()
        self.hypothesis_engine = HypothesisEngine(self.discovery_engine)
        self.simulation_brain = SimulationBrain(symbol, timeframe)
        self.judge_brain = JudgeBrain()
        self.active_learning = ActiveLearningEngine()
        self.qc_brain = QualityControlBrain()
        self._pending_hypotheses: Dict[str, Any] = {}
        self._last_learning_summary: Dict[str, Any] = {}
        self._processed_candle_timestamps = set()
        self._last_report: Optional[AnalysisReport] = None

    def process_live_candle(self, raw_candle: Dict[str, Any]) -> AnalysisReport:
        """
        Processes a new live candle, updates sequence perception, discovers matching
        patterns, creates simulated decisions, and evaluates reasoning quality.
        """
        # 1. Ingest into Data Reality Layer
        observations = self.data_layer.ingest_raw_candles(self.timeframe, [raw_candle])
        if not observations:
            raise ValueError("Invalild or missing raw candle data.")

        latest_obs = observations[-1]
        if latest_obs.timestamp in self._processed_candle_timestamps:
            if self._last_report is None:
                raise ValueError("Duplicate candle received before a live Brain report was established.")
            return self._last_report
        self._processed_candle_timestamps.add(latest_obs.timestamp)

        # 2. Update active simulation trades first and learn from closed outcomes.
        closed_trades = self.simulation_brain.update_active_trades(latest_obs)
        for closed_trade in closed_trades:
            hypothesis = self._pending_hypotheses.pop(closed_trade.trade_id, None)
            if hypothesis is None:
                continue
            judge_res = self.judge_brain.evaluate_hypothesis_and_decision(
                hypothesis=hypothesis,
                virtual_trade=closed_trade,
                actual_outcome_ticks=[{
                    "close": latest_obs.close_price,
                    "timestamp": latest_obs.timestamp.isoformat()
                }]
            )
            from src.Research.Brain.models import ExperienceMemory
            experience = ExperienceMemory(
                experience_id=f"exp-live-{uuid.uuid4().hex[:8]}",
                symbol=self.symbol,
                timeframe=self.timeframe,
                timestamp=closed_trade.exit_time or latest_obs.timestamp,
                situation_signature=list(hypothesis.sequence_signature),
                decision_action=closed_trade.decision_action,
                outcome_result=closed_trade.final_result or "NEUTRAL",
                lesson_feedback=judge_res["learning_feedback"],
                max_favorable_excursion=closed_trade.max_favorable_movement,
                max_adverse_excursion=closed_trade.max_adverse_movement,
                meta={
                    "judge_reasoning_score": judge_res["reasoning_quality_score"],
                    "judge_accuracy": judge_res["pattern_accuracy"],
                    "is_lucky_win": judge_res["was_influenced_by_luck"],
                    "trade_id": closed_trade.trade_id
                }
            )
            self.memory_system.add_experience(experience)

        # 3. Process Observations in Observation Brain
        sequence = self.observation_brain.process_observations(observations)

        # 4. Extract the raw signature and formulate the canonical Brain hypothesis.
        sig = self.discovery_engine.extract_signature(sequence.observations)
        matched = self.discovery_engine.find_matches(sig, self.memory_system.get_patterns())
        outcome_agg = self.discovery_engine.aggregate_outcomes(matched)
        hypothesis = self.hypothesis_engine.formulate_hypothesis(
            current_signature=sig,
            historical_patterns=self.memory_system.get_patterns()
        )
        decision = hypothesis.expected_direction
        expected = "Continuation" if decision == "BUY" else ("Reversal" if decision == "SELL" else "Stable")

        # 5. Simulate the hypothesis only; this path has no broker/execution capability.
        virtual_trade = None
        if decision in ("BUY", "SELL") and not self.simulation_brain.active_trades:
            virtual_trade = self.simulation_brain.make_virtual_decision(
                action=decision,
                entry_price=latest_obs.close_price,
                timestamp=latest_obs.timestamp,
                expected_scenario=expected
            )
            if virtual_trade:
                self._pending_hypotheses[virtual_trade.trade_id] = hypothesis

        # 5b. Consolidate learning layers after observed outcomes and refresh active-learning priorities.
        promoted_experiences = self.memory_system.promote_raw_events_to_experiences(self.symbol, self.timeframe)
        promoted_patterns = self.memory_system.promote_experiences_to_patterns()
        priorities = self.active_learning.analyze_weaknesses_and_set_priorities(self.memory_system.get_patterns())
        consolidated = self.memory_system.consolidate_patterns_to_concepts(min_samples=4, min_validation_score=0.70)
        self._last_learning_summary = {
            "promoted_experiences": len(promoted_experiences),
            "promoted_patterns": len(promoted_patterns),
            "active_learning_priorities": priorities[:10],
            "concepts_consolidated": len(consolidated),
            "memory": self.memory_system.get_learning_statistics()
        }

        # 6. Evaluate Quality Control Score
        quality_score = self.qc_brain.evaluate_reasoning_quality(
            matched_patterns=matched,
            historical_sample_size=len(self.memory_system.get_events())
        )

        report = AnalysisReport(
            report_id=f"rpt-brain-{uuid.uuid4().hex[:8]}",
            symbol=self.symbol,
            timestamp=datetime.now(),
            latest_observations=[
                {
                    "timestamp": latest_obs.timestamp.isoformat(),
                    "close": latest_obs.close_price,
                    "high": latest_obs.high,
                    "low": latest_obs.low
                }
            ],
            active_hypotheses=[
                {
                    "matched_patterns": len(matched),
                    "continuation_likelihood": outcome_agg["continuation_pct"],
                    "reversal_likelihood": outcome_agg["reversal_pct"],
                    "suggested_virtual_action": decision
                }
            ],
            simulated_trades=[
                {
                    "trade_id": t.trade_id,
                    "action": t.decision_action,
                    "entry_price": t.entry_price,
                    "stop": t.virtual_stop,
                    "target": t.virtual_target
                }
                for t in self.simulation_brain.active_trades
            ],
            reasoning_quality_score=quality_score,
            is_read_only_compliant=True
        )

        self._last_report = report
        return report
