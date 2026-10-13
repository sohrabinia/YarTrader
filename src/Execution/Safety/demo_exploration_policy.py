"""Explicitly scoped demo/backtest exploration policy; never authorizes live trading."""
import os

def demo_exploration_autonomy_enabled() -> bool:
    enabled = lambda key: os.environ.get(key, "").strip().lower() in {"1", "true", "yes", "on"}
    live_value = os.environ.get("LIVE_TRADING_ENABLED", "false").strip().lower()
    live_disabled = live_value in {"0", "false", "no", "off", ""}
    return (enabled("YARTRADER_DEMO_EXPLORATION_MODE")
            and enabled("YARTRADER_AUTONOMOUS_DEMO_TRADING_ENABLED")
            and os.environ.get("YARTRADER_TRADING_MODE", "").strip().upper() == "DEMO"
            and live_disabled)
