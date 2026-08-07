# YarTrader Frontend Migration Risk Register (v1.1.0)

This registry catalogs the critical architectural, security, and rendering risks identified during Phase 0 discovery, with corresponding mitigation strategies to ensure zero regressions across active services.

---

### Risk 1: API Contract Mismatch Risk
- **Description:** Differences between the backend JSON models (e.g., snake_case properties like `active_markets_count`, `registered_symbols`, and SRE health states) and frontend parsing keys could cause the UI layout to crash or show empty states.
- **Severity:** Critical
- **Probability:** Medium
- **Impact:** System indicators rendering blank charts or 0% readiness scores on the dashboard, breaking product delivery standards.
- **Mitigation Strategy:**
  - Enforce strict TypeScript/Zod DTO interfaces matching the exact backend response schemas (documented in `END_TO_END_INTEGRATION_MAP.md`).
  - Implement dynamic fallback checks in properties (such as `.registered_symbols || .active_symbols || []`) to preserve rendering capabilities.

---

### Risk 2: Routing Migration Risk
- **Description:** Navigating from the current ad-hoc browser hash routing to a centralized routing engine (such as React Router or Next.js layout structures) might disrupt active path parameters, layout states, or authentication redirect rules.
- **Severity:** High
- **Probability:** Low
- **Impact:** Infinite navigation redirect loops, unauthorized view exposures, or broken bookmarks.
- **Mitigation Strategy:**
  - Preserve standard fallback route targets for unknown requests.
  - Test all access guard rules (e.g. redirecting Guest/User/Admin privileges) inside a pre-production sandboxed router module before shipping.

---

### Risk 3: State Management Migration Risk
- **Description:** Transitioning from React Hooks stored solely in `App.jsx` to a decoupled global store (such as Zustand) could introduce data synchronization lag or component state mismatch.
- **Severity:** Medium
- **Probability:** Medium
- **Impact:** Out-of-sync selected assets, stale language state, or duplicate API data fetches.
- **Mitigation Strategy:**
  - Migrate state slices incrementally. First extract auth context (`useAuthStore`), then symbol selections (`useTerminalStore`), and finally SRE statuses.
  - Implement strict state mutation flows that are unidirectional and fully testable.

---

### Risk 4: Chart Library Integration Conflicts
- **Description:** Adding interactive trading charts (such as TradingView Lightweight Charts) might trigger styling conflicts, memory leaks during rapid socket pushes, or heavy initial bundle sizes.
- **Severity:** High
- **Probability:** Medium
- **Impact:** Sluggish layout execution, slow page loads, or browser freeze.
- **Mitigation Strategy:**
  - Leverage lightweight, open-source charting libraries specifically designed for pure price-action rendering.
  - Implement proper cleanup methods (`chart.remove()`) inside React lifecycle hooks to clear DOM Nodes and canvas references on component unmounts.

---

### Risk 5: Rendering Regressions (RTL Layout Shifts)
- **Description:** Switching dynamically between RTL (Persian, Arabic) and LTR (English, Turkish) layout directions can cause flashing, shifting containers, or visual alignment distortions.
- **Severity:** High
- **Probability:** Medium
- **Impact:** Disrupted grid displays, overlapping texts, and poor visual user experience in bilingual mode.
- **Mitigation Strategy:**
  - Avoid hard-coding absolute direction attributes. Use logical Tailwind properties (e.g. `start` and `end` instead of `left` and `right`).
  - Ensure numerical financial data, timestamps, and trend percentages preserve strict LTR orientation across all translations.

---

### Risk 6: Performance Regressions (High-Frequency WebSockets)
- **Description:** Feeding rapid tick streams (30 symbols x 9 timeframes) directly into Presentation components without throttling will overload the React render loop.
- **Severity:** High
- **Probability:** Medium
- **Impact:** UI lagging, frozen page interactions, and unresponsive chat interfaces.
- **Mitigation Strategy:**
  - Decouple the incoming WebSocket message handler from presentation states.
  - Throttle render state updates to a maximum frequency of 250ms intervals.
  - Apply `React.memo` on high-frequency tables and ticker cards.

---

### Risk 7: Search Engine Optimization (SEO) Impact
- **Description:** Transitioning public marketing views into an client-side rendered (CSR) app can decrease search discoverability on search engines that do not execute client-side JavaScript perfectly.
- **Severity:** Low
- **Probability:** Low
- **Impact:** Decreased search rankings and organic user acquisition.
- **Mitigation Strategy:**
  - Maintain simple, semantic HTML structures within the public landing shell.
  - Configure precise metadata tags inside the standard `index.html` file.

---

### Risk 8: Authentication Integrity & Lockouts
- **Description:** Local token expiration mismatches, unvalidated mock token fallbacks in production, or brute-force progressive delay penalties can lead to unauthorized access or lockouts.
- **Severity:** Critical
- **Probability:** Low
- **Impact:** Unauthorized admin privilege escalation, or valid users locked out from trading terminals.
- **Mitigation Strategy:**
  - Disable any testing admin credentials or bypass rules when `RG_ENV` or `TRADEYAR_ENV` is set to `production`.
  - Add explicit server-side authorization checks on all routes, treating frontend visibility controls as purely cosmetic.

---

### Risk 9: Dependency Governance and Conflicts
- **Description:** Adding unverified npm dependencies can introduce package vulnerabilities, lockfile discrepancies, or incompatible engine requirements.
- **Severity:** Medium
- **Probability:** Low
- **Impact:** Build breaks, deployment blockages, or third-party security vulnerabilities.
- **Mitigation Strategy:**
  - Enforce strict review policies for packages. Use audit scans before adopting new UI, utility, or logic dependencies.
  - Lock package versions exactly inside `package.json` to prevent unpredictable minor/patch updates.

---

### Risk 10: Real-Time Data Heartbeat & Stale States
- **Description:** Unannounced socket dropouts or offline states can leave old, stale pricing rates displayed on the screen as if they were current.
- **Severity:** Critical
- **Probability:** High
- **Impact:** Users making decisions on outdated prices, leading to inaccurate virtual position simulation.
- **Mitigation Strategy:**
  - Enforce a strict 25s ping-pong mechanism on the socket connection.
  - Change component states and apply visual grayscales to rate tickers if no packet is received for over 10 seconds.
