import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from src.Research.Brain.models import VirtualTrade, MarketObservation

class SimulationBrain:
    """
    Simulates virtual trading decisions (BUY, SELL, WAIT) under historical replay or live monitoring.
    Connects with simulated physical trading conditions (bid, ask, spread, slippage, commission, execution delay)
    to prevent ideal-price reporting bias.
    Contains no execution linkages, guaranteeing absolute safety and read-only status.
    """
    def __init__(
        self,
        symbol: str,
        timeframe: str,
        spread_points: float = 2.0,
        slippage_points: float = 1.0,
        commission_points: float = 0.5,
        execution_delay_ms: int = 150
    ) -> None:
        self.symbol = symbol
        self.timeframe = timeframe
        self.spread_points = spread_points
        self.slippage_points = slippage_points
        self.commission_points = commission_points
        self.execution_delay_ms = execution_delay_ms

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
        """
        Creates a virtual simulation trade with virtual stop loss and take profit limits,
        incorporating spread, slippage, and commissions at transaction time.
        """
        if action == "WAIT":
            return None

        trade_id = f"vtrade-{uuid.uuid4().hex[:8]}"

        # Apply trading realities to transaction pricing:
        # BUY entry is executed at Ask price (entry_price + half spread) + slippage + commission
        # SELL entry is executed at Bid price (entry_price - half spread) - slippage - commission
        half_spread = self.spread_points / 2.0
        if action == "BUY":
            actual_entry = entry_price + half_spread + self.slippage_points + self.commission_points
            virtual_stop = actual_entry - stop_offset
            virtual_target = actual_entry + target_offset
        elif action == "SELL":
            actual_entry = entry_price - half_spread - self.slippage_points - self.commission_points
            virtual_stop = actual_entry + stop_offset
            virtual_target = actual_entry - target_offset
        else:
            raise ValueError(f"Invalid virtual action: {action}")

        trade = VirtualTrade(
            trade_id=trade_id,
            symbol=self.symbol,
            timeframe=self.timeframe,
            entry_time=timestamp,
            entry_price=actual_entry,
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
        Applies slippage and spread adjustments to exit conditions as well.
        """
        closed_this_cycle: List[VirtualTrade] = []
        still_active: List[VirtualTrade] = []

        price_high = latest_observation.high
        price_low = latest_observation.low
        timestamp = latest_observation.timestamp

        # When updating active trades, we must simulate bid/ask logic:
        # For a BUY trade:
        #   - Stops/Exits are executed on Bid (Market price). Peak high/low represents raw mid,
        #     so Bid low is raw_low - half_spread, Bid high is raw_high - half_spread.
        # For a SELL trade:
        #   - Stops/Exits are executed on Ask (Market price). Ask high is raw_high + half_spread,
        #     Ask low is raw_low + half_spread.
        half_spread = self.spread_points / 2.0

        for trade in self.active_trades:
            if trade.decision_action == "BUY":
                bid_high = price_high - half_spread
                bid_low = price_low - half_spread

                # Calculate excursions against actual entry
                fav_excursion = max(0.0, bid_high - trade.entry_price)
                adv_excursion = min(0.0, bid_low - trade.entry_price)

                trade.max_favorable_movement = max(trade.max_favorable_movement, fav_excursion)
                trade.max_adverse_movement = min(trade.max_adverse_movement, adv_excursion)

                # Check Stop Loss breach (with exit slippage)
                if bid_low <= trade.virtual_stop:
                    trade.status = "CLOSED"
                    trade.exit_time = timestamp
                    trade.exit_price = trade.virtual_stop - self.slippage_points
                    trade.final_result = "FAILURE"
                    trade.reason_of_failure = "Stop loss breach."
                    closed_this_cycle.append(trade)
                # Check Take Profit trigger (with exit slippage)
                elif bid_high >= trade.virtual_target:
                    trade.status = "CLOSED"
                    trade.exit_time = timestamp
                    trade.exit_price = trade.virtual_target - self.slippage_points
                    trade.final_result = "SUCCESS"
                    closed_this_cycle.append(trade)
                else:
                    still_active.append(trade)

            elif trade.decision_action == "SELL":
                ask_high = price_high + half_spread
                ask_low = price_low + half_spread

                # Calculate excursions against actual entry
                fav_excursion = max(0.0, trade.entry_price - ask_low)
                adv_excursion = min(0.0, trade.entry_price - ask_high)

                trade.max_favorable_movement = max(trade.max_favorable_movement, fav_excursion)
                trade.max_adverse_movement = min(trade.max_adverse_movement, adv_excursion)

                # Check Stop Loss breach (with exit slippage)
                if ask_high >= trade.virtual_stop:
                    trade.status = "CLOSED"
                    trade.exit_time = timestamp
                    trade.exit_price = trade.virtual_stop + self.slippage_points
                    trade.final_result = "FAILURE"
                    trade.reason_of_failure = "Stop loss breach."
                    closed_this_cycle.append(trade)
                # Check Take Profit trigger (with exit slippage)
                elif ask_low <= trade.virtual_target:
                    trade.status = "CLOSED"
                    trade.exit_time = timestamp
                    trade.exit_price = trade.virtual_target + self.slippage_points
                    trade.final_result = "SUCCESS"
                    closed_this_cycle.append(trade)
                else:
                    still_active.append(trade)

        self.active_trades = still_active
        self.closed_trades.extend(closed_this_cycle)
        return closed_this_cycle
