# YarTrader Autonomous Trading Baseline Freeze Report

**Date:** 2026-08-22
**Authority:** Technical Manager Release Directive
**Target Module:** Autonomous Demo Trading + Trade Lifecycle + Continuous Learning + Runtime Proof

---

## 1. Baseline Git State

```text
branch: jules-12194981418183937295-3f964fe2
commit_head: 729813aca5d3acc0e4f2e6d17f50022c7e948854
commit_subject: Merge pull request #189 from sohrabinia/jules-gate0-gate1-gate2-fractal-research-15456059273577760076
status: clean (working tree clean, 0 modified files)
git_diff_check: clean (0 trailing whitespace or merge conflict artifacts)
```

### Recent Commit History (Top 5)
```text
729813a Merge pull request #189 from sohrabinia/jules-gate0-gate1-gate2-fractal-research-15456059273577760076
```

---

## 2. Baseline Test Suite Verification

```text
Command: python3 -m pytest tests/YarTrader.Tests/ -q
Result: 1,463 passed, 1,239 warnings, 17 subtests passed in 183.16s
Pass Rate: 100.0%
Regressions: 0
```

---

## 3. Runtime Environment & System Configuration

```text
OS Environment: Linux sandbox (Containerized non-Windows)
Python Version: 3.12.13
Primary Storage Manager Root: /tmp/YarTraderAI/
  - Logs Dir: /tmp/YarTraderAI/Logs
  - Reports Dir: /tmp/YarTraderAI/Reports
  - Runtime Dir: /tmp/YarTraderAI/Runtime
  - Cache Dir: /tmp/YarTraderAI/Cache
  - Data Dir: /tmp/YarTraderAI/Data
  - Diagnostics Dir: /tmp/YarTraderAI/Diagnostics

MT5 Connectivity State:
  - Adapter Mode: Sandbox / Non-Windows
  - Health Check: Disconnected (Native MT5 IPC unavailable on Linux container)
  - Demo Account Target: 52961173 @ Alpari-MT5-Demo
  - Live Order Path: Hard-isolated (LIVE_TRADING_ENABLED=False)

Safety & Governance Flags:
  - LIVE_TRADING_ENABLED: False (Fail-closed)
  - YARTRADER_ENV: development
  - MT5_DEMO_MODE: True
  - Kill Switch (autonomous_demo_trading_enabled): True (default active)
```

---

## 4. Initial Runtime Component State

| Subsystem | State | Notes |
| :--- | :--- | :--- |
| **Research Runtime** | Operational | Multi-symbol / Multi-TF polling loop active via `ResearchWorker`. |
| **Decision Intelligence** | Dual Engines Detected | `src/Decision/Intelligence/engine.py` and legacy `src/Decision/engine.py`. |
| **Execution Intelligence Core** | Operational | Calculates narrative, liquidity, zones, alignment, similarity, and advisory plan. |
| **Demo Execution Engine** | Operational | Connects to `RealMT5BrokerAdapter` and enforces `DemoExecutionGate`. |
| **Demo Safety Gate** | Enforced | 9 SRE DEMO safety rules verified with fail-closed behavior on disconnected terminal. |
| **Pattern Memory** | Operational | Persisted under `runtime_logs/fractal_pattern_memory.json`. |
| **Trade Journal** | Partial | Shadow trades persisted in `runtime_logs/shadow_trades.json`; unified journal pending. |
| **Dashboard State** | Integrated | API endpoints bound in `src/Application/Services/web_dashboard.py`. |

---

## 5. Certification

This baseline report freezes the initial state prior to code changes for the Master Task. All future modifications will be measured against this frozen baseline.
