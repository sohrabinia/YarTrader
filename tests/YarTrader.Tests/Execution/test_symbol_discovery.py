import pytest
from src.Execution.Services.symbol_discovery import SymbolDiscoveryService

def test_symbol_discovery_fallback():
    service = SymbolDiscoveryService(mt5_adapter=None)
    symbols = service.get_tradeable_symbols()
    assert len(symbols) > 0
    sym_names = [s["symbol"] for s in symbols]
    assert "XAUUSD" in sym_names
    assert "EURUSD" in sym_names
    assert "BITCOIN" in sym_names

def test_symbol_discovery_categories():
    service = SymbolDiscoveryService(mt5_adapter=None)
    symbols = service.get_tradeable_symbols()
    for s in symbols:
        assert "category" in s
        assert "volume_min" in s
