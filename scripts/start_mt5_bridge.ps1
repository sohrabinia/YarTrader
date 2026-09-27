# ==============================================================================
# YarTrader — MT5 Interactive Session Bridge Launcher
# ==============================================================================
# Runs inside Session 2 (Interactive Administrator Session) to bridge MT5 IPC
# to the LocalSystem Session 0 YarTrader Production Windows Service.
# ==============================================================================

[CmdletBinding()]
param(
    [string]$Port = "5001",
    [string]$HostAddress = "127.0.0.1"
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $ProjectRoot

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " YarTrader MT5 Interactive Bridge Launcher" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " Project Root: $ProjectRoot" -ForegroundColor Yellow
Write-Host " Host Binding: $HostAddress:$Port" -ForegroundColor Yellow
Write-Host " User Identity: $env:USERNAME" -ForegroundColor Yellow
Write-Host " Windows Session: $([System.Diagnostics.Process]::GetCurrentProcess().SessionId)" -ForegroundColor Yellow
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Locate Virtual Environment Python
$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $VenvPython)) {
    Write-Error "Virtual environment python not found at $VenvPython"
    exit 1
}

# 2. Resolve or Generate Secure Token
# Canonical Precedence:
#   1. MT5_BRIDGE_SECRET_TOKEN environment variable
#   2. <YarTraderStorageRoot>\Secrets\mt5_bridge_token.secret
#   3. C:\YarTraderAI\Secrets\mt5_bridge_token.secret
#   No relative or legacy path fallback

$SecretsDir = if ($env:YarTraderStorageRoot) {
    Join-Path $env:YarTraderStorageRoot "Secrets"
} else {
    'C:\YarTraderAI\Secrets'
}
if (-not (Test-Path $SecretsDir)) {
    New-Item -ItemType Directory -Path $SecretsDir -Force | Out-Null
}
$TokenFile = Join-Path $SecretsDir "mt5_bridge_token.secret"

$Token = $null
$tokenSourceDetails = $null

if (-not [string]::IsNullOrWhiteSpace($env:MT5_BRIDGE_SECRET_TOKEN)) {
    $Token = $env:MT5_BRIDGE_SECRET_TOKEN.Trim()
    $tokenSourceDetails = "Using MT5_BRIDGE_SECRET_TOKEN from environment."
    Write-Host " $tokenSourceDetails" -ForegroundColor Green
} else {
    $candidateTokenFiles = @(
        $TokenFile,
        'C:\YarTraderAI\Secrets\mt5_bridge_token.secret'
    )

    foreach ($tf in $candidateTokenFiles) {
        if (Test-Path $tf) {
            try {
                $tokCandidate = (Get-Content $tf -Raw).Trim()
                if (-not [string]::IsNullOrWhiteSpace($tokCandidate)) {
                    $Token = $tokCandidate
                    $tokenSourceDetails = "Using existing secret token from $tf"
                    Write-Host " $tokenSourceDetails" -ForegroundColor Green
                    break
                }
            } catch { Write-Verbose $_.Exception.Message }
        }
    }
}

if (-not $Token) {
    $Bytes = New-Object byte[] 32
    (New-Object Security.Cryptography.RNGCryptoServiceProvider).GetBytes($Bytes)
    $Token = [System.BitConverter]::ToString($Bytes).Replace("-", "").ToLower()
    Set-Content -Path $TokenFile -Value $Token -Encoding UTF8
    Write-Host " Generated new secret token at $TokenFile" -ForegroundColor Green
}

# Restrict ACL on TokenFile
try {
    icacls $TokenFile /grant "NT AUTHORITY\SYSTEM:F" "Administrators:F" /inheritance:r /Q
} catch {
    # Non-critical if non-Windows
}

$env:MT5_BRIDGE_SECRET_TOKEN = $Token
$env:MT5_BRIDGE_PORT = $Port
$env:PYTHONPATH = $ProjectRoot

# 3. Launch Uvicorn Bridge Agent
Write-Host " Launching MT5 Interactive Bridge on $HostAddress:$Port..." -ForegroundColor Green
& $VenvPython -m src.Infrastructure.Bridge.mt5_bridge
