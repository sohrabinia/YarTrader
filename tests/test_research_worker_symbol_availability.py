from app.workers.research_worker import ResearchWorker


def test_unavailable_production_symbol_is_classified_as_skippable():
    error = RuntimeError(
        "Validation Error: Failed to fetch market data for primitive research: "
        "MT5 Adapter Error: SRE Security Error: Symbol 'BTCUSD' is not selected "
        "or available in real MT5 terminal in production mode."
    )

    assert ResearchWorker._is_market_data_unavailable_error(error) is True


def test_unrelated_research_failure_is_not_classified_as_symbol_unavailable():
    error = RuntimeError(
        "Validation Error: Failed to fetch market data for primitive research: "
        "MT5 Adapter Error: connection reset by peer."
    )

    assert ResearchWorker._is_market_data_unavailable_error(error) is False


def test_historical_queue_handles_failing_symbol_without_halting(tmp_path, monkeypatch):
    import json, subprocess
    from unittest.mock import MagicMock
    import app.workers.historical_learning_queue as queue_mod

    # Redirect ROOT and CONFIG
    state_file = tmp_path / "runtime_logs" / "backtest_learning" / "historical_queue_state.json"
    config_file = tmp_path / "config" / "historical_learning_symbols.json"
    config_file.parent.mkdir(parents=True, exist_ok=True)
    config_file.write_text(json.dumps({"symbols": ["SYM1", "SYM2_FAIL", "SYM3"]}), encoding="utf-8")

    monkeypatch.setattr(queue_mod, "ROOT", tmp_path)
    monkeypatch.setattr(queue_mod, "CONFIG", config_file)
    monkeypatch.setattr(queue_mod, "_wait_for_signal_bridge", lambda: MagicMock())

    def mock_subprocess_run(cmd, cwd=None, check=False):
        mock_res = MagicMock()
        symbol = cmd[cmd.index("--symbol") + 1]
        if symbol == "SYM2_FAIL":
            mock_res.returncode = 1
        else:
            mock_res.returncode = 0
        return mock_res

    monkeypatch.setattr(subprocess, "run", mock_subprocess_run)

    state = queue_mod.run_queue(years=5, initial_balance=10000.0, sleep_sec=0.0)

    assert state["status"] == "COMPLETED"
    assert "SYM1" in state["completed_symbols"]
    assert "SYM3" in state["completed_symbols"]
    assert "SYM2_FAIL" in state["failed_symbols"]
    assert state_file.exists()
