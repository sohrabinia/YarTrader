# YarTrader Windows Service Deployment
# Canonical production deployment entrypoint.
# Production SCM hosting uses NSSM -> venv Python -> app/workers/service.py.

param(
    [string]$OperatorOwnerId = "owner_sohrab",
    [string]$YarOperatorRuntimeUrl = "http://127.0.0.1:3000",
    [string]$NssmPath = ""
)

$InstallScript = Join-Path $PSScriptRoot "install_service.ps1"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "Deploying YarTrader Windows Service..." -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

if (-not (Test-Path $InstallScript)) {
    Write-Error "Deployment Failed: canonical install script was not found at '$InstallScript'."
    Exit 1
}

& $InstallScript -OperatorOwnerId $OperatorOwnerId -YarOperatorRuntimeUrl $YarOperatorRuntimeUrl -NssmPath $NssmPath
if ($LASTEXITCODE -ne 0) {
    Write-Error "YarTrader service deployment failed."
    Exit $LASTEXITCODE
}

Write-Host "YarTrader service deployment completed through the canonical NSSM installer." -ForegroundColor Green
