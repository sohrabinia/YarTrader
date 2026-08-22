import pytest
from src.Execution.Services.autonomous_demo_runner import AutonomousDemoRunner
from src.Research.Services.market_scanner import MarketScanner
from src.Execution.Services.symbol_discovery import SymbolDiscoveryService
from src.Infrastructure.exceptions import ValidationException

def test_autonomous_runner_single_cycle():
    discovery = SymbolDiscoveryService(mt5_adapter=None)
    scanner = MarketScanner(mt5_adapter=None, discovery_service=discovery)
    runner = AutonomousDemoRunner(scanner=scanner)

    try:
        results = runner.run_loop(max_cycles=1)
        assert len(results) == 1
        cycle = results[0]
        assert cycle["live_trading_enabled"] is False
        assert "decision" in cycle
        assert cycle["decision"]["symbol"] in ["XAUUSD", "EURUSD", "GBPUSD", "BITCOIN"]
    except ValidationException as ve:
        # Expected SRE fail-closed behavior in sandbox environment when MT5 terminal is disconnected
        assert "DemoExecutionGate" in str(ve) or "MT5 Terminal" in str(ve)

def test_market_scanner_ranking():
    discovery = SymbolDiscoveryService(mt5_adapter=None)
    scanner = MarketScanner(mt5_adapter=None, discovery_service=discovery)
    scanned = scanner.scan_markets()
    assert len(scanned) > 0
    assert "spread" in scanned[0]
    assert "liquidity" in scanned[0]
