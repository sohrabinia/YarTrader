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
        symbol_upper = symbol.upper()
        if "XAU" in symbol_upper or "GOLD" in symbol_upper:
            pip_size, multiplier = 0.1, 100.0
        elif "XAG" in symbol_upper or "SILVER" in symbol_upper:
            pip_size, multiplier = 0.01, 5000.0
        elif "JPY" in symbol_upper:
            # JPY pairs quote PnL in JPY; convert approximately to USD at exit.
            pip_size, multiplier = 0.01, 100000.0 / max(abs(float(exit_price)), 1e-9)
        elif any(token in symbol_upper for token in (
            "BTC", "ETH", "SOL", "BNB", "XRP", "ADA", "DOGE", "AVAX",
            "DOT", "LINK", "LTC", "BCH", "NEAR", "UNI", "ATOM",
        )):
            # Research convention: one price unit per lot for listed crypto symbols.
            pip_size, multiplier = 1.0, 1.0
        else:
            # Standard FX contract: 100,000 base-currency units per standard lot.
            pip_size, multiplier = 0.0001, 100000.0

        # Crypto uses the same 10 bps combined execution-friction convention as
        # BacktestAndLearningEngine, rather than FX pip/lot accounting.
        crypto_symbols = (
            "BTC", "ETH", "SOL", "BNB", "XRP", "ADA", "DOGE", "AVAX",
            "DOT", "LINK", "LTC", "BCH", "NEAR", "UNI", "ATOM",
        )
        raw_dist = (exit_price - entry_price) if direction.upper() == "BUY" else (entry_price - exit_price)
        if any(token in symbol_upper for token in crypto_symbols):
            gross_pnl = raw_dist * volume_lots
            combined_cost = abs(float(exit_price)) * volume_lots * 0.0010
            return {
                "gross_pnl": round(gross_pnl, 2),
                "total_cost": round(combined_cost, 2),
                "net_pnl": round(gross_pnl - combined_cost, 2),
                "spread_cost": round(combined_cost, 2),
                "commission_cost": 0.0,
                "slippage_cost": 0.0,
            }

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
