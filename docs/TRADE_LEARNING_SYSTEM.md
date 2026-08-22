# YarTrader Trade Learning & Adaptive Parameter System

**Version:** 1.2.0
**Scope:** Post-Trade Analysis, Pattern Memory, Evidence-Based Learning, Data Leakage Protection, and Safety Safeguards

---

## 1. Post-Trade Outcome Analysis

Upon position closure, the `OutcomeAnalyzer` evaluates actual exit price, planned targets, and price excursion metrics (Max Favorable Excursion `MFE` and Max Adverse Excursion `MAE`) to classify trade quality:

- **`GOOD_ENTRY`**: Minimal drawdown (`MAE < 0.3 * Risk`), target reached cleanly.
- **`SL_TOO_TIGHT`**: Stopped out under normal market noise.
- **`TP_TOO_FAR`**: Reached 80%+ of distance to TP before reversing to hit SL.
- **`CORRECT_DIRECTION_BAD_TIMING`**: Favorable expansion occurred, but initial stop loss was breached first.
- **`TREND_FAILURE`**: Immediate adverse movement without favorable expansion.

---

## 2. Evidence-Based Adaptation Governance

Learning updates and candidate parameter adjustments are governed by `EvidenceBasedAdaptationEngine`:

1. **Sample Size Protection Gate (`minimum_sample_size` = 5):**
   - Candidate adaptations derived from fewer than 5 sample trades are classified as `OBSERVE_ONLY`. No decision parameters are updated.
2. **Data Leakage & Look-Ahead Protection:**
   - Every adaptation record logs `source_trade_ids`, `source_timestamp_range`, `feature_snapshot_timestamp`, and `decision_timestamp`. Features cannot incorporate post-decision market data.
3. **Absolute Safety Boundary Protection:**
   - Adapters and learning algorithms are strictly prohibited from modifying protected safety parameters (`LIVE_TRADING_ENABLED`, `DemoExecutionGate`, `MetaTraderSafetyGate`, `autonomous_demo_trading_enabled`). Attempting to alter these parameters raises an immediate `ValidationException`.
4. **Versioning & Rollback:**
   - Every parameter adaptation creates a `VersionedAdaptationUpdate` tracking `configuration_version`, `previous_version`, and `rollback_reference`.

---

## 3. Storage Policy Compliance

All trade journals (`trade_journal.json`), learning adaptation records (`learning_adaptations.json`), and execution logs are persisted under `YarTraderStorageManager` roots (`TradeYarStorageRoot/Logs/`).
