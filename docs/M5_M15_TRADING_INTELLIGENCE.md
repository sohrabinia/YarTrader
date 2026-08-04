# M5_M15_TRADING_INTELLIGENCE

## Overview
TradeYar AI's **M15/M5 Trading Intelligence Platform** establishes a targeted operational execution pipeline. Rather than treating all timeframes equally, the engine delegates specific roles to different resolutions, maximizing entry precision and avoiding noise.

## Core Operational Mechanics

### 1. M15 Primary Decision Gate
- All setups must originate on the **M15** timeframe.
- The engine evaluates structural elements including:
  - Local trend direction and structural bias (Bullish/Bearish)
  - Order block formations
  - Fair Value Gaps (FVG) and liquidity sweeps
- **Strict Constraint**: No trades can be executed or analyzed if there is no valid setup on the M15 timeframe. This avoids low-probability random trades driven purely by noise.

### 2. M5 Primary Execution & Trigger Engine
- Even if a setup is detected on the M15 timeframe, the trade is **NOT** immediately triggered.
- The entry trigger is delegated to the **M5** timeframe.
- The engine monitors the M5 timeframe for active trigger confirmations, such as:
  - Candlestick closures matching the M15 bias
  - Volume spikes confirming momentum
  - Pullback rejection patterns
- Trades are triggered only when M5 displays confirmation matching the M15 setup direction.

### 3. Higher Timeframe Trend Filtering
- Higher timeframes ($H1, H4, D1$) serve as directional trend filters and confidence multipliers.
- **Trend Congruence**:
  - If the higher timeframes align with the M15/M5 direction, confidence is multiplied.
  - If higher timeframes indicate a strong counter-trend, overall trade confidence is degraded instead of immediately discarding.
  - Allowing counter-trend trades with lower confidence lets the **Memory System** track outcome success rates and pattern-matching viability under counter-trend conditions.

## Component Implementation
- **Source Module**: `src/Intelligence/Execution/alignment.py`
- **Class**: `MultiTimeframeAlignmentEngine`
- **Method**: `align_m15_m5_pipeline`
