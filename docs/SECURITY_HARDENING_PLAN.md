# TradeYar AI — Security Hardening Plan (RC-1)
**Date:** July 30, 2026
**Auditor:** Principal Software Architect, Principal Security Auditor & CTO
**Audit Phase:** Production Readiness Planning (Pure Verification — NO CODE CHANGES)

---

## 1. Introduction
The **Security Hardening Plan** outlines the active security guardrails, vulnerability scanning, secret management policies, and endpoint protection layers required to secure the **TradeYar AI RC-1** system under live operational environments.

---

## 2. Dependency Scanning & Vulnerability Management

* **Static Dependency Analysis:** To mitigate transitive dependency risks, the project limits package imports to a pinned set of four high-quality libraries: `pytest`, `fastapi`, `uvicorn`, and `httpx`.
* **CI/CD Integration:** Integrate automated security scanning using industry-standard tools (such as `safety` and `pip-audit`) inside `.github/workflows/ci.yml`.
* **Vulnerability Checks:** Add the following step to check package manifests for known CVE vulnerabilities during every build:
  ```yaml
  - name: Run Dependency Vulnerability Scan
    run: |
      pip install pip-audit
      pip-audit -r requirements.txt
  ```

---

## 3. Secret Management Policies

* **Zero Hardcoded Credentials:** TradeYar AI blocks hardcoded passwords, logins, API keys, or broker certificates inside the source code or configurations.
* **Environment-Based Inject:** All critical parameters (such as `MT5_PASSWORD`, `MT5_LOGIN`, etc.) are injected into the Docker container process runtime via secure environment variables at startup.
* **Secret Protection Guardrails:** Configure a pre-commit hook (using tools like `detect-secrets` or `gitleaks`) to scan code commits locally and block accidental secret leakage before push.
* **Production Secret Vaults:** For live enterprise environments, configuration parameters must be retrieved dynamically from secure, encrypted vault systems (such as AWS Secrets Manager or HashiCorp Vault) rather than static server env files.

---

## 4. API & Endpoint Security Protections

The administrative REST API endpoints are secured using a multi-layered security middleware design:

### A. Authorization & Scope Checks
All restricted endpoints (including `/v1/health`, `/v1/metrics`, `/v1/dashboard/*`) require a validated Client ID and Token, mapped using security scopes:
- `client_1` (CTO / Admin): Granted `read` and `write` scope permissions.
- `client_2` (ReadOnly Monitor): Granted `read` scope permissions.
Unauthorized requests are rejected immediately with HTTP `401 Unauthorized` or `403 Forbidden`.

### B. Input Validation & AST Security Scans
The `api.py` middleware checks all incoming JSON payloads against a strict list of forbidden trade-execution keywords (e.g., `order`, `position`, `buy`, `sell`).
- Any payload containing a match is immediately blocked with HTTP `400 Bad Request`.
- This ensures that even if an attacker gains unauthorized write scope, they cannot inject active broker transactions.

### C. CORS & Network Hardening
Configure FastAPI CORS middleware to restrict origin domains:
- Disable wildcard origins (`allow_origins=["*"]`).
- Explicitly authorize only the administrative domain hosting the SPA dashboard (e.g. `allow_origins=["https://admin.tradeyar.ai"]`).
- Force HTTPS on all API pathways using secure TLS 1.3 encryption.

---

## 5. Audit Logging Architecture
The security system maintains a persistent, tamper-evident security audit log inside `logs/validation.log`.

* **Captured Actions:**
  - Failed authentication attempts (IP, client_id, and timestamp).
  - Intercepted payloads containing forbidden keywords.
  - Operations mode transitions (switching between Research, Simulation, or Shadow mode).
  - Emergency halt triggers.
* **Format:** Every entry is written in structured JSON format with complete traceback details, facilitating integration with SIEM monitoring tools (such as Splunk or ELK stack).
