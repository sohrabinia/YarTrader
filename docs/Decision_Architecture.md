# Decision Architecture

## 1. Overview
Simulated trades are logged in a highly structured, immutable format. At decision-time, the system records:
- `Decision ID`
- `Timestamp`
- `Symbol`
- `Action` (`BUY`, `SELL`, `WAIT`, `NO TRADE`)
- `Entry Price` (including realistic spread/slippage markup)
- `Stop Loss` and `Target Price` boundaries
- `Confidence` and `Evidence references`

---

## 2. Immutability & Future Protection
Once created, decisions, entry boundaries, and logical reasoning are strictly immutable. Storing decisions in this manner blocks any history rewriting, cherry-picking, or future leakage.
