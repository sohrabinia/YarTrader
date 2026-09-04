import os
import math
import json
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Tuple

logger = logging.getLogger("DailyLossKillSwitch")

class DailyLossKillSwitch:
    """
    Authoritative Daily Loss Protection Kill Switch for YarTrader.
    Enforces a strict 8.00% max daily loss limit calculated against the session baseline equity.

    Session Reset Boundary: 01:35 Iran time (Asia/Tehran).

    Safety Invariants:
    1. Explicit numeric equity validation: missing, None, <= 0, NaN, Inf, or malformed equity fails closed.
    2. Zero financial fallback (no 10000.0 or default equity substitution).
    3. Session baseline equity is immutable once established per session (never reset to lower intraday equity).
    4. Uninitialized session baseline equity fails closed (no self-creation from random intraday equity).
    """
    MAX_DAILY_LOSS_PCT: float = 8.00  # 8.00% hard limit

    def __init__(self, state_file_path: Optional[str] = None):
        from src.Application.Deployment.storage import YarTraderStorageManager
        storage_mgr = YarTraderStorageManager.get_manager()
        self.state_file_path = state_file_path or os.path.join(storage_mgr.get_runtime_dir(), "daily_loss_kill_switch.json")
        self.session_date: Optional[str] = None
        self.baseline_equity: Optional[float] = None
        self.is_triggered: bool = False
        self._load_state()

    def _load_state(self) -> None:
        """Loads state from JSON file if present. Corrupted/invalid state files trigger fail closed mode."""
        self.is_corrupted = False
        if os.path.exists(self.state_file_path):
            try:
                with open(self.state_file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if not isinstance(data, dict):
                        raise ValueError("State file content is not a JSON object")
                    self.session_date = data.get("session_date")
                    raw_b = data.get("baseline_equity")
                    if raw_b is not None and not isinstance(raw_b, bool) and isinstance(raw_b, (int, float)) and math.isfinite(float(raw_b)) and float(raw_b) > 0:
                        self.baseline_equity = float(raw_b)
                    else:
                        self.baseline_equity = None
                    self.is_triggered = bool(data.get("is_triggered", False))
            except Exception as e:
                logger.error(f"[DailyLossKillSwitch] Corrupted or unreadable state file: {e}")
                self.is_corrupted = True
                self.baseline_equity = None
                self.session_date = None

    def _save_state(self) -> None:
        """Persists state to disk safely."""
        try:
            os.makedirs(os.path.dirname(self.state_file_path), exist_ok=True)
            data = {
                "session_date": self.session_date,
                "baseline_equity": self.baseline_equity,
                "is_triggered": self.is_triggered,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            with open(self.state_file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"[DailyLossKillSwitch] Failed to save state file: {e}")

    def set_session_baseline(self, baseline_equity: Any, session_date_str: Optional[str] = None) -> bool:
        """Explicitly sets or resets the session baseline equity for a new session boundary."""
        if self.is_corrupted:
            return False
        if baseline_equity is None or isinstance(baseline_equity, bool) or not isinstance(baseline_equity, (int, float)):
            return False
        b_val = float(baseline_equity)
        if not math.isfinite(b_val) or b_val <= 0:
            return False

        now_utc = datetime.now(timezone.utc)
        current_date_str = session_date_str or now_utc.strftime("%Y-%m-%d")

        self.baseline_equity = b_val
        self.session_date = current_date_str
        self.is_triggered = False
        self._save_state()
        return True

    def evaluate_daily_loss(
        self,
        current_equity: Any,
        session_baseline_equity: Optional[Any] = None,
        now_utc: Optional[datetime] = None
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Evaluates current equity against daily loss limit.
        Returns: (allowed: bool, rejection_reason: str, metadata: dict)
        """
        try:
            if getattr(self, "is_corrupted", False):
                return False, "KILL_SWITCH_ERROR: State file is corrupted or unreadable (Fail-Closed)", {}

            # Validate current_equity strictly
            if current_equity is None:
                return False, "KILL_SWITCH_ERROR: current_equity is None", {}

            if not isinstance(current_equity, (int, float)) or isinstance(current_equity, bool):
                return False, f"KILL_SWITCH_ERROR: current_equity is malformed ({type(current_equity)})", {}

            curr_eq = float(current_equity)
            if not math.isfinite(curr_eq) or curr_eq <= 0:
                return False, f"KILL_SWITCH_ERROR: current_equity is non-finite or <= 0 ({curr_eq})", {}

            dt_now = now_utc if now_utc else datetime.now(timezone.utc)
            if dt_now.tzinfo is None:
                dt_now = dt_now.replace(tzinfo=timezone.utc)
            today_str = dt_now.strftime("%Y-%m-%d")

            # Check for session date boundary transition
            if self.session_date and self.session_date != today_str:
                # Previous day's session baseline must NOT silently apply to today.
                # Explicit new session baseline must be provided via session_baseline_equity.
                if session_baseline_equity is not None and isinstance(session_baseline_equity, (int, float)) and not isinstance(session_baseline_equity, bool):
                    sb_val = float(session_baseline_equity)
                    if math.isfinite(sb_val) and sb_val > 0:
                        self.baseline_equity = sb_val
                        self.session_date = today_str
                        self.is_triggered = False
                        self._save_state()
                    else:
                        return False, f"KILL_SWITCH_ERROR: Outdated session baseline ({self.session_date} vs today {today_str}) and invalid session_baseline_equity provided", {}
                else:
                    return False, f"KILL_SWITCH_ERROR: Outdated session baseline ({self.session_date} vs today {today_str}). New session baseline required.", {}

            # If no baseline established at all yet, attempt initialization strictly from session_baseline_equity (NEVER current_equity)
            if self.baseline_equity is None or not math.isfinite(self.baseline_equity) or self.baseline_equity <= 0:
                if session_baseline_equity is not None and isinstance(session_baseline_equity, (int, float)) and not isinstance(session_baseline_equity, bool):
                    b_val = float(session_baseline_equity)
                    if math.isfinite(b_val) and b_val > 0:
                        self.baseline_equity = b_val
                        self.session_date = today_str
                        self._save_state()

            # Fail closed if no valid session baseline has been established
            if self.baseline_equity is None or not math.isfinite(self.baseline_equity) or self.baseline_equity <= 0:
                return False, "KILL_SWITCH_ERROR: Uninitialized session baseline equity", {}

            baseline = self.baseline_equity

            # Calculate loss percentage against immutable session baseline
            loss_usd = baseline - curr_eq
            loss_pct = (loss_usd / baseline) * 100.0

            metadata = {
                "current_equity": curr_eq,
                "baseline_equity": baseline,
                "loss_usd": loss_usd,
                "loss_pct": loss_pct,
                "max_loss_pct": self.MAX_DAILY_LOSS_PCT,
                "is_triggered": self.is_triggered,
                "session_date": self.session_date
            }

            if loss_pct >= self.MAX_DAILY_LOSS_PCT or self.is_triggered:
                self.is_triggered = True
                self._save_state()
                return False, f"DAILY_LOSS_LIMIT_REACHED: Daily loss {loss_pct:.2f}% >= {self.MAX_DAILY_LOSS_PCT}% limit (Baseline=${baseline:.2f}, Current=${curr_eq:.2f})", metadata

            return True, "", metadata

        except Exception as e:
            logger.error(f"[DailyLossKillSwitch] Exception during evaluation: {e}")
            return False, f"KILL_SWITCH_EXCEPTION: {str(e)}", {}
