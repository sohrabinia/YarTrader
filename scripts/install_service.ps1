# Install TradeYar-AI Windows Service Script
# This script installs and registers TradeYar-AI as a Windows Service running 24/7 on Windows Server using the local virtual environment Python.

$ServiceName = "TradeYar-AI"
$ServiceDisplayName = "TradeYar AI Production Runtime Service"
$ServiceDescription = "Coordinates the 24/7 background AI runtime, MT5 connector, intelligence, and shadow execution."

# 1. Resolve local virtual environment Python
$VenvPython = "$PSScriptRoot\..\.venv\Scripts\python.exe"
$GlobalPython = "C:\Program Files\Python312\python.exe"
$ScriptPath = "$PSScriptRoot\..\app\workers\service.py"
$WorkDir = "$PSScriptRoot\.."

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "Installing TradeYar-AI Windows Service..." -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# Check Administrator Privileges
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Error "Error: This script must be run as an Administrator!"
    Exit 1
}

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
    # 1st Failure: Restart Service (5s delay -> 5000ms)
    # 2nd Failure: Restart Service (10s delay -> 10000ms)
    # Subsequent Failures: Restart Service (30s delay -> 30000ms)
    sc.exe failure $ServiceName reset= 86400 actions= restart/5000/restart/10000/restart/30000 | Out-Null

    Write-Host "Successfully registered TradeYar-AI Windows Service natively!" -ForegroundColor Green
}

Write-Host "To start the service, run: .\start_service.ps1" -ForegroundColor Green
