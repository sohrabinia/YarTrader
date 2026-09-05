#!/usr/bin/env bash
# YarTrader Safe One-Command Production Update Automation Script
set -e

echo "=================================================="
echo " YarTrader Safe Production Update Automation "
echo "=================================================="

# 1. Preflight Verification
if [ ! -d ".git" ]; then
    echo "CRITICAL: Must be run from the root of YarTrader repository."
    exit 1
fi

CURRENT_BRANCH=$(git branch --show-current)
if [ "$CURRENT_BRANCH" = "main" ] || [ "$CURRENT_BRANCH" = "master" ]; then
    echo "WARNING: Active branch is '$CURRENT_BRANCH'. Direct push may require Pull Request."
fi

# 2. Detect Modified Tracked vs Untracked Files (Strict Approved Path Staging)
ALLOWED_PATHS=("update-site.ps1" "update-site.sh" "YARTRADER_FINAL_GIT_IDENTITY_PROOF.md")

MODIFIED_FILES=$(git status --porcelain | grep -v '^\?\?' | awk '{print $2}' || true)
UNTRACKED_FILES=$(git status --porcelain | grep '^\?\?' | awk '{print $2}' || true)

# Check for unexpected modified tracked files outside allowed paths
UNAPPROVED=""
for file in $MODIFIED_FILES; do
    is_allowed=false
    for allowed in "${ALLOWED_PATHS[@]}"; do
        if [ "$file" = "$allowed" ]; then
            is_allowed=true
            break
        fi
    done
    if [ "$is_allowed" = false ]; then
        UNAPPROVED="$UNAPPROVED $file"
    fi
done

if [ -n "$UNAPPROVED" ]; then
    echo "CRITICAL: Unapproved modified tracked files detected outside allowed deployment script scope:"
    for f in $UNAPPROVED; do
        echo "  $f"
    done
    echo "Deployment aborted to prevent staging unexpected modifications. Please review or restore these files first."
    exit 1
fi

if [ -z "$MODIFIED_FILES" ]; then
    echo "No tracked file modifications detected. Working tree clean."
    if [ -n "$UNTRACKED_FILES" ]; then
        echo "Untracked files exist but will NOT be staged automatically:"
        echo "$UNTRACKED_FILES"
    fi
    exit 0
fi

echo ""
echo "Tracked modifications to be committed:"
echo "$MODIFIED_FILES"

if [ -n "$UNTRACKED_FILES" ]; then
    echo ""
    echo "Untracked files (ignored & NOT staged):"
    echo "$UNTRACKED_FILES"
fi

# 3. Pre-Commit Validation: Pytest Suite & Frontend Build
echo ""
echo "[1/6] Running Backend Pytest Suite..."
python3 -m pytest -v

echo ""
echo "[2/6] Validating Frontend Build (trader-terminal)..."
cd trader-terminal
npm run build
cd ..
echo "Frontend build compiled successfully."

# 4. Pre-Commit Validation: Git Diff Formatting
echo ""
echo "[3/6] Checking Git Diff Formatting..."
git diff --check
echo "Git diff check passed."

# 5. User Confirmation Prompt (Fail-Closed Default = NO)
COMMIT_MSG="${1:-update: automated production release build and site synchronization}"
echo ""
echo "Proposed Commit Message: '$COMMIT_MSG'"
read -p "Continue with staging approved paths, commit, and push to origin/$CURRENT_BRANCH? [y/N] " CONFIRMATION
case "$CONFIRMATION" in
    [yY][eE][sS]|[yY])
        ;;
    *)
        echo "Update cancelled by user. No changes committed."
        exit 0
        ;;
esac

# 6. Stage Approved Allowed Files ONLY & Commit
echo ""
echo "[4/6] Staging Approved Allowed Files & Committing..."
for allowed in "${ALLOWED_PATHS[@]}"; do
    if [ -f "$allowed" ]; then
        git add "$allowed"
    fi
done

git commit -m "$COMMIT_MSG"

COMMIT_SHA=$(git rev-parse HEAD)
echo "Committed HEAD SHA: $COMMIT_SHA"

# 7. Push to Remote Source Branch (No --force)
echo ""
echo "[5/6] Pushing to GitHub Remote (origin/$CURRENT_BRANCH)..."
git push origin "$CURRENT_BRANCH"

REMOTE_SHA=$(git ls-remote origin "refs/heads/$CURRENT_BRANCH" | awk '{print $1}')
if [ "$COMMIT_SHA" != "$REMOTE_SHA" ]; then
    echo "ERROR: Remote SHA mismatch ($REMOTE_SHA != $COMMIT_SHA). Push verification failed."
    exit 1
fi
echo "Remote branch origin/$CURRENT_BRANCH verified at $REMOTE_SHA."

# 8. Multilingual & Multi-Route Fail-Closed Production HTTP Smoke Check
echo ""
echo "[6/6] Executing Multilingual Production HTTP Smoke Check..."
URLS=(
    "https://yartrader.com/"
    "https://yartrader.com/fa/"
    "https://yartrader.com/fa/pricing"
    "https://yartrader.com/fa/guide"
    "https://yartrader.com/fa/faq"
    "https://yartrader.com/en/"
    "https://yartrader.com/tr/"
    "https://yartrader.com/ar/"
)

ALL_PASSED=true
for url in "${URLS[@]}"; do
    PASSED=false
    for attempt in {1..3}; do
        STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$url" || echo "000")
        if [ "$STATUS" -ge 200 ] && [ "$STATUS" -lt 400 ]; then
            echo "  [HTTP $STATUS OK] $url"
            PASSED=true
            break
        fi
        sleep 2
    done
    if [ "$PASSED" = false ]; then
        echo "  [FAIL / UNVERIFIED] $url"
        ALL_PASSED=false
    fi
done

echo ""
echo "=================================================="
if [ "$ALL_PASSED" = true ]; then
    echo " PRODUCTION VERIFIED: All routes healthy! "
    echo "=================================================="
else
    echo " SMOKE TEST FAILED / UNVERIFIED: One or more routes failed health check. "
    echo "=================================================="
    exit 1
fi
