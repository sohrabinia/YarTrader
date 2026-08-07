import os
from typing import Dict, Any

class VirtualCapitalProvider:
    """
    Provides isolated capital and balance parameters based on the active operating mode.
    Guarantees that real brokerage balances are protected and virtual simulation
    capital of $1000 is used strictly for simulated, shadow, and research modes.
    """
    @classmethod
    def get_available_balance(cls, trading_mode: str = "SHADOW", real_broker_balance: float = 0.0) -> float:
        """
        Returns the appropriate balance based on the active trading mode.
        - LIVE: Uses the real broker account balance.
        - SHADOW / SIMULATION / RESEARCH: Strictly isolated to $1000.0 USD.
        """
        mode_upper = trading_mode.upper()
        if mode_upper == "LIVE":
            # Real Trading mode uses actual MT5 broker capital
            return float(real_broker_balance)

        # All simulation, shadow, and research modes assume virtual capital of $1000.0 USD
        return 1000.0
