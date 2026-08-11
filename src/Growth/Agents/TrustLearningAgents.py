import re
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List

logger = logging.getLogger("TrustLearningAgents")

class TrustComplianceAgent:
    """
    Trust & Compliance Agent acts as a hard system gate scanning and rejecting non-compliant content
    (unverified claims, profit guarantees, signal selling tone, direct financial advice).
    """

    def __init__(self, agent_id: str = "agent-trust-compliance"):
        self.agent_id = agent_id
        # Define forbidden patterns / regular expressions
        self.forbidden_rules = [
            (r"(guaranteed?|promise|100%|always)\s+(profit|win|gain|return|yield)", "Profit guarantees or win rate promises are strictly prohibited."),
            (r"(must|should|buy|sell|trade)\s+(now|immediately|this\s+asset)", "Direct buy/sell trading signals or execution instructions are prohibited."),
            (r"(financial|investment)\s+advice", "Direct financial or investment advice statements are prohibited."),
            (r"get\s+rich|double\s+your", "Get rich quick schemes or unverified hype statements are prohibited.")
        ]

    def scan_content(self, body_text: str) -> Dict[str, Any]:
        violations = []
        for pattern, explanation in self.forbidden_rules:
            if re.search(pattern, body_text.lower()):
                violations.append(explanation)

        is_compliant = len(violations) == 0
        return {
            "is_compliant": is_compliant,
            "violations": violations,
            "scanned_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "action": "APPROVED" if is_compliant else "REJECTED_BY_COMPLIANCE_GATE"
        }


class MarketFeedbackLearningAgent:
    """
    Market Feedback Learning Agent compares paper trading decisions with actual market outcome.
    Performs error analysis and feeds back learnings to Core MarketMemorySystem to prevent weight inflation.
    """

    def __init__(self, memory_system: Any, agent_id: str = "agent-feedback-learning"):
        self.agent_id = agent_id
        self.memory_system = memory_system
        self.error_logs_db: List[Dict[str, Any]] = []

    def process_outcome_feedback(self, trade_record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Processes trade result, determines deviation, and logs update insights in the MarketMemorySystem.
        """
        outcome = trade_record.get("outcome", "LOSS").upper()
        symbol = trade_record.get("asset", "XAUUSD")

        insight_summary = ""
        action_taken = "NO_ACTION_REQUIRED"

        if outcome == "LOSS":
            # Conduct error analysis
            reasoning = trade_record.get("reasoning", "")
            deviation_factor = abs(trade_record.get("exit_price", 0.0) - trade_record.get("stop_loss", 0.0))

            insight_summary = (
                f"Error analysis for {symbol} trade {trade_record.get('trade_id')}. "
                f"Predicted direction encountered timing lag or consolidation. "
                f"Deviation factor: {deviation_factor}."
            )
            # Log update into memory system
            if hasattr(self.memory_system, "add_event"):
                try:
                    from src.Research.Brain.models import MarketEvent
                    evt = MarketEvent(
                        symbol=symbol,
                        timeframe="H1",
                        start_time=datetime.now(timezone.utc),
                        end_time=datetime.now(timezone.utc),
                        price_change=-deviation_factor,
                        duration_candles=1,
                        previous_sequence_len=0,
                        reaction_type="LOSS_FEEDBACK",
                        reaction_magnitude=deviation_factor,
                        meta={
                            "trade_id": trade_record.get("trade_id"),
                            "insight": insight_summary,
                            "status": "EXPERIENCE_REFINED"
                        }
                    )
                    self.memory_system.add_event(evt)
                    action_taken = "MEMORY_EVENT_RECORDED"
                except Exception as e:
                    logger.exception("EXCEPTION during add_event call")
            elif hasattr(self.memory_system, "record_event"):
                self.memory_system.record_event(
                    event_type="LEARNING_FEEDBACK_OUTCOME",
                    details={
                        "symbol": symbol,
                        "trade_id": trade_record.get("trade_id"),
                        "insight": insight_summary,
                        "status": "EXPERIENCE_REFINED"
                    }
                )
                action_taken = "MEMORY_EVENT_RECORDED"

            self.error_logs_db.append({
                "trade_id": trade_record.get("trade_id"),
                "symbol": symbol,
                "error_insight": insight_summary,
                "logged_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            })
        else:
            insight_summary = f"Successful prediction on {symbol}. Pattern confirmed."

        return {
            "agent_id": self.agent_id,
            "outcome_evaluated": outcome,
            "insight": insight_summary,
            "action_taken": action_taken,
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        }
