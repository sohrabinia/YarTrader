import math
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from src.Execution.Services.trade_journal import TradeJournalRecord


@dataclass
class PerformanceMetrics:
    total_trades: int
    wins: int
    losses: int
    win_rate: float
    average_rr: float
    average_win: float
    average_loss: float
    profit_factor: float
    max_drawdown: float
    expectancy: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class PerformanceAnalyticsEngine:
    """
    Performance Analytics & Expectancy Engine for YarTrader.
    Calculates overall and breakdown metrics (win rate, average win/loss,
    profit factor, max drawdown, mathematical expectancy) from trade journal records.
    """

    def calculate_metrics(self, records: List[TradeJournalRecord]) -> PerformanceMetrics:
        closed_records = [r for r in records if r.result in ["WIN", "LOSS", "BREAKEVEN"]]
        if not closed_records:
            return PerformanceMetrics(
                total_trades=0,
                wins=0,
                losses=0,
                win_rate=0.0,
                average_rr=0.0,
                average_win=0.0,
                average_loss=0.0,
                profit_factor=1.0,
                max_drawdown=0.0,
                expectancy=0.0
            )

        total_trades = len(closed_records)
        wins = [r for r in closed_records if r.pnl > 0 or r.result == "WIN"]
        losses = [r for r in closed_records if r.pnl < 0 or r.result == "LOSS"]

        win_count = len(wins)
        loss_count = len(losses)
        win_rate = round((win_count / total_trades) * 100.0, 2)

        gross_profit = sum(r.pnl for r in wins)
        gross_loss = abs(sum(r.pnl for r in losses))

        avg_win = round(gross_profit / win_count, 2) if win_count > 0 else 0.0
        avg_loss = round(gross_loss / loss_count, 2) if loss_count > 0 else 0.0

        profit_factor = round(gross_profit / gross_loss, 2) if gross_loss > 0 else (99.0 if gross_profit > 0 else 1.0)
        avg_rr = round(sum(r.planned_rr for r in closed_records) / total_trades, 2)

        # Drawdown calculation from equity curve
        running_equity = 0.0
        peak = 0.0
        max_dd = 0.0
        for r in closed_records:
            running_equity += r.pnl
            if running_equity > peak:
                peak = running_equity
            dd = peak - running_equity
            if dd > max_dd:
                max_dd = dd

        # Mathematical Expectancy: (Win Rate * Avg Win) - (Loss Rate * Avg Loss)
        win_prob = win_count / total_trades
        loss_prob = loss_count / total_trades
        expectancy = round((win_prob * avg_win) - (loss_prob * avg_loss), 2)

        return PerformanceMetrics(
            total_trades=total_trades,
            wins=win_count,
            losses=loss_count,
            win_rate=win_rate,
            average_rr=avg_rr,
            average_win=avg_win,
            average_loss=avg_loss,
            profit_factor=profit_factor,
            max_drawdown=round(max_dd, 2),
            expectancy=expectancy
        )

    def calculate_breakdowns(self, records: List[TradeJournalRecord]) -> Dict[str, Dict[str, PerformanceMetrics]]:
        closed_records = [r for r in records if r.result in ["WIN", "LOSS", "BREAKEVEN"]]

        by_pattern: Dict[str, List[TradeJournalRecord]] = {}
        by_tf: Dict[str, List[TradeJournalRecord]] = {}
        by_direction: Dict[str, List[TradeJournalRecord]] = {}

        for r in closed_records:
            pat = r.pattern_id if hasattr(r, "pattern_id") and r.pattern_id else (r.reasoning[0] if r.reasoning else "STANDARD")
            tf = r.timeframe
            dir_str = r.direction

            by_pattern.setdefault(pat, []).append(r)
            by_tf.setdefault(tf, []).append(r)
            by_direction.setdefault(dir_str, []).append(r)

        return {
            "by_pattern": {k: self.calculate_metrics(v) for k, v in by_pattern.items()},
            "by_timeframe": {k: self.calculate_metrics(v) for k, v in by_tf.items()},
            "by_direction": {k: self.calculate_metrics(v) for k, v in by_direction.items()}
        }
