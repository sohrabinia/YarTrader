# AUDIT_VISUALIZATION.md — Audit Log Visualization Component

This document details the layout and interface design specs for rendering security, analytical, and operational audit logs inside the SRE Admin Console.

---

## 🕒 SRE Audit Timeline Component

The `/admin` shell must expose an interactive, vertical timeline rendering structured logs parsed from the server's rotating `security.log` files and live telemetry stream.

```
● 14:15:02 UTC - USER LOGIN SUCCESS (Role: PRO)
  ↳ IP: 198.51.100.12 | Account: trader@tradeyar.ai
--------------------------------------------------------------
● 14:12:10 UTC - MT5 CONNECTIVITY SYNCED (Server: IC_Markets)
  ↳ Ping: 12ms | Account: 8094321
--------------------------------------------------------------
● 14:00:00 UTC - SHADOW POSITION COMPLETED (ID: sh-90342)
  ↳ Symbol: XAUUSD | Exit: TAKE_PROFIT | P&L: +$1,270.00
```

### Visual Specifications:
- **Timeline Dot Accent Colors:**
  - `Green Dot` (`--color-success`): For successful operations (logins, synchronized connections, completed virtual positions).
  - `Yellow Dot` (`--color-warning`): For warning events (user limit reached, high latency, worker recovery initiated).
  - `Red Dot` (`--color-critical`): For security violations (unauthorized SRE access attempts, failed logins, worker crashes).
- **Log Typography:** Always use monospace font `--font-family-mono` for payload text, IPs, and timestamps to ensure tabular structure.

---

## 🔍 Log Filtering Interface

To allow SRE Operators to quickly isolate security incidents or performance issues, the Audit panel must include a filter header:

1. **Search Input Bar:** Filter logs in real-time by email, symbol, or IP.
2. **Channel Toggle Pills:** Toggles logs display from:
  - `Security Channel` (failed auth attempts, password resets, role modifications)
  - `Analytical Channel` (signals generated, memory consolidation updates, judge brain outputs)
  - `Operational Channel` (MT5 heartbeat syncs, service start/stop commands)
3. **Export Button:** Quick action to download current filtered timeline log view as clean JSON files or plain TXT files.
