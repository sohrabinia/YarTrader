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


def calculate_yartrader_daily_pnl(adapter: Any, now_utc: Optional[datetime] = None, magic: int = 143056) -> Dict[str, Any]:
    """Return current-session PnL from YarTrader-owned trades only.

    External balance/credit operations and manual trades are excluded. Open YarTrader
    positions contribute floating profit and swap. Unknown broker state raises so the
    execution gate fails closed rather than assuming zero loss.
    """
    now = now_utc or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    now = now.astimezone(timezone.utc)

    from datetime import datetime as _datetime
    session_key, _, _ = DailyLossKillSwitch.get_instance().get_session_key_and_window(now)
    session_date = _datetime.strptime(session_key, "%Y-%m-%d").date()
    session_start_local = _datetime.combine(session_date, DailyLossKillSwitch.SESSION_OPEN_TIME, tzinfo=IRAN_TZ)
    session_start_utc = session_start_local.astimezone(timezone.utc)

    mt5 = getattr(adapter, "_mt5", None)
    if mt5 is None or not getattr(adapter, "_initialized", False):
        raise RuntimeError("Cannot calculate YarTrader PnL: MT5 history state is unavailable.")

    # Alpari's MT5 server timestamps are offset from the Windows UTC wall clock.
    # Derive the broker epoch offset from a fresh live tick, rounded to a normal
    # 15-minute timezone increment. If the tick cannot establish a stable offset,
    # refuse to treat unknown history as zero PnL.
    broker_offset = 0.0
    if type(adapter).__name__ == "RealMT5BrokerAdapter":
        symbol = os.environ.get("YARTRADER_MT5_SYMBOL", "XAUUSD").strip().upper()
        quote = adapter.get_symbol_tick(symbol)
        quote_time = quote.get("time") if isinstance(quote, dict) else None
        if not isinstance(quote_time, (int, float)) or isinstance(quote_time, bool) or not math.isfinite(float(quote_time)) or float(quote_time) <= 0:
            raise RuntimeError("Cannot calculate YarTrader PnL: authoritative MT5 server timestamp is unavailable.")
        raw_offset = float(quote_time) - now.timestamp()
        broker_offset = round(raw_offset / 900.0) * 900.0
        if abs(broker_offset) > 18 * 3600 or abs(raw_offset - broker_offset) > 300:
            raise RuntimeError("Cannot calculate YarTrader PnL: MT5 server offset is unknown or the quote is stale.")

    session_start_epoch = int(session_start_utc.timestamp() + broker_offset)
    query_end_epoch = int(now.timestamp() + broker_offset)
    query_start_epoch = int(query_end_epoch - timedelta(days=90).total_seconds())
    query_start = datetime.fromtimestamp(query_start_epoch, timezone.utc)
    query_end = datetime.fromtimestamp(query_end_epoch, timezone.utc)
    # The native MetaTrader5 extension only accepts positional time bounds;
    # the JSON bridge proxy accepts keyword arguments and forwards them safely.
    if type(mt5).__name__ == "MT5BridgeProxy":
        raw_deals = mt5.history_deals_get(date_from=query_start, date_to=query_end)
    else:
        raw_deals = mt5.history_deals_get(query_start, query_end)
    if raw_deals is None:
        raise RuntimeError(f"Cannot calculate YarTrader PnL: MT5 history query failed ({mt5.last_error()}).")
    deals = [d._asdict() if hasattr(d, "_asdict") else dict(d) for d in raw_deals]
    positions = adapter.get_positions()
    if positions is None:
        raise RuntimeError("Cannot calculate YarTrader PnL: open-position state is unknown.")

    def is_owned(item: Dict[str, Any]) -> bool:
        try:
            item_magic = int(item.get("magic", 0) or 0)
        except (TypeError, ValueError):
            item_magic = 0
        comment = str(item.get("comment") or "").lower()
        return item_magic == int(magic) or comment.startswith("yartrader") or "yartrader" in comment

    owned_ids = set()
    for deal in deals:
        if is_owned(deal) and isinstance(deal.get("type"), (int, float)) and int(deal["type"]) in (0, 1):
            pos_id = deal.get("position_id") or deal.get("position")
            if pos_id not in (None, 0, "0"):
                owned_ids.add(str(pos_id))

    session_start_epoch = int(session_start_utc.timestamp())
    owned_deals = []
    realized = 0.0
    for deal in deals:
        deal_time = deal.get("time", 0)
        if not isinstance(deal_time, (int, float)) or int(deal_time) < session_start_epoch:
            continue
        pos_id = deal.get("position_id") or deal.get("position")
        if not (is_owned(deal) or (pos_id not in (None, 0, "0") and str(pos_id) in owned_ids)):
            continue
        if int(deal.get("type", -1) or 0) not in (0, 1):
            continue
        pnl = sum(float(deal.get(k) or 0.0) for k in ("profit", "commission", "swap", "fee"))
        if not math.isfinite(pnl):
            raise RuntimeError("Cannot calculate YarTrader PnL: non-finite broker deal PnL.")
        realized += pnl
        owned_deals.append(deal)

    floating = 0.0
    owned_open_count = 0
    for position in positions:
        if not is_owned(position):
            continue
        pnl = float(position.get("profit") or 0.0) + float(position.get("swap") or 0.0)
        if not math.isfinite(pnl):
            raise RuntimeError("Cannot calculate YarTrader PnL: non-finite open-position PnL.")
        floating += pnl
        owned_open_count += 1

    total = realized + floating
    return {
        "session_key": session_key,
        "realized_pnl": round(realized, 2),
        "floating_pnl": round(floating, 2),
        "total_pnl": round(total, 2),
        "owned_deal_count": len(owned_deals),
        "owned_open_positions": owned_open_count,
        "source": "MT5_MAGIC_143056_OR_YARTRADER_COMMENT",
    }


class DailyLossKillSwitch:
    """
    YarTrader Daily 10% Loss Protection Kill-Switch.
    Enforces:
    1. Maximum permitted daily loss = 10.0% of the account equity baseline captured at the start of the trading session.
    2. Session boundary: 01:35 Iran time -> 00:25 Iran time on following calendar day.
    3. Fail-closed on missing/invalid/non-finite equity or uninitialized baseline.
    """

    MAX_DAILY_LOSS_PCT: float = 10.0  # Strict 10% limit
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
        self.uses_dynamic_bot_pnl: bool = False
        self.current_wallet_equity: Optional[float] = None
        self.bot_daily_pnl_usd: Optional[float] = None

        self._load_persistence()

    def set_session_baseline(self, equity: float, session_date: str) -> bool:
        """Sets active session baseline equity explicitly for a given session date string."""
        if equity is None or isinstance(equity, bool) or not isinstance(equity, (int, float)):
            return False
        eq_val = float(equity)
        if not math.isfinite(eq_val) or eq_val <= 0:
            return False
        self.current_session_key = session_date
        self.baseline_equity = eq_val
        self.kill_switch_active = False
        self.uses_dynamic_bot_pnl = False
        self.current_wallet_equity = None
        self.bot_daily_pnl_usd = None
        self._save_persistence()
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
        now_utc: Optional[datetime] = None,
        bot_daily_pnl: Optional[Any] = None,
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

        # New session date transition: reset kill-switch and set fresh session baseline
        if self.current_session_key != session_key:
            self.current_session_key = session_key
            valid_supplied_base = False
            if session_baseline_equity is not None and not isinstance(session_baseline_equity, bool) and isinstance(session_baseline_equity, (int, float)):
                try:
                    s_base_f = float(session_baseline_equity)
                    if math.isfinite(s_base_f) and s_base_f > 0:
                        valid_supplied_base = True
                        self.baseline_equity = s_base_f
                except (ValueError, TypeError):
                    pass
            if not valid_supplied_base:
                self.baseline_equity = eq_val

            self.kill_switch_active = False
            self._save_persistence()

        if bot_daily_pnl is not None:
            if isinstance(bot_daily_pnl, bool) or not isinstance(bot_daily_pnl, (int, float)) or not math.isfinite(float(bot_daily_pnl)):
                return False, "KILL_SWITCH_ERROR", {}
            # Persist the live wallet and bot PnL, not a fixed starting-balance baseline.
            # Deposits, withdrawals, and manual trades affect the denominator but never bot PnL.
            self.uses_dynamic_bot_pnl = True
            self.current_wallet_equity = eq_val
            self.bot_daily_pnl_usd = float(bot_daily_pnl)
            baseline = eq_val
            loss_amount_usd = max(0.0, -float(bot_daily_pnl))
            loss_pct = (loss_amount_usd / eq_val) * 100.0
            self._save_persistence()
        else:
            # Compatibility path for diagnostics/tests; live execution gates must pass bot_daily_pnl.
            baseline = self.baseline_equity if (self.baseline_equity is not None and math.isfinite(self.baseline_equity) and self.baseline_equity > 0) else eq_val
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
            "kill_switch_active": self.kill_switch_active,
            "loss_amount_usd": round(loss_amount_usd, 2),
            "bot_daily_pnl_usd": round(float(bot_daily_pnl), 2) if bot_daily_pnl is not None else None,
            "risk_model": "YARTRADER_ONLY_PNL_OVER_CURRENT_WALLET_EQUITY" if bot_daily_pnl is not None else "LEGACY_ACCOUNT_EQUITY_BASELINE"
        }

        if self.kill_switch_active:
            return False, "DAILY_LOSS_LIMIT_REACHED", meta

        return True, None, meta

    def evaluate_entry_allowed(
        self,
        current_equity: float,
        unrealized_pnl_usd: float = 0.0,
        realized_pnl_usd: float = 0.0,
        dt: Optional[datetime] = None,
        bot_daily_pnl: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Evaluates pre-entry daily 8% loss limit and session window bounds.
        Returns detailed status payload.
        """
        allowed, reason, meta = self.evaluate_daily_loss(
            current_equity, now_utc=dt, bot_daily_pnl=bot_daily_pnl
        )
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

    def _save_persistence(self) -> None:
        """Persists state to disk for crash-resistant recovery across restarts."""
        try:
            data = {
                "current_session_key": self.current_session_key,
                "baseline_equity": None if self.uses_dynamic_bot_pnl else self.baseline_equity,
                "current_wallet_equity": self.current_wallet_equity,
                "bot_daily_pnl_usd": self.bot_daily_pnl_usd,
                "kill_switch_active": self.kill_switch_active,
                "realized_daily_loss_usd": self.realized_daily_loss_usd,
                "risk_model": "YARTRADER_ONLY_PNL_OVER_CURRENT_WALLET_EQUITY" if self.uses_dynamic_bot_pnl else "LEGACY_ACCOUNT_EQUITY_BASELINE",
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
                self.uses_dynamic_bot_pnl = data.get("risk_model") == "YARTRADER_ONLY_PNL_OVER_CURRENT_WALLET_EQUITY"
                self.current_wallet_equity = data.get("current_wallet_equity")
                self.bot_daily_pnl_usd = data.get("bot_daily_pnl_usd")
            except Exception as e:
                logger.error(f"[DailyLossKillSwitch] Failed to load persistence: {e}")
