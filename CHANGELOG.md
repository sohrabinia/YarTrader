# Changelog — TradeYar AI

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-07-17

### Added
- Created the **Production Acceptance and Autonomous Release Validation Platform** (`validate_release.py`).
- Integrated AST-context-aware scanners for zero-false-positive `SecurityAuditor` and `ComplianceAuditor`.
- Developed a production-grade FastAPI-based Web Dashboard and System Validation Center.
- Programmed REST APIs for health diagnostics, telemetry, run control, symbols lookup, and scorecards.
- Configured GitHub Actions CI/CD automation pipeline.

### Changed
- Refactored `SecurityAuditor` and `ComplianceAuditor` to run AST scans on codebase, skipping false positives.
- Optimized workspace configuration to derive storage roots strictly from isolated environment path directories.

### Removed
- Pruned duplicate string-matching logic to enforce Clean Architecture boundaries.
