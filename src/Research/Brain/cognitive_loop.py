import uuid
from datetime import datetime
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
    E2E historical replay and cognitive learning loop.

    The replay cursor is the sole source of decision-time market information.
    A virtual trade is evaluated only after a later replay observation closes it;
    an open trade is never treated as a completed outcome. This prevents the
    learning loop from manufacturing outcomes from the decision candle.
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

        self.replay_engine = MarketReplayEngine(symbol, observations)
        self.observation_brain = ObservationBrain(symbol, timeframe)
        self.discovery_engine = PatternDiscoveryEngine()
        self.hypothesis_engine = HypothesisEngine(self.discovery_engine)
        self.simulation_brain = SimulationBrain(symbol, timeframe)
        self.judge_brain = JudgeBrain()
        self.active_learning = ActiveLearningEngine()
        self.integrity_service = LearningIntegrityService()

        self.episodes: List[ReplayEpisode] = []
        # Trade-id -> immutable decision-time context. Outcomes are attached only
        # when SimulationBrain later closes the virtual trade.
        self._pending_trade_context: Dict[str, Dict[str, Any]] = {}

    def execute_replay_session(self, steps_count: int = 10, scale: str = "hours") -> List[ReplayEpisode]:
        session_episodes: List[ReplayEpisode] = []

        for _ in range(steps_count):
            current_time = self.replay_engine.get_current_time()
            if not current_time:
                break

            # Only data at/before the replay cursor is visible to the Brain.
            available_data = self.replay_engine.get_available_data()
            if len(available_data) < 5:
                if not self.replay_engine.advance_by_scale(scale):
                    break
                continue

            latest_obs = available_data[-1]

            # Existing trades are updated BEFORE creating the new decision.
            # Therefore a newly-created trade cannot be evaluated against its
            # own entry candle.
            closed_trades = self.simulation_brain.update_active_trades(latest_obs)

            seq = self.observation_brain.process_observations(available_data)
            for evt in seq.events:
                self.memory_system.add_event(evt)

            sig = self.discovery_engine.extract_signature(available_data)
            hypothesis = self.hypothesis_engine.formulate_hypothesis(
                current_signature=sig,
                historical_patterns=self.memory_system.get_patterns(),
                current_behavior_profile=self.discovery_engine.extract_behavior_profile(available_data),
            )

            decision_time = latest_obs.timestamp
            virtual_trade = None
            if hypothesis.expected_direction != "WAIT":
                virtual_trade = self.simulation_brain.make_virtual_decision(
                    action=hypothesis.expected_direction,
                    entry_price=latest_obs.close_price,
                    timestamp=decision_time,
                    expected_scenario=hypothesis.expected_direction
                )
                if virtual_trade is not None:
                    self._pending_trade_context[virtual_trade.trade_id] = {
                        "hypothesis": hypothesis,
                        "signature": list(sig),
                        "behavior_profile": self.discovery_engine.extract_behavior_profile(available_data),
                        "decision_time": decision_time.isoformat(),
                    }

            # Evaluate only trades that actually closed on this replay step.
            # The current decision remains pending and cannot become its own outcome.
            evaluated_trades = []
            for closed_trade in closed_trades:
                context = self._pending_trade_context.pop(closed_trade.trade_id, None)
                if not context:
                    continue

                closed_hypothesis = context["hypothesis"]
                closed_signature = context["signature"]
                outcome_ticks = [{
                    "close": closed_trade.exit_price,
                    "timestamp": closed_trade.exit_time.isoformat()
                    if closed_trade.exit_time else decision_time.isoformat()
                }]

                judge_res = self.judge_brain.evaluate_hypothesis_and_decision(
                    hypothesis=closed_hypothesis,
                    virtual_trade=closed_trade,
                    actual_outcome_ticks=outcome_ticks
                )

                self._learn_from_closed_trade(
                    signature=closed_signature,
                    trade=closed_trade,
                    judge_result=judge_res,
                    behavior_profile=context.get("behavior_profile", {}),
                )

                evaluated_trades.append((closed_trade, closed_hypothesis, judge_res))

            # Active learning is advisory only. It produces research priorities;
            # it cannot mutate execution/risk authority.
            priorities = self.active_learning.analyze_weaknesses_and_set_priorities(
                self.memory_system.get_patterns()
            )

            # Record one episode for the current decision. Its outcome is explicitly
            # PENDING when the trade has not yet closed.
            current_judge = self.judge_brain.evaluate_hypothesis_and_decision(
                hypothesis=hypothesis,
                virtual_trade=None,
                actual_outcome_ticks=[]
            )
            current_judge["outcome_status"] = "PENDING"
            current_judge["learning_feedback"] = (
                "Decision recorded; outcome remains pending until a later replay "
                "observation closes the virtual trade."
            )

            current_trade_outcome = {
                "final_result": "PENDING" if virtual_trade else "WAIT",
                "max_fav": virtual_trade.max_favorable_movement if virtual_trade else 0.0,
                "max_adv": virtual_trade.max_adverse_movement if virtual_trade else 0.0,
            }

            episode = ReplayEpisode(
                episode_id=f"ep-{uuid.uuid4().hex[:8]}",
                symbol=self.symbol,
                start_time=available_data[0].timestamp,
                decision_time=decision_time,
                market_context={
                    "current_price": latest_obs.close_price,
                    "timeframe": self.timeframe,
                    "available_history_count": len(available_data),
                    "decision_data_cutoff": decision_time.isoformat(),
                    "future_data_visible_at_decision": False,
                },
                observed_sequence=[evt.to_dict() for evt in seq.events[-3:]],
                brain_hypothesis=hypothesis.to_dict(),
                simulation_decision=virtual_trade.to_dict() if virtual_trade else None,
                actual_outcome=current_trade_outcome,
                judge_result=current_judge,
                learning_feedback={
                    "feedback": current_judge["learning_feedback"],
                    "reasoning_score": current_judge["reasoning_quality_score"],
                    "decision_score": current_judge["decision_quality_score"],
                    "active_learning_priorities": priorities[:10],
                    "closed_trades_evaluated_this_step": len(evaluated_trades),
                }
            )

            self.episodes.append(episode)
            session_episodes.append(episode)

            self.memory_system.consolidate_patterns_to_concepts(
                min_samples=4,
                min_validation_score=0.70
            )

            if not self.replay_engine.advance_by_scale(scale):
                break

        return session_episodes

    def process_live_observation(self, observations: List[MarketObservation]) -> Optional[ReplayEpisode]:
        """Processes one newly-closed live candle through the existing cognitive learning chain.

        This is observational/research-only: SimulationBrain creates virtual trades only.
        No broker/order/execution component is reachable from this method.
        """
        if len(observations) < 5:
            return None

        ordered = sorted(observations, key=lambda o: o.timestamp)
        latest_obs = ordered[-1]
        last_processed = getattr(self, "_last_live_observation_time", None)
        if last_processed is not None and latest_obs.timestamp <= last_processed:
            return None

        self.replay_engine.update_observations(ordered, current_time=latest_obs.timestamp)
        available_data = self.replay_engine.get_available_data()
        if len(available_data) < 5:
            return None

        closed_trades = self.simulation_brain.update_active_trades(latest_obs)

        seq = self.observation_brain.process_observations(available_data)
        for evt in seq.events:
            self.memory_system.add_event(evt)

        sig = self.discovery_engine.extract_signature(available_data)
        hypothesis = self.hypothesis_engine.formulate_hypothesis(
            current_signature=sig,
            historical_patterns=self.memory_system.get_patterns(),
            current_behavior_profile=self.discovery_engine.extract_behavior_profile(available_data),
        )

        evaluated_trades = []
        for closed_trade in closed_trades:
            context = self._pending_trade_context.pop(closed_trade.trade_id, None)
            if not context:
                continue
            closed_hypothesis = context["hypothesis"]
            closed_signature = context["signature"]
            outcome_ticks = [{
                "close": closed_trade.exit_price,
                "timestamp": closed_trade.exit_time.isoformat()
                if closed_trade.exit_time else latest_obs.timestamp.isoformat()
            }]
            judge_res = self.judge_brain.evaluate_hypothesis_and_decision(
                hypothesis=closed_hypothesis,
                virtual_trade=closed_trade,
                actual_outcome_ticks=outcome_ticks
            )
            self._learn_from_closed_trade(
                signature=closed_signature,
                trade=closed_trade,
                judge_result=judge_res,
                behavior_profile=context.get("behavior_profile", {}),
            )
            evaluated_trades.append((closed_trade, judge_res))

        virtual_trade = None
        if hypothesis.expected_direction != "WAIT":
            virtual_trade = self.simulation_brain.make_virtual_decision(
                action=hypothesis.expected_direction,
                entry_price=latest_obs.close_price,
                timestamp=latest_obs.timestamp,
                expected_scenario=hypothesis.expected_direction
            )
            if virtual_trade is not None:
                self._pending_trade_context[virtual_trade.trade_id] = {
                    "hypothesis": hypothesis,
                    "signature": list(sig),
                    "behavior_profile": self.discovery_engine.extract_behavior_profile(available_data),
                    "decision_time": latest_obs.timestamp.isoformat(),
                }

        priorities = self.active_learning.analyze_weaknesses_and_set_priorities(
            self.memory_system.get_patterns()
        )
        current_judge = self.judge_brain.evaluate_hypothesis_and_decision(
            hypothesis=hypothesis,
            virtual_trade=None,
            actual_outcome_ticks=[]
        )
        current_judge["outcome_status"] = "PENDING"
        current_judge["learning_feedback"] = (
            "Live research decision recorded; outcome remains pending until a later "
            "market observation closes the virtual trade."
        )

        episode = ReplayEpisode(
            episode_id=f"live-{uuid.uuid4().hex[:8]}",
            symbol=self.symbol,
            start_time=available_data[0].timestamp,
            decision_time=latest_obs.timestamp,
            market_context={
                "current_price": latest_obs.close_price,
                "timeframe": self.timeframe,
                "available_history_count": len(available_data),
                "decision_data_cutoff": latest_obs.timestamp.isoformat(),
                "future_data_visible_at_decision": False,
                "live_mode": True,
                "closed_trades_evaluated_this_step": len(evaluated_trades),
            },
            observed_sequence=[evt.to_dict() for evt in seq.events[-3:]],
            brain_hypothesis=hypothesis.to_dict(),
            simulation_decision=virtual_trade.to_dict() if virtual_trade else None,
            actual_outcome={
                "final_result": "PENDING" if virtual_trade else "WAIT",
                "max_fav": virtual_trade.max_favorable_movement if virtual_trade else 0.0,
                "max_adv": virtual_trade.max_adverse_movement if virtual_trade else 0.0,
            },
            judge_result=current_judge,
            learning_feedback={
                "feedback": current_judge["learning_feedback"],
                "reasoning_score": current_judge["reasoning_quality_score"],
                "decision_score": current_judge["decision_quality_score"],
                "active_learning_priorities": priorities[:10],
                "closed_trades_evaluated_this_step": len(evaluated_trades),
            }
        )

        self.episodes.append(episode)
        self.memory_system.consolidate_patterns_to_concepts(
            min_samples=4,
            min_validation_score=0.70
        )
        self._last_live_observation_time = latest_obs.timestamp
        return episode

    def _learn_from_closed_trade(
        self,
        signature: List[float],
        trade: Any,
        judge_result: Dict[str, Any],
        behavior_profile: Optional[Dict[str, float]] = None,
    ) -> None:
        """Apply only post-outcome learning to Pattern Memory."""
        matches = self.discovery_engine.find_matches(
            signature,
            self.memory_system.get_patterns(),
            current_behavior_profile=behavior_profile,
        )
        learning_outcome = getattr(trade, "learning_outcome", {}) or {}
        is_success = (
            trade.final_result == "SUCCESS"
            or (
                trade.final_result == "WINDOW_COMPLETE"
                and bool(learning_outcome.get("target_reached", False))
            )
        )

        if matches:
            best_pattern, _ = matches[0]
            best_pattern.occurrences_count += 1
            if is_success:
                best_pattern.continuation_count += 1
            else:
                best_pattern.reversal_count += 1
            direction = str(getattr(trade, "decision_action", "WAIT")).upper()
            if direction == "BUY":
                best_pattern.buy_count = getattr(best_pattern, "buy_count", 0) + 1
            elif direction == "SELL":
                best_pattern.sell_count = getattr(best_pattern, "sell_count", 0) + 1
            best_pattern.outcomes.append({
                "trade_id": trade.trade_id,
                "timestamp": trade.exit_time.isoformat() if trade.exit_time else datetime.now().isoformat(),
                "outcome": trade.final_result,
                "direction": direction,
                "judge_vetted_accuracy": judge_result.get("pattern_accuracy", 0.0),
                "is_lucky_win": judge_result.get("was_influenced_by_luck", False),
                "learning_outcome": learning_outcome,
            })
            self.memory_system.add_pattern(best_pattern)
        else:
            new_pattern = self.discovery_engine.create_new_pattern(
                signature,
                is_continuation=is_success,
                direction=str(getattr(trade, "decision_action", "WAIT")).upper(),
                behavior_profile=behavior_profile or {},
            )
            if learning_outcome:
                new_pattern.outcomes[-1]["learning_outcome"] = learning_outcome
            self.memory_system.add_pattern(new_pattern)
