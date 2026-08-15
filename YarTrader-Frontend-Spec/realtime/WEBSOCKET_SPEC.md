# WEBSOCKET_SPEC.md — WebSocket Connection Lifecycle Specification

This document defines the real-time client communication standard. The client must maintain a single, multiplexed WebSocket connection to receive live market quotes and system status heartbeats.

---

## 🔁 Connection Lifecycle States

The client-side WebSocket client must implement a clear, predictable state machine:

```
           ┌──────────────┐
           │  DISCONNECTED│◀────────────────────────┐
           └──────┬───────┘                         │
                  │ (Initiate Connect)              │
                  ▼                                 │
           ┌──────────────┐                         │
           │  CONNECTING  │                         │
           └──────┬───────┘                         │
                  │ (On Open Event)                 │
                  ▼                                 │
           ┌──────────────┐                         │ (Fatal Limit / Max Tries)
           │  CONNECTED   │                         │
           └──────┬───────┘                         │
                  │ (Connection Loss)               │
                  ▼                                 │
           ┌──────────────┐                         │
           │ RECONNECTING ├─────────────────────────┘
           └──────────────┘
```

### 1. `DISCONNECTED` (Initial state)
- **State Details:** The socket is closed. No active event listeners are bound to data streams.
- **Visuals:** Gray network status badge with "Offline" label.

### 2. `CONNECTING`
- **State Details:** Connection handshake initiated to `ws://localhost:8000/api/v1/ws` or production equivalent.
- **Visuals:** Amber status badge with a spinning loading indicator.

### 3. `CONNECTED`
- **State Details:** Handshake successful. Real-time ticker stream activated.
- **Visuals:** Pulsating green status badge.

### 4. `RECONNECTING`
- **State Details:** Connection lost unexpectedly. Reconnect algorithms initiated with exponential backoff.
- **Visuals:** Pulsating amber badge with a reconnect retry counter (e.g., "Reconnecting... (Attempt 2/5)").

---

## 💓 Heartbeat & Timeout Strategy

To prevent silent connection failures and detect broken sockets across routers, a client-to-server heartbeat must be executed:

1. **Ping Interval:** The client issues a small, low-overhead string `"ping"` or `{"type":"ping"}` to the server every **25 seconds**.
2. **Pong Acknowledgment:** The server must respond with `"pong"` or `{"type":"pong"}` within **5 seconds**.
3. **Timeout Trigger:** If the client does not receive the pong response within 5 seconds of a ping, it must immediately mark the socket as degraded, execute manual socket closure, and initiate the reconnection loop.
