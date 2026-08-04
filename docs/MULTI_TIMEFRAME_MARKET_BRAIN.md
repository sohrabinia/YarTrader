# MULTI_TIMEFRAME_MARKET_BRAIN

## Overview
The **TradeYar AI Hierarchical Multi-Timeframe Market Brain** is designed to process, map, and synthesize market structures across a complete 9-layer resolution matrix. This hierarchical approach ensures that localized price execution and entry setups are fully congruent with macro trend regimes, major institutional levels, and systemic liquidity patterns.

## The 9-Layer Timeframe Matrix
The system ingests and processes the following 9 resolutions in real-time or historical backtest replay sessions:

1. **Tick / Tick stream**: Micro Structure & Liquidity Absorption timing
2. **M1**: Micro-Structure Confirmation & Spread / Volume dynamics
3. **M5**: Primary Execution, Breakout Confirmations, Entry & Trigger mechanics
4. **M15**: Primary Decision, Market Structure setups (FVG, Order Blocks), and Local Bias
5. **H1**: Local Trend, Intraday Key Zones, and Support/Resistance structure
6. **H4**: Market Regime (Accumulation, Recovery, Distribution), Major Swings, and Order Flow
7. **D1**: Macro Trend Direction, Daily Key Ranges, and Macro Structure Gates
8. **W1**: Weekly Bias and long-term trend alignment
9. **MN1**: Monthly Macro Context, multi-year key levels, and global market regimes

```
+-------------------------------------------------------------+
|                     MACRO CONTEXT                           |
|      MN1  ===>  W1  ===>  D1  (Trend Direction / Bias)       |
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
|                     MARKET REGIME                           |
|         H4  ===>  H1  (Accumulation & Key Zones)            |
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
|                     PRIMARY DECISION                        |
|            M15 (Structure Setups / Bias / FVG)              |
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
|                     PRIMARY EXECUTION                       |
|           M5 (Trigger Confirmation / Pullbacks)             |
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
|                     MICRO CONFIRMATIONS                     |
|           M1 ===> Tick (Liquidity Spikes / Spreads)         |
+-------------------------------------------------------------+
```

## Structural Fractal Containment
Market structures exhibit fractal behavior, meaning smaller timeframe sequences compose higher timeframe structures. The `MultiTimeframePerception` module maps consecutive levels in the timeframe hierarchy to track these containment relationships automatically.

For example, when a high-timeframe structural zone (e.g., H4) is active, the engine monitors lower-timeframe (e.g., H1, M15) reaction cycles contained within that period to discover high-probability setups.

## Component Implementation
- **Source Module**: `src/Research/Brain/multi_timeframe.py`
- **Class**: `MultiTimeframePerception`
- **Context Constructor**: `generate_hierarchical_context`
