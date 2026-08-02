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
- [ ] **Tabular Numerals:** Confirm that price tickers and SRE telemetry screens use monospace monospace styling (`tabular-nums`) to prevent shifting layouts.
- [ ] **Responsive Breakpoints:** Test the layout on mobile (375px), tablet (768px), and ultra-wide screens (1440px+). Confirm that columns compress or hide cleanly without overlapping content.

---

## 🔗 Phase 3: Live Connection & API Integrity
- [ ] **Bilingual Static Layouts:** Verify that the `#lang-select` component dynamically switches the entire layout between LTR and RTL directions with proper alignment.
- [ ] **API Endpoint Match:** Cross-check all frontend Axios/Fetch configurations against the contracts defined in `API_CONTRACTS.md`. Ensure no "mock" or invented endpoints are called in production.
- [ ] **WebSocket Reconnect & Jitter:** Test WebSocket connection severing. Verify that the client initiates the backoff algorithm with exponential delay intervals and random jitter according to `RECONNECT_POLICY.md`.
- [ ] **Daily Support Limit Checking:** Confirm that standard USER role support chatbot entries block submissions and prompt subscription upgrade flows when the daily query count reaches the limit (10 queries/day).

---

## 🚨 Phase 4: SRE & Observability Verification
- [ ] **Pulsating Live Statuses:** Verify that active worker statuses (`ResearchWorker`, `IntelligenceWorker`, `ShadowWorker`) animate correctly in real-time.
- [ ] **Bilingual IIS Recovery Page:** Confirm that the custom `503.html` displays perfectly in both English and Persian when the downstream service port is unreachable.
- [ ] **Incident Rendering:** Test an active critical incident condition (e.g., disconnecting the MT5 feed). Verify that the SRE incident card renders instantly with glowing red borders and a double-check restart trigger button.
