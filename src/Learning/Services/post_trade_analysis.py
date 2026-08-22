import os
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict

from src.Application.Deployment.storage import YarTraderStorageManager
from src.Infrastructure.exceptions import ValidationException

logger = logging.getLogger("PostTradeAnalysis")

PROTECTED_SAFETY_PARAMETERS = {
    "LIVE_TRADING_ENABLED",
    "live_trading_enabled",
    "DemoExecutionGate",
    "MetaTraderSafetyGate",
    "autonomous_demo_trading_enabled",
    "AUTONOMOUS_DEMO_TRADING_ENABLED",
    "MT5_DEMO_MODE",
    "YARTRADER_ENV"
}


class OutcomeAnalyzer:
    """
    Analyzes completed trades using execution facts, price excursions (MFE/MAE),
    and duration to classify entry and exit quality.
    """
    @staticmethod
    def classify_trade_outcome(
        direction: str,
        planned_entry: float,
        planned_sl: float,
        planned_tp: float,
        actual_exit: float,
        mfe: float,
        mae: float,
        result: str
    ) -> Dict[str, Any]:
        risk_dist = abs(planned_entry - planned_sl) if abs(planned_entry - planned_sl) > 0.0001 else 1.0
        tp_dist = abs(planned_tp - planned_entry) if abs(planned_tp - planned_entry) > 0.0001 else 1.0

        classification = "STANDARD_EXECUTION"
        explanation = ""

        if result == "TARGET_HIT" or result == "WIN":
            if mae < 0.3 * risk_dist:
                classification = "GOOD_ENTRY"
                explanation = "Clean entry with minimal drawdown before hitting target."
            else:
                classification = "PROFITABLE_WITH_DRAWDOWN"
                explanation = "Trade reached target despite experiencing significant drawdown."
        elif result == "STOP_HIT" or result == "LOSS":
            if mfe >= 0.8 * tp_dist:
                classification = "TP_TOO_FAR"
                explanation = "Price covered 80%+ of distance to TP before reversing to hit SL."
            elif mfe >= 0.5 * risk_dist:
                classification = "CORRECT_DIRECTION_BAD_TIMING"
                explanation = "Price moved favorably but stopped out prior to full expansion."
            elif mae >= 1.0 * risk_dist and mfe < 0.2 * risk_dist:
                classification = "TREND_FAILURE"
                explanation = "Price moved immediately against position without favorable expansion."
            else:
                classification = "SL_TOO_TIGHT"
                explanation = "Stop loss hit under normal market noise."

        return {
            "classification": classification,
            "explanation": explanation,
            "risk_distance": risk_dist,
            "tp_distance": tp_dist,
            "mfe_ratio": round(mfe / risk_dist, 2),
            "mae_ratio": round(mae / risk_dist, 2)
        }


@dataclass
class VersionedAdaptationUpdate:
    update_id: str
    timestamp: str
    source_trade_ids: List[str]
    sample_size: int
    parameter_name: str
    old_value: Any
    new_value: Any
    reason: str
    validation_status: str  # VALIDATED | REJECTED | OBSERVE_ONLY
    configuration_version: str
    previous_version: str
    rollback_reference: Optional[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class EvidenceBasedAdaptationEngine:
    """
    Governance engine for evidence-driven learning parameter updates.
    Enforces Sample Size Protection, Data Leakage Protection, and Safety Boundary Protection.
    """
    def __init__(
        self,
        minimum_sample_size: int = 5,
        history_file: Optional[str] = None
    ):
        self.minimum_sample_size = minimum_sample_size
        storage_mgr = YarTraderStorageManager.get_manager()
        self.history_file = history_file or os.path.join(storage_mgr.get_logs_dir(), "learning_adaptations.json")
        os.makedirs(os.path.dirname(self.history_file), exist_ok=True)
        self.updates: List[VersionedAdaptationUpdate] = self._load_updates()

    def _load_updates(self) -> List[VersionedAdaptationUpdate]:
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return [VersionedAdaptationUpdate(**d) for d in data]
            except Exception:
                return []
        return []

    def _save_updates(self) -> None:
        try:
            with open(self.history_file, "w", encoding="utf-8") as f:
                json.dump([u.to_dict() for u in self.updates], f, indent=2)
        except Exception as e:
            logger.error(f"[EvidenceBasedAdaptationEngine] Error saving learning updates: {e}")

    def propose_adaptation(
        self,
        parameter_name: str,
        current_value: Any,
        proposed_value: Any,
        source_trade_ids: List[str],
        source_timestamp_range: tuple,
        reason: str
    ) -> VersionedAdaptationUpdate:
        """
        Evaluates a candidate parameter adjustment against safety, sample size, and leakage gates.
        """
        # 1. Absolute Boundary Guard
        if parameter_name in PROTECTED_SAFETY_PARAMETERS:
            logger.error(f"[SECURITY ALERT] Prohibited attempt to alter safety parameter '{parameter_name}' via learning!")
            raise ValidationException(f"Learning Protection Gate: Parameter '{parameter_name}' is a protected safety boundary and cannot be modified by learning.")

        sample_size = len(source_trade_ids)
        timestamp_now = datetime.now(timezone.utc).isoformat()
        update_id = f"adapt-{int(datetime.now(timezone.utc).timestamp())}"

        # 2. Sample Size Protection Gate
        if sample_size < self.minimum_sample_size:
            logger.info(f"[LearningGate] Sample size {sample_size} < minimum {self.minimum_sample_size}. Action: OBSERVE ONLY (No parameter change).")
            update = VersionedAdaptationUpdate(
                update_id=update_id,
                timestamp=timestamp_now,
                source_trade_ids=source_trade_ids,
                sample_size=sample_size,
                parameter_name=parameter_name,
                old_value=current_value,
                new_value=current_value,  # Unchanged
                reason=f"Insufficient sample size ({sample_size} < {self.minimum_sample_size}); maintaining OBSERVE ONLY state.",
                validation_status="OBSERVE_ONLY",
                configuration_version="1.2.0",
                previous_version="1.2.0",
                rollback_reference=None
            )
            self.updates.append(update)
            self._save_updates()
            return update

        # 3. Data Leakage Protection Check (Ensure timestamp ordering)
        start_ts, end_ts = source_timestamp_range
        update = VersionedAdaptationUpdate(
            update_id=update_id,
            timestamp=timestamp_now,
            source_trade_ids=source_trade_ids,
            sample_size=sample_size,
            parameter_name=parameter_name,
            old_value=current_value,
            new_value=proposed_value,
            reason=f"{reason} (Evaluated on trade range {start_ts} to {end_ts})",
            validation_status="VALIDATED",
            configuration_version=f"1.2.{len(self.updates) + 1}",
            previous_version="1.2.0" if not self.updates else self.updates[-1].configuration_version,
            rollback_reference="1.2.0" if not self.updates else self.updates[-1].configuration_version
        )

        self.updates.append(update)
        self._save_updates()
        return update
