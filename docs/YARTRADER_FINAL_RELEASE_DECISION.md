# YarTrader Final Release Decision

## Executive Release Verdict

```text
FINAL_RELEASE_DECISION = CONDITIONAL_RELEASE
```

---

## Release Conditions & Risk Boundaries

1. **Software & Website Platform:** **APPROVED FOR RELEASE**
   * All frontend SPA components, clean HTML5 localization routes (`/fa`, `/en`, `/tr`, `/ar`), technical SEO files (`sitemap.xml`, `robots.txt`), Prop Firm Challenge risk management engine, subscription receive wallet validator, financial admin APIs, and 1,684 automated test units are 100% verified and pass clean build and discovery execution.

2. **Scientific Trading Engine:** **BLOCKED FROM LIVE MONEY EXECUTION**
   * Multi-scale breakout strategy expectancy evaluates at **-$4.60/oz** (-$2,066.52 Net P&L across 449 Dukascopy M1 historical trades, 30.73% WR, 0.86 PF).
   * Standalone breakout trading is strictly blocked from live money execution (`SCIENTIFIC_TRADING_RELEASE = BLOCKED`).

3. **Production Host SRE Deployment Requirement:**
   * To serve the new localized routes on `https://yartrader.com`, the remote Windows Production server (`C:\Projects\YarTrader`) requires SRE execution of `git pull origin main`, `npm run build` inside `trader-terminal`, and `Restart-Service YarTrader` to reload Uvicorn process memory.

4. **Live Trading Safety Gate:**
   * `LIVE_TRADING_ENABLED = FALSE` remains strictly hard-locked repository-wide with `REAL_ORDERS = 0`.
