# YarTrader Real MT5 DEMO Execution PowerShell Wrapper
# Run this directly on the Windows Host machine where MetaTrader 5 terminal is installed.

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "YARTRADER — WINDOWS MT5 DEMO EXECUTION RUNNER" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan

# 1. Environment Checks
$os = [System.Environment]::OSVersion.VersionString
Write-Host "[CHECK] Operating System: $os"

if (-not ($os -like "*Windows*")) {
    Write-Host "[ERROR] This runner must be executed natively on Windows!" -ForegroundColor Red
    Write-Host "FINAL DEMO E2E VERDICT: DEMO E2E BLOCKED — WINDOWS HOST EXECUTION REQUIRED" -ForegroundColor Yellow
    Exit 1
}

# 2. Check Python
try {
    $pythonVer = python --version 2>&1
    Write-Host "[CHECK] Python Version: $pythonVer"
} catch {
    Write-Host "[ERROR] Python is not found in PATH!" -ForegroundColor Red
    Exit 1
}

# 3. Check MT5 Terminal Process
$mt5Process = Get-Process -Name "terminal64" -ErrorAction SilentlyContinue
if ($mt5Process) {
    Write-Host "[CHECK] MetaTrader 5 process (terminal64.exe) is RUNNING (PID: $($mt5Process.Id))" -ForegroundColor Green
} else {
    Write-Host "[WARNING] MetaTrader 5 process (terminal64.exe) is NOT detected!" -ForegroundColor Yellow
    Write-Host "[INFO] Attempting to locate terminal64.exe default install path..."
    $defaultPath = "C:\Program Files\MetaTrader 5\terminal64.exe"
    if (Test-Path $defaultPath) {
        Write-Host "[INFO] Starting MT5 terminal from $defaultPath..."
        Start-Process -FilePath $defaultPath
        Start-Sleep -Seconds 5
    } else {
        Write-Host "[ERROR] terminal64.exe not found at $defaultPath. Please start MT5 terminal manually." -ForegroundColor Red
    }
}

# 4. Trigger Real MT5 Demo E2E Python Script
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "EXECUTING REAL MT5 DEMO E2E PYTHON RUNNER..." -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan

$scriptPath = Join-Path $PSScriptRoot "run_real_mt5_demo_e2e.py"
if (-not (Test-Path $scriptPath)) {
    Write-Host "[ERROR] Script not found at $scriptPath" -ForegroundColor Red
    Exit 1
}

python $scriptPath $args
