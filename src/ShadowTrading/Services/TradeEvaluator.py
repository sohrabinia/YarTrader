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
        Does NOT invent synthetic values or route through ShadowTradingEngine.
        """
        rec_dict = journal_record.to_dict() if hasattr(journal_record, "to_dict") else dict(journal_record)

        decision_id = rec_dict.get("decision_id") or "DEC-UNAVAILABLE"
        parent_decision_id = rec_dict.get("parent_decision_id")
        symbol = (rec_dict.get("symbol") or "UNAVAILABLE").upper()
        timeframe = (rec_dict.get("timeframe") or "H1").upper()
        direction = (rec_dict.get("direction") or "UNAVAILABLE").upper()
        actual_entry = float(rec_dict.get("actual_entry", 0.0))
        actual_exit = float(rec_dict.get("actual_exit", 0.0))
        pnl = float(rec_dict.get("pnl", 0.0))
        result_str = rec_dict.get("result", "UNKNOWN")
        evidence = rec_dict.get("evidence") or {}

        # Extract situation signature if available; if unavailable use empty list
        sig = evidence.get("signature")
        if not isinstance(sig, list):
            sig = []

        decision = SimulatedDecision(
            timestamp=rec_dict.get("open_time") or datetime.now().isoformat(),
            symbol=symbol,
            price=actual_entry,
            decision_action=direction,
            context={
                "confidence_score": rec_dict.get("confidence", 0.0),
                "expected_scenario": evidence.get("expected_scenario", "UNAVAILABLE")
            },
            evidence=evidence,
            reason=",".join(rec_dict.get("reasoning", [])) if rec_dict.get("reasoning") else "Real DEMO Trade Outcome"
        )

        mfe = float(rec_dict.get("mfe", 0.0))
        mae = float(rec_dict.get("mae", 0.0))

        outcome_payload = {
            "final_result": "SUCCESS" if result_str in ["WIN", "SUCCESS"] else ("FAILURE" if result_str in ["LOSS", "FAILURE"] else "BREAKEVEN"),
            "realized_pnl": pnl,
            "actual_entry": actual_entry,
            "actual_exit": actual_exit,
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
            symbol=symbol,
            timeframe=timeframe,
            timestamp=datetime.now(),
            situation_signature=sig,
            decision_action=direction,
            outcome_result="SUCCESS" if result_str in ["WIN", "SUCCESS"] else ("FAILURE" if result_str in ["LOSS", "FAILURE"] else "BREAKEVEN"),
            lesson_feedback=judge_evaluation.get("learning_feedback", f"Evaluated DEMO trade {rec_dict.get('trade_id')}."),
            max_favorable_excursion=mfe,
            max_adverse_excursion=mae,
            meta={
                "trade_id": rec_dict.get("trade_id"),
                "decision_id": decision_id,
                "parent_decision_id": parent_decision_id,
                "confidence": rec_dict.get("confidence", 0.0),
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

        sig = evidence.get("signature", [])
        if not isinstance(sig, list):
            sig = []

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
                "confidence": float(d.get("confidence", 0.0)),
                "pnl": pnl,
                "is_lucky_win": judge_eval.get("is_lucky_win", False),
                "is_structural_failure": judge_eval.get("is_structural_failure", False)
            }
        )

        self.memory_system.add_experience(exp_memory)
        logger.info(f"[TradeEvaluator] Evaluated DEMO trade decision_id={decision_id} ({res_str}, PnL=${pnl:.2f}) and recorded Experience Memory.")
        return judge_eval
