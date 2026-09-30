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
