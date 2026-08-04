# start-dev.ps1 - TradeYar AI Local Development Bootstrapper
# This script configures and launches the backend FastAPI server and React Vite dev server.

$ErrorActionPreference = "Stop"

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "          TradeYar AI — Local Development Bootstrapper" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan

# 1. Detect Repository Root automatically
$ScriptPath = $MyInvocation.MyCommand.Path
if ($ScriptPath) {
    $RepoRoot = Split-Path (Split-Path $ScriptPath -Parent) -Parent
} else {
    $RepoRoot = Get-Location
}
Set-Location $RepoRoot
Write-Host "[INFO] Repository Root: $RepoRoot" -ForegroundColor Green

# 2. Port conflict checks
$Ports = @(8000, 5173)
foreach ($Port in $Ports) {
    $PortCheck = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue
    if ($PortCheck) {
        Write-Host "[WARNING] Port $Port is currently in use! Attempting to kill conflicting processes..." -ForegroundColor Yellow
        $Processes = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique
        foreach ($Pid in $Processes) {
            if ($Pid -gt 0) {
                Write-Host "[INFO] Killing process ID: $Pid" -ForegroundColor Yellow
                Stop-Process -Id $Pid -Force -ErrorAction SilentlyContinue
            }
        }
        Start-Sleep -Seconds 1
    }
}

# Double check conflicts resolved
$PortsActive = $true
$Attempt = 0
while ($PortsActive -and $Attempt -lt 3) {
    $PortsActive = $false
    foreach ($Port in $Ports) {
        if (Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue) {
            $PortsActive = $true
        }
    }
    if ($PortsActive) {
        Start-Sleep -Seconds 1
        $Attempt++
    }
}

# 3. Start Backend FastAPI Server on Port 8000
Write-Host "[INFO] Starting Backend FastAPI Server..." -ForegroundColor Green
$Env:PYTHONPATH = $RepoRoot
$BackendJob = Start-Process -FilePath "python" -ArgumentList "-m uvicorn src.Application.Services.web_dashboard:app --host 0.0.0.0 --port 8000" -NoNewWindow -PassThru -ErrorAction SilentlyContinue

# 4. Start React Frontend Vite Server on Port 5173
Write-Host "[INFO] Starting React Frontend Vite Server..." -ForegroundColor Green
Set-Location "$RepoRoot/trader-terminal"
$FrontendJob = Start-Process -FilePath "npm" -ArgumentList "run dev" -NoNewWindow -PassThru -ErrorAction SilentlyContinue

Set-Location $RepoRoot

# 5. Print Status Endpoints
Start-Sleep -Seconds 2
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "🚀 Local Development Environment successfully initialized!" -ForegroundColor Green
Write-Host "----------------------------------------------------------------------" -ForegroundColor Cyan
Write-Host " - Backend API:  http://localhost:8000" -ForegroundColor White
Write-Host " - Frontend SPA: http://localhost:5173" -ForegroundColor White
Write-Host " - Health Check: http://localhost:8000/health" -ForegroundColor White
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "Press CTRL+C to terminate the active local sessions." -ForegroundColor Yellow
