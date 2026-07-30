# DEPLOYMENT GUIDE
**Windows Server 2022 Production Hosting Manual**

TradeYar AI is fully optimized to run on Windows Server 2022 environments, coupling the FastAPI web server with a real, read-only MetaTrader5 terminal instance.

---

## 1. System Requirements
- **OS**: Windows Server 2022 (with GUI enabled)
- **Python**: Version 3.12.x
- **MetaTrader5 Terminal**: Real desktop application installed in standard directories.
- **Network**: Internet access enabled, with inbound TCP port `8000` (or `443` for SSL) open on Windows Firewall.

---

## 2. MetaTrader5 Read-Only Preparation
1. Open the MT5 Terminal on the host server.
2. Log in using your broker's **Read-Only / Investor** credentials (this strictly guarantees passive, non-trading safety).
3. Under MT5 Settings -> **Tools -> Options -> Expert Advisors**:
   - Check "Allow WebRequest for listed URLs" (if economic/news aggregators are used).

---

## 3. Installation Steps
1. Clone or copy the TradeYar AI production directory onto the server.
2. Initialize and configure environment variables in Windows System Settings or create a `.env` file in the root directory:
   ```env
   TRADEYAR_SIMULATION_MODE=True
   TRADEYAR_SECRET_KEY=my-super-secure-production-key-value-1122
   TRADEYAR_AUTH_DB_PATH=runtime_logs/auth.json
   ```
3. Install dependencies using standard Python shims:
   ```cmd
   pip install -r requirements.txt
   ```

---

## 4. Hosting with Uvicorn & Process Monitor
To run the server continuously and survive machine restarts, use Windows Task Scheduler or host the application as a Windows Service using **NSSM (Non-Sucking Service Manager)**:

1. Download NSSM and extract it on your server.
2. Run NSSM in an elevated Command Prompt:
   ```cmd
   nssm install TradeYarAI
   ```
3. Configure the parameters:
   - **Path**: `C:\Users\Administrator\AppData\Local\Programs\Python\Python312\python.exe` (or your Python path)
   - **Arguments**: `-m uvicorn src.Application.Services.web_dashboard:app --host 0.0.0.0 --port 8000 --workers 4`
   - **Startup directory**: `C:\TradeYarAI` (or your platform directory)
4. Click **Install Service** and start it:
   ```cmd
   nssm start TradeYarAI
   ```

Windows Server will now keep the FastAPI app running continuously, auto-restarting on failure or system reboot!
