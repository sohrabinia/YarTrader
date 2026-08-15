# API Contracts Specification - Separation of Concerns

All frontend requests must execute through versioned REST endpoints or authenticated WebSockets, adhering strictly to the contract defined below.

---

## 1. Authentication & Session Management
- **Endpoint:** `POST /api/v1/auth/login`
- **Method:** `POST`
- **Request Payload:**
  ```json
  {
    "username": "string",
    "password": "hashed_string"
  }
  ```
- **Response Payload:**
  ```json
  {
    "token": "string",
    "role": "USER | PRO | PREMIUM | ADMIN",
    "expires_at": "ISO-8601 UTC"
  }
  ```

---

## 2. Research Signals Retrieval
- **Endpoint:** `GET /api/v1/research/signals`
- **Method:** `GET`
- **Query Params:**
  - `symbol` (optional, default: `XAUUSD`)
  - `limit` (optional, default: `50`)
- **Response Payload:**
  ```json
  {
    "status": "success",
    "signals": [
      {
        "signal_id": "string",
        "symbol": "string",
        "timeframe": "string",
        "state": "RESEARCH | APPROVED | BLOCKED | FAILED",
        "reasons": ["string"],
        "confidence": 0.85,
        "timestamp": "ISO-8601 UTC"
      }
    ]
  }
  ```
