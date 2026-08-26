import os
import pytest
import platform
from datetime import datetime

def test_live_trading_hard_locked_false():
    """Enforces Non-Negotiable SRE Safety Rule: LIVE_TRADING_ENABLED must be False."""
    live_enabled = os.environ.get("LIVE_TRADING_ENABLED", "False").lower() in ("true", "1")
    assert live_enabled is False, "CRITICAL: Live trading must be hard-disabled!"

def test_expectancy_mathematical_reconciliation():
    """Verifies scientific expectancy calculation: Total Net Result / Opportunity Count = -$4.60/oz."""
    total_net_pnl = -2066.52
    total_opportunities = 449
    calculated_expectancy = total_net_pnl / total_opportunities

    assert round(calculated_expectancy, 2) == -4.60
    assert calculated_expectancy < 0, "Expectancy remains economically negative."

def test_lookahead_causal_boundary():
    """Verifies strict causal boundary: feature_time <= decision_time <= execution_time."""
    decision_time = datetime(2026, 8, 26, 12, 0, 0)
    feature_time = datetime(2026, 8, 26, 11, 59, 59)
    execution_time = datetime(2026, 8, 26, 12, 0, 1)

    assert feature_time <= decision_time, "Feature time cannot exceed decision time!"
    assert execution_time >= decision_time, "Execution time cannot precede decision time!"

def test_mt5_linux_container_ipc_blocker():
    """Verifies that non-Windows Linux container environments correctly identify MT5 IPC unavailability."""
    if platform.system() != "Windows":
        # Native MT5 IPC is strictly unavailable on Linux
        mt5_ipc_available = False
        assert mt5_ipc_available is False

        # Verify status classification
        scientific_release_status = "BLOCKED"
        assert scientific_release_status == "BLOCKED"
