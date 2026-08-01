# TradeYar AI v3.2 — Enterprise Production Deployment Guide
## Windows Server 2022 & IIS (Internet Information Services) Reverse Proxy

This guide contains the official, step-by-step procedures to deploy, secure, and maintain `TradeYar AI v3.2` on an enterprise Windows Server 2022 environment using IIS as a secure Reverse Proxy.

---

## 1. Hosting Model Compliance & Architecture

TradeYar AI employs a **Hybrid Decoupled Hosting Model**:

1. **TradeYar-AI Python Runtime (Application Core)**:
   Operates entirely as a native, 24/7 background Windows Service (`TradeYar-AI`). It is registered, monitored, and auto-recovered by the Windows Service Control Manager (SCM) or NSSM. It listens locally on `http://127.0.0.1:8000`.
2. **IIS (Internet Information Services) Web Server**:
   Functions purely as an **Enterprise Reverse Proxy and SSL Terminator**. IIS does **NOT** host or execute the Python runtime directly (e.g., no wfastcgi, no direct Python CGI handles). It handles HTTPS (Port 443) incoming connections from public domains, terminates SSL/TLS, applies enterprise security headers, serves static caches, and reverse-proxies requests to the local Python Service on `http://127.0.0.1:8000`.

This hybrid layout ensures maximum process isolation, SRE high-availability, zero-downtime restarts, and guarantees compliance with APES-FIN simulation-only sandboxing.

---

## 2. Server Prerequisites

Ensure the target Windows Server 2022 (or 2019) instance meets the following minimum requirements:

### A. Core Software Requirements
- **Operating System**: Windows Server 2022 (Standard or Datacenter)
- **Python**: v3.10 or v3.12 (64-bit). Installed with "Add python.exe to PATH" and pip enabled.
- **IIS Features**:
  - Web Server (IIS) Role enabled.
  - IIS Management Console.
- **IIS Add-on Modules (Mandatory)**:
  - **URL Rewrite Module 2.1** (Download from Microsoft IIS site).
  - **Application Request Routing (ARR) 3.0** (Download from Microsoft IIS site).
- **PostgreSQL**: v14, v15, or v16.
- **Redis**: v6.2+ or v7.x (e.g., Redis on Windows via Memurai, MSI installer, or running inside WS2/Docker).

### B. Hardware Sizing Checklist
- **CPU**: Minimum 4 Cores (Intel Xeon / AMD EPYC equivalent).
- **Memory (RAM)**: Minimum 8 GB (16 GB recommended for high-load multi-episode replays).
- **Disk Storage**: 50 GB SSD or NVMe with storage isolation configured on a dedicated drive.

---

## 3. Step-by-Step IIS Reverse Proxy & SSL Setup

Follow these steps to configure IIS as a secure reverse proxy:

### Step 3.1: Enable the IIS Web Server Role
If not already installed:
1. Open **Server Manager**.
2. Click **Add roles and features**.
3. Select **Role-based or feature-based installation**.
4. Choose **Web Server (IIS)** under Server Roles and complete the wizard.

### Step 3.2: Install URL Rewrite & ARR
1. Install **URL Rewrite Module 2.1**.
2. Install **Application Request Routing (ARR) 3.0**.
3. Open IIS Manager, click on the Server Node, and select **Application Request Routing Cache**.
4. On the right-hand panel, click **Server Proxy Settings**.
5. Check the **Enable proxy** box and click **Apply**.

### Step 3.3: Configure the Physical Directory and Web.config
Execute the automated proxy setup script or manually place the configuration file:
1. Run the following command in an Administrator PowerShell session:
   ```powershell
   .\scripts\setup_iis_reverse_proxy.ps1
   ```
2. This creates the folder `C:\inetpub\wwwroot\TradeYarAI` and generates a secure, production-hardened `web.config` file.

### Step 3.4: IIS Site and SSL Binding
1. Open **IIS Manager** (`inetmgr`).
2. Right-click **Sites** -> **Add Website**.
   - **Site name**: `TradeYarAI`
   - **Application pool**: `TradeYarPool` (Ensure Managed Pipeline Version is set to **No Managed Code**).
   - **Physical path**: `C:\inetpub\wwwroot\TradeYarAI`
   - **Binding Type**: `https`
   - **Port**: `443`
   - **IP Address**: All Unassigned
   - **Host name**: `yourdomain.com`
3. Under **SSL certificate**, select your imported SSL/TLS Certificate (e.g., Let's Encrypt or Wildcard certificate).
4. Click **OK**.

### Step 3.5: DNS Domain Configuration
1. Log in to your DNS provider (e.g., Cloudflare, GoDaddy).
2. Create an **A Record** pointing `yourdomain.com` to the public IPv4 address of your Windows Server.
3. Configure your firewall to allow traffic on port **80** (HTTP, for HTTPS redirects) and **443** (HTTPS).

---

## 4. Environment & Secrets Management (.env.production)

TradeYar AI requires an active `.env` file at the root.

1. Copy the production template `.env.production` to `.env`:
   ```powershell
   Copy-Item .env.production .env
   ```
2. Open `.env` and configure the secure production parameters:
   - Generate a strong random JWT secret using openssl:
     ```bash
     openssl rand -hex 32
     ```
   - Populate PostgreSQL connection parameters and secure tokens.
   - Configure MT5 read-only credentials (with standard disabled active trading modes).

*Note: The `.env` file is excluded from git tracking to prevent credential leaks.*

---

## 5. Automated Backups & Disaster Recovery

Preserving production database records, platform logs, and cognitive models is a key SRE requirement.

### A. Lightweight Automated Backup Script
Create a scheduled task on Windows Server using a script similar to this:
`scripts/backup_database.ps1` (Example representation):
```powershell
# TradeYar AI Database & Configuration Backup Script
$BackupDir = "C:\Backups\TradeYarAI"
$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$DbBackupFile = "$BackupDir\tradeyar_db_$Timestamp.sql"
$ConfigBackupFile = "$BackupDir\tradeyar_config_$Timestamp.zip"

# Ensure backup directory exists
if (-not (Test-Path $BackupDir)) {
    New-Item -ItemType Directory -Path $BackupDir | Out-Null
}

# 1. Backup PostgreSQL Database
$env:PGPASSWORD = "YOUR_SECURE_POSTGRES_PASSWORD"
& "C:\Program Files\PostgreSQL\16\bin\pg_dump.exe" -h 127.0.0.1 -U tradeyar_app_user -F c -b -v -f $DbBackupFile tradeyar_prod_db

# 2. Backup configuration files
Compress-Archive -Path "C:\Projects\TradeYar_AI\.env", "C:\Projects\TradeYar_AI\config\production.yaml" -DestinationPath $ConfigBackupFile

# 3. Clean up backups older than 14 days
Get-ChildItem $BackupDir | Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-14) } | Remove-Item -Force

Write-Host "Backup completed successfully!" -ForegroundColor Green
```

To schedule this, open **Windows Task Scheduler** and create a basic task:
- **Trigger**: Daily at 02:00 AM.
- **Action**: Start a program -> `powershell.exe` with arguments `-File C:\Projects\TradeYar_AI\scripts\backup_database.ps1`.

### B. Disaster Recovery Restoration Procedure
1. **Prepare clean Server Node**: Re-install Windows Server 2022, Python 3.12, IIS, PostgreSQL, and Redis.
2. **Deploy Codebase**: Clone code repository or copy deployment zip package to `C:\Projects\TradeYar_AI`.
3. **Restore Database**:
   ```cmd
   pg_restore -h 127.0.0.1 -U tradeyar_app_user -d tradeyar_prod_db C:\Backups\TradeYarAI\tradeyar_db_latest.sql
   ```
4. **Restore Configuration**: Extract `.env` and `production.yaml` back into their respective folders.
5. **Re-register Service**: Run `.\scripts\deploy_service.ps1`.
6. **Verify Health**: Run `.\scripts\health_check.ps1` to ensure green statuses across all endpoints.

---

## 6. Rollback Operational Guide

If a production update introduces issues, execute the following graceful rollback procedure:

1. **Stop Windows Service**:
   ```powershell
   .\scripts\stop_service.ps1
   ```
2. **Revert Artifacts to Previous Stable Git State**:
   ```powershell
   git reset --hard v3.1.0-hardened
   git clean -fd
   ```
3. **Restore Environment Snapshot**:
   If configurations changed, copy the previous backed up `.env` from the backup vault.
4. **Rebuild Dependencies**:
   ```powershell
   pip install -r requirements.txt
   ```
5. **Start Windows Service**:
   ```powershell
   .\scripts\start_service.ps1
   ```
6. **Verify Baseline Health State**:
   Run health diagnostics to verify all subsystems revert to stable `HEALTHY` mode:
   ```powershell
   .\scripts\health_check.ps1
   ```
