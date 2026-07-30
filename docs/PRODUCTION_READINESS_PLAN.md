# TradeYar AI — Production Readiness Plan (RC-1)
**Date:** July 30, 2026
**Auditor:** Principal Software Architect, Principal Security Auditor & DevOps Lead
**Audit Phase:** Production Readiness Planning (Pure Verification — NO CODE CHANGES)

---

## 1. Introduction
The purpose of this document is to outline the **Production Readiness and Deployment Architecture** for the stable **TradeYar AI Release Candidate (RC-1)**. As the codebase moves from "intelligence building" to "stability validation", this plan defines a standardized deployment, configuration, runtime environment, and startup/shutdown lifecycle to enforce 100% operational reliability.

---

## 2. Deployment Architecture
TradeYar AI operates as a passive, non-trading, descriptive-analytical system. It does not execute live broker trades, which simplifies the physical infrastructure layout by prioritizing high-fidelity historical simulations, live read-only research feeds, and asynchronous multi-agent collaboration over high-frequency transaction capabilities.

```text
               ┌────────────────────────────────────────────────────────┐
               │              TradeYar AI Docker Container              │
               │                                                        │
               │   ┌───────────────┐                  ┌─────────────┐   │
  XAUUSD H1 ──>│──>│ Live Research │──(snapshots)────>│    FastAPI  │   │
  Rates Feed   │   │ Polling Daemon│                  │  Web Server │   │
 (Read-Only)   │   └───────────────┘                  └──────┬──────┘   │
               │                                             │          │
               │                                       (HTTP REST / SPA)│
               └─────────────────────────────────────────────┼──────────┘
                                                             ▼
                                                    Administrative Desk
                                                    (Persian RTL/EN LTR)
```

### Architecture Specifications
1. **Container Isolation (Docker):** The core application is packaged within a single lightweight Debian/Ubuntu-based Docker container. This contains the FastAPI web management dashboard server, live market research worker threads, and multi-agent layers.
2. **Persistent Storage Mapping:** High-value memory layers (Raw, Experience, Pattern, Concept) and live H1 research snapshots are written to local folders and mirrored to a persistent Docker volume mounted at `/app/runtime_logs/`.
3. **MetaTrader 5 Read-Only Linkage:**
   - Under Windows hosting, the container links directly to the local terminal API via a secure read-only socket loop.
   - Under Unix/Docker environments, the system automatically runs in "Synthetic Fallback Mode", generating high-fidelity local rate streams without network dependencies.

---

## 3. Required Environment Variables
To ensure absolute isolation of environments, all system behavior is configured through environment variables. The configuration manager parses and validates these values on boot:

| Variable Name | Required Value | Purpose | Safety Check |
| :--- | :--- | :--- | :--- |
| `TRADEYAR_ENV` | `Production` \| `Sandbox` | Operational sandbox classification | Restricts active changes |
| `TRADEYAR_READ_ONLY` | `true` | Enforces strict APES-FIN read-only mode | Blocks any active order execution |
| `MT5_TERMINAL_PATH` | String (e.g. `C:/Program Files/...`) | Path to MetaTrader 5 terminal executable | Read-only connection only |
| `MT5_LOGIN` | Integer | MetaTrader 5 investor password login | Must use investor (read-only) account |
| `MT5_PASSWORD` | String | MetaTrader 5 investor password | Strictly confidential |
| `MT5_SERVER` | String | MetaTrader 5 broker server hostname | Connects to historical feeds |
| `HOST_PORT` | `8000` | FastAPI dashboard hosting port | Configurable web port |
| `LOG_LEVEL` | `INFO` | System logging level | Excludes debug noise under prod |

---

## 4. Runtime Requirements

* **Operating System:** Linux Ubuntu 22.04 LTS (Docker Host) or Windows Server 2022 (Native MT5 host).
* **CPU:** Minimum 2 Cores (vCPUs) with 2.0 GHz+ clock speed. The multi-agent collaboration sequentially routes messages, which has a very small multi-threading footprint.
* **Memory (RAM):** Minimum 2.0 GB. The memory system holds patterns and concepts in memory and writes them to atomic JSON caches, requiring less than 150MB active RAM under continuous running.
* **Disk Storage:** Minimum 10.0 GB of SSD storage (to accommodate Python Docker layers, system log files, and persistent cognitive experience layers).
* **Network Bounds:** Restricts egress connection to MT5 broker servers only. Egress connection to third-party public APIs is blocked by security policy unless explicit data connectors are defined.

---

## 5. Standard Operating Procedures (SOP)

### Startup Procedure

```text
Step 1: Check Environment Variables ──> Step 2: Validate Directory Structure ──> Step 3: Run Self-Check ──> Step 4: Server Up
```

1. **Verify Environment Configuration:** Ensure all variables (especially `TRADEYAR_READ_ONLY=true`) are present and loaded in the host environment.
2. **Execute Self-Check Script:** Execute the validation command to verify directory structure correctness and platform health:
   ```bash
   python validate_release.py
   ```
3. **Launch the Container / Server Process:** Initiate the FastAPI server using Uvicorn:
   ```bash
   uvicorn src.Application.Services.web_dashboard:app --host 0.0.0.0 --port 8000 --workers 1
   ```
4. **Monitor Port Binding & Handshake:** Verify that port `8000` is active and the live polling daemon successfully starts connection handshakes with MT5.

### Shutdown Procedure
1. **SIGTERM Signal Propagation:** Send a standard `SIGTERM` (or `Ctrl+C`) to the FastAPI process.
2. **Asynchronous Thread Join:** The server catches the termination signal and halts the live research background loop, waiting up to 5.0 seconds for the current polling cycle to conclude.
3. **Atomic Memory Sync:** The `MarketMemorySystem` executes a final atomic write, serialization, and swap of all modified patterns, experiences, and approved concepts to `runtime_logs/brain_memory/*.json` files.
4. **Clean Socket Close:** Close all active read-only TCP MT5 socket handles, releasing port allocations.
5. **Process Exit:** Terminate uvicorn process cleanly with exit code `0`.
