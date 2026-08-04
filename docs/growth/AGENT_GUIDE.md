# TradeYar AI Growth Agent Operational Guide

This document acts as an operation manual for developers and SREs to understand the standard triggers, inputs, and outputs of all growth agents.

## Operational Definitions

### 1. PerformanceValidationAgent
- **Trigger**: Upon closure of any virtual shadow trade.
- **Inputs**: Asset price levels (entry, exit, stop loss, take profit), direction, confidence, and outcome.
- **Outputs**: Dictionary record including specific calculation formulas, metrics, and exact source stream tracking IDs.

### 2. DailyIntelligenceAgent
- **Trigger**: Scheduled cron daily polling.
- **Inputs**: Recent multi-timeframe non-linear market signature metrics.
- **Outputs**: Multilingual descriptive briefs with high-fidelity disclaimer copies.

### 3. ContentIntelligenceAgent
- **Trigger**: Generated daily brief or deep report publishing.
- **Inputs**: Raw report dictionaries and desired distribution targets.
- **Outputs**: Channel-formatted posts stored to `PENDING_APPROVAL` queue.

### 4. TrustComplianceAgent
- **Trigger**: Pre-submission scan on any content generation.
- **Inputs**: Generated copy text string.
- **Outputs**: Boolean `is_compliant` flag alongside an array of rule-violation explanation notices.
