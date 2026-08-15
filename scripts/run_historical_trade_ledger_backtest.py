#!/usr/bin/env python3
"""
YARTRADER — HISTORICAL TRADE LEDGER BACKTEST RUNNER
Generates trade ledger entries with cost accounting (spread, commission, slippage)
over historical market intervals.
"""

import os
import sys
import json
import hashlib
import logging
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.Application.Backtesting.engine import IntelligenceBacktestEngine
from src.Application.Backtesting.models import BacktestScenario
from src.Data.connector import ExternalDataPipelineConnector
from src.Application.Agents.supervisor import IntelligenceSupervisor
from src.Decision.Intelligence.engine import DecisionEngine

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("TradeLedgerBacktest")


def run_trade_ledger_backtest():
    logger.info("==================================================")
    logger.info("YARTRADER — TRADE LEDGER BACKTEST EXECUTION")
    logger.info("==================================================")

    connector = ExternalDataPipelineConnector()
    supervisor = IntelligenceSupervisor()
    decision_engine = DecisionEngine()
    engine = IntelligenceBacktestEngine(supervisor=supervisor, decision_engine=decision_engine, connector=connector)

    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(days=14)
    symbol = "XAUUSD"
    timeframe = "M15"

    scenario = BacktestScenario(
        scenario_id="scen-ledger-xauusd-14d",
        name="14-Day Trade Ledger Backtest XAUUSD",
        start_time=start_time,
        end_time=end_time,
        symbol=symbol,
        timeframe=timeframe,
        parameters={
            "initial_balance": 10000.0,
            "interval_minutes": 15,
            "spread_usd": 0.25,
            "commission_usd": 0.05,
            "slippage_usd": 0.02
        }
    )

    result = engine.run_backtest(scenario)
    metrics = result.performance_metrics
    trade_list = metrics.get("trade_list", [])

    # Enrich trades with cost accounting details
    ledger_trades = []
    for t in trade_list:
        gross_pnl = t.get("p_and_l", 0.0)
        spread_cost = round(0.25 * t.get("volume", 1.0), 2)
        commission_cost = round(0.05 * t.get("volume", 1.0), 2)
        slippage_cost = round(0.02 * t.get("volume", 1.0), 2)
        net_pnl = round(gross_pnl - spread_cost - commission_cost - slippage_cost, 2)

        entry_price = t.get("entry_price", 0.0)
        exit_price = t.get("exit_price", entry_price)

        mae = round(abs(entry_price - t.get("sl", entry_price)), 2)
        mfe = round(abs(t.get("tp", entry_price) - entry_price), 2)

        ledger_trades.append({
            "trade_id": t.get("trade_id"),
            "run_id": result.backtest_id,
            "symbol": symbol,
            "timeframe": timeframe,
            "direction": t.get("direction"),
            "entry_timestamp": t.get("entry_time"),
            "entry_price": entry_price,
            "volume": t.get("volume", 1.0),
            "stop_loss": t.get("sl"),
            "take_profit": t.get("tp"),
            "exit_timestamp": t.get("exit_time"),
            "exit_price": exit_price,
            "exit_reason": "SL_OR_TP_TRIGGERED" if t.get("status") == "CLOSED" else "END_OF_BACKTEST",
            "gross_pnl": gross_pnl,
            "spread_cost": spread_cost,
            "commission_cost": commission_cost,
            "slippage_cost": slippage_cost,
            "net_pnl": net_pnl,
            "mae": mae,
            "mfe": mfe
        })

    evidence_dir = os.path.join("validation", "backtest_forensic_evidence")
    os.makedirs(evidence_dir, exist_ok=True)

    with open(os.path.join(evidence_dir, "trade_ledger.json"), "w", encoding="utf-8") as f:
        json.dump(ledger_trades, f, indent=2, default=str)

    logger.info(f"Trade ledger written to {os.path.join(evidence_dir, 'trade_ledger.json')}. Total trades: {len(ledger_trades)}")
    return ledger_trades


if __name__ == "__main__":
    run_trade_ledger_backtest()
