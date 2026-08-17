# YarTrader V1.2 Fractal Market Intelligence & Self-Similarity

## Overview
Financial markets display self-similar fractal geometry: price action patterns observed on lower timeframes (e.g. M15) frequently resemble structural formations occurring on higher timeframes (e.g. H4 or D1), differing primarily in duration, volatility amplitude, and risk exposure.

---

## Pattern Record Storage Schema
The `FractalPatternMemory` module records structural memory across time scales using the following fields:

- `pattern_id`: Unique identifier for the Price Action formation (e.g., `PAT_LIQUIDITY_SWEEP_REVERSAL`).
- `timeframe`: Primary resolution on which the pattern was recorded.
- `market_context`: Structural context (`TRENDING_UP`, `TRENDING_DOWN`, `RANGE_BOUND`).
- `frequency`: Total historical occurrences observed.
- `wins` / `losses`: Empirical outcome metrics.
- `success_rate`: Empirical win probability ($\frac{\text{wins}}{\text{frequency}}$).
- `confidence_weight`: Normalized weight dynamic allocation ($0.40 + 0.50 \times \text{success\_rate}$).

---

## Self-Similar Matching
When evaluating an active trade setup, YarTrader queries `FractalPatternMemory` for matching structural formations across timeframes to weight confidence levels and adjust signal qualification gates dynamically.
