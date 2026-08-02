# DOMAIN_UI_RULES.md - Domain Constraints and Specification

This file is the single source of truth for business meaning and domain validations in the TradeYar AI frontend.

The UI must never infer business meaning from visual design.

---

## 1. System Status Rules

### Allowed States:
- `ONLINE`
- `OFFLINE`
- `WARNING`
- `RISK_HIGH`
- `AI_THINKING`
- `EXECUTION_BLOCKED`

### Rules:
* Only use the shared `SystemStatus` component.
* Pages and views cannot create custom status colors.
* Pages and views cannot create custom status labels.

### Examples:
- **Correct:**
  ```tsx
  <SystemStatus status="ONLINE" />
  ```
- **Incorrect:**
  ```tsx
  <div style={{color:"green"}}>
  Connected
  </div>
  ```

---

## 2. Signal State Rules

The UI must represent signals precisely according to their semantic lifecycle states:

### State: `RESEARCH`
- **Meaning:** AI research output only.
- **UI Constraints:**
  - Show analysis
  - Show explanation
  - NO execution action is permitted
- **Forbidden UI Elements:**
  - Execute Button
  - Trade Button
  - Order Action

### State: `APPROVED`
- **Meaning:** Signal approved by the required engines (Research, Strategy, Risk).
- **UI Constraints:**
  - Show approval state
  - Execution action is available ONLY through a valid, authenticated, and signed API contract.

### State: `BLOCKED`
- **Meaning:** Risk engine blocked the execution or signal.
- **UI Constraints (Required):**
  - High-visibility warning state
  - Detailed risk reason
  - Specific blocking source engine/rule info

### State: `FAILED`
- **Meaning:** Processing failure or exception in the engine pipeline.
- **UI Constraints (Required):**
  - Error state
  - Diagnostic information / correlation ID
  - Recovery option if available
