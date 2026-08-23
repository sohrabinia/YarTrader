import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from src.Research.MarketAnalysis.Interfaces.interfaces import IFractalEngine
from src.Research.Brain.multi_timeframe import MultiTimeframePerception
from src.Research.Brain.fractal_memory import FractalPatternMemory
from src.Research.Brain.fractal_data_scale_engine import ScaleConstructionEngine
from src.Research.Brain.fractal_base_detection_engine import Gate3BaseDetectorEngine
from src.Intelligence.Execution.similarity import PatternSimilarityIntelligenceEngine
from src.Research.Brain.models import MarketObservation

logger = logging.getLogger("YarTrader.FractalEngine")

class FractalEngine(IFractalEngine):
    """
    Unified YarTrader Fractal Behavior Analysis Engine.
    Executes:
    1. Multi-Timeframe Containment Mapping (Structural self-similarity)
    2. Fractal Pattern Memory & Cosine Similarity Lookup
    3. Multi-Scale Aggregation (Family x3 and x4) & Base Detection
    """

    def __init__(
        self,
        fractal_memory: Optional[FractalPatternMemory] = None,
        similarity_engine: Optional[PatternSimilarityIntelligenceEngine] = None
    ) -> None:
        self.fractal_memory = fractal_memory or FractalPatternMemory()
        self.similarity_engine = similarity_engine or PatternSimilarityIntelligenceEngine()
        logger.info("[FractalEngine] Subsystem initialized cleanly.")

    def analyze_fractals(
        self,
        symbol: str,
        primary_timeframe: str,
        candles_by_tf: Dict[str, List[Any]],
        historical_patterns: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Processes candles across timeframes to analyze fractal dynamics.
        Returns a rich dictionary containing containment relationships, matching patterns,
        similarity score, scale construction manifests, and base detections.
        """
        logger.info(f"[FractalEngine] Executing analysis for {symbol} on primary TF {primary_timeframe}")
        symbol_upper = symbol.upper()

        # 1. Multi-timeframe containment mapping
        perception = MultiTimeframePerception(symbol_upper)
        tf_observations: Dict[str, List[MarketObservation]] = {}

        for tf, candles in candles_by_tf.items():
            obs_list: List[MarketObservation] = []
            for c in candles:
                # Handle dict or dataclass/object
                ts = getattr(c, "Timestamp", None) or getattr(c, "timestamp", None)
                if isinstance(ts, str):
                    try:
                        ts = datetime.fromisoformat(ts)
                    except Exception:
                        ts = datetime.now()
                elif ts is None:
                    ts = datetime.now()

                close_val = float(getattr(c, "Close", None) or getattr(c, "close", 0.0))
                vol_val = float(getattr(c, "Volume", None) or getattr(c, "volume", 0.0))

                open_val = float(getattr(c, "Open", None) or getattr(c, "open", close_val))
                high_val = float(getattr(c, "High", None) or getattr(c, "high", close_val))
                low_val = float(getattr(c, "Low", None) or getattr(c, "low", close_val))

                obs_list.append(
                    MarketObservation(
                        symbol=symbol_upper,
                        timeframe=tf.upper(),
                        timestamp=ts,
                        high=high_val,
                        low=low_val,
                        open_price=open_val,
                        close_price=close_val,
                        volume=vol_val,
                        meta={"Source": "FractalEngine"}
                    )
                )
            tf_observations[tf.upper()] = obs_list

        containment_map = perception.map_fractal_relationships(tf_observations)

        # 2. Pattern Matching via FractalPatternMemory & Cosine Similarity
        primary_candles = candles_by_tf.get(primary_timeframe.upper()) or []
        if not primary_candles and candles_by_tf:
            primary_candles = next(iter(candles_by_tf.values()))

        closes = [float(getattr(c, "Close", None) or getattr(c, "close", 0.0)) for c in primary_candles[-10:]] if primary_candles else []

        matching_pattern_record = self.fractal_memory.find_matching_pattern("LIQUIDITY_SWEEP", "TRENDING_UP")
        similarity_res = self.similarity_engine.find_similar_structures(
            current_signature=closes[-4:] if len(closes) >= 4 else closes,
            historical_patterns=historical_patterns or []
        )

        # 3. Scale Construction & Base Detection
        raw_bars = []
        for c in primary_candles:
            raw_bars.append({
                "open": float(getattr(c, "Open", None) or getattr(c, "open", 0.0)),
                "high": float(getattr(c, "High", None) or getattr(c, "high", 0.0)),
                "low": float(getattr(c, "Low", None) or getattr(c, "low", 0.0)),
                "close": float(getattr(c, "Close", None) or getattr(c, "close", 0.0)),
                "volume": float(getattr(c, "Volume", None) or getattr(c, "volume", 1.0)),
                "timestamp": str(getattr(c, "Timestamp", None) or getattr(c, "timestamp", ""))
            })

        scaled_x4 = ScaleConstructionEngine.build_scale_family(raw_bars, multiplier=4) if raw_bars else {}
        scale_audit = ScaleConstructionEngine.audit_scale_construction(scaled_x4, {}) if scaled_x4 else {}

        detected_bases_count = 0
        if scaled_x4:
            detector = Gate3BaseDetectorEngine()
            formatted_scales = {f"x{k}": v for k, v in scaled_x4.items()}
            bases_report = detector.detect_multiscale_bases(formatted_scales)
            detected_bases_count = bases_report.get("total_bases_detected", 0)

        result = {
            "symbol": symbol_upper,
            "primary_timeframe": primary_timeframe.upper(),
            "fractal_status": "ACTIVE",
            "containment_mapping": containment_map,
            "matching_pattern_record": {
                "pattern_id": matching_pattern_record.pattern_id if matching_pattern_record else "PAT_BASELINE",
                "success_rate": matching_pattern_record.success_rate if matching_pattern_record else 0.5,
                "confidence_weight": matching_pattern_record.confidence_weight if matching_pattern_record else 0.5
            },
            "similarity_analysis": similarity_res,
            "scales_evaluated_count": len(scaled_x4),
            "detected_bases_count": detected_bases_count,
            "timestamp": datetime.now().isoformat()
        }

        logger.info(f"[FractalEngine] Analysis completed for {symbol}. Matching pattern weight: {result['matching_pattern_record']['confidence_weight']}")
        return result
