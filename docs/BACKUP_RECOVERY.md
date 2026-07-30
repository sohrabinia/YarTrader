# BACKUP & RECOVERY PLAN
**State Preservation and Data Durability Guide**

To ensure high availability, platform durability, and to preserve user subscription states, cost counters, and analytical logs, the following backup schedules must be automated.

---

## 1. Directory Structure Persistence
The following directories contain critical persistent data and must be included in backup archives:
1. **User Identity & State**: `runtime_logs/auth.json` (Includes registrations, passwords, subscription tier, and analytics).
2. **Cognitive Memories**: `runtime_logs/brain_memory/` (Includes discovered patterns, hypotheses, and validated concepts).
3. **Research Snapshots**: `runtime_logs/research_snapshots/` (Market analysis daily rotations).
4. **Operations Logs**: `logs/` (All separational file streams).

---

## 2. Backup Schedules
- **Daily Atomic Backup (Local)**:
  Configure a cron task or a Windows PowerShell scheduled script to compress the `runtime_logs/` folder at `00:00 UTC` and store it in an isolated secure partition on disk.
  ```powershell
  Tar -cf D:\Backups\tradeyar-daily-%date%.tar C:\TradeYarAI\runtime_logs\
  ```
- **Weekly Offsite Backup**:
  Transfer compressed backup archives to a secure cloud-based S3 bucket (or secure private backup server) with strict access permissions.

---

## 3. Disastrous Recovery Checklist
If the hosting server crashes or files become corrupted:

1. **Provision clean instance**: Build Windows Server 2022 and install Python 3.12.
2. **Fetch backup**: Retrieve the latest stable compressed `.tar` archive.
3. **Extract directories**: Extract files back into `C:\TradeYarAI\runtime_logs\`.
4. **Boot MetaTrader5**: Log in with Read-Only Investor credentials.
5. **Start FastAPI application**: Start NSSM or python runner.
6. **Verify Health**: Visit `/health` and confirm that all 5 monitors (API, MT5, AI, Storage, Background task) report green, healthy states.
