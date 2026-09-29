# YarTrader v0.2.0 production migration inventory
# Read-only: this script does NOT modify, delete, migrate, or clear anything.

$ErrorActionPreference = "Continue"
$root = "C:\Projects\YarTrader"

Write-Host "=== SERVICE / DEMO RUNTIME ===" -ForegroundColor Cyan
Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
  Where-Object { $_.CommandLine -match "app\\workers\\service.py" } |
  Select-Object ProcessId, CommandLine | Format-List

Write-Host "AUTONOMOUS_DEMO_TRADING_ENABLED (Machine):" -ForegroundColor Yellow
[Environment]::GetEnvironmentVariable("AUTONOMOUS_DEMO_TRADING_ENABLED","Machine")

Write-Host "=== WINDOWS SERVICE CONFIG ===" -ForegroundColor Cyan
Get-CimInstance Win32_Service -Filter "Name='YarTrader'" |
  Select-Object Name, State, StartMode, StartName, PathName | Format-List

Write-Host "=== CANDIDATE DATABASE / MEMORY FILES ===" -ForegroundColor Cyan
$patterns = @("*.db","*.sqlite","*.sqlite3","events_memory.json","experiences_memory.json","patterns_memory.json","concepts_memory.json","pattern_outcomes.json","learning_memory.json","demo_trades.json","shadow_trades.json","backtest_runs.json")
$roots = @($root, (Join-Path $root "runtime_logs"), (Join-Path $root "data")) | Where-Object { Test-Path $_ } | Select-Object -Unique
$files = foreach ($r in $roots) { Get-ChildItem -Path $r -Recurse -File -ErrorAction SilentlyContinue | Where-Object { $patterns -contains $_.Name -or $_.Extension -in @(".db",".sqlite",".sqlite3") } }
$files | Sort-Object FullName -Unique | Select-Object FullName, Length, LastWriteTime | Format-Table -AutoSize

Write-Host "=== MACHINE ENVIRONMENT: PRESERVE / DO NOT CHANGE HERE ===" -ForegroundColor Cyan
Get-ChildItem Env: | Where-Object { $_.Name -match "^(YARTRADER_|GOOGLE_|RG_DB_|YAROPERATOR_)" } |
  Sort-Object Name | Select-Object Name, Value | Format-Table -AutoSize

Write-Host "=== GIT WORKTREE ===" -ForegroundColor Cyan
Set-Location $root
git rev-parse HEAD
git status --short
