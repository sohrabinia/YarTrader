# TradeYar AI Growth & Trust Data Flow Map

The autonomous growth platform relies on a trace-driven, mathematically validated data stream passing from the Core MT5 Market Data providers down through the trust validation layers, content publishing pipeline, and user behavioral feedback modules.

```
┌─────────────────────┐       ┌──────────────────────┐
│  MT5 Data Provider  ├──────►│ Performance Agent    │◄───── Real Market Tick Streams
└─────────────────────┘       └──────────┬───────────┘
                                         │ Matches and audits decisions
                                         ▼
┌─────────────────────┐       ┌──────────────────────┐
│   Memory System     ├──────►│ Daily Intel Agent    │◄───── Non-Linear Market Signatures
└─────────────────────┘       └──────────┬───────────┘
                                         │ Compiles daily briefs
                                         ▼
                              ┌──────────────────────┐
                              │  Publisher Agent     ├─────► Generates Reports (D, W, M)
                              └──────────┬───────────┘
                                         │
                                         ▼
                              ┌──────────────────────┐
                              │  Content Intel Agent │◄───── Triggers Multi-Channel Media Items
                              └──────────┬───────────┘
                                         │
                                         ▼
                              ┌──────────────────────┐
                              │ Trust Compliance Gate│◄───── Scans copy and blocks signals / advice
                              └──────────┬───────────┘
                                         │
                                         ▼
                              ┌──────────────────────┐
                              │ Human Approval Queue ├─────► Release & Publish Content
                              └──────────────────────┘
```

## Stream Telemetry and Auditable Points
- **Traceable Metric Fields**:
  Every calculated statistic contains `Asset`, `Timestamp`, `Market Condition`, `Entry`, `Exit`, `Stop Loss`, `Confidence`, and `Reasoning`.
- **Learning Feedback Stream**:
  Discrepancies in actual outcomes vs predicted targets are routed to the `MarketFeedbackLearningAgent` which triggers updates on the Core `MarketMemorySystem` database files.
