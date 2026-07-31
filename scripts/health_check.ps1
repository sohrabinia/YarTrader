# Health Check Script for TradeYar AI Production Service

$HealthUrl = "http://127.0.0.1:8000/health"

Write-Host "Querying TradeYar AI Production Service Health..." -ForegroundColor Cyan

try {
    $response = Invoke-RestMethod -Uri $HealthUrl -Method Get -TimeoutSec 5

    Write-Host "==========================================================" -ForegroundColor Green
    Write-Host "SERVICE HEALTH STATE: $($response.status)" -ForegroundColor Green
    Write-Host "==========================================================" -ForegroundColor Green
    Write-Host "Service Name: $($response.service)"
    Write-Host "API Gateway : $($response.api)"
    Write-Host "MT5 Link    : $($response.mt5)"
    Write-Host "Intelligence: $($response.intelligence)"
    Write-Host "Background  : $($response.worker)"
    Write-Host "Timestamp   : $($response.timestamp)"
    Write-Host "==========================================================" -ForegroundColor Green
} catch {
    Write-Host "==========================================================" -ForegroundColor Red
    Write-Host "SERVICE UNHEALTHY or OFFLINE" -ForegroundColor Red
    Write-Host "==========================================================" -ForegroundColor Red
    Write-Host "Error details: $($_.Exception.Message)" -ForegroundColor Yellow
}
