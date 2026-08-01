# Changelog — Version 3.0.0 (v3)
## TradeYar AI — Release v3.0.0 (Cognitive Brain v3 & SRE Infrastructure)

All notable changes during the transition from Version 2 (v2) to Version 3 (v3) are documented in this file.

---

## [3.0.0] - 2026-08-01

### Added
- **Production Server Watchdog (`server_watchdog.py`):**
  - Minimal dependency self-healing background supervisor script.
  - Automatic Garbage Collection (`gc.collect()`) triggered if system memory usage exceeds 85%.
  - Protective restart limit of 5 restarts within a sliding 10-minute window.
  - Transitions to `DEGRADED` status and dispatches simulated Telegram alerts under a 5-minute cooldown suppression filter if exceeded.
- **NSSM PowerShell Service Registry Script (`scripts/deploy_service.ps1`):**
  - Integrates NSSM for 24/7 service execution on Windows Server 2022.
  - Enforces `Automatic (Delayed Start)` service startup to let foundational Windows services initialize first.
  - Sets up stdout/stderr log output redirection and rotates logs automatically once file exceeds 10MB.
  - Locks the service execution directory explicitly to `C:\Projects\TradeYar_AI`.
- **FastAPI Health Diagnostics Endpoints:**
  - `GET /health/live`: Fast ping liveness status (`200 OK`).
  - `GET /health/ready`: Performs live ready probes checking API, read-only MT5 stream, and memory layer file integrity.
  - `GET /api/v1/health`: Detailed JSON diagnostic payload across subsystems, memory, and dependencies.
- **V2-to-V3 Release Documentation:**
  - `docs/PRODUCTION_HARDENING_AUDIT.md`: Pre-implementation audit mapping existing code and memory structures (Gate 1).
  - `docs/V2_TO_V3_MIGRATION_REPORT.md`: Data preservation, snapshot, and migration validation report.
  - `docs/CHANGE_INVENTORY.md`: Risk assessment and change records.

### Changed
- **Memory System (`src/Research/Brain/memory.py`):**
  - Added robust transactional write validations (JSON-validity check on temp writes before swap).
  - Added verified timestamped backup snapshotting (`create_snapshot` and `restore_snapshot`) with SHA-256 integrity checksums.
  - Hardened file-loading `load_all` against silent wipes. If a file is corrupt, it triggers an emergency rollback restoring from the latest valid snapshot. Wiping or starting from scratch is strictly forbidden.
- **Automated Verification Suite:**
  - Added dedicated unit tests under `tests/TRADEYAR_AI.Tests/Brain/test_architecture_integrity.py` validating snapshotting, rollbacks, and automatic disaster recovery.
  - Added health diagnostics test coverage under `tests/runtime/test_health_endpoint.py`.
  - Hardened concurrent test execution under `tests/runtime/test_health_status.py` using unit-mock dictionary patches.
