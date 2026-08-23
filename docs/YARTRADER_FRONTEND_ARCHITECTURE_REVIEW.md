# YarTrader Frontend Architecture Review v1.0

**Date:** August 23, 2026
**Author:** Jules — Lead Systems & Frontend Engineer
**Scope:** Evaluation of directory structure, API layer abstraction, state management, responsive breakpoints, and RTL layout rules.

---

## 1. Modular Directory Architecture

The recommended directory structure organizes the frontend into clean, decoupled domain features:

```
src/
├── components/          # Reusable UI Primitives (shadcn/ui based)
├── design-system/       # 17 Institutional Design System components
├── features/            # Feature domains (auth, terminal, execution, fractal, regime, risk, demo, shadow, learning, admin, saas, support)
├── layouts/             # PublicLayout, AuthLayout, TerminalLayout, AdminLayout
├── hooks/               # Custom hooks (useAuth, useWebSocket, useSignals, useTheme)
├── services/            # API client adapters (api.js, websocket.js)
├── stores/              # Reactive Zustand stores (useAuthStore, useMarketStore, useAdminStore)
└── types/               # TypeScript interfaces
```

---

## 2. API Layer & State Management Strategy

* **API Layer Separation:** UI components do not make direct `fetch()` calls. All network requests route through domain service clients wrapping `apiService` in `src/services/api.js`.
* **State Management:**
  * **Server State:** Handled via **TanStack Query (React Query)** with caching, revalidation, and background polling.
  * **Client State:** Managed via **Zustand** stores (`useAuthStore`, `useMarketStore`, `useAdminStore`).

---

## 3. Responsive Breakpoints & RTL Layout Enforcement

* **Desktop ($> 1280\text{px}$):** 3-column / 4-column widget grid.
* **Tablet ($768\text{px} - 1279\text{px}$):** 2-column layout, collapsible sidebar navigation.
* **Mobile ($< 768\text{px}$):** Single column stack, sticky header ticker, slide-over drawer navigation.
* **RTL Enforcement:** Automatically toggles `document.body.dir = 'rtl'` and applies Persian font family (`Vazirmatn`) when language is set to `fa` or `ar`.

---

*Architecture Review certified by Jules — Lead Systems & Frontend Engineer.*
*YarTrader Autonomous Financial Intelligence Platform.*
