# TradeYar AI — Architecture Governance Standard

This document defines the architectural standards, checkgates, and compliance rules that must be followed by any development, extension, or AI system working on the TradeYar AI platform.

## 1. Core Principles

### 1.1 Strict Read-Only Passivity (APES-FIN Standard)
- No module within the codebase is permitted to initiate or execute active financial transactions, place orders, modify existing brokerage account parameters, or communicate with order-routing endpoints.
- Any simulated decision, strategy, or hypothesis must remain strictly virtual and local.

### 1.2 Absolute Decoupling of Analysis and Reality
- Direct price-action observation remains 100% subjective-free. No technical indicators, moving average signals, or predefined indicators are permitted within the core newborn market brain layer.
- Execution frictions (slippage, spread, commissions) are processed inside a dedicated `TradingReality` namespace, completely detached from core market sequence observation.

---

## 2. Gate Verification Checklist

Any new feature branch or architectural modification must pass the following Verification Gate before pull request approval:

1. **Static AST Analysis:** Must run the `ComplianceScanner` / `SecurityAuditor` and score 100% clean with zero false-positive active trade execution keywords.
2. **Global Compilation Check:** Must run `python -W error -m compileall src/ tests/` with zero SyntaxWarnings, escape sequence errors, or module imports breakage.
3. **Regression Check:** All pre-existing unit and integration tests must pass cleanly.
4. **Boundary Verification:** Test cases must verify that unauthorized interfaces cannot bypass the Judge or access write-locks of the Memory System.
