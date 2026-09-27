import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from src.Research.Brain.models import MarketObservation, AnalysisReport, PatternMemory
from src.Research.Brain.data_reality import DataRealityLayer
from src.Research.Brain.observation import ObservationBrain
from src.Research.Brain.discovery import PatternDiscoveryEngine
from src.Research.Brain.hypothesis import HypothesisEngine
from src.Research.Brain.simulation import SimulationBrain
from src.Research.Brain.quality_control import QualityControlBrain
from src.Research.Brain.judge import JudgeBrain
from src.Research.Brain.active_learning import ActiveLearningEngine
from src.Research.Brain.integrity import LearningIntegrityService
from src.Research.Brain.memory import MarketMemorySystem

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
        self.integrity_service = LearningIntegrityService()
        self.qc_brain = QualityControlBrain()
        # Immutable decision-time context for open virtual trades. Outcomes are
        # learned only after a later candle closes the trade.
        self._pending_trade_context: Dict[str, Dict[str, Any]] = {}

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

        # 2. Update active simulation trades first. A trade closed here was opened
        # on an earlier candle, so it is eligible for Judge + post-outcome learning.
        closed_trades = self.simulation_brain.update_active_trades(latest_obs)
        evaluated_trades = []
        for closed_trade in closed_trades:
            context = self._pending_trade_context.pop(closed_trade.trade_id, None)
            if not context:
                continue
            judge_result = self.judge_brain.evaluate_hypothesis_and_decision(
                hypothesis=context["hypothesis"],
                virtual_trade=closed_trade,
                actual_outcome_ticks=[{
                    "close": closed_trade.exit_price,
                    "timestamp": closed_trade.exit_time.isoformat() if closed_trade.exit_time else latest_obs.timestamp.isoformat()
                }]
            )
            matches = self.discovery_engine.find_matches(
                context["signature"], self.memory_system.get_patterns()
            )
            if matches:
                pattern, _ = matches[0]
                pattern.occurrences_count += 1
                if closed_trade.final_result == "SUCCESS":
                    pattern.continuation_count += 1
                else:
                    pattern.reversal_count += 1
                pattern.outcomes.append({
                    "trade_id": closed_trade.trade_id,
                    "timestamp": closed_trade.exit_time.isoformat() if closed_trade.exit_time else latest_obs.timestamp.isoformat(),
                    "outcome": closed_trade.final_result,
                    "judge_vetted_accuracy": judge_result.get("pattern_accuracy", 0.0),
                    "is_lucky_win": judge_result.get("was_influenced_by_luck", False),
                })
                self.memory_system.add_pattern(pattern)
            else:
                new_pattern = self.discovery_engine.create_new_pattern(
                    context["signature"],
                    is_continuation=closed_trade.final_result == "SUCCESS"
                )
                self.memory_system.add_pattern(new_pattern)
            evaluated_trades.append(judge_result)

        # Active learning is advisory only; it cannot alter execution or risk policy.
        active_learning_priorities = self.active_learning.analyze_weaknesses_and_set_priorities(
            self.memory_system.get_patterns()
        )
        integrity_report = self.integrity_service.inspect_patterns_integrity(
            self.memory_system.get_patterns()
        )

        # 3. Process Observations in Observation Brain
        sequence = self.observation_brain.process_observations(observations)

        # 4. Extract close signature for similarity matching
        sig = self.discovery_engine.extract_signature(sequence.observations)
        matched = self.discovery_engine.find_matches(sig, self.memory_system.get_patterns())
        outcome_agg = self.discovery_engine.aggregate_outcomes(matched)

        # 5. Formulate the canonical Trading Brain hypothesis.
        # Live analysis may propose only a virtual action; execution remains outside
        # this Brain and is governed by the downstream risk/execution gates.
        hypothesis = self.hypothesis_engine.formulate_hypothesis(
            current_signature=sig,
            historical_patterns=self.memory_system.get_patterns()
        )
        decision = hypothesis.expected_direction
        expected = "Continuation" if decision == "BUY" else ("Reversal" if decision == "SELL" else "Stable")

        # Record Virtual Trade if decided (100% simulated, NO execution pathways exist)
        virtual_trade = None
        if decision != "WAIT":
            virtual_trade = self.simulation_brain.make_virtual_decision(
                action=decision,
                entry_price=latest_obs.close_price,
                timestamp=latest_obs.timestamp,
                expected_scenario=expected
            )
            if virtual_trade is not None:
                self._pending_trade_context[virtual_trade.trade_id] = {
                    "hypothesis": hypothesis,
                    "signature": list(sig),
                    "decision_time": latest_obs.timestamp.isoformat(),
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
                    "hypothesis_id": hypothesis.hypothesis_id,
                    "expected_direction": hypothesis.expected_direction,
                    "confidence": hypothesis.confidence,
                    "validation_status": hypothesis.validation_status,
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

        # Attach learning telemetry without giving the Brain execution authority.
        # These fields are evidence only and never mutate downstream risk/execution.
        report.learning_feedback = {
            "closed_trades_evaluated": len(evaluated_trades),
            "active_learning_priorities": active_learning_priorities[:10],
            "integrity_report": integrity_report,
            "post_outcome_learning": True,
        }

        return report
