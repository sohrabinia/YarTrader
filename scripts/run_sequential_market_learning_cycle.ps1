$ErrorActionPreference = 'Stop'
$root = 'C:\Projects\YarTrader'
Set-Location $root
$logDir = Join-Path $root 'runtime_logs\sequential_learning_cycles'
New-Item -ItemType Directory -Path $logDir -Force | Out-Null
$log = Join-Path $logDir 'scheduler.log'
Add-Content -Path $log -Value ("`n=== Sequential research cycle started {0} ===" -f (Get-Date -Format o))
& (Join-Path $root '.venv\Scripts\python.exe') (Join-Path $root 'scripts\run_sequential_market_learning_cycle.py') --years 1 --timeframe H1 --output-dir 'runtime_logs/sequential_learning_cycles' *>> $log
$exitCode = $LASTEXITCODE
Add-Content -Path $log -Value ("=== Sequential research cycle finished {0}; exit={1} ===" -f (Get-Date -Format o), $exitCode)
exit $exitCode
