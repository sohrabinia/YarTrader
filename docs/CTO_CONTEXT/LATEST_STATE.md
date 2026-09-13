# LATEST_STATE - CTO Hand-off & System Reality Summary

**Last Updated**: 2026-03-30
**Repository**: `sohrabinia/YarTrader`

---

## 1. Git & Revision State
* **Main Branch SHA**: `2c2926c`
* **Latest PR Merged**: PR #267 ("Google OIDC customer authentication exclusive integration")
* **Active Working Branch**: Documentation update for CTO Context Hand-off (`docs/CTO_CONTEXT/`)

---

## 2. Production Environment Facts
* **Domain**: `https://yartrader.com`
* **Production Host**: Windows Server 2022
* **NSSM Service Name**: `YarTrader Production Runtime Service`
* **Backend Runtime Port**: `8000` (`127.0.0.1`)
* **YarOperator Runtime Port**: `8080` (`127.0.0.1`)
* **Frontend SPA Build Target**: `trader-terminal/dist`

---

## 3. Active System Configuration
* **Customer Auth**: Exclusive Google OIDC (`/fa/login`, `/en/login`, etc.). Legacy customer password endpoints removed.
* **Admin Auth**: `/admin/operator` route & `/api/admin/operator` proxy with `Authorization: Bearer <token>`.
* **Execution Boundary**: XAUUSD Gold Backtest & Native MT5 DEMO Execution strictly (`LIVE_TRADING_ENABLED = False`).
* **Risk Limit**: 2.0% max account equity risk budget per trade, 8.0% Daily Loss Protection Kill-Switch (01:35 Iran local time baseline).

---

## 4. Immediate Next Operational Action
* **Production Service Env Verification**: Ensure `GOOGLE_CLIENT_ID` is present in Windows Server 2022 NSSM environment configuration.
* **Service Restart**: Restart `YarTrader Production Runtime Service` to apply PR #267 changes.
