# TradeYar AI Growth & Trust Architecture Map

TradeYar AI's modular agent architecture sits cleanly on top of the Core TradeYar engine without altering the underlying read-only simulation layers or active memory modules.

```
                           ┌──────────────────────────┐
                           │     TradeYar Core        │
                           │ (Read-Only Integration)  │
                           └────────────┬─────────────┘
                                        │
                           ┌────────────▼─────────────┐
                           │ Orchestrator Agent Layer │
                           └────────────┬─────────────┘
                                        │
 ┌─────────────────────────────┼─────────────────────────────┬────────────────────────────┐
 │                             │                             │                            │
┌▼──────────────────────────┐ ┌▼──────────────────────────┐ ┌▼───────────────────────────┐ ┌▼──────────────────────────┐
│       Trust Layer         │ │    Intelligence Layer     │ │       Content Layer        │ │ Growth & Business Layer  │
│ - Performance Validation  │ │ - Daily Intelligence      │ │ - Content Intelligence     │ │ - User Intelligence      │
│ - Trust & Compliance      │ │ - Research Publisher      │ │ - SEO Intelligence         │ │ - Growth & Funnel Agent  │
│ - Security Review Agent   │ │ - News Intelligence       │ │ - Social Intelligence      │ │ - Distribution Agent     │
│ - Learning Feedback Loop  │ │                           │ │ - Human Approval Queue     │ │ - Cost & Monetization    │
└───────────────────────────┘ └─────────────────────────┘ └────────────────────────────┘ └──────────────────────────┘
```

## Modular Layering Blueprint

1. **Independent Agent Directory**:
   All new growth-related agents reside under `src/Growth/Agents/`. They are packaged cleanly to communicate using modular message payload standards.

2. **Integration via Non-Intrusive API Routers**:
   New API endpoints representing the capabilities of the autonomous growth and trust network are mounted as a modular sub-router (`/api/growth/*`) under the central single-page application router `src/Application/Services/web_dashboard.py`.

3. **Zero Core Modifications Rule**:
   The core intelligence pipeline of TradeYar (such as base node detection, market analysis, and risk management) is strictly preserved without any refactoring, avoiding any regression on core SRE behaviors.
