# TradeYar AI v3.2 — Productization & Current State Audit
**Role:** Senior Enterprise Software Architect & Principal Productization Engineer
**Status:** Phase 0 System Audit & Architecture Proposal Approved

---

## 1. Frontend Structure Audit
* **Current Implementation:** The current frontend is served directly as an inline single-page application (SPA) from the FastAPI endpoint `/` in `src/Application/Services/web_dashboard.py`.
* **Visual Stack:** The layout utilizes custom CSS, dynamic language dictionaries, and classical JavaScript string concatenation to avoid Jinja2 parsing conflicts.
* **Target Architecture:** We will transition the SPA to a modular web application with multi-language i18n dictionaries stored separately under `static/locales/` (mapped via static files). It will integrate Tailwind CSS themes, persistent custom layout directions, and decoupled user/admin access controls.
* **Prohibition Rule:** Absolutely zero trading buttons, active execution controls, or order routing interfaces are permitted.

---

## 2. Backend & API Contracts Audit
The FastAPI server currently exposes active polling worker results, SRE diagnostics, validation logs, and telemetry summaries. The following additional REST API routes are proposed for v3.2 enterprise alignment:

* **Authentication REST Endpoint Routing:**
  * `POST /api/v1/auth/register` — Standard registration.
  * `POST /api/v1/auth/login` — Issues access & refresh JWT tokens.
  * `POST /api/v1/auth/refresh` — Standard JWT token refresh.
  * `GET /api/v1/auth/me` — Retrieves current profile.
* **Product Management & Blog CMS:**
  * `GET /api/v1/blog` — List Markdown-based articles with categorization, tags, search.
  * `GET /api/v1/blog/{article_slug}` — Detail view with SEO metadata.
  * `POST /api/v1/admin/blog` — Admin article creation/modification.
* **User Preferences:**
  * `GET /api/v1/user/preferences` — Load persistent layout, theme, and language.
  * `PUT /api/v1/user/preferences` — Update persistent choices.

---

## 3. Product Layer Analysis
To support enterprise productization without altering the frozen intelligence engine, we isolate the enterprise metadata from the cognitive memories:

### PostgreSQL Relational Schema Blueprints:
1. **Users Table:**
   - `id` (UUID, Primary Key)
   - `email` (String, Unique)
   - `password_hash` (String, BCrypt)
   - `role_id` (Integer, Foreign Key)
   - `created_at` (Timestamp)
2. **Roles Table (RBAC):**
   - `id` (Integer, Primary Key)
   - `name` (String, Unique: SuperAdmin, Admin, Researcher, User, Guest)
3. **User Preferences Table:**
   - `user_id` (UUID, Foreign Key)
   - `language` (String: fa, en, ar, tr)
   - `theme` (String: light, dark, custom)
4. **Blog Articles Table:**
   - `id` (UUID, Primary Key)
   - `slug` (String, Unique)
   - `title_json` (JSON dictionary for multilingual titles)
   - `content_json` (JSON dictionary for multilingual Markdown)
   - `category` (String)
   - `tags` (JSON String Array)
   - `seo_meta` (JSON Object)
   - `created_at` (Timestamp)
5. **System Audit Logs Table:**
   - `id` (UUID, Primary Key)
   - `user_id` (UUID, Nullable)
   - `action` (String)
   - `details` (String)
   - `timestamp` (Timestamp)

### Redis Session Storage:
- Session IDs mapped to user IDs with a secure 15-minute sliding TTL.
- Output response cache for `/v1/dashboard/overview` and general static catalog lookups.

---

## 4. Intelligence Boundary Verification
We audited the path from MetaTrader 5 (MT5) rates to research execution and confirm timeframe independence:
* **Current Flow:**
  - Raw H1 XAUUSD rates are pulled from `MetaTrader5Provider` via `ResearchRuntime`.
  - The rates are mapped into standardized `CandleRecord` objects inside `src/Data/Providers/MT5/mt5.py`.
  - The candles are aggregated into sequence observations by `ObservationBrain` inside `src/Research/Brain/observation.py`, producing sequential patterns.
  - The similarity engines utilize the sequence mathematical abstractions (Price, Time, Run, Reaction) rather than depending on any MT5 native or coupled timeframe variables.
* **Boundary Validation:** The decoupled, read-only design guarantees that no direct coupling exists between the MT5 connection stream and cognitive pattern learning models.

---

## 5. Audit Summary
The baseline architecture is extremely resilient. The implementation of Phase 1 to Phase 9 will proceed immediately inside the dedicated `feature/v3.2-productization` branch. All existing Pytest validation suites must remain 100% green at all times.
