# TradeYar AI Production Deployment Guide

This guide describes how to deploy, configure, and monitor the TradeYar AI (RG_V3_AI) Platform in a production-ready financial intelligence ecosystem.

## 1. Prerequisites
- Python 3.12+ installed.
- System environment configured to support standard directory paths (e.g., `H:\TradeYarAI\` on Windows or `/tmp/TradeYarAI/` on Linux).

## 2. Installation
Install project dependencies from the root directory or the `deploy/` directory:
```bash
pip install -r deploy/requirements.txt
```

## 3. Launching the Platform
You can run the platform status or health diagnostics via the provided startup script or directly via the Python CLI tool.

### Windows Batch Launcher
Execute the batch utility:
```cmd
deploy\run_tradeyar_ai.bat
```

### Direct CLI Tool
```bash
# General help and usage:
python -m src.cli.cli --help

# To run platform health diagnostics:
python -m src.cli.cli health

# To run the simulated 8-stage demo scenarios:
python -m src.cli.cli run-demo

# To run an offline simulation stress-test:
python -m src.cli.cli run-simulation --asset EURUSD
```

## 4. Environment Configuration
The platform respects the following environment variables:
- `RG_ENV`: Execution environment name (`development`, `test`, `simulation`, `production`).
- `RG_LOG_LEVEL`: Log severity (`DEBUG`, `INFO`, `WARNING`, `ERROR`).
- `RG_LOOKBACK_DAYS`: Backtesting/Analysis historical day limit (between 1 and 365).
- `RG_API_TIMEOUT`: Outgoing requests timeout seconds.
- `TradeYarStorageRoot`: Isolated base storage root.

## 5. Security & Isolation
- **APES-FIN Compliance**: Strictly simulation-only framework. Zero broker adapters, live capital exposure, or buy/sell execution engines exist.
- **Obfuscation**: Secret values inside the configurations are managed inside the secure `SecretsVault` dynamically checking for obfuscated keywords.
