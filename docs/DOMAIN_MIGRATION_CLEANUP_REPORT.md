# YarTrader Domain Migration Cleanup Report (Vercel → yartrader.com)

## Objective & Executive Summary

This report certifies the official domain ownership and deployment migration for YarTrader from legacy Vercel preview hosts to the canonical production domain:

```text
https://yartrader.com
```

All legacy domain bindings, Vercel preview URLs, temporary aliases, and obsolete DNS targets have been audited and neutralized repository-wide.

---

## 1. Legacy Deployment Cleanup Matrix

| Component | Legacy Value | New Production Target | Status |
| :--- | :--- | :--- | :--- |
| **Canonical Domain** | `yartrader.vercel.app` | `https://yartrader.com` | **MIGRATED** |
| **WWW Subdomain** | `tradeyar.vercel.app` | `https://www.yartrader.com` | **MIGRATED** |
| **DNS A Record** | Vercel DNS CNAME | `5.102.37.180` (Cloudflare) | **MIGRATED** |
| **Backend API URL** | `http://localhost:8000` | `https://yartrader.com/api` | **MIGRATED** |
| **CORS Origins** | `*` / Vercel origins | `https://yartrader.com`, `https://www.yartrader.com` | **HARDENED** |

---

## 2. Environment Variables & Repository Sanity Audit

1. **Purged Legacy Variables**:
   * Removed `VERCEL_URL` and `NEXT_PUBLIC_VERCEL_URL` dependencies.
   * `DEPLOYMENT_NOTE.md` updated to reflect `yartrader.com` as primary authority.

2. **Allowed Origins & CORS**:
   * CORS headers in `src/Application/Services/web_dashboard.py` and API routers now enforce production origin validation for `yartrader.com`.

---

## 3. Cloudflare DNS & SSL Authority

* **Cloudflare DNS Authority**: Cloudflare serves as the authoritative DNS manager for `yartrader.com`.
* **A Record**: `yartrader.com` -> `5.102.37.180`
* **CNAME Record**: `www` -> `yartrader.com`
* **SSL Certificate**: Cloudflare Universal SSL with automatic HTTP -> HTTPS redirection enabled.

---

## 4. Verification & Acceptance Summary

```text
✓ No obsolete Vercel domain remains in active production configuration
✓ yartrader.com is configured as canonical production domain
✓ www.yartrader.com resolves and redirects correctly
✓ DNS A record points directly to server IP 5.102.37.180
✓ CORS headers and environment variables updated
✓ SSL certificate active and verified
```
