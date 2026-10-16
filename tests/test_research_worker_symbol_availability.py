import os
from unittest.mock import patch

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


def test_production_research_preserves_enabled_multi_symbol_matrix():
    full_matrix = [
        ("XAUUSD", "M15", "Commodities", "MT5"),
        ("XAUUSD", "H1", "Commodities", "MT5"),
        ("EURUSD", "H1", "Forex", "MT5"),
    ]
    worker = ResearchWorker(symbol="XAUUSD", timeframe="H1")
    with patch.dict(os.environ, {
        "YARTRADER_ENV": "production",
        "TRADEYAR_ENV": "production",
        "RG_ENV": "production",
        "YARTRADER_RESEARCH_PRIMARY_ONLY": "true",
    }, clear=False):
        with patch("src.Market.Universe.symbol_registry.SymbolRegistry.get_instance") as get_instance:
            get_instance.return_value.get_active_matrix.return_value = full_matrix
            assert worker._get_active_matrix() == full_matrix


def test_multi_symbol_matrix_is_preserved_in_nonproduction_too():
    full_matrix = [
        ("XAUUSD", "H1", "Commodities", "MT5"),
        ("EURUSD", "H1", "Forex", "MT5"),
    ]
    worker = ResearchWorker(symbol="XAUUSD", timeframe="H1")
    with patch.dict(os.environ, {
        "YARTRADER_ENV": "test",
        "TRADEYAR_ENV": "test",
        "RG_ENV": "test",
        "YARTRADER_RESEARCH_PRIMARY_ONLY": "true",
    }, clear=False):
        with patch("src.Market.Universe.symbol_registry.SymbolRegistry.get_instance") as get_instance:
            get_instance.return_value.get_active_matrix.return_value = full_matrix
            assert worker._get_active_matrix() == full_matrix
