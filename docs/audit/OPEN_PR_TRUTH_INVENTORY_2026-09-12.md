# OPEN PR TRUTH INVENTORY — 2026-09-12

## 1. Audit Metadata

* **Audit Timestamp:** 2026-09-12T00:00:00Z
* **Repository:** `sohrabinia/YarTrader`
* **Base Branch:** `main`
* **Methodology:** Authoritative inspection via GitHub REST API (`https://api.github.com/repos/sohrabinia/YarTrader/pulls`) and Git commit history.
* **Authoritative Source Used:** GitHub REST API v3 live endpoints at audit time.

---

## 2. Current Open PR Inventory

| PR | Title | State | Draft | Head Branch | Head SHA | Base | Commits | + | - | Files | Created | Updated |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **#257** | feat(operator): implement production YarTraderOperatorAdapter and Admin API endpoints | open | False | `jules-10129482222596577148-002b897c` | `d4eda1c63cc86afe980f30f4099f4ce59365dbe8` | `main` | 1 | +412 | -10 | 4 | 2026-09-11T21:51:12Z | 2026-09-11T21:51:14Z |
| **#256** | Align login UI with Google OIDC single-provider model | open | False | `jules-17489445818683930448-f7ae0fc8` | `b3cd3c9cf591033052b69d3a21b913f88170c064` | `main` | 3 | +97 | -64 | 2 | 2026-09-11T20:52:36Z | 2026-09-11T21:21:07Z |
| **#255** | Integrate YarOperator Production Runtime into YarTrader Admin (/fa/admin/operator) | open | False | `jules-yartrader-yaroperator-integration-13311785683836370628` | `5f3c97734c917ac45843bd3b5f88c2dba0b0de5f` | `main` | 1 | +314 | -15 | 4 | 2026-09-11T15:09:35Z | 2026-09-11T15:09:37Z |
| **#253** | Controlled P1 Remediation Batch | open | False | `jules-10581156351122027744-de410dd3` | `39e0b6144c720916d708d9e5319b559153c3655d` | `main` | 6 | +805 | -196 | 22 | 2026-09-10T17:25:33Z | 2026-09-11T05:32:11Z |

---

## 3. Per-PR Commit Inventory

### PR #257: feat(operator): implement production YarTraderOperatorAdapter and Admin API endpoints

* **Total Commits:** 1
* **Commit List:**
  1. `d4eda1c63cc86afe980f30f4099f4ce59365dbe8` — `feat(operator): implement production YarTraderOperatorAdapter and Admin API endpoints`
     * **Stats:** +412 / -10
     * **Subsystem Classifications:**
       * `src/Application/Services/operator_adapter.py` — `operator integration`, `backend API`
       * `src/Application/Services/web_dashboard.py` — `admin`, `authorization / guards`, `backend API`
       * `tests/YarTrader.Tests/Services/test_operator_adapter.py` — `tests`
       * `trader-terminal/src/views/AdminView.jsx` — `admin`, `frontend`

### PR #256: Align login UI with Google OIDC single-provider model

* **Total Commits:** 3
* **Commit List:**
  1. `8edefe0f5fdbcd13eb76f59a772c6522bc64383f` — `feat(auth): align login UI with Google OIDC single-provider model`
     * **Stats:** +19 / -47
     * **Subsystem Classifications:**
       * `src/Application/Services/web_dashboard.py` — `auth`, `backend API`
       * `trader-terminal/src/App.jsx` — `auth`, `frontend`
  2. `0eb9bbba35000da65cb1c79b8028fe919202b2bb` — `feat(admin): enable full routing and SPA rendering for /admin/operator subpaths`
     * **Stats:** +6 / -5
     * **Subsystem Classifications:**
       * `src/Application/Services/web_dashboard.py` — `admin/operator routing`, `backend API`
       * `trader-terminal/src/App.jsx` — `admin/operator routing`, `frontend`
  3. `b3cd3c9cf591033052b69d3a21b913f88170c064` — `feat(chat): enable interactive chat assistant operational tasks and operator routing`
     * **Stats:** +72 / -12
     * **Subsystem Classifications:**
       * `src/Application/Services/web_dashboard.py` — `chat assistant`, `operator integration`, `backend API`
       * `trader-terminal/src/App.jsx` — `chat assistant`, `admin/operator routing`, `frontend`

### PR #255: Integrate YarOperator Production Runtime into YarTrader Admin (/fa/admin/operator)

* **Total Commits:** 1
* **Commit List:**
  1. `5f3c97734c917ac45843bd3b5f88c2dba0b0de5f` — `feat(admin): Integrate YarOperator production runtime into YarTrader Admin (/fa/admin/operator)`
     * **Stats:** +314 / -15
     * **Subsystem Classifications:**
       * `src/Application/Services/admin_api_router.py` — `operator integration`, `admin`, `authorization / guards`
       * `src/Application/Services/web_dashboard.py` — `admin`, `backend API`
       * `tests/YarTrader.Tests/Integration/test_operator_integration.py` — `tests`
       * `trader-terminal/src/App.jsx` — `admin/operator routing`, `frontend`

### PR #253: Controlled P1 Remediation Batch

* **Total Commits:** 6
* **Commit List:**
  1. `c106b80fa354372df979231bcf5545d0a7557b59` — `fix(security): complete controlled P1 remediation batch`
     * **Stats:** +611 / -191
     * **Subsystem Classifications:**
       * `README.md` — `docs / architecture`
       * `src/Application/Dashboard/auth_service.py` — `auth`
       * `src/Application/Services/admin_api_router.py` — `authorization / guards`, `admin`
       * `src/Application/Services/web_dashboard.py` — `auth`, `authorization / guards`, `backend API`
       * `src/Execution/Adapters/mt5_adapter.py` — `trading / execution`
       * `src/Infrastructure/Configuration/environment.py` — `auth`, `CI / deployment / release`
       * `src/Risk/Services/prop_challenge_engine.py` — `prop trading`
       * `tests/YarTrader.Tests/*` (10 test files) — `tests`
       * `validate_release.py` — `CI / deployment / release`, `tests`
  2. `a0730bf5d33671c4c3254f035f7c37068d4394ac` — `test(execution): isolate autonomous demo runtime from live MT5`
     * **Stats:** +4 / -3
     * **Subsystem Classifications:**
       * `scripts/run_autonomous_demo_runtime.py` — `trading / execution`
       * `src/Execution/Services/trade_journal.py` — `trading / execution`
  3. `f7e3eac02b3e0bbcd0d7a066a03022242d7b02f2` — `test(execution): isolate autonomous demo runtime from live MT5`
     * **Stats:** +73 / -0
     * **Subsystem Classifications:**
       * `tests/YarTrader.Tests/Execution/test_master_task_autonomous_demo_learning.py` — `tests`
       * `validate_release.py` — `CI / deployment / release`
  4. `92a933ed93849e85a044c6a9b6b0704f0cd11e4a` — `test(execution): isolate autonomous demo runtime from live MT5`
     * **Stats:** +0 / -0
     * **Subsystem Classifications:**
       * No files changed (empty commit)
  5. `d444dce9ca8e9baca880cbf82196141af6ca7095` — `fix(release): RELEASE-STABILIZATION-01 deterministic runtime identity and P1 remediation`
     * **Stats:** +48 / -2
     * **Subsystem Classifications:**
       * `app/workers/service.py` — `CI / deployment / release`
       * `validate_release.py` — `CI / deployment / release`
  6. `39e0b6144c720916d708d9e5319b559153c3655d` — `fix(release): prevent validator false-negative timeout`
     * **Stats:** +71 / -2
     * **Subsystem Classifications:**
       * `tests/YarTrader.Tests/Runtime/test_release_validator_timeout.py` — `tests`
       * `validate_release.py` — `CI / deployment / release`

---

## 4. Title-vs-Content Scope Audit

### PR #257: feat(operator): implement production YarTraderOperatorAdapter and Admin API endpoints
* **Stated Scope:** Implement production `YarTraderOperatorAdapter` gateway and Admin API endpoints.
* **Scope Assessment:** **IN SCOPE**
* **Mismatches:** None. All modified files (`operator_adapter.py`, `web_dashboard.py`, `test_operator_adapter.py`, `AdminView.jsx`) pertain directly to `YarTraderOperatorAdapter` and Admin API endpoints.

### PR #256: Align login UI with Google OIDC single-provider model
* **Stated Scope:** "Align login UI with Google OIDC single-provider model" (updates login views in `App.jsx` and `web_dashboard.py`).
* **Scope Assessment:** **SCOPE MISMATCH**
* **Mismatches Recorded:**
  1. **Commit SHA:** `0eb9bbba35000da65cb1c79b8028fe919202b2bb`
     * **Commit Message:** `feat(admin): enable full routing and SPA rendering for /admin/operator subpaths`
     * **Exact Files Touched:** `src/Application/Services/web_dashboard.py`, `trader-terminal/src/App.jsx`
     * **What it actually implements:** Adds `@app.api_route("/admin/{path:path}")` route decorator in `web_dashboard.py` and updates `App.jsx` route guards to use prefix matching (`routePath.startsWith('/admin')`) for Admin SRE Operational Control Center subpath rendering.
     * **Why not reasonably implied:** The PR title and description are explicitly focused on aligning the login card UI with Google OIDC. Enabling catch-all admin subpath routing for `/admin/operator` in the SPA is an unrelated admin infrastructure feature.
  2. **Commit SHA:** `b3cd3c9cf591033052b69d3a21b913f88170c064`
     * **Commit Message:** `feat(chat): enable interactive chat assistant operational tasks and operator routing`
     * **Exact Files Touched:** `src/Application/Services/web_dashboard.py`, `trader-terminal/src/App.jsx`
     * **What it actually implements:** Implements interactive operational task parsing/execution inside `POST /api/chat/assistant` in `web_dashboard.py` and interactive prompt chip UI handlers / navigation in `App.jsx`.
     * **Why not reasonably implied:** Interactive chat assistant task routing and navigation to operator views are unrelated to the stated PR scope of login UI Google OIDC alignment.

### PR #255: Integrate YarOperator Production Runtime into YarTrader Admin (/fa/admin/operator)
* **Stated Scope:** Integrate YarOperator production runtime into YarTrader Admin (`/fa/admin/operator`).
* **Scope Assessment:** **IN SCOPE**
* **Mismatches:** None. All modified files (`admin_api_router.py`, `web_dashboard.py`, `test_operator_integration.py`, `App.jsx`) pertain directly to YarOperator runtime integration into Admin.

### PR #253: Controlled P1 Remediation Batch
* **Stated Scope:** Controlled P1 remediation batch addressing security, authorization transport, execution volume invariant, prop account lockdown, release validator hardening, and documentation truth.
* **Scope Assessment:** **IN SCOPE**
* **Mismatches:** None. All 6 commits address security bugs, authorization guards, execution isolation, prop challenge lockdown, and release validator stability, which are explicitly part of the declared P1 batch.

---

## 5. Cross-PR File Overlap Matrix

The following matrix documents exact files modified across multiple open PRs:

| File Path | PR A | PR B | Nature of Overlap | Classification |
|---|---|---|---|---|
| `src/Application/Services/web_dashboard.py` | **#253** | **#255** | #253 adds CSP headers & P1 security guards; #255 adds `import admin_api_router` | Behavioral & Structural |
| `src/Application/Services/web_dashboard.py` | **#253** | **#256** | #253 modifies auth/admin logic; #256 modifies login endpoints, `/admin/{path:path}` route, and chat assistant | Behavioral & Structural |
| `src/Application/Services/web_dashboard.py` | **#253** | **#257** | #253 modifies admin auth guards; #257 adds `/api/admin/operator/*` REST endpoints | Behavioral & Structural |
| `src/Application/Services/web_dashboard.py` | **#255** | **#256** | #255 mounts admin operator routes; #256 adds `/admin/{path:path}` catch-all route decorator and chat task routing | Structural & Behavioral |
| `src/Application/Services/web_dashboard.py` | **#255** | **#257** | Both add Operator REST endpoints and routing in `web_dashboard.py` | Structural & Behavioral |
| `src/Application/Services/web_dashboard.py` | **#256** | **#257** | #256 routes chat operational tasks to operator; #257 adds operator status/task endpoints | Behavioral & Structural |
| `trader-terminal/src/App.jsx` | **#255** | **#256** | #255 adds `/fa/admin/operator` view rendering; #256 modifies login card UI, route guard prefix matching, and chat task prompts | Behavioral & Structural |
| `src/Application/Services/admin_api_router.py` | **#253** | **#255** | #253 hardens Bearer token auth in admin router; #255 adds YarOperator proxy endpoints to admin router | Behavioral & Structural |

---

## 6. High-Risk Feature Overlap

### 1. `src/Application/Services/web_dashboard.py` (4-Way Overlap)
* **Affected PRs:** #253, #255, #256, #257
* **Exact Affected File:** `src/Application/Services/web_dashboard.py`
* **Concise Evidence:**
  * **#253:** Adds CSP middleware, `check_admin_guard` updates, login/logout session handling, and authentication hardening.
  * **#255:** Adds `import src.Application.Services.admin_api_router`.
  * **#256:** Replaces login UI handling, adds `@app.api_route("/admin/{path:path}")` catch-all route decorator, and modifies `POST /api/chat/assistant` for operational task routing.
  * **#257:** Adds `YarTraderOperatorAdapter` API endpoints (`GET /api/admin/operator/status`, `GET/POST /api/admin/operator/tasks`, etc.) guarded by `check_admin_guard`.
* **Fact vs Inference:**
  * **FACT:** All four PRs contain git diffs modifying `src/Application/Services/web_dashboard.py`.
  * **INFERENCE:** Merging any one PR will create merge conflicts or overwrite route/security changes in the others unless reconciled on a single branch.

### 2. `trader-terminal/src/App.jsx` (2-Way Overlap)
* **Affected PRs:** #255, #256
* **Exact Affected File:** `trader-terminal/src/App.jsx`
* **Concise Evidence:**
  * **#255:** Modifies `App.jsx` (+62/-15 lines) to add `/fa/admin/operator` sub-view rendering and navigation link in the shell.
  * **#256:** Modifies `App.jsx` (+24/-34 lines) to simplify login UI to Google OIDC, add `routePath.startsWith('/admin')` prefix route-guard check, and inject chat task prompt chips.
* **Fact vs Inference:**
  * **FACT:** Both #255 and #256 modify route matching and component rendering in `App.jsx`.
  * **INFERENCE:** #256's route guard prefix check (`routePath.startsWith('/admin')`) is structurally coupled to #255's `/fa/admin/operator` route rendering, creating a implicit dependency between PRs.

### 3. `src/Application/Services/admin_api_router.py` (2-Way Overlap)
* **Affected PRs:** #253, #255
* **Exact Affected File:** `src/Application/Services/admin_api_router.py`
* **Concise Evidence:**
  * **#253:** Modifies `admin_api_router.py` (+60/-38 lines) enforcing Bearer auth header verification on admin endpoints.
  * **#255:** Creates/modifies `admin_api_router.py` (+117/-0 lines) adding YarOperator proxy endpoints.
* **Fact vs Inference:**
  * **FACT:** Both PRs modify authorization and routing in `admin_api_router.py`.
  * **INFERENCE:** If #255 is merged without #253's Bearer auth hardening, YarOperator endpoints in `admin_api_router.py` may lack enforced Bearer authorization checks.

---

## 7. Architectural Decision Required

The following open PRs represent major architectural choices or system boundary changes and require explicit repository-owner / CTO decision:

### 1. PR #255 (`Integrate YarOperator Production Runtime into YarTrader Admin`)
* **Flag:** **DECISION REQUIRED**
* **Concrete Trigger:** Introduces direct runtime integration between YarTrader and external `YarOperator`/`YarTrader.Operator` within `admin_api_router.py`, adding `/fa/admin/operator` UI surface in `App.jsx`. Shifts system boundary by embedding operator proxy logic into `admin_api_router.py`.

### 2. PR #256 (`Align login UI with Google OIDC single-provider model`)
* **Flag:** **DECISION REQUIRED**
* **Concrete Trigger:** Introduces wildcard routing `@app.api_route("/admin/{path:path}")` in `web_dashboard.py`, changes frontend route-guard logic in `App.jsx` (`routePath.startsWith('/admin')`), and expands `POST /api/chat/assistant` to execute interactive operational tasks.

### 3. PR #257 (`feat(operator): implement production YarTraderOperatorAdapter and Admin API endpoints`)
* **Flag:** **DECISION REQUIRED**
* **Concrete Trigger:** Establishes a formal server-side adapter pattern (`YarTraderOperatorAdapter` in `operator_adapter.py`) to connect YarTrader Admin to external `YarTrader.Operator` runtime with Google OIDC identity propagation, status tracking (`Created`, `Planned`, `Running`, etc.), and offline fail-closed mechanics (503 status).

---

## 8. PR Dependency / Conflict Relationships

* **#255 vs #257 (Architectural Conflict & Duplicate Implementation):**
  * Both PR #255 and PR #257 attempt to solve Operator integration for `/admin/operator`.
  * **PR #255** puts operator endpoints directly in `admin_api_router.py` and views in `App.jsx`.
  * **PR #257** abstracts operator interaction into `src/Application/Services/operator_adapter.py`, adds API endpoints in `web_dashboard.py`, and updates `AdminView.jsx`.
  * **Relationship:** Competing architectural approaches. Merging both independently would create redundant endpoints, conflicting route handlers, and duplicate state logic.
* **#255 vs #256 (Functional Overlap & Routing Dependency):**
  * PR #256 commit `0eb9bbb` adds route prefix matching `routePath.startsWith('/admin')` in `App.jsx` and `@app.api_route("/admin/{path:path}")` in `web_dashboard.py`.
  * PR #255 adds `/fa/admin/operator` view rendering in `App.jsx`.
  * **Relationship:** PR #255 depends on PR #256's route guard prefix logic to properly render subpaths like `/fa/admin/operator` without falling back to home route.
* **#253 vs (#255, #256, #257) (Security Invariant & Structural Lockout):**
  * PR #253 contains security remediations for authentication (`auth_service.py`), authorization headers (`admin_api_router.py`), CSP headers, and MT5 demo execution isolation.
  * PRs #255, #256, and #257 modify `web_dashboard.py` and `admin_api_router.py` on pre-P1 base code.
  * **Relationship:** Merging #255, #256, or #257 before #253 risks omitting critical P1 security hardening. Merging #253 first will cause git merge conflicts in #255, #256, and #257.

---

## 9. Merge-Order Risk Observations

* **Highest-Risk PR:** **PR #255**
  * Reason: Directly embeds external runtime integration into `admin_api_router.py` without an adapter layer, collides with PR #257's adapter pattern, and lacks PR #253's security authorization updates.
* **Highest-Risk Overlap:** 4-way conflict in `src/Application/Services/web_dashboard.py` (PRs #253, #255, #256, #257) and 2-way conflict in `trader-terminal/src/App.jsx` (PRs #255, #256).
* **PRs that MUST NOT be independently merged:** All open PRs (**#253, #255, #256, #257**). None of these PRs can be merged cleanly or safely on its own directly to `main`.
* **PRs that appear narrow and isolated:** None. Every open PR touches core backend routing (`web_dashboard.py`), admin router (`admin_api_router.py`), or primary frontend app routing (`App.jsx`).

---

## 10. Final Inventory Summary

* **Total Open PR Count:** 4
* **Open PR Numbers:** #253, #255, #256, #257
* **Scope Mismatch Count:** 1 (PR #256 contains 2 commits with out-of-scope work: `0eb9bbb` and `b3cd3c9`)
* **Architecturally Significant PR Count:** 3 (#255, #256, #257)
* **Highest-Risk Overlap:** 4-way modification of `src/Application/Services/web_dashboard.py` across #253, #255, #256, and #257.
* **Highest-Risk PR:** PR #255
* **Implementation/Merge Recommendation:** **PAUSE ALL INDEPENDENT PR MERGES.** Do not merge #253, #255, #256, or #257 directly. A single unified reconciliation PR must be built on a fresh branch against `main` following architectural approval of the Operator adapter model (#257 over #255) and incorporating #253 security controls.
