import os
import json
import re
import threading
from typing import Dict, Any, List, Optional
from src.Risk.Services.professional_risk_engine import ProfessionalRiskEngine

DISCLAIMER_TEXT = (
    "The YarTrader Prop Firm Challenge Plan provides objective risk control monitoring and compliance gates. "
    "It strictly does NOT guarantee passing prop firm evaluations, profits, approvals, or financial returns."
)

DEFAULT_PRESETS_CATALOG: List[Dict[str, Any]] = [
    {
        "preset_id": "ftmo-100k-illustrative",
        "display_name": "FTMO $100,000 Standard (Illustrative)",
        "account_size": 100000.0,
        "target_profit_pct": 10.0,
        "daily_loss_limit_pct": 5.0,
        "max_drawdown_pct": 10.0,
        "risk_per_trade_pct": 1.0,
        "max_exposure_pct": 3.0,
        "max_concurrent_positions": 3,
        "phase_rules": {
            "phase_1_target_pct": 10.0,
            "phase_2_target_pct": 5.0,
            "min_trading_days": 4
        },
        "restrictions": {
            "overnight_rule": "ALLOW_OVERNIGHT",
            "news_rule": "RESTRICT_HIGH_IMPACT",
            "session_rules": "ALLOW_ALL_SESSIONS"
        },
        "compatibility": {
            "supported_platforms": ["MT5"],
            "supported_symbols": ["XAUUSD"]
        },
        "status": "illustrative",
        "source": "FTMO Evaluation Parameters (Illustrative Reference)",
        "source_url": "https://ftmo.com/en/objectives/",
        "retrieved_at": "2026-09-01T00:00:00Z"
    },
    {
        "preset_id": "funding-pips-100k-illustrative",
        "display_name": "Funding Pips $100,000 2-Step (Illustrative)",
        "account_size": 100000.0,
        "target_profit_pct": 8.0,
        "daily_loss_limit_pct": 5.0,
        "max_drawdown_pct": 10.0,
        "risk_per_trade_pct": 1.0,
        "max_exposure_pct": 3.0,
        "max_concurrent_positions": 5,
        "phase_rules": {
            "phase_1_target_pct": 8.0,
            "phase_2_target_pct": 5.0,
            "min_trading_days": 0
        },
        "restrictions": {
            "overnight_rule": "ALLOW_OVERNIGHT",
            "news_rule": "ALLOW_NEWS",
            "session_rules": "ALLOW_ALL_SESSIONS"
        },
        "compatibility": {
            "supported_platforms": ["MT5"],
            "supported_symbols": ["XAUUSD"]
        },
        "status": "illustrative",
        "source": "Funding Pips Evaluation Parameters (Illustrative Reference)",
        "source_url": "https://fundingpips.com/",
        "retrieved_at": "2026-09-01T00:00:00Z"
    },
    {
        "preset_id": "generic-standard-50k-illustrative",
        "display_name": "Generic Standard $50,000 (Illustrative)",
        "account_size": 50000.0,
        "target_profit_pct": 10.0,
        "daily_loss_limit_pct": 5.0,
        "max_drawdown_pct": 10.0,
        "risk_per_trade_pct": 1.0,
        "max_exposure_pct": 3.0,
        "max_concurrent_positions": 3,
        "phase_rules": {
            "phase_1_target_pct": 10.0,
            "phase_2_target_pct": 5.0,
            "min_trading_days": 5
        },
        "restrictions": {
            "overnight_rule": "FLAT_BEFORE_CLOSE",
            "news_rule": "NO_NEW_ENTRIES_AROUND_HIGH_IMPACT",
            "session_rules": "ALLOW_ALL_SESSIONS"
        },
        "compatibility": {
            "supported_platforms": ["MT5"],
            "supported_symbols": ["XAUUSD"]
        },
        "status": "illustrative",
        "source": "YarTrader Baseline Risk Specification",
        "source_url": None,
        "retrieved_at": "2026-09-01T00:00:00Z"
    }
]


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

    def validate_preset_definition(self, preset: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validates standard rules and mandatory provenance metadata for a prop-firm preset.
        Raises ValueError if any rule or metadata constraint is violated.
        """
        if not isinstance(preset, dict):
            raise ValueError("Preset definition must be a dictionary")

        preset_id = preset.get("preset_id")
        if not preset_id or not isinstance(preset_id, str) or not re.match(r"^[a-zA-Z0-9_-]+$", preset_id):
            raise ValueError(f"Invalid or malformed preset_id: {preset_id}")

        display_name = preset.get("display_name")
        if not display_name or not isinstance(display_name, str) or not display_name.strip():
            raise ValueError("Preset must have a non-empty display_name")

        account_size = preset.get("account_size")
        if account_size is None or not isinstance(account_size, (int, float)) or isinstance(account_size, bool) or account_size <= 0:
            raise ValueError(f"account_size must be a positive number: {account_size}")

        target_profit_pct = preset.get("target_profit_pct")
        if target_profit_pct is None or not isinstance(target_profit_pct, (int, float)) or isinstance(target_profit_pct, bool) or target_profit_pct <= 0 or target_profit_pct > 100:
            raise ValueError(f"target_profit_pct must be between 0 and 100: {target_profit_pct}")

        daily_loss_limit_pct = preset.get("daily_loss_limit_pct")
        if daily_loss_limit_pct is None or not isinstance(daily_loss_limit_pct, (int, float)) or isinstance(daily_loss_limit_pct, bool) or daily_loss_limit_pct <= 0 or daily_loss_limit_pct > 100:
            raise ValueError(f"daily_loss_limit_pct must be between 0 and 100: {daily_loss_limit_pct}")

        max_drawdown_pct = preset.get("max_drawdown_pct")
        if max_drawdown_pct is None or not isinstance(max_drawdown_pct, (int, float)) or isinstance(max_drawdown_pct, bool) or max_drawdown_pct <= 0 or max_drawdown_pct > 100:
            raise ValueError(f"max_drawdown_pct must be between 0 and 100: {max_drawdown_pct}")

        risk_per_trade_pct = preset.get("risk_per_trade_pct")
        if risk_per_trade_pct is not None:
            if not isinstance(risk_per_trade_pct, (int, float)) or isinstance(risk_per_trade_pct, bool) or risk_per_trade_pct <= 0 or risk_per_trade_pct > 100:
                raise ValueError(f"risk_per_trade_pct must be between 0 and 100: {risk_per_trade_pct}")

        max_exposure_pct = preset.get("max_exposure_pct")
        if max_exposure_pct is not None:
            if not isinstance(max_exposure_pct, (int, float)) or isinstance(max_exposure_pct, bool) or max_exposure_pct <= 0 or max_exposure_pct > 100:
                raise ValueError(f"max_exposure_pct must be between 0 and 100: {max_exposure_pct}")

        max_concurrent_positions = preset.get("max_concurrent_positions")
        if max_concurrent_positions is not None:
            if not isinstance(max_concurrent_positions, int) or isinstance(max_concurrent_positions, bool) or max_concurrent_positions < 1:
                raise ValueError(f"max_concurrent_positions must be an integer >= 1: {max_concurrent_positions}")

        # Contradictory risk constraint checks
        if daily_loss_limit_pct > max_drawdown_pct:
            raise ValueError(f"Contradictory rule: daily_loss_limit_pct ({daily_loss_limit_pct}%) cannot exceed max_drawdown_pct ({max_drawdown_pct}%)")

        if risk_per_trade_pct is not None and risk_per_trade_pct > daily_loss_limit_pct:
            raise ValueError(f"Contradictory rule: risk_per_trade_pct ({risk_per_trade_pct}%) cannot exceed daily_loss_limit_pct ({daily_loss_limit_pct}%)")

        if max_exposure_pct is not None and risk_per_trade_pct is not None and max_exposure_pct < risk_per_trade_pct:
            raise ValueError(f"Contradictory rule: max_exposure_pct ({max_exposure_pct}%) cannot be less than risk_per_trade_pct ({risk_per_trade_pct}%)")

        # Mandatory provenance metadata checks
        status = preset.get("status")
        if status not in ["verified", "illustrative", "deprecated"]:
            raise ValueError(f"Invalid provenance status: '{status}'. Must be one of ['verified', 'illustrative', 'deprecated']")

        source = preset.get("source")
        if not source or not isinstance(source, str) or not source.strip():
            raise ValueError("Missing mandatory provenance field 'source'")

        retrieved_at = preset.get("retrieved_at") or preset.get("effective_at")
        if not retrieved_at or not isinstance(retrieved_at, str) or not retrieved_at.strip():
            raise ValueError("Missing mandatory provenance timestamp ('retrieved_at' or 'effective_at')")

        return preset

    def get_presets_catalog(self) -> List[Dict[str, Any]]:
        """
        Returns all valid presets in the catalog.
        """
        validated_catalog = []
        for preset in DEFAULT_PRESETS_CATALOG:
            validated_catalog.append(self.validate_preset_definition(preset))
        return validated_catalog

    def get_preset_by_id(self, preset_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves a specific preset by its unique ID.
        """
        for preset in self.get_presets_catalog():
            if preset["preset_id"] == preset_id:
                return preset
        return None

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
