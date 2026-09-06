# YARTRADER RELEASE IDENTITY MANIFEST

**Document ID:** YARTRADER-RELEASE-IDENTITY-001
**Status:** CANONICAL / AUTHORITATIVE SPECIFICATION
**Date:** September 6, 2026
**Repository:** `sohrabinia/YarTrader`

---

## 1. Purpose
This document establishes the single authoritative release identity model, version resolution rules, build traceability, artifact identity, and historical release mapping for the `sohrabinia/YarTrader` repository.

Phase 0 discovered multiple un-unified version strings across Git tags (`v1.0.0`, `v1.0.1-production-hardened`, `v2.0.0-stable`, `v3.1.0-hardened`), `trader-terminal/package.json` (`1.0.0`), UI HTML labels (`v7.0`), and `.env.production` comments (`v1.0`). Phase 2 unifies these under one deterministic, testable, and traceable release identity model.

---

## 2. Canonical Product Version Source
The canonical source of product version metadata in YarTrader is:

```text
src/Infrastructure/version.py
```

### Precedence Hierarchy for Version Resolution:
1. **Explicit Environment Override:** `APP_VERSION` or `YARTRADER_VERSION` environment variable (if explicitly set during container or deployment startup).
2. **Dynamic Git HEAD Resolution:** Subprocess `git rev-parse HEAD` or `GIT_COMMIT`/`COMMIT_SHA`/`YARTRADER_BUILD_SHA` environment resolution at runtime/build time for `commit_sha`.
3. **Configuration File:** `config/version.json` (defines baseline product version metadata).
4. **Fallback Default:** Version `'7.0.0'`, Commit `'UNKNOWN_COMMIT'` (Fallback when unconfigured; never masquerades as a fake Git commit SHA).

No UI component, HTML template, documentation file, or secondary service may independently fabricate a product release version.

---

## 3. Canonical Release Identity Model
YarTrader explicitly distinguishes the following 5 distinct identity components:

| Identity Field | Conceptual Meaning | Example Pattern | Source / Resolution |
| -------------- | ------------------ | --------------- | ------------------- |
| `product_version` | Semantic product release version | `7.0.0` | `src/Infrastructure/version.py` (`get_application_version_info()["version"]`) |
| `release_id` | Immutable release identifier string | `rel-{version}-{short_sha}` | Formatted as `rel-{product_version}-{commit_sha[:12]}` |
| `build_id` | Immutable build run identifier | `bld-{YYYYMMDD}-{short_sha}` | Formatted as `bld-{YYYYMMDD}-{commit_sha[:12]}` |
| `commit_sha` | Git source commit SHA-1 | `40-char-git-sha` | Resolved dynamically via `git rev-parse HEAD` or `GIT_COMMIT` env |
| `artifact_id` | Compiled artifact identifier | `art-yartrader-{version}-{short_sha}` | Traceable name for static frontend `dist/` or backend package |

---

## 4. Build Identity
Build identity (`build_id`) provides deterministic traceability from compiled assets to the build run.

* **Format:** `bld-{YYYYMMDD}-{commit_sha[:12]}`
* **Immutability:** Once a build process executes (e.g. `npm run build` or container compilation), `build_id` is stamped into build logs and metadata feeds.
* **Prohibition:** Mutable timestamps alone are forbidden as a standalone build identity. A build identity MUST include the source `commit_sha`.

---

## 5. Commit Identity
The source identity of every release is anchored by its immutable Git commit SHA-1.

* **Source:** Resolved dynamically via `_get_git_commit_sha()` in `src/Infrastructure/version.py` or injected via `GIT_COMMIT` / `COMMIT_SHA` environment variables.
* **Fallback Behavior:** Defaults to `'UNKNOWN_COMMIT'` when unconfigured. Stale historical SHA strings are strictly forbidden as hardcoded defaults.

---

## 6. Artifact Identity
Artifact identity (`artifact_id`) connects compiled physical outputs (e.g. `trader-terminal/dist/` bundle) to the exact build run and source commit.

* **Frontend Bundle Artifact:** `art-trader-terminal-{version}-{commit_sha[:12]}`
* **Backend Windows Service Artifact:** `art-yartrader-service-{version}-{commit_sha[:12]}`
* **Verification Rule:** Every production deployment script (`scripts/deploy_production.ps1`) must verify that the compiled frontend `dist/index.html` matches the `commit_sha` generated during the build step.

---

## 7. Runtime Exposure
Runtime release metadata is exposed via unified REST API endpoints:

1. **GET `/api/version`** (Primary Version Endpoint):
   ```json
   {
     "application": "YarTrader",
     "version": "7.0.0",
     "release_id": "rel-7.0.0-{short_sha}",
     "build_id": "bld-20260906-{short_sha}",
     "commit": "{40-char-dynamic-git-sha}",
     "artifact_id": "art-yartrader-7.0.0-{short_sha}",
     "environment": "production"
   }
   ```
2. **GET `/api/runtime/frontend-status`** (SRE Health Probe): Returns `version` and `commit` in payload DTO.

---

## 8. Frontend Consumption
* **Component Location:** `trader-terminal/src/App.jsx`
* **Consumption Rule:** On initialization, `App.jsx` executes an asynchronous fetch query to `apiService.get('/api/version')`.
* **State Management:** The returned `version` updates `appVersion` state, which is dynamically rendered in HTML headers and title tags (e.g. `Welcome to YarTrader v{appVersion}`).
* **Prohibition:** React components are forbidden from hardcoding production product version numbers in render functions.

---

## 9. CI/CD Propagation
GitHub Actions workflows (`.github/workflows/ci.yml` and `release.yml`) propagate release identity through environment variables:

```yaml
env:
  APP_VERSION: "7.0.0"
  GIT_COMMIT: ${{ github.sha }}
  YARTRADER_ENV: "production"
```

---

## 10. Docker / Deployment Propagation
For containerized or Windows Service deployments:
* Container images are tagged using both semantic version and short commit SHA:
  * `yartrader:7.0.0`
  * `yartrader:{short_sha}`
* PowerShell production deployment script `scripts/deploy_production.ps1` injects `APP_VERSION` and `GIT_COMMIT` into the service process environment prior to starting the `YarTrader` Windows service.

---

## 11. Historical Release Mapping Table

| Historical Tag | Commit SHA | Creator Date | Historical Meaning | Current Status |
| -------------- | ---------- | ------------ | ------------------ | -------------- |
| `v3.1.0-hardened` | `c76a2ab0e0e2fd83dfe770e89201f8d5b7f41c50` | Aug 1, 2026 | TradeYar AI v3.1 Hardened Enterprise Frozen Baseline Release | HISTORICAL TAG — PRESERVED |
| `v2.0.0-stable` | `2a8fe56001226b79d36fbe913668fe53fa79e96c` | Jul 31, 2026 | TradeYar AI V2 stable release | HISTORICAL TAG — PRESERVED |
| `v1.0.1-production-hardened` | `7a503ebe91782e609c502e2fbed6d0f3cfc801d4` | Aug 7, 2026 | YarTrader AI v1.0.1 Production Hardened Security Release | HISTORICAL TAG — PRESERVED |
| `v1.0.0-production-hardened` | `65f68d1d9044388675021b2f0cbf77e4bb543be1` | Aug 7, 2026 | YarTrader AI v1.0.0 Production Hardened | HISTORICAL TAG — PRESERVED |
| `v1.0.0` | `159372c42aa282947320c94afd223398ca5691e9` | Aug 3, 2026 | TradeYar AI v1.0 Production Release | HISTORICAL TAG — PRESERVED |
| `yartrader-v1.0.0-production` | `76e63970b7769fccf0ee775a6f818d80037f0641` | Aug 17, 2026 | Audit Merge Tag | HISTORICAL TAG — PRESERVED |
| `YarTrader-Gate3-MT5-DEMO-PASS` | `c8c009bec5620d9065ae093a4a1d8c1ddaf452a0` | Aug 24, 2026 | MT5 DEMO Verification Proof Tag | HISTORICAL TAG — PRESERVED |

*Note: Historical tags remain strictly preserved in Git history and are not deleted or overwritten.*

---

## 12. Version Sources Ownership Matrix

| Location | Discovered Value | Type | Canonical Owner | Action / Resolution |
| -------- | ---------------- | ---- | --------------- | ------------------- |
| `src/Infrastructure/version.py` | `7.0.0` | Python Version Module | Canonical Release Authority | **CANONICAL OWNER IDENTIFIED** — Unified release resolution engine |
| `config/version.json` | `7.0.0` | JSON Config | Version Config File | **CANONICAL CONFIG** — Stores baseline version |
| `trader-terminal/package.json` | `1.0.0` | Frontend npm package | Frontend Package Manager | **PACKAGE VERSION ONLY** — Represents npm package version; product version consumed from `/api/version` |
| `src/Application/Dashboard/content_manager.py` | `YarTrader v7.0` | Content Manager Text | Public Blog & News Feed | **DYNAMICIZED** — Replaced hardcoded strings with `get_current_version_string()` |
| `src/Application/Services/web_dashboard.py` | `Welcome to YarTrader v7.0` | HTML Header String | Web Dashboard Gateway | **DYNAMICIZED** — Replaced hardcoded strings with API version resolution |
| `.env.production` | `v1.0` | Environment Comment | Deployment Template | **STALE COMMENT** — Preserved comment for env docs; real version from `version.py` |

---

## 13. Version Contradictions Resolution Table

| Contradiction | Source A | Source B | Resolution | Target Phase |
| ------------- | -------- | -------- | ---------- | ------------ |
| App Version Discrepancy | Git Tag `v3.1.0-hardened` | UI HTML `v7.0` | `src/Infrastructure/version.py` is the single canonical release authority; UI consumes API version dynamically | Phase 2 (Completed) |
| Package vs Product Version | `package.json` (`1.0.0`) | `version.py` (`7.0.0`) | `package.json` represents npm frontend module version; `version.py` represents overall YarTrader product release version | Phase 2 (Completed) |
| Content Manager Hardcoded String | `content_manager.py` (`v7.0`) | Runtime Version Module | `content_manager.py` references `get_current_version_string()` dynamically | Phase 2 (Completed) |

---

## 14. Forbidden Version Sources
1. **No UI-Invented Versions:** React components, JSX templates, or HTML views cannot hardcode product version strings.
2. **No Independent API Router Versions:** Subservice routers cannot declare competing version numbers.
3. **No Deployment-Invented Versions:** Deployment scripts must consume version metadata from `src/Infrastructure/version.py` or `.env.production`.
4. **No Standalone Timestamp Versions:** Timestamps alone without a source Git commit SHA cannot serve as build or release identifiers.

---

## 15. Release Invariants
1. `src/Infrastructure/version.py` is the single canonical product version source of truth.
2. `product_version`, `release_id`, `build_id`, `commit_sha`, and `artifact_id` are explicitly distinguished.
3. Every release ID and build ID MUST incorporate the source Git commit SHA.
4. Historical Git tags are preserved and never deleted or overwritten.
5. The React SPA frontend consumes version metadata dynamically from `/api/version`.
6. Missing Git or environment version data falls back safely to `config/version.json` without failing runtime execution or fabricating fake commit SHAs.

---

## 16. Validation Rules & Test Verification
The release identity model is verified by automated unit tests in `tests/YarTrader.Tests/Services/test_dynamic_version.py`:

```bash
python3 -m pytest tests/YarTrader.Tests/Services/test_dynamic_version.py
```

Required assertions:
* `get_application_version_info()` returns strongly-typed dictionary containing `version`, `release_id`, `build_id`, `commit`, `artifact_id`, and `environment`.
* `get_current_version_string()` returns a valid non-empty version string.
* `GET /api/version` returns HTTP 200 with complete release identity metadata.

---

## 17. Phase 2 Completion Verdict

```text
PHASE 2 = PASS
```

**Reasoning:** One canonical release identity model has been established and documented in `docs/release/YARTRADER_RELEASE_IDENTITY.md`. Version resolution logic in `src/Infrastructure/version.py` was harmonized to dynamically expose `product_version`, `release_id`, `build_id`, `commit_sha`, and `artifact_id` without hardcoding stale commit SHA defaults. Unit tests in `tests/YarTrader.Tests/Services/test_dynamic_version.py` pass cleanly, all historical tags are mapped, and zero feature/unrelated code changes were introduced.
