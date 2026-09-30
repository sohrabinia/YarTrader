"""Shared bridge from Backtest/Research/Signal/DEMO outcomes into the canonical Brain memory loop."""

import json
import os
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from src.Research.Brain.active_learning import ActiveLearningEngine
from src.Research.Brain.judge import JudgeBrain
from src.Research.Brain.memory import MarketMemorySystem
from src.Research.Brain.models import ExperienceMemory, SimulatedDecision


class BrainLearningBridge:
    """Single persistence-backed bridge for cross-mode learning."""

    def __init__(self, storage_dir: Optional[str] = None) -> None:
        self.memory = MarketMemorySystem(storage_dir=storage_dir)
        self.judge = JudgeBrain()
        self.active_learning = ActiveLearningEngine()
        self._pending_path = os.path.join(
            storage_dir or os.path.join("runtime_logs", "brain_memory"),
            "pending_signals.json",
        )
        os.makedirs(os.path.dirname(self._pending_path), exist_ok=True)

    def _load_pending(self) -> Dict[str, Dict[str, Any]]:
        try:
            with open(self._pending_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _save_pending(self, data: Dict[str, Dict[str, Any]]) -> None:
        tmp = self._pending_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, self._pending_path)

    def record_signal(
        self,
        signal_id: str,
        symbol: str,
        timeframe: str,
        direction: str,
        entry_price: float,
        stop_loss: float,
        take_profit: float,
        confidence: float,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Persist an actionable Signal prediction until its outcome is known."""
        if direction not in {"BUY", "SELL"}:
            return
        pending = self._load_pending()
        pending[signal_id] = {
            "signal_id": signal_id,
            "symbol": symbol.upper(),
            "timeframe": timeframe.upper(),
            "direction": direction,
            "entry_price": float(entry_price),
            "stop_loss": float(stop_loss),
            "take_profit": float(take_profit),
            "confidence": float(confidence),
            "created_at": datetime.now().isoformat(),
            "context": context or {},
        }
        self._save_pending(pending)

    def record_demo_outcome(
        self,
        decision_id: str,
        symbol: str,
        timeframe: str,
        direction: str,
        entry_price: float,
        exit_price: float,
        pnl: float,
        mfe: float = 0.0,
        mae: float = 0.0,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Evaluate a completed DEMO outcome through JudgeBrain and promote it."""
        pending = self._load_pending()
        prediction = pending.pop(decision_id, None)
        self._save_pending(pending)

        final_result = "SUCCESS" if pnl > 0 else ("FAILURE" if pnl < 0 else "NEUTRAL")
        confidence = float((prediction or {}).get("confidence", 0.5))
        stop_loss = float((prediction or {}).get("stop_loss", entry_price))
        take_profit = float((prediction or {}).get("take_profit", exit_price))

        simulated = SimulatedDecision(
            timestamp=datetime.now(), symbol=symbol.upper(), price=float(entry_price),
            decision_action=direction.upper(), confidence=confidence,
            reason="DEMO outcome evaluation through canonical Brain Learning Bridge",
            context={"timeframe": timeframe.upper(), "source": "DEMO", "decision_id": decision_id, **(context or {})},
        )
        judge_eval = self.judge.evaluate_decision_outcome(
            simulated, prediction or {},
            {"final_result": final_result, "max_favorable_excursion": float(mfe), "max_adverse_excursion": float(mae)},
        )

        exp = ExperienceMemory(
            experience_id=f"exp-DEMO-{uuid.uuid4().hex[:8]}",
            symbol=symbol.upper(), timeframe=timeframe.upper(), timestamp=datetime.now(),
            situation_signature=[float(entry_price), stop_loss, take_profit],
            decision_action=direction.upper(), outcome_result=final_result,
            lesson_feedback=judge_eval.get("learning_feedback", "DEMO outcome evaluated."),
            max_favorable_excursion=float(mfe), max_adverse_excursion=float(mae),
            meta={
                "source": "DEMO", "decision_id": decision_id, "pnl": float(pnl),
                "entry_price": float(entry_price), "exit_price": float(exit_price),
                "judge_eval": judge_eval, "is_validated": True,
                "judge_reasoning_score": judge_eval.get("reasoning_quality_score", 1.0),
                "judge_accuracy": judge_eval.get("decision_quality_score", 1.0),
            },
        )
        self.memory.add_experience(exp)
        promoted = self.memory.promote_experiences_to_patterns()
        priorities = self.active_learning.analyze_weaknesses_and_set_priorities(self.memory.get_patterns())
        consolidated = self.memory.consolidate_patterns_to_concepts(min_samples=4, min_validation_score=0.70)
        return {
            "source": "DEMO", "decision_id": decision_id, "outcome": final_result,
            "judge": judge_eval, "promoted_patterns": len(promoted),
            "active_learning_priorities": priorities[:10], "concepts_consolidated": len(consolidated),
            "memory": self.memory.get_learning_statistics(),
        }
