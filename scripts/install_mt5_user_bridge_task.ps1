# PowerShell Script to Install YarTrader MT5 User-Session Bridge Scheduled Task
# Registers a Windows Scheduled Task running scripts/run_mt5_user_session_bridge.py at user logon

$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$BridgeScript = Join-Path $ProjectRoot "scripts\run_mt5_user_session_bridge.py"

if (-not (Test-Path $VenvPython)) {
    Write-Error "Virtual environment python.exe not found at $VenvPython"
}

if (-not (Test-Path $BridgeScript)) {
    Write-Error "Bridge script not found at $BridgeScript"
}

$TaskName = "YarTrader_MT5_UserSession_Bridge"
$TaskDescription = "Runs local MT5 User-Session Bridge in interactive user desktop session for YarTrader Windows Service"

# Unregister existing task if present
Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue

# Define action, trigger, principal and settings
$Action = New-ScheduledTaskAction -Execute $VenvPython -Argument "`"$BridgeScript`"" -WorkingDirectory $ProjectRoot
$Trigger = New-ScheduledTaskTrigger -AtLogOn
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Days 365) -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)

Register-ScheduledTask -TaskName $TaskName -Description $TaskDescription -Action $Action -Trigger $Trigger -Settings $Settings -User $env:USERNAME

Write-Host "[SUCCESS] Registered Windows Scheduled Task: $TaskName" -ForegroundColor Green
Write-Host "[INFO] The task will start automatically at user logon or can be triggered manually using:" -ForegroundColor Cyan
Write-Host "       Start-ScheduledTask -TaskName '$TaskName'" -ForegroundColor Yellow
