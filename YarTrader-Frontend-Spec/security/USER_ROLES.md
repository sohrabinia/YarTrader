# USER_ROLES.md — User Roles

This document details the user personas and operational roles configured across the TradeYar AI client platform.

---

## 👥 Role Mapping Matrix

The platform supports exactly five roles, mapped to hierarchical permission levels:

| Role Name | Scope / Target Shell | Allowed Screens | Hidden Actions | Daily AI Support Limits |
| :--- | :--- | :--- | :--- | :--- |
| **`GUEST`** (Public) | Public Shell Only | `/`, `/features`, `/pricing`, `/blog`, `/login`, `/register` | Cannot access `/dashboard/*` or `/admin/*` | **0** queries |
| **`USER`** (Standard Member) | Public + Terminal | `/dashboard`, `/dashboard/research`, `/dashboard/strategy`, `/dashboard/risk`, `/dashboard/execution`, `/dashboard/learning` | Cannot edit dynamic limits or access `/admin/*` | **10** queries/day |
| **`PRO`** (Advanced Trader) | Public + Terminal | `/dashboard/*` (All terminal analytics) | Cannot edit dynamic limits or access `/admin/*` | **100** queries/day |
| **`PREMIUM`** (Elite VIP) | Public + Terminal | `/dashboard/*` (All terminal analytics) | Cannot edit dynamic limits or access `/admin/*` | **500** queries/day |
| **`ADMIN`** / **`SRE`** | Public + Terminal + SRE Admin | **All Screens** (No restrictions) | None (Full control) | **Unlimited** queries |

---

## 🔏 User Identity Storage Rule

Client sessions are tracked using secure token references synced with `runtime_logs/auth.json`.

1. **PBKDF2 Password Checks:** The frontend must never attempt password hashing calculations on-client. Passwords entered during login/registration are securely piped as plain text over encrypted TLS connections to the server, where they are evaluated using a strict `100,000` iteration PBKDF2-SHA256 password hash.
2. **Session Persistence:** Secure session cookies or localStorage elements hold the dynamic session token reference. If the session token is removed or expires, the client store transitions instantly to unauthenticated and triggers the login redirect sequence.
