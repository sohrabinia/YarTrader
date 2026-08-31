from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime

import uuid
from src.Data.MarketData.Models.models import MarketDataPoint
from src.Research.Brain.trading_style import TradingStyleSelector
from src.Research.Brain.multi_timeframe_context import MultiTimeframeContextEngine
from src.Research.Brain.fractal_memory import FractalPatternMemory
from src.Risk.Services.professional_risk_engine import ProfessionalRiskEngine
from src.Decision.Intelligence.timeframe_selector import AutomaticTimeframeSelector, UnifiedSignalContract

@dataclass
class ProfessionalSignal:
    symbol: str
    direction: str  # "BUY", "SELL", "WAIT"
    trading_style: str
    timeframe: str
    entry_zone: str
    stop_loss: float
    take_profit: float
    real_rr: float
    confidence_pct: int
    historical_evidence: str
    market_reasoning: List[str]
    invalidation_condition: str
    expected_holding_period: str
    risk_level: str
    timestamp: str
    fractal_score: float = 0.85
    similarity_score: float = 88.5
    market_regime: str = "TRENDING"
    scale_state: str = "MULTISCALE_STABLE"

class ProfessionalSignalEngine:
    """
    Professional Signal Engine for YarTrader V1.2.
    Integrates Trading Knowledge, Trading Style, Multi-Timeframe Context,
    Fractal Memory, and Professional Risk Gate to output explainable BUY, SELL, or WAIT signals.
    """

    def __init__(self) -> None:
        self.style_selector = TradingStyleSelector()
        self.mtf_engine = MultiTimeframeContextEngine()
        self.fractal_memory = FractalPatternMemory()
        self.risk_engine = ProfessionalRiskEngine()
        self.tf_selector = AutomaticTimeframeSelector()

    def generate_unified_signal(
        self,
        symbol: str,
        candles_by_tf: Dict[str, List[MarketDataPoint]],
        spread_pip: float = 1.0,
        account_balance: float = 10000.0
    ) -> UnifiedSignalContract:
        # Automatic Timeframe Selection
        tf_res = self.tf_selector.select_best_timeframe(symbol, candles_by_tf)
        chosen_tf = tf_res.selected_timeframe

        sig = self.generate_signal(
            symbol=symbol,
            timeframe=chosen_tf,
            candles_by_tf=candles_by_tf,
            spread_pip=spread_pip,
            account_balance=account_balance
        )

        return UnifiedSignalContract(
            signal_id=f"SIG-{uuid.uuid4().hex[:8]}",
            symbol=sig.symbol,
            timeframe=chosen_tf,
            direction=sig.direction,
            entry_price=float(sig.entry_zone.split(" - ")[0].replace("$", "")) if sig.entry_zone != "N/A" else 0.0,
            stop_loss=sig.stop_loss,
            take_profit=sig.take_profit,
            risk_reward=sig.real_rr,
            confidence=float(sig.confidence_pct) / 100.0,
            pattern_id=sig.trading_style,
            market_context=f"MTF Selection: {tf_res.reason}",
            created_at=sig.timestamp
        )

    def generate_signal(
        self,
        symbol: str,
        timeframe: str,
        candles_by_tf: Dict[str, List[MarketDataPoint]],
        spread_pip: float = 1.0,
        account_balance: float = 10000.0
    ) -> ProfessionalSignal:
        symbol_upper = symbol.upper()
        tf_upper = timeframe.upper()

        # 1. Trading Style Selection & Spread Check
        style_profile = self.style_selector.select_style(tf_upper, spread_pip)
        trading_style = style_profile["selected_style"]
        holding_period = style_profile["holding_time"]

        # High spread environment check -> WAIT
        if not style_profile["is_spread_acceptable"]:
            return ProfessionalSignal(
                symbol=symbol_upper,
                direction="WAIT",
                trading_style=trading_style,
                timeframe=tf_upper,
                entry_zone="N/A",
                stop_loss=0.0,
                take_profit=0.0,
                real_rr=0.0,
                confidence_pct=0,
                historical_evidence="N/A",
                market_reasoning=[f"Spread ({spread_pip} pips) exceeds maximum allowed threshold for {trading_style}."],
                invalidation_condition="High spread environment.",
                expected_holding_period=holding_period,
                risk_level="HIGH_SPREAD_REJECTION",
                timestamp=datetime.now().isoformat()
            )

        # 2. Candle Data Availability Check
        current_candles = candles_by_tf.get(tf_upper) or candles_by_tf.get("M15") or []
        if not current_candles:
            return ProfessionalSignal(
                symbol=symbol_upper,
                direction="WAIT",
                trading_style=trading_style,
                timeframe=tf_upper,
                entry_zone="N/A",
                stop_loss=0.0,
                take_profit=0.0,
                real_rr=0.0,
                confidence_pct=0,
                historical_evidence="N/A",
                market_reasoning=["Insufficient market data available."],
                invalidation_condition="Missing candle series for required timeframe.",
                expected_holding_period=holding_period,
                risk_level="NO_MARKET_DATA",
                timestamp=datetime.now().isoformat()
            )

        # 3. Multi-Timeframe Context Evaluation
        mtf_context = self.mtf_engine.evaluate_context(symbol_upper, candles_by_tf)
        raw_direction = mtf_context["decision_bias"]
        market_reasoning = mtf_context["reasoning"]

        if raw_direction == "WAIT":
            return ProfessionalSignal(
                symbol=symbol_upper,
                direction="WAIT",
                trading_style=trading_style,
                timeframe=tf_upper,
                entry_zone="N/A",
                stop_loss=0.0,
                take_profit=0.0,
                real_rr=0.0,
                confidence_pct=0,
                historical_evidence="No HTF/MTF structure alignment found.",
                market_reasoning=market_reasoning,
                invalidation_condition="Higher timeframe structure in range compression.",
                expected_holding_period=holding_period,
                risk_level="Low",
                timestamp=datetime.now().isoformat()
            )

        # 3. Entry, Stop Loss, and Take Profit Calculations from Pure Price Action
        current_candles = candles_by_tf.get(tf_upper) or candles_by_tf.get("M15") or []
        if not current_candles:
            return ProfessionalSignal(
                symbol=symbol_upper,
                direction="WAIT",
                trading_style=trading_style,
                timeframe=tf_upper,
                entry_zone="N/A",
                stop_loss=0.0,
                take_profit=0.0,
                real_rr=0.0,
                confidence_pct=0,
                historical_evidence="N/A",
                market_reasoning=["Insufficient market data available."],
                invalidation_condition="Missing candle series for required timeframe.",
                expected_holding_period=holding_period,
                risk_level="NO_MARKET_DATA",
                timestamp=datetime.now().isoformat()
            )
        else:
            current_price = current_candles[-1].Close
            latest_high = max(c.High for c in current_candles[-10:])
            latest_low = min(c.Low for c in current_candles[-10:])

        pip_factor = 0.0001 if "USD" in symbol_upper and "XAU" not in symbol_upper and "BTC" not in symbol_upper else 0.1
        if "XAU" in symbol_upper:
            pip_factor = 0.1
        elif "BTC" in symbol_upper:
            pip_factor = 1.0

        if raw_direction == "BUY":
            entry_price = current_price
            stop_loss = round(latest_low - (5 * pip_factor), 2)
            tp_distance = (entry_price - stop_loss) * 2.2
            take_profit = round(entry_price + tp_distance, 2)
            entry_zone = f"${entry_price:.2f} - ${entry_price + (2 * pip_factor):.2f}"
            invalidation = f"Break below recent swing low level (${stop_loss:.2f})."
        else: # SELL
            entry_price = current_price
            stop_loss = round(latest_high + (5 * pip_factor), 2)
            tp_distance = (stop_loss - entry_price) * 2.2
            take_profit = round(entry_price - tp_distance, 2)
            entry_zone = f"${entry_price - (2 * pip_factor):.2f} - ${entry_price:.2f}"
            invalidation = f"Break above recent swing high level (${stop_loss:.2f})."

        # 4. Fractal Memory & Pattern Historical Evidence Lookup
        pattern_rec = self.fractal_memory.find_matching_pattern("LIQUIDITY_SWEEP", mtf_context.get("htf_bias", "TRENDING_UP"))
        historical_evidence = f"Historical pattern similarity matched (Success Rate: {pattern_rec.success_rate*100:.1f}%, Weight: {pattern_rec.confidence_weight})." if pattern_rec else "Baseline Price Action Evidence."

        confidence_pct = int((pattern_rec.confidence_weight if pattern_rec else 0.70) * 100)

        # 5. Professional Risk Engine Qualification Gate
        risk_result = self.risk_engine.evaluate_trade_risk(
            symbol=symbol_upper,
            direction=raw_direction,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            account_balance=account_balance,
            spread_pip=spread_pip,
            win_probability=(confidence_pct / 100.0)
        )

        final_direction = risk_result.direction
        if final_direction == "WAIT":
            market_reasoning.append(f"Risk Gate Rejection: {risk_result.rejection_reason}")

        return ProfessionalSignal(
            symbol=symbol_upper,
            direction=final_direction,
            trading_style=trading_style,
            timeframe=tf_upper,
            entry_zone=entry_zone if final_direction != "WAIT" else "N/A",
            stop_loss=stop_loss if final_direction != "WAIT" else 0.0,
            take_profit=take_profit if final_direction != "WAIT" else 0.0,
            real_rr=risk_result.real_rr,
            confidence_pct=confidence_pct if final_direction != "WAIT" else 0,
            historical_evidence=historical_evidence,
            market_reasoning=market_reasoning,
            invalidation_condition=invalidation if final_direction != "WAIT" else "Setup failed risk gate.",
            expected_holding_period=holding_period,
            risk_level="Medium" if final_direction != "WAIT" else "REJECTED",
            timestamp=datetime.now().isoformat()
        )
