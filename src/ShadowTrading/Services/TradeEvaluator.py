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
    Coordinates post-close virtual position evaluations and real MT5 DEMO trade outcome evaluations.
    Invokes the independent Judge Brain and stores the output as persistent ExperienceMemory.
    """
    _instance: Optional["TradeEvaluator"] = None

    @classmethod
    def get_instance(cls) -> "TradeEvaluator":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self, judge: Optional[JudgeBrain] = None, memory_system: Optional[MarketMemorySystem] = None) -> None:
        self.judge = judge or JudgeBrain()
        self.memory_system = memory_system or MarketMemorySystem()

    def evaluate_demo_trade_outcome(self, journal_record: Any) -> Dict[str, Any]:
        """
        Evaluates a real MT5 DEMO closed trade recorded in TradeJournalRecord.
        Passes authoritative trade outcomes to JudgeBrain and registers ExperienceMemory into MarketMemorySystem.
        Does NOT invent synthetic values, fabricated IDs, or route through ShadowTradingEngine.
        Returns INSUFFICIENT_EVIDENCE when required broker facts are missing or incomplete.
        """
        rec_dict = journal_record.to_dict() if hasattr(journal_record, "to_dict") else (dict(journal_record) if isinstance(journal_record, dict) else {})

        decision_id = rec_dict.get("decision_id")
        parent_decision_id = rec_dict.get("parent_decision_id")
        symbol = rec_dict.get("symbol")
        timeframe = rec_dict.get("timeframe", "H1")
        direction = rec_dict.get("direction")
        actual_entry = rec_dict.get("actual_entry")
        actual_exit = rec_dict.get("actual_exit")
        pnl = rec_dict.get("pnl")
        result_str = rec_dict.get("result")
        evidence = rec_dict.get("evidence") if isinstance(rec_dict.get("evidence"), dict) else {}

        # Strict Fail-Closed / Insufficient Evidence Gate:
        # If mandatory broker trade facts are missing, evaluate as INSUFFICIENT_EVIDENCE
        if not decision_id or not symbol or not direction or actual_entry is None or actual_exit is None or pnl is None or result_str in [None, "UNKNOWN", "PENDING"]:
            logger.warning(f"[TradeEvaluator] Trade outcome evaluation aborted due to missing authoritative broker facts (decision_id={decision_id}, symbol={symbol}, pnl={pnl}, result={result_str}).")
            return {
                "evaluation": "INSUFFICIENT_EVIDENCE",
                "confidence_adjustment": 0.0,
                "learning_feedback": f"Trade outcome evaluation skipped: Missing authoritative broker facts (decision_id={decision_id}, symbol={symbol}).",
                "is_lucky_win": False,
                "is_structural_failure": False,
                "status": "INSUFFICIENT_EVIDENCE"
            }

        symbol_str = str(symbol).upper()
        direction_str = str(direction).upper()
        timeframe_str = str(timeframe).upper()
        actual_entry_f = float(actual_entry)
        actual_exit_f = float(actual_exit)
        pnl_f = float(pnl)

        # Extract situation signature if available; if unavailable use empty list
        sig = evidence.get("signature")
        if not isinstance(sig, list):
            sig = []

        decision = SimulatedDecision(
            timestamp=rec_dict.get("open_time") or datetime.now().isoformat(),
            symbol=symbol_str,
            price=actual_entry_f,
            decision_action=direction_str,
            context={
                "confidence_score": float(rec_dict.get("confidence", 0.0)),
                "expected_scenario": evidence.get("expected_scenario", "UNAVAILABLE")
            },
            evidence=evidence,
            reason=",".join(rec_dict.get("reasoning", [])) if isinstance(rec_dict.get("reasoning"), list) else str(rec_dict.get("reasoning", ""))
        )

        mfe = float(rec_dict.get("mfe", 0.0))
        mae = float(rec_dict.get("mae", 0.0))

        outcome_payload = {
            "final_result": "SUCCESS" if result_str in ["WIN", "SUCCESS"] else ("FAILURE" if result_str in ["LOSS", "FAILURE"] else "BREAKEVEN"),
            "realized_pnl": pnl_f,
            "actual_entry": actual_entry_f,
            "actual_exit": actual_exit_f,
            "max_favorable_excursion": mfe,
            "max_adverse_excursion": mae,
            "exit_reason": rec_dict.get("exit_reason", "UNAVAILABLE")
        }

        judge_evaluation = self.judge.evaluate_decision_outcome(
            decision=decision,
            evidence=evidence,
            outcome=outcome_payload
        )

        exp_id = f"exp-{rec_dict.get('trade_id', decision_id)}"
        exp_memory = ExperienceMemory(
            experience_id=exp_id,
            symbol=symbol_str,
            timeframe=timeframe_str,
            timestamp=datetime.now(),
            situation_signature=sig,
            decision_action=direction_str,
            outcome_result="SUCCESS" if result_str in ["WIN", "SUCCESS"] else ("FAILURE" if result_str in ["LOSS", "FAILURE"] else "BREAKEVEN"),
            lesson_feedback=judge_evaluation.get("learning_feedback", f"Evaluated DEMO trade {rec_dict.get('trade_id')}."),
            max_favorable_excursion=mfe,
            max_adverse_excursion=mae,
            meta={
                "trade_id": rec_dict.get("trade_id"),
                "decision_id": decision_id,
                "parent_decision_id": parent_decision_id,
                "confidence": float(rec_dict.get("confidence", 0.0)),
                "is_lucky_win": judge_evaluation.get("is_lucky_win", False),
                "is_structural_failure": judge_evaluation.get("is_structural_failure", False)
            }
        )

        self.memory_system.add_experience(exp_memory)
        logger.info(f"[TradeEvaluator] Evaluated DEMO trade {rec_dict.get('trade_id')} (decision_id={decision_id}) and recorded Experience Memory.")

        return judge_evaluation

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
                "expected_scenario": position.evidence.get("expected_scenario", "UNAVAILABLE") if position.evidence else "UNAVAILABLE"
            },
            evidence=position.evidence or {},
            reason=position.reason or ""
        )

        # 2. Formulate execution outcomes (excursions, profit)
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
            evidence=position.evidence or {},
            outcome=outcome_payload
        )

        # 4. Construct unified ExperienceMemory matching existing memory system parameters
        sig = position.evidence.get("signature", []) if position.evidence else []
        if not isinstance(sig, list):
            sig = []

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
