# 06 - Master Audit Protocol & Verification Standards

## Master One-Pass Forensic Audit Requirements
Before approving PRs or issuing release verdicts, the following forensic steps must be completed:

1. **Source-Proof Modification Mandate**:
   - Verification requires actual modified git source diffs in target production files (e.g. `market_session_engine.py`, `mt5_adapter.py`, `session_execution_manager.py`, `research_worker.py`).
   - Passing test counts or documentation updates alone do not constitute completion.

2. **Automated Test Suite Verification**:
   - Run complete test suite using `/home/jules/.local/bin/pytest`.
   - Verify 100% test pass rate across unit, integration, and risk test modules without skipping core safety gates.

3. **Frontend Production Build Verification**:
   - Compile production SPA bundle: `cd trader-terminal && bun install && bun run build`.
   - Verify zero compilation errors and validate bundle generation in `trader-terminal/dist`.

4. **Release Validation Gate**:
   - Execute `python3 validate_release.py`.
   - Verify fail-closed compliance checks, zero P1 security vetoes, and readiness score calculation.
