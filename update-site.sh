#!/usr/bin/env bash
# YarTrader Safe One-Command Production Update (Bash / Linux / macOS)
set -e

echo "=================================================="
echo " YarTrader Safe One-Command Production Update "
echo "=================================================="

# 1. Verify Repository Root
if [ ! -d ".git" ]; then
    echo "Error: Must be run from the root of YarTrader repository."
    exit 1
fi

# 2. Run Frontend Build Validation
echo ""
echo "[1/5] Building Frontend (trader-terminal)..."
cd trader-terminal
npm run build
cd ..
echo "Frontend build compiled successfully."

# 3. Check Git Status
echo ""
echo "[2/5] Checking Git Status..."
if [ -z "$(git status --short)" ]; then
    echo "No local changes detected. Repository is already up to date."
    exit 0
fi

git status --short

# 4. Stage and Commit
echo ""
echo "[3/5] Staging and Committing Changes..."
COMMIT_MSG="${1:-update: automated production release build and site synchronization}"
git add .
git commit -m "$COMMIT_MSG"

# 5. Push to GitHub Remote Branch
echo ""
echo "[4/5] Pushing to GitHub Remote..."
CURRENT_BRANCH=$(git branch --show-current)
git push origin "$CURRENT_BRANCH"

echo ""
echo "[5/5] Production Verification..."
CURRENT_SHA=$(git rev-parse HEAD)
echo "Deployed HEAD Commit SHA: $CURRENT_SHA"

echo ""
echo "=================================================="
echo " SUCCESS: Production Update Complete! "
echo "=================================================="
