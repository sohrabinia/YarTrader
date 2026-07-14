# Architecture Decisions

1. **Decoupled Agent Isolation**: Sequential agent message routing enforces that individual agent failures or timeouts degrade the system gracefully without halting core pipeline runs.
2. **Simulation-Only Bound**: Trading, broker execution, and account changes are completely forbidden and blocked by design.
3. **Immutability of Context**: Contexts such as `DecisionIntelligenceContext` are frozen to ensure historical evidence cannot be mutated mid-execution.
