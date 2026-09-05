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

# 2. Check Branch Protection Warning
CURRENT_BRANCH=$(git branch --show-current)
if [ "$CURRENT_BRANCH" = "main" ] || [ "$CURRENT_BRANCH" = "master" ]; then
    echo "WARNING: You are on branch '$CURRENT_BRANCH'. Direct pushes may be blocked by branch protection."
fi

# 3. Check Git Status & Modifications
if [ -z "$(git status --porcelain | grep -v '^\?\?')" ]; then
    echo "No tracked file modifications detected. Repository working tree is clean."
    exit 0
fi

echo ""
echo "Tracked files to be committed:"
git status --porcelain | grep -v '^\?\?'

# 4. Pre-Commit Frontend Build & Git Diff Validation
echo ""
echo "[1/5] Validating Frontend Build (trader-terminal)..."
cd trader-terminal
npm run build
cd ..
echo "Frontend build compiled successfully."

echo ""
echo "[2/5] Validating Git Diff Formatting..."
git diff --check
echo "Git diff check passed."

# 5. User Confirmation Prompt
COMMIT_MSG="${1:-update: automated production release build and site synchronization}"
echo ""
echo "Proposed Commit Message: '$COMMIT_MSG'"
read -p "Continue with commit and push to origin/$CURRENT_BRANCH? [y/N] " CONFIRMATION
case "$CONFIRMATION" in
    [yY][eE][sS]|[yY])
        ;;
    *)
        echo "Update cancelled by user. No changes committed."
        exit 0
        ;;
esac

# 6. Stage Tracked Files ONLY & Commit
echo ""
echo "[3/5] Staging Tracked Files and Committing..."
git add -u
git commit -m "$COMMIT_MSG"

# 7. Push to GitHub Remote Branch
echo ""
echo "[4/5] Pushing to GitHub Remote (origin/$CURRENT_BRANCH)..."
git push origin "$CURRENT_BRANCH"

# 8. Production HTTP Smoke Check
echo ""
echo "[5/5] Performing Production HTTP Smoke Check..."
URLS=(
    "https://yartrader.com/"
    "https://yartrader.com/fa/"
    "https://yartrader.com/fa/pricing"
    "https://yartrader.com/fa/guide"
    "https://yartrader.com/fa/faq"
    "https://yartrader.com/en/"
)

for url in "${URLS[@]}"; do
    STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$url" || echo "000")
    echo "  [$STATUS] $url"
done

echo ""
echo "=================================================="
echo " Push Complete: GitHub CI / Deployment Triggered! "
echo "=================================================="
