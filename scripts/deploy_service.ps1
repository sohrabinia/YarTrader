# PowerShell NSSM Service Deployment Script for YarTrader
# Coordinates registering YarTrader as a background 24/7 Windows Service using NSSM.
# Enforces delayed auto-start, explicit working directories, log rotation, and SRE compliance.

param(
    [string]$OperatorOwnerId = "owner_sohrab",
    [string]$YarOperatorRuntimeUrl = "http://127.0.0.1:3000",
    [string]$OperatorOwnerToken = $env:OPERATOR_OWNER_TOKEN
)

$ServiceName = "YarTrader"
$ServiceDisplayName = "YarTrader Production Runtime Service"
$ServiceDescription = "Coordinates the 24/7 background AI runtime, MT5 connector, intelligence, and shadow execution."

# 1. Configuration & Directories
$TargetWorkDir = "C:\Projects\YarTrader"
$VenvPython = "$TargetWorkDir\.venv\Scripts\python.exe"
$ScriptPath = "$TargetWorkDir\app\workers\service.py"

$LogDir = "$TargetWorkDir\logs\service"
$LogStdout = "$LogDir\service_stdout.log"
$LogStderr = "$LogDir\service_stderr.log"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "Registering YarTrader Windows Service via NSSM..." -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# Check Administrator Privileges
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Error "Error: This deployment script must be executed with Administrator privileges!"
    Exit 1
}

# 2. Operator Credentials & Runtime Validation
if ([string]::IsNullOrWhiteSpace($OperatorOwnerId)) {
    Write-Error "Deployment Failed: OPERATOR_OWNER_ID is required and cannot be empty!"
    Exit 1
}

if ([string]::IsNullOrWhiteSpace($YarOperatorRuntimeUrl)) {
    Write-Error "Deployment Failed: YAROPERATOR_RUNTIME_URL is required and cannot be empty!"
    Exit 1
}

# Enforce internal endpoint rule for YarOperator URL
if (-not ($YarOperatorRuntimeUrl.StartsWith("http://127.0.0.1") -or $YarOperatorRuntimeUrl.StartsWith("http://localhost"))) {
    Write-Error "Deployment Failed: YAROPERATOR_RUNTIME_URL must point to an internal local endpoint (e.g. http://127.0.0.1:3000) for security isolation!"
    Exit 1
}

if ([string]::IsNullOrWhiteSpace($OperatorOwnerToken)) {
    Write-Error "Deployment Failed: OPERATOR_OWNER_TOKEN must be explicitly supplied via parameter (-OperatorOwnerToken) or environment variable (\$env:OPERATOR_OWNER_TOKEN)!"
    Exit 1
}

Write-Host "Service Environment Validation Check:" -ForegroundColor Green
Write-Host "  OPERATOR_OWNER_ID: configured" -ForegroundColor Green
Write-Host "  YAROPERATOR_RUNTIME_URL: configured" -ForegroundColor Green
Write-Host "  OPERATOR_OWNER_TOKEN: configured" -ForegroundColor Green

# Ensure Logs Subdirectory Exists
if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
}

# Resolve target Python path
if (Test-Path $VenvPython) {
    $PythonPath = $VenvPython
    Write-Host "Located local virtual environment Python: $PythonPath" -ForegroundColor Green
} else {
    Write-Host "Warning: Virtual environment at $VenvPython was not found." -ForegroundColor Yellow
    $PythonPath = (Get-Command python.exe -ErrorAction SilentlyContinue).Source
    if (-not $PythonPath) {
        Write-Error "Error: python.exe was not found in the path. Please install Python 3.12 or populate .venv."
        Exit 1
    }
}

# Find NSSM.exe
$nssm = (Get-Command nssm.exe -ErrorAction SilentlyContinue).Source
if (-not $nssm) {
    # Check common download or utility paths
    $nssm_default = "C:\Program Files\nssm\nssm.exe"
    if (Test-Path $nssm_default) {
        $nssm = $nssm_default
    } else {
        Write-Host "NSSM is not registered in system PATH or Program Files." -ForegroundColor Yellow
        Write-Host "Please ensure 'nssm.exe' is available in your PATH before running this script." -ForegroundColor Yellow
        Write-Host "Attempting native sc.exe fallback configuration..." -ForegroundColor Yellow
    }
}

if ($nssm) {
    Write-Host "Using NSSM executable: $nssm" -ForegroundColor Yellow

    # Stop and remove existing service if present
    $existingService = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
    if ($existingService) {
        Write-Host "Stopping and removing existing '$ServiceName' service..." -ForegroundColor Yellow
        Stop-Service -Name $ServiceName -Force -ErrorAction SilentlyContinue
        & $nssm remove $ServiceName confirm
        Start-Sleep -Seconds 2
    }

    # Register Service via NSSM
    Write-Host "Registering service '$ServiceName' via NSSM..." -ForegroundColor Yellow
    & $nssm install $ServiceName "$PythonPath" """$ScriptPath"""

    # 1. Explicit Working Directory
    Write-Host "Setting explicit AppDirectory..." -ForegroundColor Yellow
    & $nssm set $ServiceName AppDirectory "$TargetWorkDir"

    # 2. Metadata & Description
    & $nssm set $ServiceName DisplayName "$ServiceDisplayName"
    & $nssm set $ServiceName Description "$ServiceDescription"

    # 3. Environment Variables (Operator Credentials & Config)
    Write-Host "Configuring service environment variables..." -ForegroundColor Yellow
    & $nssm set $ServiceName AppEnvironmentExtra "OPERATOR_OWNER_ID=$OperatorOwnerId" "YAROPERATOR_RUNTIME_URL=$YarOperatorRuntimeUrl" "OPERATOR_OWNER_TOKEN=$OperatorOwnerToken"

    # 4. Delayed Auto-Start (Automatic delayed startup to let basic Windows/Network services boot first)
    Write-Host "Enforcing Automatic (Delayed Start) startup type..." -ForegroundColor Yellow
    & $nssm set $ServiceName Start SERVICE_DELAYED_AUTO_START

    # 5. Stdout and Stderr Redirection
    Write-Host "Redirecting service streams..." -ForegroundColor Yellow
    & $nssm set $ServiceName AppStdout "$LogStdout"
    & $nssm set $ServiceName AppStderr "$LogStderr"

    # 6. Log Rotation Configuration (Rotate logs dynamically once file exceeds 10MB)
    Write-Host "Configuring automatic Log Rotation (10MB)..." -ForegroundColor Yellow
    & $nssm set $ServiceName AppRotateFiles 1
    & $nssm set $ServiceName AppRotateOnline 1
    & $nssm set $ServiceName AppRotateBytes 10485760

    # 7. Automatic Recovery Policy
    & $nssm set $ServiceName AppThrottle 1500
    & $nssm set $ServiceName AppExit Default Restart

    Write-Host "Successfully registered and hardened YarTrader service via NSSM!" -ForegroundColor Green
    Write-Host "Log Rotation limit set to 10MB." -ForegroundColor Green
    Write-Host "Working directory locked to: $TargetWorkDir" -ForegroundColor Green
} else {
    # sc.exe fallback
    $existingService = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
    if ($existingService) {
        Stop-Service -Name $ServiceName -Force -ErrorAction SilentlyContinue
        sc.exe delete $ServiceName | Out-Null
        Start-Sleep -Seconds 2
    }

    Write-Host "Registering service via native sc.exe..." -ForegroundColor Yellow
    $BinPath = """$PythonPath"" ""$ScriptPath"""
    sc.exe create $ServiceName binPath= $BinPath start= delayed-auto DisplayName= "$ServiceDisplayName" | Out-Null
    sc.exe description $ServiceName "$ServiceDescription" | Out-Null
    sc.exe failure $ServiceName reset= 86400 actions= restart/60000/restart/60000/restart/60000 | Out-Null

    # Register environment variables via SCM Registry Key
    $RegPath = "HKLM:\SYSTEM\CurrentControlSet\Services\$ServiceName"
    if (Test-Path $RegPath) {
        $EnvMultiString = @(
            "OPERATOR_OWNER_ID=$OperatorOwnerId",
            "YAROPERATOR_RUNTIME_URL=$YarOperatorRuntimeUrl",
            "OPERATOR_OWNER_TOKEN=$OperatorOwnerToken"
        )
        Set-ItemProperty -Path $RegPath -Name "Environment" -Value $EnvMultiString -Type MultiString -ErrorAction SilentlyContinue
    }

    Write-Host "Successfully registered YarTrader service natively using sc.exe fallback!" -ForegroundColor Green
}

Write-Host "To manage the service, use start_service.ps1 and stop_service.ps1." -ForegroundColor Green
