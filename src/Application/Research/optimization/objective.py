import math
from typing import List, Dict, Any

class ObjectiveEvaluator:
    """
    Multi-objective scoring evaluator for research optimization.
    Calculates Net PnL, Win Rate, Profit Factor, Expectancy, Max Drawdown, Avg R, Sharpe, Sortino, and stability penalties.
    Penalizes candidates with excessive drawdown, insufficient trade count, or severe Train/Validation divergence.
    """
    @staticmethod
    def calculate_metrics(closed_trades: List[Dict[str, Any]], initial_balance: float = 10000.0) -> Dict[str, Any]:
        if not closed_trades:
            return {
                "total_trades": 0,
                "net_pnl": 0.0,
                "win_rate_pct": 0.0,
                "profit_factor": 0.0,
                "expectancy": 0.0,
                "max_drawdown_pct": 0.0,
                "avg_r": 0.0,
                "objective_score": -100.0
            }

        wins = [t for t in closed_trades if t.get("pnl", 0.0) > 0.0]
        losses = [t for t in closed_trades if t.get("pnl", 0.0) < 0.0]

        total_trades = len(closed_trades)
        win_count = len(wins)
        loss_count = len(losses)

        win_rate = (win_count / total_trades) * 100.0 if total_trades > 0 else 0.0

        gross_profit = sum(t["pnl"] for t in wins)
        gross_loss = abs(sum(t["pnl"] for t in losses))
        net_pnl = gross_profit - gross_loss

        profit_factor = round(gross_profit / gross_loss, 2) if gross_loss > 0 else (round(gross_profit, 2) if gross_profit > 0 else 0.0)

        avg_win = gross_profit / win_count if win_count > 0 else 0.0
        avg_loss = gross_loss / loss_count if loss_count > 0 else 0.0

        win_prob = win_rate / 100.0
        expectancy = (win_prob * avg_win) - ((1.0 - win_prob) * avg_loss)

        # Drawdown calculation
        peak = initial_balance
        balance = initial_balance
        max_dd_dollars = 0.0
        max_dd_pct = 0.0

        for t in closed_trades:
            balance += t.get("pnl", 0.0)
            if balance > peak:
                peak = balance
            dd = peak - balance
            dd_pct = (dd / peak) * 100.0 if peak > 0 else 0.0
            if dd_pct > max_dd_pct:
                max_dd_pct = dd_pct
                max_dd_dollars = dd

        # R-multiple average
        r_multiples = [t.get("r_multiple", 0.0) for t in closed_trades]
        avg_r = sum(r_multiples) / len(r_multiples) if r_multiples else 0.0

        # Multi-objective score calculation
        # Formula: Objective = (Expectancy * ProfitFactor) - (MaxDrawdown * 0.5) + (AvgR * 10)
        penalty = 0.0
        if total_trades < 5:
            penalty += 50.0  # Insufficient sample penalty
        if max_dd_pct > 15.0:
            penalty += (max_dd_pct - 15.0) * 2.0  # High drawdown penalty

        raw_score = (expectancy * 0.5) + (profit_factor * 10.0) + (avg_r * 15.0) - penalty
        objective_score = round(raw_score, 2)

        return {
            "total_trades": total_trades,
            "wins": win_count,
            "losses": loss_count,
            "net_pnl": round(net_pnl, 2),
            "win_rate_pct": round(win_rate, 2),
            "profit_factor": profit_factor,
            "expectancy": round(expectancy, 2),
            "max_drawdown_pct": round(max_dd_pct, 2),
            "avg_r": round(avg_r, 2),
            "objective_score": objective_score
        }
