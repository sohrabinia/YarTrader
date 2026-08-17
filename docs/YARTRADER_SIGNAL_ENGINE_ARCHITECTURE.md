# YarTrader V1.2 Professional Signal Engine Architecture

## Component Architecture
The V1.2 Professional Signal Generation Pipeline is structured into five cohesive modules:

```
                  ┌──────────────────────────────┐
                  │   Trading Knowledge Base    │
                  └──────────────┬───────────────┘
                                 │
                  ┌──────────────▼───────────────┐
                  │    Trading Style Selector    │
                  └──────────────┬───────────────┘
                                 │
                  ┌──────────────▼───────────────┐
                  │ Multi-Timeframe Context Eng  │
                  └──────────────┬───────────────┘
                                 │
                  ┌──────────────▼───────────────┐
                  │   Fractal Pattern Memory    │
                  └──────────────┬───────────────┘
                                 │
                  ┌──────────────▼───────────────┐
                  │   Professional Risk Engine   │
                  └──────────────┬───────────────┘
                                 │
                  ┌──────────────▼───────────────┐
                  │  Professional Signal Output  │
                  │     (BUY / SELL / WAIT)      │
                  └──────────────────────────────┘
```

---

## Signal Output Schema Definition

Each signal payload returned by `ProfessionalSignalEngine` contains:

```json
{
  "symbol": "XAUUSD",
  "direction": "BUY",
  "trading_style": "INTRADAY",
  "timeframe": "H1",
  "entry_zone": "$2000.00 - $2000.20",
  "stop_loss": 1990.00,
  "take_profit": 2022.00,
  "real_rr": 2.2,
  "confidence_pct": 74,
  "historical_evidence": "Historical pattern similarity matched (Success Rate: 68.5%, Weight: 0.7432).",
  "market_reasoning": [
    "Higher Timeframe (D1/H4) structure is BULLISH.",
    "Medium Timeframe (H1/M15) pullback/structure supports long setup.",
    "Lower Timeframe (M5/M1) entry trigger confirmed (BUY)."
  ],
  "invalidation_condition": "Break below recent swing low level ($1990.00).",
  "expected_holding_period": "Medium (1-8 hours)",
  "risk_level": "Medium",
  "timestamp": "2026-08-17T10:45:00.000000"
}
```
