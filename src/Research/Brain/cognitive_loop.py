import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from src.Research.Brain.models import MarketObservation, ReplayEpisode, PatternMemory, Hypothesis
from src.Research.Brain.replay import MarketReplayEngine
from src.Research.Brain.observation import ObservationBrain
from src.Research.Brain.discovery import PatternDiscoveryEngine
from src.Research.Brain.hypothesis import HypothesisEngine
from src.Research.Brain.simulation import SimulationBrain
from src.Research.Brain.judge import JudgeBrain
from src.Research.Brain.memory import MarketMemorySystem
from src.Research.Brain.active_learning import ActiveLearningEngine
from src.Research.Brain.integrity import LearningIntegrityService

class CognitiveReplayLoop:
    """
    Coordinates and orchestrates the E2E Market Replay Training & Cognitive Learning Engine loop.
    Ensures that:
    1. Historical reality is replayed step-by-step (Future Leakage Protection).
    2. Observation Brain notices structures without predefined terms or indicators.
    3. Hypothesis Engine creates testable expectations with supporting samples.
    4. Simulation Brain virtually triggers and tracks decisions (applying spreads/slippage).
    5. Independent Judge Brain evaluates reasoning quality, accuracy, and luck.
    6. Learning feedback is consolidated, and priorities are set via Active Learning.
    7. Memory layers are cleanly separated and saved.
    """
    def __init__(
        self,
        symbol: str,
        timeframe: str,
        observations: List[MarketObservation],
        memory_system: Optional[MarketMemorySystem] = None
    ) -> None:
        self.symbol = symbol
        self.timeframe = timeframe
        self.memory_system = memory_system or MarketMemorySystem()

        # Instantiate core subcomponents
        self.replay_engine = MarketReplayEngine(symbol, observations)
        self.observation_brain = ObservationBrain(symbol, timeframe)
        self.discovery_engine = PatternDiscoveryEngine()
        self.hypothesis_engine = HypothesisEngine(self.discovery_engine)
        self.simulation_brain = SimulationBrain(symbol, timeframe)
        self.judge_brain = JudgeBrain()
        self.active_learning = ActiveLearningEngine()
        self.integrity_service = LearningIntegrityService()

        self.episodes: List[ReplayEpisode] = []

    def execute_replay_session(self, steps_count: int = 10, scale: str = "hours") -> List[ReplayEpisode]:
        """
        Executes a series of replay steps.
        At each step, advances historical cursor, forms hypothesis, simulates decision,
        triggers exit tracking, judges accuracy, updates memories, and consolidates.
        """
        session_episodes: List[ReplayEpisode] = []

        for _ in range(steps_count):
            current_time = self.replay_engine.get_current_time()
            if not current_time:
                break

            # 1. Fetch currently available historical data (Future Leakage Protected)
            available_data = self.replay_engine.get_available_data()
            if len(available_data) < 5:
                # Need at least 5 observations to parse events/signatures
                if not self.replay_engine.advance_by_scale(scale):
                    break
                continue

            latest_obs = available_data[-1]

            # 2. Update existing active virtual trades first
            closed_trades = self.simulation_brain.update_active_trades(latest_obs)

            # 3. Formulate observations sequence
            seq = self.observation_brain.process_observations(available_data)
            for evt in seq.events:
                self.memory_system.add_event(evt)

            # 4. Formulate hypothesis
            sig = self.discovery_engine.extract_signature(available_data)
            hypothesis = self.hypothesis_engine.formulate_hypothesis(
                current_signature=sig,
                historical_patterns=self.memory_system.get_patterns()
            )

            # 5. Make virtual decision
            virtual_trade = None
            if hypothesis.expected_direction != "WAIT":
                virtual_trade = self.simulation_brain.make_virtual_decision(
                    action=hypothesis.expected_direction,
                    entry_price=latest_obs.close_price,
                    timestamp=latest_obs.timestamp,
                    expected_scenario=hypothesis.expected_direction
                )

            # If there was no virtual decision made or we wait, let's look at recently closed trades to construct episode outcomes
            # For simplicity, if we had a trade close or if we made a decision, we log an episode.
            decision_time = latest_obs.timestamp

            # Get some ticks or updates for the Judge evaluation
            mock_outcome_ticks = [{"close": latest_obs.close_price, "timestamp": latest_obs.timestamp.isoformat()}]

            # Evaluate via Judge
            judge_res = self.judge_brain.evaluate_hypothesis_and_decision(
                hypothesis=hypothesis,
                virtual_trade=virtual_trade,
                actual_outcome_ticks=mock_outcome_ticks
            )

            # If virtual trade succeeded or failed, update Pattern Memory continuation or reversal
            if virtual_trade and virtual_trade.final_result:
                # Update corresponding patterns
                matches = self.discovery_engine.find_matches(sig, self.memory_system.get_patterns())
                is_cont = virtual_trade.final_result == "SUCCESS"
                if matches:
                    best_pat, _ = matches[0]
                    best_pat.occurrences_count += 1
                    if is_cont:
                        best_pat.continuation_count += 1
                    else:
                        best_pat.reversal_count += 1
                    self.memory_system.add_pattern(best_pat)
                else:
                    # Discover and add new pattern
                    new_pat = self.discovery_engine.create_new_pattern(sig, is_continuation=is_cont)
                    self.memory_system.add_pattern(new_pat)

            # 6. Build immutable ReplayEpisode
            episode = ReplayEpisode(
                episode_id=f"ep-{uuid.uuid4().hex[:8]}",
                symbol=self.symbol,
                start_time=available_data[0].timestamp,
                decision_time=decision_time,
                market_context={
                    "current_price": latest_obs.close_price,
                    "timeframe": self.timeframe,
                    "available_history_count": len(available_data)
                },
                observed_sequence=[evt.to_dict() for evt in seq.events[-3:]],
                brain_hypothesis=hypothesis.to_dict(),
                simulation_decision=virtual_trade.to_dict() if virtual_trade else None,
                actual_outcome={
                    "final_result": virtual_trade.final_result if virtual_trade else "WAIT",
                    "max_fav": virtual_trade.max_favorable_movement if virtual_trade else 0.0,
                    "max_adv": virtual_trade.max_adverse_movement if virtual_trade else 0.0
                },
                judge_result=judge_res,
                learning_feedback={
                    "feedback": judge_res["learning_feedback"],
                    "reasoning_score": judge_res["reasoning_quality_score"],
                    "decision_score": judge_res["decision_quality_score"]
                }
            )

            self.episodes.append(episode)
            session_episodes.append(episode)

            # Consolidate memories to promote patterns to Approved Concepts if requirements are met
            self.memory_system.consolidate_patterns_to_concepts(min_samples=4, min_validation_score=0.70)

            # Advance replay engine cursor
            if not self.replay_engine.advance_by_scale(scale):
                break

        return session_episodes
