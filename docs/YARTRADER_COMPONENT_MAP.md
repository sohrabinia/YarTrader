# YarTrader Component Architecture & Reusability Map v1.0

**Date:** August 23, 2026
**Author:** Jules — Lead Systems & Frontend Engineer
**Scope:** Mapping existing UI elements to `shadcn/ui` primitives, Tailwind CSS design tokens, and modular feature locations (`src/components/ui`, `src/design-system`, `src/features/*`, `src/layouts/*`).

---

## 1. Directory Structure Architecture

```
src/
├── components/                # Reusable UI Primitives
│   ├── ui/                    # shadcn/ui components (button, card, dialog, table, badge, tabs, input, Command)
│   └── common/                # Header, Sidebar, NavigationMenu, ThemeToggle, GlobalToast, CommandPalette
├── design-system/             # 17 Institutional Design System Components
│   ├── MetricCard.jsx
│   ├── IntelligenceCard.jsx
│   ├── RiskCard.jsx
│   ├── DecisionCard.jsx
│   ├── ChartContainer.jsx
│   ├── StatusBadge.jsx
│   ├── ConfidenceBadge.jsx
│   ├── HealthIndicator.jsx
│   ├── TimelineStepper.jsx
│   ├── AuditTimeline.jsx
│   ├── DataTable.jsx
│   ├── FeatureToggle.jsx
│   ├── ConfigPanel.jsx
│   ├── EmptyState.jsx
│   ├── LoadingSkeleton.jsx
│   ├── ErrorState.jsx
│   └── PositionTimelineStepper.jsx
├── features/                  # Domain Feature Modules
│   ├── auth/                  # LoginForm, RegisterForm, ForgotPasswordForm, SessionManager
│   ├── terminal/              # SignalFeed, AssetSelector, HorizonTabs, CompoundingSim
│   ├── execution/             # FiveStageCascade, ExecutionBoard, ReasoningTrace, StructureMap, LiquidityGrid
│   ├── fractal/               # MultiScaleGraph, SimilarityOverlay, BaseDetection
│   ├── regime/                # RegimeGauge, TransitionHistory
│   ├── risk/                  # PortfolioHeat, ExposureChart, DrawdownLimits, EmergencyStopButton
│   ├── demo/                  # DemoOrderTable, AccountSummary, PnLMonitor
│   ├── shadow/                # VirtualPositionTable, CashEquityMonitor
│   ├── learning/              # PatternMatrix, Scoreboard, PatternDetailDrawer
│   ├── admin/                 # 17 Admin Subsections, LogStream, AuditViewer, SymbolManager
│   ├── saas/                  # PricingGrid, BillingManager, WalletLedger, CheckoutModal
│   └── support/               # TicketInbox, FloatingAIAssistant, CMSPublisher
├── layouts/                   # Layout Shell Containers
│   ├── PublicLayout.jsx       # Light editorial marketing shell
│   ├── AuthLayout.jsx         # Split-screen auth container
│   ├── TerminalLayout.jsx     # Dark institutional trading shell
│   └── AdminLayout.jsx        # SRE Control plane sidebar shell
├── hooks/                     # Custom React Hooks (useAuth, useWebSocket, useSignals, useTheme)
├── services/                  # API Client (api.js) & WebSocket Router (websocket.js)
└── stores/                    # Zustand Stores (useAuthStore, useMarketStore, useAdminStore)
```

---

## 2. Component Mapping Matrix

| Existing UI Element | Location in `App.jsx` | Reusability Action | Target Module & Component | shadcn/ui Base Component |
| :--- | :--- | :---: | :--- | :--- |
| **Primary Button** | `src/components/common/Button.jsx` | `REUSE` | `src/components/ui/button.jsx` | `Button` (Tailwind variant props) |
| **Global Header** | Header div (inline) | `REFACTOR` | `src/components/common/Header.jsx` | `NavigationMenu`, `Badge`, `Select` |
| **Sidebar Menu** | Sidebar div (inline) | `REFACTOR` | `src/components/common/Sidebar.jsx` | `@/components/ui/sidebar` |
| **Metric Cards** | `.status-board` grid (inline) | `REPLACE` | `src/design-system/MetricCard.jsx` | `Card`, `CardHeader`, `CardContent` |
| **Signal Cards** | `.blog-grid` feed (inline) | `REPLACE` | `src/design-system/IntelligenceCard.jsx` | `Card`, `Badge` |
| **Risk Heat Board** | Risk div (inline) | `REPLACE` | `src/design-system/RiskCard.jsx` | `Progress`, `Card` |
| **Advisory Plan** | Exec plans div (inline) | `REPLACE` | `src/design-system/DecisionCard.jsx` | `Card`, `Badge` |
| **Data Tables** | `table` elements (inline) | `REPLACE` | `src/design-system/DataTable.jsx` | `Table`, `TableHeader`, `TableRow`, `TableCell` |
| **Sub-nav Tabs** | `.sub-nav-tabs` div (inline) | `REPLACE` | `src/components/ui/tabs.jsx` | `Tabs`, `TabsList`, `TabsTrigger`, `TabsContent` |
| **Slide-over Drawer**| Detail div (inline) | `REPLACE` | `src/components/ui/sheet.jsx` | `Sheet`, `SheetContent`, `SheetHeader` |
| **Toast Alerts** | `.notification` div (inline) | `REPLACE` | `src/components/ui/toast.jsx` | `Toaster` (Sonner) |
| **AI Chatbot** | `#chat-widget` div (inline) | `REFACTOR` | `src/features/support/FloatingAIAssistant.jsx` | `Card`, `Input`, `Button` |
| **Command Search** | Admin search input (inline) | `ENHANCE` | `src/components/common/CommandPalette.jsx` | `Command`, `CommandInput`, `CommandList` |

---

*Component Map Specification certified by Jules — Lead Systems & Frontend Engineer.*
*YarTrader Autonomous Financial Intelligence Platform.*
