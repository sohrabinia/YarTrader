import logging

import pytest

from src.Execution.Services import autonomous_demo_trader
from src.Research.Brain import memory as memory_module


def _set_demo_exploration_env(monkeypatch, **overrides):
    values = {
        "YARTRADER_DEMO_EXPLORATION_MODE": "true",
        "YARTRADER_AUTONOMOUS_DEMO_TRADING_ENABLED": "true",
        "YARTRADER_TRADING_MODE": "DEMO",
        "LIVE_TRADING_ENABLED": "false",
    }
    values.update(overrides)
    for key, value in values.items():
        monkeypatch.setenv(key, value)


def test_demo_exploration_is_enabled_only_for_explicit_demo_opt_in(monkeypatch):
    _set_demo_exploration_env(monkeypatch)
    assert autonomous_demo_trader._demo_exploration_enabled() is True


@pytest.mark.parametrize(
    "overrides",
    [
        {"YARTRADER_DEMO_EXPLORATION_MODE": "false"},
        {"YARTRADER_AUTONOMOUS_DEMO_TRADING_ENABLED": "false"},
        {"YARTRADER_TRADING_MODE": "LIVE"},
        {"LIVE_TRADING_ENABLED": "true"},
    ],
)
def test_demo_exploration_fails_closed_outside_demo_opt_in(monkeypatch, overrides):
    _set_demo_exploration_env(monkeypatch, **overrides)
    assert autonomous_demo_trader._demo_exploration_enabled() is False


def test_memory_save_failure_is_logged_with_layer_and_traceback(tmp_path, monkeypatch, caplog):
    memory = memory_module.MarketMemorySystem(storage_dir=str(tmp_path))

    def fail_replace(*args, **kwargs):
        raise OSError("simulated disk write failure")

    monkeypatch.setattr(memory_module.os, "replace", fail_replace)
    with caplog.at_level(logging.ERROR, logger="yartrader_memory"):
        memory._save_layer("events")

    assert "Failed to persist memory layer 'events'" in caplog.text
    assert "simulated disk write failure" in caplog.text
