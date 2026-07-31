# TRADEYAR Risk Framework

The Risk Intelligence Framework assessed proposed portfolio allocations against predefined profiles and exposure models to guarantee total system safety.

---

## 1. Risk Framework Mission

The core mission of the Risk Framework is to:
* **Enforce Strict Multi-Factor Safety:** Audit allocations against single asset limits, total weight limits (leverage), and expected annualized volatility.
* **Support Historical Risk Auditing:** Track risk assessment histories (`RiskAssessmentFramework`) for advanced retrospective review.
* **Abstract Risk Profiles:** Support configurable low, moderate, and high risk profiles (`RiskProfile`) with modular parameters.

---

## 2. Dependencies and Direction

The Risk Layer depends on Core, Research, and Strategy packages. It maintains 100% independence from active trading execution, having no broker or transaction knowledge.
