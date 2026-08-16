# YarTrader V1 Identity Migration Execution Plan

## Executive Summary
This document establishes the safety gate, inventory scope, runtime risk assessment, rollback strategy, and validation criteria for the complete, production-safe identity migration from legacy **TradeYar / TRADEYAR** to **YarTrader / YARTRADER** across all repository tiers.

---

## Migration Scope & Inventory Overview
* **Active Runtime Modules:** `app/core/config.py`, `app/core/logging.py`, `app/workers/service.py`, `src/Infrastructure/Configuration/settings.py`, `src/Application/Deployment/storage.py`, `src/Application/Services/web_dashboard.py`, `src/ShadowTrading/Engine/PredictiveShadowEngine.py`.
* **Configurations & Automation Scripts:** `config/system_limits.yaml`, `config/market_universe.yaml`, `scripts/*.ps1`, `server_watchdog.py`.
* **Validation & Test Suites:** `src/Application/Validation/services.py`, `tests/runtime/*`, `tests/YarTrader.Tests/*`.
* **Active Documentation:** Root markdown specifications (`FEATURE_CATALOG.md`, `RELEASE_NOTES.md`, `ARCHITECTURE_REALITY_REPORT.md`, `CHANGELOG.md`) and operational runbooks under `docs/`.

---

## Runtime Risk Assessment & Mitigation
1. **Environment Variable Disruption:**
   * *Risk:* Unset `YARTRADER_*` variables in existing deployment scripts could break service initialization.
   * *Mitigation:* `src/Infrastructure/Configuration/compat.py` provides a controlled `get_env_compat` fallback emitting `logger.warning` deprecation notices while reading primary `YARTRADER_*` variables.
2. **Service Controller Registry (SCM) Misses:**
   * *Risk:* Windows SCM looking for `TradeYarAIWindowsService` during service restarts.
   * *Mitigation:* Class alias `TradeYarAIWindowsService = YarTraderWindowsService` maintained at module level in `app/workers/service.py`.

---

## Rollback Strategy
A git checkpoint tag `v1-before-final-identity-migration` is created prior to file modifications. In case of any unrecoverable runtime regression, state can be restored via:
```bash
git checkout v1-before-final-identity-migration
```

---

## Validation Criteria
* Zero active runtime/config occurrences of `TRADEYAR_*` or `TradeYar`.
* 100% test pass rate (`1,534 passed, 0 failed`).
* Production frontend build success in `trader-terminal/dist/`.
* Updated verification certificate in `docs/YARTRADER_FINAL_VERIFICATION_CERTIFICATE.md`.
