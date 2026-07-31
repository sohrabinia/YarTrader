# TradeYar AI — Windows Service Deployment Guide

This guide describes how to deploy, manage, and monitor the **TradeYar-AI** runtime as a robust 24/7 Windows Service on Windows Server (e.g. Windows Server 2022).

---

## 1. Installation

To register and install **TradeYar-AI** as a background service:

1. Open **PowerShell** as **Administrator**.
2. Navigate to the repository root directory:
   ```powershell
   cd C:\path\to\TradeYar-AI
   ```
3. Run the installation script:
   ```powershell
   .\scripts\install_service.ps1
   ```

The script registers the service name `TradeYar-AI` under the service runner host, configures directory paths, and sets the startup type to **Automatic**.

---

## 2. Start Service

To start the background service:
```powershell
.\scripts\start_service.ps1
```
Alternatively, use the standard Windows Service console (`services.msc`) or:
```powershell
Start-Service -Name "TradeYar-AI"
```

---

## 3. Stop Service

To stop the background service gracefully:
```powershell
.\scripts\stop_service.ps1
```
Alternatively:
```powershell
Stop-Service -Name "TradeYar-AI" -Force
```

---

## 4. Restart Service

To perform a complete restart cycle:
```powershell
.\scripts\restart_service.ps1
```

---

## 5. Recovery Settings

The installer script automatically configures the service recovery options on Windows Server:
- **First failure**: Restart the service after **1 minute** (60,000 ms).
- **Second failure**: Restart the service after **2 minutes** (120,000 ms).
- **Subsequent failures**: Restart the service after **5 minutes** (300,000 ms).
- **Reset fail count**: Reset the failure counter after **1 day** (86,400 seconds).

These settings guarantee automatic recovery and high availability, even if a critical error occurs.

---

## 6. Log Locations

All production event streams are outputted as structured **JSON format logs** and split into daily rotating files under the `logs/` directory:

- **General Runtime Application Logs**:
  `logs/application/application.log`
- **Error Specific Logs**:
  `logs/error/error.log`
- **Security & Activity Audit Logs**:
  `logs/audit/audit.log`
- **Intelligence Decisions & Hypotheses Logs**:
  `logs/intelligence/intelligence.log`

---

## 7. Troubleshooting & Verification

To verify that the service is running and healthy:

1. Run the local health check tool:
   ```powershell
   .\scripts\health_check.ps1
   ```
2. Check the real-time API health payload directly at:
   `http://127.0.0.1:8000/health`
3. Inspect the event log via Windows Event Viewer under `Windows Logs -> Application` filtering by source `TradeYar-AI`.

---

## 8. Server Restart Test

To confirm that the TradeYar-AI service starts automatically after a server reboot:
1. Ensure the service startup type is set to **Automatic**:
   ```powershell
   Get-Service -Name "TradeYar-AI" | Select-Object -Property Name, StartType
   ```
2. Restart the physical/virtual Windows Server.
3. Upon system restart, wait 1–2 minutes, and check that the web dashboard on port `8000` is fully online and responsive without requiring manual login.
