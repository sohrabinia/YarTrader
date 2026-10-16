import uuid
import math
from datetime import datetime, timedelta
from typing import Any, Dict, List, Tuple
from src.Application.Backtesting.models import BacktestScenario, BacktestResult
from src.Data.connector import ExternalDataPipelineConnector
from src.Data.External.models import ExternalDataRequest
from src.Application.Agents.supervisor import IntelligenceSupervisor
from src.Application.Agents.context import AgentContextBuilder
from src.Decision.Intelligence.engine import DecisionEngine
from src.Decision.Intelligence.models import DecisionIntelligenceReport
from src.Infrastructure.exceptions import ValidationException


class IntelligenceMetricsEvaluator:
    """Evaluates chronological decision consistency and research accuracy over backtesting spans."""
    def evaluate_backtest_metrics(
        self,
        reports: List[DecisionIntelligenceReport]
    ) -> Dict[str, float]:
        if not reports:
            return {
                "decision_consistency": 1.0,
                "research_accuracy_ratio": 1.0,
                "average_decision_confidence": 1.0,
                "overall_intelligence_score": 1.0
            }

        # 1. Decision Consistency: variance of confidence levels across outcomes
        confs = [r.Confidence for r in reports]
        avg_conf = sum(confs) / len(reports)
        variance = sum((c - avg_conf) ** 2 for c in confs) / len(reports)
        # Higher consistency = lower variance
        consistency = max(0.0, min(1.0, 1.0 - math.sqrt(variance)))

        # 2. Research Accuracy: ratio of high-confidence research insights
        high_conf_insights = 0
        total_insights = 0
        for r in reports:
            for insight in r.Context.ResearchInsights:
                total_insights += 1
                if hasattr(insight, "Confidence") and getattr(insight, "Confidence") >= 0.80:
                    high_conf_insights += 1

        accuracy_ratio = (high_conf_insights / total_insights) if total_insights > 0 else 1.0

        # Overall Score
        overall_score = (consistency * 0.4) + (accuracy_ratio * 0.3) + (avg_conf * 0.3)

        return {
            "decision_consistency": round(consistency, 4),
            "research_accuracy_ratio": round(accuracy_ratio, 4),
            "average_decision_confidence": round(avg_conf, 4),
            "overall_intelligence_score": round(overall_score, 4)
        }


class IntelligenceBacktestEngine:
    """
    Coordinates historical data ingestion loops, multi-agent validation runs,
    and decision quality score compilations over backtesting scenarios.
    """
    def __init__(
        self,
        supervisor: IntelligenceSupervisor,
        decision_engine: DecisionEngine,
        connector: ExternalDataPipelineConnector
    ) -> None:
        self.supervisor = supervisor
        self.decision_engine = decision_engine
        self.connector = connector
        self.evaluator = IntelligenceMetricsEvaluator()

    def run_backtest(self, scenario: BacktestScenario) -> BacktestResult:
        """Runs standard pipeline processing iteratively across the scenario date window."""
        # Enforce zero execution leakage scanning on scenario parameters
        forbidden_keywords = {"order", "position", "broker", "trade_command", "buy_signal", "sell_signal", "execute"}
        for k, v in scenario.parameters.items():
            for kw in forbidden_keywords:
                if kw in str(k).lower() or kw in str(v).lower():
                    raise ValidationException(f"Safety Violation: Backtest scenario parameters contain forbidden keyword '{kw}'.")

        requested_strategy = str(scenario.parameters.get("strategy_type", "BASE_HIERARCHY")).strip().upper()
        if requested_strategy != "BASE_HIERARCHY":
            raise ValidationException(
                f"Unsupported strategy_type '{requested_strategy}'. Only BASE_HIERARCHY is permitted; legacy strategies were removed."
            )

        reports: List[DecisionIntelligenceReport] = []
        current_time = scenario.start_time
        interval_minutes = scenario.parameters.get("interval_minutes", 60)

        # Ensure providers are registerable and resolved
        symbol = scenario.symbol

        # Setup Backtest Order/Trade Simulator Variables
        initial_balance = float(scenario.parameters.get("initial_balance", 10000.0))
        balance = initial_balance
        trades: List[Dict[str, Any]] = []
        active_trade: Optional[Dict[str, Any]] = None
        equity_curve: List[Dict[str, Any]] = []

        # Loop through intervals sequentially
        total_intervals = 0
        # No synthetic fallback prices: absent broker history means no PnL/trades.
        latest_close = 0.0

        while current_time < scenario.end_time:
            total_intervals += 1

            # 1. Fetch raw rates via Connector
            req = ExternalDataRequest(
                symbol=symbol,
                timeframe=scenario.timeframe,
                start_time=current_time - timedelta(minutes=max(1, int(interval_minutes)) * 250),
                end_time=current_time,
                parameters={"scenario": "VALID", "data_source": "MT4"}
            )
            normalized_records, data_report = self.connector.retrieve_and_process(req)

            if normalized_records:
                latest_close = normalized_records[-1].close_price

            # 2. Ingest into Agent Ecosystem
            agent_ctx = AgentContextBuilder.create_with_market_data(symbol, scenario.timeframe)
            # Historical OHLC is the only market evidence. No fabricated
            # momentum score, trend assertion, or synthetic risk approval is injected.

            # Orchestrate agents
            enriched_agent_ctx = self.supervisor.orchestrate(agent_ctx)

            # 3. Decision Synthesis
            dec_intel_ctx = self.supervisor.compile_to_decision_context(enriched_agent_ctx)

            # Evaluate Decision report
            report = self.decision_engine.evaluate_intelligence_context(dec_intel_ctx)
            reports.append(report)

            # ----------------------------------------------------
            # BACKTEST TRADE ENGINE SIMULATION LAYER
            # ----------------------------------------------------
            # Update Active Trade SL/TP and Floating Profit
            multiplier = 100.0 if "XAU" in symbol else 10000.0
            from src.Decision.Models.models import DecisionState

            if active_trade:
                # Calculate P&L
                if active_trade["direction"] == "BUY":
                    pnl = (latest_close - active_trade["entry_price"]) * multiplier * active_trade["volume"]
                else:
                    pnl = (active_trade["entry_price"] - latest_close) * multiplier * active_trade["volume"]

                active_trade["p_and_l"] = round(pnl, 2)

                # Check SL/TP exit
                sl_hit = False
                tp_hit = False
                if active_trade["direction"] == "BUY":
                    if latest_close <= active_trade["sl"]:
                        sl_hit = True
                    elif latest_close >= active_trade["tp"]:
                        tp_hit = True
                else: # SELL
                    if latest_close >= active_trade["sl"]:
                        sl_hit = True
                    elif latest_close <= active_trade["tp"]:
                        tp_hit = True

                if sl_hit or tp_hit:
                    active_trade["status"] = "CLOSED"
                    active_trade["exit_price"] = latest_close
                    active_trade["exit_time"] = current_time.isoformat()
                    balance += active_trade["p_and_l"]
                    active_trade = None

            # This legacy intelligence simulator has no trade authority. A generic
            # DecisionState approval must never create a position. The canonical
            # chronological Base-only backtest is the only source of performance trades.
            # No Momentum, MeanReversion, default BUY, or synthetic-price fallback exists.

            # Record running equity curve point
            floating_pnl = active_trade["p_and_l"] if active_trade else 0.0
            equity_curve.append({
                "timestamp": current_time.isoformat(),
                "balance": round(balance, 2),
                "equity": round(balance + floating_pnl, 2)
            })

            # Advance timeframe
            current_time += timedelta(minutes=interval_minutes)

        # Force close any remaining open trade at the final price
        if active_trade:
            multiplier = 100.0 if "XAU" in symbol else 10000.0
            if active_trade["direction"] == "BUY":
                pnl = (latest_close - active_trade["entry_price"]) * multiplier * active_trade["volume"]
            else:
                pnl = (active_trade["entry_price"] - latest_close) * multiplier * active_trade["volume"]
            active_trade["status"] = "CLOSED"
            active_trade["exit_price"] = latest_close
            active_trade["exit_time"] = scenario.end_time.isoformat()
            active_trade["p_and_l"] = round(pnl, 2)
            balance += pnl

        # Calculate rich stats from simulated trades list
        total_trades = len(trades)
        winning_trades = sum(1 for t in trades if t["p_and_l"] > 0)
        losing_trades = sum(1 for t in trades if t["p_and_l"] <= 0)
        win_rate = (winning_trades / total_trades * 100.0) if total_trades > 0 else 0.0

        gross_profit = sum(t["p_and_l"] for t in trades if t["p_and_l"] > 0)
        gross_loss = sum(abs(t["p_and_l"]) for t in trades if t["p_and_l"] < 0)
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else (gross_profit if gross_profit > 0 else 1.0)

        average_win = (gross_profit / winning_trades) if winning_trades > 0 else 0.0
        average_loss = (gross_loss / losing_trades) if losing_trades > 0 else 0.0
        expectancy = round((balance - initial_balance) / total_trades, 2) if total_trades > 0 else 0.0

        buy_trades = sum(1 for t in trades if t["direction"] == "BUY")
        sell_trades = sum(1 for t in trades if t["direction"] == "SELL")

        # Best / Worst Trade
        best_trade_pnl = max([t["p_and_l"] for t in trades], default=0.0)
        worst_trade_pnl = min([t["p_and_l"] for t in trades], default=0.0)

        # Drawdown calculation
        peak = initial_balance
        max_dd = 0.0
        for pt in equity_curve:
            eq = pt["equity"]
            if eq > peak:
                peak = eq
            dd = peak - eq
            if dd > max_dd:
                max_dd = dd
        max_dd_pct = round((max_dd / peak) * 100.0, 2) if peak > 0 else 0.0

        # Evaluate overall backtest intelligence scores
        metrics = self.evaluator.evaluate_backtest_metrics(reports)

        # Merge trading metrics dynamically
        metrics.update({
            "initial_balance": initial_balance,
            "final_balance": round(balance, 2),
            "net_p_and_l": round(balance - initial_balance, 2),
            "return_pct": round(((balance - initial_balance) / initial_balance) * 100.0, 2),
            "total_trades": total_trades,
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "win_rate_pct": round(win_rate, 2),
            "gross_profit": round(gross_profit, 2),
            "gross_loss": round(gross_loss, 2),
            "profit_factor": round(profit_factor, 2),
            "average_win": round(average_win, 2),
            "average_loss": round(average_loss, 2),
            "expectancy_usd": expectancy,
            "buy_trades_count": buy_trades,
            "sell_trades_count": sell_trades,
            "best_trade_pnl": best_trade_pnl,
            "worst_trade_pnl": worst_trade_pnl,
            "maximum_drawdown_usd": round(max_dd, 2),
            "maximum_drawdown_pct": max_dd_pct,
            "average_holding_time_minutes": 0.0,
            "decision_authority": "BASE_HIERARCHY",
            "trade_simulation_mode": "DISABLED_LEGACY_ENGINE",
            "equity_curve": equity_curve,
            "trade_list": trades
        })

        return BacktestResult(
            backtest_id=f"bt-{uuid.uuid4().hex[:8]}",
            scenario_id=scenario.scenario_id,
            start_time=scenario.start_time,
            end_time=scenario.end_time,
            total_intervals_processed=total_intervals,
            reports_history=reports,
            performance_metrics=metrics,
            compliance_audit_passed=True
        )
