from datetime import datetime, time, timedelta, timezone
from typing import Dict, Any, Optional, Tuple
import os
import json
import logging
import math

try:
    from zoneinfo import ZoneInfo
    IRAN_TZ = ZoneInfo("Asia/Tehran")
except Exception:
    IRAN_TZ = timezone(timedelta(hours=3, minutes=30))

logger = logging.getLogger("DailyLossKillSwitch")


class DailyLossKillSwitch:
    """
    YarTrader Daily 8% Loss Protection Kill-Switch.
    Enforces:
    1. Maximum permitted daily loss = 8.0% of the account equity baseline captured at the start of the trading session.
    2. Session boundary: 01:35 Iran time -> 00:25 Iran time on following calendar day.
    3. Fail-closed on missing/invalid/non-finite equity or uninitialized baseline.
    """

    MAX_DAILY_LOSS_PCT: float = 8.0  # Strict 8% limit
    SESSION_OPEN_TIME: time = time(1, 35, 0)
    SESSION_CLOSE_TIME: time = time(0, 25, 0)

    _instance: Optional["DailyLossKillSwitch"] = None

    @classmethod
    def get_instance(cls) -> "DailyLossKillSwitch":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self, persistence_path: Optional[str] = None):
        self.persistence_path = persistence_path or os.path.join("runtime_logs", "daily_loss_kill_switch.json")
        os.makedirs(os.path.dirname(self.persistence_path), exist_ok=True)

        self.current_session_key: Optional[str] = None
        self.baseline_equity: Optional[float] = None
        self.kill_switch_active: bool = False
        self.realized_daily_loss_usd: float = 0.0
        self._persistence_state: str = "UNAVAILABLE"

        self._load_persistence()

    def set_session_baseline(self, equity: float, session_date: str) -> bool:
        """Sets active session baseline equity explicitly for a given session date string."""
        if equity is None or isinstance(equity, bool) or not isinstance(equity, (int, float)):
            return False
        eq_val = float(equity)
        if not math.isfinite(eq_val) or eq_val <= 0:
            return False
        previous = (self.current_session_key, self.baseline_equity, self.kill_switch_active)
        self.current_session_key = session_date
        self.baseline_equity = eq_val
        self.kill_switch_active = False
        if not self._save_persistence():
            self.current_session_key, self.baseline_equity, self.kill_switch_active = previous
            return False
        return True

    def get_iran_time(self, dt: Optional[datetime] = None) -> datetime:
        """Converts datetime to Iran local time (Asia/Tehran)."""
        now = dt if dt else datetime.now(timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)
        return now.astimezone(IRAN_TZ)

    def get_session_key_and_window(self, dt: Optional[datetime] = None) -> tuple[str, bool, bool]:
        """
        Determines current Iran session key (YYYY-MM-DD of session start),
        whether market is in active open session, and whether market is in transition window (00:25-01:34).
        """
        iran_dt = self.get_iran_time(dt)
        t = iran_dt.time()
        d = iran_dt.date()

        if t >= self.SESSION_OPEN_TIME:
            session_key = d.strftime("%Y-%m-%d")
            is_open_session = True
            is_transition_window = False
        elif t <= self.SESSION_CLOSE_TIME:
            yesterday = d - timedelta(days=1)
            session_key = yesterday.strftime("%Y-%m-%d")
            is_open_session = True
            is_transition_window = False
        else:
            yesterday = d - timedelta(days=1)
            session_key = yesterday.strftime("%Y-%m-%d")
            is_open_session = False
            is_transition_window = True

        return session_key, is_open_session, is_transition_window

    def update_session_state(
        self,
        current_equity: float,
        dt: Optional[datetime] = None
    ) -> None:
        """
        Updates session baseline and resets kill-switch at 01:35 session boundary.
        Captured baseline is immutable during the active session.
        Fails closed: invalid equity (None, bool, non-numeric, NaN, Inf, <= 0) cannot become baseline_equity.
        """
        if current_equity is None or isinstance(current_equity, bool) or not isinstance(current_equity, (int, float)):
            logger.warning("[DailyLossKillSwitch] update_session_state rejected invalid non-numeric/bool equity.")
            return

        eq_val = float(current_equity)
        if not math.isfinite(eq_val) or eq_val <= 0:
            logger.warning(f"[DailyLossKillSwitch] update_session_state rejected non-finite or <= 0 equity: {eq_val}")
            return

        session_key, is_open, is_trans = self.get_session_key_and_window(dt)

        if self.current_session_key != session_key:
            logger.info(f"[DailyLossKillSwitch] New session start: {session_key}. Baseline equity: ${eq_val:.2f}")
            self.current_session_key = session_key
            self.baseline_equity = eq_val
            self.kill_switch_active = False
            self.realized_daily_loss_usd = 0.0
            self._save_persistence()

    def evaluate_daily_loss(
        self,
        current_equity: Optional[Any],
        session_baseline_equity: Optional[Any] = None,
        now_utc: Optional[datetime] = None
    ) -> Tuple[bool, Optional[str], Dict[str, Any]]:
        """
        Canonical fail-closed daily loss evaluation.
        Returns Tuple[allowed: bool, rejection_reason: Optional[str], metadata: dict].
        Fails closed on missing, non-positive, or non-finite current equity.
        """
        if current_equity is None or isinstance(current_equity, bool) or not isinstance(current_equity, (int, float)):
            return False, "KILL_SWITCH_ERROR", {}

        eq_val = float(current_equity)
        if not math.isfinite(eq_val) or eq_val <= 0:
            return False, "KILL_SWITCH_ERROR", {}

        session_key, is_open, is_trans = self.get_session_key_and_window(now_utc)

        if self._persistence_state != "VALID":
            return False, "KILL_SWITCH_PERSISTENCE_UNAVAILABLE", {"session_date": self.current_session_key, "persistence_state": self._persistence_state}

        if self.current_session_key != session_key:
            return False, "KILL_SWITCH_BASELINE_UNAVAILABLE", {"session_date": self.current_session_key, "expected_session_date": session_key, "persistence_state": self._persistence_state}

        if (self.baseline_equity is None or isinstance(self.baseline_equity, bool) or not isinstance(self.baseline_equity, (int, float)) or not math.isfinite(float(self.baseline_equity)) or float(self.baseline_equity) <= 0):
            return False, "KILL_SWITCH_BASELINE_INVALID", {"session_date": self.current_session_key, "persistence_state": self._persistence_state}

        baseline = float(self.baseline_equity)
        loss_amount_usd = max(0.0, baseline - eq_val)
        loss_pct = (loss_amount_usd / baseline) * 100.0

        if loss_pct >= self.MAX_DAILY_LOSS_PCT:
            self.kill_switch_active = True
            self._save_persistence()

        meta = {
            "session_date": self.current_session_key,
            "baseline_equity": baseline,
            "current_equity": eq_val,
            "loss_pct": round(loss_pct, 2),
            "kill_switch_active": self.kill_switch_active
        }

        if self.kill_switch_active:
            return False, "DAILY_LOSS_LIMIT_REACHED", meta

        return True, None, meta

    def evaluate_entry_allowed(
        self,
        current_equity: float,
        unrealized_pnl_usd: float = 0.0,
        realized_pnl_usd: float = 0.0,
        dt: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Evaluates pre-entry daily 8% loss limit and session window bounds.
        Returns detailed status payload.
        """
        allowed, reason, meta = self.evaluate_daily_loss(current_equity, now_utc=dt)
        session_key, is_open, is_transition = self.get_session_key_and_window(dt)

        if is_transition:
            return {
                "allowed": False,
                "reason": "SESSION_TRANSITION_WINDOW",
                "kill_switch_active": self.kill_switch_active,
                "daily_loss_pct": 0.0,
                "message": "New entries blocked: Session transition window (00:25 - 01:34 Iran time)."
            }

        return {
            "allowed": allowed,
            "reason": reason,
            "kill_switch_active": self.kill_switch_active,
            "daily_loss_pct": meta.get("loss_pct", 0.0),
            "baseline_equity": meta.get("baseline_equity", current_equity),
            "current_equity": current_equity,
            "message": f"Daily loss check result: allowed={allowed}, reason={reason}"
        }

    def _save_persistence(self) -> bool:
        """Persists state to disk for crash-resistant recovery across restarts."""
        try:
            data = {
                "current_session_key": self.current_session_key,
                "baseline_equity": self.baseline_equity,
                "kill_switch_active": self.kill_switch_active,
                "realized_daily_loss_usd": self.realized_daily_loss_usd,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            with open(self.persistence_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
            self._persistence_state = "VALID"
            return True
        except Exception as e:
            self._persistence_state = "ERROR"
            logger.error(f"[DailyLossKillSwitch] Failed to save persistence: {e}")
            return False

    def _load_persistence(self) -> None:
        """Loads and validates authoritative state; invalid state remains fail-closed."""
        if not os.path.exists(self.persistence_path):
            self._persistence_state = "MISSING"
            return
        try:
            with open(self.persistence_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            session_key = data.get("current_session_key")
            baseline = data.get("baseline_equity")
            kill_active = data.get("kill_switch_active")
            realized = data.get("realized_daily_loss_usd", 0.0)
            if (not isinstance(session_key, str) or not session_key or isinstance(baseline, bool) or not isinstance(baseline, (int, float)) or not math.isfinite(float(baseline)) or float(baseline) <= 0 or not isinstance(kill_active, bool) or isinstance(realized, bool) or not isinstance(realized, (int, float)) or not math.isfinite(float(realized))):
                self._persistence_state = "MALFORMED"
                return
            self.current_session_key = session_key
            self.baseline_equity = float(baseline)
            self.kill_switch_active = kill_active
            self.realized_daily_loss_usd = float(realized)
            self._persistence_state = "VALID"
        except (OSError, ValueError, TypeError, json.JSONDecodeError) as e:
            self._persistence_state = "ERROR"
            logger.error(f"[DailyLossKillSwitch] Failed to load persistence: {e}")
