import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from src.Research.Brain.models import VirtualTrade, MarketObservation

class SimulationBrain:
    """
    Simulates virtual trading decisions (BUY, SELL, WAIT) under historical replay or live monitoring.
    Contains no execution linkages, guaranteeing absolute safety and read-only status.
    """
    def __init__(self, symbol: str, timeframe: str) -> None:
        self.symbol = symbol
        self.timeframe = timeframe
        self.active_trades: List[VirtualTrade] = []
        self.closed_trades: List[VirtualTrade] = []

    def make_virtual_decision(
        self,
        action: str,  # BUY, SELL, WAIT
        entry_price: float,
        timestamp: datetime,
        stop_offset: float = 20.0,
        target_offset: float = 40.0,
        expected_scenario: str = "Continuation"
    ) -> Optional[VirtualTrade]:
        """Creates a virtual simulation trade with virtual stop loss and take profit limits."""
        if action == "WAIT":
            return None

        trade_id = f"vtrade-{uuid.uuid4().hex[:8]}"

        if action == "BUY":
            virtual_stop = entry_price - stop_offset
            virtual_target = entry_price + target_offset
        elif action == "SELL":
            virtual_stop = entry_price + stop_offset
            virtual_target = entry_price - target_offset
        else:
            raise ValueError(f"Invalid virtual action: {action}")

        trade = VirtualTrade(
            trade_id=trade_id,
            symbol=self.symbol,
            timeframe=self.timeframe,
            entry_time=timestamp,
            entry_price=entry_price,
            decision_action=action,
            virtual_stop=virtual_stop,
            virtual_target=virtual_target,
            expected_scenario=expected_scenario,
            status="OPEN"
        )
        self.active_trades.append(trade)
        return trade

    def update_active_trades(self, latest_observation: MarketObservation) -> List[VirtualTrade]:
        """
        Updates open virtual trades with the latest price high/low.
        Records maximum favorable and adverse price excursions to evaluate quality.
        """
        closed_this_cycle: List[VirtualTrade] = []
        still_active: List[VirtualTrade] = []

        price_high = latest_observation.high
        price_low = latest_observation.low
        close_price = latest_observation.close_price
        timestamp = latest_observation.timestamp

        for trade in self.active_trades:
            # Calculate excursions
            if trade.decision_action == "BUY":
                # Max potential gain: peak price high minus entry
                fav_excursion = max(0.0, price_high - trade.entry_price)
                # Max potential loss: deepest price low minus entry (adverse is negative change)
                adv_excursion = min(0.0, price_low - trade.entry_price)

                trade.max_favorable_movement = max(trade.max_favorable_movement, fav_excursion)
                trade.max_adverse_movement = min(trade.max_adverse_movement, adv_excursion)

                # Check Stop Loss
                if price_low <= trade.virtual_stop:
                    trade.status = "CLOSED"
                    trade.exit_time = timestamp
                    trade.exit_price = trade.virtual_stop
                    trade.final_result = "FAILURE"
                    trade.reason_of_failure = "Stop loss breach."
                    closed_this_cycle.append(trade)
                # Check Take Profit
                elif price_high >= trade.virtual_target:
                    trade.status = "CLOSED"
                    trade.exit_time = timestamp
                    trade.exit_price = trade.virtual_target
                    trade.final_result = "SUCCESS"
                    closed_this_cycle.append(trade)
                else:
                    still_active.append(trade)

            elif trade.decision_action == "SELL":
                # Max potential gain: entry minus deepest price low
                fav_excursion = max(0.0, trade.entry_price - price_low)
                # Max potential loss: entry minus peak price high (adverse is negative)
                adv_excursion = min(0.0, trade.entry_price - price_high)

                trade.max_favorable_movement = max(trade.max_favorable_movement, fav_excursion)
                trade.max_adverse_movement = min(trade.max_adverse_movement, adv_excursion)

                # Check Stop Loss
                if price_high >= trade.virtual_stop:
                    trade.status = "CLOSED"
                    trade.exit_time = timestamp
                    trade.exit_price = trade.virtual_stop
                    trade.final_result = "FAILURE"
                    trade.reason_of_failure = "Stop loss breach."
                    closed_this_cycle.append(trade)
                # Check Take Profit
                elif price_low <= trade.virtual_target:
                    trade.status = "CLOSED"
                    trade.exit_time = timestamp
                    trade.exit_price = trade.virtual_target
                    trade.final_result = "SUCCESS"
                    closed_this_cycle.append(trade)
                else:
                    still_active.append(trade)

        self.active_trades = still_active
        self.closed_trades.extend(closed_this_cycle)
        return closed_this_cycle
