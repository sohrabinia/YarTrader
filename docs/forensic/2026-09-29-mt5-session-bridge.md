# MT5 Session-0 / Session-2 Production Bridge

## Problem proven on 2026-09-29

The production YarTrader service runs under NSSM as LocalSystem in Windows Session 0. The interactive MetaTrader 5 terminal runs under the Administrator desktop session.

A direct LocalSystem reproduction using the same .venv and MetaTrader5 package returned:

- initialize: False
- last_error: (-10003, 'IPC initialize failed, MetaTrader 5 x64 not found')
- terminal_info: None
- account_info: None

The same host, package and terminal succeed from the Administrator session. This is a Windows session-scoped MT5 IPC boundary, not a ResearchWorker/Brain failure.

## Production design

The service remains:

NSSM -> Python service.py -> ResearchWorker/FastAPI in Session 0 / LocalSystem.

A separate MT5SessionAgent runs in the interactive user session beside terminal64.exe. It exposes a loopback-only JSON RPC endpoint protected by a machine-scoped random token.

Session 0 service -> 127.0.0.1:8765 -> Session 2 MT5SessionAgent -> MetaTrader5 IPC -> terminal64.exe

The bridge is fail-closed:

- no token => unavailable
- wrong token => 401
- unavailable terminal => unavailable
- account must be 52961173
- server must be Alpari-MT5-Demo
- trade mode must be DEMO (0)
- bridge order operations require YARTRADER_MT5_BRIDGE_ALLOW_DEMO_EXECUTION=true
- existing MetaTraderSafetyGate, demo execution gates, risk gates and autonomous-demo kill switch remain authoritative
- no LIVE trading is enabled by this bridge

## Deployment

Use scripts/windows/install_mt5_session_agent.ps1.

It creates the token if absent, stores it as a machine environment variable, and creates an interactive-logon scheduled task for the current user.

The agent must run in the same Windows session as the MT5 terminal.

After installation verify:

- http://127.0.0.1:8765/health
- /health on YarTrader
- /api/research/health
- /ready

The production service is intentionally allowed to remain degraded until the agent is reachable. It must never report MT5 healthy from synthetic data when the real terminal is unavailable.
