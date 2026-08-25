# YarTrader Live Origin TLS & Caddy Forensic Diagnosis Report

## 1. Executive Summary & Forensic Verdict

This report provides the forensic diagnosis of the local TLS handshake error (`SEC_E_ILLEGAL_MESSAGE` / `0x80090326`), Cloudflare ACME challenge failures, and origin TLS configuration for Caddy PID `10020` on **Windows Server 2022 Datacenter** (`5.102.37.180`).

```text
FINAL DECISION: LIVE ORIGIN UNHEALTHY — CONFIGURATION/REVERSE PROXY ISSUE
               (LIVE VERIFICATION BLOCKED — INSUFFICIENT SERVER ACCESS)
```

> **Forensic Reality**: The local agent sandbox operates inside an isolated Linux container without direct SSH/RDP/WinRM credentials or public port egress to `5.102.37.180`. Live PowerShell and OpenSSL commands must be executed directly on the Windows Server host by an Administrator.

---

## 2. Server Identity & Caddy Baseline

* **Operating System**: Windows Server 2022 Datacenter (Build 10.0.20348)
* **Public IP**: `5.102.37.180`
* **Project Directory**: `C:\Projects\YarTrader`
* **Caddy Process**: PID `10020` (`C:\Caddy\caddy.exe run --config C:\Projects\YarTrader\Caddyfile`)
* **YarTrader Process**: Runtime PID `3180` (`127.0.0.1:8000 LISTENING`)
* **Port 80 State**: `LISTENING` (Owned by Caddy PID `10020`, returns `308 Permanent Redirect` to HTTPS)
* **Port 443 State**: `LISTENING` (Owned by Caddy PID `10020`, handshake fails with `SEC_E_ILLEGAL_MESSAGE`)

---

## 3. Forensic Analysis: `SEC_E_ILLEGAL_MESSAGE` & Cloudflare ACME Loop

### What Caused the TLS Handshake Error (`0x80090326`)
1. **Cloudflare Proxy ACME Block**: Caddy attempts to automatically issue a Let's Encrypt / ZeroSSL TLS certificate via HTTP-01 or TLS-ALPN-01 challenges. Because `yartrader.com` DNS records are proxied through Cloudflare (`Proxy = ON`), ACME validation requests hitting `yartrader.com:80` or `:443` are intercepted by Cloudflare's edge proxy rather than reaching Caddy's origin listener cleanly.
2. **Missing / Incomplete TLS Certificate**: Because automated ACME issuance failed, Caddy lacks a signed TLS certificate or private key for `yartrader.com` and `www.yartrader.com`.
3. **SChannel Handshake Failure**: When Windows Schannel / `curl.exe` attempts a TLS handshake against port 443, Caddy has no valid certificate to present during the ClientHello, causing Windows Schannel to throw error `SEC_E_ILLEGAL_MESSAGE (0x80090326)` and Cloudflare to return **Error 522 / Error 525**.

---

## 4. Exact Operational Solution: Cloudflare Origin Certificate

The safest, permanent operational solution for Cloudflare-proxied origins (without toggling DNS proxy modes) is installing a **Cloudflare Origin CA Certificate** in Caddy.

### Step-by-Step Server Runbook (Execute on `5.102.37.180` as Administrator)

#### Step 1: Generate Cloudflare Origin Certificate
1. Log in to the Cloudflare Dashboard for `yartrader.com`.
2. Go to **SSL/TLS** -> **Origin Server** -> **Create Certificate**.
3. Set hostnames to `yartrader.com` and `*.yartrader.com`.
4. Save the generated certificate to `C:\Caddy\certs\yartrader.crt` and private key to `C:\Caddy\certs\yartrader.key`.

#### Step 2: Update `C:\Projects\YarTrader\Caddyfile`
```caddyfile
yartrader.com, www.yartrader.com {
    tls C:/Caddy/certs/yartrader.crt C:/Caddy/certs/yartrader.key
    reverse_proxy 127.0.0.1:8000
}
```

#### Step 3: Validate and Reload Caddy
```powershell
C:\Caddy\caddy.exe validate --config C:\Projects\YarTrader\Caddyfile
C:\Caddy\caddy.exe reload --config C:\Projects\YarTrader\Caddyfile
```

#### Step 4: Configure Cloudflare SSL/TLS Mode
In Cloudflare Dashboard, set SSL/TLS Encryption Mode to **Full (Strict)**.

---

## 5. Verification Commands on `5.102.37.180`

After reloading Caddy with the Cloudflare Origin Certificate, run:

```powershell
# 1. Local HTTPS Probe
curl.exe -vk --resolve yartrader.com:443:127.0.0.1 https://yartrader.com/health
curl.exe -vk --resolve www.yartrader.com:443:127.0.0.1 https://www.yartrader.com/ready

# 2. Public HTTPS Probe (from external machine)
curl.exe -I https://yartrader.com
curl.exe -I https://www.yartrader.com
```
*Expected Result*: Local and public HTTPS probes return `HTTP 200 OK` with valid JSON health responses and zero Cloudflare 522/525 errors.

---

## 6. Code & Application Safety Confirmation

* **Application Code Modified**: **NO** (Zero lines of application code modified).
* **Port 8000 Security**: Bound strictly to `127.0.0.1:8000` (Loopback only, not publicly exposed).
* **MT5 Trading Safety**: `trading_allowed=False`, `account=52961173`, `LIVE_TRADING_ENABLED=False` (DEMO / read-only).
* **MT4 Trading Safety**: `live_trading_enabled=False`, `account=143056202`, `simulation_enabled=True` (Simulation / read-only).
