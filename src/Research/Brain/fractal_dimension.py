"""
YarTrader Layer 1 — Higuchi Fractal Dimension Engine
=====================================================
Calculates Higuchi Fractal Dimension (D) for time series analysis.
Zero lookahead; purely causal data access.

D near 1.0: Smooth, highly trend-like series
D near 1.5: Random walk Brownian motion
D near 2.0: High complexity, noisy / mean-reverting space-filling series
"""

import math
import numpy as np
from typing import Dict, Any, List, Optional
from datetime import datetime


class HiguchiFractalDimension:
    """
    Computes Higuchi Fractal Dimension D over price series.
    """

    def __init__(self, k_max: int = 10) -> None:
        self.k_max = k_max

    def calculate_dimension(
        self,
        prices: List[float],
        timeframe: str = "M5",
        timestamp: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Calculates the Higuchi fractal dimension D for a given price series.
        """
        N = len(prices)
        if N < 20:
            return {
                "D": 1.5,
                "estimator": "Higuchi",
                "quality": 0.0,
                "timestamp": timestamp or datetime.now().isoformat(),
                "timeframe": timeframe.upper()
            }

        X = np.array(prices, dtype=np.float64)
        if np.any(np.isnan(X)) or np.any(np.isinf(X)):
            return {
                "D": 1.5,
                "estimator": "Higuchi",
                "quality": 0.0,
                "timestamp": timestamp or datetime.now().isoformat(),
                "timeframe": timeframe.upper()
            }

        k_max = min(self.k_max, N // 4)
        if k_max < 2:
            return {
                "D": 1.5,
                "estimator": "Higuchi",
                "quality": 0.2,
                "timestamp": timestamp or datetime.now().isoformat(),
                "timeframe": timeframe.upper()
            }

        L_k = []
        x_vals = []

        for k in range(1, k_max + 1):
            L_m_k = []
            for m in range(1, k + 1):
                # Subseries for m and k
                idx = np.arange(m - 1, N, k)
                if len(idx) < 2:
                    continue
                sub_X = X[idx]
                norm_factor = (N - 1) / (len(sub_X) * k)
                length = np.sum(np.abs(np.diff(sub_X))) * norm_factor / k
                if length > 0:
                    L_m_k.append(length)

            if L_m_k:
                L_k.append(np.mean(L_m_k))
                x_vals.append(k)

        if len(L_k) < 2:
            return {
                "D": 1.5,
                "estimator": "Higuchi",
                "quality": 0.2,
                "timestamp": timestamp or datetime.now().isoformat(),
                "timeframe": timeframe.upper()
            }

        # Linear fit of ln(L(k)) vs ln(1/k)
        log_k_inv = np.log(1.0 / np.array(x_vals, dtype=np.float64))
        log_L = np.log(np.array(L_k, dtype=np.float64))

        poly = np.polyfit(log_k_inv, log_L, 1)
        D_raw = float(poly[0])

        # Higuchi D is bounded between 1.0 and 2.0
        D = max(1.0, min(2.0, round(D_raw, 4)))

        # Quality metric from R2
        residuals = log_L - (poly[0] * log_k_inv + poly[1])
        ss_res = np.sum(residuals**2)
        ss_tot = np.sum((log_L - np.mean(log_L))**2)
        r2 = float(1.0 - (ss_res / ss_tot)) if ss_tot > 0 else 0.5
        quality = max(0.0, min(1.0, round(r2, 4)))

        return {
            "D": D,
            "estimator": "Higuchi",
            "quality": quality,
            "timestamp": timestamp or datetime.now().isoformat(),
            "timeframe": timeframe.upper()
        }
