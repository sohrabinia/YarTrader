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
        self.simulation_brain = SimulationBrain(symbol, timeframe)
        self.qc_brain = QualityControlBrain()

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

        # 2. Update active simulation trades first
        self.simulation_brain.update_active_trades(latest_obs)

        # 3. Process Observations in Observation Brain
        sequence = self.observation_brain.process_observations(observations)

        # 4. Extract close signature for similarity matching
        sig = self.discovery_engine.extract_signature(sequence.observations)
        matched = self.discovery_engine.find_matches(sig, self.memory_system.get_patterns())
        outcome_agg = self.discovery_engine.aggregate_outcomes(matched)

        # 5. Formulate Hypothesis Decision (Simulated only)
        decision = "WAIT"
        expected = "Stable"
        if matched:
            best_match, sim_score = matched[0]
            # Decide to BUY if continuation of positive pattern is likely, etc.
            if outcome_agg["continuation_pct"] > 60.0:
                decision = "BUY"
                expected = "Continuation"
            elif outcome_agg["reversal_pct"] > 60.0:
                decision = "SELL"
                expected = "Reversal"

        # Record Virtual Trade if decided (100% simulated, NO execution pathways exist)
        virtual_trade = None
        if decision != "WAIT":
            virtual_trade = self.simulation_brain.make_virtual_decision(
                action=decision,
                entry_price=latest_obs.close_price,
                timestamp=latest_obs.timestamp,
                expected_scenario=expected
            )

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

        return report
