import uuid
from datetime import datetime
from typing import List, Dict, Any
from src.Research.Brain.models import VirtualTrade, ExperienceMemory, LearningRecord
from src.Research.Brain.memory import MarketMemorySystem

class OutcomeEvaluationEngine:
    """
    Evaluates completed virtual trades, measures quality of reasoning,
    analyzes adverse excursions, and compiles experiences to update memory layers.
    """
    def __init__(self, memory_system: MarketMemorySystem) -> None:
        self.memory_system = memory_system

    def evaluate_completed_trade(self, trade: VirtualTrade, situation_signature: List[float]) -> ExperienceMemory:
        """Converts a closed VirtualTrade into a formal persistent ExperienceMemory."""
        if trade.status != "CLOSED":
            raise ValueError("Cannot evaluate a trade that is still open.")

        lesson = "Success confirmed in standard scenario."
        if trade.final_result == "FAILURE":
            lesson = (
                f"Failure occurred due to: {trade.reason_of_failure or 'unknown'}. "
                f"Max favorable excursion was {trade.max_favorable_movement:.2f} points, "
                f"while adverse excursion hit {trade.max_adverse_movement:.2f} points."
            )

        exp = ExperienceMemory(
            experience_id=f"exp-{uuid.uuid4().hex[:8]}",
            symbol=trade.symbol,
            timeframe=trade.timeframe,
            timestamp=trade.exit_time or datetime.now(),
            situation_signature=situation_signature,
            decision_action=trade.decision_action,
            outcome_result=trade.final_result or "NEUTRAL",
            lesson_feedback=lesson,
            max_favorable_excursion=trade.max_favorable_movement,
            max_adverse_excursion=trade.max_adverse_movement,
            meta={
                "entry_price": trade.entry_price,
                "exit_price": trade.exit_price,
                "expected_scenario": trade.expected_scenario
            }
        )

        # Store in Experience Memory Layer
        self.memory_system.add_experience(exp)
        return exp

    def perform_learning_update(self, symbol: str) -> LearningRecord:
        """
        Scans experiences to update Pattern Memory outcomes.
        Identifies successful patterns vs failed patterns and records context lessons.
        """
        experiences = self.memory_system.get_experiences()
        patterns = self.memory_system.get_patterns()

        successful_pats: List[str] = []
        failed_pats: List[str] = []

        # Simple associative update of pattern metrics
        for exp in experiences:
            # Let's find patterns matching this situation signature
            for pat in patterns:
                # Calculate simple similarity on situation signature
                sig1 = exp.situation_signature
                sig2 = pat.sequence_signature
                if len(sig1) == len(sig2):
                    dot_product = sum(a * b for a, b in zip(sig1, sig2))
                    norm_a = sum(a * a for a in sig1) ** 0.5
                    norm_b = sum(b * b for b in sig2) ** 0.5
                    sim = (dot_product / (norm_a * norm_b)) if (norm_a > 0 and norm_b > 0) else 0.0

                    if sim >= 0.90:  # Strong match
                        pat.occurrences_count += 1
                        if exp.outcome_result == "SUCCESS":
                            pat.continuation_count += 1
                            if pat.pattern_id not in successful_pats:
                                successful_pats.append(pat.pattern_id)
                        else:
                            pat.reversal_count += 1
                            if pat.pattern_id not in failed_pats:
                                failed_pats.append(pat.pattern_id)

                        # Save updated pattern back
                        self.memory_system.add_pattern(pat)

        record = LearningRecord(
            record_id=f"lrn-{uuid.uuid4().hex[:8]}",
            timestamp=datetime.now(),
            symbol=symbol,
            learned_patterns_count=len(patterns),
            successful_patterns=successful_pats,
            failed_patterns=failed_pats,
            context_rules_discovered={
                "total_experiences_evaluated": len(experiences),
                "recommends_avoiding": failed_pats[:5]
            }
        )
        return record
