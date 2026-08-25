#!/usr/bin/env bash
# YarTrader Production Runtime Launcher (Bash)
# Enforces storage root isolation and production environment setup

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

# 1. Enforce Production Storage Root Isolation
export TradeYarStorageRoot="${TradeYarStorageRoot:-/tmp/YarTraderAI}"
export YarTraderStorageRoot="$TradeYarStorageRoot"

mkdir -p "$TradeYarStorageRoot/Logs"

# 2. Environment Variables Configuration
export YARTRADER_ENV="production"
export TRADEYAR_ENV="production"
export LIVE_TRADING_ENABLED="False"
export YARTRADER_API_HOST="0.0.0.0"
export YARTRADER_API_PORT="8000"
export PYTHONPATH=".:$PYTHONPATH"

echo "============================================================"
echo " YarTrader Production Runtime Launcher"
echo " Storage Root  : $TradeYarStorageRoot"
echo " Logs Directory : $TradeYarStorageRoot/Logs"
echo " API Binding    : http://$YARTRADER_API_HOST:$YARTRADER_API_PORT"
echo "============================================================"

# 3. Execute Uvicorn via active Python
if [ -f "$PROJECT_ROOT/.venv/bin/python" ]; then
    exec "$PROJECT_ROOT/.venv/bin/python" -m uvicorn src.Application.Services.web_dashboard:app --host "$YARTRADER_API_HOST" --port "$YARTRADER_API_PORT" --log-level info
else
    exec python3 -m uvicorn src.Application.Services.web_dashboard:app --host "$YARTRADER_API_HOST" --port "$YARTRADER_API_PORT" --log-level info
fi
