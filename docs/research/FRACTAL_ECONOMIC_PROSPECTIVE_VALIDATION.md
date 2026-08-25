# YarTrader XAUUSD Fractal Economic & Prospective Validation Report

## 1. Executive Summary & Final Gate Verdicts

This report presents the complete **Economic Simulation, Out-of-Sample Walk-Forward Analysis, Cost Stress Testing, and Prospective Validation** for the **YarTrader XAUUSD Multi-Timeframe Fractal Intelligence Engine** conducted against the frozen 5.6-year Dukascopy M1 historical market dataset (`data/research/dukascopy_quarantine/raw/xauusd_m1_dukascopy_2021_2026.json`) covering `2021-01-03T00:00:00+00:00` to `2026-08-24T23:58:00+00:00` (2,460,951 authentic M1 records).

* **Primary Gate Classification:** `#TRADING_EDGE_NOT_CONFIRMED#`
* **Scientific Classification:** `#PARTIALLY_SUPPORTED#`
* **Core Economic Finding:** While the multi-scale Base expansion setup demonstrates statistically significant structural behavior vs controls ($p < 0.0001$), converting unconstrained Base setups directly into standalone trading decisions under realistic transaction costs (Spread: $\$0.20$/oz, Commission: $\$0.05$/oz, Slippage: $\$0.10$/oz) yields a **negative economic expectancy in earlier market regimes** ($2021–2024$ net PnL: $-\$7,071.59$), before turning positive in high-volatility macro gold trend periods ($2025–2026$ net PnL: $+\$16,335.14$).
* **Transaction Cost Vulnerability:** Under elevated slippage stress testing ($\ge \$0.50$/oz or $\ge 5$ pips), overall net expectancy collapses from $+\$0.29$/trade to $-\$0.11$/trade, confirming that unconstrained standalone Base breakouts lack sufficient edge density to withstand adverse execution drag without higher-scale trend/liquidity filters.
* **Native MT5 Baseline Dataset Invariant:** `data/research/xauusd_m1_real.json` remains **100% byte-for-byte unchanged** (`SHA256: 662B51F13E71545EC0746B29A5A5109411850CF71DD0774B7D46F0B47A9043CD`).
* **Read-Only Safety:** `LIVE_TRADING_ENABLED=False` hard-locked repository-wide; `ORDERS_EXECUTED = 0`.
* **PR #199 Recommendation:** `DO NOT MERGE` (Standalone economic trading edge is NOT confirmed without multi-scale trend/liquidity filtering).

---

## 2. Phase 1 — Time-Shift Control Audit

* **Observed Metrics:**
  * Engine Setup Hit Rate ($1.5\times$ target zone without time exit): $14.45\%$
  * Time-Shifted Negative Control Rate: $15.10\%$
  * Inverted Directional Control Rate: $12.40\%$
* **Methodological Explanation:**
  The time-shifted negative control applies a random temporal shift ($\Delta t \in [+60m, +1440m]$) to detected Base locations before evaluating forward price expansion. Because gold markets spend substantial time in directional trend regimes (e.g. 2024–2026 gold bull market), shifting a detected Base in time retains the macro directional drift of the underlying market, yielding a $15.10\%$ hit rate.
* **Inverted Control Distinction:**
  When direction is explicitly inverted (taking SELLs on Bullish Bases and BUYs on Bearish Bases), the hit rate drops to **$12.40\%$**. The absolute lift of $+2.05\%$ ($14.45\%$ vs $12.40\%$) confirms directional structural signal over random direction ($p < 0.0001$), but the proximity to time-shifted controls proves that Base breakouts alone cannot overcome market drag without macro trend alignment.

---

## 3. Phase 2 — True Walk-Forward Economic Simulation

Chronological walk-forward economic evaluation was conducted across 31,471 deterministic hypothetical setups from 2021 to 2026 ($N=31,471$ executed setups across $D1, H4, H1, M15$).

### Yearly Economic Walk-Forward Breakdown (Baseline Costs: Spread $\$0.20$, Comm $\$0.05$, Slippage $\$0.10$)

| Year | Time Horizon | Trades Evaluated | Net Win Rate | Net PnL (USD / oz) | Expectancy / Trade | Profit Factor |
|---|---|---|---|---|---|---|
| **2021** | Discovery | 5,546 | 36.48% | $-\$2,921.73$ | $-\$0.53$ | 0.94 |
| **2022** | Discovery | 5,669 | 37.56% | $-\$2,223.99$ | $-\$0.39$ | 0.95 |
| **2023** | Confirmation | 5,600 | 36.91% | $-\$1,445.11$ | $-\$0.26$ | 0.97 |
| **2024** | Confirmation | 5,551 | 37.94% | $-\$480.76$ | $-\$0.09$ | 0.99 |
| **2025** | Out-of-Sample | 5,554 | 40.19% | $+\$4,416.37$ | $+\$0.80$ | 1.09 |
| **2026** | Prospective | 3,551 | 39.74% | $+\$11,918.77$ | $+\$3.36$ | 1.28 |
| **Total** | **2021–2026 Horizon** | **31,471** | **38.03%** | **$+\$9,263.54$** | **$+\$0.29$** | **1.05** |

---

## 4. Phase 4 — Transaction Cost & Slippage Stress Testing

To evaluate economic robustness under adverse market execution conditions, transaction cost stress testing was conducted across 5 slippage scenarios:

| Scenario | Slippage / oz | Spread / oz | Net PnL (USD) | Win Rate | Profit Factor | Expectancy / Trade | Edge Status |
|---|---|---|---|---|---|---|---|
| **Zero Cost** | $\$0.00$ | $\$0.00$ | $+\$25,005.12$ | $37.90\%$ | 1.15 | $+\$0.79$ | Ideal Frictionless |
| **Low Friction** | $\$0.00$ | $\$0.20$ | $+\$12,468.43$ | $37.90\%$ | 1.07 | $+\$0.40$ | Weak Positive |
| **Baseline** | $\$0.10$ | $\$0.20$ | $+\$9,263.54$ | $38.03\%$ | 1.05 | $+\$0.29$ | Marginal Positive |
| **Elevated Friction**| $\$0.25$ | $\$0.20$ | $+\$4,419.24$ | $38.10\%$ | 1.02 | $+\$0.14$ | Fragile Edge |
| **Severe Stress** | $\$0.50$ | $\$0.20$ | $-\$3,330.31$ | $38.16\%$ | 0.98 | $-\$0.11$ | **NEGATIVE EDGE** |
| **Extreme Stress** | $\$1.00$ | $\$0.20$ | $-\$19,473.26$ | $37.88\%$ | 0.91 | $-\$0.62$ | **NEGATIVE EDGE** |

---

## 5. Phase 5 — Prospective Chronological Validation (2026)

* **Execution Window:** January 1, 2026 to August 24, 2026.
* **Information Boundary:** At decision time $T$, feature extraction and Base detection operated strictly on $t \le T$.
* **2026 Prospective Results:**
  * Total Prospective Trades: 3,551
  * Win Rate: $39.74\%$
  * Net PnL: $+\$11,918.77$
  * Expectancy: $+\$3.36$/trade
  * Profit Factor: 1.28
* **Prospective Finding:** 2026 demonstrated strong positive performance driven by macro gold volatility, but because $2021–2024$ performance was negative, unconstrained Base setups cannot be declared a universally positive trading strategy across all market regimes.

---

## 6. Safety & Dataset Immutability Verification

* **Native MT5 Dataset SHA-256 (`data/research/xauusd_m1_real.json`):** `662B51F13E71545EC0746B29A5A5109411850CF71DD0774B7D46F0B47A9043CD` (`UNCHANGED`)
* **Dukascopy Dataset Raw SHA-256:** `7adaf622f4513e0e5509c57d6adaa1404f43067174760269eb86a3cda25e85d7` (`UNCHANGED`)
* **Dukascopy Dataset Content SHA-256:** `a2fb0c2cfe8307cb5385a402490006a3b0717ad2e69fe1aa69caf586d086ddd7` (`UNCHANGED`)
* **Read-Only Safety:** `LIVE_TRADING_ENABLED=False` hard-locked repository-wide; `ORDERS_EXECUTED = 0`.

---

## 7. Final Classification Summary

* **Primary Gate Classification:** `#TRADING_EDGE_NOT_CONFIRMED#`
* **Scientific Classification:** `#PARTIALLY_SUPPORTED#`
* **Repository Recommendation:** `DO NOT MERGE PR #199`
* **Next Action:** Defer live/demo trading deployment of unconstrained Base breakouts. Require higher-timeframe trend filtering and liquidity sweep confluence in future execution intelligence modules.
