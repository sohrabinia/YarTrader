# API GUIDE
# TradeYar AI v3.2 — Enterprise Productization Phase

This guide defines the REST API contract, endpoints, payload JSON formats, and authentication schemas of **TradeYar AI v3.2**.

---

## 1. Authentication & Security

All private endpoints require a Bearer JWT Token passed in the `Authorization` header.

```http
Authorization: Bearer <your-jwt-token>
```

---

## 2. Core REST Endpoints

### 2.1. Authentication System

#### `POST /api/v1/auth/register`
Registers a new user profile.
- **Request Body:**
  ```json
  {
    "email": "researcher@tradeyar.ai",
    "password": "SuperSecurePassword123",
    "role": "Researcher"
  }
  ```
- **Response (200 OK):**
  ```json
  {
    "status": "success",
    "message": "User registered successfully."
  }
  ```

#### `POST /api/v1/auth/login`
Logs in a user and returns an access token.
- **Request Body:**
  ```json
  {
    "email": "researcher@tradeyar.ai",
    "password": "SuperSecurePassword123"
  }
  ```
- **Response (200 OK):**
  ```json
  {
    "access_token": "eyJhbGciOiJIUzI1NiIsIn...",
    "token_type": "bearer",
    "role": "Researcher"
  }
  ```

---

### 2.2. Productive Dashboard Data

#### `GET /v1/dashboard/overview`
Retrieves system overview health metrics.
- **Response (200 OK):**
  ```json
  {
    "system_health": "Healthy",
    "active_operating_mode": "Passive Research",
    "last_validated": "2023-11-20 12:00:00",
    "apes_boundary_passed": true
  }
  ```

#### `GET /v1/dashboard/cognitive`
Retrieves live cognitive learning progress metrics.
- **Response (200 OK):**
  ```json
  {
    "cognitive": {
      "Learning Progress": {
        "Validated Concepts": 320,
        "Episodes Studied": 125,
        "Patterns Found": 4820,
        "Hypotheses Tested": 1840,
        "Rejected Concepts": 42
      },
      "Brain Weakness": {
        "Highest Failure Areas": ["XAUUSD Trend Shifts"],
        "Unknown Behaviors": ["Abrupt spread anomalies"],
        "Research Priorities": [
          {
            "Topic": "High volatility pattern clustering",
            "Priority": "CRITICAL"
          }
        ]
      }
    }
  }
  ```

---

### 2.3. SRE, Health, & DevOps Status

#### `GET /api/devops/status`
Retrieves health status of underlying background services and adapters.
- **Response (200 OK):**
  ```json
  {
    "service_status": "ONLINE",
    "runtime_health": "GREEN",
    "mt5_status": "CONNECTED_FALLBACK",
    "worker_status": "RUNNING"
  }
  ```

#### `GET /api/devops/metrics`
SRE system metrics tracker.
- **Response (200 OK):**
  ```json
  {
    "pipeline_latency_ms": 142.5,
    "api_response_ms": 12.1,
    "memory_used_mb": 118.4,
    "thread_count": 14
  }
  ```

---

### 2.4. Shadow Performance & Statistics

#### `GET /api/shadow/metrics`
Retrieves stats of simulated trades managed by the Shadow Trading Engine.
- **Response (200 OK):**
  ```json
  {
    "total_positions_count": 1250,
    "active_positions_count": 4,
    "closed_positions_count": 1246,
    "win_positions_count": 820,
    "loss_positions_count": 430,
    "win_rate_pct": 65.6
  }
  ```

---

### 2.5. Conversational Explainer System

#### `GET /api/intelligence/explain/{decision_id}`
Returns a semantic explanation for a simulated trade or omission.
- **Query Parameters:**
  - `question`: Explainer question keywords.
  - `lang`: Target localization language (`fa`, `en`, `ar`, or `tr`).
- **Response (200 OK):**
  ```json
  {
    "question": "چرا این معامله را باز کردی؟",
    "lang": "fa",
    "explanation": "این موقعیت فرضی بر پایه انطباق ۸۵٪ الگوی جاری با الگوهای موفق ثبت شده در تاریخ ۲۰۰۲ لغایت ۲۰۱۲ بر روی طلا تایید شده است."
  }
  ```
