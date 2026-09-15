# 03 - Authentication & Authorization Security Contract

## Customer Authentication (Google OIDC Exclusive)
* **Exclusive Login Strategy**: Google OIDC is the single, exclusive customer authentication and registration mechanism.
* **Deprecation of Legacy Customer Auth**:
  - Legacy customer auth endpoints (`POST /api/auth/login`, `POST /api/auth/register`, `POST /api/auth/forgot-password`, `GET /api/auth/verify-email`, `POST /api/auth/reset-password`) and Telegram customer auth (`telegram_auth.py`) are permanently removed and return `404 Not Found` / `405 Method Not Allowed`.
  - Production UI (`trader-terminal/src/App.jsx`) presents exclusively Google OIDC action controls without username/password forms or third-party auth buttons.

## Admin Authorization & YarOperator Security
* **Admin Token Verification**:
  - Protected admin endpoints (`/api/admin/*`, `/api/admin/operator`) enforce strict HTTP header verification: `Authorization: Bearer <token>`.
  - Tokens passed in query parameters are strictly rejected with HTTP `401 Unauthorized`.
* **Anti-Impersonation Session Security**:
  - Operator identity (`email`, `user_id`, `role`) is derived server-side from the authenticated YarTrader admin session.
  - Candidate identities supplied in client request bodies or headers that conflict with session facts trigger immediate HTTP `403 Forbidden`.
* **Zero Secret Exposure**:
  - Proxied requests to YarOperator runtime (`http://127.0.0.1:8080`) attach `OPERATOR_SERVER_SECRET` server-side.
  - Server secrets and internal tokens are never transmitted or exposed to client browsers.
