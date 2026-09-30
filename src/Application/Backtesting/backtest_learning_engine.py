from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import uuid
import os
import json

from src.Research.Brain.memory import MarketMemorySystem
from src.Research.Brain.judge import JudgeBrain
from src.Intelligence.Execution.core import ExecutionIntelligenceCore

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

    def __init__(self, storage_dir: Optional[str] = None) -> None:
        self.storage_dir = storage_dir or os.path.join("runtime_logs", "backtest_learning")
        os.makedirs(self.storage_dir, exist_ok=True)

        self.memory_systems: Dict[str, MarketMemorySystem] = {}
        self.judge = JudgeBrain()
        self.intel_core = ExecutionIntelligenceCore.get_instance()

    def get_market_memory(self, symbol: str) -> MarketMemorySystem:
        """Sequential multi-market knowledge isolation: separate memory per market symbol."""
        sym_upper = symbol.upper()
        if sym_upper not in self.memory_systems:
            sym_dir = os.path.join(self.storage_dir, f"memory_{sym_upper}")
            self.memory_systems[sym_upper] = MarketMemorySystem(storage_dir=sym_dir)
        return self.memory_systems[sym_upper]

    def run_mt5_backtest(
        self,
        symbol: str,
        timeframe: str,
        years: int = 10,
        initial_balance: float = 10000.0,
    ) -> Dict[str, Any]:
        """Run a chronological backtest directly from history exposed by the MT5 terminal.

        No external market-data download/provider is used. The terminal's own history is
        the authoritative source, and the run fails closed if less than the requested
        historical span is available.
        """
        if years < 10:
            raise ValueError("MT5 backtest requires at least 10 years of history.")
        import MetaTrader5 as mt5

        tf_map = {
            "M1": mt5.TIMEFRAME_M1, "M5": mt5.TIMEFRAME_M5,
            "M15": mt5.TIMEFRAME_M15, "M30": mt5.TIMEFRAME_M30,
            "H1": mt5.TIMEFRAME_H1, "H4": mt5.TIMEFRAME_H4,
            "D1": mt5.TIMEFRAME_D1, "W1": mt5.TIMEFRAME_W1,
            "MN1": mt5.TIMEFRAME_MN1,
        }
        tf = timeframe.upper()
        if tf not in tf_map:
            raise ValueError(f"Unsupported MT5 timeframe: {timeframe}")
        if not mt5.initialize():
            raise RuntimeError(f"MT5 terminal unavailable: {mt5.last_error()}")
        try:
            from datetime import timezone
            end_time = datetime.now(timezone.utc)
            # Add a calendar buffer so weekends/holidays cannot make an intended
            # 10-year window fail by one or two daily bars.
            start_time = end_time - timedelta(days=365 * years + 30)
            rates = mt5.copy_rates_range(symbol, tf_map[tf], start_time, end_time)
            if rates is None or len(rates) == 0:
                raise RuntimeError(f"MT5 returned no history for {symbol}/{tf}: {mt5.last_error()}")
            first_time = datetime.fromtimestamp(int(rates[0]["time"]), timezone.utc)
            if (end_time - first_time).days < 365 * years:
                raise RuntimeError(
                    f"MT5 history is shorter than requested {years} years: "
                    f"received {(end_time - first_time).days} days."
                )
            candles = [
                {
                    "timestamp": datetime.fromtimestamp(int(r["time"]), timezone.utc).isoformat(),
                    "open": float(r["open"]), "high": float(r["high"]),
                    "low": float(r["low"]), "close": float(r["close"]),
                    "volume": float(r.get("tick_volume", 0)) if hasattr(r, "get") else float(r["tick_volume"]),
                }
                for r in rates
            ]
            result = self.run_backtest(symbol, tf, candles, initial_balance=initial_balance)
            result["data_source"] = "MT5_TERMINAL_HISTORY"
            result["history_start"] = first_time.isoformat()
            result["history_end"] = end_time.isoformat()
            result["history_years_requested"] = years
            result["history_bars"] = len(candles)
            return result
        finally:
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

        state = state or {}
        balance = float(state.get("balance", initial_balance))
        equity = float(state.get("equity", balance))
        open_position: Optional[Dict[str, Any]] = state.get("open_position")
        closed_trades: List[Dict[str, Any]] = []
        learning_updates_count = 0

        memory = self.get_market_memory(symbol)

        # Walk-forward bar by bar chronologically
        for i in range(start_index, len(candles)):
            current_bar = candles[i]
            # Keep chronological processing over the full history while bounding
            # per-bar context so a 10-year run does not become O(n²) in memory/copy cost.
            window_start = max(0, i + 1 - context_window)
            history_candles = candles[window_start:i+1]
            current_price = float(current_bar["close"])
            bar_time = current_bar.get("timestamp", f"bar-{i}")

            # 1. Update open position if exists
            if open_position:
                high_price = float(current_bar["high"])
                low_price = float(current_bar["low"])

                pos_direction = open_position["direction"]
                sl = open_position["stop_loss"]
                tp = open_position["take_profit"]

                exit_reason = None
                exit_price = current_price

                # Track MFE and MAE
                if pos_direction == "BUY":
                    mfe = max(open_position.get("mfe", 0.0), high_price - open_position["entry"])
                    mae = min(open_position.get("mae", 0.0), low_price - open_position["entry"])
                    if low_price <= sl:
                        exit_reason = "STOP_LOSS_HIT"
                        exit_price = sl
                    elif high_price >= tp:
                        exit_reason = "TAKE_PROFIT_HIT"
                        exit_price = tp
                else:  # SELL
                    mfe = max(open_position.get("mfe", 0.0), open_position["entry"] - low_price)
                    mae = min(open_position.get("mae", 0.0), open_position["entry"] - high_price)
                    if high_price >= sl:
                        exit_reason = "STOP_LOSS_HIT"
                        exit_price = sl
                    elif low_price <= tp:
                        exit_reason = "TAKE_PROFIT_HIT"
                        exit_price = tp

                open_position["mfe"] = mfe
                open_position["mae"] = mae

                if exit_reason:
                    # Close position with execution friction (spread + commission)
                    pnl_dist = (exit_price - open_position["entry"]) if pos_direction == "BUY" else (open_position["entry"] - exit_price)
                    multiplier = 100.0 if "XAU" in symbol.upper() else 10000.0
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

                    # 2. Trigger Post-Trade Learning Update via JudgeBrain and MarketMemorySystem
                    learning_res = self._process_post_trade_learning(memory, open_position)
                    open_position["learning_update"] = learning_res
                    learning_updates_count += 1

                    closed_trades.append(open_position)
                    open_position = None

            # 2. Evaluate new entries on a bounded decision cadence.
            decision_due = True
            if decision_interval_minutes > 1:
                try:
                    decision_dt = datetime.fromisoformat(str(bar_time).replace("Z", "+00:00"))
                    decision_due = decision_dt.minute % decision_interval_minutes == 0
                except (TypeError, ValueError):
                    decision_due = True
            if not open_position and decision_due:
                mtf_context = all_timeframe_candles_provider(bar_time) if all_timeframe_candles_provider else None
                eval_res = self.intel_core.evaluate_context(
                    symbol=symbol,
                    timeframe=timeframe,
                    candles=history_candles,
                    all_timeframe_candles=mtf_context,
                    virtual_balance=balance
                )

                plan = eval_res.get("plan", {})
                action = plan.get("action", "WAIT")

                if action in ["BUY", "SELL"]:
                    open_position = {
                        "trade_id": f"BT-{symbol.upper()}-{timeframe.upper()}-{str(bar_time).replace(":", "").replace("+", "p").replace("-", "")}-{action}",
                        "symbol": symbol.upper(),
                        "timeframe": timeframe,
                        "strategy": plan.get("strategy", "FAST_SCALP"),
                        "direction": action,
                        "entry": float(plan.get("entry", current_price)),
                        "stop_loss": float(plan.get("stop_loss", 0.0)),
                        "take_profit": float(plan.get("take_profit", 0.0)),
                        "risk_reward": float(plan.get("risk_reward", 0.0)),
                        "confidence": float(plan.get("confidence", 70.0)),
                        "volume": 0.01,
                        "entry_time": bar_time,
                        "market_context": eval_res.get("narrative", {}),
                        "reasoning": plan.get("reasoning", []),
                        "mfe": 0.0,
                        "mae": 0.0
                    }

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
            context={"timeframe": closed_trade["timeframe"], "strategy": strategy}
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
            situation_signature=[closed_trade["entry"], closed_trade["stop_loss"], closed_trade["take_profit"]],
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
                "learning_update_id": f"learn-{closed_trade['trade_id']}"
            }
        )

        memory.add_experience(exp)
        memory.promote_experiences_to_patterns()

        return judge_eval
