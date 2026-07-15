# Technical Troubleshooting Guide

This guide compiles common diagnostics, troubleshooting steps, and recovery guidelines for operational failures.

## 1. Diagnostics Run
Run system diagnostics via the health command line tool:
```bash
python -m src.cli.cli health
```
And check detailed performance telemetry:
```bash
python -m src.cli.cli diagnostics
```

## 2. Common Issues and Resolutions

### Invalid Configuration Error
- **Cause**: Out-of-bounds parameters like `LOOKBACK_DAYS` greater than 365.
- **Resolution**: Reset environment variables `RG_LOOKBACK_DAYS` to a valid value (e.g., 15) and restart the host.

### Port Already In Use
- **Cause**: Active Rest API daemon running in background.
- **Resolution**: Use port termination utilities:
  ```bash
  kill $(lsof -t -i :3000) 2>/dev/null || true
  ```

### Storage Root Write Failure
- **Cause**: Permission denied on writing base path or missing isolated structure directories.
- **Resolution**: Redefine base directory base to an active temp folder using:
  ```bash
  export TradeYarStorageRoot=/tmp/TradeYarAI/
  ```
