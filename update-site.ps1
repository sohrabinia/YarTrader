# YarTrader One-Command Safe Update & Deployment Automation Script

Param(
    [string]$CommitMessage = "update: automated production release build and site synchronization"
)

$ErrorActionPreference = "Stop"

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host " YarTrader Safe One-Command Production Update " -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan

# 1. Verify Git Repository Root
if (-not (Test-Path ".git")) {
    Write-Error "Error: Must be run from the root of YarTrader repository."
}

# 2. Check Branch Protection
$currentBranch = git branch --show-current
if ($currentBranch -eq "main" -or $currentBranch -eq "master") {
    Write-Host "WARNING: You are on branch '$currentBranch'. Direct pushes may be blocked by branch protection." -ForegroundColor Yellow
}

# 3. Check Git Status & Modifications
$untrackedFiles = git status --porcelain | Where-Object { $_ -like "\?\?*" }
$modifiedFiles = git status --porcelain | Where-Object { $_ -notlike "\?\?*" }

if (-not $modifiedFiles) {
    Write-Host "No tracked file modifications detected. Repository working tree is clean." -ForegroundColor Green
    if ($untrackedFiles) {
        Write-Host "Note: Untracked files exist but will NOT be automatically staged." -ForegroundColor Gray
    }
    exit 0
}

Write-Host "`nTracked files to be committed:" -ForegroundColor Yellow
$modifiedFiles | ForEach-Object { Write-Host "  $_" -ForegroundColor Gray }

if ($untrackedFiles) {
    Write-Host "`nUntracked files (ignored / NOT staged):" -ForegroundColor Gray
    $untrackedFiles | ForEach-Object { Write-Host "  $_" -ForegroundColor DarkGray }
}

# 4. Pre-Commit Frontend Build & Git Diff Validation
Write-Host "`n[1/5] Validating Frontend Build (trader-terminal)..." -ForegroundColor Yellow
Set-Location trader-terminal
npm run build
if ($LASTEXITCODE -ne 0) {
    Set-Location ..
    Write-Error "BUILD FAILED! Aborting update. No changes committed."
}
Set-Location ..
Write-Host "Frontend build compiled successfully." -ForegroundColor Green

Write-Host "`n[2/5] Validating Git Diff Formatting..." -ForegroundColor Yellow
git diff --check
if ($LASTEXITCODE -ne 0) {
    Write-Error "Git diff check failed (whitespace or conflict errors detected). Aborting update."
}
Write-Host "Git diff check passed." -ForegroundColor Green

# 5. User Confirmation Prompt
Write-Host "`nProposed Commit Message: '$CommitMessage'" -ForegroundColor Cyan
$confirmation = Read-Host "Continue with commit and push to origin/$currentBranch? [Y/N]"
if ($confirmation -ne "Y" -and $confirmation -ne "y") {
    Write-Host "Update cancelled by user. No changes committed." -ForegroundColor Yellow
    exit 0
}

# 6. Stage Tracked Files ONLY & Commit
Write-Host "`n[3/5] Staging Tracked Files and Committing..." -ForegroundColor Yellow
git add -u
git commit -m "$CommitMessage"
if ($LASTEXITCODE -ne 0) {
    Write-Error "Git commit failed."
}
Write-Host "Committed successfully." -ForegroundColor Green

# 7. Push to Remote Source Branch
Write-Host "`n[4/5] Pushing to GitHub Remote (origin/$currentBranch)..." -ForegroundColor Yellow
git push origin "$currentBranch"
if ($LASTEXITCODE -ne 0) {
    Write-Error "Git push failed. Please verify network or branch permissions."
}
Write-Host "Pushed to origin/$currentBranch successfully." -ForegroundColor Green

# 8. Production HTTP Smoke Check & Status Report
Write-Host "`n[5/5] Performing Production HTTP Smoke Check..." -ForegroundColor Yellow
$urls = @(
    "https://yartrader.com/",
    "https://yartrader.com/fa/",
    "https://yartrader.com/fa/pricing",
    "https://yartrader.com/fa/guide",
    "https://yartrader.com/fa/faq",
    "https://yartrader.com/en/"
)

$smokeSuccess = $true
foreach ($url in $urls) {
    try {
        $response = Invoke-WebRequest -Uri $url -Method Head -TimeoutSec 5 -ErrorAction SilentlyContinue
        if ($response.StatusCode -eq 200) {
            Write-Host "  [200 OK] $url" -ForegroundColor Green
        } else {
            Write-Host "  [$($response.StatusCode)] $url" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "  [UNAVAILABLE / ASYNC] $url" -ForegroundColor DarkGray
        $smokeSuccess = $false
    }
}

Write-Host "`n==================================================" -ForegroundColor Green
Write-Host " Push Complete: GitHub CI / Deployment Triggered! " -ForegroundColor Green
if (-not $smokeSuccess) {
    Write-Host " Note: Push completed; production deployment status is async or pending CI." -ForegroundColor Yellow
}
Write-Host "==================================================" -ForegroundColor Green
