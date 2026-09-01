from typing import Dict, Any

class CostModel:
    """
    Cost-adjusted accounting engine for research evaluation.
    Calculates net PnL, deducting spread, $7/lot commission, and slippage.
    """
    def __init__(
        self,
        spread_pips: float = 1.0,
        commission_per_lot: float = 7.0,
        slippage_pips: float = 0.5
    ) -> None:
        self.spread_pips = spread_pips
        self.commission_per_lot = commission_per_lot
        self.slippage_pips = slippage_pips

    def calculate_cost_adjusted_pnl(
        self,
        symbol: str,
        direction: str,
        entry_price: float,
        exit_price: float,
        volume_lots: float
    ) -> Dict[str, float]:
        pip_size = 0.1 if "XAU" in symbol.upper() else 0.0001
        multiplier = 100.0 if "XAU" in symbol.upper() else 10000.0

        # Raw Price Distance PnL
        raw_dist = (exit_price - entry_price) if direction == "BUY" else (entry_price - exit_price)
        gross_pnl = raw_dist * volume_lots * multiplier

        # Transaction Costs
        spread_cost = (self.spread_pips * pip_size) * volume_lots * multiplier
        slippage_cost = (self.slippage_pips * pip_size) * volume_lots * multiplier
        commission_cost = self.commission_per_lot * volume_lots

        total_cost = spread_cost + slippage_cost + commission_cost
        net_pnl = gross_pnl - total_cost

        return {
            "gross_pnl": round(gross_pnl, 2),
            "total_cost": round(total_cost, 2),
            "net_pnl": round(net_pnl, 2),
            "spread_cost": round(spread_cost, 2),
            "commission_cost": round(commission_cost, 2),
            "slippage_cost": round(slippage_cost, 2)
        }
