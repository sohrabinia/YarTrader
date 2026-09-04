"""
Unit and Integration Tests for Continuous Market-Following Engine & Gold Trading Contract
========================================================================================
"""

import pytest
from datetime import datetime, timezone, timedelta
from src.Research.MarketAnalysis.Services.continuous_market_following_engine import (
    ContinuousMarketFollowingEngine,
    ProbabilisticPathForecast,
    TradeEfficiencyMetrics
)
from src.Risk.Services.professional_risk_engine import ProfessionalRiskEngine
from src.Execution.Safety.demo_execution_gate import DemoExecutionGate
from src.Infrastructure.exceptions import ValidationException


class DummyRequest:
    def __init__(self, symbol="XAUUSD", order_type="BUY", price=2500.0, sl=2497.5, tp=2506.0, strategy="FAST_SCALP", volume=0.1):
        self.Symbol = symbol
        self.OrderType = order_type
        self.Price = price
        self.StopLoss = sl
        self.TakeProfit = tp
        self.StrategyName = strategy
        self.Volume = volume


class DummyAdapter:
    def get_account_info(self):
        return {"login": 52961173, "server": "Alpari-MT5-Demo", "trade_mode": 0, "is_real": False, "platform": "MT5"}
    def get_terminal_info(self):
        return {"trade_allowed": True, "tradeapi_disabled": False}
    def get_symbol_info(self, symbol):
        return {"trade_mode": 4, "volume_min": 0.01, "volume_max": 100.0, "volume_step": 0.01}
    def get_positions(self, symbol=None):
        return []


def test_continuous_market_following_engine_observation_and_path_estimation():
    engine = ContinuousMarketFollowingEngine(symbol="XAUUSD")
    base_price = 2500.0
    for i in range(20):
        engine.observe(price=base_price + (i * 0.5), volume=1.0 + (i * 0.1))

    forecast = engine.estimate_path_distribution()
    assert isinstance(forecast, ProbabilisticPathForecast)
    assert forecast.symbol == "XAUUSD"
    assert 0.0 <= forecast.continuation_probability <= 1.0
    assert 0.0 <= forecast.exhaustion_probability <= 1.0
    assert 0.0 <= forecast.reversal_probability <= 1.0
    assert forecast.expected_mfe > 0.0
    assert forecast.expected_mae > 0.0


def test_trade_efficiency_metrics_calculation():
    engine = ContinuousMarketFollowingEngine(symbol="XAUUSD")
    eff = engine.calculate_trade_efficiency(
        trade_id="TR-1001",
        direction="BUY",
        entry_price=2500.0,
        exit_price=2507.0,
        local_min_price=2499.0,
        local_max_price=2508.0,
        holding_time_seconds=300.0
    )
    assert isinstance(eff, TradeEfficiencyMetrics)
    assert eff.entry_efficiency_pct > 0.0
    assert eff.exit_efficiency_pct > 0.0
    assert eff.move_capture_ratio > 0.5


def test_dynamic_risk_and_execution_gate_verification():
    risk_engine = ProfessionalRiskEngine()
    adapter = DummyAdapter()

    # Valid trade evaluation with dynamic SL/TP
    res_valid = risk_engine.evaluate_trade_risk(
        symbol="XAUUSD",
        direction="BUY",
        entry_price=2500.0,
        stop_loss=2497.0,
        take_profit=2508.0
    )
    assert res_valid.is_valid is True

    # Valid request evaluated through execution gate
    req_valid = DummyRequest(symbol="XAUUSD", sl=2497.0, tp=2508.0, strategy="DYNAMIC_FOLLOW")
    assert DemoExecutionGate.verify_demo_execution_eligibility(adapter, req_valid, demo_mode_flag=True) is True
