# YarTrader Safe One-Command Production Update Automation Script

Param(
    [string]$CommitMessage = "update: automated production release build and site synchronization"
)

$ErrorActionPreference = "Stop"

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host " YarTrader Safe Production Update Automation " -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan

# 1. Preflight Verification
if (-not (Test-Path ".git")) {
    Write-Error "CRITICAL: Must be run from the root of YarTrader repository."
    exit 1
}

$currentBranch = git branch --show-current
if ($currentBranch -eq "main" -or $currentBranch -eq "master") {
    Write-Host "WARNING: Active branch is '$currentBranch'. Direct push may require Pull Request due to branch protection." -ForegroundColor Yellow
}

# 2. Detect Modified Tracked vs Untracked Files (Strict Approved Path Staging)
$allowedPaths = @("update-site.ps1", "update-site.sh", "YARTRADER_FINAL_GIT_IDENTITY_PROOF.md")
$statusPorcelain = git status --porcelain

$modifiedFiles = $statusPorcelain | Where-Object { $_ -notlike "\?\?*" } | ForEach-Object { $_.Substring(3).Trim() }
$untrackedFiles = $statusPorcelain | Where-Object { $_ -like "\?\?*" } | ForEach-Object { $_.Substring(3).Trim() }

# Reject any unexpected modified tracked files outside allowed paths
$unapprovedModified = $modifiedFiles | Where-Object { $allowedPaths -notcontains $_ }

if ($unapprovedModified) {
    Write-Host "CRITICAL: Unapproved modified tracked files detected outside allowed deployment script scope:" -ForegroundColor Red
    $unapprovedModified | ForEach-Object { Write-Host "  $_" -ForegroundColor Red }
    Write-Error "Deployment aborted to prevent staging unexpected modifications. Please review or restore these files first."
    exit 1
}

if (-not $modifiedFiles) {
    Write-Host "No tracked file modifications detected. Working tree clean." -ForegroundColor Green
    if ($untrackedFiles) {
        Write-Host "Untracked files exist but will NOT be staged automatically:" -ForegroundColor Gray
        $untrackedFiles | ForEach-Object { Write-Host "  $_" -ForegroundColor DarkGray }
    }
    exit 0
}

Write-Host "`nTracked modifications to be committed:" -ForegroundColor Yellow
$modifiedFiles | ForEach-Object { Write-Host "  $_" -ForegroundColor Gray }

if ($untrackedFiles) {
    Write-Host "`nUntracked files (ignored & NOT staged):" -ForegroundColor Gray
    $untrackedFiles | ForEach-Object { Write-Host "  $_" -ForegroundColor DarkGray }
}

# 3. Pre-Commit Validation: Pytest Suite & Frontend Build
Write-Host "`n[1/6] Running Backend Pytest Suite..." -ForegroundColor Yellow
python3 -m pytest -v
if ($LASTEXITCODE -ne 0) {
    Write-Error "TEST SUITE FAILED! Aborting update. No changes committed."
    exit 1
}

Write-Host "`n[2/6] Validating Frontend Build (trader-terminal)..." -ForegroundColor Yellow
Set-Location trader-terminal
npm run build
if ($LASTEXITCODE -ne 0) {
    Set-Location ..
    Write-Error "FRONTEND BUILD FAILED! Aborting update. No changes committed."
    exit 1
}
Set-Location ..
Write-Host "Frontend build compiled successfully." -ForegroundColor Green

# 4. Pre-Commit Validation: Git Diff Formatting
Write-Host "`n[3/6] Checking Git Diff Formatting..." -ForegroundColor Yellow
git diff --check
if ($LASTEXITCODE -ne 0) {
    Write-Error "Git diff check failed (whitespace or conflict markers). Aborting update."
    exit 1
}

# 5. User Confirmation Prompt (Fail-Closed Default = NO)
Write-Host "`nProposed Commit Message: '$CommitMessage'" -ForegroundColor Cyan
$confirmation = Read-Host "Continue with staging approved paths, commit, and push to origin/$currentBranch? [y/N]"
if ($confirmation -ne "Y" -and $confirmation -ne "y") {
    Write-Host "Update cancelled by user. No changes staged or committed." -ForegroundColor Yellow
    exit 0
}

# 6. Stage ONLY Approved Allowed Files & Commit
Write-Host "`n[4/6] Staging Approved Allowed Files & Committing..." -ForegroundColor Yellow
foreach ($file in $allowedPaths) {
    if (Test-Path $file) {
        git add $file
    }
}

git commit -m "$CommitMessage"
if ($LASTEXITCODE -ne 0) {
    Write-Error "Git commit failed."
    exit 1
}

$commitSHA = git rev-parse HEAD
Write-Host "Committed HEAD SHA: $commitSHA" -ForegroundColor Green

# 7. Push to Remote Source Branch (No --force)
Write-Host "`n[5/6] Pushing to GitHub Remote (origin/$currentBranch)..." -ForegroundColor Yellow
git push origin "$currentBranch"
if ($LASTEXITCODE -ne 0) {
    Write-Error "Git push failed. Verify remote branch permissions or pull request rules."
    exit 1
}

$remoteSHA = git ls-remote origin "refs/heads/$currentBranch" | ForEach-Object { $_.Split("`t")[0] }
if ($commitSHA -ne $remoteSHA) {
    Write-Error "Remote SHA mismatch ($remoteSHA != $commitSHA). Push verification failed."
    exit 1
}
Write-Host "Remote branch origin/$currentBranch verified at $remoteSHA." -ForegroundColor Green

# 8. Multilingual & Multi-Route Fail-Closed Production HTTP Smoke Check (Bounded Retries)
Write-Host "`n[6/6] Executing Multilingual Production HTTP Smoke Check..." -ForegroundColor Yellow
$urls = @(
    "https://yartrader.com/",
    "https://yartrader.com/fa/",
    "https://yartrader.com/fa/pricing",
    "https://yartrader.com/fa/guide",
    "https://yartrader.com/fa/faq",
    "https://yartrader.com/en/",
    "https://yartrader.com/tr/",
    "https://yartrader.com/ar/"
)

$allPassed = $true
foreach ($url in $urls) {
    $passed = $false
    for ($attempt = 1; $attempt -le 3; $attempt++) {
        try {
            $req = [System.Net.WebRequest]::Create($url)
            $req.Method = "GET"
            $req.Timeout = 5000
            $res = $req.GetResponse()
            $code = [int]$res.StatusCode
            $res.Close()
            if ($code -ge 200 -and $code -lt 400) {
                Write-Host "  [HTTP $code OK] $url" -ForegroundColor Green
                $passed = $true
                break
            }
        } catch {
            Start-Sleep -Seconds 2
        }
    }
    if (-not $passed) {
        Write-Host "  [FAIL / UNVERIFIED] $url" -ForegroundColor Red
        $allPassed = $false
    }
}

Write-Host "`n==================================================" -ForegroundColor Green
if ($allPassed) {
    Write-Host " PRODUCTION VERIFIED: All routes healthy! " -ForegroundColor Green
    Write-Host "==================================================" -ForegroundColor Green
} else {
    Write-Host " SMOKE TEST FAILED / UNVERIFIED: One or more routes failed health check. " -ForegroundColor Red
    Write-Host "==================================================" -ForegroundColor Red
    exit 1
}
