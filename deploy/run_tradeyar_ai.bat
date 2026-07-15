@echo off
rem ==========================================================================
rem                   TradeYar AI Production Release Launcher
rem ==========================================================================

echo [INFO] Initializing TradeYar AI Production Environment...

rem 1. Set Environment Parameters
set RG_ENV=production
set RG_LOG_LEVEL=INFO
set RG_LOOKBACK_DAYS=15
set RG_API_TIMEOUT=5.0
set RG_MAX_RETRIES=3
set TradeYarStorageRoot=%TEMP%\TradeYarAI\

rem 2. Verify Python Installation
where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python was not found in your PATH. Please install Python 3.12+ and try again.
    exit /b 1
)

rem 3. Execute Platform Diagnostics
echo [INFO] Running Platform Diagnostics...
python -m src.cli.cli health
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Health diagnostics check failed. System is UNHEALTHY.
    exit /b 1
)

rem 4. Launch Status
echo [INFO] System is HEALTHY. Launching status dashboard...
python -m src.cli.cli status

echo [INFO] Execution completed successfully.
exit /b 0
