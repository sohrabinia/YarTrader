# YARTRADER — CUSTOMER AUTHENTICATION MERGE & RECOVERY FORENSIC RECORD

**Date:** September 15, 2026
**Repository:** `sohrabinia/YarTrader`
**Base/Main SHA:** `fcc391bc654729a4174ead1d3eaa79d995441f76`
**Jules Branch SHA:** `ca252199bdad54c562524ec3bc58a6ad5ffd73ac`
**Scope:** Forensic documentation of completed customer authentication remediation, OIDC audience validation, password recovery security boundaries, and git merge provenance.
**Classification:** CTO SECURITY & FORENSIC RECORD — DOCUMENTATION ONLY

---

## 1. PURPOSE

This document establishes a concise, technically accurate forensic record detailing the root cause analysis, security design decisions, remediation implementation, test verification, and merge provenance for YarTrader customer authentication and password recovery work.

Specifically, this record documents:
1. The original Google OIDC audience mismatch root cause.
2. The configuration normalization and fallback remediation (`GOOGLE_CLIENT_ID` / `YARTRADER_GOOGLE_CLIENT_ID`).
3. The nested exception-handling bug that produced `Audience doesn't match: Audience doesn't match`.
4. The password recovery requirement for existing Google-authenticated customer accounts.
5. Why unauthenticated `/register` password attachment was rejected as an unsafe account-takeover vector.
6. The trusted authenticated `set-password` flow (`POST /api/auth/set-password`).
7. The cross-account authorization security boundary (`HTTP 403 Forbidden`).
8. The merge and conflict resolution decision.
9. Verification evidence (unit tests, full backend suite, and Vite production frontend build).
10. What remains outside the scope of this remediation.

---

## 2. CURRENT AUTHENTICATION MODEL

### Customer Authentication Flow (Google OIDC)

```text
Google OIDC (Frontend)
    ↓
Google ID Token (JWT)
    ↓
Server-Side Cryptographic Validation (oidc_validator.py)
    ├── Signature Verification (RS256 via Google JWKS)
    ├── Issuer Validation ("accounts.google.com", "https://accounts.google.com")
    ├── Audience Validation (matches configured Client ID)
    ├── Expiration Validation (exp claim)
    └── Required Claims Validation (exp, iss, aud, sub)
    ↓
Existing Customer Identity (auth_repo.py / auth_service.py)
    ↓
Server Session Creation (AuthService.create_session)
    ↓
Authenticated Customer
```

### Authentication vs. Authorization Boundary Principle

```text
Customer Session Authentication (Session Token / Cookies)
        ≠
Internal / Admin Bearer Authorization (Authorization: Bearer <token>)
```

* **Customer Authentication**: Used by end-user traders accessing terminal features, settings, or customer endpoints. Session state is managed via server-side session tokens derived from validated credentials (OIDC ID token or PBKDF2-SHA256 password login).
* **Internal / Admin Authorization**: Used for operational, administrative, and service-to-service endpoints (`/api/admin/*`, `/api/admin/operator`). Admin authorization requires an explicit `Authorization: Bearer <token>` HTTP header verified by `enforce_admin_token()`. Query parameter authorization tokens are strictly rejected with `HTTP 401 Unauthorized`. Internal admin authorization is strictly isolated and must never be described or exposed as customer login.

---

## 3. GOOGLE OIDC AUDIENCE ROOT CAUSE

### Validator Inspection (`src/Application/Dashboard/oidc_validator.py`)

During OIDC token validation, `validate_social_token(token, "google")` decodes and cryptographically verifies incoming Google ID tokens.

* **Configuration Normalization**:
  - Google Client ID is read from environment variables: `GOOGLE_CLIENT_ID` with fallback to `YARTRADER_GOOGLE_CLIENT_ID`.
  - The variable is explicitly sanitized using `.strip()` to prevent trailing whitespace or line breaks from causing silent audience comparison mismatches.
* **Fail-Closed Security Mandate**:
  - Audience verification remains strictly enabled (`verify_aud=True`).
  - Disabling audience validation (`verify_aud=False`) is strictly prohibited in production.
  - Accepting wildcards or multiple undocumented client IDs is strictly prohibited.
* **Diagnostic Reporting**:
  - In the event of a configuration or token mismatch, diagnostic logging extracts the unverified JWT header/claims to construct a safe fingerprint error: `Server expected client_id fingerprint '...<suffix>', token contains aud='<aud>', azp='<azp>'`.
  - No secret keys or raw credentials are ever exposed in error output.

---

## 4. NESTED EXCEPTION BUG

### Root Cause Analysis

In `src/Application/Dashboard/oidc_validator.py`, when `jwt.InvalidAudienceError` occurred during `jwt.decode(...)`, the exception handler constructed and raised a structured `ValidationException`:

```python
except jwt.InvalidAudienceError as e:
    try:
        unverified = jwt.decode(token, options={"verify_signature": False, "verify_aud": False})
        ...
        raise ValidationException(f"Social token validation error: Audience mismatch. ...")
    except Exception:
        raise ValidationException(f"Social token validation error: Audience doesn't match: {str(e)}")
```

However, in the outer exception block wrapping `validate_social_token`:

```python
except Exception as e:
    raise ValidationException(f"Unexpected token validation error: {str(e)}")
```

Because `except Exception as e:` did not re-raise existing `ValidationException` instances directly, the inner `ValidationException("Social token validation error: Audience doesn't match: Audience doesn't match")` was caught and wrapped a second time, producing duplicate diagnostic strings:

```text
Audience doesn't match: Audience doesn't match
```

### Remediation

The exception handling in `oidc_validator.py` was updated to check if the caught exception is already a `ValidationException`:

```python
except Exception as e:
    if isinstance(e, ValidationException):
        raise e
    raise ValidationException(f"Unexpected token validation error: {str(e)}")
```

This ensures that structured validation exceptions retain their exact diagnostic message without double-wrapping or message duplication.

---

## 5. GOOGLE ACCOUNT PASSWORD RECOVERY

### Background & Security Threat Model

* Customers originally registering via Google OIDC had user records created in `AuthRepository` with `password_hash = ""`.
* If a customer attempted to log in using the standard email/password form, authentication failed because no password hash existed.
* If a customer attempted to use `POST /api/auth/register` with their Google email address, the endpoint returned:
  `An account with this email address already exists.`

### Security Boundary Decision

**Unauthenticated registration must never serve as an account-takeover or password-attachment mechanism.**

Allowing an unauthenticated user to attach a password to an existing account merely by specifying an email address on `/register` would allow arbitrary third parties to hijack existing Google-created user accounts.

Therefore, the security policy is strictly hard-locked:

```text
POST /api/auth/register
    ↓
Existing Email Address?
    ├── YES ──> REJECT (HTTP 400 ValidationException: "Email address is already registered.")
    └── NO  ──> CREATE NEW ACCOUNT (PBKDF2-SHA256 Password Hash)
```

No existing account (Google, Admin, or Password-authenticated) may have its password, role, or identity mutated via an unauthenticated registration call.

---

## 6. TRUSTED PASSWORD MANAGEMENT

### Implemented Flow (`POST /api/auth/set-password`)

To support password establishment and recovery for existing Google-authenticated accounts without introducing takeover vulnerabilities, a trusted, authenticated endpoint was implemented in `src/Application/Services/web_dashboard.py` and `src/Application/Dashboard/auth_service.py`.

```text
Authenticated Customer Session
    ↓
POST /api/auth/set-password
    ├── Require Session Token Validation (validate_session)
    ├── Derive Authoritative Account Email from Session (session.get("email"))
    ├── Enforce Cross-Account Authorization (payload.email == session_email)
    └── Hash & Store New Password (PBKDF2-SHA256)
    ↓
Updated Account Credential (Preserves Identity, Google sub, Roles, & Data)
```

### Key Security Properties

1. **Authentication Required**: The caller must possess a valid, active server session token (`yartrader_token`).
2. **Authoritative Identity**: The target account is determined by the server-side session identity, not untrusted client inputs.
3. **PBKDF2-SHA256 Hashing**: Passwords are hashed using `PBKDF2-SHA256` with 100,000 iterations and per-password 16-byte random salts (`pbkdf2_sha256$100000$<salt>$<hash>`).
4. **Data Preservation**: Account identity (`user_id`), email address, roles (`ADMIN` / `USER`), tier, trading history, and Google `social_providers` binding (`sub`) remain 100% intact.

---

## 7. CROSS-ACCOUNT SECURITY BOUNDARY

### Authorization Rule

To prevent an authenticated user from modifying password credentials belonging to a different customer, `set_user_password` enforces strict cross-account session validation:

```python
session_email = session.get("email", "").strip().lower()
payload_email = payload.email.strip().lower()

if payload_email != session_email:
    raise HTTPException(status_code=403, detail="Cross-account password modification is forbidden.")
```

### Fail-Closed Execution

If `payload.email != session_email`:
* The request is rejected immediately with **HTTP 403 Forbidden**.
* Target account password hash remains unchanged.
* Target account identity, roles, and social provider bindings remain unchanged.
* The authorization violation is logged for audit inspection.

### Security Test Reference

This boundary is verified by unit test `test_cross_account_password_modification_rejected` in `tests/YarTrader.Tests/Services/test_auth_api.py`.

---

## 8. REGISTRATION SECURITY TESTS

Registration endpoints (`POST /api/auth/register`) strictly enforce existing-account protection across all account types:
* Existing Google OIDC accounts.
* Existing Admin accounts.
* Existing Email/Password customer accounts.

Expected behavior on duplicate registration attempt:
* **Response**: `HTTP 400 Bad Request` / `ValidationException("Email address is already registered.")`.
* **Zero Mutation**: Password hash, user identity (`user_id`), role, tier, and Google social provider associations are guaranteed not to be overwritten or modified.

---

## 9. MERGE & PROVENANCE RECORD

### Git Lineage

* **Base/Main SHA**: `fcc391bc654729a4174ead1d3eaa79d995441f76`
* **Jules Branch SHA at Investigation**: `ca252199bdad54c562524ec3bc58a6ad5ffd73ac`

### Jules Customer Authentication Commits

1. `68b6ace` — `fix(auth): fix nested exception handling in oidc_validator audience mismatch path`
2. `16ce159` — `Fix Google OIDC audience validation and social user password credential setting`
3. `9bbba36` — `Fix customer password recovery and registration security boundaries`
4. `95bd377` — `Secure existing Google account password recovery and cross-account authorization`
5. `ca25219` — `Final CTO Gate Verification: Secure customer password recovery and cross-account authorization`

### Merge Provenance

The branch was merged into main via PR #275 at commit `fcc391bc654729a4174ead1d3eaa79d995441f76` (`Merge pull request #275 from sohrabinia/jules-customer-auth-audit-and-completion-17035948580427581999`).

During local merge evaluation:
* **Conflict File**: `src/Application/Dashboard/oidc_validator.py`
* **Resolution Decision**: Selected the Jules-side implementation to preserve the corrected audience mismatch exception handling (`if isinstance(e, ValidationException): raise e`) and explicit `.strip()` configuration normalization.

---

## 10. CURRENT LOCAL WORKING TREE STATE

### Working Tree Isolation

* `.env.production` is a pre-existing local modification and remains uncommitted.
* **Staged Authentication Files**:
  - `src/Application/Dashboard/auth_service.py`
  - `src/Application/Dashboard/oidc_validator.py`
  - `src/Application/Services/web_dashboard.py`
  - `tests/YarTrader.Tests/Services/test_auth_api.py`

**Mandate**: `.env.production` was NOT part of the customer authentication merge and must not be committed.

---

## 11. VERIFICATION EVIDENCE

### Unit & Integration Test Results

* **Authentication API Test Suite** (`tests/YarTrader.Tests/Services/test_auth_api.py`):
  `11 passed` (100% pass rate)
* **Full Backend Pytest Suite**:
  `1853 passed` (100% pass rate)

### Frontend Production Build

* **Command**: `npm run build` / `bun run build` in `trader-terminal/`
* **Result**: Successful Vite production build without warnings or errors.

---

## 12. PRODUCTION STATUS

### Verified Production Status

* **Live Domain Health**:
  - `https://yartrader.com/` → HTTP 200 OK
  - `https://yartrader.com/fa/login` → HTTP 200 OK
  - `https://yartrader.com/health` → HTTP 200 OK
* **Production Service**: YarTrader → Running
* **Current Deployed Main Commit**: `fcc391bc654729a4174ead1d3eaa79d995441f76`

---

## 13. SECURITY FINDINGS SUMMARY

### Fixed
* Google OIDC audience configuration whitespace normalization (`.strip()`).
* Google OIDC audience validation error diagnostics.
* Nested exception handling in `oidc_validator.py`.
* Unsafe unauthenticated password attachment vector on `/register`.
* Cross-account password modification vulnerability (`HTTP 403 Forbidden` enforced).
* Existing-account registration overwrite risk.

### Preserved
* Cryptographic signature validation (RS256 via Google JWKS).
* Issuer validation (`accounts.google.com`).
* Audience validation (`verify_aud=True` fail-closed).
* Expiration validation (`exp`).
* Existing Google social identity bindings (`sub`).
* Existing account identity, roles (`ADMIN` / `USER`), tier, and trading data.
* Isolation between Customer Authentication and Admin Authorization.

### Unchanged (Protected Core)
* Trading Core (`src/Research/`, `src/Decision/`, `src/Execution/`).
* MT5 / MT4 Adapters.
* Risk Engine & Sizing Calculations.
* Demo Execution Safety Gate (`LIVE_TRADING_ENABLED = False`).
* Daily 8% Loss Protection Kill-Switch.
* Trade lifecycle logic.
* YarOperator / Internal runtime architecture.

---

## 14. OUT-OF-SCOPE ITEMS

1. **Production Google OIDC Live Testing**:
   `Production Google OIDC end-to-end login remains pending live verification.`
2. **Deployment Verification**:
   The password recovery and OIDC remediation changes are committed and merged into `main` branch SHA `fcc391bc654729a4174ead1d3eaa79d995441f76`.
