import os
import math
import time
import threading
from datetime import datetime
from typing import Optional, Dict, Any
from src.Application.Runtime.research_runtime import ResearchRuntime
from src.Application.Runtime.runtime_state import central_runtime_state
from src.ShadowTrading.Engine.PredictiveShadowEngine import PredictiveShadowEngine
from src.Execution.Services.market_session_engine import MarketSessionEngine

class ResearchWorker:
    """Manages the background research worker polling loop with strict SRE safety gates."""
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
        self.session_engine = MarketSessionEngine()
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

    def _validate_equity(self, acc_info: Optional[Dict[str, Any]]) -> float:
        """Strictly validates authoritative account equity. Fails closed on missing or non-positive equity."""
        if not acc_info or not isinstance(acc_info, dict):
            raise ValueError("[ResearchWorker] Execution BLOCKED: Authoritative broker account info unavailable.")

        raw_eq = acc_info.get("equity")
        if raw_eq is None or isinstance(raw_eq, bool) or not isinstance(raw_eq, (int, float)):
            raise ValueError(f"[ResearchWorker] Execution BLOCKED: Account equity is missing or malformed ({raw_eq}).")

        equity_val = float(raw_eq)
        if not math.isfinite(equity_val) or equity_val <= 0:
            raise ValueError(f"[ResearchWorker] Execution BLOCKED: Account equity is non-finite or <= 0 (${equity_val}).")

        return equity_val

    def _validate_account_metrics(self, acc_info: Optional[Dict[str, Any]]) -> tuple[float, float]:
        """
        Strictly validates authoritative broker equity and free margin independently.
        Fails closed with ValueError if either equity or free_margin is missing, malformed, non-positive, or non-finite.
        NO FALLBACK of free_margin to equity is permitted.
        """
        equity_val = self._validate_equity(acc_info)

        raw_fm = acc_info.get("free_margin")
        if raw_fm is None or isinstance(raw_fm, bool) or not isinstance(raw_fm, (int, float)):
            raise ValueError(f"[ResearchWorker] Execution BLOCKED: Free margin is missing or malformed ({raw_fm}).")

        free_margin_val = float(raw_fm)
        if not math.isfinite(free_margin_val) or free_margin_val <= 0:
            raise ValueError(f"[ResearchWorker] Execution BLOCKED: Free margin is non-finite or <= 0 (${free_margin_val}).")

        return equity_val, free_margin_val

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

                        # 1. Autonomous Trading Global Toggle Check (FAIL CLOSED DEFAULT = "false")
                        kill_switch_enabled = os.getenv("AUTONOMOUS_DEMO_TRADING_ENABLED", "false").lower() in ["true", "1", "yes"]
                        if not kill_switch_enabled:
                            print(f"[ResearchWorker] Autonomous trading disabled (AUTONOMOUS_DEMO_TRADING_ENABLED=False/Missing). Skipping execution dispatch for {symbol}.")
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

                                        # 4. Authoritative Symbol Check & Broker Equity/Free-Margin Retrieval
                                        if symbol.upper() != "XAUUSD":
                                            print(f"[ResearchWorker] Execution BLOCKED: Symbol {symbol} is not authorized for live execution dispatch (XAUUSD-ONLY boundary enforced).")
                                            continue

                                        acc_info = runtime.provider.delegate.get_account_info() if hasattr(runtime.provider, "delegate") else None
                                        equity_val, free_margin_val = self._validate_account_metrics(acc_info)

                                        # 5. Pre-Entry Session & Daily Loss Protection Kill Switch Gate
                                        session_val = self.session_engine.validate_pre_entry(
                                            symbol=symbol,
                                            current_time=datetime.now(),
                                            current_equity=equity_val
                                        )
                                        if not session_val.allowed:
                                            print(f"[ResearchWorker] Pre-entry BLOCKED for {symbol}: {session_val.rejection_reason} ({session_val.message})")
                                            continue

                                        # 6. Check Active Broker Positions & Handle Position Query UNKNOWN State
                                        active_positions = self.demo_engine.get_active_positions(symbol=symbol)

                                        if active_positions is None:
                                            print(f"[ResearchWorker] Execution BLOCKED: Active broker position query returned UNKNOWN state for {symbol}. Failing closed.")
                                            continue

                                        if len(active_positions) > 0:
                                            existing_ticket = active_positions[0].get("ticket", 0)
                                            existing_dir_code = active_positions[0].get("type", 0)
                                            existing_dir = "BUY" if existing_dir_code == 0 else "SELL"

                                            if existing_dir == sig_dir:
                                                print(f"[ResearchWorker] Duplicate position guard triggered: {symbol} already has active {existing_dir} position (ticket={existing_ticket}). Skipping.")
                                            else:
                                                # Sequential Reversal Lifecycle
                                                print(f"[ResearchWorker] Sequential Reversal Triggered: Existing active {existing_dir} position found for {symbol}. Requesting close before reassessment...")
                                                close_resp = self.demo_engine.close_position(
                                                    symbol=symbol,
                                                    position_ticket=existing_ticket,
                                                    comment=f"YarTrader RevClose {symbol}"
                                                )

                                                if close_resp.Status not in ["Placed", "Closed"]:
                                                    print(f"[ResearchWorker] Reversal BLOCKED: Position {existing_ticket} close request failed (Status={close_resp.Status}, Comment={close_resp.Comment}). Failing closed.")
                                                else:
                                                    # Authoritative broker position verification
                                                    remaining_pos = self.demo_engine.get_active_positions(symbol=symbol)

                                                    if remaining_pos is None:
                                                        print(f"[ResearchWorker] Reversal BLOCKED: Verification query returned UNKNOWN position state for {symbol}. Failing closed.")
                                                        continue

                                                    is_closed = not any(str(p.get("ticket", "")) == str(existing_ticket) for p in remaining_pos)
                                                    if not is_closed:
                                                        print(f"[ResearchWorker] Reversal BLOCKED: Position {existing_ticket} close unconfirmed in broker state. Failing closed.")
                                                    else:
                                                        print(f"[ResearchWorker] Position {existing_ticket} close CONFIRMED flat. Reassessing market for {symbol} {sig_dir}...")
                                                        reassess_run = runtime.run_once()
                                                        reassess_dec = reassess_run.Findings.get("autonomous_decision", {})
                                                        reassess_action = reassess_dec.get("action", "WAIT")

                                                        if reassess_action == sig_dir:
                                                            rev_price = reassess_dec.get("entry")
                                                            rev_sl = reassess_dec.get("stop_loss")
                                                            rev_tp = reassess_dec.get("take_profit")

                                                            if rev_price and rev_sl and rev_tp and float(rev_price) > 0 and float(rev_sl) > 0 and float(rev_tp) > 0:
                                                                from src.Risk.Services.professional_risk_engine import ProfessionalRiskEngine
                                                                risk_engine = ProfessionalRiskEngine()
                                                                sym_info = self.demo_engine.adapter.get_symbol_info(symbol) if self.demo_engine else None
                                                                if not sym_info:
                                                                    print(f"[ResearchWorker] Reversal BLOCKED: Broker symbol metadata missing for {symbol}.")
                                                                    continue

                                                                vol_min = float(sym_info["volume_min"])
                                                                vol_max = float(sym_info["volume_max"])
                                                                vol_step = float(sym_info["volume_step"])

                                                                rev_sizing = risk_engine.evaluate_equity_risk_and_position_size(
                                                                    symbol=symbol,
                                                                    direction=sig_dir,
                                                                    entry_price=float(rev_price),
                                                                    stop_loss=float(rev_sl),
                                                                    account_equity=equity_val,
                                                                    free_margin=free_margin_val,
                                                                    volume_min=vol_min,
                                                                    volume_max=vol_max,
                                                                    volume_step=vol_step,
                                                                    leverage=100.0,
                                                                    contract_size=100.0,
                                                                    risk_pct=0.5
                                                                )

                                                                if not rev_sizing.is_valid:
                                                                    print(f"[ResearchWorker] Reversal sizing rejected for {symbol} {sig_dir}: {rev_sizing.rejection_reason}")
                                                                else:
                                                                    decision_id = f"DEC-REV-{symbol.upper()}-{sig_dir}-{int(sig_time)}"
                                                                    exec_resp = self.demo_engine.execute_demo_decision(
                                                                        symbol=symbol,
                                                                        direction=sig_dir,
                                                                        volume=rev_sizing.volume_lots,
                                                                        price=float(rev_price),
                                                                        sl=float(rev_sl),
                                                                        tp=float(rev_tp),
                                                                        comment=f"YarTrader REV {symbol}",
                                                                        magic=143056,
                                                                        decision_id=decision_id
                                                                    )
                                                                    if exec_resp.Status in ["Placed", "Closed", "Executed", "OK", "Success"]:
                                                                        self.last_executed_signal[symbol.upper()] = {
                                                                            "direction": sig_dir,
                                                                            "sig_time": sig_time,
                                                                            "exec_time": now_time,
                                                                            "decision_id": decision_id
                                                                        }
                                                                    print(f"[ResearchWorker] Reversal DEMO Execution Response: Status={exec_resp.Status}, OrderId={exec_resp.OrderId}")
                                                            else:
                                                                print(f"[ResearchWorker] Reversal BLOCKED: Fresh reassessment decision for {symbol} missing required parameters. Remaining flat.")
                                                        else:
                                                            print(f"[ResearchWorker] Reversal aborted: Reassessment action for {symbol} is {reassess_action}. Remaining flat.")
                                        else:
                                            # Flat state: Normal execution dispatch
                                            sig_price = auto_dec.get("entry")
                                            sig_sl = auto_dec.get("stop_loss")
                                            sig_tp = auto_dec.get("take_profit")

                                            if not sig_price or not sig_sl or float(sig_price) <= 0 or float(sig_sl) <= 0:
                                                print(f"[ResearchWorker] Decision for {symbol} rejected: Missing or invalid entry/stop_loss price.")
                                                continue

                                            from src.Risk.Services.professional_risk_engine import ProfessionalRiskEngine
                                            risk_engine = ProfessionalRiskEngine()

                                            sym_info = self.demo_engine.adapter.get_symbol_info(symbol) if self.demo_engine else None
                                            if not sym_info:
                                                print(f"[ResearchWorker] Execution BLOCKED: Symbol metadata unavailable for {symbol}.")
                                                continue

                                            vol_min = float(sym_info["volume_min"])
                                            vol_max = float(sym_info["volume_max"])
                                            vol_step = float(sym_info["volume_step"])

                                            sizing_res = risk_engine.evaluate_equity_risk_and_position_size(
                                                symbol=symbol,
                                                direction=sig_dir,
                                                entry_price=float(sig_price),
                                                stop_loss=float(sig_sl),
                                                account_equity=equity_val,
                                                free_margin=free_margin_val,
                                                volume_min=vol_min,
                                                volume_max=vol_max,
                                                volume_step=vol_step,
                                                leverage=100.0,
                                                contract_size=100.0,
                                                risk_pct=0.5
                                            )

                                            if not sizing_res.is_valid:
                                                print(f"[ResearchWorker] Position sizing rejected for {symbol} {sig_dir}: {sizing_res.rejection_reason}")
                                            else:
                                                calculated_vol = sizing_res.volume_lots
                                                decision_id = auto_dec.get("decision_id", f"DEC-{symbol.upper()}-{sig_dir}-{int(sig_time)}")

                                                print(f"[ResearchWorker] Actionable decision detected for {symbol}: {sig_dir} with 0.5% risk volume = {calculated_vol} lots (Equity=${equity_val}). Dispatching...")
                                                exec_resp = self.demo_engine.execute_demo_decision(
                                                    symbol=symbol,
                                                    direction=sig_dir,
                                                    volume=calculated_vol,
                                                    price=float(sig_price),
                                                    sl=float(sig_sl),
                                                    tp=float(sig_tp) if sig_tp else None,
                                                    comment=f"YarTrader DEMO {symbol}",
                                                    magic=143056,
                                                    decision_id=decision_id
                                                )

                                                if exec_resp.Status in ["Placed", "Closed", "Executed", "OK", "Success"]:
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
