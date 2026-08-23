import pytest
from unittest.mock import MagicMock
from src.Execution.Adapters.mt5_adapter import RealMT5BrokerAdapter


def test_recovery_reloads_active_positions():
    adapter = RealMT5BrokerAdapter(auto_initialize=False)
    adapter._initialized = True

    mock_mt5 = MagicMock()
    mock_pos_1 = MagicMock(ticket=1001, symbol="XAUUSD", type=0, volume=0.01, profit=12.50)
    mock_pos_1._asdict.return_value = {"ticket": 1001, "symbol": "XAUUSD", "type": 0, "volume": 0.01, "profit": 12.50}
    mock_pos_2 = MagicMock(ticket=1002, symbol="EURUSD", type=1, volume=0.02, profit=-3.20)
    mock_pos_2._asdict.return_value = {"ticket": 1002, "symbol": "EURUSD", "type": 1, "volume": 0.02, "profit": -3.20}
    mock_mt5.positions_get.return_value = [mock_pos_1, mock_pos_2]

    adapter._mt5 = mock_mt5

    positions = adapter.get_positions()
    assert len(positions) == 2
    assert positions[0]["ticket"] == 1001
    assert positions[1]["ticket"] == 1002
