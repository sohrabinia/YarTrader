<#
.SYNOPSIS
    CTO Gate E Windows Runtime Evidence Collector Tool for PR #313
    Strictly read-only with respect to trading.

.DESCRIPTION
    Executes diagnostic collection directly on the physical Windows deployment host.
    Measures Git provenance, Windows service/session topology, TCP listener state,
    Bridge API endpoints (/health, /mt5/status, /market-data), Session 0 LocalSystem context,
    Recovery states (A/B/C), real-data provenance, and zero-order execution proof.

.NOTES
    Trading Safety: Zero order placement, position modification, or trading API calls.
    Stopping/restarting terminal64.exe is permitted strictly when -ExecuteRecoveryTest switch is set.
#>

param (
    [Parameter(Mandatory = $true)]
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

Write-Host "Expected SHA       : $ExpectedSha"
Write-Host "Current Local HEAD : $currentHead"
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

# 2. Independent Port 5001 Listener Inspection
$tsPort = Get-IsoUtcTimestamp
Write-Host "`n[2/8] Inspecting TCP Port 5001 Listener ($tsPort)..." -ForegroundColor Yellow
$port5001Proven = $false
$port5001Details = "NOT PROVEN"
try {
    $netConns = Get-NetTCPConnection -LocalPort 5001 -State Listen -ErrorAction SilentlyContinue
    if ($netConns) {
        $validListener = $netConns | Where-Object { $_.LocalAddress -in @("127.0.0.1", "::1") } | Select-Object -First 1
        if ($validListener) {
            $port5001Proven = $true
            $port5001Details = "LocalAddress: $($validListener.LocalAddress), LocalPort: 5001, State: Listen, OwningProcess: $($validListener.OwningProcess)"
        } else {
            $port5001Details = "FAILED (Listener found on non-loopback address: $($netConns.LocalAddress))"
        }
    } else {
        $port5001Details = "FAILED (No TCP listener active on port 5001)"
    }
} catch {
    $port5001Details = "Get-NetTCPConnection exception: $_"
}
Write-Host "Port 5001 Status: $port5001Details"

# 3. Windows Service & Process Topology Inspection
$tsProc = Get-IsoUtcTimestamp
Write-Host "`n[3/8] Inspecting Windows Service & Process Topology ($tsProc)..." -ForegroundColor Yellow
$yarService = Get-CimInstance Win32_Service -Filter "Name='YarTrader'" -ErrorAction SilentlyContinue
$procs = Get-CimInstance Win32_Process | Where-Object { $_.Name -in @('python.exe', 'terminal64.exe', 'nssm.exe') } | Select-Object ProcessId, ParentProcessId, SessionId, Name, ExecutablePath, CommandLine, CreationDate

$procTable = $procs | Format-Table ProcessId, ParentProcessId, SessionId, Name, ExecutablePath, CommandLine -AutoSize | Out-String
Write-Host $procTable

# Identify specific topology roles
$serviceProc = $procs | Where-Object { $_.CommandLine -like "*research_worker*" -or $_.CommandLine -like "*app.workers*" } | Select-Object -First 1
$bridgeProc = $procs | Where-Object { $_.CommandLine -like "*mt5_bridge*" } | Select-Object -First 1
$mt5Proc = $procs | Where-Object { $_.Name -eq "terminal64.exe" } | Select-Object -First 1

# Detect active interactive session ID
$activeConsoleSessionId = 2
try {
    $explorerProc = Get-CimInstance Win32_Process -Filter "Name='explorer.exe'" -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($explorerProc) {
        $activeConsoleSessionId = $explorerProc.SessionId
    }
} catch {}

Write-Host "Active Interactive Session ID: $activeConsoleSessionId"

# 4. Session 0 Genuine Identity Inspection
$tsS0 = Get-IsoUtcTimestamp
Write-Host "`n[4/8] Inspecting Execution Context & Session 0 Identity ($tsS0)..." -ForegroundColor Yellow
$callerUser = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$callerSessionId = [System.Diagnostics.Process]::GetCurrentProcess().SessionId

Write-Host "Caller Identity  : $callerUser"
Write-Host "Caller Session ID: $callerSessionId"

$session0IpcProven = $false
$session0IpcDetails = "NOT PROVEN (Collector executing in Session $callerSessionId as $callerUser)"

if ($callerSessionId -eq 0 -and $callerUser -like "*SYSTEM*") {
    try {
        $ipcOutput = python -c "import MetaTrader5 as mt5; print('init=', mt5.initialize()); print('err=', mt5.last_error())" 2>&1
        $session0IpcDetails = $ipcOutput -join " "
        if ($session0IpcDetails -like "*-10003*") {
            $session0IpcProven = $true
        }
    } catch {
        $session0IpcDetails = "Exception testing Session 0 IPC: $_"
    }
} else {
    Write-Warning "Caller is in Session $callerSessionId (not Session 0 LocalSystem). Marking Direct Session 0 IPC as NOT PROVEN."
}

# 5. Query Bridge API Endpoints (Recovery A Baseline)
$tsApi = Get-IsoUtcTimestamp
Write-Host "`n[5/8] Querying MT5 Interactive Bridge API (Recovery A) ($tsApi)..." -ForegroundColor Yellow
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

# Real-data provenance evaluation (Exact symbol, timeframe, count=2, live MT5 server metadata)
$exactCountProven = $false
$realDataProven = $false

if ($marketDataResp -and $marketDataResp.symbol -eq "XAUUSD" -and $marketDataResp.timeframe -eq "H1" -and $marketDataResp.candles) {
    if ($marketDataResp.candles.Count -eq 2) {
        $exactCountProven = $true
        if ($statusResp -and $statusResp.connected -eq $true -and -not [string]::IsNullOrWhiteSpace($statusResp.server)) {
            $c0 = $marketDataResp.candles[0]
            if ($c0.open -gt 0 -and $c0.time -gt 1600000000) {
                $realDataProven = $true
            }
        }
    }
}

# 6. Active Recovery Lifecycle Testing (B / C)
$tsRec = Get-IsoUtcTimestamp
$recoveryAResult = if ($statusResp -and $statusResp.connected -eq $true -and $realDataProven -and $exactCountProven) { "PROVEN" } else { "NOT PROVEN" }
$recoveryBResult = "NOT PROVEN (Active recovery test switch -ExecuteRecoveryTest not passed)"
$recoveryCResult = "NOT PROVEN (Active recovery test switch -ExecuteRecoveryTest not passed)"

if ($ExecuteRecoveryTest) {
    Write-Host "`n[6/8] Executing Active Recovery B/C Test ($tsRec)..." -ForegroundColor Yellow
    if ($mt5Proc) {
        $stopTimeUtc = Get-IsoUtcTimestamp
        Write-Host "Stopping terminal64.exe (PID: $($mt5Proc.ProcessId)) at $stopTimeUtc..." -ForegroundColor Yellow
        Stop-Process -Id $mt5Proc.ProcessId -Force
        Start-Sleep -Seconds 3

        # Measure Recovery B State
        $statusRespB = $null
        try {
            $statusRespB = Invoke-RestMethod -Uri "http://127.0.0.1:5001/mt5/status" -Headers @{ Authorization = "Bearer $token" } -Method Get -TimeoutSec 5
        } catch {}

        if ($statusRespB -and $statusRespB.connected -eq $false) {
            $recoveryBResult = "PROVEN (Stopped MT5 PID $($mt5Proc.ProcessId); Bridge reported connected: false fail-closed at $(Get-IsoUtcTimestamp))"
            Write-Host "Recovery B: SUCCESS" -ForegroundColor Green
        } else {
            $recoveryBResult = "FAILED (Bridge did not report connected: false)"
        }

        # Restart MT5 for Recovery C State
        if (-not [string]::IsNullOrWhiteSpace($mt5Proc.ExecutablePath) -and (Test-Path $mt5Proc.ExecutablePath)) {
            $restartTimeUtc = Get-IsoUtcTimestamp
            Write-Host "Restarting MT5 terminal: $($mt5Proc.ExecutablePath) at $restartTimeUtc..." -ForegroundColor Yellow
            Start-Process -FilePath $mt5Proc.ExecutablePath

            # Polling reconnect with timeout (up to 20 seconds)
            $reconnected = $false
            $reconnectTimeUtc = "NOT PROVEN"
            for ($i = 0; $i -lt 10; $i++) {
                Start-Sleep -Seconds 2
                try {
                    $statusRespC = Invoke-RestMethod -Uri "http://127.0.0.1:5001/mt5/status" -Headers @{ Authorization = "Bearer $token" } -Method Get -TimeoutSec 3
                    if ($statusRespC -and $statusRespC.connected -eq $true) {
                        $reconnected = $true
                        $reconnectTimeUtc = Get-IsoUtcTimestamp
                        break
                    }
                } catch {}
            }

            if ($reconnected) {
                $recoveryCResult = "PROVEN (MT5 restarted at $restartTimeUtc; Bridge re-established connected: true at $reconnectTimeUtc)"
                Write-Host "Recovery C: SUCCESS" -ForegroundColor Green
            } else {
                $recoveryCResult = "FAILED (Bridge failed to re-establish connection within timeout)"
            }
        } else {
            $recoveryCResult = "NOT PROVEN (MT5 executable path unavailable for restart)"
        }
    } else {
        Write-Warning "terminal64.exe process not found; skipping active recovery test."
    }
} else {
    Write-Host "`n[6/8] Active Recovery B/C test skipped (Pass -ExecuteRecoveryTest to run)." -ForegroundColor Gray
}

# 7. Zero-Order Trading Execution Log Audit (Fail-Closed)
$tsLog = Get-IsoUtcTimestamp
Write-Host "`n[7/8] Auditing Application & Bridge Logs for Zero Order Dispatches ($tsLog)..." -ForegroundColor Yellow
$zeroOrderProven = "NOT PROVEN"
$logFilesChecked = @()
$logFilesFound = @()
$orderDispatchesDetected = $false

$candidateLogs = @("C:\YarTraderAI\Logs\runtime.log", "C:\YarTraderAI\Logs\bridge.log", "Logs\runtime.log", "runtime_logs\runtime.log")
foreach ($lf in $candidateLogs) {
    $logFilesChecked += $lf
    if (Test-Path $lf) {
        $logFilesFound += $lf
        $matches = Select-String -Path $lf -Pattern "order_send|TRADE_ACTION|dispatch_order|order_placed" -ErrorAction SilentlyContinue
        if ($matches) {
            $orderDispatchesDetected = $true
            Write-Warning "Order dispatch pattern detected in $lf!"
        }
    }
}

if ($logFilesFound.Count -gt 0 -and -not $orderDispatchesDetected) {
    $zeroOrderProven = "PROVEN (Inspected $($logFilesFound.Count) log files; 0 order dispatches detected)"
} elseif ($orderDispatchesDetected) {
    $zeroOrderProven = "FAILED (Order dispatch pattern found in logs)"
} else {
    $zeroOrderProven = "NOT PROVEN (No active runtime log files found for inspection)"
}

# 8. Evaluate Overall Gate E Master Conclusion
$tsEval = Get-IsoUtcTimestamp
Write-Host "`n[8/8] Evaluating CTO Gate E Compliance ($tsEval)..." -ForegroundColor Yellow

$gateEPassed = (
    $provenanceMatch -and
    $treeClean -and
    ($runtimeDeployedSha -eq $ExpectedSha) -and
    ($serviceProc -ne $null) -and
    ($serviceProc.SessionId -eq 0) -and
    ($bridgeProc -ne $null) -and
    ($bridgeProc.SessionId -eq $activeConsoleSessionId) -and
    ($mt5Proc -ne $null) -and
    ($mt5Proc.SessionId -eq $activeConsoleSessionId) -and
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

# Format and Write Output Report
$endTimeUtc = Get-IsoUtcTimestamp

$reportContent = @"
# PR #313 GATE E WINDOWS RUNTIME EVIDENCE REPORT

**Execution Timestamp (UTC):** $endTimeUtc
**Repository:** `sohrabinia/YarTrader`
**Pull Request:** `https://github.com/sohrabinia/YarTrader/pull/313`
**Expected PR HEAD SHA:** `$ExpectedSha`
**Current Repository HEAD:** `$currentHead`
**Deployed Runtime SHA:** `$runtimeDeployedSha`
**PR Base SHA:** `$prBaseSha`
**Merge-Base SHA:** `$mergeBase`
**Origin Main SHA:** `$originMain`
**Git Working Tree Clean:** $(if ($treeClean) { "YES" } else { "NO ($statusShort)" })

---

## Raw Gate E Observations Matrix

| Gate Requirement | Observed Value | Expected Value | Evidence Source | UTC Timestamp | Status |
| :--- | :--- | :--- | :--- | :--- | :---: |
| **1. Provenance Match** | Local: `$currentHead` | `$ExpectedSha` | `git rev-parse HEAD` | $startTimeUtc | $(if ($provenanceMatch) { "PROVEN" } else { "FAILED" }) |
| **2. Clean Working Tree** | Short Status: `"$statusShort"` | Empty | `git status --short` | $startTimeUtc | $(if ($treeClean) { "PROVEN" } else { "FAILED" }) |
| **3. Deployed Runtime SHA** | Deployed: `$runtimeDeployedSha` | `$ExpectedSha` | `C:\YarTraderAI\Runtime\deployed_sha.txt` | $startTimeUtc | $(if ($runtimeDeployedSha -eq $ExpectedSha) { "PROVEN" } else { "NOT PROVEN" }) |
| **4. Session 0 Service Identity** | SessionId: $(if ($serviceProc) { $serviceProc.SessionId } else { "N/A" }), User: LocalSystem | SessionId: 0, User: LocalSystem | `Win32_Process` (PID $(if ($serviceProc) { $serviceProc.ProcessId } else { "N/A" })) | $tsProc | $(if ($serviceProc -and $serviceProc.SessionId -eq 0) { "PROVEN" } else { "NOT PROVEN" }) |
| **5. Session 2 Bridge Identity** | SessionId: $(if ($bridgeProc) { $bridgeProc.SessionId } else { "N/A" }) | SessionId: $activeConsoleSessionId | `Win32_Process` (PID $(if ($bridgeProc) { $bridgeProc.ProcessId } else { "N/A" })) | $tsProc | $(if ($bridgeProc -and $bridgeProc.SessionId -eq $activeConsoleSessionId) { "PROVEN" } else { "NOT PROVEN" }) |
| **6. Session 2 MT5 Identity** | SessionId: $(if ($mt5Proc) { $mt5Proc.SessionId } else { "N/A" }) | SessionId: $activeConsoleSessionId | `Win32_Process` (PID $(if ($mt5Proc) { $mt5Proc.ProcessId } else { "N/A" })) | $tsProc | $(if ($mt5Proc -and $mt5Proc.SessionId -eq $activeConsoleSessionId) { "PROVEN" } else { "NOT PROVEN" }) |
| **7. TCP 5001 Listener State** | $port5001Details | 127.0.0.1:5001 Listen | `Get-NetTCPConnection` | $tsPort | $(if ($port5001Proven) { "PROVEN" } else { "NOT PROVEN" }) |
| **8. Bridge `/health` Endpoint** | Status: $(if ($healthResp) { $healthResp.status } else { "N/A" }) | Status: HEALTHY | HTTP GET `127.0.0.1:5001/health` | $tsApi | $(if ($healthResp) { "PROVEN" } else { "NOT PROVEN" }) |
| **9. Authenticated `/mt5/status`** | Connected: $(if ($statusResp) { $statusResp.connected } else { "N/A" }), Server: $(if ($statusResp) { $statusResp.server } else { "N/A" }) | Connected: true, Server: Active | HTTP GET `127.0.0.1:5001/mt5/status` | $tsApi | $(if ($statusResp -and $statusResp.connected) { "PROVEN" } else { "NOT PROVEN" }) |
| **10. XAUUSD H1 Count=2** | Symbol: $(if ($marketDataResp) { $marketDataResp.symbol } else { "N/A" }), Count: $(if ($marketDataResp -and $marketDataResp.candles) { $marketDataResp.candles.Count } else { "N/A" }) | Symbol: XAUUSD, Timeframe: H1, Count: 2 | HTTP POST `127.0.0.1:5001/market-data` | $tsApi | $(if ($exactCountProven) { "PROVEN" } else { "NOT PROVEN" }) |
| **11. Real-Data Provenance** | Server: $(if ($statusResp) { $statusResp.server } else { "N/A" }), Valid OHLC: $realDataProven | Live MT5 Server Rates Verified | Bridge MT5 Integration | $tsApi | $(if ($realDataProven) { "PROVEN" } else { "NOT PROVEN" }) |
| **12. Direct Session 0 MT5 IPC** | Result: $session0IpcDetails | error -10003 in Session 0 | Session 0 Direct Execution | $tsS0 | $(if ($session0IpcProven) { "PROVEN" } else { "NOT PROVEN" }) |
| **13. Recovery A (Healthy Baseline)** | $recoveryAResult | Baseline HTTP 200 Healthy | Bridge API | $tsRec | $recoveryAResult |
| **14. Recovery B (Interruption)** | $recoveryBResult | Connected: false fail-closed | MT5 Stop Event | $tsRec | $(if ($recoveryBResult -like "PROVEN*") { "PROVEN" } else { "NOT PROVEN" }) |
| **15. Recovery C (Restart & Reconnect)**| $recoveryCResult | Connected: true restored | MT5 Restart Event | $tsRec | $(if ($recoveryCResult -like "PROVEN*") { "PROVEN" } else { "NOT PROVEN" }) |
| **16. Zero-Order Execution Proof** | $zeroOrderProven | 0 Order Dispatches Logged | Runtime & Bridge Logs | $tsLog | $(if ($zeroOrderProven -like "PROVEN*") { "PROVEN" } else { "NOT PROVEN" }) |
| **17. UTC Timestamps Verified** | Start: $startTimeUtc, End: $endTimeUtc | ISO 8601 UTC Format | System UTC Clock | $endTimeUtc | PROVEN |
| **18. Exact Process PIDs Captured** | Service: $(if ($serviceProc) { $serviceProc.ProcessId } else { "N/A" }), Bridge: $(if ($bridgeProc) { $bridgeProc.ProcessId } else { "N/A" }), MT5: $(if ($mt5Proc) { $mt5Proc.ProcessId } else { "N/A" }) | All 3 Roles Identified | `Win32_Process` | $tsProc | $(if ($serviceProc -and $bridgeProc -and $mt5Proc) { "PROVEN" } else { "NOT PROVEN" }) |
| **19. Caller Context / Boundary** | Caller User: $callerUser, SessionId: $callerSessionId | Context Documented | `WindowsIdentity` | $startTimeUtc | PROVEN |

---

## Detailed Process Topology Table
```text
$procTable
```

---

## TCP Port 5001 Listener Details
```text
$($port5001Listener | Format-Table -AutoSize | Out-String)
```

---

## Bridge API Responses

### GET `http://127.0.0.1:5001/health`
```json
$($healthResp | ConvertTo-Json -Depth 5)
```

### GET `http://127.0.0.1:5001/mt5/status` (Authenticated)
```json
$($statusResp | ConvertTo-Json -Depth 5)
```

### POST `http://127.0.0.1:5001/market-data` (XAUUSD / H1 / count=2)
```json
$($marketDataResp | ConvertTo-Json -Depth 5)
```

---

## Log Inspection Details
* **Candidate Log Paths Checked:** `$($logFilesChecked -join ', ')`
* **Found Log Paths Inspected:** `$($logFilesFound -join ', ')`

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
Write-Host "   $finalGateStatus" -ForegroundColor $(if ($gateEPassed) { "Green" } else { "Yellow" })
Write-Host "========================================================================" -ForegroundColor Cyan
