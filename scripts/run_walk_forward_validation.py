#!/usr/bin/env python3
"""
YARTRADER — WALK-FORWARD VALIDATION & AUTONOMOUS BATCH PROCESSING RUNNER
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
logger = logging.getLogger("WalkForwardValidation")


def run_walk_forward_validation():
    logger.info("==================================================")
    logger.info("YARTRADER — WALK-FORWARD VALIDATION RUNNER")
    logger.info("==================================================")

    connector = ExternalDataPipelineConnector()
    supervisor = IntelligenceSupervisor()
    decision_engine = DecisionEngine()
    engine = IntelligenceBacktestEngine(supervisor=supervisor, decision_engine=decision_engine, connector=connector)

    # 3 Sequential Windows: Train (14d), Validate (7d), OOS (7d)
    base_time = datetime.now(timezone.utc) - timedelta(days=28)
    symbol = "XAUUSD"
    timeframe = "M15"

    windows = [
        {
            "name": "TRAIN_WINDOW_1",
            "start": base_time,
            "end": base_time + timedelta(days=14)
        },
        {
            "name": "VALIDATION_WINDOW_1",
            "start": base_time + timedelta(days=14),
            "end": base_time + timedelta(days=21)
        },
        {
            "name": "OOS_WINDOW_1",
            "start": base_time + timedelta(days=21),
            "end": base_time + timedelta(days=28)
        }
    ]

    wf_results = []
    for w in windows:
        logger.info(f"Executing Walk-Forward Window: {w['name']} ({w['start'].isoformat()} -> {w['end'].isoformat()})")
        scenario = BacktestScenario(
            scenario_id=f"scen-wf-{w['name'].lower()}",
            name=f"Walk-Forward {w['name']}",
            start_time=w["start"],
            end_time=w["end"],
            symbol=symbol,
            timeframe=timeframe,
            parameters={"interval_minutes": 15, "initial_balance": 10000.0}
        )

        res = engine.run_backtest(scenario)
        metrics = res.performance_metrics

        wf_results.append({
            "window": w["name"],
            "start_time": w["start"].isoformat(),
            "end_time": w["end"].isoformat(),
            "intervals_processed": res.total_intervals_processed,
            "total_trades": metrics.get("total_trades", 0),
            "win_rate_pct": metrics.get("win_rate_pct", 0.0),
            "net_pnl": metrics.get("net_p_and_l", 0.0),
            "max_drawdown_pct": metrics.get("maximum_drawdown_pct", 0.0)
        })

    evidence_dir = os.path.join("validation", "backtest_forensic_evidence")
    os.makedirs(evidence_dir, exist_ok=True)

    wf_manifest = {
        "symbol": symbol,
        "timeframe": timeframe,
        "walk_forward_windows": wf_results,
        "executed_at": datetime.now(timezone.utc).isoformat()
    }

    with open(os.path.join(evidence_dir, "walk_forward_manifest.json"), "w", encoding="utf-8") as f:
        json.dump(wf_manifest, f, indent=2, default=str)

    logger.info("Walk-Forward Validation complete. Manifest saved to validation/backtest_forensic_evidence/walk_forward_manifest.json")
    return wf_manifest


if __name__ == "__main__":
    run_walk_forward_validation()
