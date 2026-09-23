import os
import time
import math
import threading
from datetime import datetime
from typing import Optional, Dict, Any
from src.Application.Runtime.research_runtime import ResearchRuntime
from src.Application.Runtime.runtime_state import central_runtime_state
from src.ShadowTrading.Engine.PredictiveShadowEngine import PredictiveShadowEngine


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
        self.timeframe = timeframe
        self.interval_sec = interval_sec
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
        self.last_diagnostic_events: Dict[str, Dict[str, Any]] = {}
        central_runtime_state.update_state("research_status", "Stopped")

    def _record_non_trade_event(self, symbol: str, timeframe: str, reason: str, details: Optional[str] = None, decision_id: Optional[str] = None) -> None:
        """Records structured diagnostic event explaining why a trade was not executed."""
        evt = {
            "timestamp": datetime.now().isoformat(),
            "symbol": symbol.upper(),
            "timeframe": timeframe.upper(),
            "reason": reason,
            "details": details or "",
            "decision_id": decision_id or ""
        }
        self.last_diagnostic_events[symbol.upper()] = evt
        try:
            central_runtime_state.update_state(f"last_diagnostic_{symbol.upper()}", evt)
        except Exception:
            pass

    def get_last_diagnostic_status(self, symbol: str = "XAUUSD") -> Dict[str, Any]:
        """Operator diagnostic helper answering 'Why did YarTrader not trade this cycle?'"""
        return self.last_diagnostic_events.get(symbol.upper(), {
            "timestamp": datetime.now().isoformat(),
            "symbol": symbol.upper(),
            "reason": "NO_ANALYSIS_EXECUTED_YET",
            "details": "Worker cycle has not evaluated this symbol yet."
        })

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
            from src.ShadowTrading.Engine.SymbolRegistry import SymbolRegistry
            return SymbolRegistry.get_instance().get_active_matrix()
        except Exception:
            return [(self.default_symbol, self.timeframe, "Commodities", "MT5")]

    def start(self) -> None:
        """Starts the background worker thread."""
        if self.is_running:
            return
        self.is_running = True
        self.status = "RUNNING"
        central_runtime_state.update_state("research_status", "Running")
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
        Canonical Fail-Closed Validation & 0.5% Risk Position Sizing Pipeline.
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
            allowed, reason, meta = kill_switch.evaluate_daily_loss(equity_val)
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

        # 3. Validate Entry Price and Stop Loss Parameters Without Fallbacks
        raw_price = decision_dict.get("entry")
        raw_sl = decision_dict.get("stop_loss")
        raw_tp = decision_dict.get("take_profit")

        price_val = -1.0
        sl_val = -1.0
        if raw_price is not None and raw_sl is not None:
            try:
                price_val = float(raw_price)
                sl_val = float(raw_sl)
            except (ValueError, TypeError):
                price_val = sl_val = -1.0

        is_valid_prices = (
            price_val > 0 and sl_val > 0 and
            math.isfinite(price_val) and math.isfinite(sl_val)
        )

        if is_valid_prices:
            if sig_dir == "BUY" and sl_val >= price_val:
                is_valid_prices = False
            elif sig_dir == "SELL" and sl_val <= price_val:
                is_valid_prices = False

        if not is_valid_prices:
            print(f"[ResearchWorker] Execution BLOCKED: Decision entry/SL parameters missing or invalid for {symbol} {sig_dir} (entry={raw_price}, sl={raw_sl}). Failing closed.")
            return None

        # 4. Calculate Risk Position Sizing (hard max ceiling 2.0% risk)
        from src.Risk.Services.professional_risk_engine import ProfessionalRiskEngine
        risk_engine = ProfessionalRiskEngine()

        # Target requested risk percentage (Fail-Closed: target 0.5%, strictly <= 2.0%)
        raw_risk_env = os.getenv("RISK_PCT_PER_TRADE", "0.5")
        try:
            req_risk_f = float(raw_risk_env) if not isinstance(raw_risk_env, bool) else -1.0
            if not math.isfinite(req_risk_f) or req_risk_f <= 0.0 or req_risk_f > 2.0:
                print(f"[ResearchWorker] Execution BLOCKED: Requested risk_pct ({raw_risk_env}) is invalid or exceeds 2.0% ceiling. Failing closed.")
                return None
            requested_risk_pct = req_risk_f
        except (ValueError, TypeError):
            print(f"[ResearchWorker] Execution BLOCKED: Requested risk_pct ({raw_risk_env}) is non-numeric. Failing closed.")
            return None

        sizing_res = risk_engine.evaluate_equity_risk_and_position_size(
            symbol=symbol,
            direction=sig_dir,
            entry_price=price_val,
            stop_loss=sl_val,
            account_equity=equity_val,
            free_margin=free_margin_val,
            risk_pct=requested_risk_pct,
            volume_min=vol_min,
            volume_max=vol_max,
            volume_step=vol_step
        )

        if not sizing_res.is_valid:
            print(f"[ResearchWorker] Position sizing rejected for {symbol} {sig_dir}: {sizing_res.rejection_reason}")
            return None

        return {
            "equity": equity_val,
            "free_margin": free_margin_val,
            "price": price_val,
            "sl": sl_val,
            "tp": float(raw_tp) if raw_tp is not None else None,
            "volume_lots": sizing_res.volume_lots,
            "risk_budget_usd": sizing_res.risk_budget_usd
        }

    def _run_loop(self) -> None:
        """Worker loop running on the background thread."""
        try:
            from src.ShadowTrading.Engine.SymbolRegistry import SymbolRegistry
            registry = SymbolRegistry.get_instance()
            active_matrix = registry.get_active_matrix()
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

                    # Phase 1 Scope Boundary: Trading Core & execution dispatch are strictly XAUUSD ONLY
                    if symbol.upper() != "XAUUSD":
                        continue

                    try:
                        print(f"Research Started\nSymbol: {symbol}\nTimeframe: {tf}")

                        runtime = self._get_or_create_runtime(symbol, tf, asset_class, provider)

                        # Active read-only connection check
                        conn_health = runtime.provider.delegate.get_connection_health()
                        is_healthy = bool(isinstance(conn_health, dict) and conn_health.get("connected") is True and conn_health.get("status") in ["HEALTHY", "CONNECTED", "OK"])

                        if not is_healthy:
                            last_err = conn_health.get("reason") or conn_health.get("last_error") if isinstance(conn_health, dict) else None
                            if not last_err:
                                last_err = "MT5 process disconnected or terminal unavailable"
                            print(f"[ResearchWorker] MT5 Connection Health Check FAILED for {symbol} {tf}: {last_err}")
                            from app.core.logging import log_event
                            log_event("WARNING", f"ResearchWorker MT5_DISCONNECTED for {symbol} {tf}: {last_err}")
                            central_runtime_state.update_state("research_status", "MT5_Disconnected")
                            self._record_non_trade_event(symbol, tf, "MT5_DISCONNECTED", details=str(last_err))
                            continue

                        print("MT5: Connected")

                        res = runtime.run_once()

                        self.last_analysis_time = datetime.now()
                        if res.Request.EndTime:
                            self.last_candle_time = res.Request.EndTime
                        self.status = "RUNNING"
                        self.error_count = 0

                        candles_count = len(res.Findings.get("pipeline_outputs", {}).get("technical_analysis", {}).get("candles", []))
                        print(f"Candles: {candles_count}")
                        print("Features: Generated")
                        print("Research: Completed\n")

                        # DEMO Execution Bridge: Consume AutonomousTradingDecision with Kill Switch, RR, and Cooldown gates
                        auto_dec = res.Findings.get("autonomous_decision", {})
                        action = auto_dec.get("action", "WAIT")

                        # 1. Kill Switch Enforcement
                        kill_switch_enabled = is_autonomous_demo_enabled()
                        if not kill_switch_enabled:
                            print(f"[ResearchWorker] Kill Switch ACTIVE (AUTONOMOUS_DEMO_TRADING_ENABLED=False). Skipping execution dispatch for {symbol}.")
                            self._record_non_trade_event(symbol, tf, "AUTONOMOUS_DEMO_DISABLED", details="AUTONOMOUS_DEMO_TRADING_ENABLED=False", decision_id=auto_dec.get("decision_id"))
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
                                self._record_non_trade_event(symbol, tf, "RR_BELOW_MINIMUM", details=f"RR {rr_val} < min_rr {min_rr}", decision_id=auto_dec.get("decision_id"))
                            elif conf_val < min_conf:
                                print(f"[ResearchWorker] Decision for {symbol} {sig_dir} REJECTED by Risk Gate: Confidence {conf_val} < min_conf {min_conf}.")
                                self._record_non_trade_event(symbol, tf, "CONFIDENCE_BELOW_MINIMUM", details=f"Confidence {conf_val} < min_conf {min_conf}", decision_id=auto_dec.get("decision_id"))
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
                                        self._record_non_trade_event(symbol, tf, "COOLDOWN", details=f"Deduplicated / Cooldown active ({int(elapsed)}s < {int(self.cooldown_sec)}s)", decision_id=auto_dec.get("decision_id"))

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
                                                self._record_non_trade_event(symbol, tf, "POSITION_ALREADY_OPEN", details=f"Active position exists (ticket={existing_ticket})", decision_id=auto_dec.get("decision_id"))
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
                                                            # Run Reversal Decision through Canonical Validation & 0.5% Risk Position Sizing
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
                                                            self._record_non_trade_event(symbol, tf, "REVERSAL_ABORTED", details=f"Reassessment action is {reassess_action}", decision_id=auto_dec.get("decision_id"))
                                        else:
                                            # Flat state: Canonical Single Execution Path
                                            flat_sized = self._validate_and_size_decision(symbol, sig_dir, auto_dec)
                                            if flat_sized:
                                                calculated_vol = flat_sized["volume_lots"]
                                                decision_id = auto_dec.get("decision_id", f"DEC-{symbol.upper()}-{sig_dir}-{int(sig_time)}")

                                                print(f"[ResearchWorker] Actionable decision detected for {symbol}: {sig_dir} with 0.5% risk volume = {calculated_vol} lots (Equity=${flat_sized['equity']}). Dispatching...")
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
                                                    self._record_non_trade_event(symbol, tf, "BROKER_ORDER_SEND_FAILED", details=f"Status={exec_resp.Status if exec_resp else 'None'}", decision_id=decision_id)
                                            else:
                                                self._record_non_trade_event(symbol, tf, "RISK_GATE_REJECTED", details="Position sizing or risk gate failed", decision_id=auto_dec.get("decision_id"))
                                    except Exception as exec_err:
                                        print(f"[ResearchWorker] DEMO Execution Gate / Fail-Closed: {exec_err}")
                                        self._record_non_trade_event(symbol, tf, "EXECUTION_GATE_REJECTED", details=str(exec_err), decision_id=auto_dec.get("decision_id"))
                        else:
                            print(f"[ResearchWorker] Symbol {symbol} decision is {action}. Continuation loop proceeding.")
                            self._record_non_trade_event(symbol, tf, "WAIT_DECISION", details=f"Action is {action}", decision_id=auto_dec.get("decision_id"))

                        central_runtime_state.update_multiple({
                            "research_status": "Running",
                            "last_cycle_time": self.last_analysis_time.isoformat()
                        })
                    except Exception as e:
                        import traceback
                        err_tb = traceback.format_exc()
                        self.error_count += 1
                        self.status = "RECOVERING"
                        central_runtime_state.update_state("research_status", "Recovering")
                        from app.core.logging import log_event
                        log_event("ERROR", f"ResearchWorker Exception in cycle for {symbol} {tf} ({type(e).__name__}): {e}\n{err_tb}")
                        print(f"[ResearchWorker] EXCEPTION in cycle for {symbol} {tf} ({type(e).__name__}): {e}")
                        self._record_non_trade_event(symbol, tf, "WORKER_EXCEPTION", details=f"{type(e).__name__}: {e}")
                        time.sleep(0.5)

                # Wait for the next interval
                sleep_elapsed = 0.0
                while sleep_elapsed < self.interval_sec and self.is_running:
                    time.sleep(0.1)
                    sleep_elapsed += 0.1
        finally:
            self.status = "STOPPED"
            central_runtime_state.update_state("research_status", "Stopped")
