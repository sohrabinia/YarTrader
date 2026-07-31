# TradeYar AI — Backup & Recovery Plan (RC-1)
**Date:** July 30, 2026
**Auditor:** Principal Software Architect & DevOps Lead
**Audit Phase:** Production Readiness Planning (Pure Verification — NO CODE CHANGES)

---

## 1. Introduction
This **Backup & Recovery Plan** defines the data preservation and recovery policies required to safeguard **TradeYar AI RC-1** system files, configuration states, and cognitive experience memories. It ensures that the system's learned market structures, experience files, and approved concepts can be recovered cleanly in the event of hardware or filesystem failure.

---

## 2. Backup Target Inventory
Below is the list of persistent data assets required for a complete system restoration:

| Asset Name | Source Path | Backup Priority | File Format | Details |
| :--- | :--- | :--- | :--- | :--- |
| **Raw Event Memory** | `runtime_logs/brain_memory/events_memory.json` | High | JSON | Chronicles objective detected price action structures |
| **Experience Memory** | `runtime_logs/brain_memory/experiences_memory.json` | Critical | JSON | Catalogs virtual trading decisions, actual outcomes, excursions, and Judge lessons |
| **Pattern Memory** | `runtime_logs/brain_memory/patterns_memory.json` | High | JSON | Tracks repeating historical structure occurrences |
| **Concept Memory** | `runtime_logs/brain_memory/concepts_memory.json` | Critical | JSON | Vetted, approved market concepts backed by ample evidence and approved by Judge |
| **Research Snapshots** | `runtime_logs/research_snapshots/*.json` | Medium | JSON | Rotated history of last 50 compiled research outputs |
| **System Configurations** | `configs/` | Medium | YAML / JSON | Operating configs and environment settings |

---

## 3. Backup Execution Policy

* **Methodology:** Snapshot replication.
* **Interval:** Daily at 00:00 UTC (during low market activity periods).
* **Storage Location:** Backups must be replicated off-site to a secure, encrypted object storage container (e.g. AWS S3 or private secure MinIO bucket) mapped outside the container hosts.
* **Retention Policy:**
  - Daily backups: Retain for 30 days.
  - Weekly backups: Retain for 12 weeks.
  - Monthly backups: Retain for 12 months.

### Automated Backup Script Template
The following command maps a daily tarball archive of memory and logs, and uploads it securely:
```bash
# Example Cron Backup SOP Execution (daily task)
tar -czf /backups/tradeyar_backup_$(date +%F).tar.gz configs/ runtime_logs/
```

---

## 4. Disaster Recovery & Restoration Procedures

### Scenario: Local Storage Corruption or JSON Parsing Exception
If a disk block error or crash causes a memory file (such as `concepts_memory.json`) to fail parsing during server boot, follow this procedure:

1. **Halt Process:** Shut down the FastAPI server process cleanly.
2. **Isolate Corrupted File:** Move the corrupted file to a quarantine directory for diagnostic analysis:
   ```bash
   mv runtime_logs/brain_memory/concepts_memory.json runtime_logs/brain_memory/concepts_memory.json.corrupted
   ```
3. **Fetch Latest Backup:** Download the last verified daily tarball from secure off-site object storage.
4. **Extract Targets:** Extract the clean backup files back to the target directory:
   ```bash
   tar -xzf /backups/tradeyar_backup_[LATEST_DATE].tar.gz -C /
   ```
5. **Execute Integrity Validation:** Execute the test suite to verify file parser compliance:
   ```bash
   pytest tests/RG_V3_AI.Tests/Brain/
   ```
6. **Re-Launch Service:** Start up the server and monitor logs to verify successful boot.

---

## 5. Recovery Time & Point Objectives

* **Recovery Point Objective (RPO):** 24 Hours. Maximum data loss in a worst-case disaster scenario is limited to the last 24 hours of cognitive learning runs.
* **Recovery Time Objective (RTO):** 1 Hour. The restoration process is fully automated via shell scripts, allowing complete environment reconstitution and startup in under 60 minutes.
