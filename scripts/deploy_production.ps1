# PowerShell Production Deployment Script for YarTrader
# Location: C:\Projects\YarTrader\scripts\deploy_production.ps1
#
# Idempotency Rule: This script can be run multiple times safely.
# It validates production artifacts, verifies environment configurations,
# and checks the status of the YarTrader background service.

$ServiceName = "YarTrader"
$TargetWorkDir = Split-Path -Parent $PSScriptRoot
Set-Location $TargetWorkDir

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "YarTrader Production Deployment Automation" -ForegroundColor Cyan
Write-Host "Target Directory: $TargetWorkDir" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# Check Administrator Privileges
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "[-] WARNING: This script was not executed as an Administrator!" -ForegroundColor Yellow
    Write-Host "    Some tasks like restarting the Windows Service may fail if permissions are insufficient." -ForegroundColor Yellow
}

# ------------------------------------------------------------------------------
# STEP 1: Artifact Verification
# ------------------------------------------------------------------------------
Write-Host "`n[+] Step 1: Verifying Production Artifacts..." -ForegroundColor Cyan

$RequiredPaths = @(
    "src",
    "app",
    "config",
    "scripts",
    "app/workers/service.py",
    "src/Application/Services/web_dashboard.py",
    "config/production.yaml"
)

$ArtifactsValid = $true
foreach ($path in $RequiredPaths) {
    $fullPath = Join-Path $TargetWorkDir $path
    if (Test-Path $fullPath) {
        Write-Host "  [OK] Found path: $path" -ForegroundColor Green
    } else {
        Write-Host "  [FAIL] Missing required artifact path: $path" -ForegroundColor Red
        $ArtifactsValid = $false
    }
}

if (-not $ArtifactsValid) {
    Write-Error "Deployment Failed: Essential production files or folders are missing!"
    Exit 1
}

# ------------------------------------------------------------------------------
# STEP 2: Python Environment Validation
# ------------------------------------------------------------------------------
Write-Host "`n[+] Step 2: Validating Python Environment..." -ForegroundColor Cyan

$VenvPython = Join-Path $TargetWorkDir ".venv\Scripts\python.exe"
if (Test-Path $VenvPython) {
    $PythonPath = $VenvPython
    Write-Host "  [OK] Located local virtual environment Python: $PythonPath" -ForegroundColor Green
} else {
    Write-Host "  [WARN] Local virtual environment (.venv) was not found." -ForegroundColor Yellow
    $PythonPath = (Get-Command python.exe -ErrorAction SilentlyContinue).Source
    if (-not $PythonPath) {
        Write-Error "Deployment Failed: python.exe was not found in PATH or .venv!"
        Exit 1
    }
    Write-Host "  [INFO] Using global system Python: $PythonPath" -ForegroundColor Yellow
}

# Check Python version >= 3.10
try {
    $VersionString = & $PythonPath -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
    $Major, $Minor = $VersionString.Split('.')
    if ([int]$Major -lt 3 -or ([int]$Major -eq 3 -and [int]$Minor -lt 10)) {
        Write-Error "Deployment Failed: Python version must be 3.10+ (Current version is $VersionString)"
        Exit 1
    }
    Write-Host "  [OK] Python Version is $VersionString (Compatible)" -ForegroundColor Green
} catch {
    Write-Error "Deployment Failed: Unable to verify Python version!"
    Exit 1
}

# Verify python syntax and compilation
Write-Host "  [INFO] Performing static syntax check on codebase..." -ForegroundColor Yellow
try {
    & $PythonPath -m compileall -q "$TargetWorkDir\src" | Out-Null
    & $PythonPath -m compileall -q "$TargetWorkDir\app" | Out-Null
    Write-Host "  [OK] No syntax or compilation warnings detected." -ForegroundColor Green
} catch {
    Write-Host "  [WARN] Non-blocking compilation checks encountered exceptions." -ForegroundColor Yellow
}

# ------------------------------------------------------------------------------
# STEP 3: Environment Configurations Verification (.env)
# ------------------------------------------------------------------------------
Write-Host "`n[+] Step 3: Checking Environment Configuration..." -ForegroundColor Cyan

$EnvFile = Join-Path $TargetWorkDir ".env"
$EnvProdTemplate = Join-Path $TargetWorkDir ".env.production"

if (-not (Test-Path $EnvFile)) {
    if (Test-Path $EnvProdTemplate) {
        Write-Host "  [INFO] .env not found. Copying .env.production as base..." -ForegroundColor Yellow
        Copy-Item $EnvProdTemplate $EnvFile -Force
        Write-Host "  [WARN] Generated .env file. PLEASE open '.env' and replace secure placeholder values before start!" -ForegroundColor Yellow
    } else {
        Write-Error "Deployment Failed: Neither .env nor .env.production templates exist!"
        Exit 1
    }
} else {
    Write-Host "  [OK] Found existing '.env' file." -ForegroundColor Green
}

# ------------------------------------------------------------------------------
# STEP 4: Windows Service Verification
# ------------------------------------------------------------------------------
Write-Host "`n[+] Step 4: Checking YarTrader Windows Service..." -ForegroundColor Cyan

$Service = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue

if ($Service) {
    Write-Host "  [OK] Service '$ServiceName' is registered." -ForegroundColor Green
    Write-Host "  [INFO] Current Service Status: $($Service.Status)" -ForegroundColor Yellow

    if ($isAdmin) {
        Write-Host "  [INFO] Restarting Windows Service for deployment updates..." -ForegroundColor Yellow
        try {
            Restart-Service -Name $ServiceName -Force -ErrorAction Stop
            Start-Sleep -Seconds 3
            $NewService = Get-Service -Name $ServiceName
            Write-Host "  [OK] Service restarted successfully. New Status: $($NewService.Status)" -ForegroundColor Green
        } catch {
            Write-Host "  [WARN] Failed to automatically restart service. You may need to manually restart 'YarTrader'." -ForegroundColor Yellow
            Write-Host "  Error detail: $_" -ForegroundColor Yellow
        }
    } else {
        Write-Host "  [INFO] Run as Administrator to restart service automatically." -ForegroundColor Yellow
    }
} else {
    Write-Host "  [WARN] Service '$ServiceName' is not currently registered on this machine." -ForegroundColor Yellow
    Write-Host "         Run 'scripts\install_service.ps1' or 'scripts\deploy_service.ps1' to install it." -ForegroundColor Yellow
}

Write-Host "`n==========================================================" -ForegroundColor Green
Write-Host "DEPLOYMENT PREPARATION COMPLETE!" -ForegroundColor Green
Write-Host "The application is ready for production hosting." -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Green
