# domain-state-matrix.md

## Domain State Matrix

Maps the standard semantic system states to the corresponding frontend rendering rules.

| System State | Visual Treatment | Icon | Allowed Action / Scope |
|---|---|---|---|
| `ONLINE` | Glowing Neon Emerald Green | Pulse dot | Full monitoring & research query |
| `OFFLINE` | Muted Gray-Slate | Offline link | Retries with exponential reconnect |
| `WARNING` | Amber / Gold Neon | Warning sign | Degraded telemetry viewing |
| `RISK_HIGH` | Pulsating Ruby Red | Biohazard | Full passive risk alert panel display |
| `AI_THINKING` | Animated Cyan Spinner | Spinning brain | Loading skeletons across telemetry |
| `EXECUTION_BLOCKED` | Solid Deep Crimson | Stop hand | Displays detailed SRE blocking reason |

---

## Signal Lifecycle Mappings
1. **`RESEARCH`**: Passive advisory mode. UI allows full analysis & reason expansion. NO execution buttons are displayed.
2. **`APPROVED`**: System approved state. Exposes secure contract parameters but forbids client-side order dispatch.
3. **`BLOCKED`**: High-visibility block layout detailing the specific SRE rule trigger and engine source.
4. **`FAILED`**: Displays a fallback layout with correlation ID and diagnostic logs.
