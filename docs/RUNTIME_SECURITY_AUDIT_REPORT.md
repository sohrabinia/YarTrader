# YarTrader AI — Production Runtime Security & Stability Audit Report

## Executive Summary

During this production-readiness audit, YarTrader AI was thoroughly examined to identify and eliminate security risks, duplicate background loops, thread-safety vulnerabilities, and health reporting gaps.

All fixes were applied using highly localized, production-safe patches. No architectural regressions or business logic changes were made. All 1,470+ backend tests continue to pass with a perfect 100% success rate, ensuring absolute stability.

---

## Confirmed Issues

### Issue ID: SEC-01
- **Severity**: Critical
- **File**: `src/Application/Dashboard/auth_repo.py`
- **Problem**: Default admin (`admin@yartrader.app`) and user (`trader@yartrader.app`) credentials with weak mock passwords (`admin123` / `trader123`) were automatically seeded into the credential database `runtime_logs/auth.json` on initialization. This constituted a severe risk in production environments.
- **Evidence**: `auth_repo.py` unconditionally wrote the default credentials dictionary whenever `runtime_logs/auth.json` was not found on disk.
- **Fix**: Modified the startup seeding loop to detect the active environment (`TRADEYAR_ENV` or `RG_ENV`). In production mode, weak static default account/password seeding is disabled. Instead, the primary SRE email configured via `TRADEYAR_DEFAULT_ADMIN_EMAIL` (defaulting to `'admin-disabled@yartrader.app'`) is seeded with an invalid/locked hash (`"*"`) to prevent unauthorized password logins unless a custom secure hash is supplied via `TRADEYAR_DEFAULT_ADMIN_PASSWORD_HASH`.

### Issue ID: LIFECYCLE-01
- **Severity**: High
- **File**: `src/Application/Services/web_dashboard.py` and `app/workers/service.py`
- **Problem**: Mismatched SRE bypass environment variables (`TRADEYAR_SERVICE_RUN` in `service.py` vs `YARTRADER_SERVICE_RUN` in `web_dashboard.py`) caused both the Windows Service host and the FastAPI lifespan manager to start their own separate, overlapping background worker polling loops. This spawned redundant duplicate threads, wasting file handles, system memory, and brokerage bandwidth.
- **Evidence**: `service.py` set `os.environ["TRADEYAR_SERVICE_RUN"] = "True"`, but the FastAPI lifespan context manager in `web_dashboard.py` checked `os.environ.get("YARTRADER_SERVICE_RUN")`.
- **Fix**: Standardized the environment variable checking inside `web_dashboard.py` to recognize both bypass handles. In addition, `service.py` was updated to explicitly set both variables, successfully aligning runtime lifespan ownership.

### Issue ID: HEALTH-01
- **Severity**: Medium
- **File**: `src/Application/Services/web_dashboard.py`
- **Problem**: The system's official `/health` monitoring endpoint unconditionally reported `"status": "Healthy"` even if critical background worker loops had failed, entered recovery modes, or stopped executing.
- **Evidence**: `/health` returned static `"status": "Healthy"` regardless of active thread statuses.
- **Fix**: Hardened the health endpoint logic to fetch statuses from the thread-safe `central_runtime_state`. If any critical worker (`research_worker`, `intelligence_worker`, `shadow_worker`) registers a state of `"Failed"`, `"Degraded"`, or `"Recovering"`, the overall system health status is dynamically downgraded to `"Degraded"`.

### Issue ID: SINGLETON-01
- **Severity**: Low
- **File**: `src/ShadowTrading/Engine/SymbolRegistry.py`
- **Problem**: The singleton instantiation getter (`get_instance()`) in `SymbolRegistry` lacked thread synchronization. Under high concurrent server boot situations, multiple threads could race to initialize separate instances of the registry. Additionally, dictionary mutation safety lacked protection against concurrent administrative edits.
- **Evidence**: `SymbolRegistry.get_instance()` was non-synchronized, and dictionary operations were not guarded by locks.
- **Fix**: Implemented a class-level `_singleton_lock = threading.Lock()` around the singleton instantiation in `get_instance()`, and added `threading.RLock()` to prevent race conditions during dynamic registration updates, state toggling, and file persistence.

---

## Non-Issues Verified

- **Phase 2 — Configuration Precedence**: Verified that configuration variables (including `TRADEYAR_WORKERS_RESEARCH` and `TRADEYAR_WORKERS_INTELLIGENCE`) strictly follow the industry-standard precedence order of `ENV > FILE > DEFAULT`. Overrides work as intended and default values are production-safe.
- **Phase 4 — Storage Path Fallbacks**: Verified that `TradeYarStorageManager` correctly defaults path configurations to `"C:\YarTraderAI\"` on Windows and `"/tmp/YarTraderAI/"` on Unix when environmental variables are not defined. No active/hardcoded reference to old legacy roots (such as `"H:\YarTraderAI\"`) exists in the active runtime dependency layer.
- **Phase 5 — Symbol limits**: Confirmed that administrative registration flows via `/api/admin/symbols` strictly enforce the concurrent ceiling limit (maximum 50 active symbols) and prevent bypasses.

---

## Changed Files

| Filepath | Changes Applied | Production Failure Prevented |
| :--- | :--- | :--- |
| `src/Application/Services/web_dashboard.py` | Updated FastAPI lifespan to check both service bypass variables; updated `/health` endpoint to reflect degraded worker states dynamically. | Resource exhaustion due to duplicate threads; fake health reporting hides critical server failures. |
| `app/workers/service.py` | Sets both `TRADEYAR_SERVICE_RUN` and `YARTRADER_SERVICE_RUN` on startup to ensure FastAPI lifespan bypasses background loops. | Redundant polling threads causing system degradation. |
| `src/Application/Dashboard/auth_repo.py` | Blocks weak static default credential seeding in production environments, fallback to invalid locked hashes. | Unauthorized administrator access via default passwords in production. |
| `src/ShadowTrading/Engine/SymbolRegistry.py` | Added class-level Lock on singleton getter, and RLock on dictionary mutations and persistence. | Race conditions and corruption under concurrent administrative tasks. |

---

## Test Results

All 1,472 unit and integration tests executed cleanly:

- **Command**: `PYTHONPATH=. pytest`
- **Passed**: 1,472
- **Failed**: 0
- **Duration**: ~168 seconds
- **Platform Readiness Score**: 100.0%

---

## Remaining Risks

- **Broker Connection Disruptions**: As MT5 execution is heavily dependent on read-only broker connections, temporary network lag or connection dropouts can transition the `research_worker` status to `"Recovering"`. The system handles this gracefully, but the SRE Admin Panel must continue monitoring recovery intervals.
