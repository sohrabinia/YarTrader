# TRADEYAR_DEBUG_AUDIT_REPORT.md

## TradeYar AI — Debug & Recovery Audit Report (Phase A)

### 1. Claimed vs Verified Status

| Component / Claim | Claimed State | Verified Real State | Verification Method | Gap / Status |
|---|---|---|---|---|
| **Platform Test Suite** | 1,437 tests passing | **1,437 / 1,437 passed** | AST analysis + `pytest` runs | **100% Valid**. Real assertion blocks. |
| **Runtime Data Isolation**| Clean repository | **Dirty repository prior to fix** | `git status` check | **Resolved**. Ignored dynamic folders. |
| **Real MT5 Feed** | Production integration | **Real integration exists** | Inspected `mt5.py` and mocks | **100% Valid**. High timezone fallback. |
| **Bases & Nodes** | Stored mathematically | **Stored in JSON under runtime_logs**| Read `PredictiveShadowEngine.py` | **100% Valid**. Stored with ID and metrics. |
| **Memory Layers** | Raw -> Concept promotion | **Exists in `memory.py`** | Read `memory.py` and `cognitive_loop.py` | **100% Valid**. Standardized promotion. |
| **Decision Trace** | High-fidelity persistence | **Partial representation** | Read `models.py` | **Minor Gap**. Need native risk/unknowns fields. |
| **Replay Engine** | Playback simulation | **Candle-based replay with protection**| Inspected `replay.py` | **100% Valid**. Future leakage protection. |
| **Frontend Rules** | Strict passive spec | **Specifications exist and are valid**| Checked `DOMAIN_UI_RULES.md` | **100% Valid**. Restricted UI execution. |

### 2. Working Capabilities
- **AST Security compliance scanner**: Correctly rejects forbidden imports and keyword executions.
- **Dynamic MT5 timezone mapping & Mock Fallback**: Ensures offline testing succeeds perfectly.
- **Cognitive Replay Loop**: Step-by-step historical playback, future leakage protection, and pattern promotion.
- **Emergency Recovery System**: Atomic memory swapping with corruption backup and snap restore.
- **SymbolRuntimeManager**: Handles 150+ concurrent partitioned symbol engines.

### 3. Broken / Incomplete Capabilities
- **Workspace Pollution**: Runtime data and test logs were previously tracked by git, making the workspace dirty on execution. (Fixed in Step A2).
- **SimulatedDecision Attribute Completeness**: Risk, Confidence, and Unknowns are stored inside generic context dicts rather than as first-class, typed dataclass attributes.

### 4. Bugs Found
- **Dynamic File Pollution**: The test suite execution generated/renamed dynamic files inside `runtime_logs/` and `test_timeframe_logs/` which contaminated `git status`.

### 5. Fixes Applied
- **Workspace Ignored**: Configured comprehensive ignores in `.gitignore` for `runtime_logs/`, `test_timeframe_logs/`, and `TRADEYAR_FINAL_INTELLIGENCE_VALIDATION_REPORT.txt` and purged them from the git index cache.

### 6. Open Risks
- **Data corruption risk**: If the machine suddenly shuts down during a JSON write, data could corrupt. However, this is largely mitigated by the atomic temp-swap writing pattern and automatic snapshot recovery implemented in `memory.py`.

### 7. Recommended Build Order
1. Standardize memory architecture layer promotion in `memory.py`.
2. Add full memory promotion pipeline tests.
3. Enhance base, touch, and node path detection.
4. Mandate SimulatedDecision persistence of all evidence, reasoning, risk, confidence, and unknown factors.
5. Upgrade replay to explicitly model Market State transitions.
6. Create `frontend-audit/` with inventory files.
7. Build passive Agent Orchestrator foundation.
8. Build experience learning pipeline.
9. Implement Self Directed Development Loop (SDDL) sandboxed foundation.
