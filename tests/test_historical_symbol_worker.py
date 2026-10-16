from app.workers import historical_symbol_worker as worker


def test_history_requests_are_capped_for_constrained_host():
    assert worker.required_bars("M1", 10) == 100000
    assert worker.required_bars("H1", 10) == 15000
    assert worker.required_bars("MN1", 100) == 600


def test_missing_timeframe_is_skipped_without_aborting_other_history(monkeypatch):
    class FakeBridge:
        def heartbeat(self):
            return {"login": worker.SIGNAL_LOGIN, "server": worker.SIGNAL_SERVER, "is_demo": False}

    class FakeProvider:
        pass

    class FakeAcquisition:
        def __init__(self, bridge, provider):
            self.bridge = bridge
            self.provider = provider

        def acquire(self, symbol, timeframe, bars, allow_partial=True):
            if timeframe == "M30":
                raise RuntimeError("NO_HISTORY")
            return {
                "symbol": symbol,
                "timeframe": timeframe,
                "source": "MT4_BROKER_HST",
                "first_time": 0,
                "last_time": 2 * 365 * 86400,
                "synthetic_data": False,
                "future_data_injected": False,
            }

    monkeypatch.setattr(worker, "find_signal_bridge", lambda: FakeBridge())
    monkeypatch.setattr(worker, "MT4HistoricalDataProvider", FakeProvider)
    monkeypatch.setattr(worker, "MT4HistoryAcquisition", FakeAcquisition)

    manifests, effective_years = worker.acquire_all("XAUUSD", 10)
    by_tf = {item["timeframe"]: item for item in manifests}
    assert by_tf["M30"]["status"] == "SKIPPED"
    assert by_tf["H1"]["status"] == "READY"
    assert effective_years == 2.0


def test_effective_years_reflect_selected_timeframe_coverage(tmp_path, monkeypatch):
    import json

    manifests = [
        {"timeframe": "H1", "status": "READY", "available_days": 218.7,
         "source": "MT4_BROKER_HST", "synthetic_data": False, "future_data_injected": False},
        {"timeframe": "M15", "status": "READY", "available_days": 105.9,
         "source": "MT4_BROKER_HST", "synthetic_data": False, "future_data_injected": False},
        {"timeframe": "M1", "status": "READY", "available_days": 76.3,
         "source": "MT4_BROKER_HST", "synthetic_data": False, "future_data_injected": False},
    ]
    monkeypatch.setattr(worker, "acquire_all", lambda symbol, years: (manifests, 10.0))
    monkeypatch.setattr(
        worker, "run_staged_backtest",
        lambda symbol, timeframe, years, balance, root, **kwargs: {
            "status": "COMPLETED", "symbol": symbol, "timeframe": timeframe,
            "processed_bars": 10,
        },
    )
    monkeypatch.setenv("YARTRADER_HISTORICAL_LEARNING_ROOT", str(tmp_path / "queue"))
    monkeypatch.setenv("YARTRADER_HISTORICAL_LEARNING_TIMEFRAMES", "H1")

    result = worker.run("XAUUSD", 10, 10000.0, 0.0)
    manifest = json.loads((tmp_path / "queue" / "historical_staging" / "XAUUSD" / "acquisition_manifest.json").read_text())
    expected_years = 218.7 / 365.0
    assert abs(result["effective_learning_years"] - expected_years) < 1e-9
    assert abs(manifest["effective_learning_years"] - expected_years) < 1e-9
    assert manifest["learning_timeframes"] == ["H1"]
