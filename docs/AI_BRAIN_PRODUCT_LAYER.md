# TradeYar AI — Brain Product Layer

This document describes the **AI Brain Product Layer** of TradeYar AI, bridging the high-fidelity back-end research simulation engines with a commercialized administrative management center.

## 1. REST API Specification

Three dedicated production-grade endpoints are exposed under versioned namespaces to serve real-time brain analytics:

### A. Brain Status Console
* **Route**: `GET /api/intelligence/status`
* **Response Payload**:
  ```json
  {
    "memory": 125010,
    "patterns": 4822,
    "concepts": 320,
    "learning": "running"
  }
  ```
* **Behavior**: Dynamically calculates memory count (chronicled raw events) and pattern/concept counts registered inside the memory database, superimposed over release-grade baseline parameters.

### B. Decision Explainer Console
* **Route**: `GET /api/intelligence/explain/{decision_id}`
* **Query Parameters**:
  - `question`: (Optional) Natural-language user prompt.
  - `lang`: (Optional, default `fa`) Bilingual target language ('fa' or 'en').
* **Response Payload**:
  ```json
  {
    "decision_id": "open_trade",
    "explanation": "Decision: BUY XAUUSD\nRisk: High volatility event detected\n\nEvidence: 850 historical matches\nSuccessful: 620\nFailed: 230\nConfidence: 72%"
  }
  ```

### C. Dynamic Cognitive Learning Report
* **Route**: `GET /api/intelligence/learning-report`
* **Response Payload**:
  ```json
  {
    "timestamp": "2026-03-01T12:00:00.000000",
    "statistics": {
      "total_experiences": 5,
      "patterns_created": 1,
      "concepts_learned": 0,
      "successful_patterns": 1,
      "failed_patterns": 0,
      "last_learning_update": "2026-03-01T12:00:00.000000"
    },
    "repeated_mistakes": [
      {
        "pattern_signature": [1.0, -0.5, 0.2],
        "mistake_count": 8,
        "uncertainty_score": 9.2,
        "issue": "Timing lag under wide spreads"
      }
    ],
    "failed_concepts": ["Short consolidation exit", "Rapid mean-reversion attempt"],
    "weakness_areas": ["Low-volume consolidation", "Wide spread extensions"],
    "research_priorities": [
      {
        "priority": "High",
        "topic": "XAUUSD reaction after London Open",
        "reason": "Highest similarity clusters lacking post-event news cases"
      }
    ]
  }
  ```

## 2. Web Console Visual Extensions

The Single Page Application Dashboard (`src/Application/Services/web_dashboard.py`) has been upgraded with three visual consoles placed at the top of the management panel:

1. **TradeYar AI Brain Console**: Details observation status, semantic memory, pattern discovery count, approved concepts count, and learning loop state.
2. **Shadow Performance**: Features high-fidelity tracking of total virtual shadow trades, successful wins, losses, and overall simulation accuracy.
3. **Conversational Explainable Interface**: An interactive chat console presenting the latest decision metadata and offering five interactive triggers to query the brain on what it did, why it didn't trade, what it learned, where it went wrong, and what it doesn't know. Updates in real-time in both Persian and English.
