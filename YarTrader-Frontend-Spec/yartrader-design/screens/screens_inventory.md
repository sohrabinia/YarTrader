# Screen Inventory and Target Workspaces

This document lists the five target workspaces required to be rendered by the Single Page Application platform.

---

## 1. Trader Terminal (`trader-terminal`)
- **Main trading workspace.**
- Shows high-performance financial charts.
- Visualizes real-time market monitors (`MarketCard`), `SymbolSelector`, active shadow signals (`SignalPanel`), and virtual order portfolios.

## 2. Public Platform (`public-platform`)
- **Public marketing site.**
- Landing pages explaining passive descriptive capabilities.
- Complete localized GDPR consent popups, long-form clean blog system, and user login forms.

## 3. Admin Console (`admin-console`)
- **Governance & Configuration dashboard.**
- Real-time limit selectors for managing active symbol configurations.
- User management and scope assignment lists.

## 4. SRE Control Center (`sre-control-center`)
- **Telemetry and monitoring cockpit.**
- Visualizes health probes (`/health/live`, `/health/ready`).
- Shows system performance metrics, watchdog state, and memory metrics.

## 5. Auth Workspace (`auth`)
- **Authentication Gateway.**
- Login, Register, password recovery screens utilizing secure PBKDF2-SHA256 password hashes.
