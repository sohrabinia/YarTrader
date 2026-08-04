# TradeYar AI — Production serving & Deployment

This runbook describes how to build, verify, and host the TradeYar AI React interface under production single-server setups.

## 1. Local Production Compilation
To build highly optimized, compiled static bundle files:
```bash
cd trader-terminal
npm install
npm run build
```
This generates compiled chunks under `trader-terminal/dist/`.

---

## 2. Standalone Hosting via FastAPI
To serve both JSON REST APIs and the React bundle natively from a single Python server:
```bash
PYTHONPATH=. python -m uvicorn src.Application.Services.web_dashboard:app --host 0.0.0.0 --port 8000
```
Then load `http://localhost:8000/` inside your browser. No Node.js or development dependencies are required at runtime.

---

## 3. Server Deployment (e.g. Windows IIS / Linux Nginx)
When deploying under production reverse proxies, configure the gateway to forward incoming requests directly to port `8000` locally.
- **IIS setup:** Use Application Request Routing (ARR) and URL Rewrite to route to local port `8000`.
- **Nginx setup:** Standard `proxy_pass http://127.0.0.1:8000;` blocks.
- **SSL Termination:** Handle SSL/TLS certificates strictly at the IIS or Nginx reverse proxy level to secure data streams.
