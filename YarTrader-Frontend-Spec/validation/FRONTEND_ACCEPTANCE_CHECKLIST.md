# FRONTEND_ACCEPTANCE_CHECKLIST.md — Frontend Acceptance Checklist

This document defines the strict, non-negotiable quality and compliance checkgates required to approve and merge any frontend codebases or custom UI components.

---

## 🏁 Phase 1: Directory Structure & Artifact Compliance
- [ ] **Directory Integrity:** Check that all core files match the defined workspace map in `APPLICATION_STRUCTURE.md`.
- [ ] **Clean Git Hygiene:** Verify that no compiled frontend artifacts (`/dist`, `/out`, `.next/`) are tracked in Git. Exclude them via `.gitignore`.
- [ ] **Zero Secrets:** Audit all components to guarantee that no API keys, private credentials, or broker passwords are included. All dynamic configurations must be sourced from environment variables.

---

## 🎨 Phase 2: Design System & UX Verification
- [ ] **Color Mapping Compliance:** Verify that background, surface, card, and diagnostic status colors match the specifications in `COLORS.md` exactly.
- [ ] **Font Integration:** Ensure that `Vazirmatn` loads correctly and is set as the primary body font for Persian (`fa`) and Arabic (`ar`) configurations.
- [ ] **Tabular Numerals:** Confirm that price tickers and SRE telemetry screens use monospace styling (`tabular-nums`) to prevent shifting layouts.
- [ ] **Responsive Breakpoints:** Test the layout on mobile (375px), tablet (768px), and ultra-wide screens (1440px+). Confirm that columns compress or hide cleanly without overlapping content.

---

## 🎮 Phase 3: Demo Trading & Risk UI Verification
- [ ] **Demo Capital Initialization:** Confirm that the Demo Dashboard Account Overview widget initializes with exactly **1194 USD** starting balance on fetch.
- [ ] **Bilingual AI Explanation:** Check that the Trade History view displays detailed bilingual (English & Persian) explanation logs mapping the detected pattern, strategy, confidence score, and decision chain.
- [ ] **Learning Experience Logging:** Confirm that completed simulated trades log their corresponding structural lessons, classifying outcomes as `SUCCESS`, `FAILURE`, `LUCKY_WIN`, or `STRUCTURAL_ERROR`.
- [ ] **Dual Mode Risk Meters:** Confirm that risk telemetry cards render both Learning Validation Mode (10% daily risk limit = 119.40 USD max loss) and Production Simulation Mode (2% risk = 23.88 USD max loss) metrics cleanly.
- [ ] **Live Trading Perm-Block Check:** Audit client layouts and codebase. Verify that the UI strictly contains **ZERO** entry points, forms, inputs, toggles, or routes allowing active live trading configuration, real account keys, or production broker connection endpoints.

---

## 🔗 Phase 4: Live Connection & API Integrity
- [ ] **Bilingual Static Layouts:** Verify that the `#lang-select` component dynamically switches the entire layout between LTR and RTL directions with proper alignment.
- [ ] **API Endpoint Match:** Cross-check all frontend Axios/Fetch configurations against the contracts defined in `API_CONTRACTS.md`. Ensure no "mock" or invented endpoints are called in production.
- [ ] **WebSocket Reconnect & Jitter:** Test WebSocket connection severing. Verify that the client initiates the backoff algorithm with exponential delay intervals and random jitter according to `RECONNECT_POLICY.md`.
- [ ] **Daily Support Limit Checking:** Confirm that standard USER role support chatbot entries block submissions and prompt subscription upgrade flows when the daily query count reaches the limit (10 queries/day).

---

## 🚨 Phase 5: SRE & Observability Verification
- [ ] **Pulsating Live Statuses:** Verify that active worker statuses (`ResearchWorker`, `IntelligenceWorker`, `ShadowWorker`, and `DemoTradingWorker`) animate correctly in real-time.
- [ ] **Bilingual IIS Recovery Page:** Confirm that the custom `503.html` displays perfectly in both English and Persian when the downstream service port is unreachable.
- [ ] **Incident Rendering:** Test an active critical incident condition (e.g., disconnecting the MT5 feed). Verify that the SRE incident card renders instantly with glowing red borders and a double-check restart trigger button.
