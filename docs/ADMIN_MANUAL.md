# ADMIN MANUAL
# TradeYar AI v3.2 — Enterprise Productization Phase

This manual is intended for **System Administrators**, **SREs**, and **DevOps Engineers** managing the production environment of **TradeYar AI v3.2**.

---

## 1. System Requirements & Stack

- **Operating System:** Windows Server 2022 (configured with NSSM) or Linux (Ubuntu 20.04+).
- **Python Version:** 3.12 (compiles clean with zero syntax warnings).
- **Database:**
  - **Product Metadata:** PostgreSQL 14+ (or SQLite local fallback for development).
  - **Memory Persistence:** Direct-to-disk filesystem JSON structures located at `runtime_logs/brain_memory/`.
- **Backend Framework:** FastAPI (served via Uvicorn/Gunicorn).

---

## 2. Managing the Admin Portal

The **Admin Portal** is accessible in the main dashboard header to users logged in with the `Admin` or `SuperAdmin` role. It contains the following tools:

### 2.1. System Validation Runner
- Triggered by clicking **"Run Full Validation"** (اجرای فرآیند تایید نهایی).
- This starts the background execution of the automated system acceptance script (`validate_release.py`).
- The panel receives live websocket/polling events containing:
  - Total passed, failed, skipped, and warned tests.
  - Active execution phase & active boundary component.
  - Real-time SRE logs.

### 2.2. Historical Audit Log Table
Provides a full chronological table of previous system validation execution runs:
- **Timestamp:** Exact execution time.
- **Duration:** Processing duration in seconds.
- **Passed Ratio:** Number of green tests over total test cases.
- **Final Status:** "Production Ready" or "Failed".
- **Readiness Score:** Weighted score from 0% to 100%.

---

## 3. Database Management with Alembic

To manage database updates safely for PostgreSQL, TradeYar AI utilizes **Alembic**.

### 3.1. Generating Database Migrations
When changing SQLAlchemy models inside `src/Application/Dashboard/database.py`, generate a new migration script using:
```bash
alembic revision --autogenerate -m "description_of_change"
```

### 3.2. Applying Migrations
Apply pending migrations to update the PostgreSQL schema:
```bash
alembic upgrade head
```

### 3.3. Rolling Back Migrations
Rollback the last migration:
```bash
alembic downgrade -1
```

---

## 4. Troubleshooting and Recovery

### 4.1. MT5 Connection Failures
If the MetaTrader5 link is disconnected, TradeYar AI's `MT5DataProvider` will automatically fallback to **Deterministic validation generation mode** for unsupported symbols. SREs should check broker login credentials or verify terminal path parameters.

### 4.2. Memory Recovery Flow
If a file corruption occurs during memory persistence writes, the `MarketMemorySystem`'s internal transaction safeguards will detect the failure and attempt automatic recovery from the latest safe backup snapshot located under `runtime_logs/brain_memory/backups/`.
