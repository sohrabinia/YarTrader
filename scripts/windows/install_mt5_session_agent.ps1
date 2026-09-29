# Installs the interactive-session MT5 bridge for the currently logged-in Windows user.
# Run from an elevated PowerShell on the production machine.
$ErrorActionPreference = "Stop"

$repo = "C:\Projects\YarTrader"
$python = "$repo\.venv\Scripts\python.exe"
$entry = "$repo\app\workers\mt5_session_agent.py"
$task = "YarTrader MT5 Session Agent"

if (-not (Test-Path $python)) { throw "YarTrader Python not found: $python" }
if (-not (Test-Path $entry)) { throw "MT5 bridge entrypoint not found: $entry" }

$token = [Environment]::GetEnvironmentVariable("YARTRADER_MT5_BRIDGE_TOKEN", "Machine")
if ([string]::IsNullOrWhiteSpace($token)) {
    $bytes = New-Object byte[] 32
    $rng = [Security.Cryptography.RandomNumberGenerator]::Create()
    try {
        $rng.GetBytes($bytes)
    }
    finally {
        $rng.Dispose()
    }
    $token = [BitConverter]::ToString($bytes).Replace("-", "").ToLowerInvariant()
    [Environment]::SetEnvironmentVariable("YARTRADER_MT5_BRIDGE_TOKEN", $token, "Machine")
}

# Register the agent as an interactive user task. The working directory is
# explicit so the module entrypoint can import the repository's src package.
$action = New-ScheduledTaskAction `
    -Execute $python `
    -Argument "-m app.workers.mt5_session_agent" `
    -WorkingDirectory $repo
$principal = New-ScheduledTaskPrincipal `
    -UserId "$env:USERDOMAIN\$env:USERNAME" `
    -LogonType Interactive `
    -RunLevel Highest
$trigger = New-ScheduledTaskTrigger -AtLogOn -User "$env:USERDOMAIN\$env:USERNAME"

Unregister-ScheduledTask -TaskName $task -Confirm:$false -ErrorAction SilentlyContinue
Register-ScheduledTask `
    -TaskName $task `
    -Action $action `
    -Principal $principal `
    -Trigger $trigger `
    -Force | Out-Null

Write-Host "MT5 Session Agent task installed for the current user." -ForegroundColor Green
Write-Host "The agent must run in the same Windows session as terminal64.exe." -ForegroundColor Yellow
Write-Host "Token is stored as a machine environment variable and is not printed."

# Restart the LocalSystem service so it reads the machine-level token.
sc.exe stop YarTrader | Out-Null
Start-Sleep -Seconds 3
sc.exe start YarTrader | Out-Null
Write-Host "YarTrader restarted; it remains fail-closed until the session agent is reachable." -ForegroundColor Yellow
