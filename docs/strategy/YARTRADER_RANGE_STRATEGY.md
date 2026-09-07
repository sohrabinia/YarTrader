# YARTRADER DETERMINISTIC RANGE STRATEGY SPECIFICATION

**Document ID:** YARTRADER-STRATEGY-RANGE-001
**Status:** CANONICAL / AUTHORITATIVE SPECIFICATION
**Date:** September 7, 2026
**Repository:** `sohrabinia/YarTrader`
**Core Modules:** `src/Application/Strategy/range_strategy.py`, `src/Application/Services/range_strategy_service.py`, `src/Application/Services/web_dashboard.py`

---

## 1. Executive Summary
This document specifies the canonical mathematical definition, configuration parameters, signal semantics, and zero-look-ahead evaluation logic for YarTrader's Range Strategy (Phase 8).

The strategy evaluates normalized OHLCV market data series from Phase 6 to detect consolidated, sideways price channels ("ranges") without order execution, trade placement, or broker interaction.

---

## 2. Mathematical Definition & Formulas

### Rolling Channel High & Low ($RH_T, RL_T$)
For candle window $W_T = \{t_1, t_2, \dots, T\}$ of size $N = LookbackPeriod$:
$$RH_T = \max_{t \in W_T} (High_t)$$
$$RL_T = \min_{t \in W_T} (Low_t)$$

### Range Width ($RW_T$)
$$RW_T = RH_T - RL_T$$

### Volatility Baseline ($MTR_T$)
The baseline volatility $MTR_T$ is the Mean True Range calculated strictly over candles prior to $T$ ($t - N \dots t - 1$):
$$MTR_T = \max \left( \frac{1}{N} \sum_{i=1}^{N} TR_{T-i}, MinVolBaseline \right)$$

### Normalized Range Ratio ($NRR_T$)
$$NRR_T = \frac{RW_T}{MTR_T}$$

### Range Condition
At evaluation timestamp $T$:
1. If $RW_T \ge MinRangeWidth$ AND $NRR_T \le MaxNormalizedRange$: $\mathbf{RANGE}$
2. Otherwise: $\mathbf{NO\_SIGNAL}$

---

## 3. Configuration Parameters

| Parameter | Type | Default | Range | Description |
| --------- | ---- | ------- | ----- | ----------- |
| `lookback_period` | int | 20 | 3..500 | Rolling window size for channel high/low and MTR |
| `max_normalized_range` | float | 4.5 | 0.1..50.0 | Maximum allowed ratio of channel width to MTR |
| `min_range_width` | float | 0.5 | $\ge 0.0$ | Minimum absolute channel range ($RH - RL$) |
| `min_volatility_baseline` | float | 0.1 | $\ge 0.0$ | Floor to prevent divide-by-zero on micro-range bars |

---

## 4. Zero Look-Ahead Bias Guarantee
At timestamp $T$, the strategy processes candles $t \le T$ exclusively. Rolling channel bounds ($RH_T, RL_T$) and volatility baseline $MTR_T$ are computed strictly using candles available at or before $T$. Adding future candles $T+1, T+2 \dots$ leaves the signal evaluation at $T$ completely invariant.

---

## 5. Phase 8 Completion Verdict

```text
PHASE 8 = PASS
```
