# Platform Operations Guide

This guide describes standard operational procedures for administrative monitoring of the TradeYar AI platform.

## 1. CLI Commands Execution
The platform provides a standalone command-line interface tool to control the platform without a GUI:
```bash
# General status checks:
python -m src.cli.cli status

# Health checks:
python -m src.cli.cli health

# Subsystem diagnostics & latency:
python -m src.cli.cli diagnostics

# Run standard pipelines demo:
python -m src.cli.cli run-demo

# Exporting formatted reports:
python -m src.cli.cli generate-report --type research --format html
```

## 2. Structured Storage Structure
All platform logs, reports, cached artifacts, and snapshots are strictly confined to the isolated root base directory (defined in configuration settings as `TradeYarStorageRoot`):
- `Logs/`: Appends structured JSON logging entries.
- `Reports/`: Saved PDF-ready print reports and HTML trace outputs.
- `Cache/`: Stores metadata parameters.
