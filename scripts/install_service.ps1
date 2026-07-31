# Install TradeYar-AI Windows Service Script
# This script installs and registers TradeYar-AI as a Windows Service running 24/7 on Windows Server.

$ServiceName = "TradeYar-AI"
$ServiceDisplayName = "TradeYar AI Production Runtime Service"
$ServiceDescription = "Coordinates the 24/7 background AI runtime, MT5 connector, intelligence, and shadow execution."
$PythonPath = "C:\Program Files\Python312\python.exe"
$ScriptPath = "$PSScriptRoot\..\app\workers\service.py"
$WorkDir = "$PSScriptRoot\.."

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "Installing TradeYar-AI Windows Service..." -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Check Administrator Privileges
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Error "Error: This script must be run as an Administrator!"
    Exit 1
}

# 2. Check Python installation
if (-not (Test-Path $PythonPath)) {
    # Attempt to locate python via PATH
    $PythonPath = (Get-Command python.exe -ErrorAction SilentlyContinue).Source
    if (-not $PythonPath) {
        Write-Error "Error: python.exe was not found. Please install Python 3.12 or specify PythonPath."
        Exit 1
    }
}

Write-Host "Using Python path: $PythonPath" -ForegroundColor Yellow
Write-Host "Using Script path: $ScriptPath" -ForegroundColor Yellow
Write-Host "Working Directory: $WorkDir" -ForegroundColor Yellow

# 3. Check if service already exists
$existingService = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
if ($existingService) {
    Write-Host "Service '$ServiceName' already exists. Re-installing..." -ForegroundColor Yellow
    Stop-Service -Name $ServiceName -Force -ErrorAction SilentlyContinue
    sc.exe delete $ServiceName | Out-Null
    Start-Sleep -Seconds 2
}

# 4. Try installing using sc.exe (Native Windows Service Controller)
$BinPath = """$PythonPath"" ""$ScriptPath"" start"
Write-Host "Registering service via sc.exe..." -ForegroundColor Yellow

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
    sc.exe description $ServiceName "$ServiceDescription" | Out-Null
    sc.exe failure $ServiceName reset= 86400 actions= restart/60000/restart/120000/restart/300000 | Out-Null
    Write-Host "Successfully registered TradeYar-AI Windows Service natively!" -ForegroundColor Green
}

Write-Host "To start the service, run: .\start_service.ps1" -ForegroundColor Green
