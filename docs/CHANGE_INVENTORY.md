# CHANGE INVENTORY
# TradeYar AI v3.2 — Enterprise Productization Phase

This catalog keeps track of all file modifications and creations introduced during **Phase 3.2 — Enterprise Productization**.

---

## 1. Created Files & Artifacts

| File Path | Description |
|---|---|
| `docs/PRODUCTIZATION_CURRENT_STATE_AUDIT.md` | Initial structural audit verifying frontend, backend endpoints, and timeframe boundaries. |
| `docs/PRODUCT_COMPLETION_REPORT.md` | Complete product phase signoff report. |
| `docs/USER_MANUAL.md` | User manual describing public website pages, RTL/LTR layouts, and dashboard panels. |
| `docs/ADMIN_MANUAL.md` | SRE/DevOps manual covering PostgreSQL Alembic migrations and troubleshooting. |
| `docs/API_GUIDE.md` | Developer documentation detailing REST API endpoint JSON payloads and authentication. |
| `docs/DEPLOYMENT_GUIDE.md` | System deployment details for staging, production, and Windows background services. |
| `docs/TIMEFRAME_INDEPENDENCE_AUDIT.md` | Specific architectural audit certifying the independence of internal cognitive timeframe scales. |
| `static/locales/fa.json` | Persian language translation file with RTL layout support (Default). |
| `static/locales/en.json` | English language translation file. |
| `static/locales/ar.json` | Arabic language translation file with RTL layout support. |
| `static/locales/tr.json` | Turkish language translation file. |
| `tests/TRADEYAR_AI.Tests/Services/test_v32_productization.py` | New backend integration tests verifying authorization, Blog CMS, migrations, and translation files. |

---

## 2. Modified Files

| File Path | Modification Summary |
|---|---|
| `src/Application/Services/web_dashboard.py` | Overhauled dashboard SPA page with translations loader, RTL layout support, fully removed technical indicators, integrated Cognitive Evidence Panel, JWT-based Authentication, and Markdown Blog CMS models. Connected live metrics bindings directly to API endpoints (`/v1/dashboard/cognitive`, `/api/shadow/metrics`, etc.) avoiding arithmetic offsets. |
| `src/Application/Dashboard/database.py` | Added SQLAlchemy schemas for Users, Roles, User Preferences, Blog Articles, and System Audit Logs. Provided direct compatibility with SQLite database mock files and production-grade PostgreSQL engines. |
| `alembic.ini` | Configured base alembic setup for database migration workflows. |
| `alembic/env.py` | Connected Alembic migration metadata target strictly to product-only metadata structures. |
| `alembic/script.py.mako` | Custom migration templates supporting transaction-safe execution flows. |
