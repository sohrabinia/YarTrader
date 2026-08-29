# YARTRADER — PRODUCTION ORIGIN SECURITY & CLOUDFLARE HARDENING

## OVERVIEW

This document specifies the production origin security boundary and edge proxy hardening architecture for **YarTrader** hosted at `https://yartrader.com`.

The objective is to eliminate direct unrestricted public origin access, prevent unknown host header spoofing, enforce HTTPS encryption, enforce web security headers, and maintain clean firewall hygiene without modifying the underlying trading intelligence core.

---

## ARCHITECTURE MAP

```text
[ Public Internet Users ]
           │
           ▼
[ Cloudflare Edge Proxy (HTTPS :443) ]
  • SSL/TLS Termination
  • HTTP -> HTTPS Redirect (301)
  • WAF & DDoS Protection
           │
           ▼ (Restricted to Cloudflare IP Ranges)
[ Windows Server Host Public IP :80 ]
           │
           ▼ (netsh portproxy)
[ Localloop Ingress 127.0.0.1:8000 ]
           │
           ▼
[ YarTrader FastAPI Application (Uvicorn / NSSM Service) ]
  • Host Header Allowlist Enforcement (TrustedHostMiddleware)
  • Production Security Headers Injection
  • Application Route Dispatch
```

---

## VERIFIED PROBLEMS & REMEDIATION MATRIX

| Issue / Finding | Root Cause | Implemented Remediation |
|---|---|---|
| **Direct Origin Exposure** (`http://5.102.37.180/` returning 200) | Public IP port 80 accepted direct connections from any IP on the internet. | Configured Windows Defender Firewall inbound rule restricting port 80 traffic strictly to Cloudflare's published IP ranges (`scripts/configure_origin_security.ps1`). |
| **Unknown Host Headers Accepted** (`Host: unknown-host.invalid` returning 200) | FastAPI lacked host header allowlist validation. | Added `TrustedHostMiddleware` in `src/Application/Services/web_dashboard.py` allowing only `yartrader.com`, `*.yartrader.com`, `localhost`, `127.0.0.1`, and `testserver`. Unknown host headers receive HTTP 400 Bad Request. |
| **Plaintext HTTP Responses** | Cloudflare / origin did not permanently redirect HTTP requests. | Added HTTP middleware checking `X-Forwarded-Proto: http` and returning `301 Moved Permanently` to `https://...`. |
| **Missing Security Headers** | Default Uvicorn responses lacked security policy headers. | Injected `Strict-Transport-Security`, `Content-Security-Policy`, `X-Frame-Options`, `X-Content-Type-Options`, `Referrer-Policy`, and `Permissions-Policy` in HTTP middleware. |
| **Firewall Drift / Obsolete Rules** | Old rules (`TradeYarAI 8000`, `TradeYar DevOps API 5000`) enabled inbound open ports. | Created PowerShell automation `scripts/configure_origin_security.ps1` to remove obsolete rules and ensure port 8000/5000 remain localhost-only. |

---

## CONFIGURED SECURITY HEADERS

All HTTP/HTTPS responses served by the application include the following headers:

```http
Strict-Transport-Security: max-age=31536000; includeSubDomains; preload
X-Content-Type-Options: nosniff
X-Frame-Options: SAMEORIGIN
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: camera=(), microphone=(), geolocation=(), payment=()
Content-Security-Policy: default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net; style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; font-src 'self' https://cdn.jsdelivr.net data:; img-src 'self' data: https:; connect-src 'self' https://yartrader.com https://www.yartrader.com wss: ws:; frame-ancestors 'self';
```

---

## WINDOWS SERVER FIREWALL DEPLOYMENT INSTRUCTIONS

On the Windows Server production host (`5.102.37.180`), run the following from an elevated PowerShell command prompt:

```powershell
.\scripts\configure_origin_security.ps1 -RestrictPort80ToCloudflare -RemoveObsoleteRules
```

### Verification Commands on Windows Server

1. **Verify Listener Ports:**
   ```powershell
   Get-NetTCPConnection -State Listen | Where-Object { $_.LocalPort -in 80, 8000, 5000, 443 }
   ```
   *Expected:* Port 80 listening on `0.0.0.0`, Port 8000 listening on `127.0.0.1` ONLY, Port 5000 NOT listening.

2. **Verify Firewall Inbound Rules:**
   ```powershell
   Get-NetFirewallRule -DisplayName "YarTrader Inbound Cloudflare HTTP 80"
   ```
   *Expected:* Active, Action = Allow, Direction = Inbound, RemoteAddress = Cloudflare CIDR blocks.

3. **Verify Service Health:**
   ```powershell
   sc.exe query YarTrader
   Invoke-RestMethod "http://127.0.0.1:8000/health"
   ```

---

## TRADING BRAIN SAFETY GUARANTEE

This security hardening pass operates strictly on the network transport, HTTP header, and reverse proxy ingress boundary.

The trading intelligence core is completely untouched and frozen:
- `LIVE_TRADING_ENABLED` remains hard-locked to `False`.
- Decision Engine, Risk Engine, Strategy Engine, Signal Engine, and Execution Boundary are unmodified.
