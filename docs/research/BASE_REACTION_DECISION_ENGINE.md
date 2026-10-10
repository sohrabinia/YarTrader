# Multi-timeframe Base reaction decision engine

## Design contract

Each Base is measured in its own timeframe. The reaction profile key is:

`timeframe | Base type | parent timeframe | parent relation | alignment | prospective/observed reaction number | penetration bin`

Depth is normalized from the near edge toward the far edge: EDGE (0-0.25), OUTER (0.25-0.50), INNER (0.50-0.75), FAR_EDGE (0.75-1.0). These are descriptive buckets, not presumed profitable entry points. The live proposal currently tests a midpoint retest; alternative entry depths must be compared in the offline simulation before selecting one.

## Parent/child causal requirements

- Parent is a higher timeframe than child, and parent confirmation must precede child confirmation.
- Parent and child departure directions must agree for continuation entries.
- A fresh, direction-aligned closed M1 Base departure must confirm timing.
- The measured reaction must belong to the selected child Base; future or stale information is rejected.
- Historical profiles are learned only from completed, costed `net_R` labels explicitly marked `broker_costed` or `historical_execution_simulation`. The descriptive `base_reaction_profile_1200k.json` contains excursion statistics, not trade PnL, and must never be loaded as an execution model.

## Entry, exit and reverse decisions

- Entry: proposal-only conditional retest plan, only if the exact profile passes sample, win-rate, mean net-R and order geometry/cost gates.
- Hold: retain a position only while its own wave structure remains valid and its estimated continuation net expected value remains positive; protective broker stops remain authoritative.
- Exit: propose closing if the held wave loses structural validity or its continuation net expected value is non-positive/missing. A missing opposite edge does not justify a reverse entry.
- Reverse: only after the current wave loses its edge, the opposite structure is explicitly confirmed, the opposite scenario's net expected value after costs is positive, net reward/risk is at least 1.2, and the opposite Base reaction profile and conditional order plan pass. Close-first and broker-flat confirmation are required before any future reverse execution.

## Safety and status

`src/Decision/Intelligence/base_reaction_decision_engine.py` is pure and broker-independent. `AutonomousDemoTrader` adds its result as `reaction_analysis`; no order is placed, modified, cancelled, or closed by this component. It looks only for a separate `base_reaction_behavior_model_research.json` costed model. If absent, it returns WAIT. The existing reaction profile report is exploratory and is not such a model.

## Expanded reaction-grid replay (implemented and run; no profile qualified)

`scripts/research/train_hierarchical_base_behavior.py` now evaluates four candidate penetration fractions (0.125, 0.375, 0.625, 0.875 from the near edge) crossed with the first, second and third future zone revisit after the M1 trigger. The global reaction ordinal includes visits since child Base confirmation; the first/second/third parameter is the future visit offset from the trigger. The target Base must have been confirmed by the M1 trigger timestamp, preventing future destination leakage. Keys use the same schema as the decision engine: `timeframe|base_type|parent_timeframe|parent_relation|alignment|reaction_number|depth_bin`.

This grid is a sensitivity study, not permission to choose the best in-sample cell. It uses the current 0.05 ATR round-trip cost proxy and sampled event detector. The runtime gate additionally requires a conservative depth-familywise lower bound of mean net-R (`mean_net_r - 2.5 * mean_net_r_standard_error`) to meet the minimum edge threshold, approximating a Bonferroni adjustment for the four depth bins compared within a fixed context. This does not replace broader multiple-comparison correction across all Base/timeframe/revisit contexts. A model missing mean-net-R uncertainty is rejected. Compare only with chronological walk-forward, an untouched final holdout, multiple-comparison correction, and robust cost stress tests. The four depths and three revisit offsets are configurable via `--depth-fractions` and `--reaction-numbers`.

### 1.2-million-M1-bar grid result

`runtime_logs/mt5_gold_history_full/base_reaction_grid_walkforward_1200k.json` reports 493 simulated filled outcomes across the 12 depth/revisit configurations pooled together: 54.97% wins, mean net-R proxy -0.0610, profit-factor proxy 0.8129, and pooled 95% lower bound -0.1396. This pooled statistic is not a single strategy and must not be treated as an estimate for one deployable configuration. There were 317 exact profile groups, but maximum group sample size was only 10 against a minimum of 40; zero groups passed and chronological walk-forward accepted zero trades. The model includes mean-net-R standard errors and loads successfully, but zero profiles qualify for proposals. The older model without uncertainty is preserved as `base_reaction_behavior_model_research_legacy_no_mean_se.json` and must not be used. The result is negative/inconclusive for deployment, not a profitable result.

`runtime_logs/mt5_gold_history_full/base_reaction_grid_sensitivity_summary_1200k.json` aggregates descriptive outcomes by depth and revisit number. By depth: EDGE n=193 mean -0.0435R; OUTER n=122 mean -0.0721R; INNER n=93 mean -0.1784R; FAR_EDGE n=85 mean +0.0435R, but its 95% lower bound is -0.235R. By total reaction ordinal, reaction 3 has mean +0.2042R across n=93, but its 95% lower bound is -0.0324R; reaction 1 is -0.1204R (n=132), reaction 2 -0.0009R (n=142), and later reactions trend worse in this sample. These are overlapping sensitivity aggregates across different configurations, not independent strategy returns. No depth/reaction group has evidence strong enough to enable trading.

## Required next research

1. Replace the ATR cost proxy with verified broker-specific spread, commission and slippage distributions; preserve a conservative gap/fill model and order expiry/cancellation.
2. Split by time, not random shuffle; train profiles only on outcomes completed before each decision timestamp.
3. Compare reaction depth and visit number by timeframe, Base type, parent relation/alignment, volatility and session. Correct for multiple comparisons and overlapping bases; report effective independent samples.
4. Run untouched holdout, shadow, then demo-forward with durable order reconciliation. Keep real-money execution disabled until separate validation and explicit authorization.

The autonomous candle fetcher now starts from MT5 bar shift 1, excluding the still-forming shift-0 candle from Base detection and M1 confirmation.

## Descriptive study snapshot

`base_reaction_profile_1200k.json` covers H4/H1/M15/M5 and 1.2 million M1 bars. It reports 75,910 reaction visits across 29,492 detected bases. These are overlapping descriptive reaction observations, not independent trades. The script's MFE/MAE metrics have no transaction costs and cannot establish profitability. No reaction profile is currently approved for trading.
