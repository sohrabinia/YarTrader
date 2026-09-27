# YarTrader MT5 Interactive Session Bridge Architecture

## 1. Executive Summary & Problem Statement

In Windows Server operating systems, background Windows Services run under `NT AUTHORITY\SYSTEM` in **Session 0** (non-interactive service session).
Conversely, desktop graphical user interface applications—such as MetaTrader 5 (`terminal64.exe`)—run in interactive user sessions (e.g., **Session 2**, `Administrator` via RDP).

Windows OS kernel object namespace isolation (`\BaseNamedObjects` vs `\Sessions\2\BaseNamedObjects`) prevents background processes in Session 0 from opening shared memory handles, named pipes, or GUI IPC handles created by desktop applications in Session 2. As a result, direct calls to `mt5.initialize()` from a Session 0 service fail with Win32 IPC error `-10003` (`IPC initialize failed, MetaTrader 5 x64 not found`).

The **YarTrader MT5 Interactive Bridge** provides a dedicated, lightweight, read-only local loopback agent running in Session 2 alongside `terminal64.exe`. It bridges market data and terminal connection health across the Windows session boundary to the Session 0 `YarTrader` production service cleanly and securely.

---

## 2. Architecture Overview

```text
YarTrader Windows Service
        │
        │ Session 0 (LocalSystem)
        │ http://127.0.0.1:5001 (Bearer Auth)
        ▼
MT5BridgeClient
        │
        │ Local Loopback HTTP Transport
        ▼
MT5 Interactive Bridge Agent (FastAPI / Uvicorn)
        │
        │ Session 2 (Administrator Interactive Session)
        │ In-Process MetaTrader5 C-Extension IPC
        ▼
MetaTrader 5 terminal64.exe
```

### Key Architectural Invariants:
1. **Read-Only Capability:** In Phase 1, the Bridge exposes strictly read-only health and market-data endpoints (`/health`, `/mt5/status`, `/market-data`). Write/order execution capabilities are explicitly out-of-scope.
2. **Zero Strategy Authority:** The Bridge is pure runtime transport infrastructure. It contains zero Brain, Strategy, Risk, or Decision logic.
3. **Local Loopback Security Boundary:** Bound strictly to `127.0.0.1`. Non-loopback network requests are rejected fail-closed with HTTP 403 Forbidden.
4. **Bearer Token Authorization:** All operational endpoints require an ACL-restricted Bearer token (`secrets/mt5_bridge_token.secret`).

---

## 3. API Contract & Endpoints

### 3.1 `GET /health` (Public Probe)
- **Authentication:** Unauthenticated
- **Response:**
  ```json
  {
    "status": "HEALTHY",
    "service": "YarTrader.MT5Bridge",
    "version": "1.0.0",
    "mt5_installed": true,
    "timestamp": 1774000000.0
  }
  ```

### 3.2 `GET /mt5/status` (Terminal Health)
- **Authentication:** `Authorization: Bearer <token>`
- **Response:**
  ```json
  {
    "connected": true,
    "initialized": true,
    "server": "Alpari-MT5-Demo",
    "login": 52961173,
    "last_error": null,
    "ping_ms": 15.4
  }
  ```

### 3.3 `POST /market-data` (Candle Retrieval)
- **Authentication:** `Authorization: Bearer <token>`
- **Payload:**
  ```json
  {
    "symbol": "XAUUSD",
    "timeframe": "H1",
    "count": 100
  }
  ```
- **Response:**
  ```json
  {
    "symbol": "XAUUSD",
    "timeframe": "H1",
    "count": 100,
    "candles": [
      {
        "time": 1774000000,
        "open": 2300.50,
        "high": 2305.10,
        "low": 2298.00,
        "close": 2302.25,
        "tick_volume": 450,
        "spread": 12,
        "real_volume": 0
      }
    ]
  }
  ```

---

## 4. Process Lifecycle & Startup Sequence

1. **Session 2 Login:** Administrator logs into interactive Session 2 via RDP.
2. **MT5 Launch:** `terminal64.exe` is started in Session 2 and connects to `Alpari-MT5-Demo`.
3. **Bridge Agent Launch:** Executed via `scripts/start_mt5_bridge.ps1` or Windows Task Scheduler (on user logon).
4. **YarTrader Service Connection:** `YarTrader` service in Session 0 polls `http://127.0.0.1:5001/mt5/status`. When connected, `ResearchWorker` transitions status from `RECOVERING` to `RUNNING`.

---

## 5. Fail-Closed & Recovery Behavior

- **Bridge Unreachable / Stopped:** `MT5DataProvider` returns `connected=False` with `last_error="Bridge Connection Timeout"` or `last_error="Bridge Client Exception"`. `ResearchWorker` transitions to `RECOVERING`, skips `ResearchRuntime.run_once()`, and produces 0 trading decisions.
- **Unauthorized Token:** Returns HTTP 401. `MT5DataProvider` returns `connected=False` with `last_error="Bridge Authentication Failed"`.
- **Non-Loopback Access:** Rejected with HTTP 403 Forbidden.
- **MT5 Disconnected:** Bridge returns `connected=False` with MT5's actual error message. `ResearchWorker` remains in `RECOVERING` state.
- **Restored Connectivity:** As soon as MT5 or Bridge recovers, `MT5DataProvider.get_connection_health()` returns `connected=True`, and `ResearchWorker` automatically recovers status to `RUNNING`.

---

## 6. Known Limitations
- **Read-Only Scope:** Phase 1 implements read-only market data retrieval. Order placement and position modification remain strictly out-of-scope for the Bridge agent and must be dispatched through authorized SRE-governed execution adapters.
