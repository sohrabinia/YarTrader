#!/usr/bin/env python3
"""
YARTRADER — STANDALONE MT5 CLOSE REQUEST DIAGNOSTIC SCRIPT
Connects to MT5, inspects open positions (e.g., ticket 368555219), logs symbol/ticks/filling modes,
builds CLOSE trade requests, and tests order_check() across all filling modes (FOK, IOC, RETURN).
"""

import os
import sys
import json
import logging

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.Execution.Adapters.mt5_adapter import RealMT5BrokerAdapter

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("DebugMT5CloseRequest")


def debug_close_request(target_ticket: int = 368555219):
    adapter = RealMT5BrokerAdapter(auto_initialize=True)
    mt5 = adapter._mt5

    if not mt5 or not adapter._initialized:
        logger.error("[DEBUG MT5 CLOSE] MT5 Terminal process unavailable in current environment.")
        return

    term_info = adapter.get_terminal_info()
    acc_info = adapter.get_account_info()
    logger.info(f"[DEBUG MT5 CLOSE] Terminal connected: {term_info.get('name') if term_info else False}")
    logger.info(f"[DEBUG MT5 CLOSE] Account login: {acc_info.get('login') if acc_info else None}")

    positions = adapter.get_positions(ticket=target_ticket)
    if not positions:
        logger.info(f"[DEBUG MT5 CLOSE] Position ticket {target_ticket} not found in positions_get(). Querying all positions...")
        positions = adapter.get_positions()
        logger.info(f"[DEBUG MT5 CLOSE] Active open positions count: {len(positions)}")

    if not positions:
        logger.error("[DEBUG MT5 CLOSE] No open positions found on account.")
        return

    pos = positions[0]
    pos_ticket = pos.get("ticket")
    symbol = pos.get("symbol")
    pos_type = pos.get("type", 0)  # 0=BUY, 1=SELL
    volume = pos.get("volume", 0.01)

    sym_info = mt5.symbol_info(symbol)
    tick = mt5.symbol_info_tick(symbol)

    filling_mode_flags = getattr(sym_info, "filling_mode", None) if sym_info else None
    logger.info(f"[DEBUG MT5 CLOSE] Position Ticket: {pos_ticket}")
    logger.info(f"[DEBUG MT5 CLOSE] Symbol: {symbol}, Type: {'BUY' if pos_type==0 else 'SELL'}, Volume: {volume}")
    logger.info(f"[DEBUG MT5 CLOSE] Tick Bid: {getattr(tick, 'bid', None)}, Ask: {getattr(tick, 'ask', None)}")
    logger.info(f"[DEBUG MT5 CLOSE] symbol.filling_mode flags: {filling_mode_flags}")

    from src.Execution.Models.models import OrderRequest

    close_req = OrderRequest(
        Symbol=symbol,
        OrderType="CLOSE",
        Volume=volume,
        PositionTicket=int(pos_ticket),
        Comment="YarClose"
    )

    digits = int(getattr(sym_info, "digits", 2))
    base_trade_req = adapter._build_close_trade_request(close_req, mt5, sym_info, tick, digits)

    filling_modes = {
        "ORDER_FILLING_FOK": getattr(mt5, "ORDER_FILLING_FOK", 0),
        "ORDER_FILLING_IOC": getattr(mt5, "ORDER_FILLING_IOC", 1),
        "ORDER_FILLING_RETURN": getattr(mt5, "ORDER_FILLING_RETURN", 2),
    }

    results = {}
    for mode_name, mode_val in filling_modes.items():
        trade_req = dict(base_trade_req)
        trade_req["type_filling"] = mode_val

        check_res = mt5.order_check(trade_req)
        last_err = mt5.last_error()

        results[mode_name] = {
            "type_filling": mode_val,
            "order_check_result": check_res._asdict() if check_res and hasattr(check_res, "_asdict") else str(check_res),
            "retcode": getattr(check_res, "retcode", -1) if check_res else -1,
            "comment": getattr(check_res, "comment", None) if check_res else None,
            "mt5_last_error": last_err
        }

        logger.info(
            f"[DEBUG MT5 CLOSE] Mode {mode_name} ({mode_val}): "
            f"retcode={results[mode_name]['retcode']}, comment={results[mode_name]['comment']}, last_error={last_err}"
        )

    print("\n==================================================")
    print("MT5 CLOSE REQUEST DIAGNOSTIC REPORT")
    print("==================================================")
    print(json.dumps(results, indent=2, default=str))
    print("==================================================\n")


if __name__ == "__main__":
    ticket_arg = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 368555219
    debug_close_request(target_ticket=ticket_arg)
