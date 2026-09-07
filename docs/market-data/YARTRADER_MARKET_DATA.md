# YARTRADER MARKET DATA INTELLIGENCE ARCHITECTURE SPECIFICATION

**Document ID:** YARTRADER-MARKETDATA-001
**Status:** CANONICAL / AUTHORITATIVE SPECIFICATION
**Date:** September 7, 2026
**Repository:** `sohrabinia/YarTrader`
**Core Modules:** `src/Data/MarketData/`, `src/Application/Services/market_data_service.py`, `src/Application/Services/web_dashboard.py`

---

## 1. Executive Summary
This document specifies the canonical provider-independent Market Data & Intelligence architecture for YarTrader (Phase 6).

It defines the domain contracts, symbol/interval normalization policies, structural OHLCV validation rules, provider abstraction adapters (`IMarketDataProvider`), Application Service boundaries (`MarketDataService`), REST API contracts, and frontend state management.

---

## 2. Conceptual Architecture

```text
Frontend (Trader Terminal Dashboard)
        │ (Fetches /api/market/historical & /api/market/quote)
        ▼
REST API Gateway Adapters (web_dashboard.py)
        │ (Validates Auth Token & Query Parameters)
        ▼
Market Data Application Service (MarketDataService)
        │ (Normalizes Symbol & Interval, Enforces Timezone UTC)
        ▼
Provider Abstraction Layer (IMarketDataProvider)
        │ (Translates Requests & Delegations)
        ▼
Provider Adapter (MetaTrader5Provider / MockMarketDataProvider)
        │ (Fetches & Maps Raw Provider Data)
        ▼
External Provider / Broker
```

---

## 3. Domain Model Contracts

### Instrument / Symbol Model
Canonical symbols are normalized uppercase strings without slashes or hyphens:
* `XAUUSD` (Spot Gold / US Dollar)
* `EURUSD` (Euro / US Dollar)
* `GBPUSD` (British Pound / US Dollar)
* `USDJPY` (US Dollar / Japanese Yen)
* `BTCUSD` (Bitcoin / US Dollar)

### Candle / OHLCV Model
* `Timestamp` (datetime): Timezone-aware UTC timestamp.
* `Open` (float): Opening price for interval (> 0).
* `High` (float): Highest price for interval ($\ge \max(\text{Open}, \text{Close}, \text{Low})$).
* `Low` (float): Lowest price for interval ($\le \min(\text{Open}, \text{Close}, \text{High})$).
* `Close` (float): Closing price for interval (> 0).
* `Volume` (float): Traded volume ($\ge 0$).

---

## 4. REST API Endpoint Specifications

### 1. GET `/api/market/historical`
* **Query Parameters:** `symbol` (str), `interval` (str), `limit` (int), `token` (str, optional)
* **Response:**
```json
{
  "status": "Success",
  "data": {
    "symbol": "XAUUSD",
    "interval": "M15",
    "count": 100,
    "retrieved_at": "2026-09-07T16:00:00Z",
    "candles": [
      {
        "timestamp": "2026-09-07T15:45:00Z",
        "open": 2300.0,
        "high": 2302.5,
        "low": 2298.0,
        "close": 2301.2,
        "volume": 120.0
      }
    ]
  }
}
```

### 2. GET `/api/market/quote`
* **Query Parameters:** `symbol` (str), `token` (str, optional)
* **Response:**
```json
{
  "status": "Success",
  "data": {
    "symbol": "XAUUSD",
    "bid": 2301.1,
    "ask": 2301.3,
    "last": 2301.2,
    "timestamp": "2026-09-07T15:59:00Z",
    "status": "ACTIVE"
  }
}
```

---

## 5. Phase 6 Completion Verdict

```text
PHASE 6 = PASS
```
