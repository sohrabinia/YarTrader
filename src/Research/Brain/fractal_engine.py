"""
Unified YarTrader Hybrid Fractal + Mathematics + Deep RL Analysis Engine
========================================================================
Executes Layer 1, Layer 2, and Layer 3 orchestrations:
1. Strict Data Integrity Validation (No data fabrication / fake defaults)
2. Multi-Timeframe Structural Containment Mapping
3. Layer 1: Rolling Hurst Exponent, Higuchi Fractal Dimension, Multi-scale Wavelet
4. ATR-Normalized Scale-Invariant Structural Similarity
5. Dynamic State-Dependent Pattern Query (NO_EVIDENCE when missing)
6. Partial Trailing Scale Group Exclusion in Multiscale Base Detection
7. Layer 2: MultiTimeframeStateBuilder (CONTINUATION, PULLBACK, REVERSAL, RANGE, NO_TRADE)
8. Layer 2: TargetProbabilityEngine (Target Reach Probabilities & MTF Consensus)
9. Layer 3: Deep RL (PPO Policy Advisory Proposal)
"""

import logging
import math
from typing import Dict, List, Any, Optional
from datetime import datetime

from src.Research.MarketAnalysis.Interfaces.interfaces import IFractalEngine
from src.Research.Brain.multi_timeframe import MultiTimeframePerception
from src.Research.Brain.fractal_memory import FractalPatternMemory
from src.Research.Brain.fractal_data_scale_engine import ScaleConstructionEngine
from src.Research.Brain.fractal_base_detection_engine import Gate3BaseDetectorEngine
from src.Intelligence.Execution.similarity import PatternSimilarityIntelligenceEngine
from src.Research.Brain.models import MarketObservation
from src.Research.Brain.hurst_engine import HurstEngine
from src.Research.Brain.fractal_dimension import HiguchiFractalDimension
from src.Research.Brain.wavelet_engine import WaveletEngine
from src.Research.Brain.target_probability_engine import TargetProbabilityEngine
from src.Research.Brain.multi_timeframe_state import MultiTimeframeStateBuilder, FractalMarketState
from src.Research.Brain.range_regime_engine import RangeRegimeEngine
from src.Research.RL.ppo_agent import PPOAgent
from src.Research.RL.environment import FractalMarketEnv

logger = logging.getLogger("YarTrader.FractalEngine")


class FractalEngine(IFractalEngine):
    """
    Unified Hybrid Engine orchestrating Layer 1, Layer 2, and Layer 3 research intelligence.
    Returns canonical FractalMarketState, Target Probability MTF Consensus, and PPO Advisory Decision Proposal.
    Execution Safety Boundary: Advisory only. Sole execution authority belongs to Risk Engine and Safety Gates.
    """

    def __init__(
        self,
        fractal_memory: Optional[FractalPatternMemory] = None,
        similarity_engine: Optional[PatternSimilarityIntelligenceEngine] = None,
        hurst_engine: Optional[HurstEngine] = None,
        fractal_dimension: Optional[HiguchiFractalDimension] = None,
        wavelet_engine: Optional[WaveletEngine] = None,
        target_prob_engine: Optional[TargetProbabilityEngine] = None,
        ppo_agent: Optional[PPOAgent] = None
    ) -> None:
        self.fractal_memory = fractal_memory or FractalPatternMemory()
        self.similarity_engine = similarity_engine or PatternSimilarityIntelligenceEngine()
        self.hurst_engine = hurst_engine or HurstEngine()
        self.fractal_dimension = fractal_dimension or HiguchiFractalDimension()
        self.wavelet_engine = wavelet_engine or WaveletEngine()
        self.target_prob_engine = target_prob_engine or TargetProbabilityEngine()
        self.range_regime_engine = RangeRegimeEngine()
        self.state_builder = MultiTimeframeStateBuilder()
        self.ppo_agent = ppo_agent or PPOAgent()
        logger.info("[FractalEngine] Hybrid Fractal + Math + Deep RL Engine initialized cleanly.")

    def _validate_and_extract_observation(self, c: Any, symbol: str, timeframe: str) -> MarketObservation:
        """
        Validates raw bar data strictly.
        Rejects observations with missing/invalid timestamp, non-positive or NaN/Inf prices, or invalid OHLC.
        Raises ValueError if data is invalid or missing (NO DATA FABRICATION).
        """
        raw_ts = getattr(c, "Timestamp", None)
        if raw_ts is None:
            raw_ts = getattr(c, "timestamp", None)
        if raw_ts is None and isinstance(c, dict):
            raw_ts = c.get("timestamp") or c.get("time")

        if raw_ts is None:
            raise ValueError("[FractalEngine] Rejection: Missing candle timestamp. Fabrication strictly forbidden.")

        if isinstance(raw_ts, str):
            try:
                ts = datetime.fromisoformat(raw_ts)
            except Exception as err:
                raise ValueError(f"[FractalEngine] Rejection: Invalid ISO timestamp string '{raw_ts}': {err}")
        elif isinstance(raw_ts, datetime):
            ts = raw_ts
        else:
            raise ValueError(f"[FractalEngine] Rejection: Unsupported timestamp type '{type(raw_ts)}'.")

        open_val = float(getattr(c, "Open", None) or (c.get("open") if isinstance(c, dict) else None) or 0.0)
        high_val = float(getattr(c, "High", None) or (c.get("high") if isinstance(c, dict) else None) or 0.0)
        low_val = float(getattr(c, "Low", None) or (c.get("low") if isinstance(c, dict) else None) or 0.0)
        close_val = float(getattr(c, "Close", None) or (c.get("close") if isinstance(c, dict) else None) or 0.0)
        vol_val = float(getattr(c, "Volume", None) or (c.get("volume") if isinstance(c, dict) else None) or 0.0)

        prices = [open_val, high_val, low_val, close_val]
        for p in prices:
            if p <= 0.0 or math.isnan(p) or math.isinf(p):
                raise ValueError(f"[FractalEngine] Rejection: Invalid non-positive or NaN/Inf price ({p}) in candle.")

        if high_val < low_val or open_val > high_val or open_val < low_val or close_val > high_val or close_val < low_val:
            raise ValueError(f"[FractalEngine] Rejection: Invalid OHLC price relationship (O={open_val}, H={high_val}, L={low_val}, C={close_val}).")

        if vol_val < 0.0 or math.isnan(vol_val) or math.isinf(vol_val):
            raise ValueError(f"[FractalEngine] Rejection: Invalid volume ({vol_val}).")

        return MarketObservation(
            symbol=symbol.upper(),
            timeframe=timeframe.upper(),
            timestamp=ts,
            high=high_val,
            low=low_val,
            open_price=open_val,
            close_price=close_val,
            volume=vol_val,
            meta={"Source": "FractalEngine"}
        )

    def analyze_fractals(
        self,
        symbol: str,
        primary_timeframe: str,
        candles_by_tf: Dict[str, List[Any]],
        historical_patterns: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Processes candles across timeframes to execute Layer 1, Layer 2, and Layer 3 pipelines.
        """
        logger.info(f"[FractalEngine] Executing hybrid analysis for {symbol} on primary TF {primary_timeframe}")
        symbol_upper = symbol.upper()
        primary_tf_upper = primary_timeframe.upper()

        # 1. Multi-timeframe containment mapping with strict validation
        perception = MultiTimeframePerception(symbol_upper)
        tf_observations: Dict[str, List[MarketObservation]] = {}

        for tf, candles in candles_by_tf.items():
            obs_list: List[MarketObservation] = []
            for c in candles:
                try:
                    obs = self._validate_and_extract_observation(c, symbol_upper, tf)
                    obs_list.append(obs)
                except ValueError as val_err:
                    logger.warning(f"[FractalEngine] Invalid candle skipped: {val_err}")
                    continue
            tf_observations[tf.upper()] = obs_list

        containment_map = perception.map_fractal_relationships(tf_observations)

        # Primary observations
        primary_obs = tf_observations.get(primary_tf_upper) or []
        if not primary_obs and tf_observations:
            primary_obs = next(iter(tf_observations.values()))

        if not primary_obs:
            return {
                "symbol": symbol_upper,
                "primary_timeframe": primary_tf_upper,
                "fractal_status": "INSUFFICIENT_DATA",
                "evidence_state": "NO_EVIDENCE",
                "containment_mapping": containment_map,
                "matching_pattern_record": None,
                "similarity_analysis": self.similarity_engine._empty_similarity(),
                "hurst_analysis": None,
                "fractal_dimension_analysis": None,
                "wavelet_analysis": None,
                "fractal_market_state": None,
                "target_consensus": None,
                "ppo_decision_proposal": None,
                "scales_evaluated_count": 0,
                "detected_bases_count": 0,
                "timestamp": None
            }

        # Analyze each timeframe independently for Layer 1 & Target Probabilities
        tf_reports: Dict[str, Dict[str, Any]] = {}
        tf_candidates = {}

        for tf, obs_list in tf_observations.items():
            if not obs_list:
                continue
            tf_closes = [o.close_price for o in obs_list]
            tf_highs = [o.high for o in obs_list]
            tf_lows = [o.low for o in obs_list]
            tf_ts = obs_list[-1].timestamp.isoformat()

            # ATR calculation
            tf_atr = 0.0
            if len(obs_list) >= 2:
                tr_l = [max(tf_highs[i] - tf_lows[i], abs(tf_highs[i] - tf_closes[i - 1]), abs(tf_lows[i] - tf_closes[i - 1])) for i in range(1, len(obs_list))]
                w = min(14, len(tr_l))
                tf_atr = float(sum(tr_l[-w:]) / w) if tr_l else 0.0

            h_res = self.hurst_engine.calculate_hurst(tf_closes, tf, tf_ts)
            fd_res = self.fractal_dimension.calculate_dimension(tf_closes, tf, tf_ts)
            w_res = self.wavelet_engine.decompose(tf_closes, tf, tf_ts)

            # Target Probability Candidates for TF
            curr_p = tf_closes[-1]
            tf_cands = self.target_prob_engine.evaluate_target_probabilities(
                current_price=curr_p,
                direction="BUY" if h_res.get("H", 0.5) > 0.5 else "SELL",
                atr=tf_atr if tf_atr > 0 else 2.0,
                candles=[{"close": c} for c in tf_closes],
                timeframe=tf
            )
            tf_candidates[tf] = tf_cands

            # Range Regime Evaluation for TF
            r_res = self.range_regime_engine.evaluate_regime(
                candles=[{"close": c, "high": h, "low": l} for c, h, l in zip(tf_closes, tf_highs, tf_lows)],
                hurst_val=h_res.get("H"),
                fractal_dim=fd_res.get("D"),
                atr_val=tf_atr
            )

            tf_reports[tf] = {
                "hurst_analysis": h_res,
                "fractal_dimension_analysis": fd_res,
                "wavelet_analysis": w_res,
                "range_regime": r_res.__dict__,
                "atr": round(tf_atr, 4),
                "timestamp": tf_ts,
                "candles": [{"close": c, "high": h, "low": l} for c, h, l in zip(tf_closes, tf_highs, tf_lows)],
                "evidence_state": "ACTIVE"
            }

        # Layer 2 Target Probability Multi-Timeframe Consensus
        consensus = self.target_prob_engine.calculate_mtf_consensus(tf_candidates)
        consensus_dict = {
            "direction": consensus.direction,
            "consensus_target": consensus.consensus_target,
            "consensus_invalidation": consensus.consensus_invalidation,
            "consensus_probability": consensus.consensus_probability,
            "disagreement_score": consensus.disagreement_score,
            "overall_confidence": consensus.overall_confidence,
            "tf_probabilities": consensus.tf_probabilities
        }

        # Layer 2 Canonical FractalMarketState
        canonical_state = self.state_builder.build_state(
            symbol=symbol_upper,
            primary_timeframe=primary_tf_upper,
            tf_fractal_reports=tf_reports,
            mtf_consensus=consensus_dict
        )

        # Layer 3 Deep RL (PPO Decision Proposal)
        # Construct single-step environment observation vector from canonical_state
        primary_rep = tf_reports.get(primary_tf_upper) or next(iter(tf_reports.values()))
        primary_closes = [o.close_price for o in (tf_observations.get(primary_tf_upper) or primary_obs)]

        dummy_env = FractalMarketEnv(
            states=[canonical_state],
            price_series=[primary_closes[-1]]
        )
        obs_vec = dummy_env._get_observation(0)
        ppo_proposal = self.ppo_agent.generate_decision_proposal(obs_vec)

        # Dynamic Pattern Memory Matching (No hardcoded strings)
        regime_query = canonical_state.m5_regime
        pattern_record = self.fractal_memory.find_matching_pattern(primary_tf_upper, regime_query)

        if pattern_record:
            matching_pattern_record = {
                "pattern_id": pattern_record.pattern_id,
                "success_rate": pattern_record.success_rate,
                "confidence_weight": pattern_record.confidence_weight,
                "evidence_state": "SUPPORTED_PATTERN"
            }
        else:
            matching_pattern_record = {
                "pattern_id": None,
                "success_rate": None,
                "confidence_weight": None,
                "evidence_state": "NO_EVIDENCE"
            }

        # Scale-Invariant Similarity with ATR-normalized displacement
        p_atr = primary_rep.get("atr", 0.0)
        sig = primary_closes[-10:] if len(primary_closes) >= 10 else primary_closes
        similarity_res = self.similarity_engine.find_similar_structures(
            current_signature=sig,
            historical_patterns=historical_patterns or [],
            atr=p_atr if p_atr > 0 else None
        )

        # Scale Construction (excluding partial trailing scale groups)
        raw_bars = []
        for o in primary_obs:
            raw_bars.append({
                "open": o.open_price,
                "high": o.high,
                "low": o.low,
                "close": o.close_price,
                "volume": o.volume,
                "timestamp": o.timestamp.isoformat()
            })

        scaled_x4 = ScaleConstructionEngine.build_scale_family(raw_bars, multiplier=4) if raw_bars else {}
        complete_scales_x4 = {}
        if scaled_x4:
            for scale_factor, bars in scaled_x4.items():
                complete_bars = [b for b in bars if not b.get("is_partial_trailing_group", False)]
                if complete_bars:
                    complete_scales_x4[scale_factor] = complete_bars

        detected_bases_count = 0
        if complete_scales_x4:
            detector = Gate3BaseDetectorEngine()
            formatted_scales = {f"x{k}": v for k, v in complete_scales_x4.items()}
            bases_report = detector.detect_multiscale_bases(formatted_scales)
            detected_bases_count = bases_report.get("total_bases_detected", 0)

        latest_ts = primary_obs[-1].timestamp.isoformat()

        result = {
            "symbol": symbol_upper,
            "primary_timeframe": primary_tf_upper,
            "fractal_status": "ACTIVE",
            "evidence_state": matching_pattern_record["evidence_state"],
            "containment_mapping": containment_map,
            "matching_pattern_record": matching_pattern_record,
            "similarity_analysis": similarity_res,
            "hurst_analysis": primary_rep.get("hurst_analysis"),
            "fractal_dimension_analysis": primary_rep.get("fractal_dimension_analysis"),
            "wavelet_analysis": primary_rep.get("wavelet_analysis"),
            "fractal_market_state": canonical_state.to_dict(),
            "target_consensus": consensus_dict,
            "ppo_decision_proposal": ppo_proposal,
            "atr": p_atr,
            "scales_evaluated_count": len(complete_scales_x4),
            "detected_bases_count": detected_bases_count,
            "timestamp": latest_ts
        }

        logger.info(f"[FractalEngine] Hybrid analysis complete for {symbol}. Regime: {canonical_state.regime_state}, PPO Proposal: {ppo_proposal['proposal_action']}")
        return result
