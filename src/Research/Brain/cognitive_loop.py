import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional

from src.Research.Brain.models import (
    MarketObservation,
    ReplayEpisode,
    ExperienceMemory,
    SimulatedDecision,
)
from src.Research.Brain.replay import MarketReplayEngine
from src.Research.Brain.observation import ObservationBrain
from src.Research.Brain.discovery import PatternDiscoveryEngine
from src.Research.Brain.hypothesis import HypothesisEngine
from src.Research.Brain.simulation import SimulationBrain
from src.Research.Brain.judge import JudgeBrain
from src.Research.Brain.memory import MarketMemorySystem
from src.Research.Brain.active_learning import ActiveLearningEngine
from src.Research.Brain.integrity import LearningIntegrityService
from src.Research.Brain.brain_context import build_brain_context


class CognitiveReplayLoop:
    """Canonical chronological replay and learning loop for the single Brain."""

    def __init__(
        self,
        symbol: str,
        timeframe: str,
        observations: List[MarketObservation],
        memory_system: Optional[MarketMemorySystem] = None,
    ) -> None:
        self.symbol = symbol
        self.timeframe = timeframe.upper()
        self.memory_system = memory_system or MarketMemorySystem()
        self.replay_engine = MarketReplayEngine(symbol, observations)
        self.observation_brain = ObservationBrain(symbol, self.timeframe)
        self.discovery_engine = PatternDiscoveryEngine()
        self.hypothesis_engine = HypothesisEngine(self.discovery_engine)
        self.simulation_brain = SimulationBrain(symbol, self.timeframe)
        self.judge_brain = JudgeBrain()
        self.active_learning = ActiveLearningEngine()
        self.integrity_service = LearningIntegrityService()
        self.episodes: List[ReplayEpisode] = []
        self._trade_context: Dict[str, Dict[str, Any]] = {}

    def _learn_from_closed_trade(
        self,
        trade: Any,
        trade_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Judge only after a trade has a terminal historical outcome."""
        outcome = trade.final_result or "NEUTRAL"
        sim_decision = SimulatedDecision(
            timestamp=trade.entry_time,
            symbol=trade.symbol,
            price=float(trade.entry_price),
            decision_action=trade.decision_action,
            context=trade_context.get("context", {}),
            evidence={
                "hypothesis_id": trade_context.get("hypothesis_id"),
                "pattern_ids": trade_context.get("pattern_ids", []),
                "timeframe_signature": trade_context.get("timeframe_signature", []),
                "context_id": trade_context.get("context_id", ""),
            },
            reason="Historical replay outcome evaluation.",
            confidence=float(trade_context.get("confidence", 0.0)),
        )
        judge_eval = self.judge_brain.evaluate_decision_outcome(
            sim_decision,
            trade_context.get("hypothesis", {}),
            {
                "final_result": outcome,
                "max_favorable_excursion": float(trade.max_favorable_movement),
                "max_adverse_excursion": float(trade.max_adverse_movement),
            },
        )
        exp = ExperienceMemory(
            experience_id=f"exp-REPLAY-{uuid.uuid4().hex[:10]}",
            symbol=trade.symbol.upper(),
            timeframe=trade.timeframe.upper(),
            timestamp=trade.exit_time or datetime.now(),
            situation_signature=list(trade_context.get("signature", [])),
            decision_action=trade.decision_action,
            outcome_result=outcome,
            lesson_feedback=judge_eval.get("learning_feedback", ""),
            max_favorable_excursion=float(trade.max_favorable_movement),
            max_adverse_excursion=float(trade.max_adverse_movement),
            meta={
                "source": "COGNITIVE_REPLAY",
                "trade_id": trade.trade_id,
                "hypothesis_id": trade_context.get("hypothesis_id"),
                "pattern_ids": trade_context.get("pattern_ids", []),
                "predicted_action": trade.decision_action,
                "pattern_symbol": trade.symbol.upper(),
                "pattern_timeframe": trade.timeframe.upper(),
                "timeframe_signature": trade_context.get(
                    "timeframe_signature", [trade.timeframe.upper()]
                ),
                "context_id": trade_context.get("context_id", ""),
                "context_signature": trade_context.get("context_signature", {}),
                "judge_accuracy": judge_eval.get("decision_quality_score", 0.0),
                "judge_reasoning_score": judge_eval.get("reasoning_quality_score", 0.0),
                "favorable_excursion": float(trade.max_favorable_movement),
                "adverse_excursion": float(trade.max_adverse_movement),
                "is_validated": True,
            },
        )
        self.memory_system.add_experience(exp)
        promoted = self.memory_system.promote_experiences_to_patterns()
        priorities = self.active_learning.analyze_weaknesses_and_set_priorities(
            self.memory_system.get_patterns()
        )
        consolidated = self.memory_system.consolidate_patterns_to_concepts(
            min_samples=4, min_validation_score=0.70
        )
        return {
            "judge": judge_eval,
            "promoted_patterns": len(promoted),
            "active_learning_priorities": priorities[:10],
            "concepts_consolidated": len(consolidated),
            "experience_id": exp.experience_id,
        }

    def execute_replay_session(
        self, steps_count: int = 10, scale: str = "hours"
    ) -> List[ReplayEpisode]:
        """
        Replay historical observations chronologically.

        A trade is judged only when SimulationBrain closes it on a later
        historical observation. The resulting ExperienceMemory is promoted
        through PatternMemory, ActiveLearning, and ConceptMemory before the
        next decision is formed.
        """
        session_episodes: List[ReplayEpisode] = []

        for _ in range(steps_count):
            current_time = self.replay_engine.get_current_time()
            if not current_time:
                break

            available_data = self.replay_engine.get_available_data()
            if len(available_data) < 5:
                if not self.replay_engine.advance_by_scale(scale):
                    break
                continue

            latest_obs = available_data[-1]
            brain_context = build_brain_context(
                symbol=self.symbol,
                primary_timeframe=self.timeframe,
                decision_time=latest_obs.timestamp,
                observations_by_tf={self.timeframe: available_data},
            )
            context_id = brain_context["context_id"]
            closed_trades = self.simulation_brain.update_active_trades(latest_obs)

            seq = self.observation_brain.process_observations(available_data)
            for evt in seq.events:
                self.memory_system.add_event(evt)

            closed_learning: List[Dict[str, Any]] = []
            for trade in closed_trades:
                trade_context = self._trade_context.pop(trade.trade_id, {})
                closed_learning.append(
                    self._learn_from_closed_trade(trade, trade_context)
                )

            sig = self.discovery_engine.extract_signature(available_data)
            history_patterns = self.memory_system.get_patterns()
            hypothesis = self.hypothesis_engine.formulate_hypothesis(
                current_signature=sig,
                historical_patterns=history_patterns,
                symbol=self.symbol,
                timeframe=self.timeframe,
                timeframe_signature=[self.timeframe],
                context_id=context_id,
            )

            virtual_trade = None
            exploration_trades = []

            def register_trade(trade: Any, exploration: bool = False) -> None:
                self._trade_context[trade.trade_id] = {
                    "signature": list(sig),
                    "hypothesis_id": hypothesis.hypothesis_id,
                    "hypothesis": hypothesis.to_dict(),
                    "pattern_ids": [
                        p.get("pattern_id")
                        for p in hypothesis.supporting_samples
                        if p.get("pattern_id")
                    ],
                    "confidence": hypothesis.confidence,
                    "timeframe_signature": [self.timeframe],
                    "context_id": context_id,
                    "context_signature": brain_context,
                    "context": brain_context,
                    "exploration": exploration,
                }

            if hypothesis.expected_direction != "WAIT":
                virtual_trade = self.simulation_brain.make_virtual_decision(
                    action=hypothesis.expected_direction,
                    entry_price=latest_obs.close_price,
                    timestamp=latest_obs.timestamp,
                    expected_scenario=hypothesis.expected_direction,
                )
                register_trade(virtual_trade)
            elif not history_patterns and not self.simulation_brain.active_trades:
                # Bootstrap discovery without a user-supplied strategy.
                # Both directions are simulated counterfactuals only.
                for action in ("BUY", "SELL"):
                    trade = self.simulation_brain.make_virtual_decision(
                        action=action,
                        entry_price=latest_obs.close_price,
                        timestamp=latest_obs.timestamp,
                        expected_scenario="EXPLORATION",
                    )
                    register_trade(trade, exploration=True)
                    exploration_trades.append(trade)
                virtual_trade = exploration_trades[0] if exploration_trades else None
            current_outcome = "WAIT"
            if virtual_trade:
                current_outcome = "PENDING"
            elif closed_trades:
                current_outcome = closed_trades[-1].final_result or "NEUTRAL"

            judge_result = (
                closed_learning[-1]["judge"] if closed_learning else None
            )
            learning_feedback = {
                "status": "OUTCOME_PENDING" if virtual_trade else (
                    "LEARNED" if closed_learning else "NO_DECISION"
                ),
                "closed_trades": len(closed_trades),
                "learning_updates": len(closed_learning),
                "active_learning_priorities": (
                    closed_learning[-1]["active_learning_priorities"]
                    if closed_learning
                    else []
                ),
            }
            if judge_result:
                learning_feedback["feedback"] = judge_result.get(
                    "learning_feedback", ""
                )

            episode = ReplayEpisode(
                episode_id=f"ep-{uuid.uuid4().hex[:8]}",
                symbol=self.symbol,
                start_time=available_data[0].timestamp,
                decision_time=latest_obs.timestamp,
                market_context={
                    "current_price": latest_obs.close_price,
                    "timeframe": self.timeframe,
                    "available_history_count": len(available_data),
                    "context_id": context_id,
                    "context": brain_context,
                },
                observed_sequence=[evt.to_dict() for evt in seq.events[-3:]],
                brain_hypothesis=hypothesis.to_dict(),
                simulation_decision=(
                    virtual_trade.to_dict() if virtual_trade else None
                ),
                actual_outcome={
                    "final_result": current_outcome,
                    "closed_trade_results": [
                        t.final_result for t in closed_trades
                    ],
                    "max_fav": (
                        closed_trades[-1].max_favorable_movement
                        if closed_trades
                        else 0.0
                    ),
                    "max_adv": (
                        closed_trades[-1].max_adverse_movement
                        if closed_trades
                        else 0.0
                    ),
                },
                judge_result=judge_result,
                learning_feedback=learning_feedback,
            )
            self.episodes.append(episode)
            session_episodes.append(episode)

            if not self.replay_engine.advance_by_scale(scale):
                break

        return session_episodes
