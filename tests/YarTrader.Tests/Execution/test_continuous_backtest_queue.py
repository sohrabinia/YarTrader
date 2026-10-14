import json
from pathlib import Path

from app.workers import continuous_backtest_queue as queue
from app.workers import mt5_backtest_supervisor as supervisor


def test_queue_excludes_known_missing_mt5_symbol(monkeypatch, tmp_path):
    cfg = tmp_path / "symbols.json"
    cfg.write_text(json.dumps({"symbols": ["XAUUSD", "EURUSD", "BTCUSD"]}), encoding="utf-8")
    monkeypatch.setattr(queue, "CONFIG", cfg)
    monkeypatch.setattr(queue, "ROOT", tmp_path)
    monkeypatch.delenv("YARTRADER_BACKTEST_SYMBOLS", raising=False)
    monkeypatch.delenv("YARTRADER_BACKTEST_EXCLUDED_SYMBOLS", raising=False)
    assert queue.symbols() == ["XAUUSD", "EURUSD"]


def test_summary_complete_requires_every_reported_timeframe_completed(monkeypatch, tmp_path):
    monkeypatch.setattr(queue, "SUMMARY_ROOT", tmp_path)
    symbol_dir = tmp_path / "XAUUSD"
    symbol_dir.mkdir()
    summary = symbol_dir / "summary.json"
    summary.write_text(json.dumps({"timeframe_windows": {"M1": {"status": "COMPLETED"}, "H1": {"status": "RUNNING"}}}), encoding="utf-8")
    assert not queue.summary_complete("XAUUSD")
    summary.write_text(json.dumps({"timeframe_windows": {"M1": {"status": "COMPLETED"}, "H1": {"status": "COMPLETED"}}}), encoding="utf-8")
    assert queue.summary_complete("XAUUSD")


def test_supervisor_reads_symbol_level_mtf_summary(monkeypatch, tmp_path):
    monkeypatch.setattr(supervisor, "ROOT", tmp_path)
    p = tmp_path / "runtime_logs" / "backtest_learning" / "mtf_incremental" / "XAUUSD" / "summary.json"
    p.parent.mkdir(parents=True)
    p.write_text(json.dumps({"timeframe_windows": {"M1": {"status": "COMPLETED"}, "H1": {"status": "COMPLETED"}}}), encoding="utf-8")
    assert supervisor.checkpoint({"symbol": "XAUUSD", "timeframe": "MTF"})["status"] == "COMPLETED"
    p.write_text(json.dumps({"timeframe_windows": {"M1": {"status": "COMPLETED"}, "H1": {"status": "RUNNING"}}}), encoding="utf-8")
    assert supervisor.checkpoint({"symbol": "XAUUSD", "timeframe": "MTF"})["status"] == "RUNNING"
