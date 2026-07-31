# Restart TradeYar-AI Windows Service Script

Write-Host "Restarting TradeYar-AI Windows Service..." -ForegroundColor Cyan

& "$PSScriptRoot\stop_service.ps1"
Start-Sleep -Seconds 2
& "$PSScriptRoot\start_service.ps1"
