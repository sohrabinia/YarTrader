# TradeYar AI — Local Setup Guide

This document describes how to quickly set up and run the TradeYar AI local development environment.

## 1. Prerequisites
- **Python:** Python 3.12+ (or current active pyenv/virtualenv)
- **Node.js:** Node.js v18+ and `npm`

---

## 2. One-Command Dev Startup

To spin up both the FastAPI backend and the React hot-reload server side-by-side with zero manual port hunting:

Run the PowerShell startup script from the root folder:
```powershell
.\scripts\start-dev.ps1
```

This automates checking if the backend is running, safekeeping active research loops, killing dangling Vite processes, starting Node, and printing active URLs.

---

## 3. Manual Dev Process

If you prefer launching components in separate terminal instances:

1. **Terminal 1: Start FastAPI Backend**
   ```bash
   PYTHONPATH=. python -m uvicorn src.Application.Services.web_dashboard:app --host 127.0.0.1 --port 8000
   ```

2. **Terminal 2: Start Vite Client**
   ```bash
   cd trader-terminal
   npm install
   npm run dev
   ```

3. Open your browser to `http://localhost:5173`
