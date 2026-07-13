# 08. Decision Engine

## 1. Decision Logic & Flow
The `DecisionEngine` synthesizes multi-factor insights (Research, Strategy, Risk) to produce explainable decision reports without generating trading triggers.

```text
DecisionIntelligenceContext
        │
        ▼
Validation (structure & missing fields check)
        │
        ▼
Analyzer (completeness ratio, confidence limits)
        │
        ▼
Quality Scoring (evidence weight, consistency, reliability)
        │
        ▼
Conflict Resolution (disagreement detection & resolution)
        │
        ▼
Evidence Collection (preserves source records trail)
        │
        ▼
Decision Report Compilation (Approved, Rejected, ReviewRequired, NoAction)
```

---

## 2. Sub-services

### DecisionContextBuilder
Normalizes research report findings, strategy assessments, and risk limits into unified, audited contexts.

### DecisionAnalyzer
Checks completeness ratios, determines research-to-strategy alignments, and audits risk compliance bounds.

### DecisionQualityEvaluator
Scores overall suitability, evidence depth, alignment consistency, and confidence stability.

### DecisionConflictResolver
Identifies discrepancies (such as bullish sentiment vs. risk rejections) and logs resolution strategies.

### DecisionEvidenceCollector
Assembles comprehensive, unmodifiable trace links to source agents.

---

## 3. Cross References
*   [03_DOMAIN_MODEL.md](03_DOMAIN_MODEL.md)
*   [04_INTELLIGENCE_PIPELINE.md](04_INTELLIGENCE_PIPELINE.md)
*   [07_KNOWLEDGE_PLATFORM.md](07_KNOWLEDGE_PLATFORM.md)
