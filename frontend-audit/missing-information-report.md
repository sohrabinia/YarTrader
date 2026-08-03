# missing-information-report.md

## Missing Information Report (Rule 3)

Documents any unknown assumptions, risks, and required design decisions for the TradeYar AI user experience.

### 1. Missing Items
- **Broker Auth Client Flows**: The exact OAuth client flow specifications for reading third-party demo broker accounts are partially unspecified.
- **WebSocket Heartbeat Payload**: The exact timeout payload schema for client liveness is not natively standardized.

### 2. Risk Assessment
- **Risk**: Client-side stale data if the WebSocket drops silently without a ping/pong heartbeat validation.
- **Impact Rating**: Medium. Could lead the user to view stale virtual position states.

### 3. Safe Assumption
- **Assumption**: We assume a client-side watchdog timer that automatically sets the UI state to `OFFLINE` and forces reconnect if no tick stream message is received within 15 seconds.

### 4. Required Future Decisions
- Decide on the standard WebSocket `PING` payload structure (e.g. `{"type": "ping"}`) and integrate it cleanly with SRE diagnostics.
