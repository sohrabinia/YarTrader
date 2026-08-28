import pytest
import uuid
import hashlib
from datetime import datetime, timezone
from src.Learning.Services.experiment_runner import PerturbatedExperimentRunner

class TestPhaseDExperimentRunner:
    def test_perturbated_experiment_execution(self):
        runner = PerturbatedExperimentRunner()
        historical_bars = [{"timestamp": f"2026-03-01T{i:02d}:00:00Z", "close": 2000.0 + i} for i in range(100)]

        res = runner.run_experiment(
            strategy_version="v1.2.0",
            market="XAUUSD",
            timeframe="M5",
            historical_bars=historical_bars,
            slippage_perturbation_pip=0.8,
            spread_perturbation_pip=1.2,
            parameter_overrides={"rsi_period": 14}
        )

        assert res.experiment_id.startswith("exp-")
        assert res.total_trades > 0
        assert res.perturbations["slippage_pip"] == 0.8
        assert res.net_pnl_usd != 0.0
