# YarTrader Final Release Evidence Manifest

## Overview

This document serves as the immutable-style **Final Release Evidence Manifest** for the **YarTrader Platform** under the Release Candidate / Feature Freeze directive (`FINAL CLOSURE / EVIDENCE / RELEASE GATE TASK`).

---

## 1. Repository & Commit Provenance

- **Git HEAD Commit:** `729813aca5d3acc0e4f2e6d17f50022c7e948854`
- **Git Branch:** `jules-6891381065580437406-43b76f4f`
- **Repository Remote:** `https://github.com/sohrabinia/YarTrader`
- **Worktree Conflicts:** `0` (`git diff --name-only --diff-filter=U` clean)
- **Host OS Environment:** Linux 6.6.137+ (Sandbox Container)
- **Python Version:** Python 3.12.13
- **Node.js Version:** v20.19.0 (Vite v5.4.21)

---

## 2. Core Evidence Matrix

| Area / Subsystem | Claimed Capability | Forensic Classification | Supporting Artifact / Evidence Path | Blocker / Reason |
| :--- | :--- | :--- | :--- | :--- |
| **Git Identity** | Source Checkout Frozen | `TEST-PROVEN` | `729813aca5d3acc0e4f2e6d17f50022c7e948854` | None |
| **Test Baseline** | 1,583 passed + 17 subtests | `TEST-PROVEN` | `python -m pytest tests -q` (186.55s) | Reconciled 1,594 -> 1,600 |
| **Gate 3 Provenance** | `base_detector_v1.1.0` | `TEST-PROVEN` | `src/Research/Brain/fractal_base_detection_engine.py` | None |
| **Gate 3 Dataset** | XAUUSD M1 Real Dataset | `EXTERNAL-BLOCKER` | `runtime_logs/research_center/Gate3_BaseDetectionReport_REAL.json` | `data/research/xauusd_m1_real.json` missing in container |
| **Static Live Safety** | `LIVE_TRADING_ENABLED=False` | `TEST-PROVEN` | `src/Execution/Safety/safety_gate.py` | None (Hardcoded Fail-Closed) |
| **MT5 Pre-Check Safety** | `order_check()` Fail-Closed | `TEST-PROVEN` | `src/Execution/Adapters/mt5_adapter.py` | None (Halts `order_send` on error) |
| **Dynamic Filling Mode** | Symbol-Aware FOK/IOC/RETURN | `TEST-PROVEN` | `src/Execution/Adapters/mt5_adapter.py` | None |
| **Comment Normalization** | ASCII <= 31 chars | `TEST-PROVEN` | `src/Execution/Adapters/mt5_adapter.py` | None |
| **Storage Root Isolation** | `TradeYarStorageRoot` | `TEST-PROVEN` | `src/Application/Deployment/storage.py` | None |
| **Telegram OIDC Auth** | HMAC-SHA256 Signature Check | `IMPLEMENTED` | `/api/auth/telegram` in `web_dashboard.py` | Returns 503 `CONFIG_REQUIRED` when unconfigured |
| **Auth & Session Security** | PBKDF2-SHA256 & Session Tokens | `TEST-PROVEN` | `src/Application/Dashboard/auth_service.py` | None |
| **Role-Based Authorization** | Tier Gating (Free/Pro/Inst) | `TEST-PROVEN` | `src/Application/Services/web_dashboard.py` | None |
| **Wallet & Ledger** | Precision Balance Ledger | `TEST-PROVEN` | `src/Application/Dashboard/ledger_manager.py` | Explicit `DEMO/SIMULATED` labeling |
| **Prop Trading Rules** | Challenge Evaluation | `TEST-PROVEN` | `src/Application/Services/web_dashboard.py` | None |
| **Signal Engine** | Pure Price Action Analysis | `TEST-PROVEN` | `src/Research/analysis_pipeline.py` | None |
| **Shadow Trading** | Virtual Capital Paper Execution | `TEST-PROVEN` | `src/ShadowTrading/Engine/PredictiveShadowEngine.py` | 100% isolated from real MT5 `order_send` |
| **DEMO Execution Engine** | Autonomous DEMO Execution | `TEST-PROVEN` | `src/Execution/Services/demo_execution_engine.py` | Routed on Account `52961173` on `Alpari-MT5-Demo` |
| **Post-Trade Learning** | Sample-Size Protection | `TEST-PROVEN` | `src/Learning/Services/experience_memory.py` | `N < 5 → OBSERVE_ONLY` guard |
| **Frontend Production Build** | React SPA (Vite v5.4.21) | `TEST-PROVEN` | `cd trader-terminal && npm run build` | 0 compilation errors (`dist/` generated) |
| **i18n Locale Parity** | 100% Parity across 4 locales | `TEST-PROVEN` | `trader-terminal/public/locales/` | 161 keys each in `fa`, `en`, `tr`, `ar` |
| **Native Windows MT5 Pre-Flight** | Terminal Process & IPC Link | `NOT-PROVEN` | `docs/AUTONOMOUS_EXECUTION_FINAL_FORENSIC_REPORT.md` | Linux Sandbox Container (Non-Windows) |
| **Real MT5 Position Open/Close** | Forward Demo Order Execution | `NOT-PROVEN` | `docs/AUTONOMOUS_EXECUTION_FINAL_FORENSIC_REPORT.md` | Native MT5 terminal IPC unavailable |
| **Independent P&L Reconciliation** | Field-by-Field Deal Query | `NOT-PROVEN` | `docs/AUTONOMOUS_EXECUTION_FINAL_FORENSIC_REPORT.md` | Awaiting native Windows MT5 execution |

---

## 3. Final Release Verdict

```text
FINAL RELEASE VERDICT:
PUBLIC RELEASE BLOCKED — Awaiting Native Windows MT5 DEMO Execution Evidence
```
