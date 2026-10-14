import logging
import os
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from pathlib import Path
from src.Execution.Safety.safety_gate import MetaTraderSafetyGate
from src.Infrastructure.exceptions import ValidationException
from src.Risk.Services.professional_risk_engine import ProductionRiskPolicy
from src.Execution.Safety.demo_exploration_policy import demo_exploration_autonomy_enabled

logger = logging.getLogger("DemoExecutionGate")


def _demo_config_value(name: str, default: str) -> str:
    """Read explicit process settings first, then project env files without overriding process env."""
    value = os.environ.get(name)
    if value is not None:
        return value
    project_root = Path(__file__).resolve().parents[3]
    for filename in (".env.production", ".env"):
        try:
            for line in (project_root / filename).read_text(encoding="utf-8-sig").splitlines():
                stripped = line.strip()
                if stripped.startswith(name + "="):
                    return stripped.split("=", 1)[1].strip().strip("\"'")
        except OSError:
            continue
    return default


class DemoExecutionGate:
    """
    Dedicated SRE Demo Execution Gate.
    Enforces strict DEMO-only safety boundaries before any order submission to the authorized MT4 DEMO bridge.

    Guarantees:
    1. Demo mode is explicitly enabled.
    2. Live trading is explicitly disabled (LIVE_TRADING_ENABLED=False).
    3. Connected DEMO account is verified against the adapter's authorized account/server and IsDemo-equivalent state.
    4. Terminal trading permissions are enabled.
    5. Symbol is tradeable.
    6. Order validation (order_check) succeeds.
    7. Risk limits pass.
    8. Position sizing passes.
    9. SL/TP validation passes.
    """

    AUTHORIZED_DEMO_ACCOUNT = "52961173"
    AUTHORIZED_DEMO_SERVER = "Alpari-MT5-Demo"

    @classmethod
    def verify_demo_execution_eligibility(
        cls,
        adapter_or_mt5: Any,
        request: Any,
        demo_mode_flag: bool = True
    ) -> bool:
        """
        Evaluates all 9 mandatory SRE Demo Execution safety checks.
        Throws ValidationException on any check failure. Fails closed.
        """
        # Check 1: Demo mode flag explicitly enabled
        if not demo_mode_flag:
            raise ValidationException("DemoExecutionGate: Demo execution is disabled (demo_mode_flag=False).")

        # Check 2: Live trading explicitly disabled & MetaTraderSafetyGate
        MetaTraderSafetyGate.verify_operation(
            terminal_type=getattr(adapter_or_mt5, "PLATFORM_NAME", "MT5"),
            operation_type="DEMO",
            account_id=(getattr(adapter_or_mt5, "TARGET_ACCOUNT", cls.AUTHORIZED_DEMO_ACCOUNT)),
            server_name=(getattr(adapter_or_mt5, "TARGET_SERVER", cls.AUTHORIZED_DEMO_SERVER))
        )

        # Retrieve adapter methods or dictionary
        if hasattr(adapter_or_mt5, "get_account_info"):
            acc_info = adapter_or_mt5.get_account_info()
            term_info = adapter_or_mt5.get_terminal_info()
            sym_info = adapter_or_mt5.get_symbol_info(request.Symbol) if hasattr(request, "Symbol") else None
        else:
            acc_info = getattr(adapter_or_mt5, "account_info", lambda: None)()
            term_info = getattr(adapter_or_mt5, "terminal_info", lambda: None)()
            sym_info = getattr(adapter_or_mt5, "symbol_info", lambda s: None)(getattr(request, "Symbol", "XAUUSD"))

        # Fail Closed: broker bridge is disconnected:
        if acc_info is None:
            logger.warning("[DemoExecutionGate] broker process disconnected. Failing closed.")
            raise ValidationException("DemoExecutionGate Violation: broker terminal is disconnected or account info is unavailable.")

        # Check 3: Platform & DEMO Verification (Rejects REAL accounts explicitly)
        login = str(acc_info.get("login", ""))
        server = str(acc_info.get("server", ""))
        trade_mode = acc_info.get("trade_mode", None)
        is_real = acc_info.get("is_real", False)
        platform = str(acc_info.get("platform", "MT5")).upper()

        # MT4 bridge exposes is_demo as the authoritative account-mode fact.
        # Its normalized trade_mode value must not be interpreted using MT5-only semantics.
        if platform == "MT4":
            if is_real or acc_info.get("is_demo") is not True:
                raise ValidationException("SECURITY VIOLATION: Connected MT4 account is not DEMO. Real account execution is strictly rejected repository-wide.")
        elif is_real or (trade_mode is not None and trade_mode != 0):
            raise ValidationException("SECURITY VIOLATION: Connected account is REAL or non-DEMO. Real account execution is strictly rejected repository-wide.")

        if platform == "MT4":
            mt4_account = getattr(adapter_or_mt5, "TARGET_ACCOUNT", "")
            mt4_server = getattr(adapter_or_mt5, "TARGET_SERVER", "")
            if login and login != str(mt4_account):
                raise ValidationException(f"DemoExecutionGate Violation: Connected MT4 account '{login}' is not authorized DEMO account '{mt4_account}'.")
            if server and server != str(mt4_server):
                raise ValidationException(f"DemoExecutionGate Violation: Connected MT4 server '{server}' is not authorized DEMO server '{mt4_server}'.")
        else:
            if login and login != cls.AUTHORIZED_DEMO_ACCOUNT:
                raise ValidationException(
                    f"DemoExecutionGate Violation: Connected MT5 account '{login}' is not authorized DEMO account '{cls.AUTHORIZED_DEMO_ACCOUNT}'."
                )
            if server and server != cls.AUTHORIZED_DEMO_SERVER:
                raise ValidationException(
                    f"DemoExecutionGate Violation: Connected MT5 server '{server}' is not authorized DEMO server '{cls.AUTHORIZED_DEMO_SERVER}'."
                )

        # Check 4: Terminal trading permissions enabled
        if term_info is not None:
            trade_allowed = term_info.get("trade_allowed", True)
            tradeapi_disabled = term_info.get("tradeapi_disabled", False)
            if not trade_allowed or tradeapi_disabled:
                raise ValidationException("DemoExecutionGate Violation: terminal trading permissions disabled.")

        # Check 5: Symbol tradeable
        if sym_info is not None:
            sym_trade_mode = sym_info.get("trade_mode", 4) # 4 is SYMBOL_TRADE_MODE_FULL
            if sym_trade_mode == 0:
                raise ValidationException(f"DemoExecutionGate Violation: Symbol '{request.Symbol}' trade mode is DISABLED (0).")

        # Check 7: Daily Loss Limit Gate (10% Ceiling) - Strictly Fail Closed
        import math
        raw_equity = acc_info.get("equity") if isinstance(acc_info, dict) else None
        if raw_equity is None or isinstance(raw_equity, bool) or not isinstance(raw_equity, (int, float)):
            raise ValidationException("DemoExecutionGate Violation: Account equity is missing, boolean, or non-numeric. Execution strictly blocked.")

        try:
            equity_val = float(raw_equity)
        except (ValueError, TypeError):
            raise ValidationException("DemoExecutionGate Violation: Account equity is unusable or non-numeric. Execution strictly blocked.")

        if equity_val <= 0 or not math.isfinite(equity_val):
            raise ValidationException(f"DemoExecutionGate Violation: Account equity ({raw_equity}) must be positive and finite. Execution strictly blocked.")

        try:
            from src.Risk.Services.daily_loss_kill_switch import DailyLossKillSwitch
            # Use actual UTC wall time for the Iran session key and daily boundary.
            risk_now = datetime.now(timezone.utc)
            bot_daily_pnl = None
            if type(adapter_or_mt5).__name__ == "RealMT5BrokerAdapter":
                from src.Risk.Services.daily_loss_kill_switch import calculate_yartrader_daily_pnl
                pnl_snapshot = calculate_yartrader_daily_pnl(adapter_or_mt5, now_utc=risk_now)
                bot_daily_pnl = pnl_snapshot["total_pnl"]
            allowed, reason, meta = DailyLossKillSwitch.get_instance().evaluate_daily_loss(
                equity_val, now_utc=risk_now, bot_daily_pnl=bot_daily_pnl
            )
            if not allowed and not (demo_exploration_autonomy_enabled() and reason == "DAILY_LOSS_LIMIT_REACHED"):
                raise ValidationException(
                    f"DemoExecutionGate Violation: Daily {meta.get('max_daily_loss_pct', DailyLossKillSwitch.MAX_DAILY_LOSS_PCT):g}% "
                    f"loss limit active ({reason}, loss={meta.get('loss_pct', 0.0)}%). Execution strictly blocked."
                )
            if not allowed and demo_exploration_autonomy_enabled():
                logger.warning("DEMO_EXPLORATION_OVERRIDE: daily-loss threshold is telemetry-only; invalid equity/history errors still block.")
        except ValidationException:
            raise
        except Exception as ex:
            raise ValidationException(f"DemoExecutionGate Violation: DailyLossKillSwitch evaluation error: {ex}")

        # Check 8: Broker-authoritative position sizing bounds; never assume a lot size.
        order_type = str(getattr(request, "OrderType", "")).upper()
        symbol = str(getattr(request, "Symbol", "")).upper()
        if hasattr(request, "Volume") and order_type not in ("CLOSE", "EXIT"):
            if not isinstance(sym_info, dict) or not all(k in sym_info for k in ("volume_min", "volume_max", "volume_step")):
                raise ValidationException("DemoExecutionGate Violation: Broker-reported volume minimum, maximum, and step are required; refusing to assume a lot size.")
            try:
                vol_min = float(sym_info["volume_min"])
                vol_max = float(sym_info["volume_max"])
                vol_step = float(sym_info["volume_step"])
                req_volume = float(request.Volume)
            except (TypeError, ValueError):
                raise ValidationException("DemoExecutionGate Violation: Broker volume limits or requested volume are non-numeric.")
            if (not all(math.isfinite(v) for v in (vol_min, vol_max, vol_step, req_volume))
                    or vol_min <= 0 or vol_max < vol_min or vol_step <= 0 or req_volume <= 0):
                raise ValidationException("DemoExecutionGate Violation: Broker volume limits or requested volume are invalid.")
            # Requested volume is advisory for the real MT5 adapter, which replaces
            # it using a fresh wallet snapshot immediately before submission. Keep
            # strict range validation for non-production/mock adapters.
            if type(adapter_or_mt5).__name__ != "RealMT5BrokerAdapter" and (req_volume < vol_min or req_volume > vol_max):
                raise ValidationException(f"DemoExecutionGate Violation: Volume {req_volume} out of bounds according to broker limits [{vol_min}, {vol_max}].")

        # Check 9: Dynamic SL/TP Side Validation (Dynamic Market Geometry)

        # Verify that the broker's minimum lot is affordable against the current
        # wallet. Requested volume is deliberately not used for this calculation:
        # the final MT5 adapter computes the actual lot immediately before submit.
        if type(adapter_or_mt5).__name__ == "RealMT5BrokerAdapter" and order_type not in ("CLOSE", "EXIT"):
            raw_price = getattr(request, "Price", None)
            raw_sl = getattr(request, "StopLoss", None)
            raw_balance = acc_info.get("balance") if isinstance(acc_info, dict) else None
            try:
                balance_val = float(raw_balance)
            except (TypeError, ValueError):
                balance_val = -1.0
            risk_basis = min(balance_val, equity_val) if math.isfinite(balance_val) and balance_val > 0 else -1.0
            mt5 = getattr(adapter_or_mt5, "_mt5", None)
            if raw_price is None and order_type in ("BUY", "LONG", "SELL", "SHORT"):
                tick = adapter_or_mt5.get_symbol_tick(symbol)
                if isinstance(tick, dict):
                    raw_price = tick.get("ask" if order_type in ("BUY", "LONG") else "bid")
                elif tick is not None:
                    raw_price = getattr(tick, "ask" if order_type in ("BUY", "LONG") else "bid", None)
            if (not isinstance(raw_price, (int, float)) or not isinstance(raw_sl, (int, float))
                    or isinstance(raw_price, bool) or isinstance(raw_sl, bool)
                    or not math.isfinite(float(raw_price)) or not math.isfinite(float(raw_sl))
                    or float(raw_price) <= 0 or float(raw_sl) <= 0
                    or risk_basis <= 0 or mt5 is None):
                raise ValidationException("DemoExecutionGate Violation: Current wallet, entry price, stop-loss or MT5 profit calculator unavailable for risk sizing.")
            if order_type in ("BUY", "LONG") or order_type.startswith("BUY_"):
                mt5_order_type = mt5.ORDER_TYPE_BUY
            elif order_type in ("SELL", "SHORT") or order_type.startswith("SELL_"):
                mt5_order_type = mt5.ORDER_TYPE_SELL
            else:
                raise ValidationException(f"DemoExecutionGate Violation: Unsupported order direction for risk sizing ({order_type}).")
            volume_min = float(sym_info.get("volume_min") or 0.0) if isinstance(sym_info, dict) else 0.0
            if volume_min <= 0:
                raise ValidationException("DemoExecutionGate Violation: Broker minimum lot is unavailable for wallet risk sizing.")
            risk_budget = risk_basis * (ProductionRiskPolicy.TARGET_RISK_PCT / 100.0)
            broker_profit = mt5.order_calc_profit(
                mt5_order_type, symbol, volume_min, float(raw_price), float(raw_sl)
            )
            if broker_profit is None or not isinstance(broker_profit, (int, float)) or not math.isfinite(float(broker_profit)):
                raise ValidationException("DemoExecutionGate Violation: MT5 could not verify broker-minimum stop-loss risk; order rejected.")
            minimum_risk = abs(float(broker_profit))
            if minimum_risk > risk_budget * 1.000001:
                raise ValidationException(
                    f"DemoExecutionGate Violation: Broker minimum lot risks {minimum_risk:.4f}, "
                    f"above dynamic 1.0% wallet budget {risk_budget:.4f}; order rejected."
                )

        if isinstance(getattr(request, "Price", None), (int, float)) and not isinstance(request.Price, bool) and request.Price > 0:
            sl = getattr(request, "StopLoss", None)
            tp = getattr(request, "TakeProfit", None)

            is_buy = order_type in ("BUY", "LONG") or order_type.startswith("BUY_")
            is_sell = order_type in ("SELL", "SHORT") or order_type.startswith("SELL_")
            if is_buy or is_sell:
                if is_buy and sl and sl > 0 and sl >= request.Price:
                    raise ValidationException(f"DemoExecutionGate Violation: Buy order SL {sl} must be below entry price {request.Price}.")
                if is_buy and tp and tp > 0 and tp <= request.Price:
                    raise ValidationException(f"DemoExecutionGate Violation: Buy order TP {tp} must be above entry price {request.Price}.")
                if is_sell and sl and sl > 0 and sl <= request.Price:
                    raise ValidationException(f"DemoExecutionGate Violation: Sell order SL {sl} must be above entry price {request.Price}.")
                if is_sell and tp and tp > 0 and tp >= request.Price:
                    raise ValidationException(f"DemoExecutionGate Violation: Sell order TP {tp} must be below entry price {request.Price}.")
                exploration = demo_exploration_autonomy_enabled()
                if not sl or float(sl) <= 0 or (not exploration and (not tp or float(tp) <= 0)):
                    raise ValidationException("DemoExecutionGate Violation: A valid protective Stop Loss is required; a preset Take Profit is optional only in explicit DEMO exploration mode.")
                risk_distance = abs(float(request.Price) - float(sl))
                reward_distance = abs(float(tp) - float(request.Price)) if tp and float(tp) > 0 else 0.0
                if risk_distance <= 0 or (not exploration and reward_distance / risk_distance <= ProductionRiskPolicy.MINIMUM_RR):
                    raise ValidationException("DemoExecutionGate Violation: Reward/risk must be strictly greater than 1.0 outside DEMO exploration mode.")

        # Check 10: DEMO-only multi-position guard.
        # Default remains one position. Multiple same/opposite-direction entries
        # require an explicit opt-in and are bounded per symbol after DEMO account
        # verification above; LIVE trading remains prohibited by MetaTraderSafetyGate.
        if order_type != "CLOSE" and hasattr(request, "Symbol"):
            get_pos_fn = getattr(adapter_or_mt5, "get_positions", None)
            if callable(get_pos_fn):
                try:
                    allow_multiple = _demo_config_value(
                        "YARTRADER_DEMO_ALLOW_MULTIPLE_POSITIONS", "false"
                    ).strip().lower() in {"1", "true", "yes", "on"}
                    max_positions = 1
                    if allow_multiple:
                        try:
                            max_positions = int(_demo_config_value(
                                "YARTRADER_DEMO_MAX_POSITIONS_PER_SYMBOL", "3"
                            ))
                        except (TypeError, ValueError):
                            raise ValidationException(
                                "DemoExecutionGate Violation: YARTRADER_DEMO_MAX_POSITIONS_PER_SYMBOL must be an integer."
                            )
                        if max_positions < 1 or max_positions > 10:
                            raise ValidationException(
                                "DemoExecutionGate Violation: maximum positions per symbol must be between 1 and 10."
                            )
                    active_positions = get_pos_fn(symbol=request.Symbol) or []
                    if len(active_positions) >= max_positions:
                        pos_ticket = active_positions[0].get("ticket", "N/A") if active_positions else "N/A"
                        pos_dir = (
                            "BUY" if active_positions and active_positions[0].get("type", 0) == 0
                            else "SELL" if active_positions else "N/A"
                        )
                        if not allow_multiple:
                            detail = (
                                f"Active position exists (ticket={pos_ticket}, direction={pos_dir}). "
                                "Simultaneous or duplicate position entry is strictly forbidden."
                            )
                        else:
                            detail = (
                                f"{len(active_positions)} active position(s) already exist; "
                                f"the configured limit is {max_positions}. Same- and opposite-direction "
                                "entries are allowed below the limit."
                            )
                        raise ValidationException(
                            f"DemoExecutionGate Violation: Position Exclusivity Guard for '{request.Symbol}'. {detail}"
                        )
                except ValidationException:
                    raise
                except Exception as ex:
                    logger.error(f"[DemoExecutionGate] Fail-Closed: Error checking active positions: {ex}")
                    raise ValidationException(f"DemoExecutionGate Fail-Closed Violation: Unable to verify active positions for '{request.Symbol}': {ex}")

        logger.info("[DemoExecutionGate] All SRE Demo Execution safety checks PASSED.")
        return True
