# API DOCUMENTATION
**TradeYar AI Version 1 REST API Catalog**

All production endpoints reside under the `/api/v1` version prefix. Standard response formats are serialized as JSON.

---

## 1. Authentication Services

### 1.1 User Registration
* **Endpoint**: `POST /api/v1/auth/register`
* **Access**: Public
* **Payload**:
  ```json
  {
    "email": "user@tradeyar.ai",
    "password": "Password123",
    "role": "USER"
  }
  ```
* **Success Response (200 OK)**:
  ```json
  {
    "status": "Success",
    "message": "User registered successfully.",
    "email": "user@tradeyar.ai"
  }
  ```

### 1.2 Secure User Login
* **Endpoint**: `POST /api/v1/auth/login`
* **Access**: Public
* **Payload**:
  ```json
  {
    "email": "user@tradeyar.ai",
    "password": "Password123"
  }
  ```
* **Success Response (200 OK)**:
  *Sets HTTP-only secure session cookie `tradeyar_session`.*
  ```json
  {
    "status": "Success",
    "token": "a1f3de8c...",
    "user": {
      "email": "user@tradeyar.ai",
      "role": "USER",
      "subscription_plan": "FREE"
    }
  }
  ```

### 1.3 User Logout
* **Endpoint**: `POST /api/v1/auth/logout`
* **Access**: Authenticated Session
* **Success Response (200 OK)**:
  *Clears cookie `tradeyar_session` and revokes token.*
  ```json
  {
    "status": "Success",
    "message": "Logged out successfully."
  }
  ```

---

## 2. Market Intelligence & Analysis

### 2.1 Get Multi-Tier Market Analysis
* **Endpoint**: `GET /api/v1/analysis`
* **Access**: Authenticated (Role-Restricted)
* **Response for USER (FREE)**:
  ```json
  {
    "tier": "FREE",
    "symbol": "XAUUSD",
    "bias": "Bullish",
    "confidence": "78%",
    "message": "Upgrade to PRO or PREMIUM to view advanced technical metrics...",
    "indicators": "RESTRICTED",
    "reasoning": "RESTRICTED"
  }
  ```
* **Response for PREMIUM**:
  ```json
  {
    "tier": "PREMIUM",
    "symbol": "XAUUSD",
    "bias": "Bullish",
    "confidence": "78%",
    "indicators": {
      "sma_20": 2680.5,
      "ema_12": 2682.4,
      "rsi": 58.4
    },
    "reasoning": [
      "Demand accumulation is strong.",
      "Volume supports bullish trend continuation."
    ],
    "risk_disclosure": "Financial trading contains high risks..."
  }
  ```

---

## 3. AI Support Assistant

### 3.1 Process Chat Query
* **Endpoint**: `POST /api/v1/support/query`
* **Access**: Authenticated (Enforces Cost-Control Quota Limits)
* **Payload**:
  ```json
  {
    "query": "Tell me about risk",
    "language": "en"
  }
  ```
* **Success Response (200 OK)**:
  ```json
  {
    "reply": "Trading financial speculation involves high capital risks..."
  }
  ```
* **Error Response (429 Too Many Requests)**:
  ```json
  {
    "detail": "AI limit reached for tier USER (10 requests/day). Please upgrade your plan."
  }
  ```

---

## 4. Administration

### 4.1 List Users
* **Endpoint**: `GET /api/v1/users`
* **Access**: ADMIN role only
* **Success Response (200 OK)**:
  ```json
  [
    {
      "email": "user@tradeyar.ai",
      "role": "USER",
      "status": "ACTIVE"
    }
  ]
  ```

### 4.2 Update User Role (Monetization Trigger)
* **Endpoint**: `POST /api/v1/users/update-role`
* **Access**: ADMIN role only
* **Payload**:
  ```json
  {
    "email": "user@tradeyar.ai",
    "role": "PREMIUM"
  }
  ```
* **Success Response (200 OK)**:
  *Generates invoice, logs transactions, sends email confirmation, and dispatches Telegram notification.*
  ```json
  {
    "status": "Success",
    "message": "User user@tradeyar.ai updated to role PREMIUM."
  }
  ```
