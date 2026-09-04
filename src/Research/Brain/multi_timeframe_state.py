"""
YarTrader Layer 2 — Multi-Timeframe Fractal Market State Builder
===============================================================
Constructs unified canonical FractalMarketState across H4, H1, M15, M5 horizons.
Provides explicit Pullback vs Reversal Classification:
- CONTINUATION
- PULLBACK
- REVERSAL
- RANGE
- NO_TRADE

Guarantees that a normal pullback in a strong higher-timeframe trend is NOT misclassified as a reversal.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class FractalMarketState:
    symbol: str
    timestamp: str
    primary_timeframe: str
    regime_state: str  # CONTINUATION, PULLBACK, REVERSAL, RANGE, NO_TRADE
    h4_regime: str
    h1_regime: str
    m15_regime: str
    m5_regime: str
    hurst_h: float
    fractal_dimension_d: float
    wavelet_dominant_scale: str
    wavelet_high_freq_ratio: float
    atr: float
    containment_status: str
    target_consensus: Dict[str, Any]
    quality_score: float
    meta: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class MultiTimeframeStateBuilder:
    """
    Builds canonical Multi-Timeframe FractalMarketState and performs explicit
    Pullback vs Reversal classification.
    """

    @staticmethod
    def classify_regime_state(
        h4_analysis: Dict[str, Any],
        h1_analysis: Dict[str, Any],
        m15_analysis: Dict[str, Any],
        m5_analysis: Dict[str, Any]
    ) -> str:
        """
        Classifies regime into CONTINUATION, PULLBACK, REVERSAL, RANGE, or NO_TRADE.
        """
        if not m5_analysis or not h1_analysis:
            return "NO_TRADE"

        m5_hurst = m5_analysis.get("hurst_analysis", {}) or {}
        h1_hurst = h1_analysis.get("hurst_analysis", {}) or {}

        m5_h = m5_hurst.get("H", 0.5)
        h1_h = h1_hurst.get("H", 0.5)

        # Higher-Timeframe Trend Direction
        h1_regime = h1_hurst.get("regime", "RANDOM_WALK")
        m5_regime = m5_hurst.get("regime", "RANDOM_WALK")

        # Range & Regime evaluation via RangeRegimeEngine integration
        from src.Research.Brain.range_regime_engine import RangeRegimeEngine
        range_engine = RangeRegimeEngine()
        candles = m5_analysis.get("candles", [])
        if candles:
            r_res = range_engine.evaluate_regime(
                candles=candles,
                hurst_val=m5_h,
                htf_bias=h1_hurst.get("regime")
            )
            if r_res.regime in ["RANGE", "PULLBACK", "REVERSAL", "TRANSITION"]:
                return r_res.regime

        # Range fallback detection: low persistence on both MTF and LTF
        if m5_h >= 0.45 and m5_h <= 0.55 and h1_h >= 0.45 and h1_h <= 0.55:
            return "RANGE"

        # Check structural swings for CHoCH / BOS
        m5_choch = m5_analysis.get("choch_detected", False)
        m15_structure_break = m15_analysis.get("structure_break", False)

        # Check if LTF is pulling back against persistent HTF trend
        # Pullback condition: HTF is persistent trending (H1 H > 0.55), but LTF temporary momentum is counter
        if h1_h > 0.55 and not m15_structure_break:
            if m5_choch or m5_h < 0.45:
                # LTF is in pullback, but HTF trend is intact -> PULLBACK (DO NOT REVERSE)
                return "PULLBACK"
            else:
                return "CONTINUATION"

        # Reversal condition: Loss of persistence across HTF + M15 structure break + M5 CHoCH
        if m15_structure_break and m5_choch and h1_h <= 0.50:
            return "REVERSAL"

        if h1_h > 0.55 and m5_h > 0.55:
            return "CONTINUATION"

        return "NO_TRADE"

    def build_state(
        self,
        symbol: str,
        primary_timeframe: str,
        tf_fractal_reports: Dict[str, Dict[str, Any]],
        mtf_consensus: Dict[str, Any]
    ) -> FractalMarketState:
        """
        Builds the canonical FractalMarketState.
        """
        p_tf = primary_timeframe.upper()
        p_report = tf_fractal_reports.get(p_tf) or tf_fractal_reports.get("M5") or {}

        h4_rep = tf_fractal_reports.get("H4", {})
        h1_rep = tf_fractal_reports.get("H1", {})
        m15_rep = tf_fractal_reports.get("M15", {})
        m5_rep = tf_fractal_reports.get("M5", p_report)

        classified_regime = self.classify_regime_state(h4_rep, h1_rep, m15_rep, m5_rep)

        hurst_data = p_report.get("hurst_analysis") or {}
        fd_data = p_report.get("fractal_dimension_analysis") or {}
        wavelet_data = p_report.get("wavelet_analysis") or {}

        h_val = float(hurst_data.get("H", 0.5)) if isinstance(hurst_data, dict) else 0.5
        d_val = float(fd_data.get("D", 1.5)) if isinstance(fd_data, dict) else 1.5

        dom_scale = wavelet_data.get("dominant_scale", "D1") if isinstance(wavelet_data, dict) else "D1"
        hf_ratio = float(wavelet_data.get("high_freq_energy", 0.5)) if isinstance(wavelet_data, dict) else 0.5

        atr_val = float(p_report.get("atr", 0.0))
        latest_ts = p_report.get("timestamp") or datetime.now().isoformat()

        quality = float(p_report.get("hurst_analysis", {}).get("quality", 0.5) if isinstance(p_report.get("hurst_analysis"), dict) else 0.5)

        return FractalMarketState(
            symbol=symbol.upper(),
            timestamp=latest_ts,
            primary_timeframe=p_tf,
            regime_state=classified_regime,
            h4_regime=str(h4_rep.get("hurst_analysis", {}).get("regime", "UNKNOWN") if isinstance(h4_rep.get("hurst_analysis"), dict) else "UNKNOWN"),
            h1_regime=str(h1_rep.get("hurst_analysis", {}).get("regime", "UNKNOWN") if isinstance(h1_rep.get("hurst_analysis"), dict) else "UNKNOWN"),
            m15_regime=str(m15_rep.get("hurst_analysis", {}).get("regime", "UNKNOWN") if isinstance(m15_rep.get("hurst_analysis"), dict) else "UNKNOWN"),
            m5_regime=str(m5_rep.get("hurst_analysis", {}).get("regime", "UNKNOWN") if isinstance(m5_rep.get("hurst_analysis"), dict) else "UNKNOWN"),
            hurst_h=h_val,
            fractal_dimension_d=d_val,
            wavelet_dominant_scale=dom_scale,
            wavelet_high_freq_ratio=hf_ratio,
            atr=atr_val,
            containment_status=str(p_report.get("evidence_state", "NO_EVIDENCE")),
            target_consensus=mtf_consensus,
            quality_score=quality,
            meta={"Source": "MultiTimeframeStateBuilder"}
        )
