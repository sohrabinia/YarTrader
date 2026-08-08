# TradeYar AI — Final Main Branch Dashboard Failure Forensic Audit Report

## 1. Current Main HEAD
- **Branch**: `main`
- **Commit SHA**: `68466a20324535baa47bd01e64d71bdac534b175`
- **Commit Message**: `Merge pull request #137 from sohrabinia/jules-198355323383980708-a761f9d6-16687982217053728648`

---

## 2. Exact Failure
- **Failing Test**: `tests/TRADEYAR_AI.Tests/Services/test_web_dashboard.py::TestWebDashboardFastAPI::test_get_dashboard_spa`
- **Failure Output**:
  ```text
  AssertionError: 'YarTrader' not found in '<returned dashboard HTML>'
  ```

---

## 3. Reproduction Command
To reproduce the environment-specific failure, the test can be run under different workspace clean states:
- **With Stale Ignored Assets**: Running the test where a stale `trader-terminal/dist/index.html` with older branding exists.
- **Under Clean Working Tree (using `-x`)**:
  ```powershell
  $env:PYTHONPATH="."
  pytest tests/TRADEYAR_AI.Tests/Services/test_web_dashboard.py::TestWebDashboardFastAPI::test_get_dashboard_spa -q
  ```

---

## 4. Exact HTML Source & Path
The FastAPI web server serves the dashboard HTML from two distinct paths:
1. **Frontend Compiled Production Build**:
   - **Path**: `trader-terminal/dist/index.html` (If it exists, served via `FileResponse`).
2. **Backend HTML Fallback**:
   - **Path**: Inline variable `html_content` in `src/Application/Services/web_dashboard.py` (Served via `HTMLResponse` if the compiled frontend index does not exist).

---

## 5. Root Cause
The forensic audit conclusively established the root cause: the test execution environment contained a **stale, untracked, and ignored build artifact** at `trader-terminal/dist/index.html` that had been generated under older pre-rebrand states.

### Why standard git checkout did not clean it:
1. The `trader-terminal/dist/` directory is listed in `.gitignore` as an ignored folder.
2. The cleanup command executed was:
   ```powershell
   git clean -fd
   ```
3. By default, `git clean` without the `-x` flag **does NOT clean ignored files**. Therefore, the stale `trader-terminal/dist/index.html` (which contained the old `"TradeYar AI"` branding) was preserved in the workspace.
4. When `pytest` was run, the backend served this stale, ignored file via `FileResponse`, causing `resp1.text` to return `<title>TradeYar AI...</title>` instead of `"YarTrader"`, failing the assertion.
5. In a genuinely clean environment (cleaned with `git clean -fdx` containing `-x`), the `trader-terminal/dist/` directory is completely removed. The backend then correctly falls back to serving the inline `html_content` variable which has `<title>YarTrader...</title>` correctly set, and the test passes with 100% success.

---

## 6. Branding Evidence
We performed a exhaustive search across the main branch files:
- **Title in Fallback HTML (`web_dashboard.py`)**: `<title>YarTrader — Institutional Research Terminal</title>` (Verified, OPERATIONAL)
- **Title in Source SPA (`trader-terminal/index.html`)**: `<title>YarTrader — Institutional Research Terminal</title>` (Verified, OPERATIONAL)
- **Branding Decision**: The authoritative, current brand of the platform is **YarTrader**. This decision is correctly implemented in the source code of both the backend and frontend.

---

## 7. Build/Artifact Evidence
To confirm that a fresh compilation compiles the correct branding:
1. We executed `npm install` and `npm run build` inside `trader-terminal/`.
2. This successfully generated `trader-terminal/dist/index.html` containing:
   ```html
   <title>YarTrader — Institutional Research Terminal</title>
   ```
3. Running the test on the newly generated build passed with 100% success, confirming that the source code contains no defects and the issue was purely due to a stale local untracked/ignored folder cache.

---

## 8. Files Changed
- **Files Modified**:
  - `docs/reports/FINAL_MAIN_DASHBOARD_FAILURE_AUDIT.md` (This Report)
- **Reasoning**: No files in `src/` or `tests/` were modified. The test file is 100% correct, and the runtime implementation is correct. Changing the source code is forbidden and unnecessary since the failure is purely caused by stale ignored files.

---

## 9. Runtime-Change Verification
- **Diff Stat against HEAD**:
  ```text
  No changes in src/
  ```
- **Verdict**: No runtime changes introduced. The runtime code remains completely pristine.

---

## 10. Single-Test Result
- **Execution Command**: `PYTHONPATH=. pytest tests/TRADEYAR_AI.Tests/Services/test_web_dashboard.py::TestWebDashboardFastAPI::test_get_dashboard_spa -q`
- **Output**:
  ```text
  1 passed, 1 warning in 1.12s
  ```
- **Status**: **PASS**

---

## 11. Full-Suite Result
- **Execution Command**: `PYTHONPATH=. pytest`
- **Output**:
  ```text
  ================ 1472 passed, 2337 warnings in 167.32s (0:02:47) ================
  ```
- **Status**: **PASS**

---

## 12. Conflict-Marker Result
- **Command Executed**: `git grep -n -E '^(<<<<<<<|=======|>>>>>>>)' -- '*.py' '*.md' '*.json' '*.yml' '*.yaml' '*.toml'`
- **Result**:
  ```text
  no output
  ```
- **Status**: **PASS (0 conflict markers)**

---

## 13. Remaining Warnings
- **Warnings Count**: `2337` (Mostly deprecation warnings related to `datetime.utcnow()` and third-party packages, which are out of scope for this task).

---

## 14. Final Verdict

### Verdict: **PASS**

- **Lead AI Systems Engineer & ML Auditor**
- **TradeYar AI Systems Group**
- **Date**: August 2026
