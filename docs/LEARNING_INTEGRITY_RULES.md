# TradeYar AI — Learning Integrity Rules

To protect the Market Discovery Brain from self-deception, overfitting, and unscientific generalizations, these mathematical and architectural constraints are strictly enforced across the learning pipeline.

## 1. Rules of Learning and Generalization

### 1.1 No Learning from Unfinished Replay
- Memory updates are strictly prohibited from evaluating open, active virtual simulation trades.
- No pattern outcome can be recorded in Pattern Memory until the simulated trade has been definitively closed by Stop Loss, Take Profit, or maximum duration termination.

### 1.2 Multi-Factor Sample-Size Validation
- No conceptual pattern or market rule can be promoted to Concept Memory based on weak samples.
- The minimum sample-size check is defined as:
  $$\text{Sample Size} \ge 5\text{ matching occurrences}$$
- If the sample size is below this threshold, the reasoning quality score receives a proportional mathematical penalty.

### 1.3 Detection of "Lucky Wins" (Accidental Success)
- A simulated trade result of SUCCESS with high maximum adverse excursion (MAM) approaching the stop loss boundary is flagged as a potential "Lucky Win".
- The Judge Brain must analyze whether the trade close was accidental by comparing the entry reasoning similarity score against the actual excursion path.

### 1.4 Protection Against Future Leakage
- Replay tests and simulated decisions are strictly sandboxed.
- At decision timestamp $T$, the simulation engine must have zero access to price information, candles, ticks, or events with timestamp $t > T$.
