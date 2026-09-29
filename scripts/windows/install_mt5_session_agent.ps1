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
    $token = [Convert]::ToHexString([Security.Cryptography.RandomNumberGenerator]::GetBytes(32))
    [Environment]::SetEnvironmentVariable("YARTRADER_MT5_BRIDGE_TOKEN", $token, "Machine")
}

schtasks.exe /Delete /TN "$task" /F 2>$null | Out-Null
$action = '"' + $python + '" "' + $entry + '"'
schtasks.exe /Create /TN "$task" /TR $action /SC ONLOGON /RL HIGHEST /F | Out-Null

Write-Host "MT5 Session Agent task installed for the current user." -ForegroundColor Green
Write-Host "The agent must run in the same Windows session as terminal64.exe." -ForegroundColor Yellow
Write-Host "Token is stored as a machine environment variable and is not printed."

# Restart the LocalSystem service so it reads the machine-level token.
sc.exe stop YarTrader | Out-Null
Start-Sleep -Seconds 3
sc.exe start YarTrader | Out-Null
Write-Host "YarTrader restarted; it remains fail-closed until the session agent is reachable." -ForegroundColor Yellow
