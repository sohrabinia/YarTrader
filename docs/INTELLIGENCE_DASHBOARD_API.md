# TradeYar AI Operational Intelligence Command Center API Specifications

This document outlines the API specifications for the Operational Intelligence Command Center endpoints hosted by FastAPI under the `/api/intelligence/*` tags.

---

## 1. Get Intelligence Dashboard Telemetry
- **Endpoint**: `GET /api/intelligence/dashboard`
- **Description**: Returns live connection health metrics, MT5 status, and recent activity logs.
- **Request Parameters**: None
- **Response Schema**:
  ```json
  {
    "status": "Healthy",
    "mt5_connection": "CONNECTED",
    "last_activity_time": "2026-08-15T12:00:00Z",
    "recent_logs": [
      "Cognitive memory pipeline loaded and audited.",
      "MT5 Link status evaluated: CONNECTED",
      "SRE Operational diagnostics thread running."
    ]
  }
  ```

---

## 2. Get Intelligence Snapshots & Reports
- **Endpoint**: `GET /api/intelligence/reports`
- **Description**: Parses and returns recent analytical reports/snapshots compiled from disk backups.
- **Request Parameters**: None
- **Response Schema**:
  ```json
  {
    "reports_count": 1,
    "recent_reports": [
      {
        "symbol": "XAUUSD",
        "timeframe": "H1",
        "bias": "BULLISH_CONTINUATION",
        "confidence": 85,
        "reasoning": [
          "Buy-side liquidity pool swept successfully.",
          "Bullish Order Block validation confirmed."
        ]
      }
    ]
  }
  ```

---

## 3. Get Pattern Validation Outcomes
- **Endpoint**: `GET /api/intelligence/validation`
- **Description**: Returns the outcomes of validated patterns comparing AI predictions vs actual historical outcomes.
- **Request Parameters**: None
- **Response Schema**:
  ```json
  {
    "accuracy_pct": 78.4,
    "completed_checks": 1,
    "outcomes": [
      {
        "pattern": "BASE_BREAKOUT_COMPRESSION",
        "predicted": "BUY",
        "actual": "BULLISH_EXPANSION",
        "status": "SUCCESS",
        "confidence": 80.0
      }
    ]
  }
  ```

---

## 4. Get Shadow Trading Capital & Positions
- **Endpoint**: `GET /api/intelligence/shadow`
- **Description**: Exposes simulated trade executions, virtual balance, entry/exit ticks, and current drawdown.
- **Request Parameters**: None
- **Response Schema**:
  ```json
  {
    "virtual_balance": 1194.0,
    "max_drawdown_pct": 4.12,
    "total_shadow_trades": 1,
    "trades": [
      {
        "trade_id": "sh-9921",
        "symbol": "XAUUSD",
        "direction": "BUY",
        "entry_price": 1805.0,
        "exit_price": 1818.0,
        "status": "TARGET_HIT",
        "pnl_virtual": 13.0
      }
    ]
  }
  ```

---

## 5. Get AI Brain Cognitive Memory Updates
- **Endpoint**: `GET /api/intelligence/learning`
- **Description**: Exposes memory promotions, cognitive corrections, and weakness identifiers recorded under `runtime_logs/brain_memory/`.
- **Request Parameters**: None
- **Response Schema**:
  ```json
  {
    "concepts_learned": 18,
    "weakness_areas": [
      "Low-volume lateral range",
      "Macro volatility spike sessions"
    ],
    "history": [
      {
        "episode": "ep-14",
        "type": "MISTAKE_CORRECTION",
        "concept": "Lateral range break-out lag",
        "resolution": "Decoupled timing threshold by 5 candles"
      }
    ]
  }
  ```
