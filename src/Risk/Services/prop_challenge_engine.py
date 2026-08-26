from typing import Dict, Any, Optional

class PropChallengeEngine:
    """Prop Firm Challenge Risk Management & Monitoring Engine.

    Calculates challenge status, remaining daily loss limits, remaining drawdown,
    and risk parameters without offering guaranteed passing promises or profit guarantees.
    """

    DEFAULT_CONFIG = {
        "account_size": 100000.0,
        "daily_loss_limit_percent": 5.0,
        "max_drawdown_percent": 10.0,
        "risk_per_trade_percent": 1.0,
        "max_concurrent_positions": 3,
        "session_rules": "No holding through high-impact news or overnight session close."
    }

    def __init__(self):
        self._config: Optional[Dict[str, Any]] = None
        self._equity: float = 100000.0
        self._start_of_day_equity: float = 100000.0
        self._peak_equity: float = 100000.0
        self._open_positions_count: int = 0

    def configure(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validates and applies configuration parameters."""
        account_size = float(config.get("account_size", self.DEFAULT_CONFIG["account_size"]))
        daily_loss_pct = float(config.get("daily_loss_limit_percent", self.DEFAULT_CONFIG["daily_loss_limit_percent"]))
        max_dd_pct = float(config.get("max_drawdown_percent", self.DEFAULT_CONFIG["max_drawdown_percent"]))
        risk_per_trade_pct = float(config.get("risk_per_trade_percent", self.DEFAULT_CONFIG["risk_per_trade_percent"]))
        max_positions = int(config.get("max_concurrent_positions", self.DEFAULT_CONFIG["max_concurrent_positions"]))

        if account_size <= 0:
            raise ValueError("account_size must be positive")
        if not (0 < daily_loss_pct <= 20):
            raise ValueError("daily_loss_limit_percent must be between 0 and 20")
        if not (0 < max_dd_pct <= 30):
            raise ValueError("max_drawdown_percent must be between 0 and 30")
        if not (0 < risk_per_trade_pct <= 10):
            raise ValueError("risk_per_trade_percent must be between 0 and 10")
        if max_positions < 1:
            raise ValueError("max_concurrent_positions must be at least 1")

        self._config = {
            "account_size": account_size,
            "daily_loss_limit_percent": daily_loss_pct,
            "max_drawdown_percent": max_dd_pct,
            "risk_per_trade_percent": risk_per_trade_pct,
            "max_concurrent_positions": max_positions,
            "session_rules": str(config.get("session_rules", self.DEFAULT_CONFIG["session_rules"]))
        }
        self._equity = account_size
        self._start_of_day_equity = account_size
        self._peak_equity = account_size
        return self.get_status()

    def update_equity(self, current_equity: float, open_positions_count: int = 0):
        self._equity = current_equity
        if current_equity > self._peak_equity:
            self._peak_equity = current_equity
        self._open_positions_count = open_positions_count

    def get_status(self) -> Dict[str, Any]:
        if not self._config:
            return {
                "status": "NOT_CONFIGURED",
                "configured": False,
                "message": "Prop Challenge parameters are not configured.",
                "config": None,
                "metrics": None
            }

        account_size = self._config["account_size"]
        daily_loss_limit = account_size * (self._config["daily_loss_limit_percent"] / 100.0)
        max_dd_limit = account_size * (self._config["max_drawdown_percent"] / 100.0)

        daily_pnl = self._equity - self._start_of_day_equity
        daily_loss = max(0.0, -daily_pnl)
        remaining_daily_loss = max(0.0, daily_loss_limit - daily_loss)

        current_dd = max(0.0, self._peak_equity - self._equity)
        remaining_dd = max(0.0, max_dd_limit - current_dd)

        # Determine State
        if daily_loss >= daily_loss_limit or current_dd >= max_dd_limit:
            state = "TRADING_HALTED"
        elif daily_loss >= daily_loss_limit * 0.8:
            state = "DAILY_LIMIT_NEAR"
        elif current_dd >= max_dd_limit * 0.8:
            state = "DRAWDOWN_NEAR"
        elif daily_loss >= daily_loss_limit * 0.5 or current_dd >= max_dd_limit * 0.5:
            state = "CAUTION"
        elif self._equity >= account_size:
            state = "CHALLENGE_READY"
        else:
            state = "NORMAL"

        return {
            "status": state,
            "configured": True,
            "config": self._config,
            "metrics": {
                "account_size": account_size,
                "equity": round(self._equity, 2),
                "start_of_day_equity": round(self._start_of_day_equity, 2),
                "peak_equity": round(self._peak_equity, 2),
                "daily_pnl": round(daily_pnl, 2),
                "daily_loss_limit": round(daily_loss_limit, 2),
                "remaining_daily_loss": round(remaining_daily_loss, 2),
                "max_drawdown_limit": round(max_dd_limit, 2),
                "current_drawdown": round(current_dd, 2),
                "remaining_drawdown": round(remaining_dd, 2),
                "open_positions": self._open_positions_count,
                "max_concurrent_positions": self._config["max_concurrent_positions"]
            },
            "disclaimer": "Prop Firm Challenge monitoring framework provided for risk evaluation only. Positive challenge outcome is not guaranteed."
        }

prop_challenge_engine = PropChallengeEngine()
