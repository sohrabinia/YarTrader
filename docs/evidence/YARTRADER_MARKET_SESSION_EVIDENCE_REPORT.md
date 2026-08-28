# YARTRADER — MARKET SESSION & BROKER TRADING CALENDAR ENGINE EVIDENCE REPORT

## Executive Summary
This report documents the implementation and verification of the canonical `MarketSessionEngine` and `BrokerTradingCalendar` subsystem for YarTrader.

## Subsystem Architecture
- **Location**: `src/Execution/Services/market_session_engine.py`
- **Data Models**: `SessionInterval`, `BrokerTradingCalendar`, `HolidayCalendar`, `SessionBoundaryEngine`, `TPFeasibilityAssessment`, `MarketSessionValidationResult`.
- **Authoritative Hierarchy**:
  1. Live Broker / MT5 Symbol Trading Sessions
  2. Broker-Specific Symbol Contract Specification
  3. Broker-Specific Holiday / Trading Schedule
  4. Official Exchange / Market Calendar
  5. Verified External Calendar
  6. ForexFactory Enrichment (Advisory 6th precedence)
  7. Generic Fallback (Fails closed as UNKNOWN)

## Multi-Session & Holiday Support
- Supports $N$ open/close intervals per calendar day (e.g. Saturday/Sunday Crypto multi-session schedules).
- Handles Forex DST boundaries and broker server timezone normalizations to UTC.
- Incorporates `HolidayCalendar` for Bank Holiday / Christmas / New Year closures.

## Pre-Entry Feasibility Gates
1. **Pre-Entry >120s Session Remaining Gate**:
   Calculates `remaining_session_seconds`. Rejects entries if remaining session time is $\le 121.0$ seconds (`INSUFFICIENT_SESSION_TIME`).
2. **Causal Pre-Entry TP-Time Feasibility Gate**:
   Estimates expected time to reach TP based on ATR and historical movement speed. Rejects entries if `estimated_tp_seconds <= 120.0s` (`TP_TIME_TOO_FAST_BELOW_MIN_HOLD_120S`) or `estimated_tp_seconds > remaining_session_seconds` (`TP_TIME_EXCEEDS_REMAINING_SESSION`).

## Integration & API Exposure
- Integrated into `SessionExecutionManager.evaluate_entry_permission()`.
- Exposed via REST endpoint GET `/api/market/session-status` in `src/Application/Services/web_dashboard.py`.
- Rendered in UI components `DashboardView.jsx` and `DemoView.jsx`.

## Verification Metrics
- **Unit Tests**: 8/8 tests passed in `tests/YarTrader.Tests/Execution/test_market_session_engine.py`.
- **Dashboard Tests**: 120/120 tests passed in `tests/YarTrader.Tests/Dashboard/test_dashboard.py`.
- **Execution Lifecycle Tests**: 10/10 tests passed in `tests/YarTrader.Tests/Execution/test_phase_c_execution_lifecycle.py`.
- **Frontend Build**: Vite production build completed cleanly in `trader-terminal`.
