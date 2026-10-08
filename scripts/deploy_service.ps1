# YarTrader Windows Service Deployment
# Canonical deployment entrypoint. Uses the pywin32 ServiceFramework installer
# so SCM hosts YarTrader through PythonService.exe rather than raw python.exe.

param(
    [string]$OperatorOwnerId = "owner_sohrab",
    [string]$YarOperatorRuntimeUrl = "http://127.0.0.1:3000"
)

$InstallScript = Join-Path $PSScriptRoot "install_service.ps1"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "Deploying YarTrader Windows Service..." -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

if (-not (Test-Path $InstallScript)) {
    Write-Error "Deployment Failed: canonical install script was not found at '$InstallScript'."
    Exit 1
}

# Keep a single service-registration implementation. This prevents the
# deployment path from silently reintroducing NSSM/raw-python registration.
& $InstallScript -OperatorOwnerId $OperatorOwnerId -YarOperatorRuntimeUrl $YarOperatorRuntimeUrl

if ($LASTEXITCODE -ne 0) {
    Write-Error "YarTrader service deployment failed."
    Exit $LASTEXITCODE
}

Write-Host "YarTrader service deployment completed through the canonical pywin32 installer." -ForegroundColor Green
