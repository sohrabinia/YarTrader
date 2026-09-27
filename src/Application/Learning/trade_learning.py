import os
import json
import threading
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from src.Application.Journal.trade_journal import TradeJournalManager, TradeJournalRecord

class TradeLearningEngine:
    """
    Observational & Advisory Learning Engine.
    Consumes historical trade journal records from TradeJournalManager and compiles
    observational performance metrics (win rate, expectancy, average win/loss, slippage,
    symbol & timeframe performance, repeated failure patterns).

    STRICT SAFETY RULE:
    Learning/feedback is strictly OBSERVATIONAL and ADVISORY.
    It MUST NOT automatically mutate live strategy parameters, risk limits,
    market universe, or decision rules.
    """
    _instance = None
    _lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> "TradeLearningEngine":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def __init__(self, journal_manager: Optional[TradeJournalManager] = None) -> None:
        self.journal_manager = journal_manager or TradeJournalManager.get_instance()

    def generate_learning_summary(self) -> Dict[str, Any]:
        """
        Calculates observational feedback metrics over all completed trades in TradeJournal.
        Returns a structured advisory learning report.
        """
        trades = [t for t in self.journal_manager.get_all_trades() if t.exit_timestamp is not None]

        total_completed = len(trades)
        if total_completed == 0:
            return {
                "status": "NO_COMPLETED_TRADES",
                "total_trades": 0,
                "win_rate_pct": 0.0,
                "expectancy_usd": 0.0,
                "avg_win_usd": 0.0,
                "avg_loss_usd": 0.0,
                "planned_vs_realized_rr": 0.0,
                "exit_reasons_breakdown": {},
                "symbol_performance": {},
                "timeframe_performance": {},
                "advisory_insights": ["Insufficient completed trade history for statistical learning."]
            }

        wins = [t for t in trades if t.result_classification == "WIN"]
        losses = [t for t in trades if t.result_classification == "LOSS"]
        breakevens = [t for t in trades if t.result_classification == "BREAKEVEN"]

        win_count = len(wins)
        loss_count = len(losses)
        win_rate_pct = (win_count / total_completed) * 100.0

        total_pnl = sum(t.realized_pnl for t in trades if t.realized_pnl is not None)
        avg_pnl = total_pnl / total_completed

        avg_win = (sum(t.realized_pnl for t in wins if t.realized_pnl is not None) / win_count) if win_count > 0 else 0.0
        avg_loss = (sum(t.realized_pnl for t in losses if t.realized_pnl is not None) / loss_count) if loss_count > 0 else 0.0

        # Expectancy = (Win Rate * Avg Win) - (Loss Rate * |Avg Loss|)
        win_prob = win_count / total_completed
        loss_prob = loss_count / total_completed
        expectancy = (win_prob * avg_win) + (loss_prob * avg_loss) # avg_loss is negative

        # Breakdown by Exit Reason
        exit_reasons: Dict[str, int] = {}
        for t in trades:
            reason = t.exit_reason or "UNKNOWN"
            exit_reasons[reason] = exit_reasons.get(reason, 0) + 1

        # Performance by Symbol
        symbol_perf: Dict[str, Dict[str, Any]] = {}
        for t in trades:
            sym = t.symbol
            if sym not in symbol_perf:
                symbol_perf[sym] = {"trades": 0, "wins": 0, "pnl": 0.0}
            symbol_perf[sym]["trades"] += 1
            if t.result_classification == "WIN":
                symbol_perf[sym]["wins"] += 1
            symbol_perf[sym]["pnl"] += (t.realized_pnl or 0.0)

        for sym, data in symbol_perf.items():
            data["win_rate_pct"] = round((data["wins"] / data["trades"]) * 100.0, 2)
            data["pnl"] = round(data["pnl"], 2)

        # Performance by Timeframe
        tf_perf: Dict[str, Dict[str, Any]] = {}
        for t in trades:
            tf = t.timeframe
            if tf not in tf_perf:
                tf_perf[tf] = {"trades": 0, "wins": 0, "pnl": 0.0}
            tf_perf[tf]["trades"] += 1
            if t.result_classification == "WIN":
                tf_perf[tf]["wins"] += 1
            tf_perf[tf]["pnl"] += (t.realized_pnl or 0.0)

        for tf, data in tf_perf.items():
            data["win_rate_pct"] = round((data["wins"] / data["trades"]) * 100.0, 2)
            data["pnl"] = round(data["pnl"], 2)

        insights = []
        if win_rate_pct < 40.0:
            insights.append(f"Low Win Rate ({win_rate_pct:.1f}%). Consider reviewing entry quality and timeframe alignment.")
        if expectancy < 0:
            insights.append(f"Negative Expectancy (${expectancy:.2f}). Strategy is losing capital on average.")
        if exit_reasons.get("STOP_LOSS", 0) > (total_completed * 0.5):
            insights.append("High proportion of Stop Loss exits (>50%). Review Stop Loss placement and market volatility.")

        if not insights:
            insights.append("Performance parameters within normal statistical variance.")

        return {
            "status": "COMPLETED",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_trades": total_completed,
            "win_rate_pct": round(win_rate_pct, 2),
            "expectancy_usd": round(expectancy, 2),
            "total_pnl_usd": round(total_pnl, 2),
            "avg_pnl_usd": round(avg_pnl, 2),
            "avg_win_usd": round(avg_win, 2),
            "avg_loss_usd": round(avg_loss, 2),
            "exit_reasons_breakdown": exit_reasons,
            "symbol_performance": symbol_perf,
            "timeframe_performance": tf_perf,
            "advisory_insights": insights,
            "live_strategy_mutation": False,
            "autonomous_adaptation_blocked": True
        }
