$ErrorActionPreference = 'Stop'
$root = 'C:\Projects\YarTrader'
Set-Location $root
$logDir = Join-Path $root 'runtime_logs\backtest_validation'
New-Item -ItemType Directory -Path $logDir -Force | Out-Null
$stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$backup = Join-Path $logDir ("scheduled_backup_" + $stamp)
New-Item -ItemType Directory -Path $backup -Force | Out-Null
foreach ($p in @('runtime_logs\backtest_validation\base_mother_child_xauusd_1y.json','runtime_logs\mt5_gold_history_full\hierarchical_base_behavior_model_research.json','runtime_logs\mt5_gold_history_full\base_reaction_behavior_model_research.json')) { if (Test-Path $p) { Copy-Item -LiteralPath $p -Destination $backup } }
$log = Join-Path $logDir 'base_behavior_learning_scheduler.log'
$env:PYTHONUNBUFFERED = '1'
$env:PYTHONPATH = $root
Add-Content -Path $log -Value ("`n=== Base-only research/backtest started {0}; backup={1} ===" -f (Get-Date -Format o), $backup)
# Capture native Python stderr as ordinary log text; PowerShell 5 otherwise treats
# native stderr as a terminating error when ErrorActionPreference is Stop.
& (Join-Path $root '.venv\Scripts\python.exe') (Join-Path $root 'runtime_logs\backtest_validation\run_base_mother_child_backtest.py') 2>&1 | ForEach-Object { $_.ToString() | Add-Content -Path $log }
$exitCode = $LASTEXITCODE
Add-Content -Path $log -Value ("=== Base-only research/backtest finished {0}; exit={1} ===" -f (Get-Date -Format o), $exitCode)
exit $exitCode
