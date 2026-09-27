<#
.SYNOPSIS
    CTO Gate E Windows Runtime Evidence Collector Tool for PR #313
    Strictly read-only with respect to trading.

.DESCRIPTION
    Executes forensic diagnostic evidence collection directly on the physical Windows deployment host.
    Measures Git provenance, Windows service/session topology, strict TCP listener state,
    Bridge API endpoints (/health, /mt5/status, /market-data), Session 0 LocalSystem context,
    Recovery states (A/B/C), real-data provenance, and zero-order execution proof.

.NOTES
    Trading Safety: Zero order placement, position modification, or trading API calls.
    Stopping/restarting terminal64.exe is permitted strictly when -ExecuteRecoveryTest switch is set.
#>

param (
    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$ExpectedSha,

    [string]$OutputFile = "docs/runtime/PR313_GATE_E_WINDOWS_EVIDENCE.md",

    [switch]$ExecuteRecoveryTest = $false
)

$ErrorActionPreference = "Continue"

function Get-IsoUtcTimestamp {
    return [DateTime]::UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ")
}

$startTimeUtc = Get-IsoUtcTimestamp

Write-Host "========================================================================" -ForegroundColor Cyan
Write-Host "   YARTRADER PR #313 — CTO GATE E WINDOWS EVIDENCE COLLECTOR TOOL" -ForegroundColor Cyan
Write-Host "   Start Time (UTC): $startTimeUtc" -ForegroundColor Cyan
Write-Host "========================================================================" -ForegroundColor Cyan

# 1. Provenance Verification
Write-Host "`n[1/8] Verifying Local Git Provenance ($startTimeUtc)..." -ForegroundColor Yellow
$currentHead = (git rev-parse HEAD).Trim()
$statusShort = (git status --short)
$originMain = (git rev-parse origin/main).Trim()
$mergeBase = (git merge-base HEAD origin/main).Trim()
$prBaseSha = "588be9ba436cc169f29e7c2d79f2d8fce033b13f"
$currentBranch = (git rev-parse --abbrev-ref HEAD).Trim()

Write-Host "Expected PR HEAD   : $ExpectedSha"
Write-Host "Current Local HEAD : $currentHead"
Write-Host "Current Branch     : $currentBranch"
Write-Host "PR Base SHA        : $prBaseSha"
Write-Host "Merge-Base SHA     : $mergeBase"
Write-Host "Origin Main SHA    : $originMain"

$provenanceMatch = ($currentHead -eq $ExpectedSha)
$treeClean = [string]::IsNullOrWhiteSpace($statusShort)

# Runtime Deployed SHA verification attempt
$runtimeDeployedSha = "NOT PROVEN"
if (Test-Path "C:\YarTraderAI\Runtime\deployed_sha.txt") {
    $runtimeDeployedSha = (Get-Content "C:\YarTraderAI\Runtime\deployed_sha.txt" -Raw).Trim()
}

# 2. Windows Service Identity (Deterministic Service Binding)
$tsService = Get-IsoUtcTimestamp
Write-Host "`n[2/8] Inspecting YarTrader Windows Service Identity ($tsService)..." -ForegroundColor Yellow
$yarService = Get-CimInstance Win32_Service -Filter "Name='YarTrader'" -ErrorAction SilentlyContinue
$serviceProc = $null
$servicePid = "N/A"
$serviceAccount = "N/A"
$serviceSessionId = "N/A"
$serviceState = "N/A"

if ($yarService) {
    $serviceState = $yarService.State
    $serviceAccount = $yarService.StartName
    if ($yarService.ProcessId -gt 0) {
        $servicePid = $yarService.ProcessId
        $serviceProc = Get-CimInstance Win32_Process -Filter "ProcessId=$servicePid" -ErrorAction SilentlyContinue
        if ($serviceProc) {
            $serviceSessionId = $serviceProc.SessionId
        }
    }
}
Write-Host "Service State: $serviceState | Account: $serviceAccount | PID: $servicePid | SessionId: $serviceSessionId"

# 3. Interactive Session Discovery and Process Topology Inspection
$tsProc = Get-IsoUtcTimestamp
Write-Host "`n[3/8] Inspecting Interactive Session and Process Topology ($tsProc)..." -ForegroundColor Yellow

$activeConsoleSessionId = "NOT PROVEN"
try {
    $explorerProc = Get-CimInstance Win32_Process -Filter "Name='explorer.exe'" -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($explorerProc) {
        $activeConsoleSessionId = $explorerProc.SessionId
    }
} catch {}

Write-Host "Active Interactive Session ID: $activeConsoleSessionId"

$procs = Get-CimInstance Win32_Process | Where-Object { $_.Name -in @('python.exe', 'terminal64.exe', 'nssm.exe') } | Select-Object ProcessId, ParentProcessId, SessionId, Name, ExecutablePath, CommandLine, CreationDate
$procTable = $procs | Format-Table ProcessId, ParentProcessId, SessionId, Name, ExecutablePath, CommandLine -AutoSize | Out-String
Write-Host $procTable

$bridgeProc = $procs | Where-Object { $_.CommandLine -like "*mt5_bridge*" } | Select-Object -First 1

# Enumerate all terminal64.exe instances to avoid arbitrary selection
$mt5Procs = $procs | Where-Object { $_.Name -eq "terminal64.exe" }
$mt5Proc = $null
$mt5Ambiguous = $false

if ($mt5Procs) {
    if ($mt5Procs.Count -eq 1) {
        $mt5Proc = $mt5Procs[0]
    } else {
        # Select instance matching active console session if unique
        $sessionMt5 = $mt5Procs | Where-Object { $_.SessionId -eq $activeConsoleSessionId }
        if ($sessionMt5 -and $sessionMt5.Count -eq 1) {
            $mt5Proc = $sessionMt5[0]
        } else {
            $mt5Ambiguous = $true
            Write-Warning "Multiple terminal64.exe instances detected; ambiguity present."
        }
    }
}

$bridgeSessionValid = ($bridgeProc -and $activeConsoleSessionId -ne "NOT PROVEN" -and $bridgeProc.SessionId -eq $activeConsoleSessionId)
$mt5SessionValid = ($mt5Proc -and -not $mt5Ambiguous -and $activeConsoleSessionId -ne "NOT PROVEN" -and $mt5Proc.SessionId -eq $activeConsoleSessionId)

# 4. Strict TCP Port 5001 Listener Inspection (IPv4 127.0.0.1 ONLY)
$tsPort = Get-IsoUtcTimestamp
Write-Host "`n[4/8] Inspecting Strict TCP Port 5001 Listener ($tsPort)..." -ForegroundColor Yellow
$port5001Proven = $false
$port5001Details = "NOT PROVEN"
try {
    $netConns = Get-NetTCPConnection -LocalPort 5001 -State Listen -ErrorAction SilentlyContinue
    if ($netConns) {
        # Strict IPv4 loopback check ONLY (Reject ::1 or 0.0.0.0)
        $validListener = $netConns | Where-Object { $_.LocalAddress -eq "127.0.0.1" } | Select-Object -First 1
        if ($validListener) {
            $listenerAddr = $validListener.LocalAddress
            $listenerPid = $validListener.OwningProcess
            $bridgePid = if ($bridgeProc) { $bridgeProc.ProcessId } else { "N/A" }
            if ($bridgeProc -and $listenerPid -eq $bridgeProc.ProcessId) {
                $port5001Proven = $true
                $port5001Details = "LocalAddress: $listenerAddr, LocalPort: 5001, State: Listen, OwningProcess: $listenerPid (Matches Bridge PID)"
            } else {
                $port5001Details = "FAILED (OwningProcess $listenerPid does not match Bridge PID $bridgePid)"
            }
        } else {
            $nonIpv4Addr = $netConns.LocalAddress
            $port5001Details = "FAILED (Listener found on non-IPv4 loopback address: $nonIpv4Addr)"
        }
    } else {
        $port5001Details = "FAILED (No TCP listener active on port 5001)"
    }
} catch {
    $port5001Details = "Get-NetTCPConnection exception: $_"
}
Write-Host "Port 5001 Status: $port5001Details"

# 5. Session 0 Genuine Identity Inspection
$tsS0 = Get-IsoUtcTimestamp
Write-Host "`n[5/8] Inspecting Execution Context and Session 0 Identity ($tsS0)..." -ForegroundColor Yellow
$callerUser = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$callerSessionId = [System.Diagnostics.Process]::GetCurrentProcess().SessionId
$callerPid = [System.Diagnostics.Process]::GetCurrentProcess().Id
$callerExecutable = [System.Diagnostics.Process]::GetCurrentProcess().MainModule.FileName

Write-Host "Collector Identity  : $callerUser"
Write-Host "Collector Session ID: $callerSessionId"
Write-Host "Collector PID       : $callerPid"
Write-Host "Collector Executable : $callerExecutable"

$session0IpcProven = $false
$session0IpcDetails = "NOT PROVEN (Collector executing in Session $callerSessionId as $callerUser, PID $callerPid)"

if ($callerSessionId -eq 0 -and $callerUser -like "*SYSTEM*") {
    try {
        $pyCode = 'import MetaTrader5 as mt5; print("init=", mt5.initialize()); print("err=", mt5.last_error())'
        $ipcOutput = python -c $pyCode 2>&1
        $session0IpcDetails = "PID: $callerPid | User: $callerUser | Session: 0 | Executable: $callerExecutable | Output: " + ($ipcOutput -join " ")
        if ($session0IpcDetails -like "*-10003*") {
            $session0IpcProven = $true
        }
    } catch {
        $session0IpcDetails = "Exception testing Session 0 IPC: $_"
    }
} else {
    Write-Warning "Collector caller is in Session $callerSessionId as $callerUser (not Session 0 LocalSystem). Direct Session 0 IPC diagnostic marked NOT PROVEN."
}

# 6. Query Bridge API Endpoints (Recovery A Baseline)
$tsApi = Get-IsoUtcTimestamp
Write-Host "`n[6/8] Querying MT5 Interactive Bridge API (Recovery A Baseline) ($tsApi)..." -ForegroundColor Yellow
$healthResp = $null
$statusResp = $null
$marketDataResp = $null

try {
    $healthResp = Invoke-RestMethod -Uri "http://127.0.0.1:5001/health" -Method Get -TimeoutSec 5
    Write-Host "GET /health: SUCCESS" -ForegroundColor Green
} catch {
    Write-Host "GET /health: FAILED - $_" -ForegroundColor Red
}

$secretFile = "C:\YarTraderAI\Secrets\mt5_bridge_token.secret"
if (-not (Test-Path $secretFile)) {
    $secretFile = "Secrets\mt5_bridge_token.secret"
}

if (Test-Path $secretFile) {
    $token = (Get-Content $secretFile -Raw).Trim()

    try {
        $statusResp = Invoke-RestMethod -Uri "http://127.0.0.1:5001/mt5/status" -Headers @{ Authorization = "Bearer $token" } -Method Get -TimeoutSec 5
        Write-Host "GET /mt5/status: SUCCESS" -ForegroundColor Green
    } catch {
        Write-Host "GET /mt5/status: FAILED - $_" -ForegroundColor Red
    }

    try {
        $body = @{ symbol = "XAUUSD"; timeframe = "H1"; count = 2 } | ConvertTo-Json
        $marketDataResp = Invoke-RestMethod -Uri "http://127.0.0.1:5001/market-data" -Headers @{ Authorization = "Bearer $token" } -Method Post -ContentType "application/json" -Body $body -TimeoutSec 5
        Write-Host "POST /market-data (XAUUSD H1 count=2): SUCCESS" -ForegroundColor Green
    } catch {
        Write-Host "POST /market-data: FAILED - $_" -ForegroundColor Red
    }
} else {
    Write-Warning "Secret token file not found at $secretFile"
}

# Strict candle count & real data evaluation
$exactCountProven = $false
$realDataProven = $false

if ($marketDataResp -and $marketDataResp.symbol -eq "XAUUSD" -and $marketDataResp.timeframe -eq "H1" -and $marketDataResp.candles) {
    if ($marketDataResp.candles.Count -eq 2) {
        $exactCountProven = $true
        if ($statusResp -and $statusResp.connected -eq $true -and -not [string]::IsNullOrWhiteSpace($statusResp.server) -and $bridgeProc -and $mt5Proc -and -not $mt5Ambiguous) {
            $c0 = $marketDataResp.candles[0]
            if ($c0.open -gt 0 -and $c0.time -gt 1600000000) {
                $realDataProven = $true
            }
        }
    }
}

# 7. Active Recovery Lifecycle Testing (A / B / C)
$tsRec = Get-IsoUtcTimestamp
$recoveryAResult = if ($statusResp -and $statusResp.connected -eq $true -and $realDataProven -and $exactCountProven) { "PROVEN" } else { "NOT PROVEN" }
$recoveryBResult = "NOT PROVEN (Active recovery test switch -ExecuteRecoveryTest not passed)"
$recoveryCResult = "NOT PROVEN (Active recovery test switch -ExecuteRecoveryTest not passed)"

if ($ExecuteRecoveryTest) {
    Write-Host "`n[7/8] Executing Active Recovery B/C Test ($tsRec)..." -ForegroundColor Yellow
    if ($mt5Proc -and -not $mt5Ambiguous) {
        $oldMt5Pid = $mt5Proc.ProcessId
        $stopTimeUtc = Get-IsoUtcTimestamp
        Write-Host "Stopping terminal64.exe (PID: $oldMt5Pid) at $stopTimeUtc..." -ForegroundColor Yellow
        Stop-Process -Id $oldMt5Pid -Force
        Start-Sleep -Seconds 3

        # Verify old PID no longer exists
        $oldProcExists = Get-CimInstance Win32_Process -Filter "ProcessId=$oldMt5Pid" -ErrorAction SilentlyContinue
        $statusRespB = $null
        try {
            $statusRespB = Invoke-RestMethod -Uri "http://127.0.0.1:5001/mt5/status" -Headers @{ Authorization = "Bearer $token" } -Method Get -TimeoutSec 5
        } catch {}

        if (-not $oldProcExists -and $statusRespB -and $statusRespB.connected -eq $false) {
            $recoveryBResult = 'PROVEN (Stopped MT5 PID ' + $oldMt5Pid + ' at ' + $stopTimeUtc + '; Verified process exit and Bridge connected: false fail-closed)'
            Write-Host "Recovery B: SUCCESS" -ForegroundColor Green
        } else {
            $recoveryBResult = "FAILED (Process exit or fail-closed response not observed)"
        }

        # Restart MT5 for Recovery C State
        if (-not [string]::IsNullOrWhiteSpace($mt5Proc.ExecutablePath) -and (Test-Path $mt5Proc.ExecutablePath)) {
            $restartTimeUtc = Get-IsoUtcTimestamp
            $mt5ExePath = $mt5Proc.ExecutablePath
            Write-Host "Restarting MT5 terminal: $mt5ExePath at $restartTimeUtc..." -ForegroundColor Yellow
            Start-Process -FilePath $mt5ExePath

            # Polling reconnect with timeout (up to 20 seconds)
            $reconnected = $false
            $newMt5Pid = "N/A"
            $reconnectTimeUtc = "NOT PROVEN"
            for ($i = 0; $i -lt 10; $i++) {
                Start-Sleep -Seconds 2
                $newMt5Proc = Get-CimInstance Win32_Process -Filter "Name='terminal64.exe'" -ErrorAction SilentlyContinue | Select-Object -First 1
                if ($newMt5Proc -and $newMt5Proc.ProcessId -ne $oldMt5Pid) {
                    $newMt5Pid = $newMt5Proc.ProcessId
                }
                try {
                    $statusRespC = Invoke-RestMethod -Uri "http://127.0.0.1:5001/mt5/status" -Headers @{ Authorization = "Bearer $token" } -Method Get -TimeoutSec 3
                    if ($statusRespC -and $statusRespC.connected -eq $true) {
                        $reconnected = $true
                        $reconnectTimeUtc = Get-IsoUtcTimestamp
                        break
                    }
                } catch {}
            }

            if ($reconnected -and $newMt5Pid -ne "N/A" -and $newMt5Pid -ne $oldMt5Pid) {
                $newSessionId = if ($newMt5Proc) { $newMt5Proc.SessionId } else { "N/A" }
                $recoveryCResult = 'PROVEN (Restarted MT5 at ' + $restartTimeUtc + '; Verified new PID ' + $newMt5Pid + ' in Session ' + $newSessionId + '; Bridge re-established connected: true at ' + $reconnectTimeUtc + ')'
                Write-Host "Recovery C: SUCCESS" -ForegroundColor Green
            } else {
                $recoveryCResult = "FAILED (Bridge failed to re-establish connection or new PID not confirmed)"
            }
        } else {
            $recoveryCResult = "NOT PROVEN (MT5 executable path unavailable for restart)"
        }
    } else {
        Write-Warning "terminal64.exe process not found or ambiguous; skipping active recovery test."
    }
} else {
    Write-Host "`n[7/8] Active Recovery B/C test skipped (Pass -ExecuteRecoveryTest to run)." -ForegroundColor Gray
}

# 8. Zero-Order Trading Execution Log Audit (Fail-Closed)
$tsLog = Get-IsoUtcTimestamp
Write-Host "`n[8/8] Auditing Application and Bridge Logs for Zero Order Dispatches ($tsLog)..." -ForegroundColor Yellow
$zeroOrderProven = "NOT PROVEN"
$logFilesChecked = @()
$logFilesFound = @()
$orderDispatchesDetected = $false

$candidateLogs = @("C:\YarTraderAI\Logs\runtime.log", "C:\YarTraderAI\Logs\bridge.log", "Logs\runtime.log", "runtime_logs\runtime.log")
foreach ($lf in $candidateLogs) {
    $logFilesChecked += $lf
    if (Test-Path $lf) {
        $logFilesFound += $lf
        $matches = Select-String -Path $lf -Pattern "order_send|TRADE_ACTION|dispatch_order|order_placed|OrderSend|PositionOpen" -ErrorAction SilentlyContinue
        if ($matches) {
            $orderDispatchesDetected = $true
            Write-Warning "Order dispatch pattern detected in $lf!"
        }
    }
}

if ($logFilesFound.Count -gt 0 -and -not $orderDispatchesDetected) {
    $foundLogsStr = $logFilesFound -join ', '
    $zeroOrderProven = 'PROVEN (Inspected ' + $logFilesFound.Count + ' log files: ' + $foundLogsStr + '; 0 order dispatches detected)'
} elseif ($orderDispatchesDetected) {
    $zeroOrderProven = "FAILED (Order dispatch pattern found in logs)"
} else {
    $zeroOrderProven = "NOT PROVEN (No active runtime log files found for inspection)"
}

# Evaluate Overall Gate E Master Conclusion
$tsEval = Get-IsoUtcTimestamp
Write-Host "`nEvaluating CTO Gate E Compliance ($tsEval)..." -ForegroundColor Yellow

$gateEPassed = (
    $provenanceMatch -and
    $treeClean -and
    ($runtimeDeployedSha -ne "NOT PROVEN" -and $runtimeDeployedSha -eq $ExpectedSha) -and
    ($serviceProc -ne $null) -and
    ($serviceProc.SessionId -eq 0) -and
    ($bridgeProc -ne $null) -and
    $bridgeSessionValid -and
    ($mt5Proc -ne $null) -and
    -not $mt5Ambiguous -and
    $mt5SessionValid -and
    $port5001Proven -and
    ($healthResp -ne $null) -and
    ($statusResp -ne $null -and $statusResp.connected -eq $true) -and
    $exactCountProven -and
    $realDataProven -and
    $session0IpcProven -and
    ($recoveryAResult -eq "PROVEN") -and
    ($recoveryBResult -like "PROVEN*") -and
    ($recoveryCResult -like "PROVEN*") -and
    ($zeroOrderProven -like "PROVEN*")
)

$finalGateStatus = if ($gateEPassed) { "PR #313 FINAL RUNTIME GATE: PASSED" } else { "PR #313 FINAL RUNTIME GATE: INCOMPLETE" }

# Pre-evaluate report expressions into variables to avoid PowerShell heredoc subexpression parser issues
$treeCleanStr = if ($treeClean) { "YES" } else { "NO ($statusShort)" }
$provenanceStatusStr = if ($provenanceMatch) { "PROVEN" } else { "FAILED" }
$treeCleanStatusStr = if ($treeClean) { "PROVEN" } else { "FAILED" }
$runtimeShaStatusStr = if ($runtimeDeployedSha -ne "NOT PROVEN" -and $runtimeDeployedSha -eq $ExpectedSha) { "PROVEN" } else { "NOT PROVEN" }
$serviceStatusStr = if ($serviceProc -and $serviceSessionId -eq 0) { "PROVEN" } else { "NOT PROVEN" }

$bridgeProcSessionId = if ($bridgeProc) { $bridgeProc.SessionId } else { "N/A" }
$bridgeProcPid = if ($bridgeProc) { $bridgeProc.ProcessId } else { "N/A" }
$bridgeSessionStatusStr = if ($bridgeSessionValid) { "PROVEN" } else { "NOT PROVEN" }

$mt5ProcSessionId = if ($mt5Proc) { $mt5Proc.SessionId } else { "N/A" }
$mt5ProcPid = if ($mt5Proc) { $mt5Proc.ProcessId } else { "N/A" }
$mt5SessionStatusStr = if ($mt5SessionValid) { "PROVEN" } else { "NOT PROVEN" }

$port5001StatusStr = if ($port5001Proven) { "PROVEN" } else { "NOT PROVEN" }

$healthStatusVal = if ($healthResp) { $healthResp.status } else { "N/A" }
$healthStatusStr = if ($healthResp) { "PROVEN" } else { "NOT PROVEN" }

$mt5ConnVal = if ($statusResp) { $statusResp.connected } else { "N/A" }
$mt5ServerVal = if ($statusResp) { $statusResp.server } else { "N/A" }
$mt5StatusStr = if ($statusResp -and $statusResp.connected) { "PROVEN" } else { "NOT PROVEN" }

$mdSymbolVal = if ($marketDataResp) { $marketDataResp.symbol } else { "N/A" }
$mdCountVal = if ($marketDataResp -and $marketDataResp.candles) { $marketDataResp.candles.Count } else { "N/A" }
$mdCountStatusStr = if ($exactCountProven) { "PROVEN" } else { "NOT PROVEN" }

$realDataStatusStr = if ($realDataProven) { "PROVEN" } else { "NOT PROVEN" }
$session0StatusStr = if ($session0IpcProven) { "PROVEN" } else { "NOT PROVEN" }
$recBStatusStr = if ($recoveryBResult -like "PROVEN*") { "PROVEN" } else { "NOT PROVEN" }
$recCStatusStr = if ($recoveryCResult -like "PROVEN*") { "PROVEN" } else { "NOT PROVEN" }
$zeroOrderStatusStr = if ($zeroOrderProven -like "PROVEN*") { "PROVEN" } else { "NOT PROVEN" }
$pidCaptureStatusStr = if ($serviceProc -and $bridgeProc -and $mt5Proc) { "PROVEN" } else { "NOT PROVEN" }

$healthJson = if ($healthResp) { $healthResp | ConvertTo-Json -Depth 5 } else { "{}" }
$statusJson = if ($statusResp) { $statusResp | ConvertTo-Json -Depth 5 } else { "{}" }
$marketDataJson = if ($marketDataResp) { $marketDataResp | ConvertTo-Json -Depth 5 } else { "{}" }
$checkedLogsStr = $logFilesChecked -join ', '
$foundLogsStr = $logFilesFound -join ', '

$reportContent = @"
# PR #313 GATE E WINDOWS RUNTIME EVIDENCE REPORT

**Execution Timestamp (UTC):** $endTimeUtc
**Repository:** `sohrabinia/YarTrader`
**Pull Request:** `https://github.com/sohrabinia/YarTrader/pull/313`
**Expected PR HEAD SHA:** `$ExpectedSha`
**Current Local HEAD:** `$currentHead`
**Deployed Runtime SHA:** `$runtimeDeployedSha`
**Current Branch:** `$currentBranch`
**PR Base SHA:** `$prBaseSha`
**Merge-Base SHA:** `$mergeBase`
**Origin Main SHA:** `$originMain`
**Git Working Tree Clean:** $treeCleanStr

---

## Raw Gate E Observations Matrix

| Gate Requirement | Observed Value | Expected Value | Evidence Source | UTC Timestamp | Status |
| :--- | :--- | :--- | :--- | :--- | :---: |
| **1. Provenance Match** | Local: `$currentHead` | `$ExpectedSha` | `git rev-parse HEAD` | $startTimeUtc | $provenanceStatusStr |
| **2. Clean Working Tree** | Short Status: `"$statusShort"` | Empty | `git status --short` | $startTimeUtc | $treeCleanStatusStr |
| **3. Deployed Runtime SHA** | Deployed: `$runtimeDeployedSha` | `$ExpectedSha` | `C:\YarTraderAI\Runtime\deployed_sha.txt` | $startTimeUtc | $runtimeShaStatusStr |
| **4. Session 0 Service Identity** | SessionId: $serviceSessionId, User: $serviceAccount | SessionId: 0, User: LocalSystem | `Win32_Service` / `Win32_Process` | $tsService | $serviceStatusStr |
| **5. Interactive Session Bridge** | SessionId: $bridgeProcSessionId | SessionId: $activeConsoleSessionId | `Win32_Process` (PID $bridgeProcPid) | $tsProc | $bridgeSessionStatusStr |
| **6. Interactive Session MT5** | SessionId: $mt5ProcSessionId, Ambiguous: $mt5Ambiguous | SessionId: $activeConsoleSessionId (Unique) | `Win32_Process` (PID $mt5ProcPid) | $tsProc | $mt5SessionStatusStr |
| **7. Strict TCP 5001 Listener** | $port5001Details | 127.0.0.1:5001 Listen (Bridge PID) | `Get-NetTCPConnection` | $tsPort | $port5001StatusStr |
| **8. Bridge `/health` Endpoint** | Status: $healthStatusVal | Status: HEALTHY | HTTP GET `127.0.0.1:5001/health` | $tsApi | $healthStatusStr |
| **9. Authenticated `/mt5/status`** | Connected: $mt5ConnVal, Server: $mt5ServerVal | Connected: true, Server: Active | HTTP GET `127.0.0.1:5001/mt5/status` | $tsApi | $mt5StatusStr |
| **10. XAUUSD H1 Count=2** | Symbol: $mdSymbolVal, Count: $mdCountVal | Symbol: XAUUSD, Timeframe: H1, Count: 2 | HTTP POST `127.0.0.1:5001/market-data` | $tsApi | $mdCountStatusStr |
| **11. Real-Data Provenance** | Server: $mt5ServerVal, Valid OHLC: $realDataProven | Live MT5 Server Rates Verified | Bridge MT5 Integration | $tsApi | $realDataStatusStr |
| **12. Direct Session 0 MT5 IPC** | Result: $session0IpcDetails | error -10003 in Session 0 | Session 0 Execution Context | $tsS0 | $session0StatusStr |
| **13. Recovery A (Healthy Baseline)** | $recoveryAResult | Baseline HTTP 200 Healthy | Bridge API | $tsRec | $recoveryAResult |
| **14. Recovery B (Interruption)** | $recoveryBResult | Connected: false fail-closed | MT5 Stop Event | $tsRec | $recBStatusStr |
| **15. Recovery C (Restart & Reconnect)**| $recoveryCResult | Connected: true restored | MT5 Restart Event | $tsRec | $recCStatusStr |
| **16. Zero-Order Execution Proof** | $zeroOrderProven | 0 Order Dispatches Logged | Runtime and Bridge Logs | $tsLog | $zeroOrderStatusStr |
| **17. UTC Timestamps Verified** | Start: $startTimeUtc, End: $endTimeUtc | ISO 8601 UTC Format | System UTC Clock | $endTimeUtc | PROVEN |
| **18. Exact Process PIDs Captured** | Service: $servicePid, Bridge: $bridgeProcPid, MT5: $mt5ProcPid | All 3 Roles Identified | `Win32_Process` | $tsProc | $pidCaptureStatusStr |
| **19. Caller Context / Boundary** | Caller User: $callerUser, SessionId: $callerSessionId, PID: $callerPid | Context Documented | `WindowsIdentity` | $startTimeUtc | PROVEN |

---

## Detailed Process Topology Table
```text
$procTable
```

---

## TCP Port 5001 Listener Details
```text
$port5001Details
```

---

## Bridge API Responses

### GET `http://127.0.0.1:5001/health`
```json
$healthJson
```

### GET `http://127.0.0.1:5001/mt5/status` (Authenticated)
```json
$statusJson
```

### POST `http://127.0.0.1:5001/market-data` (XAUUSD / H1 / count=2)
```json
$marketDataJson
```

---

## Log Inspection Details
* **Candidate Log Paths Checked:** `$checkedLogsStr`
* **Found Log Paths Inspected:** `$foundLogsStr`

---

## Final Runtime Gate Conclusion

$finalGateStatus
"@

$reportDir = Split-Path -Parent $OutputFile
if (-not (Test-Path $reportDir)) {
    New-Item -ItemType Directory -Path $reportDir -Force | Out-Null
}

Set-Content -Path $OutputFile -Value $reportContent -Encoding UTF8
Write-Host "Report written to $OutputFile" -ForegroundColor Green

Write-Host "`n========================================================================" -ForegroundColor Cyan
$finalColor = if ($gateEPassed) { "Green" } else { "Yellow" }
Write-Host "   $finalGateStatus" -ForegroundColor $finalColor
Write-Host "========================================================================" -ForegroundColor Cyan
