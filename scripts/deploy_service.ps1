# PowerShell NSSM Service Deployment Script for TradeYar-AI
# Coordinates registering TradeYar-AI as a background 24/7 Windows Service using NSSM.
# Enforces delayed auto-start, explicit working directories, log rotation, and SRE compliance.

$ServiceName = "TradeYar-AI"
$ServiceDisplayName = "TradeYar AI Production Runtime Service"
$ServiceDescription = "Coordinates the 24/7 background AI runtime, MT5 connector, intelligence, and shadow execution."

# 1. Configuration & Directories
$TargetWorkDir = "C:\Projects\TradeYar_AI"
$VenvPython = "$TargetWorkDir\.venv\Scripts\python.exe"
$ScriptPath = "$TargetWorkDir\app\workers\service.py"

$LogDir = "$TargetWorkDir\logs\service"
$LogStdout = "$LogDir\service_stdout.log"
$LogStderr = "$LogDir\service_stderr.log"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "Registering TradeYar-AI Windows Service via NSSM..." -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# Check Administrator Privileges
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Error "Error: This deployment script must be executed with Administrator privileges!"
    Exit 1
}

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

    # 3. Delayed Auto-Start (Automatic delayed startup to let basic Windows/Network services boot first)
    Write-Host "Enforcing Automatic (Delayed Start) startup type..." -ForegroundColor Yellow
    & $nssm set $ServiceName Start SERVICE_DELAYED_AUTO_START

    # 4. Stdout and Stderr Redirection
    Write-Host "Redirecting service streams..." -ForegroundColor Yellow
    & $nssm set $ServiceName AppStdout "$LogStdout"
    & $nssm set $ServiceName AppStderr "$LogStderr"

    # 5. Log Rotation Configuration (Rotate logs dynamically once file exceeds 10MB)
    Write-Host "Configuring automatic Log Rotation (10MB)..." -ForegroundColor Yellow
    & $nssm set $ServiceName AppRotateFiles 1
    & $nssm set $ServiceName AppRotateOnline 1
    & $nssm set $ServiceName AppRotateBytes 10485760

    # 6. Automatic Recovery Policy
    & $nssm set $ServiceName AppThrottle 1500
    & $nssm set $ServiceName AppExit Default Restart

    Write-Host "Successfully registered and hardened TradeYar-AI service via NSSM!" -ForegroundColor Green
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

    Write-Host "Successfully registered TradeYar-AI service natively using sc.exe fallback!" -ForegroundColor Green
}

Write-Host "To manage the service, use start_service.ps1 and stop_service.ps1." -ForegroundColor Green
