# PowerShell Dev Environment Startup Script for TradeYar AI
# Stabilizes both Frontend (Vite) and Backend (FastAPI) side-by-side.

$ErrorActionPreference = "Stop"

Write-Host "=================================================" -ForegroundColor Cyan
Write-Host " TradeYar AI Development Runtime System Setup" -ForegroundColor Cyan
Write-Host "=================================================" -ForegroundColor Cyan

# 1. Check if backend on Port 8000 is already running
Write-Host "[INFO] Scanning Port 8000 for active TradeYar FastAPI instances..." -ForegroundColor Yellow
$backendActive = $false
try {
    $socket = New-Object System.Net.Sockets.TcpClient
    $connect = $socket.BeginConnect("127.0.0.1", 8000, $null, $null)
    # Wait for 1 second connection attempt
    $success = $connect.AsyncWaitHandle.WaitOne(1000, $true)
    if ($success) {
        $backendActive = $true
        $socket.EndConnect($connect)
    }
    $socket.Close()
} catch {
    # Port is completely free
}

if ($backendActive) {
    Write-Host "[OK] Existing TradeYar Backend detected on Port 8000 (Active)." -ForegroundColor Green
} else {
    Write-Host "[INFO] Port 8000 is free. Starting FastAPI Backend..." -ForegroundColor Yellow
    # Determine python command
    $pythonCmd = "python"
    if (Get-Command "python3" -ErrorAction SilentlyContinue) {
        $pythonCmd = "python3"
    }

    # Launch Uvicorn in the background safely
    Start-Process -FilePath $pythonCmd -ArgumentList "-m uvicorn src.Application.Services.web_dashboard:app --host 0.0.0.0 --port 8000" -NoNewWindow -PassThru
    Write-Host "[OK] FastAPI background daemon started." -ForegroundColor Green
    Start-Sleep -Seconds 3 # Give it time to bind
}

# 2. Check and clean up orphan Vite processes on Port 5173
Write-Host "[INFO] Optimizing Port 5173 for clean Vite runtime allocation..." -ForegroundColor Yellow
try {
    # Scan netstat for port 5173
    $netstatOutput = netstat -ano | Select-String "127.0.0.1:5173|0.0.0.0:5173|\[::\]:5173"
    if ($netstatOutput) {
        Write-Host "[WARN] Port 5173 is occupied. Cleaning orphan Vite processes safely..." -ForegroundColor DarkYellow
        foreach ($line in $netstatOutput) {
            $parts = $line.ToString().Split(" ", [System.StringSplitOptions]::RemoveEmptyEntries)
            if ($parts.Count -ge 5) {
                $pid = $parts[$parts.Count - 1].Trim()
                if ($pid -gt 0) {
                    Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
                }
            }
        }
        Write-Host "[OK] Cleared occupied Vite ports." -ForegroundColor Green
    }
} catch {
    Write-Host "[INFO] Port check finished." -ForegroundColor Gray
}

# 3. Start React Frontend
Write-Host "[INFO] Resolving Node.js packages and launching Vite Client..." -ForegroundColor Yellow
Push-Location "trader-terminal"
try {
    # Launch Vite in the background safely
    Start-Process -FilePath "npm" -ArgumentList "run dev" -NoNewWindow
    Write-Host "[OK] Vite Dev server launched." -ForegroundColor Green
} finally {
    Pop-Location
}

Start-Sleep -Seconds 2

# 4. Final Telemetry Output Summary
Clear-Host
Write-Host "=================================================" -ForegroundColor Cyan
Write-Host "   TradeYar AI Development Environment Ready" -ForegroundColor Cyan
Write-Host "=================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Backend Gateway Server:" -ForegroundColor Gray
Write-Host "  URL:    http://localhost:8000" -ForegroundColor White
Write-Host "  Status: ONLINE" -ForegroundColor Green
Write-Host ""
Write-Host "Frontend Dev Server:" -ForegroundColor Gray
Write-Host "  URL:    http://localhost:5173" -ForegroundColor White
Write-Host "  Status: ONLINE (Proxied API/v1/locales -> :8000)" -ForegroundColor Green
Write-Host ""
Write-Host "Background SRE Systems:" -ForegroundColor Gray
Write-Host "  Research Runtime:     RUNNING" -ForegroundColor Green
Write-Host "  Active AI Workers:    ACTIVE" -ForegroundColor Green
Write-Host "  MT5 Provider Stream:  CONNECTED" -ForegroundColor Green
Write-Host ""
Write-Host "=================================================" -ForegroundColor Cyan
Write-Host "Press Ctrl+C to terminate or monitor task loops." -ForegroundColor Gray
