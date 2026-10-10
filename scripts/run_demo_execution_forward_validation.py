import os
import json
import logging
from datetime import datetime, timezone

from src.Execution.Adapters.mt5_adapter import RealMT5BrokerAdapter
from src.Execution.Services.demo_execution_engine import DemoExecutionEngine
from src.Execution.Models.models import OrderRequest
from src.Execution.Safety.demo_execution_gate import DemoExecutionGate
from src.Execution.Services.autonomous_demo_trader import calculate_demo_volume_by_risk

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DemoForwardValidation")


def run_demo_forward_validation():
    print("================================================================================")
    print("YARTRADER CONTROLLED MT5 DEMO EXECUTION FORWARD VALIDATION")
    print("================================================================================")

    from src.Application.Deployment.storage import YarTraderStorageManager
    storage_mgr = YarTraderStorageManager.get_manager()
    out_dir = os.path.join(storage_mgr.get_reports_dir(), "mt5_demo_execution_audit")
    os.makedirs(out_dir, exist_ok=True)

    adapter = RealMT5BrokerAdapter(auto_initialize=True)
    engine = DemoExecutionEngine(adapter=adapter, demo_mode=True, log_dir=out_dir)

    # 1. Environment & Safety Inspection
    acc_info = adapter.get_account_info()
    term_info = adapter.get_terminal_info()

    env_data = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "live_trading_enabled": False,
        "demo_mode_enabled": True,
        "authorized_account": "52961173",
        "authorized_server": "Alpari-MT5-Demo",
        "account_info": acc_info,
        "terminal_info": term_info
    }

    with open(os.path.join(out_dir, "01_environment.json"), "w") as f:
        json.dump(env_data, f, indent=2)

    # 2. Size only from current broker facts and the unified 1% wallet risk policy.
    print("\n[Step 1] Checking whether a risk-sized XAUUSD DEMO order is eligible...")
    try:
        account = adapter.get_account_info()
        symbol_info = adapter.get_symbol_info("XAUUSD")
        tick = adapter.get_symbol_tick("XAUUSD")
        if not account or not symbol_info or not tick or float(tick.get("ask") or 0.0) <= 0:
            raise RuntimeError("Current DEMO account, symbol contract, or quote unavailable; no order submitted.")
        price = float(tick["ask"])
        sl = price - 10.0
        tp = price + 20.0
        sizing = calculate_demo_volume_by_risk(
            adapter._mt5, "XAUUSD", "BUY", price, sl, symbol_info,
            balance=float(account.get("balance") or 0.0),
            equity=float(account.get("equity") or 0.0), risk_pct=1.0,
        )
        if not sizing.get("allowed"):
            raise RuntimeError(f"1% risk sizing rejected the trade: {sizing.get('reason')}; no order submitted.")
        resp = engine.execute_demo_decision(
            symbol="XAUUSD",
            direction="BUY",
            volume=float(sizing["volume"]),
            price=price,
            sl=sl,
            tp=tp,
            comment="YarTrader DEMO Forward Test",
            magic=143056,
            decision_id="DEC-FORWARD-DEMO-001"
        )
        print(f"Order Response: Status={resp.Status}, OrderId={resp.OrderId}, Comment={resp.Comment}")

        result_data = {
            "status": resp.Status,
            "order_id": resp.OrderId,
            "deal_ticket": resp.DealTicket,
            "retcode": resp.Retcode,
            "comment": resp.Comment,
            "raw_response": resp.RawResponse
        }
        with open(os.path.join(out_dir, "02_execution_result.json"), "w") as f:
            json.dump(result_data, f, indent=2)
    except Exception as e:
        print(f"Demo Execution Gate / Adapter Exception: {e}")
        with open(os.path.join(out_dir, "02_execution_error.json"), "w") as f:
            json.dump({"error": str(e)}, f, indent=2)

    print("\n================================================================================")
    print("DEMO FORWARD VALIDATION COMPLETE")
    print(f"Evidence artifacts stored under: {out_dir}/")
    print("================================================================================")


if __name__ == "__main__":
    run_demo_forward_validation()
