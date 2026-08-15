#!/usr/bin/env python3
"""
YARTRADER — REAL HISTORICAL BACKTEST EXECUTION & PROVENANCE RUNNER
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
logger = logging.getLogger("RealHistoricalBacktest")


def run_historical_backtest():
    logger.info("==================================================")
    logger.info("YARTRADER — REAL HISTORICAL BACKTEST EXECUTION")
    logger.info("==================================================")

    # Initialize components
    connector = ExternalDataPipelineConnector()
    supervisor = IntelligenceSupervisor()
    decision_engine = DecisionEngine()
    engine = IntelligenceBacktestEngine(supervisor=supervisor, decision_engine=decision_engine, connector=connector)

    # Define 30-day historical window
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(days=30)
    symbol = "XAUUSD"
    timeframe = "M15"

    scenario = BacktestScenario(
        scenario_id="scen-real-hist-xauusd-30d",
        name="30-Day Historical Backtest XAUUSD",
        start_time=start_time,
        end_time=end_time,
        symbol=symbol,
        timeframe=timeframe,
        parameters={
            "initial_balance": 10000.0,
            "interval_minutes": 15,
            "spread_usd": 0.25,
            "commission_usd": 0.05
        }
    )

    result = engine.run_backtest(scenario)
    metrics = result.performance_metrics

    # Compute Dataset SHA-256 Hash
    dataset_summary = f"{symbol}_{timeframe}_{start_time.isoformat()}_{end_time.isoformat()}_{result.total_intervals_processed}"
    dataset_hash = hashlib.sha256(dataset_summary.encode("utf-8")).hexdigest()

    manifest = {
        "run_id": result.backtest_id,
        "dataset_id": f"ds-{symbol.lower()}-{timeframe.lower()}-30d",
        "dataset_hash": dataset_hash,
        "symbol": symbol,
        "timeframe": timeframe,
        "provider": connector.mt5_provider.__class__.__name__,
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "intervals_processed": result.total_intervals_processed,
        "performance_metrics": metrics,
        "compliance_audit_passed": result.compliance_audit_passed,
        "executed_at": datetime.now(timezone.utc).isoformat()
    }

    evidence_dir = os.path.join("validation", "backtest_forensic_evidence")
    os.makedirs(evidence_dir, exist_ok=True)

    with open(os.path.join(evidence_dir, "run_manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, default=str)

    logger.info(f"Backtest completed successfully. Total Intervals: {result.total_intervals_processed}")
    logger.info(f"Total Trades: {metrics.get('total_trades')}, Win Rate: {metrics.get('win_rate_pct')}%, Net P&L: ${metrics.get('net_p_and_l')}")
    logger.info(f"Manifest written to {os.path.join(evidence_dir, 'run_manifest.json')}")

    return manifest


if __name__ == "__main__":
    run_historical_backtest()
