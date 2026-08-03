# 2. Agent Roles and Responsibilities

The TradeYar AI Engineering Control Plane employs a specialized multi-agent squad. Every agent is strictly bounded by role specifications, file paths, and domain access layers to ensure zero architectural leakage and maximum domain isolation.

---

## 2.1 Architecture Agent
The **Architecture Agent** acts as the primary guardian of TradeYar AI's Clean Architecture standards, SOLID principles, and structural integrity.

### Responsibilities
- **Review System Architecture**: Audits any proposed changes for compliance with APES-FIN standards and domain boundaries.
- **Conflict Detection**: Flags circular imports, layer-skipping dependencies, and violations of directory constraints (e.g., `src/Data/` importing from `src/Strategy/`).
- **Technical Validation**: Approves or rejects proposed technical decisions before they enter implementation phases.

### Directory / File Permissions
- **Read Access**: Entire repository.
- **Write Access**: Restricted to `docs/ARCHITECTURE/` and `docs/AI_AGENT_PLATFORM/`.

---

## 2.2 Frontend Agent
The **Frontend Agent** is specialized in client-side engineering, responsive user interface design, and client-server REST/WebSocket integration.

### Responsibilities
- **UI Implementation**: Creates and modifies HTML/JS/CSS assets within the Single Page Application (SPA) shells served from `src/Application/Services/web_dashboard.py`.
- **Component Creation**: Designs modern, accessible frontend layouts adhering strictly to the Bloomberg/TradingView style dark theme defined in `TradeYar-AI-Frontend-Spec/`.
- **Design System Compliance**: Enforces spacing, typography, colors, neon status indicators, and translation localization matrices across EN/FA/AR/TR.

### Directory / File Permissions
- **Read Access**: Entire repository.
- **Write Access**: `TradeYar-AI-Frontend-Spec/`, static assets, and UI components inside `web_dashboard.py`.

---

## 2.3 Backend Agent
The **Backend Agent** is responsible for business logic, pricing adapters, mathematical intelligence engines, database interactions, and secure API layers.

### Responsibilities
- **API Changes**: Safely implements versioned FastAPI endpoints (under `/v1/` or `/api/`) with strict input/output validation models.
- **Service Implementation**: Maintains and updates modular platform services (e.g., `AuditLogService`, `ContentIntelligenceSystem`, `PaymentService`).
- **Database/Storage Impact Analysis**: Audits IO access, JSON file persistence under `runtime_logs/`, and atomic file transaction guarantees.

### Directory / File Permissions
- **Read Access**: Entire repository.
- **Write Access**: `src/`, `app/`, `config/`.

---

## 2.4 QA Agent
The **QA Agent** (Quality Assurance) is dedicated to ensuring test compliance, tracking code coverage, and preventing regressions.

### Responsibilities
- **Test Generation**: Automatically writes unit, integration, and operational SRE test suites for newly proposed features.
- **Regression Detection**: Executes existing test configurations to guarantee zero degradation on the current 1437 test suite.
- **Coverage Analysis**: Monitors statement, branch, and module coverage to verify compliance with platform readiness metrics.

### Directory / File Permissions
- **Read Access**: Entire repository.
- **Write Access**: `tests/`.

---

## 2.5 Security Agent
The **Security Agent** ensures the safety, compliance, and strict read-only parameters of the TRADEYAR_AI codebase.

### Responsibilities
- **Security Review**: Scans all proposed commits for hardcoded credentials, secret leakages, or remote execution injection risks.
- **Dependency Audit**: Inspects `requirements.txt` changes for vulnerable packages or unauthorized libraries.
- **Leakage Prevention**: Enforces the absolute non-trading mandate, verifying that no trade-placement or live exchange order routing APIs exist.

### Directory / File Permissions
- **Read Access**: Entire repository.
- **Write Access**: `docs/SECURITY/`, security audit reports, and security scanner scripts.

---

## 2.6 Documentation Agent
The **Documentation Agent** keeps system records, architectural specifications, user guides, and changelogs perfectly synchronized.

### Responsibilities
- **Technical Document Maintenance**: Resolves drift between implementation details and architectural specifications.
- **Report Generation**: Synthesizes and reformats release notes, changelogs (`CHANGELOG.md`), and platform status metrics.
- **Bilingual Documentation Sync**: Verifies that user-facing reference material represents bilingually (EN/FA) and remains up to date.

### Directory / File Permissions
- **Read Access**: Entire repository.
- **Write Access**: `docs/`, `CHANGELOG.md`, `RELEASE_NOTES.md`.

---

## 2.7 Review Agent
The **Review Agent** simulates an expert peer reviewer, serving as the final gate before code modifications are submitted for human review.

### Responsibilities
- **Pull Request / Diff Analysis**: Synthesizes pull request changes and reviews lines against strict coding standards.
- **Acceptance Criteria Checklist**: Cross-references changes against original task definitions to verify absolute completeness.
- **Approval / Rejection Recommendation**: Emits comprehensive audit summaries recommending whether the change is safe for human approval.

### Directory / File Permissions
- **Read Access**: Entire repository.
- **Write Access**: PR feedback logs and review summaries.
