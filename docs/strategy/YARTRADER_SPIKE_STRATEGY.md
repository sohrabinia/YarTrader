# YARTRADER DETERMINISTIC SPIKE STRATEGY SPECIFICATION

**Document ID:** YARTRADER-STRATEGY-SPIKE-001
**Status:** CANONICAL / AUTHORITATIVE SPECIFICATION
**Date:** September 7, 2026
**Repository:** `sohrabinia/YarTrader`
**Core Modules:** `src/Application/Strategy/spike_strategy.py`, `src/Application/Services/spike_strategy_service.py`, `src/Application/Services/web_dashboard.py`

---

## 1. Executive Summary
This document specifies the canonical mathematical definition, configuration rules, signal semantics, and zero-look-ahead evaluation logic for YarTrader's Spike Strategy (Phase 7).

The strategy evaluates normalized OHLCV market data series from Phase 6 to detect statistically abnormal price impulses ("spikes") without order execution, trade placement, or broker interaction.

---

## 2. Mathematical Definition & Formulas

### True Range ($TR_t$)
For candle $t$, the True Range is defined as:
$$TR_t = \max(High_t - Low_t, |High_t - Close_{t-1}|, |Low_t - Close_{t-1}|)$$

### Mean True Range Baseline ($MTR_t$)
The baseline volatility $MTR_t$ is the Simple Moving Average of $TR$ calculated strictly over $N$ candles prior to candle $T$ ($t - N \dots t - 1$):
$$MTR_t = \frac{1}{N} \sum_{i=1}^{N} TR_{t-i}$$

### Spike Condition
For candle $T$ with body $Body_T = Close_T - Open_T$:
1. $SpikeRatio_T = \frac{|Body_T|}{\max(MTR_T, MinVolBaseline)}$
2. Candle Range $Range_T = High_T - Low_T \ge MinMovement$
3. If $SpikeRatio_T \ge Threshold$ and $Range_T \ge MinMovement$:
   * $Body_T > 0 \implies \mathbf{SPIKE\_UP}$
   * $Body_T < 0 \implies \mathbf{SPIKE\_DOWN}$
4. Otherwise: $\mathbf{NO\_SIGNAL}$

---

## 3. Configuration Parameters

| Parameter | Type | Default | Range | Description |
| --------- | ---- | ------- | ----- | ----------- |
| `lookback_period` | int | 14 | 2..500 | Historical window size for MTR baseline |
| `spike_threshold` | float | 2.5 | 0.1..50.0 | Minimum ratio of candle body to MTR |
| `min_movement` | float | 1.0 | $\ge 0.0$ | Minimum absolute candle range ($High - Low$) |
| `min_volatility_baseline` | float | 0.1 | $\ge 0.0$ | Floor to prevent divide-by-zero on micro-range bars |

---

## 4. Zero Look-Ahead Bias Guarantee
At timestamp $T$, the strategy processes candles $t \le T$ exclusively. Historical baseline $MTR_T$ is computed strictly from prior bars $t - N \dots t - 1$. Adding future candles $T+1, T+2 \dots$ leaves the signal evaluation at $T$ completely invariant.

---

## 5. Phase 7 Completion Verdict

```text
PHASE 7 = PASS
```
