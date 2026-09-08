# YarTrader — Phase 14: Support AI Foundation

## 1. Overview
YarTrader Phase 14 establishes a production-grade, deterministic, anti-hallucination Support AI application foundation.
This capability powers the frontend chat assistant (`/api/chat/assistant`) to provide users with clear, grounded explanations of system decisions, strategy logic, and platform capabilities without exposing private account state or attempting autonomous trading mutations.

---

## 2. Architecture & Data Flow

```text
Frontend Chat Widget (trader-terminal/src/App.jsx)
          │
          ▼
POST /api/chat/assistant (src/Application/Services/web_dashboard.py)
          │
          ▼
SupportAIService (src/Application/Services/support_ai_service.py)
          │
          ▼
SupportAIEngine (src/Application/Support/support_ai_engine.py)
          │
          ▼
Deterministic Explanations & Grounded Foundation Context
```

---

## 3. Core Domain Engine (`support_ai_engine.py`)

- **`SupportQuery`**: Immutable value object representing incoming user queries. Enforces max length (1000 characters) and query sanitation.
- **`SupportResponse`**: Immutable value object containing the grounded response text, status code, and UTC timestamp.
- **`SupportAIEngine`**: Pure deterministic engine that maps user queries to grounded explanations using actual Phase 10–16 foundation outputs.

---

## 4. Safety & Anti-Hallucination Boundaries

1. **Private User State Isolation**:
   - Queries referencing balances, equity, positions, or orders require an authenticated user session (`user_context.get("authenticated") == True`).
   - If unauthenticated, the engine returns a strict limit message (`UNAUTHENTICATED_ACCESS_LIMIT`) without inventing numbers.

2. **No Execution Authority**:
   - Support AI cannot place, modify, or cancel trades.
   - Support AI cannot alter wallet balances, double-entry ledger entries, or payment subscriptions.

3. **Grounded Foundation Context**:
   - Explanations for governance decisions, historical intelligence, and learning insights are derived directly from Phase 10–16 summaries.

---

## 5. API Response Contract Compatibility

The `POST /api/chat/assistant` endpoint preserves 100% backward compatibility with existing clients:

```json
{
  "response": "پلتفرم YarTrader یک سیستم تحلیل خودکار و بدون وابستگی به شاخص‌های تاخیری است.",
  "status": "GENERAL_EXPLANATION_PROVIDED",
  "timestamp": "2026-09-08T12:00:00+00:00"
}
```

---

## 6. Verification & Test Evidence
- **Unit & Integration Tests**: `tests/YarTrader.Tests/Services/test_support_ai_phase14.py` (25 test cases).
- **Frontend Build**: Verified clean compilation in `trader-terminal`.
