"""
Prop Firm Challenge Risk Engine & Rules Manager.
Enforces institutional prop firm challenge risk parameters, daily loss thresholds,
maximum drawdowns, position limits, and state transitions.

DISCLAIMER: YarTrader does NOT offer or guarantee prop firm challenge passing or profit generation.
Trading financial markets carries high risk. Past simulated or paper performance is not indicative of future results.
"""

import os
import json
from enum import Enum
from typing import Dict, Any, Optional, List
from datetime import datetime


class PropChallengeState(str, Enum):
    NOT_CONFIGURED = "NOT_CONFIGURED"
    CHALLENGE_READY = "CHALLENGE_READY"
    NORMAL = "NORMAL"
    CAUTION = "CAUTION"
    DAILY_LIMIT_NEAR = "DAILY_LIMIT_NEAR"
    DRAWDOWN_NEAR = "DRAWDOWN_NEAR"
    TRADING_HALTED = "TRADING_HALTED"


class PropChallengeEngine:
    """Manages Prop Challenge risk rules, account state, drawdown tracking, and execution halt boundaries."""

    DISCLAIMER = (
        "SAFETY DISCLAIMER: YarTrader provides risk modeling tools for educational and analytical purposes only. "
        "YarTrader makes zero guarantees regarding passing third-party prop firm challenges or generating trading profits."
    )

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = {
            "account_size": 100000.0,
            "daily_loss_limit_pct": 5.0,  # 5% max daily loss
            "max_drawdown_pct": 10.0,     # 10% overall max drawdown
            "risk_per_trade_pct": 1.0,    # 1% per trade max risk
            "max_concurrent_positions": 3,
            "allow_weekend_holding": False,
            "profit_target_pct": 10.0,
        }
        if config:
            self.config.update(config)

        self.initial_balance = self.config["account_size"]
        self.current_balance = self.initial_balance
        self.current_equity = self.initial_balance
        self.peak_equity = self.initial_balance
        self.day_start_equity = self.initial_balance

        self.active_positions_count = 0
        self.closed_trades_count = 0
        self.winning_trades_count = 0
        self.losing_trades_count = 0

        self.state = PropChallengeState.CHALLENGE_READY if config else PropChallengeState.NOT_CONFIGURED

    def configure(self, config_updates: Dict[str, Any]) -> Dict[str, Any]:
        """Configures or updates prop challenge risk parameters."""
        if "account_size" in config_updates and config_updates["account_size"] > 0:
            self.config["account_size"] = float(config_updates["account_size"])
            self.initial_balance = self.config["account_size"]
            self.current_balance = self.initial_balance
            self.current_equity = self.initial_balance
            self.peak_equity = self.initial_balance
            self.day_start_equity = self.initial_balance

        if "daily_loss_limit_pct" in config_updates:
            self.config["daily_loss_limit_pct"] = float(config_updates["daily_loss_limit_pct"])
        if "max_drawdown_pct" in config_updates:
            self.config["max_drawdown_pct"] = float(config_updates["max_drawdown_pct"])
        if "risk_per_trade_pct" in config_updates:
            self.config["risk_per_trade_pct"] = float(config_updates["risk_per_trade_pct"])
        if "max_concurrent_positions" in config_updates:
            self.config["max_concurrent_positions"] = int(config_updates["max_concurrent_positions"])
        if "allow_weekend_holding" in config_updates:
            self.config["allow_weekend_holding"] = bool(config_updates["allow_weekend_holding"])
        if "profit_target_pct" in config_updates:
            self.config["profit_target_pct"] = float(config_updates["profit_target_pct"])

        self.state = PropChallengeState.CHALLENGE_READY
        return self.get_status()

    def update_account_state(self, current_balance: float, current_equity: float, active_positions: int = 0) -> Dict[str, Any]:
        """Updates live account balance, equity, and active positions count, evaluating state transitions."""
        self.current_balance = float(current_balance)
        self.current_equity = float(current_equity)
        self.active_positions_count = int(active_positions)

        if self.current_equity > self.peak_equity:
            self.peak_equity = self.current_equity

        self._evaluate_state()
        return self.get_status()

    def _evaluate_state(self) -> None:
        """Evaluates thresholds and transitions the engine state."""
        if self.state == PropChallengeState.NOT_CONFIGURED:
            return

        # Calculate daily loss from day_start_equity
        daily_loss_amount = self.day_start_equity - self.current_equity
        daily_loss_pct = (daily_loss_amount / self.day_start_equity) * 100.0 if self.day_start_equity > 0 else 0.0

        # Calculate total drawdown from peak_equity or initial_balance (strictest)
        total_drawdown_amount = self.initial_balance - self.current_equity
        total_drawdown_pct = (total_drawdown_amount / self.initial_balance) * 100.0 if self.initial_balance > 0 else 0.0

        daily_limit = self.config["daily_loss_limit_pct"]
        max_dd_limit = self.config["max_drawdown_pct"]

        # Hard Breach Conditions -> TRADING_HALTED
        if daily_loss_pct >= daily_limit or total_drawdown_pct >= max_dd_limit:
            self.state = PropChallengeState.TRADING_HALTED
            return

        # Warning Conditions
        if daily_loss_pct >= (daily_limit * 0.8):
            self.state = PropChallengeState.DAILY_LIMIT_NEAR
            return

        if total_drawdown_pct >= (max_dd_limit * 0.8):
            self.state = PropChallengeState.DRAWDOWN_NEAR
            return

        if total_drawdown_pct >= (max_dd_limit * 0.5) or daily_loss_pct >= (daily_limit * 0.5):
            self.state = PropChallengeState.CAUTION
            return

        self.state = PropChallengeState.NORMAL

    def validate_trade_eligibility(self, proposed_risk_amount: float) -> Dict[str, Any]:
        """Validates if a new trade complies with Prop Challenge rules."""
        if self.state in (PropChallengeState.NOT_CONFIGURED, PropChallengeState.TRADING_HALTED):
            return {
                "allowed": False,
                "reason": f"Trading blocked due to state: {self.state.value}",
                "state": self.state.value
            }

        if self.active_positions_count >= self.config["max_concurrent_positions"]:
            return {
                "allowed": False,
                "reason": f"Max concurrent positions limit reached ({self.active_positions_count}/{self.config['max_concurrent_positions']})",
                "state": self.state.value
            }

        max_allowed_risk = self.current_balance * (self.config["risk_per_trade_pct"] / 100.0)
        if proposed_risk_amount > max_allowed_risk:
            return {
                "allowed": False,
                "reason": f"Proposed risk (${proposed_risk_amount:.2f}) exceeds trade limit (${max_allowed_risk:.2f})",
                "state": self.state.value
            }

        return {
            "allowed": True,
            "reason": "Trade complies with all Prop Challenge risk parameters",
            "state": self.state.value
        }

    def reset_daily_baseline(self) -> None:
        """Resets the day start baseline equity (typically at 00:00 UTC)."""
        self.day_start_equity = self.current_equity
        self._evaluate_state()

    def get_status(self) -> Dict[str, Any]:
        """Returns comprehensive status dictionary for API and UI rendering."""
        daily_loss_amount = max(0.0, self.day_start_equity - self.current_equity)
        daily_loss_pct = (daily_loss_amount / self.day_start_equity) * 100.0 if self.day_start_equity > 0 else 0.0

        total_drawdown_amount = max(0.0, self.initial_balance - self.current_equity)
        total_drawdown_pct = (total_drawdown_amount / self.initial_balance) * 100.0 if self.initial_balance > 0 else 0.0

        profit_amount = self.current_equity - self.initial_balance
        profit_pct = (profit_amount / self.initial_balance) * 100.0 if self.initial_balance > 0 else 0.0

        return {
            "state": self.state.value,
            "disclaimer": self.DISCLAIMER,
            "config": self.config,
            "metrics": {
                "initial_balance": round(self.initial_balance, 2),
                "current_balance": round(self.current_balance, 2),
                "current_equity": round(self.current_equity, 2),
                "peak_equity": round(self.peak_equity, 2),
                "day_start_equity": round(self.day_start_equity, 2),
                "daily_loss_amount": round(daily_loss_amount, 2),
                "daily_loss_pct": round(daily_loss_pct, 2),
                "total_drawdown_amount": round(total_drawdown_amount, 2),
                "total_drawdown_pct": round(total_drawdown_pct, 2),
                "profit_amount": round(profit_amount, 2),
                "profit_pct": round(profit_pct, 2),
                "active_positions": self.active_positions_count,
            },
            "limits": {
                "max_daily_loss_allowed": round(self.day_start_equity * (self.config["daily_loss_limit_pct"] / 100.0), 2),
                "max_total_drawdown_allowed": round(self.initial_balance * (self.config["max_drawdown_pct"] / 100.0), 2),
                "max_trade_risk_allowed": round(self.current_balance * (self.config["risk_per_trade_pct"] / 100.0), 2),
            }
        }
