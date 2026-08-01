import math
from typing import List, Dict, Any, Optional

class MarketBehaviorEngine:
    """
    Computes mathematical price action metrics from tick sequences or custom structures.
    Strictly forbidden: RSI, MACD, EMA, SMA, Bollinger Bands, ATR, or any classical indicator.
    """
    def __init__(self) -> None:
        pass

    def calculate_velocity(self, prices: List[float], times: List[float]) -> float:
        """
        Calculates price displacement speed (points per second).
        Velocity = (Price_now - Price_prev) / (Time_now - Time_prev)
        """
        if len(prices) < 2 or len(times) < 2:
            return 0.0

        displacement = prices[-1] - prices[-2]
        time_diff = times[-1] - times[-2]
        if time_diff <= 0.0:
            time_diff = 0.001 # prevent division by zero
        return displacement / time_diff

    def calculate_acceleration(self, velocities: List[float], times: List[float]) -> float:
        """
        Calculates acceleration of price movement (change in velocity per second).
        """
        if len(velocities) < 2 or len(times) < 2:
            return 0.0

        vel_diff = velocities[-1] - velocities[-2]
        time_diff = times[-1] - times[-2]
        if time_diff <= 0.0:
            time_diff = 0.001
        return vel_diff / time_diff

    def calculate_displacement(self, prices: List[float]) -> float:
        """
        Calculates net price change over the sequence.
        """
        if not prices:
            return 0.0
        return prices[-1] - prices[0]

    def is_compression(self, prices: List[float], threshold: float = 0.05) -> bool:
        """
        Detects compression (extremely tight price range).
        """
        if not prices:
            return False
        price_range = max(prices) - min(prices)
        # Compression occurs when max - min is below a threshold
        return price_range <= threshold

    def is_expansion(self, prices: List[float], prev_range: float, multiplier: float = 2.0) -> bool:
        """
        Detects expansion (breakout, range is significantly larger than previous range).
        """
        if not prices or prev_range <= 0:
            return False
        curr_range = max(prices) - min(prices)
        return curr_range >= (prev_range * multiplier)

    def calculate_reaction(self, initial_move: float, pullback_move: float) -> float:
        """
        Calculates reaction magnitude (retracement percentage).
        """
        if abs(initial_move) < 0.00001:
            return 0.0
        return abs(pullback_move / initial_move)

    def calculate_similarity(self, seq1: List[float], seq2: List[float]) -> float:
        """
        Computes cosine similarity between two price footprint vectors of equal length.
        """
        if not seq1 or not seq2 or len(seq1) != len(seq2):
            return 0.0

        dot_product = sum(a * b for a, b in zip(seq1, seq2))
        norm_a = math.sqrt(sum(a * a for a in seq1))
        norm_b = math.sqrt(sum(b * b for b in seq2))

        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
        return dot_product / (norm_a * norm_b)
