# YarTrader Frontend Design Priority Matrix v1.0

**Document Version:** 1.0.0
**Status:** Certified Priority Matrix
**Target Phase:** AI-Led Redesign & Component Rebuild Implementation

---

## 1. Executive Priority Summary

The redesign of the YarTrader frontend is prioritized based on trading decision impact, execution safety clarity, and core trader terminal usability.

---

## 2. Priority Tier Breakdown

### Tier P0 — Critical (Core Trader Terminal & Execution Safety)

| ID | Redesign Area | Route | Primary Objectives | Rationale |
| :--- | :--- | :--- | :--- | :--- |
| **P0-1** | Trader Terminal | `#/dashboard` | Above-the-fold horizon filter bar, high-visibility signal cards, responsive layout. | Primary daily workspace for financial intelligence. |
| **P0-2** | Execution Board | `#/execution-intel` | Institutional trade plans, price action structure maps, order block/FVG supply-demand zones. | Delivers actionable trade plans and portfolio risk management. |
| **P0-3** | Signal Hub | `#/signals` | Multi-category tabs (Live, Shadow, Backtest, Historical), complete signal details. | Core signal delivery stream. |
| **P0-4** | Live Safety Gate | `#/live` | Unambiguous SRE fail-closed alert banner, clear execution boundary warnings. | Prevents user confusion regarding live real-money trading status. |

---

### Tier P1 — High (Trading Shells & Intelligence)

| ID | Redesign Area | Route | Primary Objectives | Rationale |
| :--- | :--- | :--- | :--- | :--- |
| **P1-1** | MT5 Demo Operations | `#/demo` | Broker demo account scorecard (`Alpari-MT5-Demo` account `52961173`), broker order history. | Tracks real MT5 broker demo execution. |
| **P1-2** | Shadow Paper Trading | `#/shadow` | Virtual $1,000 paper capital manager, virtual position table. | Tracks cognitive paper execution without broker connections. |
| **P1-3** | Backtest Engine UI | `#/backtest` | Simulation parameter controls, point-in-time audit status board, backtest runs ledger. | Evaluates historical strategy performance. |
| **P1-4** | Pattern Memory Matrix | `#/learning` | Multi-timeframe pattern scoreboard, performance table, sample size $N$ evidence inspector. | Visualizes active pattern weight updates. |
| **P1-5** | Authentication Views | `#/login`, `#/register` | Fluid card layouts, field validation, social OAuth integration. | Core user onboarding gateway. |

---

### Tier P2 — Medium (SRE Admin & Subscription Monitization)

| ID | Redesign Area | Route | Primary Objectives | Rationale |
| :--- | :--- | :--- | :--- | :--- |
| **P2-1** | SRE Control Center | `#/admin` | Active symbol registration bar, SRE validation runner, readiness score badge, monospaced logs console. | Internal DevOps and platform health monitoring. |
| **P2-2** | Pricing & Plans | `#/pricing` | Subscription plan cards, feature checklist drawer/modal. | Subscription monetization presentation. |
| **P2-3** | Marketing Landing | `#/` | Editorial welcome card, platform performance metrics tiles, standards summary. | Public landing presentation. |

---

### Tier P3 — Cosmetic (Secondary Public Pages)

| ID | Redesign Area | Route | Primary Objectives | Rationale |
| :--- | :--- | :--- | :--- | :--- |
| **P3-1** | Cognitive Features | `#/features` | 4-card feature grid highlighting price action and 4-layered memory. | Secondary informational page. |
| **P3-2** | Research Blog | `#/blog` | Institutional research article grid, tag badges. | Secondary educational content. |
| **P3-3** | Forgot Password | `#/forgot-password` | Form layout alignment. | Secondary auth flow. |

---

## 3. Sequential Implementation Roadmap

```text
Phase 1: P0 Critical Screens (Dashboard, Execution Intel, Signals, Live Gate)
   ↓
Phase 2: P1 High Shells (MT5 Demo, Shadow Paper, Backtest, Learning, Login/Register)
   ↓
Phase 3: P2 Medium Controls (SRE Admin, Pricing, Marketing Landing)
   ↓
Phase 4: P3 Cosmetic Pages (Features, Blog, Forgot Password)
```
