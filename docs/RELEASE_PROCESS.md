# RELEASE PROCESS
**Platform Release Engineering & Testing Checks**

To guarantee absolute safety, stability, and zero regressions on public updates, all deployments must proceed through this structured release process.

---

## 1. Local Pre-Release Checks
Before pushing any change to the production branch, the release engineer must run:

1. **Syntax & escape checks**:
   ```bash
   python -m compileall src/
   ```
2. **Pytest regression suites**:
   ```bash
   python -m pytest
   ```
   All 1,330+ tests must pass with 100% success rate.
3. **AST Non-trading Compliance Audit**:
   Verify that no active trading terms (e.g. `open_position`, `place_order`) are compiled in code blocks using `python validate_release.py`.

---

## 2. CI/CD Pipeline Verifications
Our GitHub Actions workflow `.github/workflows/ci.yml` is automatically triggered on every push or Pull Request to main or master:
- Builds the sandbox workspace.
- Runs standard dependency scans.
- Executes the pytest suite.
- Re-generates the visual Production Readiness Score inside `validation/production_acceptance_report.json`.

---

## 3. Rollback Procedures
If a live release triggers critical alarms (high server load, database write blocks, MT5 connection loss, auth loop drops):

1. **Halt active cycles**: Trigger emergency stop via `POST /api/control` (passing command `"stop"`).
2. **Revert changes**: Use git to checkout the previous stable baseline tag immediately:
   ```bash
   git checkout tags/v1.0.0-stable
   ```
3. **Restart service**: Auto-reboot the NSSM service or task container:
   ```cmd
   nssm restart TradeYarAI
   ```
4. **Audit logs**: Analyze `logs/errors.log` and `logs/security.log` to isolate root failure causes.
