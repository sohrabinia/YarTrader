import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from src.Research.Brain.models import SimulatedDecision, ExperienceMemory
from src.Research.Brain.judge import JudgeBrain
from src.Research.Brain.memory import MarketMemorySystem
from src.ShadowTrading.Domain.VirtualPosition import VirtualPosition
from src.ShadowTrading.Domain.TradeState import PositionResult

logger = logging.getLogger("TradeEvaluator")

class TradeEvaluator:
    """
    Coordinates post-close virtual position evaluations.
    Invokes the independent Judge Brain and stores the output as persistent ExperienceMemory.
    """
    def __init__(self, judge: Optional[JudgeBrain] = None, memory_system: Optional[MarketMemorySystem] = None) -> None:
        self.judge = judge or JudgeBrain()
        self.memory_system = memory_system or MarketMemorySystem()

    def evaluate_and_memorize(self, position: VirtualPosition, timeframe: str = "H1") -> Dict[str, Any]:
        """
        Runs full evaluations on a closed position, triggers Judge reviews,
        and serializes the result into the standard ExperienceMemory system.
        """
        # 1. Reconstruct SimulatedDecision representing original trade intent
        decision = SimulatedDecision(
            timestamp=position.open_time,
            symbol=position.symbol,
            price=position.entry_price,
            decision_action=position.direction,
            context={
                "confidence_score": position.confidence,
                "expected_scenario": "Continuation"
            },
            evidence=position.evidence,
            reason=position.reason
        )

        # 2. Formulate execution outcomes (excursions, profit)
        # For simplicity, calculate excursions representing performance boundaries
        max_fav = abs(position.profit_loss) if position.result == PositionResult.WIN else 0.0
        max_adv = -abs(position.profit_loss) if position.result == PositionResult.LOSS else 0.0

        outcome_payload = {
            "final_result": "SUCCESS" if position.result == PositionResult.WIN else "FAILURE",
            "max_favorable_excursion": max_fav,
            "max_adverse_excursion": max_adv
        }

        # 3. Call independent Judge Brain evaluation
        judge_evaluation = self.judge.evaluate_decision_outcome(
            decision=decision,
            evidence=position.evidence,
            outcome=outcome_payload
        )

        # 4. Construct unified ExperienceMemory matching existing memory system parameters
        sig = position.evidence.get("signature", [1.0, -0.5, 0.2])
        if not isinstance(sig, list):
            sig = [1.0, -0.5, 0.2]

        exp_memory = ExperienceMemory(
            experience_id=f"exp-{position.position_id[5:] if position.position_id.startswith('vpos-') else position.position_id}",
            symbol=position.symbol,
            timeframe=timeframe,
            timestamp=datetime.now(),
            situation_signature=sig,
            decision_action=position.direction,
            outcome_result="SUCCESS" if position.result == PositionResult.WIN else "FAILURE",
            lesson_feedback=judge_evaluation.get("learning_feedback", "Evaluated closed position."),
            max_favorable_excursion=max_fav,
            max_adverse_excursion=max_adv,
            meta={
                "position_id": position.position_id,
                "confidence": position.confidence,
                "is_lucky_win": judge_evaluation.get("is_lucky_win", False),
                "is_structural_failure": judge_evaluation.get("is_structural_failure", False)
            }
        )

        # 5. Add to memory persistence
        self.memory_system.add_experience(exp_memory)
        logger.info(f"Evaluated position {position.position_id} and recorded Experience Memory.")

        return judge_evaluation

    def evaluate_demo_trade_outcome(self, journal_record: Any, timeframe: str = "H1") -> Dict[str, Any]:
        """
        Accepts a canonical production DEMO TradeJournalRecord or TradeOutcome dict directly,
        triggers JudgeBrain evaluation, records ExperienceMemory, and updates MarketMemorySystem.
        Does NOT depend on ShadowTradingEngine.
        """
        if hasattr(journal_record, "to_dict"):
            d = journal_record.to_dict()
        elif isinstance(journal_record, dict):
            d = journal_record
        else:
            d = {}

        pnl = float(d.get("pnl", 0.0))
        res_str = str(d.get("result", "BREAKEVEN")).upper()
        if pnl > 0.01:
            res_str = "WIN"
        elif pnl < -0.01:
            res_str = "LOSS"

        mfe = float(d.get("mfe", abs(pnl) if res_str == "WIN" else 0.0))
        mae = float(d.get("mae", -abs(pnl) if res_str == "LOSS" else 0.0))

        decision_id = str(d.get("decision_id", f"DEC-{uuid.uuid4().hex[:8]}"))
        symbol = str(d.get("symbol", "XAUUSD")).upper()
        direction = str(d.get("direction", "BUY")).upper()
        evidence = d.get("evidence", {}) if isinstance(d.get("evidence"), dict) else {}

        decision = SimulatedDecision(
            timestamp=datetime.now(),
            symbol=symbol,
            price=float(d.get("actual_entry", d.get("planned_entry", 2000.0))),
            decision_action=direction,
            context={
                "confidence_score": float(d.get("confidence", 50.0)),
                "expected_scenario": "Continuation"
            },
            evidence=evidence,
            reason="; ".join(d.get("reasoning", [])) if isinstance(d.get("reasoning"), list) else str(d.get("reasoning", ""))
        )

        outcome_payload = {
            "final_result": "SUCCESS" if res_str == "WIN" else ("FAILURE" if res_str == "LOSS" else "NEUTRAL"),
            "max_favorable_excursion": mfe,
            "max_adverse_excursion": mae,
            "pnl": pnl
        }

        judge_eval = self.judge.evaluate_decision_outcome(
            decision=decision,
            evidence=evidence,
            outcome=outcome_payload
        )

        sig = evidence.get("signature", [1.0, -0.5, 0.2])
        if not isinstance(sig, list):
            sig = [1.0, -0.5, 0.2]

        exp_memory = ExperienceMemory(
            experience_id=f"exp-{decision_id}",
            symbol=symbol,
            timeframe=timeframe,
            timestamp=datetime.now(),
            situation_signature=sig,
            decision_action=direction,
            outcome_result="SUCCESS" if res_str == "WIN" else ("FAILURE" if res_str == "LOSS" else "NEUTRAL"),
            lesson_feedback=judge_eval.get("learning_feedback", f"Evaluated DEMO trade outcome {res_str} (PnL=${pnl:.2f})."),
            max_favorable_excursion=mfe,
            max_adverse_excursion=mae,
            meta={
                "decision_id": decision_id,
                "confidence": float(d.get("confidence", 50.0)),
                "pnl": pnl,
                "is_lucky_win": judge_eval.get("is_lucky_win", False),
                "is_structural_failure": judge_eval.get("is_structural_failure", False)
            }
        )

        self.memory_system.add_experience(exp_memory)
        logger.info(f"[TradeEvaluator] Evaluated DEMO trade decision_id={decision_id} ({res_str}, PnL=${pnl:.2f}) and recorded Experience Memory.")
        return judge_eval
