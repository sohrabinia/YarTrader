from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta, timezone
from bisect import bisect_right
from pathlib import Path
import math
import uuid
import os
import json

from src.Research.Brain.memory import MarketMemorySystem
from src.Research.Brain.judge import JudgeBrain


def resolve_bar_exit_fill(
    direction: str,
    open_price: float,
    high_price: float,
    low_price: float,
    stop_loss: float,
    take_profit: Optional[float],
) -> tuple[Optional[str], float]:
    """Resolve OHLC stop/target fills without look-ahead.

    A gap through a stop fills at the worse bar open. A gap through a target
    fills at the open. If both levels are touched intrabar and the open is
    between them, stop-loss wins the ambiguity conservatively.
    """
    side = str(direction).upper()
    opening = float(open_price)
    high = float(high_price)
    low = float(low_price)
    stop = float(stop_loss)
    target = float(take_profit) if take_profit is not None and float(take_profit) > 0 else None

    if side == "BUY":
        if opening <= stop:
            return "STOP_LOSS_HIT", opening
        if target is not None and opening >= target:
            return "TAKE_PROFIT_HIT", opening
        if low <= stop:
            return "STOP_LOSS_HIT", stop
        if target is not None and high >= target:
            return "TAKE_PROFIT_HIT", target
    elif side == "SELL":
        if opening >= stop:
            return "STOP_LOSS_HIT", opening
        if target is not None and opening <= target:
            return "TAKE_PROFIT_HIT", opening
        if high >= stop:
            return "STOP_LOSS_HIT", stop
        if target is not None and low <= target:
            return "TAKE_PROFIT_HIT", target
    else:
        raise ValueError("direction must be BUY or SELL")

    return None, opening


class BacktestAndLearningEngine:
    """
    Realistic Chronological Backtesting & Multi-Market Learning Engine for YarTrader.
    Guarantees:
    - Zero look-ahead bias (evaluates market bar-by-bar strictly in historical chronological order).
    - Immediate post-trade outcome evaluation on WIN, LOSS, and BREAKEVEN.
    - Comprehensive trade outcome metrics logging: market context, timeframe context, detected patterns,
      strategy, direction, entry, SL, TP, R/R, confidence, exit reason, outcome, R-multiple, MFE, MAE, hold time.
    - Sequential multi-market knowledge isolation (XAUUSD, EURUSD, GBPUSD, USDJPY).
    - Walk-forward out-of-sample validation support.
    """

    def __init__(self, storage_dir: Optional[str] = None, memory_autosave_every: int = 1, learning_interval_bars: int = 1) -> None:
        self.storage_dir = storage_dir or os.path.join("runtime_logs", "backtest_learning")
        os.makedirs(self.storage_dir, exist_ok=True)

        self.memory_systems: Dict[str, MarketMemorySystem] = {}
        self.memory_autosave_every = max(1, int(memory_autosave_every))
        self.learning_interval_bars = max(1, int(learning_interval_bars))
        self.live_brains: Dict[tuple, Any] = {}
        self.judge = JudgeBrain()
        self._base_engulf_observation_path = Path(self.storage_dir) / "base_engulf_reversal_observations.jsonl"
        self._base_engulf_observation_keys = set()
        self._base_engulf_labeled_keys = set()
        self._base_engulf_forward_labeled_keys = set()
        self._base_engulf_pending_observations = {}
        if self._base_engulf_observation_path.exists():
            try:
                for line in self._base_engulf_observation_path.read_text(encoding="utf-8-sig").splitlines():
                    row = json.loads(line)
                    if row.get("observation_key"):
                        key = str(row["observation_key"])
                        if row.get("record_type") == "OUTCOME_LABEL":
                            self._base_engulf_labeled_keys.add(key)
                        elif row.get("record_type") == "FORWARD_OUTCOME_LABEL":
                            self._base_engulf_forward_labeled_keys.add(key)
                        else:
                            self._base_engulf_observation_keys.add(key)
                            if (row.get("label_status") == "PENDING_FORWARD_OUTCOME"
                                    and row.get("observation_time") is not None
                                    and row.get("observation_close") is not None
                                    and (row.get("base") or {}).get("width") is not None):
                                self._base_engulf_pending_observations[key] = row
            except (OSError, ValueError, TypeError):
                # Corrupt research history must not prevent ordinary backtesting.
                pass

    def get_market_memory(self, symbol: str) -> MarketMemorySystem:
        """Sequential multi-market knowledge isolation: separate memory per market symbol."""
        sym_upper = symbol.upper()
        if sym_upper not in self.memory_systems:
            sym_dir = os.path.join(self.storage_dir, f"memory_{sym_upper}")
            self.memory_systems[sym_upper] = MarketMemorySystem(storage_dir=sym_dir)
            self.memory_systems[sym_upper].configure_event_persistence(self.memory_autosave_every)
        return self.memory_systems[sym_upper]

    def get_live_brain(self, symbol: str, timeframe: str):
        from src.Research.Brain.live_brain import LiveAnalysisBrain
        key = (symbol.upper(), timeframe.upper())
        if key not in self.live_brains:
            self.live_brains[key] = LiveAnalysisBrain(
                symbol.upper(), timeframe.upper(), memory_system=self.get_market_memory(symbol)
            )
        return self.live_brains[key]

    def _record_base_engulf_observations(self, symbol: str, strategy_result: Dict[str, Any],
                                         decision_time: Any, timeframe_candles: Optional[Dict[str, Any]] = None,
                                         now_epoch: Optional[float] = None) -> None:
        """Persist unique Base states and label their forward reversal outcomes causally."""
        for tf, item in (strategy_result.get("timeframe_results") or {}).items():
            base = item.get("base")
            if not isinstance(base, dict):
                continue
            engulfed = item.get("engulfed") is True
            event_time = item.get("engulf_time") if engulfed else None
            key = "|".join((str(symbol).upper(), str(tf).upper(), str(base.get("start_time")),
                            str(base.get("end_time")), str(event_time if event_time is not None else "NOT_ENGULFED_YET")))
            if key in self._base_engulf_observation_keys:
                continue
            row = {
                "observation_key": key, "symbol": str(symbol).upper(), "timeframe": str(tf).upper(),
                "decision_time": str(decision_time), "observation_time": item.get("observation_time"),
                "observation_close": item.get("observation_close"), "base": base,
                "trend_direction": item.get("trend_direction"),
                "departure_time": item.get("departure_time"),
                "engulfed": engulfed, "engulf_time": event_time,
                "direction": item.get("direction", "WAIT"),
                "status": item.get("status", "WAIT"), "reason": item.get("reason", ""),
                "label_status": "PENDING_FORWARD_OUTCOME",
                "note": "Observation only; future bars are not used until the fixed horizon has elapsed.",
            }
            try:
                self._base_engulf_observation_path.parent.mkdir(parents=True, exist_ok=True)
                with self._base_engulf_observation_path.open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
                self._base_engulf_observation_keys.add(key)
                self._base_engulf_pending_observations[key] = row
            except OSError:
                continue
        if timeframe_candles and now_epoch is not None:
            self._label_base_engulf_forward_outcomes(str(symbol).upper(), timeframe_candles, float(now_epoch))

    def _label_base_engulf_forward_outcomes(self, symbol: str, timeframe_candles: Dict[str, Any],
                                            now_epoch: float, horizon_bars: int = 10) -> None:
        """Compare engulfed and not-yet-engulfed Base snapshots using a fixed 10-bar horizon.

        These are OHLC research labels, not broker-costed labels and not eligible for
        the validated net-R reaction model. Same-bar stop/target collisions are ambiguous.
        """
        seconds = {"M1":60,"M5":300,"M15":900,"M30":1800,"H1":3600,
                   "H4":14400,"D1":86400,"W1":604800,"MN1":31*86400}
        for key, row in list(self._base_engulf_pending_observations.items()):
            if str(row.get("symbol", "")).upper() != symbol or key in self._base_engulf_forward_labeled_keys:
                continue
            tf = str(row.get("timeframe", "")).upper()
            if tf not in seconds:
                continue
            try:
                obs_time = float(row["observation_time"])
                entry = float(row["observation_close"])
                width = float((row.get("base") or {}).get("width"))
                trend = int(row.get("trend_direction", 0))
            except (TypeError, ValueError, KeyError):
                continue
            if width <= 0 or trend not in (-1, 1):
                continue
            duration = seconds[tf]
            # observation_time is the signal candle's open time; its close is known
            # one timeframe later, followed by exactly horizon_bars completed candles.
            horizon_end = obs_time + (horizon_bars + 1) * duration
            if now_epoch < horizon_end:
                continue
            raw_bars = timeframe_candles.get(tf) or []
            future = []
            for candle in raw_bars:
                try:
                    stamp = candle.get("timestamp", candle.get("time"))
                    if isinstance(stamp, str):
                        stamp = datetime.fromisoformat(stamp.replace("Z", "+00:00")).timestamp()
                    stamp = float(stamp)
                    if obs_time < stamp <= obs_time + horizon_bars*duration and stamp + duration <= now_epoch:
                        future.append({"time":stamp,"high":float(candle["high"]),"low":float(candle["low"])})
                except (TypeError, ValueError, KeyError, OverflowError):
                    continue
            future.sort(key=lambda x:x["time"])
            if len(future) < horizon_bars:
                continue
            future = future[:horizon_bars]
            direction = "SELL" if trend > 0 else "BUY"
            stop = entry + width if direction == "SELL" else entry - width
            target = entry - 2*width if direction == "SELL" else entry + 2*width
            first_transition = "horizon_expired"
            for candle in future:
                stop_hit = candle["high"] >= stop if direction == "SELL" else candle["low"] <= stop
                target_hit = candle["low"] <= target if direction == "SELL" else candle["high"] >= target
                if stop_hit and target_hit:
                    first_transition = "ambiguous_same_bar"
                    break
                if target_hit:
                    first_transition = "reversal_target_first"
                    break
                if stop_hit:
                    first_transition = "reversal_stop_first"
                    break
            if direction == "SELL":
                mfe = max(0.0, entry-min(x["low"] for x in future))/width
                mae = max(0.0, max(x["high"] for x in future)-entry)/width
            else:
                mfe = max(0.0, max(x["high"] for x in future)-entry)/width
                mae = max(0.0, entry-min(x["low"] for x in future))/width
            label = {
                "record_type":"FORWARD_OUTCOME_LABEL", "observation_key":key,
                "symbol":symbol, "timeframe":tf, "engulfed":row.get("engulfed") is True,
                "direction":direction, "label_status":"LABELED",
                "outcome_source":"historical_ohlc_barrier_simulation",
                "label_horizon_bars":horizon_bars, "first_transition":first_transition,
                "favorable_excursion_base_widths":round(mfe,4),
                "adverse_excursion_base_widths":round(mae,4),
                "entry_reference":entry, "base_width":width,
                "note":"Research-only OHLC label; spread, commission, slippage and broker execution are not included.",
            }
            try:
                with self._base_engulf_observation_path.open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps(label, ensure_ascii=False, default=str) + "\n")
                self._base_engulf_forward_labeled_keys.add(key)
                self._base_engulf_pending_observations.pop(key, None)
            except OSError:
                continue

    def _record_base_engulf_outcome(self, closed_trade: Dict[str, Any]) -> None:
        """Attach the actual chronological backtest result to its Base-engulf event."""
        if str(closed_trade.get("strategy", "")).upper() != "BASE_ENGULF_REVERSAL":
            return
        key = str(closed_trade.get("base_engulf_observation_key") or "")
        if not key or key in self._base_engulf_labeled_keys:
            return
        row = {
            "record_type": "OUTCOME_LABEL", "observation_key": key,
            "symbol": str(closed_trade.get("symbol", "")).upper(),
            "timeframe": str(closed_trade.get("setup_timeframe") or closed_trade.get("timeframe", "")).upper(),
            "strategy": "BASE_ENGULF_REVERSAL", "label_status": "LABELED",
            "outcome_source": "historical_execution_simulation",
            "outcome": closed_trade.get("outcome"), "exit_reason": closed_trade.get("exit_reason"),
            "entry_time": closed_trade.get("entry_time"), "exit_time": closed_trade.get("exit_time"),
            "entry": closed_trade.get("entry"), "exit_price": closed_trade.get("exit_price"),
            "stop_loss": closed_trade.get("stop_loss"), "take_profit": closed_trade.get("take_profit"),
            "pnl": closed_trade.get("pnl"), "r_multiple": closed_trade.get("r_multiple"),
            "mfe": closed_trade.get("mfe"), "mae": closed_trade.get("mae"),
            "note": "Backtest outcome label; costs and stop-first bar simulation are applied by the backtest engine.",
        }
        try:
            self._base_engulf_observation_path.parent.mkdir(parents=True, exist_ok=True)
            with self._base_engulf_observation_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
            self._base_engulf_labeled_keys.add(key)
        except OSError:
            # Research persistence failure must not affect the backtest result.
            return

    def build_mt5_multitimeframe_provider(
        self, symbol: str, primary_timeframe: str, start_time: datetime,
        end_time: datetime, mt5_module,
    ):
        """Build a no-lookahead provider of three adjacent, fully closed MT5 timeframes."""
        tf_map = {
            "M1": mt5_module.TIMEFRAME_M1, "M5": mt5_module.TIMEFRAME_M5,
            "M15": mt5_module.TIMEFRAME_M15, "M30": mt5_module.TIMEFRAME_M30,
            "H1": mt5_module.TIMEFRAME_H1, "H4": mt5_module.TIMEFRAME_H4,
            "D1": mt5_module.TIMEFRAME_D1, "W1": mt5_module.TIMEFRAME_W1,
            "MN1": mt5_module.TIMEFRAME_MN1,
        }
        tf_seconds = {
            "M1": 60, "M5": 300, "M15": 900, "M30": 1800,
            "H1": 3600, "H4": 14400, "D1": 86400,
            "W1": 604800, "MN1": 31 * 86400,
        }
        lookbacks = {
            "M1": timedelta(hours=10), "M5": timedelta(days=2),
            "M15": timedelta(days=6), "M30": timedelta(days=13),
            "H1": timedelta(days=22), "H4": timedelta(days=52),
            "D1": timedelta(days=205), "W1": timedelta(days=700),
            "MN1": timedelta(days=1800),
        }
        primary = str(primary_timeframe).upper()
        if primary not in tf_map:
            raise ValueError(f"Unsupported MT5 timeframe: {primary_timeframe}")
        chain = ("MN1", "W1", "D1", "H4", "H1", "M30", "M15", "M5", "M1")
        idx = chain.index(primary)
        start = max(0, min(idx - 1, len(chain) - 3))
        selected = chain[start:start + 3]
        histories: Dict[str, List[Dict[str, Any]]] = {}
        closed_epochs: Dict[str, List[float]] = {}

        for tf in selected:
            rates = mt5_module.copy_rates_range(
                symbol, tf_map[tf], start_time - lookbacks[tf], end_time
            )
            if rates is None or len(rates) == 0:
                raise RuntimeError(f"MT5 returned no closed {tf} history for {symbol}: {mt5_module.last_error()}")
            bars: List[Dict[str, Any]] = []
            closes: List[float] = []
            for rate in rates:
                opened_at = datetime.fromtimestamp(int(rate["time"]), timezone.utc)
                closed_at = opened_at + timedelta(seconds=tf_seconds[tf])
                if closed_at > end_time:
                    continue
                bars.append({
                    "timestamp": opened_at.isoformat(),
                    "open": float(rate["open"]), "high": float(rate["high"]),
                    "low": float(rate["low"]), "close": float(rate["close"]),
                    "volume": float(rate["tick_volume"]),
                })
                closes.append(closed_at.timestamp())
            if len(bars) <= 50:
                raise RuntimeError(
                    f"Insufficient fully closed MT5 history for {symbol}/{tf}: {len(bars)} bars; at least 51 required."
                )
            histories[tf] = bars
            closed_epochs[tf] = closes

        def provider(cutoff_time):
            if isinstance(cutoff_time, datetime):
                cutoff = cutoff_time
            else:
                cutoff = datetime.fromisoformat(str(cutoff_time).replace("Z", "+00:00"))
            if cutoff.tzinfo is None:
                cutoff = cutoff.replace(tzinfo=timezone.utc)
            cutoff_epoch = cutoff.timestamp()
            context: Dict[str, List[Dict[str, Any]]] = {}
            for tf in selected:
                count = bisect_right(closed_epochs[tf], cutoff_epoch)
                context[tf] = histories[tf][max(0, count - 500):count]
            return context

        return provider, {tf: len(histories[tf]) for tf in selected}

    def run_mt5_backtest(
        self,
        symbol: str,
        timeframe: str,
        years: int = 10,
        initial_balance: float = 10000.0,
    ) -> Dict[str, Any]:
        """Run a chronological backtest directly from history exposed by the MT5 terminal.

        No external market-data download/provider is used. The terminal's own history is
        the authoritative source. History is capped at the requested maximum, but shorter
        terminal history is valid and is analyzed as-is.
        """
        import MetaTrader5 as mt5

        tf_map = {
            "M1": mt5.TIMEFRAME_M1, "M5": mt5.TIMEFRAME_M5,
            "M15": mt5.TIMEFRAME_M15, "M30": mt5.TIMEFRAME_M30,
            "H1": mt5.TIMEFRAME_H1, "H4": mt5.TIMEFRAME_H4,
            "D1": mt5.TIMEFRAME_D1, "W1": mt5.TIMEFRAME_W1,
            "MN1": mt5.TIMEFRAME_MN1,
        }
        tf_seconds = {
            "M1": 60, "M5": 300, "M15": 900, "M30": 1800,
            "H1": 3600, "H4": 14400, "D1": 86400,
            "W1": 604800, "MN1": 31 * 86400,
        }
        tf = timeframe.upper()
        if tf not in tf_map:
            raise ValueError(f"Unsupported MT5 timeframe: {timeframe}")
        terminal_was_initialized = mt5.terminal_info() is not None
        initialized_here = False
        if not terminal_was_initialized:
            if not mt5.initialize():
                raise RuntimeError(f"MT5 terminal unavailable: {mt5.last_error()}")
            initialized_here = True
        try:
            end_time = datetime.now(timezone.utc)
            # Add a calendar buffer so weekends/holidays cannot make an intended
            # 10-year window fail by one or two daily bars.
            start_time = end_time - timedelta(days=365 * years + 30)
            rates = mt5.copy_rates_range(symbol, tf_map[tf], start_time, end_time)
            if rates is None or len(rates) == 0:
                raise RuntimeError(f"MT5 returned no history for {symbol}/{tf}: {mt5.last_error()}")
            closed_rates = []
            for rate in rates:
                opened_at = datetime.fromtimestamp(int(rate["time"]), timezone.utc)
                if opened_at + timedelta(seconds=tf_seconds[tf]) <= end_time:
                    closed_rates.append(rate)
            if len(closed_rates) <= 50:
                raise RuntimeError(f"MT5 returned insufficient fully closed history for {symbol}/{tf}.")
            first_time = datetime.fromtimestamp(int(closed_rates[0]["time"]), timezone.utc)
            actual_history_days = (end_time - first_time).days
            if actual_history_days <= 0:
                raise RuntimeError(f"MT5 returned invalid history window for {symbol}/{tf}.")
            candles = [
                {
                    "timestamp": datetime.fromtimestamp(int(r["time"]), timezone.utc).isoformat(),
                    "open": float(r["open"]), "high": float(r["high"]),
                    "low": float(r["low"]), "close": float(r["close"]),
                    "volume": float(r["tick_volume"]),
                }
                for r in closed_rates
            ]
            mtf_provider, mtf_history_counts = self.build_mt5_multitimeframe_provider(
                symbol=symbol, primary_timeframe=tf, start_time=start_time,
                end_time=end_time, mt5_module=mt5,
            )
            result = self.run_backtest(
                symbol, tf, candles, initial_balance=initial_balance,
                all_timeframe_candles_provider=mtf_provider,
            )
            result["data_source"] = "MT5_TERMINAL_HISTORY"
            result["decision_authority"] = "BASE_HIERARCHY"
            result["base_timeframe_history_bars"] = mtf_history_counts
            result["history_start"] = first_time.isoformat()
            result["history_end"] = end_time.isoformat()
            result["history_years_requested"] = years
            result["history_years_actual"] = round(actual_history_days / 365.0, 2)
            result["history_days_actual"] = actual_history_days
            result["history_bars"] = len(candles)
            return result
        finally:
            if initialized_here:
                mt5.shutdown()

    def run_backtest(
        self,
        symbol: str,
        timeframe: str,
        candles: List[Dict[str, Any]],
        initial_balance: float = 10000.0,
        start_index: int = 50,
        context_window: int = 500,
        state: Optional[Dict[str, Any]] = None,
        all_timeframe_candles_provider=None,
        decision_interval_minutes: int = 1,
        learn_from_outcomes: bool = True,
        max_daily_drawdown_pct: float = 60.0,
        autonomous_exploration_mode: bool = False,
    ) -> Dict[str, Any]:
        """
        Executes a chronological, walk-forward backtest simulation across historical candles.
        Feeds closed trade outcomes (`WIN`, `LOSS`, `BREAKEVEN`) directly to JudgeBrain
        and MarketMemorySystem for adaptive learning update.
        """
        if len(candles) <= start_index:
            return {
                "symbol": symbol.upper(),
                "timeframe": timeframe,
                "total_trades": 0,
                "closed_trades": [],
                "summary": "Insufficient candles for backtest."
            }

        if isinstance(max_daily_drawdown_pct, bool) or not isinstance(max_daily_drawdown_pct, (int, float)) or not math.isfinite(float(max_daily_drawdown_pct)) or not 0.0 < float(max_daily_drawdown_pct) <= 100.0:
            raise ValueError("max_daily_drawdown_pct must be finite and within (0, 100].")
        max_daily_drawdown_pct = float(max_daily_drawdown_pct)
        state = state or {}
        balance = float(state.get("balance", initial_balance))
        equity = float(state.get("equity", balance))
        daily_session_key = None
        daily_session_start_balance = balance
        daily_realized_pnl = 0.0
        daily_halted = False
        daily_halted_sessions = set()
        open_position: Optional[Dict[str, Any]] = state.get("open_position")
        closed_trades: List[Dict[str, Any]] = []
        learning_updates_count = 0
        latest_brain_report = None

        memory = self.get_market_memory(symbol)
        # The backtest decision source is Base-only. MarketMemory receives outcomes
        # from Base trades, but no generic Brain/indicator strategy may originate entries.
        from src.Intelligence.Execution.strategy_orchestrator import StrategyOrchestrator
        base_orchestrator = StrategyOrchestrator()

        # Walk-forward bar by bar chronologically
        for i in range(start_index, len(candles)):
            current_bar = candles[i]
            # Keep chronological processing over the full history while bounding
            # per-bar context so a 10-year run does not become O(n²) in memory/copy cost.
            window_start = max(0, i + 1 - context_window)
            history_candles = candles[window_start:i+1]
            current_price = float(current_bar["close"])
            bar_time = current_bar.get("timestamp", f"bar-{i}")
            try:
                parsed_bar_time = datetime.fromisoformat(str(bar_time).replace("Z", "+00:00"))
                if parsed_bar_time.tzinfo is None:
                    parsed_bar_time = parsed_bar_time.replace(tzinfo=timezone.utc)
                current_day_key = parsed_bar_time.date().isoformat()
            except (TypeError, ValueError, OverflowError):
                current_day_key = daily_session_key
            if current_day_key and current_day_key != daily_session_key:
                daily_session_key = current_day_key
                daily_session_start_balance = balance
                daily_realized_pnl = 0.0
                daily_halted = False

            # 1. Update open position if exists
            if open_position:
                high_price = float(current_bar["high"])
                low_price = float(current_bar["low"])

                pos_direction = open_position["direction"]
                sl = open_position["stop_loss"]
                tp = open_position.get("take_profit")

                # Track MFE and MAE independently of the execution fill.
                if pos_direction == "BUY":
                    mfe = max(open_position.get("mfe", 0.0), high_price - open_position["entry"])
                    mae = min(open_position.get("mae", 0.0), low_price - open_position["entry"])
                else:  # SELL
                    mfe = max(open_position.get("mfe", 0.0), open_position["entry"] - low_price)
                    mae = min(open_position.get("mae", 0.0), open_position["entry"] - high_price)

                exit_reason, exit_price = resolve_bar_exit_fill(
                    pos_direction,
                    float(current_bar.get("open", current_price)),
                    high_price,
                    low_price,
                    float(sl),
                    tp,
                )
                if not exit_reason and autonomous_exploration_mode:
                    opposite_direction = "SELL" if pos_direction == "BUY" else "BUY"
                    if str(((latest_brain_report or {}).get("best_candidate") or {}).get("direction", "")).upper() == opposite_direction:
                        exit_reason = "OPPOSITE_BASE_SIGNAL"
                        exit_price = current_price

                open_position["mfe"] = mfe
                open_position["mae"] = mae

                if exit_reason:
                    # Close position with execution friction (spread + commission)
                    pnl_dist = (exit_price - open_position["entry"]) if pos_direction == "BUY" else (open_position["entry"] - exit_price)
                    sym_upper = symbol.upper()
                    if "XAU" in sym_upper or "GOLD" in sym_upper:
                        multiplier = 100.0
                    elif "XAG" in sym_upper or "SILVER" in sym_upper:
                        multiplier = 5000.0
                    elif any(token in sym_upper for token in ("BTC", "ETH", "SOL", "BNB", "XRP", "ADA", "DOGE", "AVAX", "DOT", "LINK", "LTC", "BCH", "NEAR", "UNI", "ATOM")):
                        multiplier = 1.0
                    elif "JPY" in sym_upper:
                        multiplier = 100000.0 / max(exit_price, 1e-9)  # quote-currency JPY converted to USD
                    else:
                        multiplier = 100000.0  # standard FX contract size
                    raw_pnl = pnl_dist * open_position["volume"] * multiplier

                    # Asset-Class Specific Execution Friction Model
                    sym_upper = symbol.upper()
                    vol = open_position["volume"]

                    if "XAU" in sym_upper:
                        # Gold: $0.20 spread ($20/lot) + $7/lot commission
                        spread_cost_usd = 0.20 * vol * 100.0
                        commission_cost_usd = 7.0 * vol
                        total_friction_usd = spread_cost_usd + commission_cost_usd
                    elif "XAG" in sym_upper:
                        # Silver: $0.02 spread ($100/lot on 5000 oz) + $7/lot commission
                        spread_cost_usd = 0.02 * vol * 5000.0
                        commission_cost_usd = 7.0 * vol
                        total_friction_usd = spread_cost_usd + commission_cost_usd
                    elif any(c in sym_upper for c in ["BTC", "ETH", "SOL", "BNB", "XRP", "ADA", "DOGE", "AVAX", "DOT", "LINK", "LTC", "BCH", "NEAR", "UNI", "ATOM"]):
                        # Crypto: 0.10% (10 bps) combined fee/spread on trade value
                        notional_value_usd = exit_price * vol
                        total_friction_usd = notional_value_usd * 0.0010
                    else:
                        # Forex: 1.0 pip spread + $7/lot commission
                        pip_dist = 0.01 if "JPY" in sym_upper else 0.0001
                        spread_cost_usd = 1.0 * pip_dist * vol * 100000.0
                        commission_cost_usd = 7.0 * vol
                        total_friction_usd = spread_cost_usd + commission_cost_usd

                    trade_pnl = raw_pnl - total_friction_usd
                    balance += trade_pnl
                    equity = balance
                    daily_realized_pnl += trade_pnl
                    daily_loss_pct = max(0.0, -daily_realized_pnl) / max(daily_session_start_balance, 1e-9) * 100.0
                    if daily_loss_pct >= max_daily_drawdown_pct:
                        daily_halted = True
                        if daily_session_key:
                            daily_halted_sessions.add(daily_session_key)

                    risk_dist = abs(open_position["entry"] - sl)
                    r_multiple = round(pnl_dist / risk_dist, 2) if risk_dist > 0 else 0.0

                    if trade_pnl > 0.5:
                        outcome = "WIN"
                    elif trade_pnl < -0.5:
                        outcome = "LOSS"
                    else:
                        outcome = "BREAKEVEN"

                    open_position["exit_price"] = exit_price
                    open_position["exit_reason"] = exit_reason
                    open_position["exit_time"] = bar_time
                    open_position["pnl"] = round(trade_pnl, 2)
                    open_position["r_multiple"] = r_multiple
                    open_position["outcome"] = outcome
                    self._record_base_engulf_outcome(open_position)

                    # Evaluation-only segments must not update memory from held-out outcomes.
                    if learn_from_outcomes:
                        learning_res = self._process_post_trade_learning(memory, open_position)
                        learning_updates_count += 1
                    else:
                        learning_res = {"status": "FROZEN_EVALUATION_NO_LEARNING"}
                    open_position["learning_update"] = learning_res

                    closed_trades.append(open_position)
                    open_position = None

            # 2. Evaluate after the current bar closes. MT5 timestamps are candle-open
            # times; using the close timestamp keeps parent/child context strictly causal.
            timeframe_seconds = {
                "M1": 60, "M5": 300, "M15": 900, "M30": 1800,
                "H1": 3600, "H4": 14400, "D1": 86400,
                "W1": 604800, "MN1": 31 * 86400,
            }
            decision_time_value = bar_time
            decision_dt = None
            try:
                opened_at = datetime.fromisoformat(str(bar_time).replace("Z", "+00:00"))
                if opened_at.tzinfo is None:
                    opened_at = opened_at.replace(tzinfo=timezone.utc)
                decision_dt = opened_at + timedelta(seconds=timeframe_seconds.get(str(timeframe).upper(), 60))
                decision_time_value = decision_dt.isoformat()
            except (TypeError, ValueError):
                decision_dt = None

            decision_due = True
            if decision_interval_minutes > 1 and decision_dt is not None:
                decision_due = decision_dt.minute % decision_interval_minutes == 0
            mtf_context = all_timeframe_candles_provider(decision_time_value) if all_timeframe_candles_provider else None
            base_report = base_orchestrator.evaluate_all_strategies(
                symbol=symbol, primary_timeframe=timeframe, candles=history_candles,
                all_timeframe_candles=mtf_context, spread_pip=1.0,
                exploration_mode=bool(autonomous_exploration_mode),
            )
            latest_brain_report = base_report
            # Backtest the independent Base-engulf reversal hypothesis on the same
            # causally closed multi-timeframe candles. A valid engulf proposal takes
            # precedence for this bar so its trades are explicitly attributed to the
            # new strategy rather than silently blended into BASE_HIERARCHY results.
            engulf_candidate = {}
            if decision_due:
                try:
                    from src.Intelligence.Execution.multi_timeframe_style_analyzer import MultiTimeframeStyleAnalyzer
                    style_frames = dict(mtf_context or {})
                    style_frames[str(timeframe).upper()] = history_candles
                    style_now = decision_dt.timestamp() if decision_dt is not None else datetime.fromisoformat(str(decision_time_value).replace("Z", "+00:00")).timestamp()
                    px = float(current_price)
                    pip_factor = 0.1 if "XAU" in symbol.upper() else (1.0 if "BTC" in symbol.upper() else 0.0001)
                    spread_abs = pip_factor
                    style_result = MultiTimeframeStyleAnalyzer().evaluate(
                        symbol=symbol, timeframe_candles=style_frames,
                        quote={"bid": max(1e-12, px-spread_abs/2), "ask": px+spread_abs/2},
                        now=float(style_now), spread_allowance=spread_abs,
                    ).get("BASE_ENGULF_REVERSAL", {})
                    self._record_base_engulf_observations(symbol, style_result, decision_time_value,
                                                          timeframe_candles=style_frames, now_epoch=float(style_now))
                    style_plan = style_result.get("order_plan") or {}
                    if (style_result.get("status") == "ENTRY_PROPOSAL"
                            and style_plan.get("status") == "PROPOSED"
                            and style_plan.get("direction") in ("BUY", "SELL")
                            and style_plan.get("entry") is not None
                            and style_plan.get("stop_loss") is not None
                            and style_result.get("research_target") is not None):
                        selected_base = style_result.get("base") or {}
                        selected_tf = str(style_result.get("timeframe") or style_result.get("setup_timeframe") or "").upper()
                        selected_event_time = style_result.get("engulf_time")
                        observation_key = "|".join((str(symbol).upper(), selected_tf,
                            str(selected_base.get("start_time")), str(selected_base.get("end_time")),
                            str(selected_event_time if selected_event_time is not None else "NOT_ENGULFED_YET")))
                        engulf_candidate = {
                            "strategy_name": "BASE_ENGULF_REVERSAL",
                            "strategy_id": "BASE_ENGULF_REVERSAL",
                            "base_engulf_observation_key": observation_key,
                            "setup_timeframe": selected_tf,
                            "direction": style_plan["direction"],
                            "entry": float(style_plan["entry"]),
                            "stop_loss": float(style_plan["stop_loss"]),
                            "take_profit": float(style_result["research_target"]),
                            "risk_reward": float(style_result.get("research_reward_risk", 2.0)),
                            "confidence": float(style_result.get("confidence", 72.0)),
                            "reasoning": [style_result.get("reason", "Base engulf reversal research signal")],
                            "market_context": {"strategy": "BASE_ENGULF_REVERSAL",
                                               "base_engulf_reversal": style_result},
                        }
                except Exception:
                    # A secondary research strategy must never abort the canonical
                    # backtest or fabricate a candidate when its analysis fails.
                    engulf_candidate = {}
            if not open_position and decision_due and (not daily_halted or autonomous_exploration_mode):
                candidate = engulf_candidate or (base_report.get("best_candidate") or {})
                action = str(candidate.get("direction", "WAIT")).upper()
                params = {
                    "entry": candidate.get("entry"),
                    "stop_loss": candidate.get("stop_loss"),
                    "take_profit": candidate.get("take_profit"),
                    "risk_reward": candidate.get("risk_reward", 0.0),
                    "source": "BASE_HIERARCHY_COSTED_REENTRY_REACTION",
                } if candidate else {}
                confidence = float(candidate.get("confidence", 0.0) or 0.0)
                market_context = candidate.get("market_context") or {}
                base_structure = market_context.get("base_structure") or {}
                selected_hypothesis = {
                    "hypothesis_id": candidate.get("strategy_id"),
                    "context": market_context,
                    "matched_pattern_ids": [],
                    "sequence_signature": [
                        str(candidate.get("strategy_name") or "BASE_HIERARCHY"),
                        f"CHILD_TF:{base_structure.get('child_timeframe', candidate.get('setup_timeframe', 'UNKNOWN'))}",
                        f"PARENT_TF:{base_structure.get('parent_timeframe', 'UNKNOWN')}",
                        f"RELATION:{base_structure.get('parent_relation', 'UNKNOWN')}",
                        f"PROFILE:{base_structure.get('profile_key', 'UNKNOWN')}",
                    ],
                    "reasoning": candidate.get("reasoning") or [],
                }
                if (action in ["BUY", "SELL"]
                        and (confidence >= 50.0 or base_report.get("exploration_mode") is True)
                        and params.get("stop_loss")
                        and (autonomous_exploration_mode or (params.get("take_profit") and float(params.get("risk_reward", 0.0)) > 1.0))):
                    open_position = {
                        "trade_id": f"BT-{symbol.upper()}-{timeframe.upper()}-{str(bar_time).replace(":", "").replace("+", "p").replace("-", "")}-{action}",
                        "symbol": symbol.upper(),
                        "timeframe": timeframe,
                        "strategy": str(candidate.get("strategy_name") or "BASE_HIERARCHY").upper(),
                        "base_engulf_observation_key": candidate.get("base_engulf_observation_key"),
                        "setup_timeframe": candidate.get("setup_timeframe", timeframe),
                        "direction": action,
                        "entry": float(params.get("entry", current_price)),
                        "stop_loss": float(params.get("stop_loss", 0.0)),
                        "take_profit": (float(params["take_profit"]) if params.get("take_profit") else None),
                        "risk_reward": float(params.get("risk_reward", 0.0)),
                        "confidence": confidence,
                        "exploration_mode": bool(base_report.get("exploration_mode")),
                        "autonomous_exploration_mode": bool(autonomous_exploration_mode),
                        "volume": 0.0,
                        "entry_time": bar_time,
                        "market_context": selected_hypothesis.get("context", {}),
                        "reasoning": list(selected_hypothesis.get("reasoning") or ["Validated Base re-entry reaction"]),
                        "mfe": 0.0,
                        "mae": 0.0
                    }
                    open_position["brain_hypothesis_id"] = selected_hypothesis.get("hypothesis_id")
                    open_position["brain_signature"] = list(selected_hypothesis.get("sequence_signature", []))
                    open_position["brain_pattern_ids"] = list(selected_hypothesis.get("matched_pattern_ids", []) )
                    from src.Risk.Services.professional_risk_engine import ProductionRiskPolicy
                    risk_budget_pct = ProductionRiskPolicy.TARGET_RISK_PCT / 100.0
                    risk_dollars = max(0.0, balance * risk_budget_pct)
                    risk_distance = abs(open_position["entry"] - open_position["stop_loss"])
                    sym_upper = symbol.upper()
                    if "XAU" in sym_upper or "GOLD" in sym_upper:
                        pnl_multiplier = 100.0
                    elif "XAG" in sym_upper or "SILVER" in sym_upper:
                        pnl_multiplier = 5000.0
                    elif any(token in sym_upper for token in ("BTC", "ETH", "SOL", "BNB", "XRP", "ADA", "DOGE", "AVAX", "DOT", "LINK", "LTC", "BCH", "NEAR", "UNI", "ATOM")):
                        pnl_multiplier = 1.0
                    elif "JPY" in sym_upper:
                        pnl_multiplier = 100000.0 / max(float(params.get("entry", current_price)), 1e-9)
                    else:
                        pnl_multiplier = 100000.0
                    if autonomous_exploration_mode:
                        # Match demo exploration's minimum-volume sampling rather than
                        # sizing every trade from the production percentage-risk policy.
                        open_position["volume"] = 0.01
                    elif risk_distance > 0.0 and risk_dollars > 0.0:
                        open_position["volume"] = round(risk_dollars / (risk_distance * pnl_multiplier), 6)

        # Calculate backtest report metrics
        wins = sum(1 for t in closed_trades if t["outcome"] == "WIN")
        losses = sum(1 for t in closed_trades if t["outcome"] == "LOSS")
        bes = sum(1 for t in closed_trades if t["outcome"] == "BREAKEVEN")
        total_closed = len(closed_trades)
        win_rate = (wins / total_closed * 100.0) if total_closed > 0 else 0.0

        net_pnl = balance - initial_balance

        previous_total = int(state.get("total_trades", 0))
        previous_wins = int(state.get("wins", 0))
        previous_losses = int(state.get("losses", 0))
        previous_bes = int(state.get("breakevens", 0))
        cumulative_total = previous_total + total_closed
        cumulative_wins = previous_wins + wins
        cumulative_losses = previous_losses + losses
        cumulative_bes = previous_bes + bes
        cumulative_win_rate = (cumulative_wins / cumulative_total * 100.0) if cumulative_total else 0.0
        cumulative_learning = int(state.get("learning_updates_count", 0)) + learning_updates_count
        return {
            "symbol": symbol.upper(),
            "timeframe": timeframe,
            "initial_balance": initial_balance,
            "final_balance": round(balance, 2),
            "net_pnl": round(balance - initial_balance, 2),
            "total_trades": cumulative_total,
            "wins": cumulative_wins,
            "losses": cumulative_losses,
            "breakevens": cumulative_bes,
            "win_rate_pct": round(cumulative_win_rate, 2),
            "learning_updates_count": cumulative_learning,
            "daily_drawdown_limit_pct": max_daily_drawdown_pct,
            "daily_halted_sessions_count": len(daily_halted_sessions),
            "exploration_mode": True,
            "closed_trades": closed_trades,
            "state": {
                "balance": balance,
                "equity": equity,
                "open_position": open_position,
                "total_trades": cumulative_total,
                "wins": cumulative_wins,
                "losses": cumulative_losses,
                "breakevens": cumulative_bes,
                "learning_updates_count": cumulative_learning,
            },
        }

    def _process_post_trade_learning(self, memory: MarketMemorySystem, closed_trade: Dict[str, Any]) -> Dict[str, Any]:
        """
        Processes closed trade outcome (`WIN`, `LOSS`, `BREAKEVEN`) through JudgeBrain
        and records experience to MarketMemorySystem.
        """
        outcome = closed_trade["outcome"]
        strategy = closed_trade["strategy"]
        confidence = closed_trade["confidence"]

        from src.Research.Brain.models import SimulatedDecision
        sim_dec = SimulatedDecision(
            timestamp=datetime.now(),
            symbol=closed_trade["symbol"],
            price=closed_trade["entry"],
            decision_action=closed_trade["direction"],
            confidence=confidence / 100.0,
            reason="Backtest trade execution evaluation",
            context={"timeframe": closed_trade["timeframe"], "strategy": strategy, "pattern_ids": closed_trade.get("brain_pattern_ids", [])}
        )

        outcome_payload = {
            "final_result": "SUCCESS" if outcome == "WIN" else ("FAILURE" if outcome == "LOSS" else "NEUTRAL"),
            "max_favorable_excursion": closed_trade.get("mfe", 0.0),
            "max_adverse_excursion": closed_trade.get("mae", 0.0)
        }

        judge_eval = self.judge.evaluate_decision_outcome(sim_dec, closed_trade.get("market_context", {}), outcome_payload)

        # Retrospective review: learn from both wins and losses without a second decision cycle.
        entry = float(closed_trade["entry"])
        exit_price = float(closed_trade["exit_price"])
        risk_dist = abs(entry - float(closed_trade["stop_loss"]))
        realized_favorable = abs(exit_price - entry)
        mfe = abs(float(closed_trade.get("mfe", 0.0)))
        mae = abs(float(closed_trade.get("mae", 0.0)))
        capture_ratio = min(1.0, realized_favorable / mfe) if mfe > 0 else 0.0
        adverse_ratio = mae / risk_dist if risk_dist > 0 else 0.0
        missed_favorable = max(0.0, mfe - realized_favorable)
        if outcome == "WIN":
            why = "clean directional follow-through"
            if adverse_ratio >= 0.80:
                why = "profitable despite substantial adverse excursion; timing/entry quality needs review"
            elif adverse_ratio >= 0.40:
                why = "profitable after meaningful adverse excursion"
            improvement = "Review exit/management: favorable movement exceeded realized movement." if missed_favorable > max(risk_dist * 0.25, 0.0) else "No material post-exit opportunity identified from available excursion data."
        elif outcome == "LOSS":
            why = "directional thesis failed or risk was reached"
            if mfe >= risk_dist * 0.50:
                why = "loss occurred after meaningful favorable movement; entry/management timing needs review"
            improvement = "Review entry/management because favorable movement existed before failure." if mfe >= risk_dist * 0.50 else "Review market-context hypothesis; little favorable movement followed entry."
        else:
            why = "trade produced no material net outcome after friction"
            improvement = "Review whether waiting for clearer evidence would improve expectancy."
        post_trade_review = {
            "outcome": outcome,
            "why": why,
            "could_have_done_better": improvement,
            "mfe": round(mfe, 6),
            "mae": round(mae, 6),
            "realized_favorable_move": round(realized_favorable, 6),
            "missed_favorable_move": round(missed_favorable, 6),
            "favorable_capture_ratio": round(capture_ratio, 4),
            "adverse_to_initial_risk_ratio": round(adverse_ratio, 4),
            "counterfactual_future_data_used_for_decision": False,
        }

        # Store experience record
        from src.Research.Brain.models import ExperienceMemory
        exp = ExperienceMemory(
            experience_id=f"exp-{closed_trade['trade_id']}",
            symbol=closed_trade["symbol"],
            timeframe=closed_trade["timeframe"],
            timestamp=datetime.now(),
            situation_signature=list(closed_trade.get("brain_signature") or []),
            decision_action=closed_trade["direction"],
            outcome_result=outcome_payload["final_result"],
            lesson_feedback=(
                judge_eval["learning_feedback"]
                + f" Post-trade review: {post_trade_review['why']}. "
                + post_trade_review["could_have_done_better"]
            ),
            max_favorable_excursion=closed_trade.get("mfe", 0.0),
            max_adverse_excursion=closed_trade.get("mae", 0.0),
            meta={
                "strategy": strategy,
                "r_multiple": closed_trade.get("r_multiple", 0.0),
                "judge_eval": judge_eval,
                "post_trade_review": post_trade_review,
                "is_lucky_win": bool(judge_eval.get("is_lucky_win", False)),
                "learning_update_id": f"learn-{closed_trade['trade_id']}",
                "pattern_symbol": closed_trade["symbol"].upper(),
                "pattern_timeframe": closed_trade["timeframe"].upper(),
                "timeframe_signature": [closed_trade["timeframe"].upper()],
                "hypothesis_id": closed_trade.get("brain_hypothesis_id"),
                "pattern_ids": closed_trade.get("brain_pattern_ids", []),
                "favorable_excursion": mfe,
                "adverse_excursion": mae,
            }
        )

        if exp.situation_signature:
            memory.add_experience(exp)
        memory.promote_experiences_to_patterns()

        return judge_eval
