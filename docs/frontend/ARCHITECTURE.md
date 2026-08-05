# TradeYar AI — Frontend Integration Architecture

This document describes the dynamic API Gateway and serving routing architecture of TradeYar AI.

## 1. Unified Gateway Routing

The React standalone Single Page Application (`/trader-terminal`) is decoupled from the FastAPI backend, utilizing same-origin relative URLs or local proxies to communicate.

```
                    +------------------------------------+
                    |       ACTIVE DEVELOPMENT           |
                    +------------------------------------+

        React Client [5173] =====[Proxy /api]=====> FastAPI Backend [8000]
                                                     (Active Research Loop)
                                                     (Active Shadow Workers)

                    +------------------------------------+
                    |       PRODUCTION LOCAL             |
                    +------------------------------------+

        React Client [8000] ======================> FastAPI Backend [8000]
        (Served from dist/)                          (Active Research Loop)
                                                     (Active Shadow Workers)
```

- **Vite Proxy:** Hardened in `trader-terminal/vite.config.js` to route relative `/api`, `/v1`, and `/locales` endpoints to FastAPI.
- **Dynamic Config Fallback:** Configured in `trader-terminal/src/core/config.js` to dynamically drop external host prefixes in production, ensuring relative URLs resolve natively to the same origin.

---

## 2. FastAPI Static Assets Serve Pipeline

The backend server in `src/Application/Services/web_dashboard.py` mounts compiled static React bundles and serves `/` and `/dashboard` (and other SPA routing paths) using `FileResponse`.

```python
os.makedirs("trader-terminal/dist/assets", exist_ok=True)
app.mount("/assets", StaticFiles(directory="trader-terminal/dist/assets"), name="assets")
```

If the compiled `trader-terminal/dist/index.html` is not present, FastAPI automatically falls back to serving the robust inline legacy HTML, preserving backward compatibility and zero downtime.
