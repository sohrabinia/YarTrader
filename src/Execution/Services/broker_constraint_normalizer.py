import logging
from typing import Dict, Any, Tuple

logger = logging.getLogger("BrokerConstraintNormalizer")


class BrokerConstraintNormalizer:
    """
    Centralized service that dynamically normalizes trade parameters (Entry, SL, TP, Volume)
    against MT5 symbol specifications (digits, point, trade_stops_level, trade_freeze_level, volume_min/step/max).
    """

    @staticmethod
    def normalize_trade_parameters(
        symbol: str,
        direction: str,  # "BUY" or "SELL"
        raw_price: float,
        raw_sl: float,
        raw_tp: float,
        raw_volume: float,
        symbol_info: Dict[str, Any]
    ) -> Tuple[float, float, float, float, Dict[str, Any]]:
        """
        Normalizes price, SL, TP, and volume to adhere strictly to broker requirements.
        Returns: (norm_price, norm_sl, norm_tp, norm_volume, constraints_meta)
        """
        def _get_val(obj: Any, key: str, default: Any) -> Any:
            if isinstance(obj, dict):
                return obj.get(key, default)
            return getattr(obj, key, default)

        digits = int(_get_val(symbol_info, "digits", 2))
        point = float(_get_val(symbol_info, "point", 0.01))
        trade_stops_level = float(_get_val(symbol_info, "trade_stops_level", 0))
        trade_freeze_level = float(_get_val(symbol_info, "trade_freeze_level", 0))

        # Minimum stop distance in price terms
        stop_level_pts = max(trade_stops_level, trade_freeze_level)
        min_stop_distance = max(stop_level_pts * point, 10.0 * point if point > 0 else 0.1)

        # 1. Price Normalization
        norm_price = round(raw_price, digits)

        # 2. SL / TP Normalization & Distance Enforcement
        norm_sl = round(raw_sl, digits) if raw_sl and raw_sl > 0 else 0.0
        norm_tp = round(raw_tp, digits) if raw_tp and raw_tp > 0 else 0.0

        dir_upper = direction.upper()
        if dir_upper in ["BUY", "LONG"]:
            if norm_sl > 0:
                if norm_sl >= norm_price or (norm_price - norm_sl) < min_stop_distance:
                    norm_sl = round(norm_price - min_stop_distance, digits)
            if norm_tp > 0:
                if norm_tp <= norm_price or (norm_tp - norm_price) < min_stop_distance:
                    norm_tp = round(norm_price + min_stop_distance, digits)
        elif dir_upper in ["SELL", "SHORT"]:
            if norm_sl > 0:
                if norm_sl <= norm_price or (norm_sl - norm_price) < min_stop_distance:
                    norm_sl = round(norm_price + min_stop_distance, digits)
            if norm_tp > 0:
                if norm_tp >= norm_price or (norm_price - norm_tp) < min_stop_distance:
                    norm_tp = round(norm_price - min_stop_distance, digits)

        # 3. Volume Normalization & Step Alignment
        vol_min = float(_get_val(symbol_info, "volume_min", 0.01))
        vol_step = float(_get_val(symbol_info, "volume_step", 0.01))
        vol_max = float(_get_val(symbol_info, "volume_max", 100.0))

        norm_vol = max(vol_min, min(raw_volume, vol_max))
        if vol_step > 0:
            norm_vol = round(round(norm_vol / vol_step) * vol_step, 4)

        constraints_meta = {
            "symbol": symbol,
            "digits": digits,
            "point": point,
            "min_stop_distance": min_stop_distance,
            "vol_min": vol_min,
            "vol_step": vol_step,
            "vol_max": vol_max,
        }

        logger.info(
            f"[NORMALIZER] {symbol} {dir_upper}: Price={norm_price} (raw={raw_price}), "
            f"SL={norm_sl} (raw={raw_sl}), TP={norm_tp} (raw={raw_tp}), Vol={norm_vol}"
        )

        return norm_price, norm_sl, norm_tp, norm_vol, constraints_meta
