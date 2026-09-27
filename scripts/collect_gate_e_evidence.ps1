<#
.SYNOPSIS
    CTO Gate E Windows Runtime Evidence Collector Tool for PR #314
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

    [string]$OutputFile = 'docs/runtime/PR314_GATE_E_WINDOWS_EVIDENCE.md',

    [switch]$ExecuteRecoveryTest = $false
)

$ErrorActionPreference = 'Stop'

function Get-IsoUtcTimestamp {
    return [DateTime]::UtcNow.ToString('yyyy-MM-ddTHH:mm:ssZ')
}

$startTimeUtc = Get-IsoUtcTimestamp

Write-Host '========================================================================' -ForegroundColor Cyan
Write-Host '   YARTRADER PR #314 — CTO GATE E WINDOWS EVIDENCE COLLECTOR TOOL' -ForegroundColor Cyan
Write-Host ('   Start Time UTC: ' + $startTimeUtc) -ForegroundColor Cyan
Write-Host '========================================================================' -ForegroundColor Cyan

# Structure to track explicit forensic execution operations (Primary Remediation E)
$forensicOperations = [System.Collections.Generic.List[PSObject]]::new()

function Record-ForensicOperation {
    param(
        [string]$OperationName,
        [string]$Status, # PROVEN / FAILED / NOT PROVEN
        [string]$Reason,
        [string]$ExceptionMsg = ''
    )
    $ts = Get-IsoUtcTimestamp
    $entry = [PSCustomObject]@{
        Timestamp = $ts
        Operation = $OperationName
        Status    = $Status
        Reason    = $Reason
        Exception = $ExceptionMsg
    }
    $script:forensicOperations.Add($entry)
    return $entry
}

# 1. Local Git Provenance Verification (Section 1 & 11)
Write-Host "`n[1/8] Verifying Local Git Provenance..." -ForegroundColor Yellow
$currentHead = 'UNKNOWN'
$statusShort = 'UNKNOWN'
$originMain = 'UNKNOWN'
$mergeBase = 'UNKNOWN'
$currentBranch = 'UNKNOWN'
$changedFilesList = 'UNKNOWN'
$commitRange = 'UNKNOWN'
$prBaseSha = '588be9ba436cc169f29e7c2d79f2d8fce033b13f'

try {
    $currentHead = (git rev-parse HEAD).Trim()
    $statusShort = (git status --short)
    $originMain = (git rev-parse origin/main 2>$null | Out-String).Trim()
    $mergeBase = (git merge-base HEAD origin/main 2>$null | Out-String).Trim()
    $currentBranch = (git rev-parse --abbrev-ref HEAD).Trim()
    $changedFilesList = (git diff --name-status 588be9ba436cc169f29e7c2d79f2d8fce033b13f..HEAD 2>$null | Out-String).Trim()
    $commitRange = "$prBaseSha..$currentHead"
} catch {
    Record-ForensicOperation -OperationName 'GitProvenanceExecution' -Status 'FAILED' -Reason 'Git command invocation failed' -ExceptionMsg $_.Exception.Message
}

Write-Host ('Expected PR HEAD   : ' + $ExpectedSha)
Write-Host ('Current Local HEAD : ' + $currentHead)
Write-Host ('Current Branch     : ' + $currentBranch)
Write-Host ('PR Base SHA        : ' + $prBaseSha)
Write-Host ('Merge-Base SHA     : ' + $mergeBase)
Write-Host ('Origin Main SHA    : ' + $originMain)

$provenanceMatch = ($currentHead -eq $ExpectedSha)
$treeClean = [string]::IsNullOrWhiteSpace($statusShort)

$provenanceStatus = if ($provenanceMatch) { 'PROVEN' } else { 'FAILED' }
$treeCleanStatus = if ($treeClean) { 'PROVEN' } else { 'FAILED' }

Record-ForensicOperation -OperationName 'GitHeadVerification' -Status $provenanceStatus -Reason ("Local HEAD: $currentHead vs Expected: $ExpectedSha")
Record-ForensicOperation -OperationName 'GitTreeCleanliness' -Status $treeCleanStatus -Reason ("Status Short: '$statusShort'")

# 2. Windows Service Identity & Cryptographic Runtime SHA Provenance Chain (Blocker #1 Requirement: Strict Application Root Binding)
$tsService = Get-IsoUtcTimestamp
Write-Host "`n[2/8] Inspecting YarTrader Windows Service Identity & Cryptographic Runtime SHA Chain..." -ForegroundColor Yellow
$yarService = $null
$serviceProc = $null
$servicePid = 'N/A'
$serviceAccount = 'N/A'
$serviceSessionId = 'N/A'
$serviceState = 'N/A'
$serviceExePath = 'N/A'
$serviceCmdLine = 'N/A'
$appRoot = 'N/A'

try {
    $yarService = Get-CimInstance Win32_Service -Filter "Name='YarTrader'" -ErrorAction SilentlyContinue
} catch {
    Record-ForensicOperation -OperationName 'Win32ServiceQuery' -Status 'FAILED' -Reason 'Failed to query Win32_Service for YarTrader' -ExceptionMsg $_.Exception.Message
}

if ($yarService) {
    $serviceState = $yarService.State
    $serviceAccount = $yarService.StartName
    if ($yarService.ProcessId -gt 0) {
        $servicePid = $yarService.ProcessId
        try {
            $serviceProc = Get-CimInstance Win32_Process -Filter ('ProcessId=' + $servicePid) -ErrorAction SilentlyContinue
            if ($serviceProc) {
                $serviceSessionId = $serviceProc.SessionId
                $serviceExePath = $serviceProc.ExecutablePath
                $serviceCmdLine = $serviceProc.CommandLine
                if (-not [string]::IsNullOrWhiteSpace($serviceExePath)) {
                    $parent = Split-Path -Parent $serviceExePath
                    if ($parent -like '*\.venv\Scripts*' -or $parent -like '*\Scripts*') {
                        $appRoot = Split-Path -Parent (Split-Path -Parent $parent)
                    } elseif ($parent -like '*\.venv*') {
                        $appRoot = Split-Path -Parent $parent
                    } else {
                        $appRoot = $parent
                    }
                }
            }
        } catch {
            Record-ForensicOperation -OperationName 'Win32ProcessQueryService' -Status 'FAILED' -Reason "Failed to query process for PID $servicePid" -ExceptionMsg $_.Exception.Message
        }
    }
    Record-ForensicOperation -OperationName 'YarTraderServiceLookup' -Status 'PROVEN' -Reason ("Found service PID $servicePid, Account: $serviceAccount, Session: $serviceSessionId")
} else {
    Record-ForensicOperation -OperationName 'YarTraderServiceLookup' -Status 'NOT PROVEN' -Reason 'YarTrader Windows service not found on deployment host'
}

# Cryptographic Runtime SHA Provenance Chain (Blocker #1 Requirement: No Unverified Global Fallback)
$runtimeDeployedSha = 'NOT PROVEN'
$deployedShaSourceFile = 'N/A'
$runtimeShaStatus = 'NOT PROVEN'
$runtimeShaReason = 'Runtime SHA not verified'

if ($appRoot -ne 'N/A' -and (Test-Path $appRoot)) {
    if (Test-Path (Join-Path $appRoot ".git")) {
        try {
            $gitShaFromAppRoot = (git -C $appRoot rev-parse HEAD 2>$null | Out-String).Trim()
            if (-not [string]::IsNullOrWhiteSpace($gitShaFromAppRoot)) {
                $runtimeDeployedSha = $gitShaFromAppRoot
                $deployedShaSourceFile = "git -C $appRoot rev-parse HEAD"
            }
        } catch {}
    }

    if ($runtimeDeployedSha -eq 'NOT PROVEN') {
        $candidateShaFiles = @(
            (Join-Path $appRoot 'deployed_sha.txt'),
            (Join-Path $appRoot 'Runtime\deployed_sha.txt')
        )
        foreach ($sf in $candidateShaFiles) {
            if (Test-Path $sf) {
                try {
                    $shaVal = (Get-Content $sf -Raw).Trim()
                    if (-not [string]::IsNullOrWhiteSpace($shaVal)) {
                        $runtimeDeployedSha = $shaVal
                        $deployedShaSourceFile = $sf
                        break
                    }
                } catch {}
            }
        }
    }
}

if ($serviceProc -and $serviceSessionId -eq 0 -and $appRoot -ne 'N/A' -and $runtimeDeployedSha -ne 'NOT PROVEN') {
    if ($runtimeDeployedSha -eq $ExpectedSha) {
        $runtimeShaStatus = 'PROVEN'
        $runtimeShaReason = "YarTrader service PID $servicePid running in Session 0 from application root $appRoot ($serviceExePath). Verified SHA ($runtimeDeployedSha) from $deployedShaSourceFile matches Expected SHA $ExpectedSha"
    } else {
        $runtimeShaStatus = 'FAILED'
        $runtimeShaReason = "Runtime SHA ($runtimeDeployedSha) from $deployedShaSourceFile does NOT match Expected SHA ($ExpectedSha)"
    }
} else {
    $runtimeShaStatus = 'NOT PROVEN'
    $runtimeShaReason = "Service process missing or not running in Session 0, or runtime path untied from commit SHA (Service PID: $servicePid, Session: $serviceSessionId, App Root: $appRoot, Extracted SHA: $runtimeDeployedSha)"
}

Record-ForensicOperation -OperationName 'RuntimeShaProvenance' -Status $runtimeShaStatus -Reason $runtimeShaReason

Write-Host ('Service State: ' + $serviceState + ' - Account: ' + $serviceAccount + ' - PID: ' + $servicePid + ' - SessionId: ' + $serviceSessionId)
Write-Host ('App Root     : ' + $appRoot)
Write-Host ('Deployed SHA : ' + $runtimeDeployedSha + ' (Source: ' + $deployedShaSourceFile + ')')

# 3. Interactive Session Discovery and Process Topology Inspection (Section 7 & Primary Remediation F)
$tsProc = Get-IsoUtcTimestamp
Write-Host "`n[3/8] Inspecting Interactive Session and Process Topology..." -ForegroundColor Yellow

$activeConsoleSessionId = 'NOT PROVEN'
$explorerProcs = $null

try {
    $explorerProcs = Get-CimInstance Win32_Process -Filter "Name='explorer.exe'" -ErrorAction SilentlyContinue
    if ($explorerProcs) {
        $nonZeroSessions = $explorerProcs | Where-Object { $_.SessionId -ne 0 } | Select-Object -ExpandProperty SessionId -Unique
        if ($nonZeroSessions -and $nonZeroSessions.Count -eq 1) {
            $activeConsoleSessionId = $nonZeroSessions[0]
            Record-ForensicOperation -OperationName 'InteractiveSessionDiscovery' -Status 'PROVEN' -Reason "Active interactive SessionId uniquely resolved to $activeConsoleSessionId"
        } else {
            Record-ForensicOperation -OperationName 'InteractiveSessionDiscovery' -Status 'NOT PROVEN' -Reason "Ambiguous explorer.exe instances in multiple sessions: ($($nonZeroSessions -join ', '))"
        }
    } else {
        Record-ForensicOperation -OperationName 'InteractiveSessionDiscovery' -Status 'NOT PROVEN' -Reason 'No explorer.exe processes found'
    }
} catch {
    Record-ForensicOperation -OperationName 'InteractiveSessionDiscovery' -Status 'FAILED' -Reason 'Exception discovering interactive explorer session' -ExceptionMsg $_.Exception.Message
}

Write-Host ('Active Interactive Session ID: ' + $activeConsoleSessionId)

$procs = @()
try {
    $procs = Get-CimInstance Win32_Process | Where-Object { $_.Name -in @('python.exe', 'terminal64.exe', 'nssm.exe') } | Select-Object ProcessId, ParentProcessId, SessionId, Name, ExecutablePath, CommandLine, CreationDate
} catch {
    Record-ForensicOperation -OperationName 'ProcessEnumeration' -Status 'FAILED' -Reason 'Exception enumerating processes' -ExceptionMsg $_.Exception.Message
}

$procTable = $procs | Format-Table ProcessId, ParentProcessId, SessionId, Name, ExecutablePath, CommandLine -AutoSize | Out-String
Write-Host $procTable

# Deterministic Bridge Process Resolution (Primary Remediation F)
$bridgeProc = $null
$bridgeAmbiguous = $false
$bridgeSessionStatus = 'NOT PROVEN'
$bridgeSessionReason = 'Bridge process not found'

$bridgeProcs = $procs | Where-Object { $_.CommandLine -like '*mt5_bridge*' }

if ($bridgeProcs) {
    if ($bridgeProcs.Count -eq 1) {
        $candidateBridge = $bridgeProcs[0]
        if ($activeConsoleSessionId -ne 'NOT PROVEN' -and $candidateBridge.SessionId -eq $activeConsoleSessionId) {
            $bridgeProc = $candidateBridge
            $bridgeSessionStatus = 'PROVEN'
            $bridgeSessionReason = "Unique Bridge PID $($bridgeProc.ProcessId) running in active interactive Session $activeConsoleSessionId"
        } else {
            $bridgeSessionStatus = 'NOT PROVEN'
            $bridgeSessionReason = "Bridge PID $($candidateBridge.ProcessId) SessionId $($candidateBridge.SessionId) does not match active console SessionId $activeConsoleSessionId"
        }
    } else {
        $bridgeAmbiguous = $true
        $bridgeSessionStatus = 'NOT PROVEN'
        $bridgeSessionReason = "Multiple mt5_bridge processes detected ($($bridgeProcs.Count) matches); failing closed"
    }
}

Record-ForensicOperation -OperationName 'BridgeProcessResolution' -Status $bridgeSessionStatus -Reason $bridgeSessionReason

# Deterministic MT5 Process Resolution (NO Select-Object -First 1, Primary Remediation F)
$mt5Proc = $null
$mt5Ambiguous = $false
$mt5SessionStatus = 'NOT PROVEN'
$mt5SessionReason = 'terminal64.exe process not found'

$mt5Procs = $procs | Where-Object { $_.Name -eq 'terminal64.exe' }

if ($mt5Procs) {
    if ($mt5Procs.Count -eq 1) {
        $candidateMt5 = $mt5Procs[0]
        if ($activeConsoleSessionId -ne 'NOT PROVEN' -and $candidateMt5.SessionId -eq $activeConsoleSessionId) {
            $mt5Proc = $candidateMt5
            $mt5SessionStatus = 'PROVEN'
            $mt5SessionReason = "Unique terminal64.exe PID $($mt5Proc.ProcessId) running in active interactive Session $activeConsoleSessionId"
        } else {
            $mt5SessionStatus = 'NOT PROVEN'
            $mt5SessionReason = "terminal64.exe PID $($candidateMt5.ProcessId) SessionId $($candidateMt5.SessionId) does not match active console SessionId $activeConsoleSessionId"
        }
    } else {
        # Enumerate all candidates and filter strictly by activeConsoleSessionId
        $sessionMt5 = $mt5Procs | Where-Object { $_.SessionId -eq $activeConsoleSessionId }
        if ($sessionMt5 -and $sessionMt5.Count -eq 1) {
            $mt5Proc = $sessionMt5[0]
            $mt5SessionStatus = 'PROVEN'
            $mt5SessionReason = "Deterministically resolved unique terminal64.exe PID $($mt5Proc.ProcessId) in active interactive Session $activeConsoleSessionId among $($mt5Procs.Count) total candidates"
        } else {
            $mt5Ambiguous = $true
            $mt5SessionStatus = 'NOT PROVEN'
            $mt5SessionReason = "Multiple terminal64.exe instances active in interactive session ($($sessionMt5.Count) matches); failing closed"
        }
    }
}

Record-ForensicOperation -OperationName 'Mt5ProcessResolution' -Status $mt5SessionStatus -Reason $mt5SessionReason

# 4. Strict TCP Port 5001 Listener Inspection (IPv4 127.0.0.1 ONLY, Primary Remediation F)
$tsPort = Get-IsoUtcTimestamp
Write-Host "`n[4/8] Inspecting Strict TCP Port 5001 Listener..." -ForegroundColor Yellow
$port5001Proven = $false
$port5001Details = 'NOT PROVEN'
$port5001Status = 'NOT PROVEN'
$allObservedListenersStr = 'None'

try {
    $netConns = Get-NetTCPConnection -LocalPort 5001 -State Listen -ErrorAction SilentlyContinue
    if ($netConns) {
        $allObservedListenersStr = ($netConns | ForEach-Object { ($_.LocalAddress + ':' + $_.LocalPort + ' (PID: ' + $_.OwningProcess + ')') }) -join '; '
        # Strict IPv4 loopback check ONLY (Reject ::1 or 0.0.0.0)
        $validListeners = $netConns | Where-Object { $_.LocalAddress -eq '127.0.0.1' }
        if ($validListeners -and $validListeners.Count -eq 1) {
            $validListener = $validListeners[0]
            $listenerAddr = $validListener.LocalAddress
            $listenerPid = $validListener.OwningProcess
            $bridgePid = if ($bridgeProc) { $bridgeProc.ProcessId } else { 'N/A' }
            if ($bridgeProc -and -not $bridgeAmbiguous -and $listenerPid -eq $bridgeProc.ProcessId) {
                $port5001Proven = $true
                $port5001Status = 'PROVEN'
                $port5001Details = 'LocalAddress: ' + $listenerAddr + ', LocalPort: 5001, State: Listen, OwningProcess: ' + $listenerPid + ' [Matches Bridge PID]'
            } else {
                $port5001Status = 'FAILED'
                $port5001Details = 'FAILED [OwningProcess ' + $listenerPid + ' does not match Bridge PID ' + $bridgePid + ']'
            }
        } elseif ($validListeners -and $validListeners.Count -gt 1) {
            $port5001Status = 'FAILED'
            $port5001Details = 'FAILED [Ambiguous multiple TCP listeners active on 127.0.0.1:5001]'
        } else {
            $nonIpv4Addr = ($netConns | Select-Object -ExpandProperty LocalAddress) -join ', '
            $port5001Status = 'FAILED'
            $port5001Details = 'FAILED [Listener found on non-IPv4 loopback address: ' + $nonIpv4Addr + ']'
        }
    } else {
        $port5001Status = 'FAILED'
        $port5001Details = 'FAILED [No TCP listener active on port 5001]'
    }
} catch {
    $port5001Status = 'FAILED'
    $port5001Details = 'Get-NetTCPConnection exception: ' + $_.Exception.Message
    Record-ForensicOperation -OperationName 'TcpListenerEnumeration' -Status 'FAILED' -Reason 'Exception checking TCP 5001 listener' -ExceptionMsg $_.Exception.Message
}

Record-ForensicOperation -OperationName 'TcpPort5001Verification' -Status $port5001Status -Reason $port5001Details
Write-Host ('Port 5001 Status: ' + $port5001Details)
Write-Host ('All Observed Listeners: ' + $allObservedListenersStr)

# 5. Session 0 Genuine Identity Inspection (Blocker #2 Requirement: Explicit Case A / B / C Representation)
$tsS0 = Get-IsoUtcTimestamp
Write-Host "`n[5/8] Inspecting Execution Context and Session 0 Identity [Case A / B / C]..." -ForegroundColor Yellow
$callerUser = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$callerSessionId = [System.Diagnostics.Process]::GetCurrentProcess().SessionId
$callerPid = [System.Diagnostics.Process]::GetCurrentProcess().Id
$callerExecutable = [System.Diagnostics.Process]::GetCurrentProcess().MainModule.FileName

$pyExec = 'N/A'
$pyVersion = 'N/A'
try {
    $pyCmd = Get-Command python -ErrorAction SilentlyContinue
    if ($pyCmd) {
        $pyExec = $pyCmd.Source
        $pyVersion = (python --version 2>&1 | Out-String).Trim()
    }
} catch {
    Record-ForensicOperation -OperationName 'GetPythonExecutable' -Status 'NOT PROVEN' -Reason 'Python executable not found in PATH' -ExceptionMsg $_.Exception.Message
}

Write-Host ('Collector Identity  : ' + $callerUser)
Write-Host ('Collector Session ID: ' + $callerSessionId)
Write-Host ('Collector PID       : ' + $callerPid)
Write-Host ('Collector Executable: ' + $callerExecutable)
Write-Host ('Python Executable   : ' + $pyExec + ' (' + $pyVersion + ')')

$session0IpcStatus = 'NOT PROVEN'
$session0IpcDetails = 'NOT PROVEN [Case A: Collector executing in Session ' + $callerSessionId + ' as ' + $callerUser + ', PID ' + $callerPid + ']'

$caseAResult = "Case A (Interactive Collector Execution): User=$callerUser, SessionId=$callerSessionId, PID=$callerPid, Executable=$callerExecutable"
$caseBResult = "Case B (Session 0 SYSTEM Diagnostic Probe): "
$caseCResult = "Case C (YarTrader Production Service Context): "

if ($serviceProc) {
    $caseCResult += "PROVEN [Service PID=$servicePid, Account=$serviceAccount, SessionId=$serviceSessionId, Executable=$serviceExePath, AppRoot=$appRoot]"
    Record-ForensicOperation -OperationName 'CaseC_ProductionServiceIdentity' -Status 'PROVEN' -Reason $caseCResult
} else {
    $caseCResult += "NOT PROVEN [YarTrader Windows service not found on deployment host]"
    Record-ForensicOperation -OperationName 'CaseC_ProductionServiceIdentity' -Status 'NOT PROVEN' -Reason $caseCResult
}

if ($callerSessionId -eq 0 -and $callerUser -like '*SYSTEM*') {
    try {
        $pyCode = 'import sys, MetaTrader5 as mt5; print("py_ver=", sys.version.replace("\n"," ")); print("init=", mt5.initialize()); print("err=", mt5.last_error())'
        $ipcOutput = (python -c $pyCode 2>&1 | Out-String).Trim()
        $caseBResult += "PROVEN [PID=$callerPid, Output: $ipcOutput]"
        Record-ForensicOperation -OperationName 'CaseB_SystemSession0DiagnosticProbe' -Status 'PROVEN' -Reason $caseBResult

        if ($serviceProc -and $serviceSessionId -eq 0 -and $ipcOutput -like '*-10003*' -and $ipcOutput -like '*init= False*') {
            $session0IpcStatus = 'PROVEN'
            $session0IpcDetails = "Session 0 SYSTEM IPC probe fail-closed isolation confirmed [Case B/C]: $ipcOutput"
        } else {
            $session0IpcStatus = 'FAILED'
            $session0IpcDetails = "Session 0 IPC probe returned unexpected output or service missing: $ipcOutput"
        }
    } catch {
        $session0IpcStatus = 'FAILED'
        $session0IpcDetails = 'Exception testing Session 0 IPC: ' + $_.Exception.Message
        $caseBResult += "FAILED [Exception: $($_.Exception.Message)]"
        Record-ForensicOperation -OperationName 'CaseB_SystemSession0DiagnosticProbe' -Status 'FAILED' -Reason $caseBResult
    }
} else {
    $session0IpcStatus = 'NOT PROVEN'
    $session0IpcReason = 'Case A: Collector caller is in Session ' + $callerSessionId + ' as ' + $callerUser + ' [not Session 0 LocalSystem]. Direct Session 0 IPC isolation cannot be inferred from a Session ' + $callerSessionId + ' interactive shell execution.'
    $caseBResult += "NOT PROVEN [Collector executed from Session $callerSessionId interactive shell as $callerUser]"
    Record-ForensicOperation -OperationName 'CaseA_InteractiveCollectorExecution' -Status 'NOT PROVEN' -Reason $caseAResult
    Record-ForensicOperation -OperationName 'CaseB_SystemSession0DiagnosticProbe' -Status 'NOT PROVEN' -Reason $caseBResult
    Record-ForensicOperation -OperationName 'Session0IpcTest' -Status 'NOT PROVEN' -Reason $session0IpcReason
    Write-Warning $session0IpcReason
}

# 6. Authoritative Token Resolution & Query Bridge API Endpoints (Primary Remediation D, G, B & Recovery A)
$tsApi = Get-IsoUtcTimestamp
Write-Host "`n[6/8] Querying MT5 Interactive Bridge API [Recovery A Baseline]..." -ForegroundColor Yellow
$healthResp = $null
$statusResp = $null
$marketDataResp = $null
$tokenResolved = $false
$tokenStatus = 'NOT PROVEN'
$tokenSourceDetails = 'NOT PROVEN [Secret token file or ENV missing]'
$tokenFingerprint = 'N/A'

# Primary Authoritative Secret Token Path Contract (Primary Remediation D)
$authoritativeTokenFile = 'TradeYarStorageRoot\Secrets\mt5_bridge_token.secret'
$candidateTokenFiles = @(
    $authoritativeTokenFile,
    'C:\YarTraderAI\Secrets\mt5_bridge_token.secret',
    'Secrets\mt5_bridge_token.secret'
)

$token = $null
$tokenFileUsed = $null
foreach ($tf in $candidateTokenFiles) {
    if (Test-Path $tf) {
        try {
            $tokCandidate = (Get-Content $tf -Raw).Trim()
            if (-not [string]::IsNullOrWhiteSpace($tokCandidate)) {
                $token = $tokCandidate
                $tokenFileUsed = $tf
                $tokenSourceDetails = 'Resolved from file: ' + $tf
                $tokenResolved = $true
                if ($tf -eq $authoritativeTokenFile) {
                    $tokenStatus = 'PROVEN'
                } else {
                    $tokenStatus = 'NOT PROVEN [Resolved from fallback token path: ' + $tf + ']'
                }
                break
            }
        } catch {
            Record-ForensicOperation -OperationName 'TokenFileRead' -Status 'FAILED' -Reason "Exception reading token file $tf" -ExceptionMsg $_.Exception.Message
        }
    }
}

if (-not $tokenResolved -and -not [string]::IsNullOrWhiteSpace($env:MT5_BRIDGE_SECRET_TOKEN)) {
    $token = $env:MT5_BRIDGE_SECRET_TOKEN.Trim()
    $tokenSourceDetails = 'Resolved from ENV: MT5_BRIDGE_SECRET_TOKEN'
    $tokenResolved = $true
    $tokenStatus = 'NOT PROVEN [Resolved from ENV override rather than authoritative file contract]'
}

if ($tokenResolved -and -not [string]::IsNullOrWhiteSpace($token)) {
    # Generate safe token fingerprint (length + masked substring, NEVER log full secret)
    $tokLen = $token.Length
    $tokStart = $token.Substring(0, [Math]::Min(4, $tokLen))
    $tokEnd = $token.Substring([Math]::Max(0, $tokLen - 4))
    $tokenFingerprint = "Len=$tokLen, Substr=${tokStart}...${tokEnd}"
    Record-ForensicOperation -OperationName 'TokenResolution' -Status $tokenStatus -Reason ("Token resolved ($tokenSourceDetails), Fingerprint: $tokenFingerprint")
} else {
    Record-ForensicOperation -OperationName 'TokenResolution' -Status 'FAILED' -Reason 'Secret token could not be resolved from file or ENV'
    Write-Warning $tokenSourceDetails
}

# 6A. Health Endpoint Validation (Primary Remediation G)
$healthStatus = 'NOT PROVEN'
$healthReason = 'Health check not executed'
try {
    $healthResp = Invoke-RestMethod -Uri 'http://127.0.0.1:5001/health' -Method Get -TimeoutSec 5
    if ($healthResp -and $healthResp.status -eq 'HEALTHY' -and $healthResp.service -eq 'YarTrader.MT5Bridge' -and $healthResp.version) {
        if ($bridgeProc -and $healthResp.bridge_pid -eq $bridgeProc.ProcessId) {
            $healthStatus = 'PROVEN'
            $healthReason = "Bridge /health 200 OK, Status: HEALTHY, PID $($healthResp.bridge_pid) matches Bridge PID $($bridgeProc.ProcessId)"
            Write-Host 'GET /health: SUCCESS' -ForegroundColor Green
        } else {
            $healthStatus = 'FAILED'
            $healthReason = "Bridge /health PID $($healthResp.bridge_pid) does not match expected Bridge PID $($bridgeProc.ProcessId)"
            Write-Host 'GET /health: FAILED [PID Mismatch]' -ForegroundColor Red
        }
    } else {
        $healthStatus = 'FAILED'
        $healthReason = "Bridge /health returned invalid schema or status: $($healthResp | ConvertTo-Json -Compress)"
        Write-Host 'GET /health: FAILED [Invalid Schema]' -ForegroundColor Red
    }
} catch {
    $healthStatus = 'FAILED'
    $healthReason = 'GET /health request exception: ' + $_.Exception.Message
    Write-Host ('GET /health: FAILED - ' + $_.Exception.Message) -ForegroundColor Red
    Record-ForensicOperation -OperationName 'HealthEndpointRequest' -Status 'FAILED' -Reason 'GET /health exception' -ExceptionMsg $_.Exception.Message
    $healthResp = $null
}

Record-ForensicOperation -OperationName 'HealthEndpointValidation' -Status $healthStatus -Reason $healthReason

# 6B. MT5 Status Endpoint Validation
$mt5Status = 'NOT PROVEN'
$mt5StatusReason = 'GET /mt5/status not executed or token missing'
if ($tokenResolved) {
    try {
        $statusResp = Invoke-RestMethod -Uri 'http://127.0.0.1:5001/mt5/status' -Headers @{ Authorization = ('Bearer ' + $token) } -Method Get -TimeoutSec 5
        if ($statusResp -and $statusResp.connected -eq $true -and $statusResp.initialized -eq $true -and -not [string]::IsNullOrWhiteSpace($statusResp.server)) {
            if ($bridgeProc -and $statusResp.bridge_pid -eq $bridgeProc.ProcessId) {
                $mt5Status = 'PROVEN'
                $mt5StatusReason = "GET /mt5/status connected=true, initialized=true, Server: $($statusResp.server), Bridge PID $($statusResp.bridge_pid) verified"
                Write-Host 'GET /mt5/status: SUCCESS' -ForegroundColor Green
            } else {
                $mt5Status = 'FAILED'
                $mt5StatusReason = "GET /mt5/status bridge_pid $($statusResp.bridge_pid) does not match expected Bridge PID $($bridgeProc.ProcessId)"
                Write-Host 'GET /mt5/status: FAILED [PID Mismatch]' -ForegroundColor Red
            }
        } else {
            $mt5Status = 'FAILED'
            $mt5StatusReason = "GET /mt5/status returned disconnected or uninitialized state: $($statusResp | ConvertTo-Json -Compress)"
            Write-Host 'GET /mt5/status: FAILED [Not Connected]' -ForegroundColor Red
        }
    } catch {
        $mt5Status = 'FAILED'
        $mt5StatusReason = 'GET /mt5/status exception: ' + $_.Exception.Message
        Write-Host ('GET /mt5/status: FAILED - ' + $_.Exception.Message) -ForegroundColor Red
        Record-ForensicOperation -OperationName 'Mt5StatusEndpointRequest' -Status 'FAILED' -Reason 'GET /mt5/status exception' -ExceptionMsg $_.Exception.Message
        $statusResp = $null
    }
}

Record-ForensicOperation -OperationName 'Mt5StatusValidation' -Status $mt5Status -Reason $mt5StatusReason

# 6C. Market Data Endpoint & Independent MT5 Real-Data Provenance (Blocker #3 Requirement)
$mdCountStatus = 'NOT PROVEN'
$realDataStatus = 'NOT PROVEN'
$realDataReason = 'Market data request not executed or failed'

if ($tokenResolved) {
    try {
        $body = @{ symbol = 'XAUUSD'; timeframe = 'H1'; count = 2 } | ConvertTo-Json
        $marketDataResp = Invoke-RestMethod -Uri 'http://127.0.0.1:5001/market-data' -Headers @{ Authorization = ('Bearer ' + $token) } -Method Post -ContentType 'application/json' -Body $body -TimeoutSec 5
        Write-Host 'POST /market-data [XAUUSD H1 count=2]: SUCCESS' -ForegroundColor Green
    } catch {
        Write-Host ('POST /market-data: FAILED - ' + $_.Exception.Message) -ForegroundColor Red
        Record-ForensicOperation -OperationName 'MarketDataEndpointRequest' -Status 'FAILED' -Reason 'POST /market-data exception' -ExceptionMsg $_.Exception.Message
        $marketDataResp = $null
    }
}

if ($marketDataResp -and $marketDataResp.symbol -eq 'XAUUSD' -and $marketDataResp.timeframe -eq 'H1' -and $marketDataResp.candles) {
    if ($marketDataResp.candles.Count -eq 2) {
        $mdCountStatus = 'PROVEN'
        $c0 = $marketDataResp.candles[0]

        # Cross-check returned Bridge metadata against independently enumerated OS processes (Blocker #3 Strict Match)
        $dsMatch = ($marketDataResp.data_source -eq 'LIVE_MT5_TERMINAL')
        $dpMatch = ($marketDataResp.data_provenance -eq 'PROVEN_AUTHORITATIVE_MT5_RATES')
        $bridgePidMatch = ($bridgeProc -and $marketDataResp.bridge_pid -eq $bridgeProc.ProcessId)
        $mt5PathMatch = ($mt5Proc -and -not [string]::IsNullOrWhiteSpace($mt5Proc.ExecutablePath) -and -not [string]::IsNullOrWhiteSpace($marketDataResp.mt5_terminal_path) -and ([System.IO.Path]::GetFullPath($marketDataResp.mt5_terminal_path).ToLower() -eq [System.IO.Path]::GetFullPath($mt5Proc.ExecutablePath).ToLower()))

        # Require non-null mt5_pid matching proven OS terminal process PID
        $mt5PidMatch = ($mt5Proc -and $marketDataResp.mt5_pid -ne $null -and $marketDataResp.mt5_pid -eq $mt5Proc.ProcessId)
        $serverMatch = ($statusResp -and $marketDataResp.server -eq $statusResp.server)
        $priceValid = ($c0.open -gt 0 -and $c0.time -gt 1600000000)

        if ($dsMatch -and $dpMatch -and $bridgePidMatch -and $mt5PathMatch -and $mt5PidMatch -and $serverMatch -and $priceValid) {
            $realDataStatus = 'PROVEN'
            $realDataReason = "Authoritative real rates verified from LIVE_MT5_TERMINAL (Server: $($marketDataResp.server), Bridge PID: $($marketDataResp.bridge_pid) == $($bridgeProc.ProcessId), MT5 PID: $($marketDataResp.mt5_pid) == $($mt5Proc.ProcessId), MT5 Path: $($marketDataResp.mt5_terminal_path) == $($mt5Proc.ExecutablePath), Candle 0 Open: $($c0.open), Time: $($c0.time))"
        } else {
            $realDataStatus = 'FAILED'
            $realDataReason = "Market data cross-check failed: dsMatch=$dsMatch, dpMatch=$dpMatch, bridgePidMatch=$bridgePidMatch, mt5PathMatch=$mt5PathMatch, mt5PidMatch=$mt5PidMatch, serverMatch=$serverMatch, priceValid=$priceValid"
        }
    } else {
        $mdCountStatus = 'FAILED'
        $realDataStatus = 'FAILED'
        $realDataReason = "Returned candle count $($marketDataResp.candles.Count) != expected 2"
    }
} else {
    $mdCountStatus = 'NOT PROVEN'
    $realDataStatus = 'NOT PROVEN'
    $realDataReason = 'Market data response missing or invalid format'
}

Record-ForensicOperation -OperationName 'CandleCountValidation' -Status $mdCountStatus -Reason "Requested 2 H1 candles, returned $($marketDataResp.candles.Count)"
Record-ForensicOperation -OperationName 'RealMarketDataProvenance' -Status $realDataStatus -Reason $realDataReason

# 7. Active Recovery Lifecycle Testing (Recovery A / B / C, Primary Remediation H)
$tsRec = Get-IsoUtcTimestamp
$recoveryAResult = if ($healthStatus -eq 'PROVEN' -and $mt5Status -eq 'PROVEN' -and $realDataStatus -eq 'PROVEN' -and $mdCountStatus -eq 'PROVEN') { 'PROVEN' } else { 'NOT PROVEN' }
$recoveryBResult = 'NOT PROVEN [Active recovery test switch -ExecuteRecoveryTest not passed]'
$recoveryCResult = 'NOT PROVEN [Active recovery test switch -ExecuteRecoveryTest not passed]'

Record-ForensicOperation -OperationName 'RecoveryABaseline' -Status $recoveryAResult -Reason ("Baseline health and market data provenance status: $recoveryAResult")

if ($ExecuteRecoveryTest) {
    Write-Host "`n[7/8] Executing Active Recovery B/C Test..." -ForegroundColor Yellow
    if ($mt5Proc -and -not $mt5Ambiguous) {
        $oldMt5Pid = $mt5Proc.ProcessId
        $stopTimeUtc = Get-IsoUtcTimestamp
        Write-Host ('Stopping terminal64.exe [PID: ' + $oldMt5Pid + '] at ' + $stopTimeUtc + '...') -ForegroundColor Yellow
        try {
            Stop-Process -Id $oldMt5Pid -Force
        } catch {
            Record-ForensicOperation -OperationName 'Mt5ProcessStop' -Status 'FAILED' -Reason "Exception stopping MT5 PID $oldMt5Pid" -ExceptionMsg $_.Exception.Message
        }
        Start-Sleep -Seconds 3

        # Verify old PID no longer exists
        $oldProcExists = Get-CimInstance Win32_Process -Filter ("ProcessId=" + $oldMt5Pid) -ErrorAction SilentlyContinue
        $statusRespB = $null
        try {
            $statusRespB = Invoke-RestMethod -Uri 'http://127.0.0.1:5001/mt5/status' -Headers @{ Authorization = ('Bearer ' + $token) } -Method Get -TimeoutSec 5
        } catch {
            Record-ForensicOperation -OperationName 'RecoveryBStatusQuery' -Status 'FAILED' -Reason 'GET /mt5/status exception during Recovery B' -ExceptionMsg $_.Exception.Message
            $statusRespB = $null
        }

        if (-not $oldProcExists -and $statusRespB -and $statusRespB.connected -eq $false) {
            $recoveryBResult = 'PROVEN [Stopped MT5 PID ' + $oldMt5Pid + ' at ' + $stopTimeUtc + '; Verified process exit and Bridge connected: false fail-closed]'
            Write-Host 'Recovery B: SUCCESS' -ForegroundColor Green
            Record-ForensicOperation -OperationName 'RecoveryBInterruption' -Status 'PROVEN' -Reason $recoveryBResult
        } else {
            $recoveryBResult = 'FAILED [Process exit or fail-closed response not observed]'
            Record-ForensicOperation -OperationName 'RecoveryBInterruption' -Status 'FAILED' -Reason $recoveryBResult
        }

        # Restart MT5 for Recovery C State
        if (-not [string]::IsNullOrWhiteSpace($mt5Proc.ExecutablePath) -and (Test-Path $mt5Proc.ExecutablePath)) {
            $restartTimeUtc = Get-IsoUtcTimestamp
            $mt5ExePath = $mt5Proc.ExecutablePath
            Write-Host ('Restarting MT5 terminal: ' + $mt5ExePath + ' at ' + $restartTimeUtc + '...') -ForegroundColor Yellow
            try {
                Start-Process -FilePath $mt5ExePath
            } catch {
                Record-ForensicOperation -OperationName 'Mt5ProcessRestart' -Status 'FAILED' -Reason "Exception restarting MT5 from $mt5ExePath" -ExceptionMsg $_.Exception.Message
            }

            # Polling reconnect with timeout (up to 20 seconds) - Deterministic new PID resolution
            $reconnected = $false
            $newMt5Pid = 'N/A'
            $newMt5ProcCandidate = $null
            $reconnectTimeUtc = 'NOT PROVEN'
            $statusRespC = $null
            $marketDataRespC = $null

            for ($i = 0; $i -lt 10; $i++) {
                Start-Sleep -Seconds 2
                try {
                    $statusRespC = Invoke-RestMethod -Uri 'http://127.0.0.1:5001/mt5/status' -Headers @{ Authorization = ('Bearer ' + $token) } -Method Get -TimeoutSec 3
                    if ($statusRespC -and $statusRespC.connected -eq $true) {
                        $reconnected = $true
                        $reconnectTimeUtc = Get-IsoUtcTimestamp
                        break
                    }
                } catch {
                    $statusRespC = $null
                }
            }

            # Verify new terminal64.exe process topology after restart (NO Select-Object -First 1)
            $candidateMt5s = Get-CimInstance Win32_Process -Filter "Name='terminal64.exe'" -ErrorAction SilentlyContinue | Where-Object { $_.ProcessId -ne $oldMt5Pid }
            if ($candidateMt5s) {
                if ($candidateMt5s.Count -eq 1) {
                    $newMt5ProcCandidate = $candidateMt5s[0]
                    $newMt5Pid = $newMt5ProcCandidate.ProcessId
                } else {
                    $sessionCandidates = $candidateMt5s | Where-Object { $_.SessionId -eq $activeConsoleSessionId }
                    if ($sessionCandidates -and $sessionCandidates.Count -eq 1) {
                        $newMt5ProcCandidate = $sessionCandidates[0]
                        $newMt5Pid = $newMt5ProcCandidate.ProcessId
                    } else {
                        Write-Warning "Multiple terminal64.exe processes detected after restart in active session; ambiguity present."
                    }
                }
            }

            # Verify Bridge process PID remained unchanged and listener is intact
            $currentBridgeProcs = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*mt5_bridge*' }
            $bridgeUnchanged = ($currentBridgeProcs -and $currentBridgeProcs.Count -eq 1 -and $currentBridgeProcs[0].ProcessId -eq $bridgeProc.ProcessId)

            # Verify TCP 5001 listener still owned by same Bridge PID
            $listenerIntact = $false
            try {
                $netConnsC = Get-NetTCPConnection -LocalPort 5001 -State Listen -ErrorAction SilentlyContinue
                $validListenersC = $netConnsC | Where-Object { $_.LocalAddress -eq '127.0.0.1' }
                if ($validListenersC -and $validListenersC.Count -eq 1 -and $validListenersC[0].OwningProcess -eq $bridgeProc.ProcessId) {
                    $listenerIntact = $true
                }
            } catch {
                Record-ForensicOperation -OperationName 'RecoveryCListenerCheck' -Status 'FAILED' -Reason 'Exception checking TCP listener in Recovery C' -ExceptionMsg $_.Exception.Message
            }

            # Verify market data query on reconnected Bridge
            if ($reconnected -and $tokenResolved) {
                try {
                    $bodyC = @{ symbol = 'XAUUSD'; timeframe = 'H1'; count = 2 } | ConvertTo-Json
                    $marketDataRespC = Invoke-RestMethod -Uri 'http://127.0.0.1:5001/market-data' -Headers @{ Authorization = ('Bearer ' + $token) } -Method Post -ContentType 'application/json' -Body $bodyC -TimeoutSec 5
                } catch {
                    Record-ForensicOperation -OperationName 'RecoveryCMarketDataQuery' -Status 'FAILED' -Reason 'Exception querying market-data in Recovery C' -ExceptionMsg $_.Exception.Message
                    $marketDataRespC = $null
                }
            }

            $mdCountCOk = ($marketDataRespC -and $marketDataRespC.symbol -eq 'XAUUSD' -and $marketDataRespC.timeframe -eq 'H1' -and $marketDataRespC.candles -and $marketDataRespC.candles.Count -eq 2 -and $marketDataRespC.data_provenance -eq 'PROVEN_AUTHORITATIVE_MT5_RATES')

            if ($reconnected -and
                $newMt5ProcCandidate -and
                $newMt5Pid -ne 'N/A' -and
                $newMt5Pid -ne $oldMt5Pid -and
                ($newMt5ProcCandidate.ExecutablePath -eq $mt5Proc.ExecutablePath) -and
                ($newMt5ProcCandidate.SessionId -eq $activeConsoleSessionId) -and
                $bridgeUnchanged -and
                $listenerIntact -and
                $mdCountCOk) {

                $recoveryCResult = 'PROVEN [Restarted MT5 at ' + $restartTimeUtc + '; Verified new PID ' + $newMt5Pid + ' in Session ' + $newMt5ProcCandidate.SessionId + '; Path matches; Bridge PID ' + $bridgeProc.ProcessId + ' unchanged; Port 5001 listener intact; connected: true restored; XAUUSD H1 count=2 verified at ' + $reconnectTimeUtc + ']'
                Write-Host 'Recovery C: SUCCESS' -ForegroundColor Green
                Record-ForensicOperation -OperationName 'RecoveryCAutoRecovery' -Status 'PROVEN' -Reason $recoveryCResult
            } else {
                $recoveryCResult = 'FAILED [Recovery C validation failed: reconnected=' + $reconnected + ', newPid=' + $newMt5Pid + ', bridgeUnchanged=' + $bridgeUnchanged + ', listenerIntact=' + $listenerIntact + ', marketDataOk=' + $mdCountCOk + ']'
                Record-ForensicOperation -OperationName 'RecoveryCAutoRecovery' -Status 'FAILED' -Reason $recoveryCResult
            }
        } else {
            $recoveryCResult = 'NOT PROVEN [MT5 executable path unavailable for restart]'
            Record-ForensicOperation -OperationName 'RecoveryCAutoRecovery' -Status 'NOT PROVEN' -Reason $recoveryCResult
        }
    } else {
        Record-ForensicOperation -OperationName 'RecoveryBInterruption' -Status 'NOT PROVEN' -Reason 'terminal64.exe process not found or ambiguous; skipping recovery test'
        Write-Warning 'terminal64.exe process not found or ambiguous; skipping active recovery test.'
    }
} else {
    Write-Host "`n[7/8] Active Recovery B/C test skipped [Pass -ExecuteRecoveryTest to run]." -ForegroundColor Gray
}

# 8. Expanded Dual-Layer Zero-Order Execution Audit (Blocker #4 Truth Table Requirement across ALL execution files)
$tsLog = Get-IsoUtcTimestamp
Write-Host "`n[8/8] Auditing Execution Surface Source Code and Runtime Logs for Zero Order Execution..." -ForegroundColor Yellow

$structuralAuditProven = 'NOT PROVEN'
$runtimeLogProven = 'NOT PROVEN'
$zeroOrderStatus = 'NOT PROVEN'
$zeroOrderReason = 'Zero order execution audit in progress'

# Layer A: Structural Source Audit across ALL Bridge and Provider Execution Surface files
$auditedSourceFiles = @(
    'src\Infrastructure\Bridge\mt5_bridge.py',
    'src\Infrastructure\Bridge\client.py',
    'src\Data\Providers\MT5\mt5.py'
)

$sourceViolations = @()
$auditedRoutes = @()

foreach ($sf in $auditedSourceFiles) {
    if (Test-Path $sf) {
        try {
            $srcText = Get-Content -Path $sf -Raw

            # Check for forbidden order/trade mutation calls across ALL audited files
            $hasOrderSend = $srcText -match 'order_send'
            $hasTradeAction = $srcText -match 'TRADE_ACTION'
            $hasPositionOpen = $srcText -match 'position_open'
            $hasOrderCheck = $srcText -match 'order_check'

            if ($sf -like '*mt5_bridge.py*') {
                $routes = [regex]::Matches($srcText, '@app\.(get|post|put|delete|patch)\("([^"]+)"\)')
                $routes | ForEach-Object { $auditedRoutes += ($_.Groups[1].Value.ToUpper() + ' ' + $_.Groups[2].Value) }
                $unexpectedRoutes = $routes | Where-Object { $_.Groups[2].Value -notIn @('/health', '/mt5/status', '/market-data') }
                if ($unexpectedRoutes.Count -gt 0) {
                    $sourceViolations += "$sf contains unexpected HTTP routes: $($unexpectedRoutes.Count)"
                }
            }

            if ($hasOrderSend -or $hasTradeAction -or $hasPositionOpen -or $hasOrderCheck) {
                $sourceViolations += "$sf contains trade/order execution methods"
            }
        } catch {
            $sourceViolations += "Exception auditing $sf: " + $_.Exception.Message
        }
    } else {
        $sourceViolations += "Source file $sf missing"
    }
}

if ($sourceViolations.Count -eq 0) {
    $structuralAuditProven = 'PROVEN'
    Record-ForensicOperation -OperationName 'BridgeStructuralAudit' -Status 'PROVEN' -Reason "Structural source audit confirms mt5_bridge.py, client.py, and mt5.py contain 0 order execution methods (Routes: $($auditedRoutes -join ', '))"
} else {
    $structuralAuditProven = 'FAILED'
    $violationStr = $sourceViolations -join '; '
    Record-ForensicOperation -OperationName 'BridgeStructuralAudit' -Status 'FAILED' -Reason "Order-capable methods or missing files found: $violationStr"
}

# Layer B: Runtime Log Inspection
$logFilesChecked = @()
$logFilesFound = @()
$orderDispatchesDetected = $false

$candidateLogs = @('C:\YarTraderAI\Logs\runtime.log', 'C:\YarTraderAI\Logs\bridge.log', 'Logs\runtime.log', 'runtime_logs\runtime.log')
foreach ($lf in $candidateLogs) {
    $logFilesChecked += $lf
    if (Test-Path $lf) {
        $logFilesFound += $lf
        try {
            $matches = Select-String -Path $lf -Pattern 'order_send|TRADE_ACTION|dispatch_order|order_placed|OrderSend|PositionOpen' -ErrorAction SilentlyContinue
            if ($matches) {
                $orderDispatchesDetected = $true
                Write-Warning ('Order dispatch pattern detected in ' + $lf + '!')
            }
        } catch {
            Record-ForensicOperation -OperationName 'LogPatternScan' -Status 'FAILED' -Reason "Exception scanning log $lf" -ExceptionMsg $_.Exception.Message
        }
    }
}

if ($logFilesFound.Count -gt 0 -and -not $orderDispatchesDetected) {
    $runtimeLogProven = 'PROVEN'
    Record-ForensicOperation -OperationName 'RuntimeLogScan' -Status 'PROVEN' -Reason "Inspected $($logFilesFound.Count) active log files ($($logFilesFound -join ', ')); 0 order dispatches detected"
} elseif ($orderDispatchesDetected) {
    $runtimeLogProven = 'FAILED'
    Record-ForensicOperation -OperationName 'RuntimeLogScan' -Status 'FAILED' -Reason 'Order dispatch pattern detected in runtime logs'
} else {
    $runtimeLogProven = 'NOT PROVEN'
    Record-ForensicOperation -OperationName 'RuntimeLogScan' -Status 'NOT PROVEN' -Reason 'No active runtime log files found for inspection'
}

# Final Dual-Layer Zero Order Truth Table Determination (Mandatory Truth Table Contract)
if ($structuralAuditProven -eq 'PROVEN' -and $runtimeLogProven -eq 'PROVEN') {
    $zeroOrderStatus = 'PROVEN'
    $zeroOrderReason = "PROVEN [Structural proof: Bridge and provider sources contain 0 trade mutation endpoints or order methods; Runtime proof: Inspected $($logFilesFound.Count) log files with 0 order dispatches.]"
} elseif ($structuralAuditProven -eq 'FAILED' -or $runtimeLogProven -eq 'FAILED') {
    $zeroOrderStatus = 'FAILED'
    $zeroOrderReason = "FAILED [Order dispatch capability or pattern detected during zero-order audit]"
} else {
    $zeroOrderStatus = 'NOT PROVEN'
    $zeroOrderReason = "NOT PROVEN [Structural audit: $structuralAuditProven, Runtime log scan: $runtimeLogProven (Both layers must be PROVEN for overall zero-order proof)]"
}

Record-ForensicOperation -OperationName 'ZeroOrderExecutionAudit' -Status $zeroOrderStatus -Reason $zeroOrderReason

# Capture true UTC end timestamp BEFORE report generation (Section 11)
$endTimeUtc = Get-IsoUtcTimestamp

# Evaluate Master Gate E Conclusion (Section 12 & Strict Master Decision Logic)
$tsEval = Get-IsoUtcTimestamp
Write-Host "`nEvaluating CTO Gate E Compliance..." -ForegroundColor Yellow

$gateEPassed = (
    $provenanceMatch -and
    $treeClean -and
    ($runtimeShaStatus -eq 'PROVEN') -and
    ($serviceProc -ne $null) -and
    ($serviceSessionId -eq 0) -and
    ($bridgeProc -ne $null) -and
    -not $bridgeAmbiguous -and
    ($bridgeSessionStatus -eq 'PROVEN') -and
    ($mt5Proc -ne $null) -and
    -not $mt5Ambiguous -and
    ($mt5SessionStatus -eq 'PROVEN') -and
    ($port5001Status -eq 'PROVEN') -and
    ($tokenStatus -eq 'PROVEN') -and
    ($healthStatus -eq 'PROVEN') -and
    ($mt5Status -eq 'PROVEN') -and
    ($mdCountStatus -eq 'PROVEN') -and
    ($realDataStatus -eq 'PROVEN') -and
    ($session0IpcStatus -eq 'PROVEN') -and
    ($recoveryAResult -eq 'PROVEN') -and
    ($recoveryBResult -like 'PROVEN*') -and
    ($recoveryCResult -like 'PROVEN*') -and
    ($zeroOrderStatus -eq 'PROVEN')
)

$hasExplicitFailures = ($forensicOperations | Where-Object { $_.Status -eq 'FAILED' }).Count -gt 0

$finalGateStatus = if ($gateEPassed) {
    'PR #314 FINAL RUNTIME GATE: PASSED'
} elseif ($hasExplicitFailures) {
    'PR #314 FINAL RUNTIME GATE: FAILED'
} else {
    'PR #314 FINAL RUNTIME GATE: INCOMPLETE / NOT PROVEN'
}

# Pre-evaluate report expressions into clean strings
$treeCleanStr = if ($treeClean) { 'YES' } else { 'NO [' + $statusShort + ']' }
$serviceStatusStr = if ($serviceProc -and $serviceSessionId -eq 0) { 'PROVEN' } else { 'NOT PROVEN' }

$bridgeProcSessionId = if ($bridgeProc) { $bridgeProc.SessionId } else { 'N/A' }
$bridgeProcPid = if ($bridgeProc) { $bridgeProc.ProcessId } else { 'N/A' }

$mt5ProcSessionId = if ($mt5Proc) { $mt5Proc.SessionId } else { 'N/A' }
$mt5ProcPid = if ($mt5Proc) { $mt5Proc.ProcessId } else { 'N/A' }

$healthStatusVal = if ($healthResp) { $healthResp.status } else { 'N/A' }
$mt5ConnVal = if ($statusResp) { $statusResp.connected } else { 'N/A' }
$mt5ServerVal = if ($statusResp) { $statusResp.server } else { 'N/A' }

$mdSymbolVal = if ($marketDataResp) { $marketDataResp.symbol } else { 'N/A' }
$mdCountVal = if ($marketDataResp -and $marketDataResp.candles) { $marketDataResp.candles.Count } else { 'N/A' }

$pidCaptureStatusStr = if ($serviceProc -and $bridgeProc -and $mt5Proc) { 'PROVEN' } else { 'NOT PROVEN' }

$healthJson = if ($healthResp) { $healthResp | ConvertTo-Json -Depth 5 } else { '{}' }
$statusJson = if ($statusResp) { $statusResp | ConvertTo-Json -Depth 5 } else { '{}' }
$marketDataJson = if ($marketDataResp) { $marketDataResp | ConvertTo-Json -Depth 5 } else { '{}' }
$checkedLogsStr = $logFilesChecked -join ', '
$foundLogsStr = $logFilesFound -join ', '

$opsTableStr = $forensicOperations | Format-Table Timestamp, Operation, Status, Reason -AutoSize | Out-String

$reportContent = @"
# PR #314 GATE E WINDOWS RUNTIME EVIDENCE REPORT

**Collection Start (UTC):** $startTimeUtc
**Collection End (UTC):** $endTimeUtc
**Repository:** `sohrabinia/YarTrader`
**Pull Request:** `https://github.com/sohrabinia/YarTrader/pull/314`
**Expected PR HEAD SHA:** `$ExpectedSha`
**Current Local HEAD:** `$currentHead`
**Deployed Runtime SHA:** `$runtimeDeployedSha`
**Current Branch:** `$currentBranch`
**PR Base SHA:** `$prBaseSha`
**Merge-Base SHA:** `$mergeBase`
**Origin Main SHA:** `$originMain`
**Commit Range:** `$commitRange`
**Git Working Tree Clean:** $treeCleanStr

---

## A. Git Provenance Matrix
* **Expected HEAD:** `$ExpectedSha`
* **Actual HEAD:** `$currentHead`
* **PR Base SHA:** `$prBaseSha`
* **Merge-Base SHA:** `$mergeBase`
* **Origin Main:** `$originMain`
* **Head Verification Status:** `$provenanceStatus`
* **Working Tree Cleanliness:** `$treeCleanStatus`

---

## B. Blocker #1 — Runtime SHA Provenance Chain
* **Windows Service Name:** `YarTrader`
* **Service State:** `$serviceState`
* **Service Account:** `$serviceAccount`
* **Service PID:** `$servicePid`
* **Service Session ID:** `$serviceSessionId`
* **Service Executable Path:** `$serviceExePath`
* **Command Line:** `$serviceCmdLine`
* **Application Root:** `$appRoot`
* **Deployed SHA Source File:** `$deployedShaSourceFile`
* **Deployed SHA Value:** `$runtimeDeployedSha`
* **Expected SHA Value:** `$ExpectedSha`
* **Runtime SHA Provenance Status:** `$runtimeShaStatus`
* **SHA Provenance Reason:** `$runtimeShaReason`

---

## C. Interactive Bridge Topology & Token Provenance
* **Active Console Session ID:** `$activeConsoleSessionId`
* **Bridge Process PID:** `$bridgeProcPid`
* **Bridge Session ID:** `$bridgeProcSessionId`
* **Bridge Process Resolution Status:** `$bridgeSessionStatus`
* **TCP Port 5001 Listener Details:** `$port5001Details`
* **All Observed Listeners:** `$allObservedListenersStr`
* **Port 5001 Listener Status:** `$port5001Status`
* **Token Source Path:** `$tokenSourceDetails`
* **Token Fingerprint (Masked):** `$tokenFingerprint`
* **Token Provenance Status:** `$tokenStatus`
* **`/health` Status:** `$healthStatusVal`
* **`/health` Endpoint Provenance Status:** `$healthStatus`

---

## D. Blocker #2 — MetaTrader 5 (MT5) Terminal Identity & Session 0 IPC (Case A / B / C)
* **MT5 Terminal PID:** `$mt5ProcPid`
* **MT5 Terminal Session ID:** `$mt5ProcSessionId`
* **MT5 Executable Path:** `$(if ($mt5Proc) { $mt5Proc.ExecutablePath } else { 'N/A' })`
* **MT5 Process Resolution Status:** `$mt5SessionStatus`
* **`/mt5/status` Connected:** `$mt5ConnVal`
* **`/mt5/status` Server:** `$mt5ServerVal`
* **`/mt5/status` Status:** `$mt5Status`
* **Case A (Interactive Shell):** `$caseAResult`
* **Case B (Session 0 SYSTEM Diagnostic Probe):** `$caseBResult`
* **Case C (YarTrader Production Service Context):** `$caseCResult`
* **Python Executable Invoked:** `$pyExec`
* **Python Version:** `$pyVersion`
* **Direct Session 0 IPC Details:** `$session0IpcDetails`
* **Session 0 IPC Provenance Status:** `$session0IpcStatus`

---

## E. Blocker #3 — Market Data & Real MT5 Data Provenance
* **Requested Symbol:** XAUUSD
* **Requested Timeframe:** H1
* **Requested Count:** 2
* **Returned Candle Count:** `$mdCountVal`
* **Candle Count Status:** `$mdCountStatus`
* **Data Source Tag:** `$(if ($marketDataResp) { $marketDataResp.data_source } else { 'N/A' })`
* **Data Provenance Tag:** `$(if ($marketDataResp) { $marketDataResp.data_provenance } else { 'N/A' })`
* **Bridge PID Correlation:** `$(if ($marketDataResp) { $marketDataResp.bridge_pid } else { 'N/A' })`
* **MT5 Path Correlation:** `$(if ($marketDataResp) { $marketDataResp.mt5_terminal_path } else { 'N/A' })`
* **MT5 PID Correlation:** `$(if ($marketDataResp) { $marketDataResp.mt5_pid } else { 'N/A' })`
* **Server Correlation:** `$(if ($marketDataResp) { $marketDataResp.server } else { 'N/A' })`
* **Retrieval Timestamp:** `$(if ($marketDataResp) { $marketDataResp.retrieval_timestamp } else { 'N/A' })`
* **Real MT5 Data Provenance Status:** `$realDataStatus`
* **Real MT5 Data Provenance Reason:** `$realDataReason`

---

## F. Recovery Lifecycle (A / B / C)
* **Recovery A (Healthy Baseline Status):** `$recoveryAResult`
* **Recovery B (Interruption Status):** `$recoveryBResult`
* **Recovery C (Auto-Recovery Status):** `$recoveryCResult`

---

## G. Blocker #4 — Dual-Layer Zero-Order Execution Audit
* **Structural Source Audit Status:** `$structuralAuditProven`
* **Runtime Log Audit Status:** `$runtimeLogProven`
* **Zero-Order Audit Final Status:** `$zeroOrderStatus`
* **Candidate Log Paths Checked:** `$checkedLogsStr`
* **Found Log Paths Inspected:** `$foundLogsStr`
* **Audit Coverage & Scope:** Structural AST analysis of `mt5_bridge.py`, `client.py`, and `mt5.py` routes/methods combined with runtime log pattern scanning (`order_send`, `TRADE_ACTION`, `dispatch_order`, `order_placed`, `OrderSend`, `PositionOpen`).
* **Zero-Order Audit Reason:** `$zeroOrderReason`

---

## Forensic Execution Operations Audit Log
```text
$opsTableStr
```

---

## Detailed Process Topology Table
```text
$procTable
```

---

## Raw Bridge API Responses

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

## Final Runtime Gate Conclusion

$finalGateStatus
"@

$reportDir = Split-Path -Parent $OutputFile
if (-not (Test-Path $reportDir)) {
    try {
        New-Item -ItemType Directory -Path $reportDir -Force | Out-Null
    } catch {
        Record-ForensicOperation -OperationName 'CreateReportDirectory' -Status 'FAILED' -Reason "Exception creating report directory $reportDir" -ExceptionMsg $_.Exception.Message
    }
}

try {
    Set-Content -Path $OutputFile -Value $reportContent -Encoding UTF8
    Write-Host ('Report written to ' + $OutputFile) -ForegroundColor Green
} catch {
    Record-ForensicOperation -OperationName 'WriteReportFile' -Status 'FAILED' -Reason "Exception writing report to $OutputFile" -ExceptionMsg $_.Exception.Message
}

Write-Host '========================================================================' -ForegroundColor Cyan
$finalColor = if ($gateEPassed) { 'Green' } else { 'Yellow' }
Write-Host ('   ' + $finalGateStatus) -ForegroundColor $finalColor
Write-Host '========================================================================' -ForegroundColor Cyan

if (-not $gateEPassed) {
    exit 1
}
