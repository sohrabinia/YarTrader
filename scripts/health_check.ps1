param (
    [string]$BackendUrl = "http://127.0.0.1:8000",
    [string]$ExternalUrl = ""
)

# Health Check Script for YarTrader Production Service
# Location: C:\Projects\YarTrader_AI\scripts\health_check.ps1
#
# Idempotency Rule: This script can be run multiple times safely.
# It performs end-to-end HTTP health checks against local runtime endpoints
# and optionally against external proxy endpoints (e.g., IIS reverse proxy domain).

# Force TLS 1.2/1.3 and ignore self-signed certificates during development/staging verification
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12 -bor [Net.SecurityProtocolType]::Tls13
[System.Net.ServicePointManager]::ServerCertificateValidationCallback = { $true }

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "YarTrader Production SRE Health Check Diagnostics" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. LOCAL RUNTIME ENDPOINT DIAGNOSTICS
$LocalHealthUrl = "$BackendUrl/health"
Write-Host "[+] Step 1: Checking Local FastAPI Service: $LocalHealthUrl" -ForegroundColor Cyan

try {
    $startTime = Get-Date
    $response = Invoke-RestMethod -Uri $LocalHealthUrl -Method Get -TimeoutSec 5
    $endTime = Get-Date
    $latency = [Math]::Round(($endTime - $startTime).TotalMilliseconds, 2)

    Write-Host "  [OK] Local Service is ONLINE." -ForegroundColor Green
    Write-Host "  [OK] Latency: $latency ms" -ForegroundColor Green

    Write-Host "`n  --- Local Subsystems Telemetry ---" -ForegroundColor Yellow
    Write-Host "  Service Name     : $($response.service)"
    Write-Host "  Service Status   : $($response.status)"
    Write-Host "  API Gateway      : $($response.api)"
    Write-Host "  MT5 Link State   : $($response.mt5)"
    Write-Host "  Intelligence State: $($response.intelligence)"
    Write-Host "  Worker Daemon    : $($response.worker)"
    Write-Host "  Last Heartbeat   : $($response.timestamp)"
} catch {
    Write-Host "  [FAIL] Local Service is UNHEALTHY or OFFLINE!" -ForegroundColor Red
    Write-Host "  Error details: $($_.Exception.Message)" -ForegroundColor Yellow
}

# 2. EXTERNAL PROXY ENDPOINT DIAGNOSTICS
if ($ExternalUrl) {
    Write-Host "`n[+] Step 2: Checking External IIS Reverse Proxy: $ExternalUrl" -ForegroundColor Cyan
    $ExternalHealthUrl = "$ExternalUrl/health"
    try {
        $startTime = Get-Date
        $response = Invoke-RestMethod -Uri $ExternalHealthUrl -Method Get -TimeoutSec 5
        $endTime = Get-Date
        $latency = [Math]::Round(($endTime - $startTime).TotalMilliseconds, 2)

        Write-Host "  [OK] External IIS Reverse Proxy is ONLINE & Proxying Successfully." -ForegroundColor Green
        Write-Host "  [OK] Proxy Latency: $latency ms" -ForegroundColor Green
        Write-Host "  [OK] Status Code  : 200 (OK)" -ForegroundColor Green
        Write-Host "  [OK] Response Status: $($response.status)" -ForegroundColor Green
    } catch {
        Write-Host "  [FAIL] External Reverse Proxy Check Failed!" -ForegroundColor Red
        Write-Host "  Url checked: $ExternalHealthUrl" -ForegroundColor Yellow
        Write-Host "  Error details: $($_.Exception.Message)" -ForegroundColor Yellow
        Write-Host "  Checklist: Is URL Rewrite enabled? Is Application Request Routing (ARR) Proxy turned on?" -ForegroundColor Yellow
    }
} else {
    Write-Host "`n[+] Step 2: External Proxy check skipped." -ForegroundColor Yellow
    Write-Host "    To check your IIS Reverse Proxy domain, run:" -ForegroundColor Yellow
    Write-Host "    .\scripts\health_check.ps1 -ExternalUrl https://yourdomain.com" -ForegroundColor Yellow
}

Write-Host "`n==========================================================" -ForegroundColor Green
Write-Host "HEALTH CHECK DIAGNOSTICS COMPLETED!" -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Green
