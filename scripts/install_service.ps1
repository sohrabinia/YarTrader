# Install YarTrader Windows Service Script
# Canonical production registration: NSSM -> venv Python -> service.py console runner.
# pywin32 ServiceFramework remains available for diagnostics/debugging only.

param(
    [string]$OperatorOwnerId = "owner_sohrab",
    [string]$YarOperatorRuntimeUrl = "http://127.0.0.1:3000",
    [string]$NssmPath = ""
)

$ErrorActionPreference = "Stop"

$ServiceName = "YarTrader"
$ServiceDisplayName = "YarTrader Production Runtime Service"
$ServiceDescription = "Coordinates the 24/7 background AI runtime, MT5 connector, research, and DEMO execution."
$VenvPython = (Resolve-Path (Join-Path $PSScriptRoot "..\.venv\Scripts\python.exe")).Path
$ScriptPath = (Resolve-Path (Join-Path $PSScriptRoot "..\app\workers\service.py")).Path
$WorkDir = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$LogDir = Join-Path $WorkDir "logs\windows_service"
$StdoutLog = Join-Path $LogDir "service_stdout.log"
$StderrLog = Join-Path $LogDir "service_stderr.log"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "Installing YarTrader Windows Service (NSSM)..." -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
    [Security.Principal.WindowsBuiltInRole]::Administrator
)
if (-not $isAdmin) { throw "Deployment Failed: this script must be run as Administrator." }

if ([string]::IsNullOrWhiteSpace($OperatorOwnerId)) { throw "Deployment Failed: OPERATOR_OWNER_ID is required." }
if ([string]::IsNullOrWhiteSpace($YarOperatorRuntimeUrl)) { throw "Deployment Failed: YAROPERATOR_RUNTIME_URL is required." }
if (-not ($YarOperatorRuntimeUrl.StartsWith("http://127.0.0.1") -or $YarOperatorRuntimeUrl.StartsWith("http://localhost"))) {
    throw "Deployment Failed: YAROPERATOR_RUNTIME_URL must be loopback-only."
}

$SecretsDir = Join-Path $WorkDir "secrets"
$SecretsFile = Join-Path $SecretsDir "operator_owner_token.secret"
$OperatorOwnerToken = $env:OPERATOR_OWNER_TOKEN
if ([string]::IsNullOrWhiteSpace($OperatorOwnerToken) -and (Test-Path $SecretsFile)) {
    $OperatorOwnerToken = (Get-Content -Path $SecretsFile -Raw -ErrorAction SilentlyContinue).Trim()
}
if ([string]::IsNullOrWhiteSpace($OperatorOwnerToken)) {
    throw "Deployment Failed: OPERATOR_OWNER_TOKEN environment variable or $SecretsFile is required."
}
if (-not (Test-Path $SecretsDir)) { New-Item -ItemType Directory -Force -Path $SecretsDir | Out-Null }
Set-Content -Path $SecretsFile -Value $OperatorOwnerToken -Encoding UTF8 -NoNewline -Force
icacls.exe "$SecretsFile" /inheritance:r /grant:r "SYSTEM:(F)" /grant:r "Administrators:(F)" | Out-Null

if ([string]::IsNullOrWhiteSpace($NssmPath) -and -not [string]::IsNullOrWhiteSpace($env:NSSM_PATH)) {
    $NssmPath = $env:NSSM_PATH
}
if ([string]::IsNullOrWhiteSpace($NssmPath)) {
    $cmd = Get-Command nssm.exe -ErrorAction SilentlyContinue
    if ($cmd) { $NssmPath = $cmd.Source }
}
if ([string]::IsNullOrWhiteSpace($NssmPath)) {
    $known = @(
        "C:\Tools\nssm\nssm-2.24-101-g897c7ad\win64\nssm.exe",
        "C:\Tools\nssm\win64\nssm.exe"
    ) | Where-Object { Test-Path $_ } | Select-Object -First 1
    if ($known) { $NssmPath = $known }
}
if ([string]::IsNullOrWhiteSpace($NssmPath) -or -not (Test-Path $NssmPath)) {
    throw "Deployment Failed: NSSM executable not found. Supply -NssmPath or set NSSM_PATH."
}
$NssmPath = (Resolve-Path $NssmPath).Path

New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

$existing = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
if ($existing) {
    Write-Host "Stopping existing '$ServiceName' service..." -ForegroundColor Yellow
    sc.exe stop $ServiceName | Out-Null
    Start-Sleep -Seconds 2
    Write-Host "Removing existing '$ServiceName' registration..." -ForegroundColor Yellow
    sc.exe delete $ServiceName | Out-Null
    Start-Sleep -Seconds 3
}

Write-Host "Registering NSSM service..." -ForegroundColor Yellow
& $NssmPath install $ServiceName $VenvPython $ScriptPath
if ($LASTEXITCODE -ne 0) { throw "NSSM service installation failed with exit code $LASTEXITCODE." }

& $NssmPath set $ServiceName AppDirectory $WorkDir
& $NssmPath set $ServiceName DisplayName $ServiceDisplayName
& $NssmPath set $ServiceName Description $ServiceDescription
& $NssmPath set $ServiceName ObjectName LocalSystem
& $NssmPath set $ServiceName Start SERVICE_AUTO_START
& $NssmPath set $ServiceName AppNoConsole 1
& $NssmPath set $ServiceName AppThrottle 5000
& $NssmPath set $ServiceName AppRestartDelay 5000
& $NssmPath set $ServiceName AppExit Default Restart
& $NssmPath set $ServiceName AppStopMethodSkip 0
& $NssmPath set $ServiceName AppStopMethodConsole 5000
& $NssmPath set $ServiceName AppStopMethodWindow 5000
& $NssmPath set $ServiceName AppStopMethodThreads 5000
& $NssmPath set $ServiceName AppStdout $StdoutLog
& $NssmPath set $ServiceName AppStderr $StderrLog
& $NssmPath set $ServiceName AppEnvironmentExtra "OPERATOR_OWNER_ID=$OperatorOwnerId" "YAROPERATOR_RUNTIME_URL=$YarOperatorRuntimeUrl"
if ($LASTEXITCODE -ne 0) { throw "NSSM configuration failed with exit code $LASTEXITCODE." }

sc.exe failure $ServiceName reset= 86400 actions= restart/5000/restart/10000/restart/30000 | Out-Null

$service = Get-CimInstance Win32_Service -Filter "Name='$ServiceName'"
if (-not $service) { throw "Deployment verification failed: YarTrader service was not registered." }
if ($service.StartName -ne "LocalSystem") { throw "Deployment verification failed: service account is '$($service.StartName)', expected LocalSystem." }
if ($service.PathName -notmatch "(?i)nssm\.exe") { throw "Deployment verification failed: service is not hosted by NSSM. PathName='$($service.PathName)'" }

$app = (& $NssmPath get $ServiceName Application).Trim()
$appDir = (& $NssmPath get $ServiceName AppDirectory).Trim()
$appParams = (& $NssmPath get $ServiceName AppParameters).Trim()

if ($app -ne $VenvPython) { throw "Deployment verification failed: NSSM Application='$app'; expected '$VenvPython'." }
if ($appDir -ne $WorkDir) { throw "Deployment verification failed: NSSM AppDirectory='$appDir'; expected '$WorkDir'." }
if ($appParams -ne $ScriptPath) { throw "Deployment verification failed: NSSM AppParameters='$appParams'; expected '$ScriptPath'." }

Write-Host "YarTrader NSSM service registration verified." -ForegroundColor Green
Write-Host "  Service: $ServiceName" -ForegroundColor Green
Write-Host "  NSSM: $NssmPath" -ForegroundColor Green
Write-Host "  Python: $VenvPython" -ForegroundColor Green
Write-Host "  Entrypoint: $ScriptPath" -ForegroundColor Green
Write-Host "  Account: LocalSystem" -ForegroundColor Green
Write-Host "  Startup: Automatic" -ForegroundColor Green
