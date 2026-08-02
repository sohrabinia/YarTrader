# REALTIME_PROTOCOL.md - Real-Time and Time Integrity Protocol

TradeYar operates on high-frequency, real-time market and intelligence streams. This protocol defines the synchronization, reconnection, latency monitoring, and time integrity rules.

---

## 1. WebSocket Connection Rules

The frontend must implement a robust WebSocket consumer that guarantees the following properties:
- **High-Frequency Stream Parsing:** Efficient JSON unpacking with minimum garbage collection overhead.
- **Incremental State Re-Sync:** Re-establish complete state upon connection recovery instead of leaving stale items in memory.
- **Deterministic Backoff Reconnect:** Implement exponential backoff reconnect logic starting at 100ms capping at 10s.

---

## 2. Latency Monitoring

Every real-time packet must carry a diagnostic latency envelope.

### Latency Thresholds:
- **Normal:** `<= 300ms`
- **Degraded/Warning:** `> 300ms`

### Behavior when Threshold is Exceeded:
- Activate the visually distinctive global/component level `Latency Indicator`.
- Change connection status indicators to `WARNING`.
- Highlight data age on relevant telemetry charts.

---

## 3. Reconnection & Drops

During network drops or signal loss, the UI must **never** render fallback or zeroed values:
- **Forbidden Actions:**
  - Setting Price = `0`
  - Setting Price = `empty` or `"-"` without warning
- **Correct Behavior:**
  - Freeze the last known valid price.
  - Display "Reconnecting..." status.
  - Apply a visually distinctive "stale data" filter/opacity (e.g., desaturate or reduce opacity to 60%).

---

## 4. Time Integrity Rules

Every market and signal component rendering real-time metrics must track and explicitly correlate the following timestamps:

- **Exchange Timestamp:** Epoch UTC when the price was generated at the liquidity source.
- **Server Timestamp:** Epoch UTC when the packet was processed and transmitted by the backend server.
- **Client Timestamp:** Epoch UTC when the packet was received by the frontend client.
- **Data Age:** `Client Timestamp - Exchange Timestamp`
- **Freshness Window:** The maximum age threshold (configured dynamically per asset, e.g., 2000ms). If exceeded, mark the UI block as **STALE**.
