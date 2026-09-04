"""
YarTrader Layer 1 — Hurst Engine
=================================
Calculates rolling Hurst exponent (H) for market persistence and regime analysis
using Rescaled Range (R/S) analysis. Zero lookahead; purely causal data access.

H > 0.5: Persistent / Trending regime
H = 0.5: Random Walk / Brownian motion
H < 0.5: Anti-persistent / Mean-reverting regime
"""

import math
import numpy as np
from typing import Dict, Any, List, Optional
from datetime import datetime


class HurstEngine:
    """
    Computes rolling Hurst exponent H over price/return series using R/S analysis.
    """

    def __init__(self, default_window: int = 100, min_chunk: int = 8) -> None:
        self.default_window = default_window
        self.min_chunk = min_chunk

    def calculate_hurst(
        self,
        prices: List[float],
        timeframe: str = "M5",
        timestamp: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Calculates the Hurst exponent for a given price series.
        """
        sample_count = len(prices)
        if sample_count < 20:
            return {
                "H": 0.5,
                "estimator": "Rescaled Range R/S",
                "window": sample_count,
                "sample_count": sample_count,
                "quality": 0.0,
                "regime": "INSUFFICIENT_DATA",
                "timestamp": timestamp or datetime.now().isoformat(),
                "timeframe": timeframe.upper()
            }

        # Calculate logarithmic returns
        p = np.array(prices, dtype=np.float64)
        if np.any(p <= 0):
            return {
                "H": 0.5,
                "estimator": "Rescaled Range R/S",
                "window": sample_count,
                "sample_count": sample_count,
                "quality": 0.0,
                "regime": "INVALID_PRICES",
                "timestamp": timestamp or datetime.now().isoformat(),
                "timeframe": timeframe.upper()
            }

        returns = np.diff(np.log(p))
        N = len(returns)

        # Generate sub-window sizes (lags)
        max_lag = N // 2
        min_lag = self.min_chunk
        if max_lag <= min_lag:
            lags = [min_lag]
        else:
            lags = np.unique(np.logspace(np.log10(min_lag), np.log10(max_lag), num=8, dtype=int))

        rs_values = []
        valid_lags = []

        for lag in lags:
            if lag < 4 or lag > N:
                continue
            num_chunks = N // lag
            if num_chunks < 1:
                continue

            chunk_rs = []
            for i in range(num_chunks):
                chunk = returns[i * lag : (i + 1) * lag]
                mean_adj = chunk - np.mean(chunk)
                cum_sum = np.cumsum(mean_adj)
                R = np.max(cum_sum) - np.min(cum_sum)
                S = np.std(chunk, ddof=1)
                if S > 1e-12:
                    chunk_rs.append(R / S)

            if chunk_rs:
                rs_values.append(np.mean(chunk_rs))
                valid_lags.append(lag)

        if len(valid_lags) < 2:
            return {
                "H": 0.5,
                "estimator": "Rescaled Range R/S",
                "window": N,
                "sample_count": sample_count,
                "quality": 0.3,
                "regime": "RANDOM_WALK",
                "timestamp": timestamp or datetime.now().isoformat(),
                "timeframe": timeframe.upper()
            }

        # Linear regression log(R/S) vs log(lag)
        log_lags = np.log(valid_lags)
        log_rs = np.log(rs_values)

        poly = np.polyfit(log_lags, log_rs, 1)
        H_raw = float(poly[0])

        # Clamp H between 0.01 and 0.99
        H = max(0.01, min(0.99, round(H_raw, 4)))

        # Quality metric based on linear fit R-squared
        residuals = log_rs - (poly[0] * log_lags + poly[1])
        ss_res = np.sum(residuals**2)
        ss_tot = np.sum((log_rs - np.mean(log_rs))**2)
        r_squared = float(1.0 - (ss_res / ss_tot)) if ss_tot > 0 else 0.5
        quality = max(0.0, min(1.0, round(r_squared, 4)))

        if H > 0.55:
            regime = "PERSISTENT_TRENDING"
        elif H < 0.45:
            regime = "ANTI_PERSISTENT_MEAN_REVERTING"
        else:
            regime = "RANDOM_WALK"

        return {
            "H": H,
            "estimator": "Rescaled Range R/S",
            "window": N,
            "sample_count": sample_count,
            "quality": quality,
            "regime": regime,
            "timestamp": timestamp or datetime.now().isoformat(),
            "timeframe": timeframe.upper()
        }
