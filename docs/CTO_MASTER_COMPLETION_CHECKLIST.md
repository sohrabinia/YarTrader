# YarTrader CTO Master Completion Checklist

> Working checklist for final completion. A checkbox is marked complete only when the corresponding source, test, or runtime evidence is actually proven.

## Product / Brain
- [x] One existing Brain architecture retained; no second Brain introduced.
- [x] Brain remains advisory/learning authority and has no order-placement API.
- [ ] Raw-market multi-timeframe perception is proven on the physical production runtime (Gate-E).
- [ ] M1/M5/M15/H1/H4/D1/W1/MN1 are all available to the production Brain at the same point-in-time boundary.
- [ ] Cross-timeframe context is proven indicator-free and non-rule-dependent.
- [ ] Self-learning loop is proven to update memory from outcomes without changing safety invariants.
- [ ] Learning can improve market knowledge/behavior without acquiring execution authority.

## Backtest
- [ ] Point-in-time replay is proven against future leakage / look-ahead.
- [ ] No future candle, future outcome, or post-decision information can affect a historical decision.
- [ ] Costs/slippage/spread and ambiguous candle handling are evidence-backed.
- [ ] Backtest uses the same Brain decision authority as production research.

## Execution / Risk
- [x] LIVE trading infrastructure is retained but hard-disabled/fail-closed.
- [x] DEMO execution is restricted to XAUUSD.
- [x] Requested risk target is 0.5% with 2% hard ceiling.
- [x] Minimum RR gate is 1.5.
- [x] Daily Loss Kill Switch is 8%.
- [x] Missing/invalid daily-loss baseline fails closed.
- [ ] Every actual DEMO order path is proven to pass the authoritative safety gate.
- [ ] No execution bypass exists outside the gate.

## Signal / Demo / Prop
- [x] Signal is generated through the canonical Brain decision/intelligence path in the tested runtime contract.
- [x] DEMO uses the same Brain decision path plus execution safety gates in the final CI contract.
- [ ] Prop uses the same Brain decision path plus Prop-specific risk/account constraints.
- [x] Shadow is not an execution authority and is closed as a customer-facing mode.

## Indicator-Free Invariant
- [x] Production default research path is PrimitiveMarketResearchEngine.
- [x] TechnicalAnalysisEngine is not on the default production path.
- [x] ATR/True-Range Gate-3 base detector is disconnected from FractalEngine.
- [ ] Full production reachability audit proves no forbidden indicator reaches executable decision logic.

## Auth / i18n
- [x] Customer login UI is Google/Gmail-only.
- [x] Backend customer-auth endpoints are covered by the final CI auth contract tests; physical production runtime remains a Gate-E item.
- [x] FA/EN/TR/AR locale key parity is proven on the final HEAD.
- [x] Locale parity and user-visible localization contracts pass the final CI suite; human visual review remains open.
- [ ] RTL/LTR and typography are verified for FA/AR vs EN/TR.

## UI / UX / Brand
- [ ] First-impression public website reviewed for human/institutional product quality.
- [ ] No fabricated metrics, fake activity, or misleading status claims remain.
- [ ] Typography, spacing, hierarchy, charts, tables, empty/loading/error states are polished.
- [ ] Responsive behavior is verified across desktop/tablet/mobile.
- [ ] Trading terminology is consistent across all four languages.
- [ ] Live/Disabled, Demo, Backtest, Signal, and Prop states are visually truthful.

## Gate E / Production Runtime
- [ ] Exact final HEAD CI succeeds.
- [ ] Windows Session 0 service identity proven.
- [ ] Interactive Session 2 bridge proven.
- [ ] Authenticated Alpari-MT5-Demo proven.
- [ ] Real XAUUSD/H1 data provenance proven.
- [ ] Recovery A/B/C proven.
- [ ] Dual-layer zero-order proof proven.
- [ ] Final Gate E derived status = PROVEN.

## Final Release
- [ ] Exact base / merge-base / HEAD and diff verified.
- [ ] Full test suite passes on final HEAD.
- [ ] Frontend production build passes on final HEAD.
- [ ] Final forensic report reconciles source + tests + runtime evidence.
- [ ] Only after all mandatory gates are PROVEN: merge PR.


## Final CI Evidence — 2026-09-28
- Final PR head: `a1622cffdab30de4474cfbb85084301f0736ce54`
- Base/main: `00d676016d130120b10c4e9bd9d2b0e39b3ad0ee`
- Merge-base: `00d676016d130120b10c4e9bd9d2b0e39b3ad0ee`
- CI run: `#1261` (`36364107266`) — **SUCCESS**
- Validation: **1960 passed, 0 failed, 0 skipped**
- Frontend production build: **SUCCESS**
- Physical Windows Gate-E: **NOT PROVEN** until final-head collector evidence is supplied from the deployment host.
