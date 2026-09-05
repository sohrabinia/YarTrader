"""
YarTrader Layer 1 — Wavelet Engine
===================================
Multi-scale wavelet decomposition and energy distribution analysis
using Discrete Wavelet Transformation (Haar / multi-resolution filter bank in NumPy).
Zero lookahead; purely causal data access.
"""

import math
import numpy as np
from typing import Dict, Any, List, Optional
from datetime import datetime


class WaveletEngine:
    """
    Computes multi-scale wavelet decomposition energy, dominant scale,
    high-frequency vs low-frequency energy ratios, and reconstruction error.
    """

    def __init__(self, max_levels: int = 4) -> None:
        self.max_levels = max_levels

    def decompose(
        self,
        prices: List[float],
        timeframe: str = "M5",
        timestamp: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Decomposes price series into multi-scale wavelet components using Haar filter bank.
        """
        N = len(prices)
        if N < 8:
            return {
                "energy_per_scale": {"A1": 0.5, "D1": 0.5},
                "dominant_scale": "D1",
                "high_freq_energy": 0.5,
                "low_freq_energy": 0.5,
                "reconstruction_error": 0.0,
                "quality": 0.0,
                "timestamp": timestamp or datetime.now().isoformat(),
                "timeframe": timeframe.upper()
            }

        X = np.array(prices, dtype=np.float64)

        # Truncate to power of 2 for clean multi-resolution decomposition
        levels = min(self.max_levels, int(np.floor(np.log2(N))))
        if levels < 1:
            levels = 1

        power_len = 2**levels
        signal = X[-power_len:]

        # Perform 1D Haar Wavelet Decomposition
        current = signal.copy()
        details = []
        approx = None

        for lvl in range(levels):
            n_curr = len(current)
            if n_curr < 2:
                break
            # Haar low-pass (approximation) and high-pass (detail)
            a = (current[0::2] + current[1::2]) / np.sqrt(2.0)
            d = (current[0::2] - current[1::2]) / np.sqrt(2.0)
            details.append(d)
            current = a

        approx = current

        # Calculate energy at each scale
        energy_per_scale = {}
        total_energy = np.sum(approx**2)
        energy_per_scale[f"A{levels}"] = float(np.sum(approx**2))

        high_freq_e = 0.0
        low_freq_e = float(np.sum(approx**2))

        for idx, d in enumerate(details):
            scale_name = f"D{idx + 1}"
            e_val = float(np.sum(d**2))
            energy_per_scale[scale_name] = e_val
            total_energy += e_val
            if idx == 0:  # Highest frequency scale D1
                high_freq_e += e_val

        # Normalize energies
        if total_energy > 0:
            norm_energy = {k: round(v / total_energy, 4) for k, v in energy_per_scale.items()}
            norm_high = round(high_freq_e / total_energy, 4)
            norm_low = round(low_freq_e / total_energy, 4)
        else:
            norm_energy = {k: 0.0 for k in energy_per_scale}
            norm_high = 0.5
            norm_low = 0.5

        # Find dominant scale
        dominant_scale = max(norm_energy, key=norm_energy.get) if norm_energy else "D1"

        # Quality metric based on signal length suitability
        quality = max(0.0, min(1.0, round(power_len / float(N), 4)))

        return {
            "energy_per_scale": norm_energy,
            "dominant_scale": dominant_scale,
            "high_freq_energy": norm_high,
            "low_freq_energy": norm_low,
            "reconstruction_error": 0.0,  # Exact orthogonal transformation
            "quality": quality,
            "timestamp": timestamp or datetime.now().isoformat(),
            "timeframe": timeframe.upper()
        }
