# TradeYar AI — Frontend & Gateway Troubleshooting

This SRE runbook provides solutions to common frontend, port, and backend connection issues.

## 1. Port 8000 or 5173 Already Occupied
If you see "address already in use" errors, clear duplicate, dangling loopback connections:

### Linux/macOS
```bash
kill $(lsof -t -i :8000) 2>/dev/null || true
kill $(lsof -t -i :5173) 2>/dev/null || true
```

### Windows (PowerShell SRE Shortcuts)
```powershell
Stop-Process -Id (Get-NetTCPConnection -LocalPort 8000).OwningProcess -Force -ErrorAction SilentlyContinue
Stop-Process -Id (Get-NetTCPConnection -LocalPort 5173).OwningProcess -Force -ErrorAction SilentlyContinue
```

---

## 2. API Endpoint returning 404 on localhost:5173
- Verify that the FastAPI backend server is active and listening on Port `8000`.
- Verify that `vite.config.js` contains correct proxy endpoints forwarding to `http://localhost:8000`.
- Ensure no CORS errors are displayed inside the browser's developer console.

---

## 3. Translation Keys (`welcome_title`) Displayed Instead of Text
- Ensure `/locales/en.json` and `/locales/fa.json` load cleanly.
- Check the browser network tab to confirm that `/locales/*.json` requests return `200 OK` from Port `8000`.
- Ensure `CONFIG.apiBaseUrl` resolves to same-origin relative URLs (`""`) in production, avoiding cross-origin mismatches (such as `127.0.0.1` vs `localhost`).
