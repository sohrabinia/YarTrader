$ErrorActionPreference = 'Stop'
$root = 'C:\Projects\YarTrader'
Set-Location $root
$logDir = Join-Path $root 'runtime_logs\base_behavior_runtime'
New-Item -ItemType Directory -Path $logDir -Force | Out-Null
$log = Join-Path $logDir 'demo_worker.log'
Add-Content -Path $log -Value ("`n=== Base DEMO worker started {0} ===" -f (Get-Date -Format o))
$env:PYTHONUNBUFFERED = '1'
& (Join-Path $root '.venv\Scripts\python.exe') -u (Join-Path $root 'scripts\run_base_behavior_demo_worker.py') *>> $log
$exitCode = $LASTEXITCODE
Add-Content -Path $log -Value ("=== Base DEMO worker exited {0}; exit={1} ===" -f (Get-Date -Format o), $exitCode)
exit $exitCode
