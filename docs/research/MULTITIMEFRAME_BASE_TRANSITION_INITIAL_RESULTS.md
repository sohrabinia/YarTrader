# Initial Results — Multi-Timeframe Base & Transition Study

Date: 2026-10-10  
Status: research-only; not approved for live execution  
Data: broker-specific XAUUSD OHLC history from Alpari-MT5-Demo  
Full machine-readable report: runtime_logs\mt5_gold_history_full\multitimeframe_base_transition_study.json

## Coverage

The sampled detector produced 25,504 departure events: MN1 11, W1 54, D1 280, H4 1,084, H1 3,206, M15 6,476, M5 11,826, and M1 2,567. The M1 sample is capped to the latest 600,000 bars; other timeframes use the available history. Scan steps are deliberately greater than one on some timeframes, so these are not exhaustive base counts.

The hierarchy mapped 2,934 events with at least one contained, already-confirmed child base. 2,203 events had aligned children and 1,565 had opposing children; these groups overlap because an event may contain both aligned and opposing structures.

## Baseline trade simulation

Entries occur at the next bar open after a confirmed departure. The fixed_2R variant uses a stop beyond the far edge of the base plus 0.1 ATR, a 2R target, and a 24-bar maximum hold. The next_base variant targets the nearest already-known base zone in the departure direction. Same-bar stop/target touches resolve conservatively as stop-first.

The cost-adjusted metric subtracts 0.05 ATR per completed trade as a rough round-trip cost proxy. Actual spread, commission, and slippage are not included. Values below are mean net R proxy, not validated expectancy.

| Timeframe | fixed_2R overall | fixed_2R last 30% | next_base overall | next_base last 30% |
|---|---:|---:|---:|---:|
| MN1 | +0.6749 (n=11) | +0.5587 (n=4) | -0.0055 (n=7) | +0.0336 (n=2) |
| W1 | +0.3446 (n=54) | +0.5294 (n=17) | -0.0714 (n=32) | -0.0128 (n=10) |
| D1 | +0.2212 (n=280) | +0.2214 (n=84) | -0.0384 (n=193) | -0.0593 (n=62) |
| H4 | +0.0314 (n=1,084) | +0.0228 (n=326) | -0.0468 (n=1,004) | -0.0315 (n=298) |
| H1 | +0.0322 (n=3,206) | +0.0172 (n=962) | -0.0585 (n=3,029) | -0.0561 (n=901) |
| M15 | -0.0262 (n=6,465) | -0.0084 (n=1,940) | -0.0178 (n=6,248) | -0.0445 (n=1,875) |
| M5 | -0.0207 (n=11,805) | -0.0348 (n=3,547) | +0.0357 (n=11,467) | -0.0568 (n=3,457) |
| M1 | -0.0480 (n=2,564) | -0.0475 (n=771) | -0.0408 (n=2,464) | -0.0358 (n=771) |

## What these results say so far

1. D1 fixed_2R is the clearest provisional candidate in this first pass: its mean net R proxy is similar in the first 70% and last 30% of events. This is not yet independent validation, and actual broker costs may remove the edge.
2. H4 and H1 fixed_2R are near flat after the ATR-cost proxy; their last-30% results are weaker than D1.
3. M5 next_base looks positive over the full sample but turns negative in the last 30% (-0.0568R proxy). Do not advance it as a strategy based on the full-sample result.
4. The next-base target can have a high hit rate while still producing negative R expectancy because targets may be too close relative to risk. Hit rate alone is not sufficient.
5. Compact pauses form during travel between bases, but follow-through is not consistently aligned with the original departure: H4 56 aligned vs 63 opposed, H1 342 vs 406, M15 705 vs 788, M5 1,116 vs 1,196. These counts are descriptive and depend on the current pause definition.
6. About 42–48% of H4 through M1 transition labels are ambiguous same-bar outcomes. OHLC bars cannot reliably order all intrabar events; this needs more careful treatment or finer-grained execution data.

## Recommended next validation gate

Keep the nested-base context and closed higher-timeframe trend/volatility snapshots. Pre-register D1 fixed_2R as a candidate for a stricter validation only; do not tune its thresholds on the last-30% slice. Next, use a truly untouched chronological period, split long and short results, apply actual historical spread/commission/slippage, and account for correlated/overlapping trades. No live signal or order execution should be enabled until the candidate survives that gate.
