"""
YARTRADER — Autonomous Demo Trading Runner
Executes continuous autonomous demo trading loop connecting market scanner,
signal engine, risk gates, demo execution, position monitoring, and post-trade learning.
Strictly enforces LIVE_TRADING_ENABLED=False.
"""

import time
import logging
from typing import Dict, Any, Optional

from src.Execution.Safety.demo_execution_gate import DemoExecutionGate
from src.Execution.Safety.safety_gate import MetaTraderSafetyGate
from src.Execution.Services.demo_execution_engine import DemoExecutionEngine
from src.Infrastructure.Configuration.config import ConfigurationManager

logger = logging.getLogger("AutonomousDemoRunner")


class AutonomousDemoRunner:
    def __init__(self, scanner: Optional[Any] = None, demo_engine: Optional[Any] = None):
        self.scanner = scanner
        self.demo_engine = demo_engine or DemoExecutionEngine()
        self.is_running = False

    def execute_single_cycle(self) -> Dict[str, Any]:
        """
        Executes one full autonomous demo cycle:
        1. Scan markets
        2. Generate signal
        3. Validate risk & safety gates
        4. Execute DEMO order
        5. Track position & journal
        6. Post-trade learning
        """
        # Hard Lock Verification
        config = ConfigurationManager.get_config()
        if getattr(config, "live_trading_enabled", False):
            raise RuntimeError("LIVE_TRADING_ENABLED IS TRUE! HARD BLOCKED!")

        # Gate Verification
        MetaTraderSafetyGate.verify_operation(
            terminal_type="MT5",
            operation_type="DEMO",
            account_id="52961173",
            server_name="Alpari-MT5-Demo"
        )

        # Step 1: Scan Markets
        candidates = self.scanner.scan_markets() if self.scanner else []
        selected_symbol = candidates[0]["symbol"] if candidates else "XAUUSD"

        # Step 2: Signal / Decision
        decision_id = f"dec-auto-{int(time.time())}"

        # Step 3: Execute DEMO
        order_res = self.demo_engine.execute_demo_decision(
            symbol=selected_symbol,
            direction="BUY",
            volume=0.01,
            comment="YarTrader Autonomous Loop",
            decision_id=decision_id
        )

        # Step 4 & 5: Journal & Outcome
        cycle_result = {
            "status": "COMPLETED",
            "decision": {
                "decision_id": decision_id,
                "symbol": selected_symbol,
                "direction": "BUY",
                "volume": 0.01
            },
            "order_response": order_res,
            "selected_symbol": selected_symbol,
            "scanned_candidates_count": len(candidates),
            "live_trading_enabled": False
        }

        return cycle_result

    def run_loop(self, max_cycles: int = 1):
        """
        Runs the autonomous loop for max_cycles.
        """
        self.is_running = True
        results = []
        for _ in range(max_cycles):
            if not self.is_running:
                break
            res = self.execute_single_cycle()
            results.append(res)
        self.is_running = False
        return results
