$ErrorActionPreference = 'Stop'
$root = 'C:\Projects\YarTrader'
Set-Location $root

$logDir = Join-Path $root 'runtime_logs\base_behavior_runtime'
New-Item -ItemType Directory -Path $logDir -Force | Out-Null
$log = Join-Path $logDir 'demo_worker.log'
$stdout = Join-Path $logDir 'demo_worker.stdout.log'
$stderr = Join-Path $logDir 'demo_worker.stderr.log'

# Make the task's environment explicit; the strategy itself still enforces every safety gate.
$token = [Environment]::GetEnvironmentVariable('YARTRADER_MT5_BRIDGE_TOKEN', 'Machine')
if ([string]::IsNullOrWhiteSpace($token)) { throw 'MT5 bridge token is missing from machine environment.' }
$env:YARTRADER_MT5_BRIDGE_TOKEN = $token
$allowDemo = [Environment]::GetEnvironmentVariable('YARTRADER_MT5_BRIDGE_ALLOW_DEMO_EXECUTION', 'Machine')
if (-not [string]::IsNullOrWhiteSpace($allowDemo)) { $env:YARTRADER_MT5_BRIDGE_ALLOW_DEMO_EXECUTION = $allowDemo }

$flagLine = Select-String -Path (Join-Path $root '.env.production') -Pattern '^YARTRADER_AUTONOMOUS_DEMO_TRADING_ENABLED=(.*)$' | Select-Object -First 1
if (-not $flagLine) { throw 'DEMO trading opt-in is missing from .env.production.' }
$demoFlag = $flagLine.Matches[0].Groups[1].Value.Trim().Trim('"').Trim("'").ToLowerInvariant()
$env:YARTRADER_AUTONOMOUS_DEMO_TRADING_ENABLED = $demoFlag
$env:AUTONOMOUS_DEMO_TRADING_ENABLED = $demoFlag
# Keep exploration opt-in separate from ordinary guarded DEMO trading.
$explorationLine = Select-String -Path (Join-Path $root '.env.production') -Pattern '^YARTRADER_DEMO_EXPLORATION_MODE=(.*)$' | Select-Object -First 1
$explorationFlag = if ($explorationLine) { $explorationLine.Matches[0].Groups[1].Value.Trim().Trim('"').Trim("'").ToLowerInvariant() } else { 'false' }
$env:YARTRADER_TRADING_MODE = 'DEMO'
$env:YARTRADER_DEMO_EXPLORATION_MODE = $explorationFlag
$env:YARTRADER_ENV = 'production'
$env:RG_ENV = 'production'
$env:PYTHONUNBUFFERED = '1'

Add-Content -Path $log -Value (([Environment]::NewLine) + '=== Base DEMO worker started ' + (Get-Date -Format o) + '; enabled=' + $demoFlag + '; exploration=' + $explorationFlag + ' ===')
$python = Join-Path $root '.venv\Scripts\python.exe'
$script = Join-Path $root 'scripts\run_base_behavior_demo_worker.py'
$proc = Start-Process -FilePath $python -ArgumentList @('-u', $script) -WorkingDirectory $root -PassThru -Wait -RedirectStandardOutput $stdout -RedirectStandardError $stderr
$exitCode = $proc.ExitCode
Add-Content -Path $log -Value ('=== Base DEMO worker exited ' + (Get-Date -Format o) + '; exit=' + $exitCode + ' ===')
exit $exitCode
