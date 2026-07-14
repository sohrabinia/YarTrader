# RG_V3_AI Autonomous Financial Intelligence Platform

## Overview
The **RG_V3_AI Platform** is a production-ready, highly-decoupled, and strictly non-trading Autonomous Financial Intelligence Platform. Built using **Python 3.12**, it adheres strictly to the **APES-FIN Clean Architecture** standard, ensuring absolute domain isolation with **zero execution leakage**.

This system is strictly descriptive, analytical, and diagnostic; it contains **zero execution or trade placement logic**.

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
  └── Application/   - Backtesting, demo scenario platform, shadow mode live tracking, and dashboard
```

---

## 2. Comprehensive Master Guides
To get started developing, deploying, or testing the platform, refer to our comprehensive documentation guides:
* **[Developer Guide](docs/DEVELOPER_GUIDE.md)**: Workspace setup, package manifests, and codebase workflow.
* **[Architecture Guide](docs/ARCHITECTURE_GUIDE.md)**: Clean architecture, layer separation rules, and SOLID compliance.
* **[Deployment Guide](docs/DEPLOYMENT_GUIDE.md)**: Configuration parameters, secrets handling, and structured JSON logs.
* **[API Guide](docs/API_GUIDE.md)**: Scoped, versioned endpoints, and parameter middle validation.
* **[Testing Guide](docs/TESTING_GUIDE.md)**: Unit tests, coverage map, and safety leakage scanners.
* **[User Guide](docs/USER_GUIDE.md)**: Running backtesting loops, demo scenarios, and shadow live sessions.

---

## 3. Engineering Reviews & Audits (Version 1.0)
Before declaring Version 1.0 complete, the codebase has undergone thorough reviews:
* **[Final Architecture Review](docs/FINAL_ARCHITECTURE_REVIEW.md)**: Evaluates clean boundaries and SOLID conformity.
* **[Code Quality Review](docs/CODE_QUALITY_REVIEW.md)**: Verifies error handling, validations, and lack of duplicate/dead code.
* **[Intelligence Subsystem Review](docs/INTELLIGENCE_REVIEW.md)**: Focuses on indicators, evaluations, risk limits, and agent synergy.
* **[Dashboard Subsystem Review](docs/DASHBOARD_REVIEW.md)**: Audits aggregators, metrics consistency, and endpoint routing.
* **[Testing Subsystem Review](docs/TESTING_REVIEW.md)**: Details test coverage, metrics, and discoverability.
* **[Final Security Review](docs/SECURITY_FINAL_REVIEW.md)**: Certifies absolute non-trading boundaries and zero leakage.
* **[Documentation Review](docs/DOCUMENTATION_REVIEW.md)**: Audits overall consistency.

---

## 4. Operational Execution
### Run Platform Tests
Verify that all 1268+ automated tests pass cleanly:
```bash
PYTHONPATH=. pytest
```

### Access REST Endpoints
Ensure local servers and orchestrators run. Scoped endpoint responses:
* `GET /v1/health` for diagnostics.
* `GET /v1/metrics` for telemetry performance.
* `GET /v1/dashboard/shadow` for live shadow mode sessions.
