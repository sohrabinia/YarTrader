"""Shared bridge from Backtest/Research/Signal/DEMO outcomes into the canonical Brain memory loop."""

import json
import math
import os
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from src.Research.Brain.active_learning import ActiveLearningEngine
from src.Research.Brain.judge import JudgeBrain
from src.Research.Brain.memory import MarketMemorySystem
from src.Research.Brain.models import ExperienceMemory, SimulatedDecision


class BrainLearningBridge:
    """Persistence-backed bridge with strict per-symbol learning isolation."""

    def __init__(self, storage_dir: Optional[str] = None) -> None:
        self.storage_dir = os.path.abspath(storage_dir or os.path.join("runtime_logs", "brain_memory"))
        self.memories: Dict[str, MarketMemorySystem] = {}
        self.active_learners: Dict[str, ActiveLearningEngine] = {}
        self.judge = JudgeBrain()
        self._pending_path = os.path.join(self.storage_dir, "pending_signals.json")
        os.makedirs(os.path.dirname(self._pending_path), exist_ok=True)

    def get_market_memory(self, symbol: str) -> MarketMemorySystem:
        """Return durable memory scoped to one normalized market symbol."""
        key = str(symbol).strip().upper()
        if not key or any(ch in key for ch in ("/", "\\", "..")):
            raise ValueError("A valid symbol is required for isolated learning memory.")
        if key not in self.memories:
            self.memories[key] = MarketMemorySystem(
                storage_dir=os.path.join(self.storage_dir, f"symbol_{key}")
            )
        return self.memories[key]

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
        """Persist only geometrically valid, finite actionable predictions."""
        if direction not in {"BUY", "SELL"}:
            return
        try:
            entry = float(entry_price)
            stop = float(stop_loss)
            target = float(take_profit)
            conf = float(confidence)
        except (TypeError, ValueError, OverflowError):
            return
        if (not all(math.isfinite(v) for v in (entry, stop, target, conf))
                or min(entry, stop, target) <= 0 or not 0.0 <= conf <= 1.0):
            return
        if direction == "BUY" and not stop < entry < target:
            return
        if direction == "SELL" and not target < entry < stop:
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
        if not isinstance(decision_id, str) or not decision_id.strip():
            raise ValueError("A stable decision_id is required for DEMO outcome attribution.")
        numeric_outcome = {}
        for field_name, value in (("entry_price", entry_price), ("exit_price", exit_price),
                                  ("pnl", pnl), ("mfe", mfe), ("mae", mae)):
            if isinstance(value, bool):
                raise ValueError(f"Invalid DEMO outcome field: {field_name}")
            try:
                numeric_value = float(value)
            except (TypeError, ValueError, OverflowError) as exc:
                raise ValueError(f"Invalid DEMO outcome field: {field_name}") from exc
            if not math.isfinite(numeric_value):
                raise ValueError(f"Non-finite DEMO outcome field: {field_name}")
            numeric_outcome[field_name] = numeric_value
        if numeric_outcome["entry_price"] <= 0 or numeric_outcome["exit_price"] <= 0:
            raise ValueError("DEMO outcome entry and exit prices must be positive.")
        entry_price = numeric_outcome["entry_price"]
        exit_price = numeric_outcome["exit_price"]
        pnl = numeric_outcome["pnl"]
        mfe = numeric_outcome["mfe"]
        mae = numeric_outcome["mae"]
        pending = self._load_pending()
        prediction = pending.get(decision_id)
        outcome_context = dict(context or {})
        # The autonomous worker keys closed positions differently from pending signal IDs.
        # Recover only from its persisted submitted setup, and validate its symbol/direction/SL/TP.
        if prediction is None:
            snapshot = outcome_context.get("setup_snapshot")
            try:
                snapshot_symbol = str(snapshot.get("symbol", "")).upper() if isinstance(snapshot, dict) else ""
                snapshot_direction = str(snapshot.get("direction", "")).upper() if isinstance(snapshot, dict) else ""
                snapshot_entry = float(snapshot.get("entry", snapshot.get("entry_price", entry_price))) if isinstance(snapshot, dict) else float("nan")
                snapshot_stop = float(snapshot.get("stop_loss", outcome_context.get("stop_loss"))) if isinstance(snapshot, dict) else float("nan")
                snapshot_target = float(snapshot.get("take_profit", outcome_context.get("take_profit"))) if isinstance(snapshot, dict) else float("nan")
                geometry_valid = (
                    (direction.upper() == "BUY" and snapshot_stop < snapshot_entry < snapshot_target)
                    or (direction.upper() == "SELL" and snapshot_target < snapshot_entry < snapshot_stop)
                )
                snapshot_valid = (
                    snapshot_symbol == str(symbol).upper()
                    and snapshot_direction == direction.upper()
                    and all(math.isfinite(v) and v > 0 for v in (snapshot_entry, snapshot_stop, snapshot_target))
                    and geometry_valid
                )
            except (TypeError, ValueError, OverflowError):
                snapshot_valid = False
            if snapshot_valid:
                prediction = {
                    "symbol": snapshot_symbol, "timeframe": timeframe.upper(),
                    "direction": snapshot_direction, "entry_price": snapshot_entry,
                    "stop_loss": snapshot_stop, "take_profit": snapshot_target,
                    "confidence": snapshot.get("confidence", 0.5),
                    "confidence_source": "recorded_setup_or_neutral_default",
                }
            else:
                return {
                    "source": "DEMO", "decision_id": decision_id, "status": "UNVALIDATED",
                    "reason": "No persisted prediction or valid submitted setup exists; learning was skipped.",
                }
        # Do not consume or learn from a signal under a different symbol.
        if str(prediction.get("symbol", "")).upper() != str(symbol).upper():
            raise ValueError(
                f"Signal symbol mismatch for {decision_id}: "
                f"expected {prediction.get('symbol')}, received {symbol}"
            )
        memory = self.get_market_memory(symbol)
        # Durable deduplication also covers outcomes re-read after the worker's bounded
        # in-memory processed-ID cache is truncated or the process restarts.
        existing = next((
            exp for exp in memory.experiences.values()
            if exp.meta.get("source") == "DEMO"
            and str(exp.meta.get("decision_id", "")) == decision_id
        ), None)
        if existing is not None:
            pending.pop(decision_id, None)
            self._save_pending(pending)
            return {
                "source": "DEMO", "decision_id": decision_id, "status": "DUPLICATE_IGNORED",
                "outcome": existing.outcome_result, "symbol": str(symbol).upper(),
            }
        pending.pop(decision_id, None)
        self._save_pending(pending)
        active_learning = self.active_learners.setdefault(str(symbol).upper(), ActiveLearningEngine())

        final_result = "SUCCESS" if pnl > 0 else ("FAILURE" if pnl < 0 else "NEUTRAL")
        confidence = float((prediction or {}).get("confidence", 0.5))
        outcome_context = dict(context or {})
        stop_value = (prediction or {}).get("stop_loss")
        if stop_value is None:
            stop_value = outcome_context.get("stop_loss")
        if stop_value is None:
            stop_value = entry_price
        target_value = (prediction or {}).get("take_profit")
        if target_value is None:
            target_value = outcome_context.get("take_profit")
        if target_value is None:
            target_value = exit_price
        stop_loss = float(stop_value)
        take_profit = float(target_value)

        simulated = SimulatedDecision(
            timestamp=datetime.now(), symbol=symbol.upper(), price=float(entry_price),
            decision_action=direction.upper(), confidence=confidence,
            reason="DEMO outcome evaluation through canonical Brain Learning Bridge",
            context={"timeframe": timeframe.upper(), "source": "DEMO", "decision_id": decision_id, **outcome_context},
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
        memory.add_experience(exp)
        promoted = memory.promote_experiences_to_patterns()
        priorities = active_learning.analyze_weaknesses_and_set_priorities(memory.get_patterns())
        consolidated = memory.consolidate_patterns_to_concepts(min_samples=4, min_validation_score=0.70)
        return {
            "source": "DEMO", "decision_id": decision_id, "outcome": final_result,
            "judge": judge_eval, "promoted_patterns": len(promoted),
            "active_learning_priorities": priorities[:10], "concepts_consolidated": len(consolidated),
            "symbol": str(symbol).upper(),
            "memory_scope": os.path.basename(memory._storage_dir),
            "memory": memory.get_learning_statistics(),
        }
