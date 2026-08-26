import os
import json
import threading
from typing import Dict, Any, Optional
from src.Risk.Services.professional_risk_engine import ProfessionalRiskEngine

DISCLAIMER_TEXT = (
    "The YarTrader Prop Firm Challenge Plan provides objective risk control monitoring and compliance gates. "
    "It strictly does NOT guarantee passing prop firm evaluations, profits, approvals, or financial returns."
)

class PropChallengeEngine:
    """
    Risk-management product engine for Prop Firm Challenges.
    Consumes existing ProfessionalRiskEngine rules and evaluates account exposure,
    daily loss limits, max drawdown limits, and session constraints.
    """
    def __init__(self, config_filepath: str = "runtime_logs/prop_challenge_config.json") -> None:
        self.config_filepath = config_filepath
        self.lock = threading.RLock()
        self.risk_engine = ProfessionalRiskEngine()
        os.makedirs(os.path.dirname(self.config_filepath), exist_ok=True)

    def _get_default_config(self) -> Dict[str, Any]:
        return {
            "is_configured": False,
            "prop_firm_name": "Generic Prop Firm",
            "account_number": "",
            "account_size": 100000.0,
            "target_profit_pct": 10.0,
            "daily_loss_limit_pct": 5.0,
            "max_drawdown_pct": 10.0,
            "risk_per_trade_pct": 1.0,
            "max_exposure_pct": 3.0,
            "max_concurrent_positions": 3,
            "session_rules": "ALLOW_ALL_SESSIONS",
            "overnight_rule": "FLAT_BEFORE_CLOSE",
            "news_rule": "NO_NEW_ENTRIES_AROUND_HIGH_IMPACT",
            "last_updated": None
        }

    def load_config(self) -> Dict[str, Any]:
        with self.lock:
            if os.path.exists(self.config_filepath):
                try:
                    with open(self.config_filepath, "r", encoding="utf-8") as f:
                        cfg = json.load(f)
                        defaults = self._get_default_config()
                        defaults.update(cfg)
                        return defaults
                except Exception:
                    pass
            return self._get_default_config()

    def save_config(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        with self.lock:
            current = self.load_config()
            for k, v in config_data.items():
                if k in current:
                    current[k] = v
            current["is_configured"] = True
            tmp_file = self.config_filepath + ".tmp"
            with open(tmp_file, "w", encoding="utf-8") as f:
                json.dump(current, f, indent=4)
            os.replace(tmp_file, self.config_filepath)
            return current

    def get_status(self, live_equity: Optional[float] = None, live_daily_pl: Optional[float] = None, open_positions_count: int = 0) -> Dict[str, Any]:
        with self.lock:
            cfg = self.load_config()
            if not cfg.get("is_configured", False):
                return {
                    "is_configured": False,
                    "status": "NOT_CONFIGURED",
                    "status_message": "PROP ACCOUNT NOT CONFIGURED",
                    "disclaimer": DISCLAIMER_TEXT,
                    "config": cfg,
                    "metrics": None
                }

            account_size = float(cfg["account_size"])
            daily_loss_limit_pct = float(cfg["daily_loss_limit_pct"])
            max_drawdown_pct = float(cfg["max_drawdown_pct"])
            target_profit_pct = float(cfg.get("target_profit_pct", 10.0))

            equity = live_equity if live_equity is not None else account_size
            daily_pl = live_daily_pl if live_daily_pl is not None else 0.0

            max_daily_loss_usd = account_size * (daily_loss_limit_pct / 100.0)
            max_total_drawdown_usd = account_size * (max_drawdown_pct / 100.0)

            daily_loss_used_usd = abs(min(0.0, daily_pl))
            remaining_daily_loss = max(0.0, max_daily_loss_usd - daily_loss_used_usd)

            current_drawdown_usd = max(0.0, account_size - equity)
            current_drawdown_pct = (current_drawdown_usd / account_size) * 100.0
            remaining_drawdown = max(0.0, max_total_drawdown_usd - current_drawdown_usd)

            profit_usd = equity - account_size
            target_profit_usd = account_size * (target_profit_pct / 100.0)
            challenge_progress_pct = round(max(0.0, min(100.0, (profit_usd / target_profit_usd) * 100.0)), 2) if target_profit_usd > 0 else 0.0

            # Determine challenge state
            state = "NORMAL"
            if current_drawdown_usd >= max_total_drawdown_usd or daily_loss_used_usd >= max_daily_loss_usd:
                state = "TRADING_HALTED"
            elif remaining_daily_loss < (max_daily_loss_usd * 0.2):
                state = "DAILY_LIMIT_NEAR"
            elif remaining_drawdown < (max_total_drawdown_usd * 0.2):
                state = "DRAWDOWN_NEAR"
            elif current_drawdown_pct > (max_drawdown_pct * 0.5):
                state = "CAUTION"
            else:
                state = "CHALLENGE_READY"

            return {
                "is_configured": True,
                "status": state,
                "status_message": f"Prop Challenge state: {state}",
                "disclaimer": DISCLAIMER_TEXT,
                "config": cfg,
                "metrics": {
                    "account_size": account_size,
                    "current_equity": round(equity, 2),
                    "daily_pl": round(daily_pl, 2),
                    "current_drawdown_usd": round(current_drawdown_usd, 2),
                    "current_drawdown_pct": round(current_drawdown_pct, 2),
                    "max_daily_loss_usd": round(max_daily_loss_usd, 2),
                    "max_total_drawdown_usd": round(max_total_drawdown_usd, 2),
                    "remaining_daily_loss": round(remaining_daily_loss, 2),
                    "remaining_drawdown": round(remaining_drawdown, 2),
                    "open_positions": open_positions_count,
                    "max_concurrent_positions": cfg.get("max_concurrent_positions", 3),
                    "challenge_progress_pct": challenge_progress_pct
                }
            }

prop_challenge_engine = PropChallengeEngine()
