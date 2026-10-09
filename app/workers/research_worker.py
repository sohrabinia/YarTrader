import os
import time
import math
import threading
from datetime import datetime
from typing import Optional, Dict, Any
from src.Application.Runtime.research_runtime import ResearchRuntime
from src.Application.Runtime.runtime_state import central_runtime_state
from src.Application.Runtime.research_runtime import validate_research_timeframe, MIN_RESEARCH_TIMEFRAME_SECONDS


def is_autonomous_demo_enabled() -> bool:
    """
    Fail-closed parser/gate for AUTONOMOUS_DEMO_TRADING_ENABLED.
    Strict Security Contract:
    - missing / absent -> False (BLOCK)
    - empty / None / whitespace -> False (BLOCK)
    - "false", "0", "no", "off", "1", "yes", unknown values -> False (BLOCK)
    - explicit "true" (case-insensitive, trimmed) -> True (ENABLE)
    - any parsing exception -> False (BLOCK)
    """
    try:
        raw_val = os.getenv("AUTONOMOUS_DEMO_TRADING_ENABLED")
        if raw_val is None:
            return False
        cleaned = raw_val.strip().lower()
        if cleaned == "true":
            return True
        return False
    except Exception:
        return False


class ResearchWorker:
    """Manages the background research worker polling loop."""
    def __init__(self, symbol: str = "XAUUSD", timeframe: str = "H1", interval_sec: float = 60.0, cooldown_sec: float = 300.0) -> None:
        self.default_symbol = symbol
        self.timeframe = validate_research_timeframe(timeframe)
        # Never schedule faster than the minimum M1 market cadence.
        self.interval_sec = max(float(interval_sec), MIN_RESEARCH_TIMEFRAME_SECONDS)
        self.cooldown_sec = cooldown_sec

        # Cache of active ResearchRuntimes per (symbol, timeframe)
        self.runtimes: Dict[Any, ResearchRuntime] = {}

        # Tracking last executed signal per symbol to prevent duplicate order spamming
        self.last_executed_signal: Dict[str, Dict[str, Any]] = {}

        self.is_running = False
        self.thread: Optional[threading.Thread] = None
        self.last_analysis_time: Optional[datetime] = None
        self.last_candle_time: Optional[datetime] = None
        self.status = "IDLE"
        self.error_count = 0
        self.demo_engine = None
        self.cycle_count = 0
        # Global single-flight guard: Brain/research cycles are strictly serialized.
        # A second worker/thread can never overlap an active research cycle.
        self._analysis_lock = threading.Lock()
        central_runtime_state.update_state("research_status", "Stopped")

    def _get_or_create_runtime(self, symbol: str, tf: str, asset_class: str = "Forex", provider: str = "MT5") -> ResearchRuntime:
        key = (symbol.upper(), tf.upper())
        if key not in self.runtimes:
            from src.Application.Deployment.storage import YarTraderStorageManager
            storage_mgr = YarTraderStorageManager.get_manager()
            self.runtimes[key] = ResearchRuntime(
                symbol=symbol.upper(),
                timeframe=tf.upper(),
                evidence_dir=os.path.join(storage_mgr.get_runtime_dir(), "research_logs"),
                provider_name=provider,
                asset_class=asset_class
            )
        return self.runtimes[key]

    def _get_active_matrix(self) -> list:
        try:
            from src.Market.Universe.symbol_registry import SymbolRegistry
            matrix = SymbolRegistry.get_instance().get_active_matrix()
            # Keep the configured multi-symbol active matrix in production.
            # Research and execution share the enabled multi-symbol registry.
            # Do not collapse production to one default symbol: each active symbol
            # is evaluated independently and must pass the same broker/risk gates.
            return matrix
        except Exception:
            return []

    @staticmethod
    def _is_market_data_unavailable_error(error: Exception) -> bool:
        """
        Classify an authoritative production market-data availability failure.

        A missing/unselected broker symbol is a per-symbol data condition, not a
        ResearchWorker lifecycle failure. It must be skipped without enabling
        synthetic data or weakening the production MT5 safety gate.
        """
        message = str(error).lower()
        return (
            "not selected or available in real mt5 terminal in production mode" in message
            or (
                "failed to fetch market data for primitive research" in message
                and "symbol" in message
                and "production mode" in message
            )
        )

    def start(self) -> None:
        """Starts the background worker thread."""
        if self.is_running:
            return
        self.is_running = True
        self.status = "RUNNING"
        central_runtime_state.update_multiple({
            "research_status": "Running",
            "research_worker_started_at": datetime.now().isoformat(),
            "research_cycle_started_at": None,
            "research_cycle_symbol": None,
            "research_cycle_timeframe": None,
            "research_last_error": None,
            "research_cycle_count": self.cycle_count,
        })
        self.thread = threading.Thread(target=self._run_loop, daemon=True, name="ResearchWorker")
        self.thread.start()

    def stop(self) -> None:
        """Stops the background worker gracefully."""
        self.is_running = False
        self.status = "STOPPED"
        central_runtime_state.update_state("research_status", "Stopped")
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5.0)

    def _validate_and_size_decision(self, symbol: str, sig_dir: str, decision_dict: dict) -> Optional[Dict[str, Any]]:
        """
        Canonical Fail-Closed Validation & 1.0% Risk Position Sizing Pipeline.
        Returns a dict with validated parameters and calculated volume_lots, or None if validation fails.
        """
        if not self.demo_engine or not hasattr(self.demo_engine, "adapter"):
            print(f"[ResearchWorker] Execution BLOCKED: Demo execution engine or adapter unavailable. Failing closed.")
            return None

        # 1. Obtain & Validate Authoritative Broker Account Info
        try:
            acc_info = self.demo_engine.adapter.get_account_info()
        except Exception as acc_err:
            print(f"[ResearchWorker] Broker get_account_info raised error: {acc_err}")
            acc_info = None

        if not acc_info or not isinstance(acc_info, dict):
            print(f"[ResearchWorker] Execution BLOCKED: Authoritative broker account info unavailable or invalid (acc_info={acc_info}). Failing closed.")
            return None

        raw_equity = acc_info.get("equity")
        equity_val = -1.0
        if raw_equity is not None:
            try:
                equity_val = float(raw_equity)
            except (ValueError, TypeError):
                equity_val = -1.0

        if equity_val <= 0 or not math.isfinite(equity_val):
            print(f"[ResearchWorker] Execution BLOCKED: Authoritative broker account equity unavailable or invalid (equity={raw_equity}). Failing closed.")
            return None

        raw_balance = acc_info.get("balance")
        try:
            balance_val = float(raw_balance)
        except (TypeError, ValueError):
            balance_val = -1.0
        if balance_val <= 0 or not math.isfinite(balance_val):
            print(f"[ResearchWorker] Execution BLOCKED: Authoritative current wallet balance unavailable or invalid (balance={raw_balance}). Failing closed.")
            return None
        risk_basis_val = min(balance_val, equity_val)

        raw_margin = acc_info.get("free_margin")
        free_margin_val = -1.0
        if raw_margin is not None:
            try:
                free_margin_val = float(raw_margin)
            except (ValueError, TypeError):
                free_margin_val = -1.0

        if free_margin_val <= 0 or not math.isfinite(free_margin_val):
            print(f"[ResearchWorker] Execution BLOCKED: Authoritative broker account free_margin unavailable or invalid (free_margin={raw_margin}). Failing closed.")
            return None

        # 1b. Enforce Daily 8% Loss Limit Protection Gate
        try:
            from src.Risk.Services.daily_loss_kill_switch import DailyLossKillSwitch
            kill_switch = DailyLossKillSwitch.get_instance()
            from datetime import datetime, timezone
            risk_now = datetime.now(timezone.utc)
            bot_daily_pnl = None
            if type(self.demo_engine.adapter).__name__ == "RealMT5BrokerAdapter":
                from src.Risk.Services.daily_loss_kill_switch import calculate_yartrader_daily_pnl
                bot_daily_pnl = calculate_yartrader_daily_pnl(
                    self.demo_engine.adapter, now_utc=risk_now
                )["total_pnl"]
            allowed, reason, meta = kill_switch.evaluate_daily_loss(
                equity_val, now_utc=risk_now, bot_daily_pnl=bot_daily_pnl
            )
            if not allowed:
                print(f"[ResearchWorker] Execution BLOCKED: Daily Loss Limit Gate active ({reason}, loss={meta.get('loss_pct', 0.0)}%). Failing closed.")
                return None
        except Exception as ks_err:
            print(f"[ResearchWorker] Execution BLOCKED: DailyLossKillSwitch evaluation raised error: {ks_err}. Failing closed.")
            return None

        # 2. Obtain & Validate Authoritative Broker Symbol Metadata
        sym_info = self.demo_engine.adapter.get_symbol_info(symbol) if hasattr(self.demo_engine.adapter, "get_symbol_info") else None
        if not sym_info or not isinstance(sym_info, dict) or "volume_min" not in sym_info or "volume_max" not in sym_info or "volume_step" not in sym_info:
            print(f"[ResearchWorker] Execution BLOCKED: Authoritative broker symbol info unavailable or missing volume limits for {symbol} (sym_info={sym_info}). Failing closed.")
            return None

        try:
            vol_min = float(sym_info["volume_min"])
            vol_max = float(sym_info["volume_max"])
            vol_step = float(sym_info["volume_step"])
        except (ValueError, TypeError):
            vol_min = vol_max = vol_step = -1.0

        if (vol_min <= 0 or not math.isfinite(vol_min) or
            vol_max <= 0 or not math.isfinite(vol_max) or
            vol_step <= 0 or not math.isfinite(vol_step)):
            print(f"[ResearchWorker] Execution BLOCKED: Authoritative broker symbol volume limits invalid for {symbol} (min={vol_min}, max={vol_max}, step={vol_step}). Failing closed.")
            return None

        # 3. Validate the model's entry against a fresh broker quote. Never submit stale model prices.
        raw_price = decision_dict.get("entry")
        raw_sl = decision_dict.get("stop_loss")
        raw_tp = decision_dict.get("take_profit")
        try:
            model_entry = float(raw_price)
            sl_val = float(raw_sl)
            tp_val = float(raw_tp)
        except (ValueError, TypeError):
            print(f"[ResearchWorker] Execution BLOCKED: Decision entry/SL/TP missing or non-numeric for {symbol} {sig_dir}.")
            return None
        if any(not math.isfinite(v) or v <= 0 for v in (model_entry, sl_val, tp_val)):
            print(f"[ResearchWorker] Execution BLOCKED: Decision entry/SL/TP invalid for {symbol} {sig_dir}.")
            return None

        try:
            tick = self.demo_engine.adapter.get_symbol_tick(symbol)
        except Exception as tick_err:
            print(f"[ResearchWorker] Execution BLOCKED: Fresh broker tick unavailable for {symbol}: {tick_err}.")
            return None
        if not isinstance(tick, dict):
            print(f"[ResearchWorker] Execution BLOCKED: Fresh broker tick unavailable for {symbol}.")
            return None
        quote_key = "ask" if sig_dir == "BUY" else "bid"
        try:
            price_val = float(tick.get(quote_key, 0.0))
        except (ValueError, TypeError):
            price_val = 0.0
        if not math.isfinite(price_val) or price_val <= 0:
            print(f"[ResearchWorker] Execution BLOCKED: Fresh broker {quote_key} quote is invalid for {symbol}.")
            return None

        max_drift_pct = float(os.getenv("MAX_DEMO_ENTRY_DRIFT_PCT", "0.5"))
        drift_pct = abs(model_entry - price_val) / price_val * 100.0
        if not math.isfinite(max_drift_pct) or max_drift_pct <= 0 or drift_pct > max_drift_pct:
            print(f"[ResearchWorker] Execution BLOCKED: Model entry is stale for {symbol} {sig_dir} (drift={drift_pct:.3f}% > max={max_drift_pct}%).")
            return None

        if sig_dir == "BUY":
            geometry_valid = sl_val < price_val < tp_val
        else:
            geometry_valid = tp_val < price_val < sl_val
        if not geometry_valid:
            print(f"[ResearchWorker] Execution BLOCKED: SL/TP do not bracket the fresh {quote_key} quote for {symbol} {sig_dir} (price={price_val}, sl={sl_val}, tp={tp_val}).")
            return None

        risk_distance = abs(price_val - sl_val)
        reward_distance = abs(tp_val - price_val)
        live_rr = reward_distance / risk_distance if risk_distance > 0 else 0.0
        min_rr = float(os.getenv("MINIMUM_RR", "1.5"))
        if not math.isfinite(live_rr) or live_rr < min_rr:
            print(f"[ResearchWorker] Execution BLOCKED: Live-quote risk/reward {live_rr:.3f} is below minimum {min_rr} for {symbol} {sig_dir}.")
            return None

        # 4. Shared broker-authoritative sizing: same 1.0% wallet policy as the
        # autonomous DEMO trader. MT5 order_calc_profit uses the actual symbol's
        # contract/tick-value conventions; no fixed-lot fallback is permitted.
        from src.Risk.Services.professional_risk_engine import ProductionRiskPolicy
        canonical_risk_pct = float(ProductionRiskPolicy.TARGET_RISK_PCT)
        raw_risk_env = os.getenv("RISK_PCT_PER_TRADE", str(canonical_risk_pct))
        try:
            req_risk_f = float(raw_risk_env)
            if (not math.isfinite(req_risk_f) or req_risk_f <= 0.0
                    or req_risk_f > ProductionRiskPolicy.HARD_CEILING_RISK_PCT
                    or not math.isclose(req_risk_f, canonical_risk_pct, rel_tol=0.0, abs_tol=1e-9)):
                print(f"[ResearchWorker] Execution BLOCKED: RISK_PCT_PER_TRADE ({raw_risk_env}) must match canonical {canonical_risk_pct:.2f}% policy.")
                return None
        except (ValueError, TypeError):
            print(f"[ResearchWorker] Execution BLOCKED: Requested risk_pct ({raw_risk_env}) is non-numeric.")
            return None

        mt5 = getattr(self.demo_engine.adapter, "_mt5", None)
        if mt5 is None or not callable(getattr(mt5, "order_calc_profit", None)):
            print(f"[ResearchWorker] Execution BLOCKED: Broker-authoritative PnL calculator unavailable for {symbol}.")
            return None
        try:
            from src.Execution.Services.autonomous_demo_trader import calculate_demo_volume_by_risk
            sizing = calculate_demo_volume_by_risk(
                mt5=mt5, symbol=symbol, direction=sig_dir,
                entry=price_val, stop_loss=sl_val, symbol_info=sym_info,
                balance=balance_val, equity=equity_val, risk_pct=canonical_risk_pct,
            )
        except Exception as sizing_error:
            print(f"[ResearchWorker] Broker-authoritative sizing rejected {symbol}: {sizing_error}")
            return None
        if not sizing.get("allowed"):
            print(f"[ResearchWorker] Position sizing rejected for {symbol} {sig_dir}: {sizing.get('reason')}")
            return None

        return {
            "equity": equity_val,
            "free_margin": free_margin_val,
            "price": price_val,
            "sl": sl_val,
            "tp": float(raw_tp) if raw_tp is not None else None,
            "volume_lots": float(sizing["volume"]),
            "risk_budget_usd": float(sizing["risk_budget_usd"]),
            "estimated_risk_usd": float(sizing["estimated_risk_usd"]),
            "risk_per_trade_pct": canonical_risk_pct,
        }

    def _run_loop(self) -> None:
        """Worker loop running on the background thread."""
        try:
            from src.Market.Universe.symbol_registry import SymbolRegistry
            registry = SymbolRegistry.get_instance()
            active_matrix = self._get_active_matrix()
            unique_symbols = sorted(list(set(s for s, t, ac, p in active_matrix)))
            configured_tfs = sorted(list(set(t for s, t, ac, p in active_matrix)))

            print("================================================")
            print("YarTrader Multi-Symbol / Multi-TF Runtime")
            print("================================================")
            print(f"Registry Capacity:\n{registry.max_symbols} Symbols\n")
            print(f"Registered Symbols:\n{len(registry.get_all_registered())}\n")
            print(f"Active Symbols:\n{len(unique_symbols)}\n")
            print(f"Configured Timeframes:\n{configured_tfs}\n")
            print("Research Workers:\nRunning\n")
            print(f"Queue Size:\n{len(active_matrix)} ({len(unique_symbols)} symbols x {len(configured_tfs)} timeframes)\n")
            print("Mode:\nProduction")
            print("================================================\n")

            while self.is_running:
                active_matrix = self._get_active_matrix()

                for symbol, tf, asset_class, provider in active_matrix:
                    if not self.is_running:
                        break

                    try:
                        print(f"Research Started\nSymbol: {symbol}\nTimeframe: {tf}")

                        runtime = self._get_or_create_runtime(symbol, tf, asset_class, provider)

                        # Active read-only connection check
                        conn_health = runtime.provider.delegate.get_connection_health()
                        p_name = getattr(runtime, "_provider_name", "MT5")
                        if p_name == "ControlledOfflineFixture":
                            print("ControlledOfflineFixture: Connected (100% Offline)")
                        else:
                            print("MT5: Connected")

                        # Strict single-flight: never run two Brain/research cycles at once.
                        acquired = self._analysis_lock.acquire(blocking=False)
                        if not acquired:
                            print("[ResearchWorker] Research cycle skipped: another Brain/research cycle is still running.")
                            continue
                        central_runtime_state.update_multiple({
                            "research_cycle_started_at": datetime.now().isoformat(),
                            "research_cycle_symbol": symbol,
                            "research_cycle_timeframe": tf,
                        })
                        try:
                            res = runtime.run_once()
                        finally:
                            self._analysis_lock.release()

                        self.last_analysis_time = datetime.now()
                        if res.Request.EndTime:
                            self.last_candle_time = res.Request.EndTime
                        self.status = "RUNNING"
                        self.error_count = 0
                        self.cycle_count += 1
                        central_runtime_state.update_multiple({
                            "research_status": "Running",
                            "last_cycle_time": self.last_analysis_time.isoformat(),
                            "research_cycle_count": self.cycle_count,
                            "research_last_successful_cycle": self.last_analysis_time.isoformat(),
                            "research_last_error": None,
                            "research_cycle_started_at": None,
                            "research_cycle_symbol": None,
                            "research_cycle_timeframe": None,
                        })

                        candles_count = len(res.Findings.get("pipeline_outputs", {}).get("technical_analysis", {}).get("candles", []))
                        print(f"Candles: {candles_count}")
                        print("Features: Generated")
                        print("Research: Completed\n")

                        # Execution eligibility is determined by the canonical active-symbol
                        # registry and broker-authoritative risk sizing, never by a gold-only gate.
                        # Every enabled symbol reaches the same signal, freshness, risk and DEMO gates.

                        # DEMO Execution Bridge: Consume AutonomousTradingDecision with Kill Switch, RR, and Cooldown gates
                        auto_dec = res.Findings.get("autonomous_decision", {})
                        action = auto_dec.get("action", "WAIT")

                        # 1. Kill Switch Enforcement
                        kill_switch_enabled = is_autonomous_demo_enabled()
                        if not kill_switch_enabled:
                            print(f"[ResearchWorker] Kill Switch ACTIVE (AUTONOMOUS_DEMO_TRADING_ENABLED=False). Skipping execution dispatch for {symbol}.")
                        elif action in ["BUY", "SELL"]:
                            sig_dir = action
                            now_time = time.time()
                            sig_time = now_time

                            # 2. Risk & Confidence Threshold Gates
                            min_rr = float(os.getenv("MINIMUM_RR", "1.5"))
                            min_conf = float(os.getenv("MINIMUM_CONFIDENCE", "50.0"))

                            rr_val = float(auto_dec.get("risk_reward", 0.0))
                            conf_val = float(auto_dec.get("confidence", 0.0))

                            if rr_val < min_rr:
                                print(f"[ResearchWorker] Decision for {symbol} {sig_dir} REJECTED by Risk Gate: RR {rr_val} < min_rr {min_rr}.")
                            elif conf_val < min_conf:
                                print(f"[ResearchWorker] Decision for {symbol} {sig_dir} REJECTED by Risk Gate: Confidence {conf_val} < min_conf {min_conf}.")
                            else:
                                # 3. Duplicate & Cooldown Gate
                                last_exec = self.last_executed_signal.get(symbol.upper())
                                is_cooldown = False
                                if last_exec is not None:
                                    elapsed = now_time - last_exec.get("exec_time", 0)
                                    is_same_signal = (last_exec.get("direction") == sig_dir)
                                    if is_same_signal and elapsed < self.cooldown_sec:
                                        print(f"[ResearchWorker] Signal for {symbol} {sig_dir} skipped (DEDUPLICATED / COOLDOWN active: {int(elapsed)}s < {int(self.cooldown_sec)}s).")
                                        is_cooldown = True

                                if not is_cooldown:
                                    try:
                                        from src.Execution.Services.demo_execution_engine import DemoExecutionEngine
                                        if self.demo_engine is None:
                                            self.demo_engine = DemoExecutionEngine(demo_mode=True)

                                        # Check active broker positions to enforce Position Exclusivity Guard
                                        active_positions = self.demo_engine.get_active_positions(symbol=symbol)
                                        if active_positions and len(active_positions) > 0:
                                            existing_ticket = active_positions[0].get("ticket", 0)
                                            existing_dir_code = active_positions[0].get("type", 0)
                                            existing_dir = "BUY" if existing_dir_code == 0 else "SELL"

                                            if existing_dir == sig_dir:
                                                print(f"[ResearchWorker] Duplicate position guard triggered: {symbol} already has active {existing_dir} position (ticket={existing_ticket}). Skipping.")
                                            else:
                                                # Opposite direction decision detected: Enforce Sequential Reversal Lifecycle
                                                # OPEN -> CLOSE REQUESTED -> CLOSE CONFIRMED -> REASSESS -> OPPOSITE ENTRY
                                                print(f"[ResearchWorker] Sequential Reversal Triggered: Existing active {existing_dir} position found for {symbol}. Requesting close before reassessment...")
                                                close_resp = self.demo_engine.close_position(
                                                    symbol=symbol,
                                                    position_ticket=existing_ticket,
                                                    comment=f"YarTrader RevClose {symbol}"
                                                )

                                                # Explicitly evaluate close response status before market reassessment
                                                if close_resp.Status not in ["Placed", "Closed"]:
                                                    print(f"[ResearchWorker] Reversal BLOCKED: Position {existing_ticket} close request failed (Status={close_resp.Status}, Comment={close_resp.Comment}). Failing closed.")
                                                else:
                                                    # Authoritative broker position verification: confirm symbol is flat
                                                    remaining_pos = self.demo_engine.get_active_positions(symbol=symbol)
                                                    is_closed = not any(str(p.get("ticket", "")) == str(existing_ticket) for p in remaining_pos)

                                                    if not is_closed:
                                                        print(f"[ResearchWorker] Reversal BLOCKED: Position {existing_ticket} close unconfirmed / pending in broker state. Failing closed.")
                                                    else:
                                                        print(f"[ResearchWorker] Position {existing_ticket} close CONFIRMED flat. Reassessing market for {symbol} {sig_dir}...")
                                                        # Fresh Market Reassessment: Must be self-contained
                                                        reassess_run = runtime.run_once()
                                                        reassess_dec = reassess_run.Findings.get("autonomous_decision", {})
                                                        reassess_action = reassess_dec.get("action", "WAIT")

                                                        if reassess_action == sig_dir:
                                                            # Run Reversal Decision through Canonical Validation & 1.0% Risk Position Sizing
                                                            rev_sized = self._validate_and_size_decision(symbol, sig_dir, reassess_dec)
                                                            if rev_sized:
                                                                decision_id = f"DEC-REV-{symbol.upper()}-{sig_dir}-{int(sig_time)}"
                                                                exec_resp = self.demo_engine.execute_demo_decision(
                                                                    symbol=symbol,
                                                                    direction=sig_dir,
                                                                    volume=rev_sized["volume_lots"],
                                                                    price=rev_sized["price"],
                                                                    sl=rev_sized["sl"],
                                                                    tp=rev_sized["tp"],
                                                                    comment=f"YarTrader REV {symbol}",
                                                                    magic=143056,
                                                                    decision_id=decision_id
                                                                )

                                                                if exec_resp and exec_resp.Status in ["Placed", "Closed", "Executed", "OK", "Success"]:
                                                                    self.last_executed_signal[symbol.upper()] = {
                                                                        "direction": sig_dir,
                                                                        "sig_time": sig_time,
                                                                        "exec_time": now_time,
                                                                        "decision_id": decision_id
                                                                    }
                                                                    print(f"[ResearchWorker] Reversal DEMO Execution Response: Status={exec_resp.Status}, OrderId={exec_resp.OrderId}")
                                                                else:
                                                                    print(f"[ResearchWorker] Reversal DEMO Execution FAILED / Rejected (Status={exec_resp.Status if exec_resp else 'None'}). State NOT mutated.")
                                                            else:
                                                                print(f"[ResearchWorker] Reversal BLOCKED: Reassessment decision for {symbol} failed validation / position sizing. Remaining flat.")
                                                        else:
                                                            print(f"[ResearchWorker] Reversal aborted: Reassessment action for {symbol} is {reassess_action} (opposite entry not independently confirmed). Remaining flat.")
                                        else:
                                            # Flat state: Canonical Single Execution Path
                                            flat_sized = self._validate_and_size_decision(symbol, sig_dir, auto_dec)
                                            if flat_sized:
                                                calculated_vol = flat_sized["volume_lots"]
                                                decision_id = auto_dec.get("decision_id", f"DEC-{symbol.upper()}-{sig_dir}-{int(sig_time)}")

                                                print(f"[ResearchWorker] Actionable decision detected for {symbol}: {sig_dir} with 1.0% risk volume = {calculated_vol} lots (Equity=${flat_sized['equity']}). Dispatching...")
                                                exec_resp = self.demo_engine.execute_demo_decision(
                                                    symbol=symbol,
                                                    direction=sig_dir,
                                                    volume=calculated_vol,
                                                    price=flat_sized["price"],
                                                    sl=flat_sized["sl"],
                                                    tp=flat_sized["tp"],
                                                    comment=f"YarTrader DEMO {symbol}",
                                                    magic=143056,
                                                    decision_id=decision_id
                                                )

                                                # Update execution state ONLY if execution response confirms order placement/execution
                                                if exec_resp and exec_resp.Status in ["Placed", "Closed", "Executed", "OK", "Success"]:
                                                    self.last_executed_signal[symbol.upper()] = {
                                                        "direction": sig_dir,
                                                        "sig_time": sig_time,
                                                        "exec_time": now_time,
                                                        "decision_id": decision_id
                                                    }
                                                    print(f"[ResearchWorker] DEMO Execution Response: Status={exec_resp.Status}, OrderId={exec_resp.OrderId}")
                                                else:
                                                    print(f"[ResearchWorker] DEMO Execution FAILED / Rejected (Status={exec_resp.Status if exec_resp else 'None'}). State NOT mutated.")
                                    except Exception as exec_err:
                                        print(f"[ResearchWorker] DEMO Execution Gate / Fail-Closed: {exec_err}")
                        else:
                            print(f"[ResearchWorker] Symbol {symbol} decision is {action}. Continuation loop proceeding.")

                        central_runtime_state.update_multiple({
                            "research_status": "Running",
                            "last_cycle_time": self.last_analysis_time.isoformat()
                        })
                    except Exception as e:
                        if self._is_market_data_unavailable_error(e):
                            # A broker symbol can be unavailable while the MT5 bridge and the
                            # rest of the research universe remain healthy. Do not poison the
                            # worker lifecycle state or enable synthetic/fallback market data.
                            self.status = "RUNNING"
                            central_runtime_state.update_multiple({
                                "research_status": "Running",
                                "research_last_error": str(e),
                                "research_cycle_started_at": None,
                                "research_cycle_symbol": None,
                                "research_cycle_timeframe": None,
                            })
                            print(
                                f"[ResearchWorker] DATA_UNAVAILABLE/SKIPPED for {symbol} {tf}: "
                                f"{type(e).__name__}: {e}"
                            )
                            continue

                        self.error_count += 1
                        self.status = "RECOVERING"
                        central_runtime_state.update_multiple({
                            "research_status": "Recovering",
                            "research_last_error": f"{type(e).__name__}: {e}",
                            "research_cycle_started_at": None,
                            "research_cycle_symbol": None,
                            "research_cycle_timeframe": None,
                        })
                        # Never swallow research-cycle failures: production diagnosis must retain
                        # the exact symbol/timeframe, exception type, and traceback.
                        import traceback
                        error_context = (
                            f"Research cycle error for {symbol} {tf}: "
                            f"{type(e).__name__}: {e}"
                        )
                        print(f"[ResearchWorker] {error_context}")
                        print(traceback.format_exc())
                        try:
                            from app.core.logging import log_event
                            log_event(
                                "ERROR",
                                error_context,
                                source="research_worker",
                            )
                            log_event(
                                "ERROR",
                                traceback.format_exc().rstrip(),
                                source="research_worker",
                            )
                        except Exception:
                            pass
                        # Graceful quick delay before next asset if error happens
                        time.sleep(0.5)

                # Wait for the next interval
                sleep_elapsed = 0.0
                while sleep_elapsed < self.interval_sec and self.is_running:
                    time.sleep(0.1)
                    sleep_elapsed += 0.1
        finally:
            self.status = "STOPPED"
            central_runtime_state.update_state("research_status", "Stopped")
