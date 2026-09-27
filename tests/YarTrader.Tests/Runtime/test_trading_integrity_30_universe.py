import os
import math
import time
import pytest
from unittest.mock import MagicMock
from app.workers.research_worker import ResearchWorker
from src.ShadowTrading.Engine.SymbolRegistry import SymbolRegistry
from src.Application.Journal.trade_journal import TradeJournalManager, TradeJournalRecord
from src.Application.Learning.trade_learning import TradeLearningEngine

class DummyAdapter:
    def __init__(self, account_info=None, symbol_info=None):
        self._account_info = account_info or {
            "balance": 10000.0,
            "equity": 10000.0,
            "free_margin": 8000.0
        }
        self._symbol_info = symbol_info or {
            "volume_min": 0.01,
            "volume_max": 100.0,
            "volume_step": 0.01
        }

    def get_account_info(self):
        return self._account_info

    def get_symbol_info(self, symbol):
        return self._symbol_info


class DummyDemoEngine:
    def __init__(self, adapter=None):
        self.adapter = adapter or DummyAdapter()
        self.execute_demo_decision = MagicMock()
        self.get_active_positions = MagicMock(return_value=[])


# --- 1. EXACT 30-UNIVERSE TESTS ---

def test_exact_30_canonical_universe_loader():
    sr = SymbolRegistry.get_instance()
    sr.load_registry()
    registered = sr.get_all_registered()
    assert len(registered) == 30
    assert "XAUUSD" in registered
    assert "BTCUSD" in registered
    assert "USOIL" not in registered
    assert "NAS100" not in registered

    active_matrix = sr.get_active_matrix()
    unique_active = sorted(list(set(s for s, t, ac, p in active_matrix)))
    assert len(unique_active) == 30


def test_registry_enforces_max_symbols_limit():
    sr = SymbolRegistry.get_instance()
    # Reset registry to 30 symbols
    sr.load_registry()
    with pytest.raises(ValueError) as exc_info:
        sr.register_symbol("NEW1", ["H1"])
    assert "Hard SRE limit reached" in str(exc_info.value)


# --- 2. DIRECTIONAL & DEMO SCOPE TESTS ---

def test_buy_and_sell_direction_mapping():
    worker = ResearchWorker(symbol="XAUUSD", timeframe="H1")
    worker.demo_engine = DummyDemoEngine()

    buy_dec = {"entry": 2300.0, "stop_loss": 2290.0, "take_profit": 2320.0}
    buy_sized = worker._validate_and_size_decision("XAUUSD", "BUY", buy_dec)
    assert buy_sized is not None
    assert buy_sized["price"] == 2300.0
    assert buy_sized["sl"] == 2290.0
    assert buy_sized["tp"] == 2320.0

    sell_dec = {"entry": 2300.0, "stop_loss": 2310.0, "take_profit": 2280.0}
    sell_sized = worker._validate_and_size_decision("XAUUSD", "SELL", sell_dec)
    assert sell_sized is not None
    assert sell_sized["price"] == 2300.0
    assert sell_sized["sl"] == 2310.0
    assert sell_sized["tp"] == 2280.0


# --- 3. 1% RISK SIZING TESTS ---

def test_risk_position_sizing_1_percent_balance():
    worker = ResearchWorker(symbol="XAUUSD", timeframe="H1")
    worker.demo_engine = DummyDemoEngine()

    # Balance = $10,000 -> 1% risk budget = $100
    # Entry = 2300.0, SL = 2290.0 (SL distance = $10.0 per oz)
    # For XAUUSD (100 oz contract size), 1 lot loss = $1000 at $10 SL
    # Lots required = $100 / $1000 = 0.10 lots
    dec = {"entry": 2300.0, "stop_loss": 2290.0, "take_profit": 2320.0}
    sized = worker._validate_and_size_decision("XAUUSD", "BUY", dec)

    assert sized is not None
    assert sized["risk_budget_usd"] == 100.0
    assert sized["risk_pct"] == 1.0
    assert sized["volume_lots"] == 0.10


def test_exceeding_max_risk_ceiling_blocked(monkeypatch):
    monkeypatch.setenv("RISK_PCT_PER_TRADE", "2.5")
    worker = ResearchWorker(symbol="XAUUSD", timeframe="H1")
    worker.demo_engine = DummyDemoEngine()
    dec = {"entry": 2300.0, "stop_loss": 2290.0, "take_profit": 2320.0}
    sized = worker._validate_and_size_decision("XAUUSD", "BUY", dec)
    assert sized is None


# --- 4. TRADE JOURNAL & POST-TRADE ANALYSIS TESTS ---

def test_trade_journal_entry_and_exit_record(tmp_path):
    journal_mgr = TradeJournalManager(log_dir=str(tmp_path))

    entry_rec = journal_mgr.record_entry(
        trade_id="TRD-XAUUSD-001",
        decision_id="DEC-001",
        symbol="XAUUSD",
        timeframe="H1",
        direction="BUY",
        strategy_id="ST-CORE",
        strategy_version="1.2.0",
        entry_price=2300.0,
        requested_price=2300.0,
        actual_fill_price=2300.0,
        volume_lots=0.10,
        account_balance=10000.0,
        account_equity=10000.0,
        risk_pct=1.0,
        risk_budget_usd=100.0,
        stop_loss=2290.0,
        take_profit=2320.0,
        risk_reward=2.0,
        confidence=80.0,
        decision_reason="Bullish structure break",
        supporting_evidence={"narrative": "TRENDING"},
        research_snapshot_id="SNAP-001",
        broker_order_ticket="1001",
        broker_deal_ticket="2001"
    )

    assert entry_rec.trade_id == "TRD-XAUUSD-001"
    assert entry_rec.symbol == "XAUUSD"

    exit_rec = journal_mgr.record_exit(
        trade_id="TRD-XAUUSD-001",
        exit_price=2320.0,
        realized_pnl=200.0,
        exit_reason="TAKE_PROFIT",
        closing_deal_ticket="2002",
        duration_seconds=3600.0
    )

    assert exit_rec is not None
    assert exit_rec.result_classification == "WIN"
    assert exit_rec.realized_pnl == 200.0
    assert exit_rec.post_trade_analysis is not None
    assert exit_rec.post_trade_analysis["result_classification"] == "WIN"


# --- 5. OBSERVATIONAL LEARNING ENGINE TESTS ---

def test_observational_learning_engine_non_mutating(tmp_path):
    journal_mgr = TradeJournalManager(log_dir=str(tmp_path))
    journal_mgr.record_entry(
        trade_id="TRD-XAUUSD-001",
        decision_id="DEC-001",
        symbol="XAUUSD",
        timeframe="H1",
        direction="BUY",
        strategy_id="ST-CORE",
        strategy_version="1.2.0",
        entry_price=2300.0,
        requested_price=2300.0,
        actual_fill_price=2300.0,
        volume_lots=0.10,
        account_balance=10000.0,
        account_equity=10000.0,
        risk_pct=1.0,
        risk_budget_usd=100.0,
        stop_loss=2290.0,
        take_profit=2320.0,
        risk_reward=2.0,
        confidence=80.0,
        decision_reason="Bullish structure break",
        supporting_evidence={"narrative": "TRENDING"},
        research_snapshot_id="SNAP-001",
        broker_order_ticket="1001",
        broker_deal_ticket="2001"
    )
    journal_mgr.record_exit(
        trade_id="TRD-XAUUSD-001",
        exit_price=2320.0,
        realized_pnl=200.0,
        exit_reason="TAKE_PROFIT",
        closing_deal_ticket="2002",
        duration_seconds=3600.0
    )

    learning_engine = TradeLearningEngine(journal_manager=journal_mgr)
    summary = learning_engine.generate_learning_summary()

    assert summary["status"] == "COMPLETED"
    assert summary["total_trades"] == 1
    assert summary["win_rate_pct"] == 100.0
    assert summary["live_strategy_mutation"] is False
    assert summary["autonomous_adaptation_blocked"] is True
