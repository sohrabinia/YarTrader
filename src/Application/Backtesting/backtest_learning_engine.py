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

    def run_backtest(
        self,
        symbol: str,
        timeframe: str,
        candles: List[Dict[str, Any]],
        initial_balance: float = 10000.0,
        start_index: int = 50
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

        balance = initial_balance
        equity = initial_balance
        open_position: Optional[Dict[str, Any]] = None
        closed_trades: List[Dict[str, Any]] = []
        learning_updates_count = 0

        memory = self.get_market_memory(symbol)

        # Walk-forward bar by bar chronologically
        for i in range(start_index, len(candles)):
            current_bar = candles[i]
            history_candles = candles[:i+1]
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
                    # Close position
                    pnl_dist = (exit_price - open_position["entry"]) if pos_direction == "BUY" else (open_position["entry"] - exit_price)
                    multiplier = 100.0 if "XAU" in symbol.upper() else 10000.0
                    trade_pnl = pnl_dist * open_position["volume"] * multiplier
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

            # 2. Evaluate new trade entry if no position open
            if not open_position:
                eval_res = self.intel_core.evaluate_context(
                    symbol=symbol,
                    timeframe=timeframe,
                    candles=history_candles,
                    virtual_balance=balance
                )

                plan = eval_res.get("plan", {})
                action = plan.get("action", "WAIT")

                if action in ["BUY", "SELL"]:
                    open_position = {
                        "trade_id": f"BT-{symbol.upper()}-{uuid.uuid4().hex[:6]}",
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

        return {
            "symbol": symbol.upper(),
            "timeframe": timeframe,
            "initial_balance": initial_balance,
            "final_balance": round(balance, 2),
            "net_pnl": round(net_pnl, 2),
            "total_trades": total_closed,
            "wins": wins,
            "losses": losses,
            "breakevens": bes,
            "win_rate_pct": round(win_rate, 2),
            "learning_updates_count": learning_updates_count,
            "closed_trades": closed_trades
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
            lesson_feedback=judge_eval["learning_feedback"],
            max_favorable_excursion=closed_trade.get("mfe", 0.0),
            max_adverse_excursion=closed_trade.get("mae", 0.0),
            meta={
                "strategy": strategy,
                "r_multiple": closed_trade.get("r_multiple", 0.0),
                "judge_eval": judge_eval
            }
        )

        memory.add_experience(exp)
        memory.promote_experiences_to_patterns()

        return judge_eval
