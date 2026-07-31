# Shadow Trading Engine Roadmap
*TradeYar AI — Strategic Architecture & Capability Audit*

---

## 1. Current Capability Analysis

* **Exists?** Partially.
* **Completeness**: 20%.
* **Current State**: The system includes a file called `src/Application/Shadow/engine.py` which exposes a `ShadowModeEngine`. However, this is currently a pass-through descriptive-analytical manager. It executes a dry-run passive research pipeline but lacks any trade execution logic, position tracking, virtual margin computation, or account states (Balance, Equity).
* **The Missing Gap**: To become a viable commercial product, the Shadow Trading Engine must support a high-fidelity **Virtual Broker Account** and manage the full lifecycle of virtual trading positions based on live, streamed market rates from the MT5 provider.

---

## 2. Virtual Account Structure Design

The proposed Virtual Account layer will run within the runtime memory space and persist its state periodically to `runtime_logs/virtual_portfolio.json`.

### A. Virtual Account Schema
```json
{
  "account_id": "vacc-demo-12345",
  "base_currency": "USD",
  "balance": 10000.00,
  "equity": 10000.00,
  "margin_used": 0.00,
  "free_margin": 10000.00,
  "margin_level_pct": 100.00,
  "leverage": 100.00,
  "positions": []
}
```

### B. Virtual Position Schema
```json
{
  "position_id": "vpos-gold-8831a",
  "symbol": "XAUUSD",
  "direction": "BUY",
  "volume_lots": 0.10,
  "entry_price": 2045.50,
  "entry_time": "2026-03-31T14:30:00Z",
  "current_price": 2045.50,
  "stop_loss": 2035.00,
  "take_profit": 2065.00,
  "swap_accumulated": 0.00,
  "commission": -2.00,
  "floating_pnl": 0.00,
  "evidence": {
    "reason_text": "Price sequence continuation pattern detected on H1 structure.",
    "matched_historical_pattern_id": "pat-gold-44123",
    "similar_historical_cases": 420,
    "historical_win_ratio_pct": 65.70,
    "confidence_score": 0.65
  }
}
```

---

## 3. The High-Fidelity Virtual Trade Lifecycle

To ensure non-trading passive safety (adhering strictly to APES-FIN rules), the shadow engine operates entirely in-memory or on local database storage with zero active communication with a real broker's trade servers.

```
       [Cognitive Brain Hypothesis Formulated]
                         │
                         ▼
           ┌───────────────────────────┐
           │     Virtual Entry         │  ◄── Applies real-time Spread, slippage
           └─────────────┬─────────────┘      and trading commissions
                         │
                         ▼
           ┌───────────────────────────┐
           │    Live Monitoring        │  ◄── Listens to live read-only ticks
           └─────────────┬─────────────┘      updates Floating PnL/Equity
                         │
                         ▼
           ┌───────────────────────────┐
           │   Position Management     │  ◄── Computes virtual margin, trailing
           └─────────────┬─────────────┘      stops or dynamic adjustments
                         │
                         ▼
           ┌───────────────────────────┐
           │     Virtual Close         │  ◄── Exits via TP/SL hit or cognitive
           └─────────────┬─────────────┘      WAIT command. Applies exit spread.
                         │
                         ▼
           ┌───────────────────────────┐
           │    Result Evaluation      │  ◄── Independent Judge Brain analyzes
           └─────────────┬─────────────┘      luck vs skill & reasoning quality
                         │
                         ▼
           ┌───────────────────────────┐
           │        Learning           │  ◄── Consolidates outcome to Experience
           └───────────────────────────┘      Memory and updates Pattern statistics
```

---

## 4. Required Implementation Plan (Technical Roadmap)

To implement this engine without disrupting any existing validated systems, we recommend a 3-step roll-out:

### Phase 4A: Core Virtual Portfolio Layer (10 Developer-Days)
* Implement `VirtualBrokerAccount` and `VirtualPositionManager` classes under `src/Application/Shadow/portfolio.py`.
* Map account calculations:
  $$\text{Floating PnL} = (\text{Current Price} - \text{Entry Price}) \times \text{Lots} \times \text{Contract Size} \quad (\text{for BUY})$$
  $$\text{Equity} = \text{Balance} + \text{Floating PnL} + \text{Commissions}$$
  $$\text{Margin Used} = \frac{\text{Current Price} \times \text{Lots} \times \text{Contract Size}}{\text{Leverage}}$$

### Phase 4B: Live Lifecycle Worker (8 Developer-Days)
* Add a thread-safe background loop in `ShadowModeEngine` that polls the MT5 provider's active price ticks.
* Check active virtual positions against current tick high/low values to trigger automatic take-profit or stop-loss closes.
* Apply transaction costs dynamically (e.g. 2.0 pips spread, $2.00 commission per lot).

### Phase 4C: UI Dashboard Exposure (5 Developer-Days)
* Expose virtual portfolio telemetry via a secure `/api/v1/shadow/portfolio` endpoint.
* Build a responsive front-end tab in the Web Dashboard showing open virtual positions, historical virtual equity curve, and brain evidence links.
