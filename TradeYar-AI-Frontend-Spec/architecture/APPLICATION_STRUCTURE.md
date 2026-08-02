# APPLICATION_STRUCTURE.md — Application Structure

This document outlines the standard folder and workspace layout expected for the TradeYar AI Frontend project. Implementing agents and engineers must maintain this exact physical structure.

## 🗂️ Workspace Layout (Recommended Next.js/React Structure)

```
/trader-terminal
├── public/                     # Static assets (images, logos, favicon)
│   └── locales/                # Bilingual / Quad-lingual localization JSONs
│       ├── en.json             # English Baseline
│       ├── fa.json             # Persian Localization
│       ├── tr.json             # Turkish Localization
│       └── ar.json             # Arabic Localization
│
├── src/
│   ├── assets/                 # CSS/SASS, global styles, font imports (Vazirmatn)
│   │   ├── globals.css
│   │   └── theme.css
│   │
│   ├── core/                   # Shared types, Constants, and Base configuration
│   │   ├── constants/
│   │   │   ├── timeframes.ts   # Core 8 timeframes: M1, M5, M15, H1, H4, D1, W1, MN1
│   │   │   └── limits.ts       # Max 30 symbol limit rule
│   │   ├── types/
│   │   │   ├── api.d.ts        # Typed API response structures
│   │   │   └── websocket.d.ts  # WebSocket schemas
│   │   └── config.ts           # Frontend environment overrides
│   │
│   ├── services/               # API Clients, WebSocket Connections, Auth
│   │   ├── api.ts              # Axios wrapper with PBKDF2 / Session Token interception
│   │   ├── auth.ts             # Auth persistence (ADMIN, USER, PRO, PREMIUM)
│   │   └── websocket.ts        # WS manager with reconnect policies & heartbeats
│   │
│   ├── store/                  # Client-side State Management (Zustand, Pinia, Redux)
│   │   ├── useAuthStore.ts     # User sessions and support usage metrics
│   │   ├── useTerminalStore.ts # Multi-timeframe ticker state and active symbol matrix
│   │   └── useSreStore.ts      # Active system health diagnostics and telemetry
│   │
│   ├── components/             # Reusable UI components
│   │   ├── common/             # Buttons, Modals, Forms, Tooltips, Toasts
│   │   ├── design-system/      # Cards, Skeletons, Status Badges, Neon Indicators
│   │   └── layouts/            # Base shells (PublicLayout, TerminalLayout, AdminLayout)
│   │
│   └── pages/                  # Router-based entry points matching the 3-shell system
│       ├── public/             # Marketing and public blogs
│       ├── terminal/           # Multi-timeframe trading interface, Virtual positions
│       └── admin/              # SRE Console, SCM service statuses, limits config
```

---

## 🏛️ Code Separation and File Naming Rules

1. **PascalCase for Components:** All visual component files must use PascalCase (e.g., `SignalCard.tsx`, `SreStatusBadge.tsx`).
2. **camelCase for Utilities:** Utility scripts and services must use camelCase (e.g., `authService.ts`, `websocketManager.ts`).
3. **Strict Separation of Concerns:** UI components must not execute raw API queries or WebSocket connection parameters directly. Instead, they must bind to Client Stores or Custom Hooks that abstract the data fetching layer.
4. **Independent Asset/Mock Scoping:** Assets or mock data used specifically for SRE offline validation must remain inside dedicated `/tests` or local files to prevent production bloat.
