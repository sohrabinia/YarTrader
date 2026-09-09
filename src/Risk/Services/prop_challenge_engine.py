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
        "phases": [
            {
                "phase_id": "phase-1",
                "display_name": "Phase 1 - Evaluation",
                "phase_order": 1,
                "phase_type": "evaluation",
                "target_profit_pct": 10.0,
                "daily_loss_limit_pct": 5.0,
                "max_drawdown_pct": 10.0,
                "min_trading_days": 4,
                "max_trading_days": 0,
                "status": "illustrative",
                "source": "FTMO Public Challenge Terms Reference"
            },
            {
                "phase_id": "phase-2",
                "display_name": "Phase 2 - Verification",
                "phase_order": 2,
                "phase_type": "verification",
                "target_profit_pct": 5.0,
                "daily_loss_limit_pct": 5.0,
                "max_drawdown_pct": 10.0,
                "min_trading_days": 4,
                "max_trading_days": 0,
                "status": "illustrative",
                "source": "FTMO Public Challenge Terms Reference"
            }
        ],
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
        "phases": [
            {
                "phase_id": "phase-1",
                "display_name": "Phase 1 - Student",
                "phase_order": 1,
                "phase_type": "evaluation",
                "target_profit_pct": 8.0,
                "daily_loss_limit_pct": 5.0,
                "max_drawdown_pct": 10.0,
                "min_trading_days": 0,
                "max_trading_days": 0,
                "status": "illustrative",
                "source": "Funding Pips Evaluation Parameters Reference"
            },
            {
                "phase_id": "phase-2",
                "display_name": "Phase 2 - Practitioner",
                "phase_order": 2,
                "phase_type": "verification",
                "target_profit_pct": 5.0,
                "daily_loss_limit_pct": 5.0,
                "max_drawdown_pct": 10.0,
                "min_trading_days": 0,
                "max_trading_days": 0,
                "status": "illustrative",
                "source": "Funding Pips Evaluation Parameters Reference"
            }
        ],
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
        "phases": [
            {
                "phase_id": "phase-1",
                "display_name": "Phase 1 - Challenge",
                "phase_order": 1,
                "phase_type": "evaluation",
                "target_profit_pct": 10.0,
                "daily_loss_limit_pct": 5.0,
                "max_drawdown_pct": 10.0,
                "min_trading_days": 5,
                "max_trading_days": 30,
                "status": "illustrative",
                "source": "YarTrader Baseline Risk Specification"
            }
        ],
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
    Supports multi-phase challenge rules and strict account-scoped isolation.
    """
    def __init__(self, config_filepath: str = "runtime_logs/prop_challenge_config.json") -> None:
        self.config_filepath = config_filepath
        self.lock = threading.RLock()
        self.risk_engine = ProfessionalRiskEngine()
        os.makedirs(os.path.dirname(self.config_filepath), exist_ok=True)

    def validate_phase_definition(self, phase: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validates standard rules for an individual phase definition.
        Raises ValueError if any structural or financial constraint is violated.
        """
        if not isinstance(phase, dict):
            raise ValueError("Phase definition must be a dictionary")

        phase_id = phase.get("phase_id")
        if not phase_id or not isinstance(phase_id, str) or not re.match(r"^[a-zA-Z0-9_-]+$", phase_id):
            raise ValueError(f"Invalid or malformed phase_id: {phase_id}")

        display_name = phase.get("display_name")
        if not display_name or not isinstance(display_name, str) or not display_name.strip():
            raise ValueError("Phase must have a non-empty display_name")

        phase_order = phase.get("phase_order")
        if phase_order is None or not isinstance(phase_order, int) or isinstance(phase_order, bool) or phase_order < 1:
            raise ValueError(f"phase_order must be an integer >= 1: {phase_order}")

        phase_type = phase.get("phase_type", "evaluation")
        if phase_type not in ["evaluation", "verification", "funded"]:
            raise ValueError(f"Invalid phase_type: '{phase_type}'. Must be one of ['evaluation', 'verification', 'funded']")

        target_profit_pct = phase.get("target_profit_pct")
        if target_profit_pct is None or not isinstance(target_profit_pct, (int, float)) or isinstance(target_profit_pct, bool) or target_profit_pct <= 0 or target_profit_pct > 100:
            raise ValueError(f"Phase target_profit_pct must be between 0 and 100: {target_profit_pct}")

        daily_loss_limit_pct = phase.get("daily_loss_limit_pct")
        if daily_loss_limit_pct is None or not isinstance(daily_loss_limit_pct, (int, float)) or isinstance(daily_loss_limit_pct, bool) or daily_loss_limit_pct <= 0 or daily_loss_limit_pct > 100:
            raise ValueError(f"Phase daily_loss_limit_pct must be between 0 and 100: {daily_loss_limit_pct}")

        max_drawdown_pct = phase.get("max_drawdown_pct")
        if max_drawdown_pct is None or not isinstance(max_drawdown_pct, (int, float)) or isinstance(max_drawdown_pct, bool) or max_drawdown_pct <= 0 or max_drawdown_pct > 100:
            raise ValueError(f"Phase max_drawdown_pct must be between 0 and 100: {max_drawdown_pct}")

        min_trading_days = phase.get("min_trading_days", 0)
        if not isinstance(min_trading_days, int) or isinstance(min_trading_days, bool) or min_trading_days < 0:
            raise ValueError(f"min_trading_days must be an integer >= 0: {min_trading_days}")

        max_trading_days = phase.get("max_trading_days", 0)
        if not isinstance(max_trading_days, int) or isinstance(max_trading_days, bool) or max_trading_days < 0:
            raise ValueError(f"max_trading_days must be an integer >= 0: {max_trading_days}")

        if max_trading_days > 0 and min_trading_days > 0 and max_trading_days < min_trading_days:
            raise ValueError(f"Logical error: max_trading_days ({max_trading_days}) cannot be less than min_trading_days ({min_trading_days})")

        # Contradictory risk constraint checks per phase
        if daily_loss_limit_pct > max_drawdown_pct:
            raise ValueError(f"Contradictory rule in phase '{phase_id}': daily_loss_limit_pct ({daily_loss_limit_pct}%) cannot exceed max_drawdown_pct ({max_drawdown_pct}%)")

        risk_per_trade_pct = phase.get("risk_per_trade_pct")
        if risk_per_trade_pct is not None:
            if not isinstance(risk_per_trade_pct, (int, float)) or isinstance(risk_per_trade_pct, bool) or risk_per_trade_pct <= 0 or risk_per_trade_pct > 100:
                raise ValueError(f"risk_per_trade_pct must be between 0 and 100: {risk_per_trade_pct}")
            if risk_per_trade_pct > daily_loss_limit_pct:
                raise ValueError(f"Contradictory rule in phase '{phase_id}': risk_per_trade_pct ({risk_per_trade_pct}%) cannot exceed daily_loss_limit_pct ({daily_loss_limit_pct}%)")

        max_exposure_pct = phase.get("max_exposure_pct")
        if max_exposure_pct is not None:
            if not isinstance(max_exposure_pct, (int, float)) or isinstance(max_exposure_pct, bool) or max_exposure_pct <= 0 or max_exposure_pct > 100:
                raise ValueError(f"max_exposure_pct must be between 0 and 100: {max_exposure_pct}")
            if risk_per_trade_pct is not None and max_exposure_pct < risk_per_trade_pct:
                raise ValueError(f"Contradictory rule in phase '{phase_id}': max_exposure_pct ({max_exposure_pct}%) cannot be less than risk_per_trade_pct ({risk_per_trade_pct}%)")

        # Phase provenance metadata checks if explicitly provided
        status = phase.get("status")
        if status is not None and status not in ["verified", "illustrative", "deprecated"]:
            raise ValueError(f"Invalid provenance status in phase '{phase_id}': '{status}'")

        return phase

    def validate_preset_definition(self, preset: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validates standard rules and mandatory provenance metadata for a prop-firm preset,
        including multi-phase validation and single-phase backward compatibility.
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

        # Multi-phase validation
        phases = preset.get("phases")
        if phases is not None:
            if not isinstance(phases, list) or len(phases) == 0:
                raise ValueError("Preset 'phases' field must be a non-empty list if provided")

            phase_ids = set()
            phase_orders = set()
            for idx, phase in enumerate(phases):
                validated_phase = self.validate_phase_definition(phase)
                pid = validated_phase["phase_id"]
                porder = validated_phase["phase_order"]

                if pid in phase_ids:
                    raise ValueError(f"Duplicate phase ID in preset '{preset_id}': '{pid}'")
                phase_ids.add(pid)

                if porder in phase_orders:
                    raise ValueError(f"Duplicate phase_order in preset '{preset_id}': {porder}")
                phase_orders.add(porder)

            # Check phase ordering continuity
            sorted_orders = sorted(list(phase_orders))
            if sorted_orders != list(range(1, len(sorted_orders) + 1)):
                raise ValueError(f"Invalid phase ordering in preset '{preset_id}': orders must be sequential starting from 1 (got {sorted_orders})")
        else:
            # Backward compatibility: generate single phase array from top-level rules
            preset["phases"] = [
                {
                    "phase_id": "phase-1",
                    "display_name": f"{display_name} - Single Phase",
                    "phase_order": 1,
                    "phase_type": "evaluation",
                    "target_profit_pct": target_profit_pct,
                    "daily_loss_limit_pct": daily_loss_limit_pct,
                    "max_drawdown_pct": max_drawdown_pct,
                    "min_trading_days": preset.get("phase_rules", {}).get("min_trading_days", 0),
                    "max_trading_days": 0,
                    "status": status,
                    "source": source
                }
            ]

        return preset

    def evaluate_phase_status(
        self,
        phase: Dict[str, Any],
        equity: float,
        account_size: float,
        daily_pl: float,
        trading_days: int = 0
    ) -> Dict[str, Any]:
        """
        Evaluates a single phase deterministically given current account metrics.
        Returns dictionary containing status: NOT_STARTED, ACTIVE, PASSED, or FAILED.
        """
        target_profit_pct = float(phase["target_profit_pct"])
        daily_loss_limit_pct = float(phase["daily_loss_limit_pct"])
        max_drawdown_pct = float(phase["max_drawdown_pct"])
        min_trading_days = int(phase.get("min_trading_days", 0))

        target_profit_usd = account_size * (target_profit_pct / 100.0)
        max_daily_loss_usd = account_size * (daily_loss_limit_pct / 100.0)
        max_total_drawdown_usd = account_size * (max_drawdown_pct / 100.0)

        current_profit_usd = equity - account_size
        current_drawdown_usd = max(0.0, account_size - equity)
        daily_loss_used_usd = abs(min(0.0, daily_pl))

        # Check failure condition
        if current_drawdown_usd >= max_total_drawdown_usd or daily_loss_used_usd >= max_daily_loss_usd:
            return {
                "phase_id": phase["phase_id"],
                "display_name": phase["display_name"],
                "phase_order": phase["phase_order"],
                "status": "FAILED",
                "reason": "Loss limit or drawdown exceeded",
                "progress_pct": 0.0
            }

        progress_pct = round(max(0.0, min(100.0, (current_profit_usd / target_profit_usd) * 100.0)), 2) if target_profit_usd > 0 else 0.0

        # Check pass condition
        if current_profit_usd >= target_profit_usd:
            if min_trading_days > 0 and trading_days < min_trading_days:
                return {
                    "phase_id": phase["phase_id"],
                    "display_name": phase["display_name"],
                    "phase_order": phase["phase_order"],
                    "status": "ACTIVE",
                    "reason": f"Target profit reached ({progress_pct}%); waiting for min trading days ({trading_days}/{min_trading_days})",
                    "progress_pct": progress_pct
                }
            return {
                "phase_id": phase["phase_id"],
                "display_name": phase["display_name"],
                "phase_order": phase["phase_order"],
                "status": "PASSED",
                "reason": "Target profit reached and minimum trading days met",
                "progress_pct": 100.0
            }

        return {
            "phase_id": phase["phase_id"],
            "display_name": phase["display_name"],
            "phase_order": phase["phase_order"],
            "status": "ACTIVE",
            "reason": "Phase active in progress",
            "progress_pct": progress_pct
        }

    def evaluate_multi_phase_challenge(
        self,
        phases: List[Dict[str, Any]],
        active_phase_id: Optional[str],
        equity: float,
        account_size: float,
        daily_pl: float,
        trading_days: int = 0
    ) -> Dict[str, Any]:
        """
        Evaluates a multi-phase challenge across all defined phases deterministically.
        Determines current active phase and overall challenge state.
        """
        sorted_phases = sorted(phases, key=lambda p: p["phase_order"])
        phase_evaluations = []
        overall_status = "ACTIVE"
        current_active_found = False

        if not active_phase_id:
            active_phase_id = sorted_phases[0]["phase_id"]

        for phase in sorted_phases:
            pid = phase["phase_id"]
            if pid == active_phase_id:
                current_active_found = True
                eval_res = self.evaluate_phase_status(phase, equity, account_size, daily_pl, trading_days)
                phase_evaluations.append(eval_res)

                if eval_res["status"] == "FAILED":
                    overall_status = "FAILED"
                elif eval_res["status"] == "PASSED":
                    next_phases = [p for p in sorted_phases if p["phase_order"] > phase["phase_order"]]
                    if not next_phases:
                        overall_status = "PASSED"
            elif not current_active_found:
                phase_evaluations.append({
                    "phase_id": pid,
                    "display_name": phase["display_name"],
                    "phase_order": phase["phase_order"],
                    "status": "PASSED",
                    "reason": "Prior phase completed",
                    "progress_pct": 100.0
                })
            else:
                phase_evaluations.append({
                    "phase_id": pid,
                    "display_name": phase["display_name"],
                    "phase_order": phase["phase_order"],
                    "status": "NOT_STARTED",
                    "reason": "Phase not started",
                    "progress_pct": 0.0
                })

        return {
            "active_phase_id": active_phase_id,
            "overall_status": overall_status,
            "phase_evaluations": phase_evaluations
        }

    def get_presets_catalog(self) -> List[Dict[str, Any]]:
        """
        Returns all valid presets in the catalog.
        """
        validated_catalog = []
        for preset in DEFAULT_PRESETS_CATALOG:
            validated_catalog.append(self.validate_preset_definition(preset.copy()))
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
            "active_phase_id": "phase-1",
            "trading_days": 0,
            "last_updated": None
        }

    def _read_all_accounts_data(self) -> Dict[str, Any]:
        """
        Internal helper to read JSON persistence and return full accounts dict.
        Migrates legacy flat config if present.
        """
        if os.path.exists(self.config_filepath):
            try:
                with open(self.config_filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)

                if isinstance(data, dict):
                    if "accounts" in data and isinstance(data["accounts"], dict):
                        return data["accounts"]
                    else:
                        # Legacy single-account migration
                        migrated_account = self._get_default_config()
                        migrated_account.update(data)
                        accounts_dict = {"default": migrated_account}
                        # Save migrated structure back to disk
                        tmp_file = self.config_filepath + ".tmp"
                        with open(tmp_file, "w", encoding="utf-8") as f:
                            json.dump({"accounts": accounts_dict}, f, indent=4)
                        os.replace(tmp_file, self.config_filepath)
                        return accounts_dict
            except Exception:
                pass
        return {}

    def load_config(self, account_id: str = "default") -> Dict[str, Any]:
        """
        Loads Prop Challenge configuration for a specific account ID.
        Ensures strict account isolation.
        """
        with self.lock:
            accounts_data = self._read_all_accounts_data()
            clean_account_id = (account_id or "default").strip().lower()

            if clean_account_id in accounts_data:
                cfg = self._get_default_config()
                cfg.update(accounts_data[clean_account_id])
                return cfg

            return self._get_default_config()

    def save_config(self, config_data: Dict[str, Any], account_id: str = "default") -> Dict[str, Any]:
        """
        Saves Prop Challenge configuration specifically for account_id.
        Prevents cross-account configuration leakage or overwrite.
        """
        with self.lock:
            accounts_data = self._read_all_accounts_data()
            clean_account_id = (account_id or "default").strip().lower()

            current = self.load_config(account_id=clean_account_id)
            for k, v in config_data.items():
                if k in current or k in ["phases", "active_phase_id", "trading_days"]:
                    current[k] = v

            current["is_configured"] = True
            accounts_data[clean_account_id] = current

            tmp_file = self.config_filepath + ".tmp"
            with open(tmp_file, "w", encoding="utf-8") as f:
                json.dump({"accounts": accounts_data}, f, indent=4)
            os.replace(tmp_file, self.config_filepath)

            return current

    def get_status(
        self,
        live_equity: Optional[float] = None,
        live_daily_pl: Optional[float] = None,
        open_positions_count: int = 0,
        account_id: str = "default"
    ) -> Dict[str, Any]:
        """
        Retrieves Prop Challenge risk status and multi-phase progression strictly for account_id.
        Enforces complete account isolation (metrics, halts, and phases do not bleed across accounts).
        """
        with self.lock:
            cfg = self.load_config(account_id=account_id)
            if not cfg.get("is_configured", False):
                return {
                    "account_id": account_id,
                    "is_configured": False,
                    "status": "NOT_CONFIGURED",
                    "status_message": "PROP ACCOUNT NOT CONFIGURED",
                    "disclaimer": DISCLAIMER_TEXT,
                    "config": cfg,
                    "metrics": None,
                    "multi_phase": None
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

            # Determine challenge state for this account
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

            # Multi-phase evaluation for this account
            phases = cfg.get("phases")
            multi_phase_eval = None
            if phases and isinstance(phases, list):
                active_phase_id = cfg.get("active_phase_id", phases[0].get("phase_id"))
                trading_days = cfg.get("trading_days", 0)
                multi_phase_eval = self.evaluate_multi_phase_challenge(
                    phases=phases,
                    active_phase_id=active_phase_id,
                    equity=equity,
                    account_size=account_size,
                    daily_pl=daily_pl,
                    trading_days=trading_days
                )

            return {
                "account_id": account_id,
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
                },
                "multi_phase": multi_phase_eval
            }

prop_challenge_engine = PropChallengeEngine()
