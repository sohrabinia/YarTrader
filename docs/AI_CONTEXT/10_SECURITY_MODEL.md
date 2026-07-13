# 10. Security Model

## 1. Forbidden Subsystems & Actions

The platform is designed with a strict non-trading boundary. The following actions and systems are completely prohibited:

❌ **Automated Orders Execution**: No buy/sell command blocks, transaction queues, or connection sockets to active financial broker platforms.
❌ **Live Positions Management**: No leverage modifiers, account balance mutators, or active position size adjustments.
❌ **Trading Signals Generation**: No automated buy/sell direction triggers.

---

## 2. Dynamic Leakage Prevention Guards

To guarantee absolute compliance with the APES-FIN guidelines, a multi-layered boundary protection is active:

1.  **AST Code Verification (Build-time)**: Static checks parse files inside `src/` to ensure no imports of forbidden trading namespaces exist.
2.  **String Scanning (Runtime)**: Key scanners verify that payloads inside messages (`IntelligenceMessage`), shared contexts (`AgentContext`), evidence entries, and secrets values do not contain raw execution terms (`"place_order"`, `"open_position"`, `"execute_trade"`, etc.), raising `ValidationException` instantly.
3.  **Encrypted Vault Boundaries**: Key-value credentials are encrypted passively in the simulated Secrets Vault.

---

## 3. Cross References
*   [01_PROJECT_UNDERSTANDING.md](01_PROJECT_UNDERSTANDING.md)
*   [02_SYSTEM_ARCHITECTURE.md](02_SYSTEM_ARCHITECTURE.md)
*   [11_API_AND_SERVICES.md](11_API_AND_SERVICES.md)
