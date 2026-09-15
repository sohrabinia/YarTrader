# 03 - Authentication & Authorization Security Contract

## Customer Authentication
* **Supported Customer Login Methods**:
  - Email + Password registration (`POST /api/auth/register`) and login (`POST /api/auth/login`).
  - Google OIDC sign-in (`POST /api/auth/google`).
  - Both methods are fully supported and issue active session tokens (`tkn-...`).
* **Unsupported Customer Methods**:
  - Non-supported customer endpoints (`POST /api/auth/forgot-password`, `GET /api/auth/verify-email`, `POST /api/auth/reset-password`, Apple, Telegram) remain unreachable and return `404 Not Found` / `405 Method Not Allowed`.

## Admin Authentication & Authorization
* **Admin Security Boundary**:
  - Admin credential authentication uses `POST /api/auth/login` (or Google OIDC callback).
  - Admin accounts are automatically assigned `role == "ADMIN"` and `tier == "INSTITUTIONAL"` server-side via `is_admin_email()`.
  - Configured admin accounts synchronize password credentials with `YARTRADER_DEFAULT_ADMIN_PASSWORD_HASH` / `TRADEYAR_DEFAULT_ADMIN_PASSWORD_HASH` without mutating existing account identities, `user_id`s, social bindings, or customer data.
* **Admin Token Verification**:
  - Protected admin endpoints (`/api/admin/*`, `/api/admin/operator`) enforce strict HTTP header verification: `Authorization: Bearer <token>`.
  - Tokens passed in query parameters are strictly rejected with HTTP `401 Unauthorized`.
* **Anti-Impersonation Session Security**:
  - Operator identity (`email`, `user_id`, `role`) is derived server-side from the authenticated YarTrader admin session.
  - Candidate identities supplied in client request bodies or headers that conflict with session facts trigger immediate HTTP `403 Forbidden`.
* **Zero Secret Exposure**:
  - Proxied requests to YarOperator runtime (`http://127.0.0.1:8080`) attach `OPERATOR_SERVER_SECRET` server-side.
  - Server secrets and internal tokens are never transmitted or exposed to client browsers.
