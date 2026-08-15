# Components Inventory Specification

This document inventories the required reusable UI components, ensuring consistent visual representations of financial telemetry.

---

## 1. `MarketCard`
- **Purpose:** Renders ticker symbol pricing details.
- **Constraints:**
  - Standardizes raw timezone conversion.
  - Freezes prices and flags STALE if real-time feeds drop.
  - Never shows 0 or empty values.

## 2. `SymbolSelector`
- **Purpose:** Selection mechanism for selecting the 30 active symbols governed by backend configuration.
- **Constraints:**
  - Grouped by asset class.

## 3. `SignalPanel`
- **Purpose:** Interactive timeline of real-time intelligence events.
- **Constraints:**
  - Dynamically updates with new AI research events.
  - Strictly follows DOMAIN_UI_RULES.md (No buy/sell buttons on RESEARCH state signals).

## 4. `RiskPanel`
- **Purpose:** Displays risk boundaries and active exposure constraints.
- **Constraints:**
  - Exposes walk-forward chronological validations.

## 5. `AIExplanationBox`
- **Purpose:** High-contrast explanation UI for the core decision trace.
- **Constraints:**
  - Displays bilingual explanations matching human questions.

## 6. `SystemStatus`
- **Purpose:** Visual neon-glowing status cards for system operational state.
- **Constraints:**
  - Accepts ONLY standard status states (`ONLINE`, `OFFLINE`, `WARNING`, `RISK_HIGH`, `AI_THINKING`, `EXECUTION_BLOCKED`).
