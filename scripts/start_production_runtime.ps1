# YarTrader Production Runtime Launcher (PowerShell)
# Enforces storage root isolation and production environment setup

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

# 1. Enforce Production Storage Root Isolation
if (-not $env:TradeYarStorageRoot) {
    $env:TradeYarStorageRoot = "C:\YarTraderAI"
}
$env:YarTraderStorageRoot = $env:TradeYarStorageRoot

$StorageLogs = Join-Path $env:TradeYarStorageRoot "Logs"
if (-not (Test-Path $StorageLogs)) {
    New-Item -ItemType Directory -Path $StorageLogs -Force | Out-Null
}

# 2. Environment Variables Configuration
$env:YARTRADER_ENV = "production"
$env:TRADEYAR_ENV = "production"
$env:LIVE_TRADING_ENABLED = "False"
$env:YARTRADER_API_HOST = "0.0.0.0"
$env:YARTRADER_API_PORT = "8000"

Write-Host "============================================================" -ForegroundColor Cipher
Write-Host " YarTrader Production Runtime Launcher" -ForegroundColor Green
Write-Host " Storage Root : $env:TradeYarStorageRoot" -ForegroundColor Cyan
Write-Host " Logs Directory: $StorageLogs" -ForegroundColor Cyan
Write-Host " API Binding   : http://$env:YARTRADER_API_HOST:$env:YARTRADER_API_PORT" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cipher

# 3. Activate Virtual Environment
$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (Test-Path $VenvPython) {
    Write-Host "[INFO] Activating virtual environment at .venv..." -ForegroundColor Green
    & $VenvPython -m uvicorn src.Application.Services.web_dashboard:app --host $env:YARTRADER_API_HOST --port $env:YARTRADER_API_PORT --log-level info
} else {
    Write-Host "[WARNING] .venv not found at $VenvPython. Using system python..." -ForegroundColor Yellow
    python -m uvicorn src.Application.Services.web_dashboard:app --host $env:YARTRADER_API_HOST --port $env:YARTRADER_API_PORT --log-level info
}
