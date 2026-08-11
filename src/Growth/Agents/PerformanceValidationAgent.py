import uuid
import math
from datetime import datetime, timezone
from typing import Dict, Any, List

class PerformanceValidationAgent:
    """
    Performance Validation Agent responsible for tracking paper trading results on MT5.
    Calculates Direction Accuracy, Timing Accuracy, Risk/Reward Ratio, Max Drawdown,
    and Win Rate with 100% traceable calculation formulas and data IDs.
    """

    def __init__(self, agent_id: str = "agent-performance-val"):
        self.agent_id = agent_id
        self.trades_db: List[Dict[str, Any]] = []

    def record_simulated_trade(
        self,
        asset: str,
        direction: str,
        entry_price: float,
        exit_price: float,
        stop_loss: float,
        take_profit: float,
        risk: float,
        confidence: float,
        reasoning: str,
        outcome: str,
        market_condition: str = "Trending",
        source_stream_id: str = "MT5_FEED_MOCK_GOLD"
    ) -> Dict[str, Any]:
        """
        Records an audited simulated trade, attaching precise timestamps and source IDs.
        """
        trade_id = f"sim-{uuid.uuid4().hex[:8]}"
        trade_record = {
            "trade_id": trade_id,
            "asset": asset.upper(),
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "market_condition": market_condition,
            "direction": direction.upper(),
            "entry_price": entry_price,
            "exit_price": exit_price,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "risk": risk,
            "confidence": confidence,
            "reasoning": reasoning,
            "outcome": outcome.upper(),  # WIN, LOSS, BREAKEVEN
            "source_stream_id": source_stream_id
        }
        self.trades_db.append(trade_record)
        return trade_record

    def calculate_metrics(self) -> Dict[str, Any]:
        """
        Computes 100% traceable performance metrics from simulated trades database.
        """
        timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        if not self.trades_db:
            return {
                "timestamp": timestamp,
                "total_trades": 0,
                "win_rate_pct": 0.0,
                "direction_accuracy_pct": 0.0,
                "timing_accuracy_pct": 0.0,
                "avg_risk_reward": 0.0,
                "max_drawdown_pct": 0.0,
                "formulas": self._get_formulas_documentation()
            }

        total = len(self.trades_db)
        wins = sum(1 for t in self.trades_db if t["outcome"] == "WIN")
        losses = sum(1 for t in self.trades_db if t["outcome"] == "LOSS")

        # Win Rate
        win_rate = (wins / total) * 100.0 if total > 0 else 0.0

        # Direction Accuracy (predicted direction matches overall price change direction)
        direction_correct = 0
        for t in self.trades_db:
            price_diff = t["exit_price"] - t["entry_price"]
            actual_direction = "BUY" if price_diff > 0 else ("SELL" if price_diff < 0 else "NONE")
            if t["direction"] == actual_direction:
                direction_correct += 1
        direction_accuracy = (direction_correct / total) * 100.0

        # Timing Accuracy: evaluates how close the entry/exit prices are compared to targets
        # Represented as absolute deviance percentage
        timing_accuracy_sum = 0.0
        for t in self.trades_db:
            target_diff = abs(t["take_profit"] - t["entry_price"])
            actual_diff = abs(t["exit_price"] - t["entry_price"])
            if target_diff > 0:
                accuracy_ratio = min(1.0, actual_diff / target_diff)
                timing_accuracy_sum += accuracy_ratio * 100.0
            else:
                timing_accuracy_sum += 100.0
        timing_accuracy = timing_accuracy_sum / total

        # Average Risk / Reward
        rr_sum = 0.0
        for t in self.trades_db:
            reward = abs(t["take_profit"] - t["entry_price"])
            risk_dist = abs(t["entry_price"] - t["stop_loss"])
            if risk_dist > 0:
                rr_sum += (reward / risk_dist)
            else:
                rr_sum += 1.0
        avg_rr = rr_sum / total

        # Drawdown calculation (equity curve-based peak-to-trough)
        # Assuming starting balance of $10000 and standard win/loss outcome values
        balance = 10000.0
        peak = balance
        max_drawdown = 0.0

        for t in self.trades_db:
            if t["outcome"] == "WIN":
                balance += t["risk"] * avg_rr * 1000.0
            elif t["outcome"] == "LOSS":
                balance -= t["risk"] * 1000.0

            if balance > peak:
                peak = balance
            drawdown = ((peak - balance) / peak) * 100.0 if peak > 0 else 0.0
            if drawdown > max_drawdown:
                max_drawdown = drawdown

        return {
            "timestamp": timestamp,
            "total_trades": total,
            "win_rate_pct": round(win_rate, 2),
            "direction_accuracy_pct": round(direction_accuracy, 2),
            "timing_accuracy_pct": round(timing_accuracy, 2),
            "avg_risk_reward": round(avg_rr, 2),
            "max_drawdown_pct": round(max_drawdown, 2),
            "traceability": {
                "source_data_ids": list(set(t["trade_id"] for t in self.trades_db)),
                "source_streams": list(set(t["source_stream_id"] for t in self.trades_db))
            },
            "formulas": self._get_formulas_documentation()
        }

    def _get_formulas_documentation(self) -> Dict[str, str]:
        return {
            "win_rate_formula": "WinRate = (Wins / TotalTrades) * 100",
            "direction_accuracy_formula": "DirectionAccuracy = (CorrectDirections / TotalTrades) * 100",
            "timing_accuracy_formula": "TimingAccuracy = Sum(Min(1.0, ActualDifference / TargetDifference)) / TotalTrades * 100",
            "avg_risk_reward_formula": "AvgRR = Sum(TakeProfitDist / StopLossDist) / TotalTrades",
            "max_drawdown_formula": "MaxDrawdown = Max((PeakBalance - Balance) / PeakBalance * 100)"
        }
