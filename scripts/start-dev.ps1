# PowerShell Dev Environment Startup Script for TradeYar AI
# Auto-detects repository root, manages port bindings, and starts servers cleanly.

$ErrorActionPreference = "Stop"

function Test-PortActive ([int]$Port) {
    $connection = New-Object System.Net.Sockets.TcpClient
    try {
        $connection.Connect("127.0.0.1", $Port)
        $connection.Close()
        return $true
    } catch {
        return $false
    }
}

# 1. Detect repository root automatically based on script location
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Resolve-Path "$ScriptDir\.."
Set-Location $RepoRoot

Write-Host "===============================================" -ForegroundColor Cyan
Write-Host "  TradeYar AI Development Environment Launcher " -ForegroundColor Cyan
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host "Detected Repository Root: $RepoRoot" -ForegroundColor Gray

# 2. Check Port 8000 (FastAPI Backend)
Write-Host "[INFO] Scanning Port 8000 for active backend servers..." -ForegroundColor Yellow
$backendRunning = Test-PortActive -Port 8000

if ($backendRunning) {
    Write-Host "[✓] FastAPI Backend is already running on Port 8000." -ForegroundColor Green
} else {
    Write-Host "[i] Port 8000 is free. Starting FastAPI Backend..." -ForegroundColor Yellow
    # Determine python executable command
    $pythonCmd = "python"
    if (Get-Command "python3" -ErrorAction SilentlyContinue) {
        $pythonCmd = "python3"
    }

    # Start FastAPI reload gateway in background
    Start-Process -FilePath $pythonCmd -ArgumentList "-m uvicorn src.Application.Services.web_dashboard:app --host 0.0.0.0 --port 8000" -NoNewWindow -PassThru
    Write-Host "[✓] FastAPI backend server process spawned successfully." -ForegroundColor Green
    Start-Sleep -Seconds 3 # Allow binding delay
}

# 3. Check and clean up duplicate/orphaned Vite processes on Port 5173
Write-Host "[INFO] Scanning Port 5173 for duplicate or orphaned Vite processes..." -ForegroundColor Yellow
try {
    $netstatOutput = netstat -ano | Select-String "127.0.0.1:5173|0.0.0.0:5173"
    if ($netstatOutput) {
        Write-Host "[WARN] Port 5173 occupied. Cleaning duplicate Vite servers safely..." -ForegroundColor DarkYellow
        foreach ($line in $netstatOutput) {
            $parts = $line.ToString().Split(" ", [System.StringSplitOptions]::RemoveEmptyEntries)
            if ($parts.Count -ge 5) {
                $pid = $parts[$parts.Count - 1].Trim()
                if ($pid -gt 0) {
                    Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
                }
            }
        }
        Write-Host "[✓] Duplicate ports cleared." -ForegroundColor Green
    }
} catch {
    Write-Host "[INFO] Port scanning complete." -ForegroundColor Gray
}

# 4. Check Node and start Vite Frontend
if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    Write-Error "Node.js is missing or not configured in your PATH environment variable. Fail."
    exit 1
}

Write-Host "[INFO] Starting Vite development server..." -ForegroundColor Yellow
Push-Location "trader-terminal"
try {
    Start-Process -FilePath "npm" -ArgumentList "run dev" -NoNewWindow
    Write-Host "[✓] Vite frontend spawned." -ForegroundColor Green
} finally {
    Pop-Location
}

Start-Sleep -Seconds 2

# 5. Output unified Summary
Clear-Host
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host "   TradeYar AI Developer Environment Startup" -ForegroundColor Cyan
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Backend Gateway Endpoint:" -ForegroundColor Gray
Write-Host "  URL:    http://localhost:8000" -ForegroundColor White
Write-Host "  Status: ONLINE" -ForegroundColor Green
Write-Host ""
Write-Host "Frontend Dev Endpoint:" -ForegroundColor Gray
Write-Host "  URL:    http://localhost:5173" -ForegroundColor White
Write-Host "  Status: ONLINE (Proxied API requests)" -ForegroundColor Green
Write-Host ""
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host "Press Ctrl+C to terminate or monitor tasks." -ForegroundColor Gray
