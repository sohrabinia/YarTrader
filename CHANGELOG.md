# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-07-15

### Added
- **Observability Platform**: Standardized structured JSON logging, correlation IDs, performance tracker, tracing spans, and read-only audit trails.
- **Diagnostics & Health Subsystem**: SubsystemHealthCheck and PlatformDiagnosticsEngine compiling READY/WARNING/FAILED states across all layers.
- **Reporting Engine**: HTML, Markdown, and JSON export utilities for Research, Risk, Decision, Simulation, and Health reports.
- **CLI Utilities**: Decoupled commands to run demo scenarios, diagnostics, health checks, and report compile outputs.
- **Deployment Platform**: Windows launcher batch scripts, pinned requirements, and operational deployment documentation manuals.
- **AST Compliance Scanner**: Abstract Syntax Tree compliance scanner verifying APES-FIN rules, skipping defensive folders, and ignoring binary `.pyc` files.
- **Production Test Suite**: Comprehensive E2E tests validating lifecycles, configuration boundaries, diagnostics, and recovery behaviors.

### Changed
- Refactored DI Registrations to bind storage managers, diagnostic engines, and report compilers dynamically.
- Integrated the new performance metrics tracker to capture sub-millisecond latencies across pipeline layers.

### Removed
- Removed old plain-text regex compliance scanning in favor of context-aware python AST syntax scanning.
