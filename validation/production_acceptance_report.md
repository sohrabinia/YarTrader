# YarTrader — Release Verification Acceptance Report

## Overall Status: Historical / Superseded — Not Release Evidence
- **Timestamp:** 2026-09-27 23:54:47
- **Ready Score:** Historical snapshot — superseded
- **Status note:** This artifact is a historical workspace snapshot and is not evidence for the current release candidate. Current acceptance must use exact-HEAD CI plus runtime/production evidence.

---

## 1. Environment Verification Summary
| Subsystem Check | Status | Details |
| :--- | :--- | :--- |
| Python Environment | PASSED | Target is Python >= 3.10 |
| Virtual Environment Isolation | WARNING | Running globally |
| Storage Availability | PASSED | Available Disk Space: 94692.6 MB |
| Package Dependencies | PASSED | All dependencies verified |
| MetaTrader 5 Link | SIMULATED_FALLBACK | Synthetic Fallback Mode Active (Non-Windows platform) |

---

## 2. Platform Tests discovered & executed
- **Total Tests Discovered:** 1960
- **Passed Count:** 1931
- **Failed Count:** 29
- **Skipped:** 0
- **Duration:** 288.57 seconds

### Recent Failed Investigations
- **Test File/Name:** `testplannerrejectsstructurewithrrbelowminimum`
  - **Subsystem:** Core (Unknown)
  - **Severity:** CRITICAL
  - **Root Cause:** Missing Import or module path misconfiguration
  - **Probable Fix:** Verify PYTHONPATH configuration or add missing project packages.

- **Test File/Name:** `TestMarketSessionEngine.testpreentry120sthresholdboundarymatrix`
  - **Subsystem:** Core (Unknown)
  - **Severity:** HIGH
  - **Root Cause:** Verification assertion failed
  - **Probable Fix:** Check class parameters and types.

- **Test File/Name:** `TestMarketSessionEngine.testcryptosaturdaymultipleintervals`
  - **Subsystem:** Core (Unknown)
  - **Severity:** HIGH
  - **Root Cause:** Verification assertion failed
  - **Probable Fix:** Check class parameters and types.

- **Test File/Name:** `TestMarketSessionEngine.testpreentrytptimefeasibilitymatrix`
  - **Subsystem:** Core (Unknown)
  - **Severity:** HIGH
  - **Root Cause:** Verification assertion failed
  - **Probable Fix:** Check class parameters and types.

- **Test File/Name:** `TestMarketSessionEngine.testsessionexecutionmanagerintegration`
  - **Subsystem:** Core (Unknown)
  - **Severity:** HIGH
  - **Root Cause:** Assertion mismatch
  - **Probable Fix:** Check class parameters and types.

- **Test File/Name:** `TestGate1BrainIntegration.testcausalbrainproposaldataflow`
  - **Subsystem:** Core (Unknown)
  - **Severity:** HIGH
  - **Root Cause:** Verification assertion failed
  - **Probable Fix:** Check class parameters and types.

- **Test File/Name:** `TestMultiTimeframeExecutionPlans.test02consecutivebuybuyplans`
  - **Subsystem:** Core (Unknown)
  - **Severity:** HIGH
  - **Root Cause:** Verification assertion failed
  - **Probable Fix:** Check class parameters and types.

- **Test File/Name:** `TestMultiTimeframeExecutionPlans.test03consecutivesellsellplans`
  - **Subsystem:** Core (Unknown)
  - **Severity:** HIGH
  - **Root Cause:** Verification assertion failed
  - **Probable Fix:** Check class parameters and types.

- **Test File/Name:** `TestTradeYarRuntimeAndConfiguration.testenvironmentresolution`
  - **Subsystem:** Core (Unknown)
  - **Severity:** HIGH
  - **Root Cause:** Verification assertion failed
  - **Probable Fix:** Check class parameters and types.

- **Test File/Name:** `TestModernFeaturesIntegration.testchatbotassistantexplanations`
  - **Subsystem:** Research (Feature Extraction Engine)
  - **Severity:** HIGH
  - **Root Cause:** Verification assertion failed
  - **Probable Fix:** Check indicators registry, descriptive statistics, or patterns detector.

- **Test File/Name:** `TestProductionPlatformSaaS.testpublicsaasmetricsandpricing`
  - **Subsystem:** Core (Unknown)
  - **Severity:** CRITICAL
  - **Root Cause:** Missing Import or module path misconfiguration
  - **Probable Fix:** Verify PYTHONPATH configuration or add missing project packages.

- **Test File/Name:** `testlivemodezerobalanceblocked`
  - **Subsystem:** Core (Unknown)
  - **Severity:** HIGH
  - **Root Cause:** Assertion mismatch
  - **Probable Fix:** Check class parameters and types.

- **Test File/Name:** `testunknownmodefailsclosed`
  - **Subsystem:** Core (Unknown)
  - **Severity:** HIGH
  - **Root Cause:** Assertion mismatch
  - **Probable Fix:** Check class parameters and types.

- **Test File/Name:** `TestHierarchicalM5M15Trading.testapimultitimeframeendpoint`
  - **Subsystem:** Dashboard (Web Admin SPA & REST Service)
  - **Severity:** CRITICAL
  - **Root Cause:** Missing Import or module path misconfiguration
  - **Probable Fix:** Verify PYTHONPATH configuration or add missing project packages.

- **Test File/Name:** `TestConfigLoading.testenvoverride`
  - **Subsystem:** Core (Unknown)
  - **Severity:** HIGH
  - **Root Cause:** Verification assertion failed
  - **Probable Fix:** Check class parameters and types.

- **Test File/Name:** `TestConfigLoading.testinvalidconfidencethreshold`
  - **Subsystem:** Core (Unknown)
  - **Severity:** HIGH
  - **Root Cause:** Verification assertion failed
  - **Probable Fix:** Check class parameters and types.

- **Test File/Name:** `TestConfigLoading.testinvalidportvalidation`
  - **Subsystem:** Core (Unknown)
  - **Severity:** HIGH
  - **Root Cause:** Verification assertion failed
  - **Probable Fix:** Check class parameters and types.


---

## 3. Core Subsystems Compliance
| Core Domain Check | Status | Details |
| :--- | :--- | :--- |
| Runtime Lifecycle | PASSED | Launcher and thread-safe operational status verified healthy |
| Security & Forbidden Tokens Scan | PASSED | Security scan passed: Zero security leakages detected. |
| APES-FIN Passive Compliance Scan | PASSED | Conformity to 100% passive non-trading guidelines verified |
| REST API Schema Routing | PASSED | Validated endpoints schemas, authorizations and serialization scopes |
| Research Pipeline Feature Extraction | PASSED | Indicator calculators pipeline compiled successfully with 0 features. |
| Platform Processing Latency | PASSED | Internal execution startup latency: 0.068 ms |

---

## 4. Release Golden Baseline Trends
- **Regression Check Status:** Regression Detected
- **Baselines Trend:** Acceptance score decreased slightly from 100.0% to 99.8% versus Golden Baseline.
