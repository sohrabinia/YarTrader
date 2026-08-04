# TradeYar AI Performance Validation & Metrics Model

All metrics computed by the validation engine rely on deterministic, traceable formulas.

## Metric Calculations Reference

1. **Win Rate**:
   $$\text{WinRate} = \frac{\text{Wins}}{\text{TotalTrades}} \times 100$$
2. **Directional Accuracy**:
   $$\text{DirectionAccuracy} = \frac{\text{CorrectDirections}}{\text{TotalTrades}} \times 100$$
3. **Timing Accuracy**:
   $$\text{TimingAccuracy} = \frac{\sum \min(1.0, \frac{\text{ActualDistance}}{\text{TargetDistance}})}{\text{TotalTrades}} \times 100$$
4. **Average Risk/Reward**:
   $$\text{AvgRR} = \frac{\sum \frac{\text{TakeProfitDistance}}{\text{StopLossDistance}}}{\text{TotalTrades}}$$
5. **Peak-to-Trough Drawdown**:
   $$\text{MaxDrawdown} = \max\left(\frac{\text{PeakBalance} - \text{CurrentBalance}}{\text{PeakBalance}}\right) \times 100$$

Every computed metrics dictionary exposes the source trade IDs, ensuring total calculation transparency.
