# TradeYar AI — Production Network Access & Windows Firewall Guide

This document describes how to configure inbound network access, register Windows Firewall rules, and verify API connectivity for the **TradeYar-AI** production service on Windows Server.

---

## 1. Required Ports

To allow external monitoring (e.g. from `TradeYar.DevOps`) or visual dashboards to securely query the runtime, you must expose the following inbound port:

| Protocol | Port | Destination | Description |
| :---: | :---: | :---: | :--- |
| **TCP** | `8000` | `0.0.0.0` (All interfaces) | FastAPI administrative REST API and Health status endpoint. |

---

## 2. Windows Firewall Rule Configuration

To open port `8000` for inbound traffic natively, open **PowerShell** as **Administrator** and execute:

```powershell
New-NetFirewallRule -DisplayName "TradeYar AI FastAPI REST Port" `
    -Direction Inbound `
    -Action Allow `
    -Protocol TCP `
    -LocalPort 8000 `
    -Description "Exposes the descriptive TradeYar AI Health and DevOps monitoring REST endpoints."
```

Alternatively, to restrict access to a specific DevOps monitor IP (e.g. `10.0.0.50`):

```powershell
New-NetFirewallRule -DisplayName "TradeYar AI DevOps Secure Port" `
    -Direction Inbound `
    -Action Allow `
    -Protocol TCP `
    -LocalPort 8000 `
    -RemoteAddress 10.0.0.50 `
    -Description "Restricts TradeYar AI access to the DevOps monitoring gateway."
```

---

## 3. Service Verification & Binding Checks

Once the firewall is open, confirm the service is running and listening on all interfaces (`0.0.0.0`):

1. **Verify Windows SCM Service Status**:
   ```powershell
   Get-Service -Name "TradeYar-AI"
   ```
   *Expected Status: `Running`*

2. **Verify Port Binding**:
   ```powershell
   netstat -ano | findstr :8000
   ```
   *Expected Output: `TCP    0.0.0.0:8000    0.0.0.0:0    LISTENING`*

---

## 4. Connectivity Health Checks

Test external reachability from another server on the network using standard tools:

- **Via PowerShell**:
  ```powershell
  Invoke-RestMethod -Uri "http://<SERVER-IP>:8000/health" -Method Get
  ```

- **Via Curl**:
  ```bash
  curl http://<SERVER-IP>:8000/health
  ```

- **Expected JSON Payload**:
  ```json
  {
    "status": "Healthy",
    "service": "TradeYar-AI",
    "api": "Online",
    "mt5": "Connected",
    "intelligence": "Ready",
    "worker": "Running",
    "research_worker": "Running",
    "intelligence_worker": "Running",
    "shadow_worker": "Running",
    "shadow_trading": "Active",
    "timestamp": "2026-07-31T12:00:00.123456"
  }
  ```
