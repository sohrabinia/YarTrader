# YARTRADER DETERMINISTIC TREND STRATEGY SPECIFICATION

**Document ID:** YARTRADER-STRATEGY-TREND-001
**Status:** CANONICAL / AUTHORITATIVE SPECIFICATION
**Date:** September 7, 2026
**Repository:** `sohrabinia/YarTrader`
**Core Modules:** `src/Application/Strategy/trend_strategy.py`, `src/Application/Services/trend_strategy_service.py`, `src/Application/Services/web_dashboard.py`

---

## 1. Executive Summary
This document specifies the canonical mathematical definition, configuration parameters, signal semantics, and zero-look-ahead evaluation logic for YarTrader's Trend Strategy (Phase 9).

The strategy evaluates normalized OHLCV market data series from Phase 6 to detect directional momentum and trend strength ("uptrend" or "downtrend") without order execution, trade placement, or broker interaction.

---

## 2. Mathematical Definition & Formulas

### Fast & Slow Simple Moving Averages ($Fast_T, Slow_T$)
For candle window $W_T = \{t_1, t_2, \dots, T\}$ and period $P$:
$$SMA(Close, P)_T = \frac{1}{P} \sum_{i=0}^{P-1} Close_{T-i}$$
* $Fast_T = SMA(Close, FastPeriod)_T$
* $Slow_T = SMA(Close, SlowPeriod)_T$

### Trend Spread ($Spread_T$)
$$Spread_T = Fast_T - Slow_T$$

### Volatility Baseline ($MTR_T$)
The baseline volatility $MTR_T$ is the Mean True Range calculated strictly over candles prior to $T$ ($t - SlowPeriod \dots t - 1$):
$$MTR_T = \max \left( \frac{1}{SlowPeriod} \sum_{i=1}^{SlowPeriod} TR_{T-i}, MinVolBaseline \right)$$

### Normalized Trend Strength ($NTS_T$)
$$NTS_T = \frac{|Spread_T|}{MTR_T}$$

### Trend Condition
At evaluation timestamp $T$:
1. If $NTS_T \ge MinimumTrendStrength$:
   * $Spread_T > 0 \implies \mathbf{TREND\_UP}$
   * $Spread_T < 0 \implies \mathbf{TREND\_DOWN}$
2. Otherwise: $\mathbf{NO\_SIGNAL}$

---

## 3. Configuration Parameters

| Parameter | Type | Default | Range | Description |
| --------- | ---- | ------- | ----- | ----------- |
| `fast_period` | int | 5 | 2..$SlowPeriod-1$ | Fast Simple Moving Average window |
| `slow_period` | int | 20 | $> FastPeriod .. 500$ | Slow Simple Moving Average & MTR window |
| `minimum_trend_strength` | float | 0.5 | 0.0..50.0 | Minimum ratio of Trend Spread to MTR |
| `min_volatility_baseline` | float | 0.1 | $\ge 0.0$ | Floor to prevent divide-by-zero on zero-volatility bars |

---

## 4. Zero Look-Ahead Bias Guarantee
At timestamp $T$, the strategy processes candles $t \le T$ exclusively. Moving averages ($Fast_T, Slow_T$) and volatility baseline $MTR_T$ are computed strictly using candles available at or before $T$. Adding future candles $T+1, T+2 \dots$ leaves the signal evaluation at $T$ completely invariant.

---

## 5. Phase 9 Completion Verdict

```text
PHASE 9 = PASS
```
