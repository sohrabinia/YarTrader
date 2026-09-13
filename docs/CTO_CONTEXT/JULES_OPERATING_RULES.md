# JULES_OPERATING_RULES - Strategic Guidance for Agent Execution

## Primary Directives for Jules

### 1. No Scope Creep or New Phases
* Do NOT propose or initiate unrequested architecture overhauls, roadmap expansions, or new development phases.
* Fulfill the specific user task with laser focus.

### 2. Zero Mock / Synthetic Data in Production
* Production runtime paths in `web_dashboard.py`, `research_worker.py`, and `mt5_adapter.py` MUST query authoritative real data or broker adapters.
* Never insert default equity fallbacks ($10,000), synthetic candle generators, fake order fills, or mock status responses into production execution paths.
* Fail closed immediately with explicit degraded states (`NO_TRADE`, `UNAVAILABLE`, `DISCONNECTED`) when real data or broker adapters are offline.

### 3. Test Suite & Code Integrity
* NEVER delete, skip, or disable existing unit/integration tests to hide failures.
* If a test fails, diagnose the root cause in the source code or update test fixtures to align with canonical rules.
* All changes must preserve 100% test pass rates across existing test suites.

### 4. Verification & Source Diffs Required
* Every completion report or submission MUST provide concrete proof:
  1. Exact modified source file paths and diffs.
  2. Automated test execution results (`pytest` logs).
  3. Git SHA reference.

### 5. Production Safety First
* `LIVE_TRADING_ENABLED = False` MUST remain hard-locked across all adapters and safety gates.
* Real accounts (`is_real = True`) MUST be unconditionally rejected.
* Daily 8% loss limit and 2.0% max account risk ceiling MUST be strictly enforced.
