# PERMISSIONS.md — Permissions and Route Guard Rules

This document outlines the strict client-side access control, security checks, and secret exposure boundaries.

---

## 🛡️ Route Guard Logic Specs

To prevent unauthenticated or unauthorized users from manually rendering dashboard or SRE administration folders, every view must implement a component wrapper check.

### Key Rules:
1. **The Guest Redirect Rule:** If a user without a session token attempts to load `/dashboard/*` or `/admin/*`, redirect them immediately to `/login` and save their target URL in a `redirect_to` query parameter for post-login routing.
2. **The 403 Forbidden Rule:** If a standard `USER`, `PRO`, or `PREMIUM` client manually edits their URL bar to browse `/admin/*`, intercept the route change, block rendering, redirect them to `/403`, and push a security audit toast.
3. **The Limit Ceiling Lock:** Only clients authenticated as `ADMIN` or `SRE_OPERATOR` are allowed to render input panels that send POST calls to `/api/control` or `/api/mode`. Standard users must see these controls as disabled or completely hidden.

---

## 🤐 Secret Storage and Exposure Boundaries

The frontend code represents a potential security vector. To ensure maximum defense in depth, the client-side code must adhere to these rules:

1. **Never Expose Private Keys:** Private keys, SSL/TLS certs, and SMTP credentials must never be included in frontend environments or JavaScript assets.
2. **Never Expose Broker Credentials:** MetaTrader5 connection login numbers, passwords, and server names must remain strictly hidden in the backend's environment configuration (`.env.production`). The frontend dashboard `/admin` can display connection status (e.g. `Connected to broker server`) and last updated timestamps, but must never display MT5 passwords or account keys.
3. **Hide API Keys:** Downstream payment gateways or assistant APIs must be proxy-routed via the backend server instead of direct frontend-to-service calls, ensuring the API key is never exposed on client browsers.
