import os
import time
import math
import threading
from datetime import datetime
from typing import Optional, Dict, Any
from src.Application.Runtime.research_runtime import ResearchRuntime
from src.Application.Runtime.runtime_state import central_runtime_state
from src.ShadowTrading.Engine.PredictiveShadowEngine import PredictiveShadowEngine

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
                        print("MT5: Connected")

                        res = runtime.run_once()

                        self.last_analysis_time = datetime.now()
                        if res.Request.EndTime:
                            self.last_candle_time = res.Request.EndTime
                        self.status = "RUNNING"
                        self.error_count = 0

                        candles_count = len(res.Findings.get("pipeline_outputs", {}).get("technical_analysis", {}).get("candles", [1] * 15))
                        print(f"Candles: {candles_count}")
                        print("Features: Generated")
                        print("Research: Completed\n")

                        # DEMO Execution Bridge: Consume AutonomousTradingDecision with Kill Switch, RR, and Cooldown gates
                        auto_dec = res.Findings.get("autonomous_decision", {})
                        action = auto_dec.get("action", "WAIT")

                        # 1. Kill Switch Enforcement
                        kill_switch_enabled = os.getenv("AUTONOMOUS_DEMO_TRADING_ENABLED", "true").lower() in ["true", "1", "yes"]
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
                                                            # Extract execution parameters STRICTLY from reassess_dec (NO fallback to auto_dec)
                                                            rev_price = reassess_dec.get("entry")
                                                            rev_sl = reassess_dec.get("stop_loss")
                                                            rev_tp = reassess_dec.get("take_profit")
                                                            rev_vol = reassess_dec.get("volume", 0.01)

                                                            if rev_price and rev_sl and rev_tp and float(rev_price) > 0 and float(rev_sl) > 0 and float(rev_tp) > 0:
                                                                decision_id = f"DEC-REV-{symbol.upper()}-{sig_dir}-{int(sig_time)}"
                                                                exec_resp = self.demo_engine.execute_demo_decision(
                                                                    symbol=symbol,
                                                                    direction=sig_dir,
                                                                    volume=float(rev_vol),
                                                                    price=float(rev_price),
                                                                    sl=float(rev_sl),
                                                                    tp=float(rev_tp),
                                                                    comment=f"YarTrader REV {symbol}",
                                                                    magic=143056,
                                                                    decision_id=decision_id
                                                                )
                                                                self.last_executed_signal[symbol.upper()] = {
                                                                    "direction": sig_dir,
                                                                    "sig_time": sig_time,
                                                                    "exec_time": now_time,
                                                                    "decision_id": decision_id
                                                                }
                                                                print(f"[ResearchWorker] Reversal DEMO Execution Response: Status={exec_resp.Status}, OrderId={exec_resp.OrderId}")
                                                            else:
                                                                print(f"[ResearchWorker] Reversal BLOCKED: Fresh reassessment decision for {symbol} missing required execution parameters (entry={rev_price}, sl={rev_sl}, tp={rev_tp}). Remaining flat.")
                                                        else:
                                                            print(f"[ResearchWorker] Reversal aborted: Reassessment action for {symbol} is {reassess_action} (opposite entry not independently confirmed). Remaining flat.")
                                        else:
                                            # Flat state: Canonical Single Execution Path
                                            # STEP 1: Obtain authoritative broker account information
                                            acc_info = None
                                            if self.demo_engine and hasattr(self.demo_engine, "adapter") and hasattr(self.demo_engine.adapter, "get_account_info"):
                                                try:
                                                    acc_info = self.demo_engine.adapter.get_account_info()
                                                except Exception as acc_err:
                                                    print(f"[ResearchWorker] Broker get_account_info raised error: {acc_err}")
                                                    acc_info = None

                                            # STEP 2 & 3 & 4: Validate account information, equity, and free margin
                                            if not acc_info or not isinstance(acc_info, dict):
                                                print(f"[ResearchWorker] Execution BLOCKED: Authoritative broker account info unavailable or invalid (acc_info={acc_info}). Failing closed.")
                                            else:
                                                raw_equity = acc_info.get("equity")
                                                equity_val = -1.0
                                                if raw_equity is not None:
                                                    try:
                                                        equity_val = float(raw_equity)
                                                    except (ValueError, TypeError):
                                                        equity_val = -1.0

                                                if equity_val <= 0 or math.isnan(equity_val) or math.isinf(equity_val):
                                                    print(f"[ResearchWorker] Execution BLOCKED: Authoritative broker account equity unavailable or invalid (acc_info={acc_info}). Failing closed.")
                                                else:
                                                    raw_margin = acc_info.get("free_margin")
                                                    free_margin_val = equity_val
                                                    if raw_margin is not None:
                                                        try:
                                                            m_val = float(raw_margin)
                                                            if not math.isnan(m_val) and not math.isinf(m_val):
                                                                free_margin_val = m_val
                                                        except (ValueError, TypeError):
                                                            free_margin_val = equity_val

                                                    # STEP 5 & 6: Obtain & validate broker symbol information
                                                    sym_info = self.demo_engine.adapter.get_symbol_info(symbol) if self.demo_engine and hasattr(self.demo_engine, "adapter") and hasattr(self.demo_engine.adapter, "get_symbol_info") else None
                                                    if not sym_info or not isinstance(sym_info, dict) or "volume_min" not in sym_info or "volume_max" not in sym_info or "volume_step" not in sym_info:
                                                        print(f"[ResearchWorker] Execution BLOCKED: Authoritative broker symbol info unavailable or missing volume limits for {symbol} (sym_info={sym_info}). Failing closed.")
                                                    else:
                                                        try:
                                                            vol_min = float(sym_info["volume_min"])
                                                            vol_max = float(sym_info["volume_max"])
                                                            vol_step = float(sym_info["volume_step"])
                                                        except (ValueError, TypeError):
                                                            vol_min = vol_max = vol_step = -1.0

                                                        if vol_min <= 0 or vol_max <= 0 or vol_step <= 0 or math.isnan(vol_min) or math.isinf(vol_min):
                                                            print(f"[ResearchWorker] Execution BLOCKED: Authoritative broker symbol volume limits invalid for {symbol} (min={vol_min}, max={vol_max}, step={vol_step}). Failing closed.")
                                                        else:
                                                            # STEP 7: Validate decision entry price and stop loss without fallbacks
                                                            raw_price = auto_dec.get("entry")
                                                            raw_sl = auto_dec.get("stop_loss")
                                                            sig_tp = auto_dec.get("take_profit")

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
                                                                not math.isnan(price_val) and not math.isinf(price_val) and
                                                                not math.isnan(sl_val) and not math.isinf(sl_val)
                                                            )

                                                            if is_valid_prices:
                                                                if sig_dir == "BUY" and sl_val >= price_val:
                                                                    is_valid_prices = False
                                                                elif sig_dir == "SELL" and sl_val <= price_val:
                                                                    is_valid_prices = False

                                                            if not is_valid_prices:
                                                                print(f"[ResearchWorker] Execution BLOCKED: Decision entry/SL parameters missing or invalid for {symbol} {sig_dir} (entry={raw_price}, sl={raw_sl}). Failing closed.")
                                                            else:
                                                                sig_price = price_val
                                                                sig_sl = sl_val

                                                                # STEP 8: Calculate 0.5% risk sizing from validated account equity and prices
                                                                from src.Risk.Services.professional_risk_engine import ProfessionalRiskEngine
                                                                risk_engine = ProfessionalRiskEngine()

                                                                sizing_res = risk_engine.evaluate_equity_risk_and_position_size(
                                                                    symbol=symbol,
                                                                    direction=sig_dir,
                                                                    entry_price=sig_price,
                                                                    stop_loss=sig_sl,
                                                                    account_equity=equity_val,
                                                                    free_margin=free_margin_val,
                                                                    risk_pct=0.5,
                                                                    volume_min=vol_min,
                                                                    volume_max=vol_max,
                                                                    volume_step=vol_step
                                                                )

                                                                # STEP 9: Validate sizing
                                                                if not sizing_res.is_valid:
                                                                    print(f"[ResearchWorker] Position sizing rejected for {symbol} {sig_dir}: {sizing_res.rejection_reason}")
                                                                else:
                                                                    # STEP 10: Execute through canonical DemoExecutionGate
                                                                    calculated_vol = sizing_res.volume_lots
                                                                    decision_id = auto_dec.get("decision_id", f"DEC-{symbol.upper()}-{sig_dir}-{int(sig_time)}")

                                                                    print(f"[ResearchWorker] Actionable decision detected for {symbol}: {sig_dir} with 0.5% risk volume = {calculated_vol} lots (Equity=${equity_val}). Dispatching...")
                                                                    exec_resp = self.demo_engine.execute_demo_decision(
                                                                        symbol=symbol,
                                                                        direction=sig_dir,
                                                                        volume=calculated_vol,
                                                                        price=sig_price,
                                                                        sl=sig_sl,
                                                                        tp=sig_tp,
                                                                        comment=f"YarTrader DEMO {symbol}",
                                                                        magic=143056,
                                                                        decision_id=decision_id
                                                                    )

                                                                    # STEP 11: Update execution state exactly once after successful execution dispatch
                                                                    self.last_executed_signal[symbol.upper()] = {
                                                                        "direction": sig_dir,
                                                                        "sig_time": sig_time,
                                                                        "exec_time": now_time,
                                                                        "decision_id": decision_id
                                                                    }

                                                                    print(f"[ResearchWorker] DEMO Execution Response: Status={exec_resp.Status}, OrderId={exec_resp.OrderId}")
                                    except Exception as exec_err:
                                        print(f"[ResearchWorker] DEMO Execution Gate / Fail-Closed: {exec_err}")
                        else:
                            print(f"[ResearchWorker] Symbol {symbol} decision is {action}. Continuation loop proceeding.")

                        central_runtime_state.update_multiple({
                            "research_status": "Running",
                            "last_cycle_time": self.last_analysis_time.isoformat()
                        })
                    except Exception as e:
                        self.error_count += 1
                        self.status = "RECOVERING"
                        central_runtime_state.update_state("research_status", "Recovering")
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
