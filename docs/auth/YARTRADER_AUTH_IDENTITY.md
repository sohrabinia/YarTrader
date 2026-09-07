# YARTRADER AUTHENTICATION & IDENTITY SPECIFICATION

**Document ID:** YARTRADER-AUTH-001
**Status:** CANONICAL / AUTHORITATIVE SPECIFICATION
**Date:** September 6, 2026
**Repository:** `sohrabinia/YarTrader`
**Core Modules:** `src/Application/Dashboard/auth_service.py`, `auth_repo.py`, `telegram_auth.py`, `web_dashboard.py`

---

## 1. Purpose
This specification defines the canonical authentication, user identity, password security, email verification lifecycle, and session token architecture for YarTrader.

Phase 4 unifies user registration, credential verification, email normalization, lockout policies, and Telegram authentication widget integration into a production-grade identity foundation.

---

## 2. Component Ownership Architecture

Authentication responsibilities are strictly separated across 4 distinct layers:

```text
HTTP REST API Gateway (web_dashboard.py)
        │
        ▼
Application Auth Service (auth_service.py) ──► Email Delivery Boundary (send_saas_email)
        │
        ├──► Verification Service (EmailVerificationService)
        │
        ▼
User & Profile Repository (auth_repo.py) ──► Lockout Audit Store (runtime_logs/lockout_audit.json)
        │
        ▼
JSON File Database (runtime_logs/auth.json)
```

1. **HTTP API Gateway (`src/Application/Services/web_dashboard.py`):** Responsible for HTTP request parsing, DTO validation, header session extraction, and status codes.
2. **Application Auth Service (`src/Application/Dashboard/auth_service.py`):** Authoritative owner of credential verification, PBKDF2-SHA256 password hashing, lockout policy enforcement, and verification challenge orchestration.
3. **User & Profile Repository (`src/Application/Dashboard/auth_repo.py`):** Owner of user identity persistence (`runtime_logs/auth.json`).
4. **External Helper (`src/Application/Services/telegram_auth.py`):** Cryptographic verification adapter for Telegram login widget payloads.

---

## 3. Canonical Identity Model

The canonical user identity DTO is structured as:

```json
{
  "user_id": "usr-8a9d20c",
  "email": "user@yartrader.app",
  "name": "Elite Trader",
  "role": "USER",
  "is_verified": false,
  "created_at": "2026-09-06T20:00:00Z",
  "password_hash": "pbkdf2_sha256$100000$salt$hash",
  "tier": "FREE"
}
```

* **Canonical User Identifier (`user_id`):** Stable, unique string identifier (`usr-{hex}`).
* **Normalized Email (`email`):** Unique, lowercased, whitespace-trimmed email address.
* **Email Verification State (`is_verified`):** Boolean indicating whether email verification challenge has been completed.

---

## 4. Email Normalization Rules

All identity lookup, registration, authentication, and token creation functions invoke `normalize_email(email)`:

```python
def normalize_email(email: str) -> str:
    if not email or not isinstance(email, str):
        raise ValidationException("Invalid email: Email address must be a non-empty string.")
    normalized = email.strip().lower()
    if "@" not in normalized or len(normalized) < 3:
        raise ValidationException(f"Invalid email structure: '{email}'.")
    return normalized
```

---

## 5. Password Security

* **Hashing Standard:** `PBKDF2-SHA256` with 100,000 iterations and 16-byte random hex salts (`secrets.token_hex(16)`).
* **Format:** `pbkdf2_sha256${iterations}${salt}${derived_key_hex}`
* **Security Invariants:** Plaintext passwords are never stored, logged, or returned in API DTOs. Constant-time comparison (`hmac.compare_digest`) is enforced during credential verification.

---

## 6. Email Verification Lifecycle

1. **Registration:** `AuthService.register_user` creates user record with `is_verified: False`.
2. **Challenge Creation:** `EmailVerificationService.create_verification_challenge` generates cryptographically random token (`vkn-{urlsafe_32}`). Token is hashed via SHA-256 prior to storage in `runtime_logs/verification_tokens.json`.
3. **Delivery Boundary:** Token is dispatched via `send_saas_email` abstraction.
4. **Verification Consumption:** User submits token to `/api/auth/verify-email`. `EmailVerificationService.verify_token` validates token expiration (24 hours) and single-use status, marking account `is_verified: True`. Reused or expired tokens raise `ValidationException`.

---

## 7. Lockout & Security Auditability

* **Threshold:** Maximum 5 failed login attempts within a 15-minute window per normalized email address.
* **Audit Store:** `runtime_logs/lockout_audit.json` records ISO-8601 UTC timestamp, source IP, user agent, event type (`USER_LOGIN_FAILURE`, `ADMIN_LOCKOUT`), and lockout state.
* **Reset Rule:** Successful login clears failed attempt history for the normalized email.

---

## 8. Telegram Widget Authorization

`src/Application/Services/telegram_auth.py` cryptographically verifies Telegram Login Widget payloads:

1. Computes secret key: `sha256(bot_token)`.
2. Computes data check string: Alphabetically sorted `key=value\n` string of payload parameters (excluding `hash`).
3. Verifies `hmac_sha256(secret_key, data_check_string) == received_hash` in constant time.
4. Enforces 24-hour freshness check on `auth_date` timestamp.
5. On success, maps Telegram ID (`telegram_id`) to canonical user identity.

---

## 9. Phase 4 Completion Verdict

```text
PHASE 4 = PASS
```

**Reasoning:** Auth, identity, email verification, password security, lockout policies, and Telegram authentication helpers have been hardened and documented. Comprehensive unit and integration tests in `tests/YarTrader.Tests/Services/test_auth_identity_phase4.py` verify email normalization, token single-use lifecycle, PBKDF2 hashing, lockout thresholds, and session issuance. Full test suite (1846+ passed) and frontend build verify zero regressions.
