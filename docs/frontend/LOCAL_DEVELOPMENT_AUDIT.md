# TradeYar AI — Local Development & Gateway Audit

This document summarizes the current local development, port configuration, and API gateway routing parameters analyzed for TradeYar AI.

## 1. Gateway Port Alignments

- **FastAPI Backend Gateway:** `http://localhost:8000` (provides REST endpoints `/health`, `/api/*`, `/v1/*`, `/locales/*`)
- **Vite Development Client:** `http://localhost:5173` (serves rapid hot-reload frontend development server)

## 2. Identified Integration Challenges

Historically, local viewing of the newly migrated standalone React client required spawning separate console processes which introduced developer overhead, orphaned Node instances, and port conflicts on `5173`/`5174`.
Additionally, hardcoded absolute references to `localhost:8000` inside client files caused CORS blocks when loading pages on different loopback addresses (such as `127.0.0.1`).

## 3. Stabilized Architectural Fixes

1. **Vite Proxy Gateway Integration:** `trader-terminal/vite.config.js` is hardened with local proxies so that requests targeting `/api/*`, `/v1/*`, and `/locales/*` are transparently proxied by Vite to port `8000` during development, avoiding CORS mismatches.
2. **Environment Controlled Base URL:** `trader-terminal/src/core/config.js` dynamically switches `CONFIG.apiBaseUrl` to relative paths (`""`) in production mode (`import.meta.env.PROD`). This guarantees zero CORS errors or hardcoded localhost hosts when serving static assets from FastAPI.
3. **Unified PowerShell Daemon:** `scripts/start-dev.ps1` automates port checks, frees duplicate processes cleanly, and triggers development mode on localhost:5173.
