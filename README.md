# YarTrader Autonomous Financial Intelligence Platform

## Overview
The **YarTrader Platform** is a production-ready, highly-decoupled, and Autonomous Financial Intelligence Platform with isolated research, backtesting, signal, and DEMO execution boundaries. Built using **Python 3.12**, it adheres strictly to the **APES-FIN Clean Architecture** standard, ensuring absolute domain isolation with **zero execution leakage**.

The platform contains execution-capable DEMO infrastructure, but LIVE trading is hard-disabled. MT4 DEMO execution is restricted to the authorized DEMO account and XAUUSD; Signal/real-account MT4 access is read-only.

---

## 1. Directory Structure & Layout
The repository is organized cleanly to enforce layer boundaries and prevent circular dependencies:

```
src/
  ├── Core/          - Fundamental entity definitions
  ├── Data/          - Adapters, providers, normalizers, and reliability trackers
  ├── Research/      - Indicator calculators, technically pattern detectors, and qualitative insights
  ├── Strategy/      - Concept scoring and candidate ranking evaluations
  ├── Risk/          - Volatility-scaled constraints and exposure auditing
  ├── Decision/      - Advanced context-aware synthesis, conflict resolution, and evidence tracing
  ├── Learning/      - Continuous feedback optimization suggestion logging
  └── Application/   - Backtesting, DEMO/Signal workflows, learning, and dashboard
```

---

## 2. Comprehensive Master Guides
To get started developing, deploying, or testing the platform, refer to our comprehensive documentation guides under nested categories:
* **[Developer Guide](docs/DEVELOPER_GUIDE.md)**: Workspace setup, package manifests, and codebase workflow.
* **[Architecture Guide](docs/ARCHITECTURE/ARCHITECTURE_GUIDE.md)**: Clean architecture, layer separation rules, and SOLID compliance.
* **[Deployment Guide](docs/DEPLOYMENT/DEPLOYMENT_GUIDE.md)**: Configuration parameters, secrets handling, and structured JSON logs.
* **[Storage Isolation Specification](docs/DEPLOYMENT/TRADEYAR_STORAGE_ISOLATION.md)**: Details TradeYar AI storage root (H:\TradeYarAI\) path isolation.
* **[API Guide](docs/API_GUIDE.md)**: Scoped, versioned endpoints, and parameter middle validation.
* **[Testing Guide](docs/TESTING/TESTING_GUIDE.md)**: Unit tests, coverage map, and safety leakage scanners.
* **[User Guide](docs/USER_GUIDE.md)**: Running backtesting loops, DEMO scenarios, Signal workflows, and learning cycles.

---

## 3. Engineering Reviews & Audits (Version 1.0)
Before declaring Version 1.0 complete, the codebase has undergone thorough reviews placed in subfolders:
* **[Final Architecture Review](docs/ARCHITECTURE/FINAL_ARCHITECTURE_REVIEW.md)**: Evaluates clean boundaries and SOLID conformity.
* **[Code Quality Review](docs/AUDIT/CODE_QUALITY_REVIEW.md)**: Verifies error handling, validations, and lack of duplicate/dead code.
* **[Intelligence Subsystem Review](docs/AUDIT/INTELLIGENCE_REVIEW.md)**: Focuses on indicators, evaluations, risk limits, and agent synergy.
* **[Dashboard Subsystem Review](docs/DASHBOARD/DASHBOARD_REVIEW.md)**: Audits aggregators, metrics consistency, and endpoint routing.
* **[Testing Subsystem Review](docs/TESTING/TESTING_REVIEW.md)**: Details test coverage, metrics, and discoverability.
* **[Final Security Review](docs/SECURITY/SECURITY_FINAL_REVIEW.md)**: Reviews execution isolation, LIVE hard-locks, and safety boundaries.
* **[Documentation Review](docs/DOCUMENTATION_REVIEW.md)**: Audits overall consistency.

---

## 4. Operational Execution
### Run Platform Tests
Run the repository's automated test suite and verify the result on the exact commit under review:
```bash
PYTHONPATH=. pytest
```

### Access REST Endpoints
Ensure local servers and orchestrators run. Scoped endpoint responses:
* `GET /v1/health` for diagnostics.
* `GET /v1/metrics` for telemetry performance.
* `GET /v1/dashboard` for dashboard diagnostics and learning/runtime status.
