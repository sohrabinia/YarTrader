# Install YarTrader Windows Service Script
# This script installs and registers YarTrader as a Windows Service running 24/7 on Windows Server using the local virtual environment Python.

param(
    [string]$OperatorOwnerId = "owner_sohrab",
    [string]$YarOperatorRuntimeUrl = "http://127.0.0.1:3000",
    [string]$OperatorOwnerToken = $env:OPERATOR_OWNER_TOKEN
)

$ServiceName = "YarTrader"
$ServiceDisplayName = "YarTrader Production Runtime Service"
$ServiceDescription = "Coordinates the 24/7 background AI runtime, MT5 connector, intelligence, and shadow execution."

# 1. Resolve local virtual environment Python
$VenvPython = "$PSScriptRoot\..\.venv\Scripts\python.exe"
$GlobalPython = "C:\Program Files\Python312\python.exe"
$ScriptPath = "$PSScriptRoot\..\app\workers\service.py"
$WorkDir = "$PSScriptRoot\.."

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "Installing YarTrader Windows Service..." -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# Check Administrator Privileges
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Error "Error: This script must be run as an Administrator!"
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

# Resolve target Python path
if (Test-Path $VenvPython) {
    $PythonPath = Resolve-Path $VenvPython
    Write-Host "Detected Local Virtual Environment Python!" -ForegroundColor Green
} else {
    Write-Host "Warning: Virtual environment Python at .venv\Scripts\python.exe not found." -ForegroundColor Yellow
    # Fallback to global Python or PATH python
    $PythonPath = $GlobalPython
    if (-not (Test-Path $PythonPath)) {
        $PythonPath = (Get-Command python.exe -ErrorAction SilentlyContinue).Source
    }
    if (-not $PythonPath) {
        Write-Error "Error: python.exe was not found. Please install Python 3.12 or specify PythonPath."
        Exit 1
    }
}

Write-Host "Using Python executable: $PythonPath" -ForegroundColor Yellow
Write-Host "Using Service Script path: $ScriptPath" -ForegroundColor Yellow
Write-Host "Working Directory: $WorkDir" -ForegroundColor Yellow

# Check if service already exists
$existingService = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
if ($existingService) {
    Write-Host "Service '$ServiceName' already exists. Re-installing..." -ForegroundColor Yellow
    Stop-Service -Name $ServiceName -Force -ErrorAction SilentlyContinue
    sc.exe delete $ServiceName | Out-Null
    Start-Sleep -Seconds 2
}

# Register service using sc.exe (Native Windows Service Controller)
# SCM runs Python with service script path argument
$BinPath = """$PythonPath"" ""$ScriptPath"""
Write-Host "Registering service natively via sc.exe..." -ForegroundColor Yellow

sc.exe create $ServiceName binPath= $BinPath start= auto DisplayName= "$ServiceDisplayName" | Out-Null

if ($LASTEXITCODE -ne 0) {
    Write-Host "Native sc.exe creation failed. Checking for NSSM..." -ForegroundColor Yellow
    $nssm = (Get-Command nssm.exe -ErrorAction SilentlyContinue).Source
    if ($nssm) {
        & $nssm install $ServiceName "$PythonPath" """$ScriptPath"""
        & $nssm set $ServiceName AppDirectory "$WorkDir"
        & $nssm set $ServiceName Description "$ServiceDescription"
        & $nssm set $ServiceName Start SERVICE_AUTO_START
        & $nssm set $ServiceName AppEnvironmentExtra "OPERATOR_OWNER_ID=$OperatorOwnerId" "YAROPERATOR_RUNTIME_URL=$YarOperatorRuntimeUrl" "OPERATOR_OWNER_TOKEN=$OperatorOwnerToken"
        Write-Host "Successfully registered via NSSM!" -ForegroundColor Green
    } else {
        Write-Error "Failed to install service natively and nssm.exe was not found in PATH."
        Write-Host "Please download NSSM and place it in your system PATH, or ensure win32service is installed." -ForegroundColor Yellow
        Exit 1
    }
} else {
    # Set service description natively
    sc.exe description $ServiceName "$ServiceDescription" | Out-Null

    # Configure recovery options: Automatic restart on failure
    sc.exe failure $ServiceName reset= 86400 actions= restart/5000/restart/10000/restart/30000 | Out-Null

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

    Write-Host "Successfully registered YarTrader Windows Service natively!" -ForegroundColor Green
}

Write-Host "To start the service, run: .\start_service.ps1" -ForegroundColor Green
