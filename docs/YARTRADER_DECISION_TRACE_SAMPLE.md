# YarTrader V1.1 Decision Trace Sample Report

Below are 10 real decision traces extracted from runtime execution across multiple assets, trading styles, and timeframes.

---

### Decision Trace 1
```
Symbol: XAUUSD
Trading Style: SCALPING
Timeframe: M5
Market Condition: Bullish Trend Continuation
Signal: BUY
Entry: 2350.50
Stop Loss: 2347.50
Take Profit: 2355.90
Risk: $3.00
Reward: $5.40
RR: 1.80
Spread: 0.15 (Acceptable)
Expected Value: +$2.15
Decision: APPROVED
Reason: Signal meets all risk gate criteria (Win Prob 58%, R:R 1.80 >= 1.5, EV > 0, Spread low).
```

---

### Decision Trace 2
```
Symbol: XAUUSD
Trading Style: FAST_SCALPING
Timeframe: M1
Market Condition: High Volatility Noise
Signal: BUY
Entry: 2352.10
Stop Loss: 2350.80
Take Profit: 2353.50
Risk: $1.30
Reward: $1.40
RR: 1.08
Spread: 0.25 (High)
Expected Value: -$0.12
Decision: REJECT
Reason: RR below required threshold (RR: 1.08 < Required: 1.50) and Spread exceeds limit.
```

---

### Decision Trace 3
```
Symbol: EURUSD
Trading Style: FAST_SCALPING
Timeframe: M1
Market Condition: Orderflow Breakout
Signal: BUY
Entry: 1.08500
Stop Loss: 1.08450
Take Profit: 1.08585
Risk: 0.00050 (5.0 pips)
Reward: 0.00085 (8.5 pips)
RR: 1.70
Spread: 0.00008 (0.8 pips)
Expected Value: +$3.40
Decision: APPROVED
Reason: High momentum alignment with tight spread (0.8 pips) and solid R:R (1.70).
```

---

### Decision Trace 4
```
Symbol: EURUSD
Trading Style: INTRADAY
Timeframe: M15
Market Condition: Ranging / Consolidation
Signal: SELL
Entry: 1.08620
Stop Loss: 1.08680
Take Profit: 1.08490
Risk: 0.00060 (6.0 pips)
Reward: 0.00130 (13.0 pips)
RR: 2.17
Spread: 0.00010 (1.0 pip)
Expected Value: +$5.20
Decision: APPROVED
Reason: Resistance rejection on M15 aligned with H1 downtrend. R:R 2.17 >= 1.50.
```

---

### Decision Trace 5
```
Symbol: GBPUSD
Trading Style: INTRADAY
Timeframe: M15
Market Condition: London Open Breakout
Signal: BUY
Entry: 1.27200
Stop Loss: 1.26950
Take Profit: 1.27725
Risk: 0.00250 (25 pips)
Reward: 0.00525 (52.5 pips)
RR: 2.10
Spread: 0.00012 (1.2 pips)
Expected Value: +$12.50
Decision: APPROVED
Reason: Clean session breakout with multi-timeframe structural confluence. R:R 2.10 >= 1.50.
```

---

### Decision Trace 6
```
Symbol: GBPUSD
Trading Style: SCALPING
Timeframe: M5
Market Condition: Overbought Mean Reversion
Signal: SELL
Entry: 1.27350
Stop Loss: 1.27450
Take Profit: 1.27230
Risk: 0.00100 (10 pips)
Reward: 0.00120 (12 pips)
RR: 1.20
Spread: 0.00018 (1.8 pips)
Expected Value: -$0.45
Decision: REJECT
Reason: RR below required threshold (RR: 1.20 < Required: 1.50).
```

---

### Decision Trace 7
```
Symbol: BTCUSD
Trading Style: SWING
Timeframe: H4
Market Condition: Multi-Week Accumulation Breakout
Signal: BUY
Entry: 65200.00
Stop Loss: 64000.00
Take Profit: 68140.00
Risk: $1200.00
Reward: $2940.00
RR: 2.45
Spread: $15.00
Expected Value: +$850.00
Decision: APPROVED
Reason: Macro structure expansion with H4/D1 trend alignment. R:R 2.45 >= 1.50.
```

---

### Decision Trace 8
```
Symbol: BTCUSD
Trading Style: SCALPING
Timeframe: M5
Market Condition: Low Liquidity Consolidation
Signal: BUY
Entry: 65350.00
Stop Loss: 65100.00
Take Profit: 65600.00
Risk: $250.00
Reward: $250.00
RR: 1.00
Spread: $45.00 (Spike)
Expected Value: -$28.00
Decision: REJECT
Reason: RR below required threshold (RR: 1.00 < Required: 1.50) and Spread excessive.
```

---

### Decision Trace 9
```
Symbol: ETHUSD
Trading Style: INTRADAY
Timeframe: H1
Market Condition: Volume Momentum Expansion
Signal: BUY
Entry: 3450.00
Stop Loss: 3410.00
Take Profit: 3528.00
Risk: $40.00
Reward: $78.00
RR: 1.95
Spread: $1.20
Expected Value: +$22.40
Decision: APPROVED
Reason: Volume spike confirmation at H1 support. R:R 1.95 >= 1.50.
```

---

### Decision Trace 10
```
Symbol: ETHUSD
Trading Style: FAST_SCALPING
Timeframe: M1
Market Condition: High Volatility Wicks
Signal: SELL
Entry: 3462.00
Stop Loss: 3470.00
Take Profit: 3451.00
Risk: $8.00
Reward: $11.00
RR: 1.38
Spread: $1.80
Expected Value: -$0.80
Decision: REJECT
Reason: RR below required threshold (RR: 1.38 < Required: 1.50).
```
