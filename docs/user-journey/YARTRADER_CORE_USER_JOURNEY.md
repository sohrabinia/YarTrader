# YARTRADER CORE USER JOURNEY SPECIFICATION

**Document ID:** YARTRADER-USER-JOURNEY-001
**Status:** CANONICAL / AUTHORITATIVE SPECIFICATION
**Date:** September 6, 2026
**Repository:** `sohrabinia/YarTrader`
**Core Modules:** `src/Application/Services/web_dashboard.py`, `src/Application/Dashboard/auth_service.py`, `trader-terminal/src/App.jsx`

---

## 1. Executive Summary
This document specifies the canonical end-to-end user journey for YarTrader.

It maps the complete lifecycle of a user transitioning from an anonymous visitor on the landing page, through registration, email verification, credentials authentication, session establishment, application shell entry, dashboard interaction, protected route authorization, and session termination via logout.

---

## 2. Canonical User Journey Flow

```text
1. Anonymous Visitor
        │ (Visits /fa/ or /)
        ▼
2. Public Landing View (Public Landing UI)
        │ (Submits Registration Form)
        ▼
3. User Registration (POST /api/auth/register)
        │ (Creates Unverified User Record & Sends Challenge Token)
        ▼
4. Email Verification Challenge (GET /api/auth/verify-email?token={raw_token})
        │ (Consumes Token, Verifies Email Account: is_verified = True)
        ▼
5. User Login (POST /api/auth/login)
        │ (PBKDF2 Hashing, Lockout Audit Check, Issues tkn-{session_id})
        ▼
6. Authenticated Application Shell (/dashboard)
        │ (Validates Token, Loads Navigation & User Profile Badge)
        ▼
7. Terminal Command Dashboard View (GET /api/user/signals)
        │ (Renders Market State, Signals, & Risk Posture)
        ▼
8. Logout / Session Termination (POST /api/auth/logout)
        │ (Revokes Token, Clears Client LocalStorage, Redirects to /)
        ▼
9. Anonymous State Restored
```

---

## 3. Step-by-Step State Transition Contracts

### Step 1: Anonymous Access
* **Route:** `/` or `/fa`
* **Security Boundary:** Public endpoint. Unauthenticated visitors can view landing features, pricing, research blog, and user guide. Protected endpoints (`/api/user/*`, `/api/admin/*`) reject anonymous access with HTTP 401 Unauthorized.

### Step 2: User Registration
* **Endpoint:** `POST /api/auth/register`
* **Request DTO:** `{ "email": "User@Domain.Com", "password": "Password123!", "name": "Trader Name" }`
* **Processing Rules:**
  1. Invokes `normalize_email` to trim whitespace and lowercase email (`user@domain.com`).
  2. Generates PBKDF2-SHA256 password hash (600,000 iterations).
  3. Creates user record with `is_verified: False`.
  4. Generates single-use cryptographically random verification token (`vkn-{urlsafe_32}`).
  5. Stores SHA-256 token hash in `runtime_logs/verification_tokens.json`.
  6. Dispatches verification challenge via `send_saas_email`.
* **Response DTO:** `{ "status": "Success", "message": "User registered successfully...", "user": { "email": "user@domain.com", "name": "Trader Name", "role": "USER", "is_verified": false } }`

### Step 3: Email Verification Challenge
* **Endpoint:** `GET /api/auth/verify-email?token={raw_token}`
* **Processing Rules:**
  1. Hashes `raw_token` via SHA-256 and looks up record in `verification_tokens.json`.
  2. Verifies token is not expired (24-hour TTL) and has not been used.
  3. Marks token `used: True` (single-use enforcement).
  4. Updates user record to `is_verified: True`.
* **Error Behavior:** Invalid, expired, or reused tokens return HTTP 400 Bad Request.

### Step 4: User Login
* **Endpoint:** `POST /api/auth/login`
* **Request DTO:** `{ "email": "user@domain.com", "password": "Password123!" }`
* **Processing Rules:**
  1. Normalizes email.
  2. Checks lockout audit threshold (max 5 failed attempts per 15 min).
  3. Verifies account `is_verified == True`. Unverified accounts raise HTTP 401 with `"Account is not verified"`.
  4. Validates password hash in constant time (`hmac.compare_digest`).
  5. If user has a legacy 100,000-iteration hash, transparently rehashes password to 600,000 iterations and persists updated hash.
  6. Issues active session token (`tkn-{hex_24}`).
* **Response DTO:** `{ "status": "Success", "session_token": "tkn-...", "user": { "email": "user@domain.com", "name": "Trader Name", "role": "USER" } }`

### Step 5: Authenticated Application Shell & Dashboard
* **Route:** `/dashboard`
* **Session Validation:** Frontend transmits session token via `Authorization: Bearer tkn-...` or query parameter. API Gateway validates active token against `AuthService.active_sessions`.
* **State Management:** `localStorage.getItem('yartrader_token')` stores session token. Profile badge renders `Name (Role)`.

### Step 6: Logout & Session Termination
* **Endpoint:** `POST /api/auth/logout`
* **Processing Rules:**
  1. Deletes token from `AuthService.active_sessions`.
  2. Clears client `yartrader_token`, `yartrader_role`, `yartrader_name` from `localStorage`.
  3. Redirects user to `/` landing view.
* **Post-Logout Security:** Reusing a revoked token on protected routes returns HTTP 401 Unauthorized.

---

## 4. Protected Route Authorization Matrix

| Endpoint Route | Unauthenticated | Verified User | Admin Role |
| -------------- | :-------------: | :-----------: | :--------: |
| `/api/public/metrics` | 200 OK | 200 OK | 200 OK |
| `/api/blog` | 200 OK | 200 OK | 200 OK |
| `/api/user/signals` | 401 Unauthorized | 200 OK | 200 OK |
| `/api/backtest/run` | 401 Unauthorized | 200 OK | 200 OK |
| `/api/prop/config` | 401 Unauthorized | 200 OK | 200 OK |
| `/api/admin/symbols` | 401 Unauthorized | 403 Forbidden | 200 OK |
| `/api/devops/status` | 401 Unauthorized | 403 Forbidden | 200 OK |

---

## 5. Phase 5 Completion Verdict

```text
PHASE 5 = PASS
```

**Reasoning:** The canonical core user journey has been fully established, aligned with Phase 1 ownership boundaries, and documented in `docs/user-journey/YARTRADER_CORE_USER_JOURNEY.md`. Endpoints in `web_dashboard.py` delegate authentication and verification directly to `global_auth_service`. Comprehensive E2E integration tests in `tests/YarTrader.Tests/Services/test_core_user_journey_phase5.py` verify registration, email verification, unverified login rejection, verified login, lockout, protected endpoint authorization, and logout session revocation. Full pytest suite (1853+ passed) and trader-terminal build verify zero regressions.
