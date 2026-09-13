# 01 - Architectural Directives & Canonical Rules

## Mandatory Architectural Principles
1. **Decoupled Intelligence & Execution Authority**:
   - `Market Data -> Timeframe Context -> Brain / Market Intelligence -> BUY/SELL/NO_TRADE -> Risk Gate -> Execution Plan` (`decision_source = 'BRAIN'`).
   - Legacy strategy profiles and `StrategyOrchestrator` carry zero direct execution authority.
   - Dynamic allocation & position sizing strictly honor broker symbol metadata (`volume_min`, `volume_max`, `volume_step`).

2. **Causal Timeframe Isolation**:
   - Timeframes (M5, M15, H1, H4) operate with independent OHLC price vectors, unique `decision_cycle_id`, and distinct SHA256 `context_identity` hashes derived strictly from price vectors.
   - Timeframe context mutations in M5 do not alter H1 context identity.
   - Research endpoints (`/api/research/*`) strictly return requested timeframe data; cross-timeframe fallbacks are prohibited.

3. **Zero Synthetic Fallbacks in Production Paths**:
   - Real market endpoints in `web_dashboard.py` and `research_worker.py` query production candle providers (`fetch_production_market_candles`).
   - Synthetic candle generation (`generate_active_ohlcv_candles`) is strictly forbidden in production execution paths and restricted to unit test fixtures.
   - Offline or disconnected market data returns explicit degraded states (`NO_TRADE`, `UNAVAILABLE`, `DISCONNECTED`) with zero confidence (`confidence = 0.0`).

4. **Multi-Market Opportunity Cost Allocation**:
   - Implemented via `PortfolioRiskIntelligenceEngine.evaluate_opportunity_cost()`.
   - Trades are scored using: `Opportunity Score = Expected Net Return / (Capital-at-Risk * max(1, Holding Time Sec / 60))`.
   - Inferior candidates are rejected with `REJECTED_INFERIOR_OPPORTUNITY`.

5. **Position Holding & Exit Constraints**:
   - 120-second minimum holding period enforced before exit permission is granted.
   - End-Of-Day (EOD) position flattening ensures zero overnight position rollover (`OPEN_POSITIONS = 0`).
