# DEPLOYMENT GUIDE
# TradeYar AI v3.2 — Enterprise Productization Phase

This guide outlines deployment processes for staging, testing, and production environments of **TradeYar AI v3.2**.

---

## 1. Local Development Setup

To boot and test the complete system locally:

1. **Clone and Install Dependencies:**
   Ensure Python 3.12 is installed.
   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Run Migrations:**
   Ensure database tables are fully generated and up-to-date.
   ```bash
   alembic upgrade head
   ```

3. **Start the Web Dashboard Application:**
   Run the FastAPI server locally:
   ```bash
   python -m uvicorn src.Application.Services.web_dashboard:app --port 8000 --reload
   ```

---

## 2. Production Deployment on Windows Server 2022

To deploy TradeYar AI as an automatic Windows SCM background service:

1. **Install NSSM (Non-Sucking Service Manager):**
   Download NSSM and add it to system path.

2. **Configure Service Execution Host Script (`install_service.ps1`):**
   Run the administrator PowerShell install script:
   ```powershell
   powershell.exe -ExecutionPolicy Bypass -File .\scripts\install_service.ps1
   ```
   This will set up the `TradeYar-AI` Windows Service with:
   - Automated delayed startup (`SERVICE_DELAYED_AUTO_START`).
   - Logging redirection to capped daily files.

3. **Verify Service Health via SCM:**
   ```powershell
   Get-Service -Name "TradeYar-AI"
   ```

---

## 3. Security Hardening Configuration

Before setting the application in a public-facing domain:

- **Configure JWT Secret:** Do not use the default secret. Override it using environment variables:
  ```bash
  export TRADEYAR_JWT_SECRET="HighlySecureProductionSecretValue"
  ```
- **SSL Termination:** Always route the FastAPI server behind a reverse proxy (such as **Nginx** or **IIS**) with an active SSL certificate.
- **Strict CORS Control:** Update CORS parameters in `src/Application/Services/web_dashboard.py` from `"*"` to specific trusted frontend domain names.
- **Port Management:** Bind the FastAPI server only to local loopback interface (`127.0.0.1`) and expose only ports `80` / `443` on the reverse proxy.
