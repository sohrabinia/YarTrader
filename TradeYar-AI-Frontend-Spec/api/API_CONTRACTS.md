# API_CONTRACTS.md — API Contracts and Endpoint Mapping

This document establishes the strict HTTP API contract between the client frontend applications and the TradeYar AI core service. All endpoints correspond exactly to the active backend FastAPI routers.

---

## 🚦 System Health and DevOps Endpoints

### 1. Unified SRE Subsystems Health
- **Endpoint:** `GET /api/v1/health`
- **Method:** `GET`
- **Access Level:** GUEST / ANY (SRE monitoring)
- **Response Schema:**
```json
{
  "status": "HEALTHY",
  "timestamp": "2023-11-20T12:00:00Z",
  "subsystems": {
    "api": "OK",
    "mt5_connection": "OK",
    "research_worker": "RUNNING",
    "intelligence_worker": "RUNNING",
    "shadow_worker": "RUNNING",
    "memory_file_parsing": "OK"
  },
  "metrics": {
    "cpu_pct": 14.5,
    "ram_pct": 52.1,
    "ping_latency_ms": 12
  }
}
```
- **Loading Behavior:** Non-blocking background call. Display as standard neon status indicators inside `/admin` and navigation bars.

---

## 🔐 User Identity and Authentication (`/api/auth/*`)

### 1. User Sign-In
- **Endpoint:** `POST /api/auth/login`
- **Method:** `POST`
- **Payload Schema:**
```json
{
  "email": "user@example.com",
  "password": "hashed_or_plain_string_via_pbkdf2"
}
```
- **Response Schema (200 OK):**
```json
{
  "access_token": "secure_hexadecimal_or_jwt_string",
  "token_type": "bearer",
  "user": {
    "email": "user@example.com",
    "role": "USER",
    "daily_ai_limit": 10
  }
}
```
- **Error States:**
  - `400 Bad Request` or `401 Unauthorized`: Form validation failed or incorrect credentials. Trigger a temporary warning toast and clear password input field.

---

## 📈 Financial Intelligence and Shadow Trading

### 1. Market Symbol List
- **Endpoint:** `GET /api/user/markets`
- **Method:** `GET`
- **Response Schema:**
```json
{
  "symbols": ["XAUUSD", "EURUSD", "GBPUSD", "USDJPY", "BTCUSD"],
  "ceiling": 30,
  "active_count": 5
}
```

### 2. Multi-Timeframe Signals
- **Endpoint:** `GET /api/user/signals`
- **Method:** `GET`
- **Query Params:** `symbol` (e.g., `XAUUSD`)
- **Response Schema:**
```json
{
  "symbol": "XAUUSD",
  "timeframes": {
    "M1": { "trend": "NEUTRAL", "score": 50, "decision": "NO_ACTION" },
    "M5": { "trend": "BULLISH", "score": 75, "decision": "BUY" },
    "M15": { "trend": "BULLISH", "score": 82, "decision": "BUY" },
    "H1": { "trend": "NEUTRAL", "score": 45, "decision": "NO_ACTION" },
    "H4": { "trend": "BEARISH", "score": 12, "decision": "SELL" },
    "D1": { "trend": "BEARISH", "score": 8, "decision": "SELL" },
    "W1": { "trend": "NEUTRAL", "score": 50, "decision": "NO_ACTION" },
    "MN1": { "trend": "BULLISH", "score": 90, "decision": "NO_ACTION" }
  }
}
```

### 3. Shadow Trading Metrics
- **Endpoint:** `GET /api/shadow/metrics`
- **Method:** `GET`
- **Response Schema:**
```json
{
  "virtual_account": {
    "balance": 100000.00,
    "equity": 101245.50,
    "margin_used": 1500.00,
    "free_margin": 99745.50
  },
  "metrics": {
    "total_trades": 142,
    "win_rate_pct": 68.3,
    "profit_factor": 1.84,
    "max_drawdown_pct": 4.2
  }
}
```

### 4. Shadow Position History (Closed)
- **Endpoint:** `GET /api/user/history`
- **Method:** `GET`
- **Response Schema:**
```json
[
  {
    "position_id": "sh-90342",
    "symbol": "XAUUSD",
    "timeframe": "H4",
    "direction": "LONG",
    "entry_price": 2315.40,
    "exit_price": 2328.10,
    "sl": 2305.00,
    "tp": 2335.00,
    "pnl": 1270.00,
    "opened_at": "2023-11-19T10:00:00Z",
    "closed_at": "2023-11-20T04:15:00Z",
    "exit_reason": "TAKE_PROFIT"
  }
]
```

---

## 🧠 Brain and Cognitive Memory

### 1. Cognitive Overview and Learning Progress
- **Endpoint:** `GET /v1/dashboard/cognitive`
- **Method:** `GET`
- **Response Schema:**
```json
{
  "learning_statistics": {
    "episodes_processed": 1420,
    "patterns_recorded": 582,
    "hypotheses_created": 41,
    "validated_concepts": 18,
    "rejected_concepts": 23,
    "forgetting_rate_pct": 2.4
  },
  "active_weaknesses": [
    { "symbol": "BTCUSD", "reason": "High historical volatility shifts structural zones rapidly" }
  ]
}
```

---

## 💬 Interactive AI Research Assistant

### 1. Bilingual Chatbot Inquiry
- **Endpoint:** `POST /api/chat/assistant`
- **Method:** `POST`
- **Payload Schema:**
```json
{
  "question": "چرا پوزیشن خرید روی اونس طلا فعال شده است؟",
  "language": "fa"
}
```
- **Response Schema (200 OK):**
```json
{
  "response": "پوزیشن خرید روی نماد طلا (XAUUSD) در تایم‌فریم H4 به دلیل همگرایی فشار خرید ساختاری و انباشت نقدینگی در محدوده حمایتی ۲۳۱۰ دلار فعال شده است. هیچ نشانه خلاف جهتی مشاهده نمی‌شود.",
  "tokens_used": 152,
  "daily_remaining": 8
}
```
