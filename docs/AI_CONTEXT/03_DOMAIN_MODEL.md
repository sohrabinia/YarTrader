# 03. Domain Model

## 1. Core Domain Context
The domain model focuses entirely on modeling passive financial states, research observations, strategy suited scores, risk parameters, and analytical decision report structures.

---

## 2. Key Domain Entities & Value Objects

### Asset
Value object representing financial instruments (symbols and names).

### MarketData & CandleRecord
Value objects representing historical pricing data points (timestamp, open, high, low, close, volume).

### StrategyCandidate & StrategyScore
Entities representing candidate concepts with overall scores, confidence weights, and multi-criteria matrices.

### RiskProfile & PortfolioRisk
Value objects modeling risk tolerances, max leverage bounds, expected volatility, and historical drawdowns.

### DecisionReport & DecisionIntelligenceContext
Aggregates storing decision states (`Approved`, `Rejected`, `ReviewRequired`, `NoAction`), confidence scores, evidence trails, and conflict records.

---

## 3. Relationships & Decoupled Services

Domain aggregates interact passively through services:
*   `StrategyEvaluator`: Evaluates candidates against suitability parameters.
*   `RiskAnalyzer`: Audits proposed weights against risk profile parameters.
*   `DecisionEngine`: Evaluates contextual reports and resolves conflicting agent proposals.

No domain models are capable of triggering trades, as all actions are represented as passive states inside audited contexts.

---

## 4. Cross References
*   [04_INTELLIGENCE_PIPELINE.md](04_INTELLIGENCE_PIPELINE.md)
*   [08_DECISION_ENGINE.md](08_DECISION_ENGINE.md)
