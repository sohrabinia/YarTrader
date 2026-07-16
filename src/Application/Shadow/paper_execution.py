import uuid
from datetime import datetime
from typing import Dict, List, Any


class VirtualOrder:
    """Represents a virtual paper order in the simulated execution environment."""

    def __init__(self, symbol: str, order_type: str, volume: float, price: float) -> None:
        self.order_id = f"VORD-{uuid.uuid4().hex[:8]}"
        self.symbol = symbol
        self.order_type = order_type # "BUY" or "SELL"
        self.volume = volume
        self.price = price
        self.timestamp = datetime.now()


class VirtualPortfolio:
    """Represents a paper-trading virtual capital and holdings tracker."""

    def __init__(self, initial_balance: float = 100000.0) -> None:
        self.balance = initial_balance
        self.holdings: Dict[str, float] = {} # symbol -> volume
        self.avg_entry_prices: Dict[str, float] = {} # symbol -> price

    def record_transaction(self, order: VirtualOrder) -> None:
        cost = order.volume * order.price
        if order.order_type == "BUY":
            if self.balance < cost:
                raise ValueError("Insufficient virtual balance to record buy transaction.")
            self.balance -= cost

            # Recalculate average entry price
            current_vol = self.holdings.get(order.symbol, 0.0)
            current_price = self.avg_entry_prices.get(order.symbol, 0.0)

            new_vol = current_vol + order.volume
            if new_vol > 0:
                self.avg_entry_prices[order.symbol] = ((current_vol * current_price) + cost) / new_vol
            self.holdings[order.symbol] = new_vol

        elif order.order_type == "SELL":
            current_vol = self.holdings.get(order.symbol, 0.0)
            if current_vol < order.volume:
                raise ValueError(f"Insufficient virtual holdings for '{order.symbol}' to execute sell transaction.")

            self.balance += cost
            self.holdings[order.symbol] = current_vol - order.volume
            if self.holdings[order.symbol] <= 0:
                del self.holdings[order.symbol]
                if order.symbol in self.avg_entry_prices:
                    del self.avg_entry_prices[order.symbol]


class TradeJournal:
    """Records chronological simulation transactions logs and reports."""

    def __init__(self) -> None:
        self.journal: List[VirtualOrder] = []

    def log_trade(self, order: VirtualOrder) -> None:
        self.journal.append(order)

    def get_journal(self) -> List[VirtualOrder]:
        return self.journal


class PaperExecutionEngine:
    """
    Paper Trading & Shadow Execution Engine.
    Coordinates virtual portfolio transactions, position tracking, and journals.
    """

    def __init__(self, portfolio: VirtualPortfolio, journal: TradeJournal) -> None:
        self.portfolio = portfolio
        self.journal = journal

    def process_decision_allocation(self, symbol: str, target_weight: float, current_price: float) -> None:
        """
        Translates a target weight allocation into simulated virtual portfolio trades.
        """
        target_cost = self.portfolio.balance * target_weight
        target_volume = target_cost / current_price if current_price > 0 else 0.0

        current_volume = self.portfolio.holdings.get(symbol, 0.0)

        if target_volume > current_volume:
            # Simulated Buy
            vol_to_buy = target_volume - current_volume
            order = VirtualOrder(symbol, "BUY", vol_to_buy, current_price)
            self.portfolio.record_transaction(order)
            self.journal.log_trade(order)
        elif target_volume < current_volume:
            # Simulated Sell
            vol_to_sell = current_volume - target_volume
            order = VirtualOrder(symbol, "SELL", vol_to_sell, current_price)
            self.portfolio.record_transaction(order)
            self.journal.log_trade(order)
