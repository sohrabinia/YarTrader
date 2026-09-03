from datetime import datetime, time, timedelta, timezone
from typing import Dict, Any, Optional
import os
import json
import logging

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
    1. Maximum permitted daily loss = 8% of the account equity baseline captured at the start of the trading session.
    2. Session boundary: 01:35 Iran time -> 00:25 Iran time on following calendar day.
       - 01:35 Iran time: Session opens -> capture daily baseline equity, reset kill-switch state.
       - 00:00 - 00:25 Iran time: Belongs to previous trading session.
       - 00:25 - 01:34 Iran time: Session transition window -> no new entries permitted.
       - 01:35 Iran time: Next session starts -> new session day key, capture fresh baseline.
    3. Fail-closed, session-aware, idempotent, persistent across process restarts.
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

        self._load_persistence()

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

        # Window A: 01:35:00 to 23:59:59.999 -> Session opened today at 01:35
        if t >= self.SESSION_OPEN_TIME:
            session_key = d.strftime("%Y-%m-%d")
            is_open_session = True
            is_transition_window = False
        # Window B: 00:00:00 to 00:25:00 -> Belongs to session that opened yesterday at 01:35
        elif t <= self.SESSION_CLOSE_TIME:
            yesterday = d - timedelta(days=1)
            session_key = yesterday.strftime("%Y-%m-%d")
            is_open_session = True
            is_transition_window = False
        # Window C: 00:25:01 to 01:34:59 -> Session transition window (No new entries allowed)
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
        Captured baseline is immutable during the session and does not continuously move.
        """
        session_key, is_open, is_trans = self.get_session_key_and_window(dt)

        if self.current_session_key != session_key:
            # New session boundary reached (e.g. 01:35 Iran time)
            logger.info(f"[DailyLossKillSwitch] New session start: {session_key}. Baseline equity: ${current_equity:.2f}")
            self.current_session_key = session_key
            self.baseline_equity = current_equity
            self.kill_switch_active = False
            self.realized_daily_loss_usd = 0.0
            self._save_persistence()

    def evaluate_entry_allowed(
        self,
        current_equity: float,
        unrealized_pnl_usd: float = 0.0,
        realized_pnl_usd: float = 0.0,
        dt: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Evaluates pre-entry daily 8% loss limit and session window bounds.
        Returns detailed status payload including baseline, loss %, kill-switch active, and decision.
        """
        self.update_session_state(current_equity, dt)

        session_key, is_open, is_transition = self.get_session_key_and_window(dt)

        if is_transition:
            return {
                "allowed": False,
                "reason": "SESSION_TRANSITION_WINDOW",
                "kill_switch_active": self.kill_switch_active,
                "daily_loss_pct": 0.0,
                "message": "New entries blocked: Session transition window (00:25 - 01:34 Iran time)."
            }

        baseline = self.baseline_equity or current_equity
        if baseline <= 0:
            return {
                "allowed": False,
                "reason": "INVALID_EQUITY_BASELINE",
                "kill_switch_active": True,
                "daily_loss_pct": 100.0,
                "message": "New entries blocked: Invalid baseline equity <= 0."
            }

        # Daily loss calculation: baseline minus current equity (or cumulative realized + unrealized loss)
        loss_amount_usd = max(0.0, baseline - current_equity)
        loss_pct = (loss_amount_usd / baseline) * 100.0

        if loss_pct >= self.MAX_DAILY_LOSS_PCT:
            if not self.kill_switch_active:
                logger.warning(f"[DailyLossKillSwitch] Kill-switch activated! Loss {loss_pct:.2f}% >= {self.MAX_DAILY_LOSS_PCT}% limit.")
                self.kill_switch_active = True
                self._save_persistence()

        if self.kill_switch_active:
            return {
                "allowed": False,
                "reason": "DAILY_LOSS_LIMIT_REACHED",
                "kill_switch_active": True,
                "daily_loss_pct": round(loss_pct, 2),
                "baseline_equity": round(baseline, 2),
                "current_equity": round(current_equity, 2),
                "message": f"New entries blocked: Daily 8% loss kill-switch active ({loss_pct:.2f}% loss >= 8.00% limit)."
            }

        return {
            "allowed": True,
            "reason": None,
            "kill_switch_active": False,
            "daily_loss_pct": round(loss_pct, 2),
            "baseline_equity": round(baseline, 2),
            "current_equity": round(current_equity, 2),
            "message": f"Pre-entry daily loss check passed ({loss_pct:.2f}% loss < 8.00% limit)."
        }

    def _save_persistence(self) -> None:
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
        except Exception as e:
            logger.error(f"[DailyLossKillSwitch] Failed to save persistence: {e}")

    def _load_persistence(self) -> None:
        """Loads state from disk if exists."""
        if os.path.exists(self.persistence_path):
            try:
                with open(self.persistence_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.current_session_key = data.get("current_session_key")
                self.baseline_equity = data.get("baseline_equity")
                self.kill_switch_active = data.get("kill_switch_active", False)
                self.realized_daily_loss_usd = data.get("realized_daily_loss_usd", 0.0)
            except Exception as e:
                logger.error(f"[DailyLossKillSwitch] Failed to load persistence: {e}")
