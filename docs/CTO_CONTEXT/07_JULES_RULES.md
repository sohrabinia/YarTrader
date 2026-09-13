# 07 - Jules Operating Rules & Execution Constraints

## Operational Guidelines for AI Engineer (Jules)

1. **No Scope Creep or Roadmap Expansion**:
   - Focus exclusively on assigned tasks. Do not introduce unrequested features, roadmap expansions, or new architectural phases.

2. **Zero Mock/Synthetic Data Policy in Production**:
   - Never inject fake financial facts, mocked broker responses, synthetic candles, or fallback equity figures into production runtime paths.

3. **Source Code Integrity**:
   - Do not delete existing tests to achieve passing status. Address root causes in source code or update test assertions to reflect explicit domain contracts.
   - Always verify changes using read-only tools (`read_file`, `list_files`) before marking steps complete.

4. **Git & PR Governance**:
   - Never execute `git merge` into `main`.
   - Submit clean, targeted feature branches with descriptive commit messages.
   - Provide concrete proof: modified file diffs, test run logs, and exact commit SHAs.

5. **Production Safety Primacy**:
   - Maintain hard-locked `LIVE_TRADING_ENABLED = False`.
   - Enforce fail-closed error handling on missing configuration, disconnected adapters, or invalid account metrics.
