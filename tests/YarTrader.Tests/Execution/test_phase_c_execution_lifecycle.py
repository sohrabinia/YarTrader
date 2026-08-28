import pytest
from datetime import datetime, timezone

from src.Decision.Models.models import ExecutableTradingContract
from src.Execution.Services.session_execution_manager import SessionExecutionManager
from src.Execution.Services.order_lifecycle_manager import OrderLifecycleManager

class TestPhaseCExecutionLifecycle:

    def test_executable_trading_contract_validation(self):
        contract = ExecutableTradingContract(
            trade_id="tr_101",
            symbol="XAUUSD",
            direction="BUY",
            entry_price=2000.0,
            stop_loss=1990.0,
            take_profit=2050.0,
            volume_lots=1.0,
            account_equity=10000.0,
            free_margin=5000.0,
            execution_timeframe="M5",
            trading_style="FAST_SCALP"
        )
        res = contract.validate_contract_rules()
        assert res["is_valid"] is True
        assert len(res["rejection_reasons"]) == 0

    def test_executable_contract_rejects_non_m5_timeframe(self):
        contract = ExecutableTradingContract(
            trade_id="tr_102",
            symbol="XAUUSD",
            direction="BUY",
            entry_price=2000.0,
            stop_loss=1990.0,
            take_profit=2050.0,
            volume_lots=1.0,
            account_equity=10000.0,
            free_margin=5000.0,
            execution_timeframe="M15",  # Invalid execution timeframe
            trading_style="SCALP"
        )
        res = contract.validate_contract_rules()
        assert res["is_valid"] is False
        assert any("violates primary M5 contract" in r for r in res["rejection_reasons"])

    def test_120_second_minimum_hold_constraint(self):
        manager = SessionExecutionManager()

        # Exit attempt at 30 seconds -> REJECTED
        res30 = manager.evaluate_exit_permission(holding_duration_seconds=30.0, exit_reason="TAKE_PROFIT")
        assert res30["allowed"] is False
        assert res30["rejection_reason"] == "EARLY_EXIT_BLOCKED_MIN_HOLD_120S"

        # Exit attempt at 119 seconds -> REJECTED
        res119 = manager.evaluate_exit_permission(holding_duration_seconds=119.0, exit_reason="TAKE_PROFIT")
        assert res119["allowed"] is False

        # Exit attempt at 120 seconds -> ALLOWED
        res120 = manager.evaluate_exit_permission(holding_duration_seconds=120.0, exit_reason="TAKE_PROFIT")
        assert res120["allowed"] is True

        # Emergency exit before 120 seconds -> ALLOWED
        res_eod = manager.evaluate_exit_permission(holding_duration_seconds=10.0, exit_reason="EOD_FLATTEN")
        assert res_eod["allowed"] is True

    def test_forbidden_trading_style_rejection(self):
        manager = SessionExecutionManager()

        # SWING style -> REJECTED
        res_swing = manager.evaluate_entry_permission(trading_style="SWING", remaining_session_seconds=3600.0)
        assert res_swing["allowed"] is False
        assert "FORBIDDEN_STYLE" in res_swing["rejection_reason"]

        # OVERNIGHT style -> REJECTED
        res_overnight = manager.evaluate_entry_permission(trading_style="OVERNIGHT", remaining_session_seconds=3600.0)
        assert res_overnight["allowed"] is False

        # FAST_SCALP -> ALLOWED
        res_scalp = manager.evaluate_entry_permission(trading_style="FAST_SCALP", remaining_session_seconds=3600.0)
        assert res_scalp["allowed"] is True

    def test_eod_flatten_safety_invariant(self):
        manager = SessionExecutionManager()
        positions = [{"ticket": "1001"}, {"ticket": "1002"}]
        pending = [{"ticket": "2001"}]

        eod_res = manager.execute_eod_flattening(active_positions=positions, pending_orders=pending)
        assert eod_res.success is True
        assert eod_res.closed_positions_count == 2
        assert eod_res.cancelled_pending_count == 1
        assert eod_res.remaining_open_positions == 0
        assert eod_res.remaining_pending_orders == 0
        assert manager.session_state == "SESSION_CLOSED"

    def test_order_deduplication_and_idempotency(self):
        om = OrderLifecycleManager()
        req_id = "req_client_hash_001"

        # First submission -> SUCCESS
        res1 = om.submit_order_request(
            request_id=req_id,
            symbol="XAUUSD",
            order_type="MARKET_BUY",
            volume_lots=1.0,
            price=2000.0,
            stop_loss=1990.0,
            take_profit=2050.0
        )
        assert res1["success"] is True
        assert res1["order_state"].status == "SUBMITTED"

        # Second submission with same request_id -> REJECTED
        res2 = om.submit_order_request(
            request_id=req_id,
            symbol="XAUUSD",
            order_type="MARKET_BUY",
            volume_lots=1.0,
            price=2000.0,
            stop_loss=1990.0,
            take_profit=2050.0
        )
        assert res2["success"] is False
        assert res2["rejection_reason"] == "DUPLICATE_ORDER_REJECTED"

    def test_restart_state_reconciliation(self):
        om = OrderLifecycleManager()
        broker_positions = [{"ticket": "101"}, {"ticket": "102"}]
        local_positions = [{"ticket": "101"}, {"ticket": "102"}]

        recon = om.reconcile_broker_and_local_state(broker_positions, local_positions)
        assert recon["is_synchronized"] is True
        assert len(recon["synchronized_tickets"]) == 2

        # Detect discrepancy
        broker_positions_discrepant = [{"ticket": "101"}, {"ticket": "102"}, {"ticket": "103"}]
        recon_disc = om.reconcile_broker_and_local_state(broker_positions_discrepant, local_positions)
        assert recon_disc["is_synchronized"] is False
        assert "103" in recon_disc["orphaned_on_broker"]
