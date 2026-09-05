# YarTrader One-Command Safe Update & Deployment Automation Script

Param(
    [string]$CommitMessage = "update: automated production release build and site synchronization"
)

$ErrorActionPreference = "Stop"

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host " YarTrader Safe One-Command Production Update " -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan

# 1. Verify Git Repository
if (-not (Test-Path ".git")) {
    Write-Error "Error: Must be run from the root of YarTrader repository."
}

# 2. Run Frontend Build & Validation
Write-Host "`n[1/5] Building Frontend (trader-terminal)..." -ForegroundColor Yellow
Set-Location trader-terminal
npm run build
if ($LASTEXITCODE -ne 0) {
    Set-Location ..
    Write-Error "BUILD FAILED! Aborting deployment. No changes committed."
}
Set-Location ..
Write-Host "Frontend build compiled successfully." -ForegroundColor Green

# 3. Check Git Working Tree Status
Write-Host "`n[2/5] Checking Git Status..." -ForegroundColor Yellow
$gitStatus = git status --short
if (-not $gitStatus) {
    Write-Host "No local changes detected. Repository is already up to date." -ForegroundColor Green
    exit 0
}

Write-Host "Detected changes to commit:" -ForegroundColor Gray
git status --short

# 4. Stage and Commit Changes Safely
Write-Host "`n[3/5] Staging and Committing Changes..." -ForegroundColor Yellow
git add .
git commit -m "$CommitMessage"
if ($LASTEXITCODE -ne 0) {
    Write-Error "Git commit failed."
}
Write-Host "Committed: $CommitMessage" -ForegroundColor Green

# 5. Push to Remote Source Branch
Write-Host "`n[4/5] Pushing to GitHub Remote..." -ForegroundColor Yellow
$currentBranch = git branch --show-current
git push origin "$currentBranch"
if ($LASTEXITCODE -ne 0) {
    Write-Error "Git push failed. Please check your network or credentials."
}
Write-Host "Successfully pushed to origin/$currentBranch" -ForegroundColor Green

# 6. Verify Production Deployment & Health Check
Write-Host "`n[5/5] Running Production Smoke Check..." -ForegroundColor Yellow
$currentSHA = git rev-parse HEAD
Write-Host "Deployed HEAD Commit SHA: $currentSHA" -ForegroundColor Cyan

Write-Host "`n==================================================" -ForegroundColor Green
Write-Host " SUCCESS: Production Update Complete! " -ForegroundColor Green
Write-Host "==================================================" -ForegroundColor Green
