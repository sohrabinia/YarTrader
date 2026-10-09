import pytest

from app.workers import historical_learning_queue as queue


def test_primary_symbol_override_is_respected_and_xauusd_is_prioritized(monkeypatch):
    monkeypatch.setenv("YARTRADER_HISTORICAL_LEARNING_SYMBOLS", "EURUSD, XAUUSD, GBPUSD")
    assert queue.load_symbols() == ["XAUUSD", "EURUSD", "GBPUSD"]


def test_empty_symbol_override_falls_back_to_config(monkeypatch):
    monkeypatch.delenv("YARTRADER_HISTORICAL_LEARNING_SYMBOLS", raising=False)
    monkeypatch.setattr(queue, "CONFIG", type("Config", (), {
        "read_text": lambda self, encoding=None: '{"symbols": ["EURUSD", "XAUUSD"]}'
    })())
    assert queue.load_symbols() == ["XAUUSD", "EURUSD"]


def test_history_queue_accepts_only_authorized_read_only_signal_heartbeat(monkeypatch):
    signal = {"login": "143056202", "server": "Alpari-Pro.ECN", "is_demo": False}
    monkeypatch.setattr(queue.glob, "glob", lambda pattern: ["common-files"])
    monkeypatch.setattr(queue, "MT4FileBridge", lambda common_dir=None: type("Bridge", (), {"heartbeat": lambda self: signal})())
    bridge = queue._wait_for_signal_bridge(poll_sec=0)
    assert bridge is not None


def test_history_queue_rejects_demo_or_wrong_server_heartbeat(monkeypatch):
    invalid = {"login": "252031952", "server": "Alpari-Pro.ECN-Demo", "is_demo": True}
    monkeypatch.setattr(queue.glob, "glob", lambda pattern: ["common-files"])
    monkeypatch.setattr(queue, "MT4FileBridge", lambda common_dir=None: type("Bridge", (), {"heartbeat": lambda self: invalid})())
    def stop_waiting(_seconds):
        raise TimeoutError("no authorized signal heartbeat")
    monkeypatch.setattr(queue.time, "sleep", stop_waiting)
    with pytest.raises(TimeoutError, match="no authorized signal heartbeat"):
        queue._wait_for_signal_bridge(poll_sec=0)
