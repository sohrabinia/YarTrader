# 05 - Current Blockers & Operational Hand-off

## Active Runtime Dependencies & Issues

1. **Google Client ID Configuration in Production**:
   - PR #267 enforced Google OIDC as the exclusive customer login method.
   - **Action Required**: Verify `GOOGLE_CLIENT_ID` environment variable is set in NSSM environment block on the Windows Server 2022 host before restarting `YarTrader Production Runtime Service`.

2. **Isolated Sandbox E2E Reachability Protocol**:
   - In isolated sandbox/testing environments where `YAROPERATOR_RUNTIME_URL` (`http://127.0.0.1:8080`) is offline or unreachable:
   - YarTrader adapter endpoint (`/api/admin/operator`) fails closed with HTTP 503 (`status = 'UNAVAILABLE'`).
   - Fabrication of mock server responses or looping code changes is strictly prohibited per CTO Directive. E2E tests are marked `FINAL CTO DECISION: ENVIRONMENT-BLOCKED`.

3. **PR Merge Authority**:
   - Automated workflows and AI agents are strictly prohibited from performing git merge operations into `main`.
   - All PR merges are subject to human CTO review and manual sign-off.
