# TradeYar AI Growth & Trust Architecture Specification

The autonomous growth layers are strictly decoupled from Core TradeYar modules. They operate exclusively as passive listeners or independent API endpoints, avoiding any side-effects on base node detectors or trading executions.

## Architectural Layers

1. **FastAPI Web Dashboard Router Layer**:
   Exposes `/api/growth/*` sub-router to serve content queues, compliance status, tracked performance metrics, and behavioral profiles.
2. **Modular Multi-Agent Core Layer**:
   Encapsulates independent python classes representing the different agents (`PerformanceValidationAgent`, `ContentIntelligenceAgent`, etc.) grouped inside `src/Growth/Agents/`.
3. **Core Memory Connector Layer**:
   Integrates with `MarketMemorySystem` via thread-safe write transactions, recording outcome error insights without learning loss.
