# Deterministic Baseline Position Management Specification

**Date:** 2026-08-25
**System Target:** YarTrader Autonomous Position Intelligence Scientific Validation
**Reference Dataset:** Frozen Dukascopy XAUUSD M1 Dataset (2021–2026, 2,460,951 valid records)

---

## 1. Purpose & Scope

This document specifies the exact deterministic baseline rules used to benchmark the **YarTrader Autonomous Fractal Position Intelligence Lifecycle Engine**.

To ensure a rigorous, scientifically valid comparison:
- Both the **Deterministic Baseline** and the **Autonomous System** consume the **identical event stream of entry opportunities** generated from historical multi-scale Base breakout detections.
- Neither system receives preferential entry timing or hindsight bias.
- The baseline acts as a control model with static position management rules.

---

## 2. Deterministic Baseline Rules

| Dimension | Baseline Rule | Specification Detail |
|---|---|---|
| **Entry Stream** | Identical Base Breakouts | Frozen event stream generated from Base breakouts across M5/M15/H1/H4 scales |
| **Position Sizing** | Fixed Risk Budget | Fixed $100 risk per trade ($100 / $20 fixed SL = 5.0 Oz) |
| **Stop Loss (SL)** | Static Fixed SL | Fixed $20.00/oz offset from entry price |
| **Take Profit (TP)** | Static Fixed TP | Fixed $30.00/oz offset from entry price (1.5:1 Fixed R:R) |
| **Structural Invalidation** | Disabled | Position holds strictly until price touches fixed SL or fixed TP |
| **Adaptive Trailing Stop** | Disabled | SL remains locked at initial entry -$20.0 (BUY) or +$20.0 (SELL) |
| **Adaptive Hold** | Disabled | No state evaluation during trade lifecycle |
| **Structural Exit** | Disabled | No exit on structural deterioration or parent-scale breakdown |
| **Re-Entry Intelligence** | Disabled | Exited positions are purged without re-entry tracking |
| **Direction Transition** | Disabled | Exited positions do not evaluate opposite structural entries |

---

## 3. Comparative Evaluation Parameters

The Autonomous System uses the identical $100 risk budget per trade, but dynamically determines:
- **Structural Invalidation Distance:** Derived from Base boundaries rather than static $20.
- **Position Sizing:** `Risk Budget / Structural Risk Distance`.
- **Structural Exits & Trailing Stops:** Dynamically updated as multi-scale support/resistance pivots form.
- **Re-Entry & Direction Transitions:** Candidate tracking and execution following structural confirmation.
