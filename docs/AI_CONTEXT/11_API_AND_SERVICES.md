# 11. API and Services

## 1. REST Endpoint Specifications

All endpoints are versioned under `/v1` and handle strongly-typed DTOs:

*   `GET /v1/health`: Returns system health, connection status, and server time.
*   `GET /v1/metrics`: Returns cumulative API request counts, latency metrics, and error logs.
*   `POST /v1/intelligence`: Ingests a request for target asset analysis and returns compiled sentiment.
*   `GET /v1/dashboard/overview`: Aggregates platform overview metrics and audit check results.
*   `GET /v1/dashboard/agents`: Gathers registered agents operational histories and workload metrics.
*   `GET /v1/dashboard/decisions`: Gathers recent decision records and trace paths.
*   `GET /v1/dashboard/providers`: Gathers data source reliability, health scores, and latency metrics.

---

## 2. Authentication & Authorization

*   **Authentication Abstraction**: Validates incoming request tokens against local registers.
*   **Authorization Abstraction**: Evaluates permissions and denies access if required scopes are missing.

---

## 3. Middleware Validation

Request payloads are processed through middleware validations checking for formatting correctness, required parameters, and execution keywords leakage.

---

## 4. Cross References
*   [02_SYSTEM_ARCHITECTURE.md](02_SYSTEM_ARCHITECTURE.md)
*   [10_SECURITY_MODEL.md](10_SECURITY_MODEL.md)
*   [12_ADMIN_DASHBOARD.md](12_ADMIN_DASHBOARD.md)
