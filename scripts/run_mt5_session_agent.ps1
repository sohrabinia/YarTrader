$ErrorActionPreference = 'Stop'
$root = 'C:\Projects\YarTrader'
Set-Location $root

# Task Scheduler may keep an older environment snapshot after machine variables change.
# Read the protected machine-scoped bridge settings explicitly; never log the token.
$token = [Environment]::GetEnvironmentVariable('YARTRADER_MT5_BRIDGE_TOKEN', 'Machine')
if ([string]::IsNullOrWhiteSpace($token)) {
    throw 'YARTRADER_MT5_BRIDGE_TOKEN is missing from machine environment.'
}
$env:YARTRADER_MT5_BRIDGE_TOKEN = $token
$allowDemo = [Environment]::GetEnvironmentVariable('YARTRADER_MT5_BRIDGE_ALLOW_DEMO_EXECUTION', 'Machine')
if (-not [string]::IsNullOrWhiteSpace($allowDemo)) {
    $env:YARTRADER_MT5_BRIDGE_ALLOW_DEMO_EXECUTION = $allowDemo
}

$logDir = Join-Path $root 'runtime_logs\base_behavior_runtime'
New-Item -ItemType Directory -Path $logDir -Force | Out-Null
$log = Join-Path $logDir 'mt5_session_agent.log'
Add-Content -Path $log -Value (([Environment]::NewLine) + '=== MT5 Session Agent started ' + (Get-Date -Format o) + ' ===')
$env:PYTHONUNBUFFERED = '1'
& (Join-Path $root '.venv\Scripts\python.exe') -u -m app.workers.mt5_session_agent *>> $log
$exitCode = $LASTEXITCODE
Add-Content -Path $log -Value ('=== MT5 Session Agent exited ' + (Get-Date -Format o) + '; exit=' + $exitCode + ' ===')
exit $exitCode
