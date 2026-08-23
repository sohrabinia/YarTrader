import logging
from typing import Tuple, Dict, Any
from src.Execution.Services.broker_constraint_normalizer import BrokerConstraintNormalizer

logger = logging.getLogger("RiskPriceValidator")


class RiskPriceValidator:
    """
    Validates directional pricing logic and stop-level requirements prior to order execution.
    Ensures BUY (SL < Entry < TP) and SELL (TP < Entry < SL) structure while preserving R:R.
    """

    @staticmethod
    def validate_and_normalize(
        symbol: str,
        direction: str,
        entry_price: float,
        stop_loss: float,
        take_profit: float,
        volume: float,
        symbol_info: Dict[str, Any]
    ) -> Tuple[bool, str, float, float, float, float, Dict[str, Any]]:
        """
        Validates directional structure and normalizes order parameters.
        Returns: (is_valid, reason, norm_price, norm_sl, norm_tp, norm_vol, meta)
        """
        dir_upper = direction.upper()

        if entry_price <= 0:
            return False, "Invalid entry price <= 0", entry_price, stop_loss, take_profit, volume, {}

        # Normalize via BrokerConstraintNormalizer
        norm_price, norm_sl, norm_tp, norm_vol, meta = BrokerConstraintNormalizer.normalize_trade_parameters(
            symbol=symbol,
            direction=dir_upper,
            raw_price=entry_price,
            raw_sl=stop_loss,
            raw_tp=take_profit,
            raw_volume=volume,
            symbol_info=symbol_info
        )

        # Validate Directional Alignment
        if dir_upper in ["BUY", "LONG"]:
            if norm_sl > 0 and norm_sl >= norm_price:
                return False, f"BUY StopLoss ({norm_sl}) must be strictly less than Entry ({norm_price})", norm_price, norm_sl, norm_tp, norm_vol, meta
            if norm_tp > 0 and norm_tp <= norm_price:
                return False, f"BUY TakeProfit ({norm_tp}) must be strictly greater than Entry ({norm_price})", norm_price, norm_sl, norm_tp, norm_vol, meta
        elif dir_upper in ["SELL", "SHORT"]:
            if norm_sl > 0 and norm_sl <= norm_price:
                return False, f"SELL StopLoss ({norm_sl}) must be strictly greater than Entry ({norm_price})", norm_price, norm_sl, norm_tp, norm_vol, meta
            if norm_tp > 0 and norm_tp >= norm_price:
                return False, f"SELL TakeProfit ({norm_tp}) must be strictly less than Entry ({norm_price})", norm_price, norm_sl, norm_tp, norm_vol, meta
        else:
            return False, f"Unsupported direction '{direction}'", norm_price, norm_sl, norm_tp, norm_vol, meta

        logger.info(f"[RISK_VALIDATOR] {symbol} {dir_upper} price validation PASSED.")
        return True, "VALIDATED", norm_price, norm_sl, norm_tp, norm_vol, meta
