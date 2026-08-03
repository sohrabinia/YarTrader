# component-inventory.md

## Frontend Component Inventory & Spec Compliance

This inventory documents all core UI components of the TradeYar AI frontend, ensuring alignment with APES-FIN standards and non-execution safety.

### 1. Shared Components

#### `SystemStatus`
- **Purpose**: Displays standard system statuses.
- **Spec Compliance**: Restricts status strings to exactly: `ONLINE`, `OFFLINE`, `WARNING`, `RISK_HIGH`, `AI_THINKING`, `EXECUTION_BLOCKED`. Custom labeling or status coloring is strictly forbidden in subclasses/views.
- **Safety Gate**: Implements a read-only render check.

#### `TelemetryCard`
- **Purpose**: Interactive Neon SRE performance telemetries (latency, memory usage, worker queue states).
- **Spec Compliance**: Connects to the passive `/api/v1/health` endpoint.

---

### 2. Trader Terminal Components

#### `ShadowTradingPanel`
- **Purpose**: Renders real-time floating position metrics (floating PnL, MAE, MFE, exit reasons).
- **Spec Compliance**: Only maps and displays virtual shadow order states. Strictly contains no code paths to active brokers or trade placing hooks.

#### `AISupportWidget`
- **Purpose**: Collapsible assistant/chatbot rendering semantic bilingual answers for the customer.
- **Spec Compliance**: Completely decoupled from any trade operations; read-only query mode.
