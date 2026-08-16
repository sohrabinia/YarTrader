# YARTRADER PRODUCT REALITY MATRIX

## Executive Summary
This document provides a comprehensive inventory and data provenance audit of all backend API endpoints across the YarTrader system.
Every endpoint has been evaluated for path existence, HTTP method support, unit/integration test coverage, frontend UI consumption, real runtime data status, and architectural classification.

---

## Endpoint Reality Matrix

| Endpoint Path | Method | Function / Module | Test Coverage | Frontend Consumed | Real Runtime Data? | Data Classification |
|---|---|---|---|---|---|---|
| `/` | `GET` | `get_dashboard_spa` | PASS | YES | YES | Runtime Data |
| `/admin` | `GET` | `get_dashboard_spa` | PASS | YES | YES | Runtime Data |
| `/api/admin/analytics/revenue` | `GET` | `get_admin_analytics_revenue` | PASS | YES | YES | Runtime Data |
| `/api/admin/backup` | `POST` | `trigger_backup` | PASS | YES | YES | Runtime Data |
| `/api/admin/billing/webhook` | `POST` | `handle_billing_webhook` | PASS | YES | YES | Runtime Data |
| `/api/admin/business/catalog` | `GET,POST` | `get_admin_business_catalog` | PASS | YES | YES | Runtime Data |
| `/api/admin/business/catalog/{product_id}` | `DELETE` | `delete_catalog_product` | PASS | YES | YES | Runtime Data |
| `/api/admin/judge` | `GET` | `get_admin_judge_panel` | PASS | YES | YES | Runtime Data |
| `/api/admin/ledger/reverse` | `POST` | `reverse_transaction` | PASS | YES | YES | Runtime Data |
| `/api/admin/ledger/transaction` | `POST` | `create_manual_transaction` | PASS | YES | YES | Runtime Data |
| `/api/admin/memory` | `GET` | `get_admin_memory_view` | PASS | YES | YES | Runtime Data |
| `/api/admin/patterns` | `GET` | `get_admin_patterns_view` | PASS | YES | YES | Runtime Data |
| `/api/admin/reports` | `GET` | `get_admin_reports` | PASS | YES | YES | Runtime Data |
| `/api/admin/restore` | `POST` | `trigger_restore` | PASS | YES | YES | Runtime Data |
| `/api/admin/shadow-trades` | `GET` | `get_admin_shadow_trades` | PASS | YES | YES | Runtime Data |
| `/api/admin/symbols` | `GET,POST` | `get_admin_symbols` | PASS | YES | YES | Runtime Data |
| `/api/admin/tickets` | `GET` | `get_admin_tickets` | PASS | YES | YES | Runtime Data |
| `/api/admin/tickets/{ticket_id}/reply` | `POST` | `reply_admin_ticket` | PASS | YES | YES | Runtime Data |
| `/api/admin/tickets/{ticket_id}/status` | `POST` | `update_admin_ticket_status` | PASS | YES | YES | Runtime Data |
| `/api/admin/timeframes` | `GET` | `get_admin_timeframes` | PASS | YES | YES | Runtime Data |
| `/api/auth/apple` | `POST` | `login_with_apple` | PASS | YES | YES | Runtime Data |
| `/api/auth/forgot-password` | `POST` | `forgot_password_recovery` | PASS | YES | YES | Runtime Data |
| `/api/auth/google` | `POST` | `login_with_google` | PASS | YES | YES | Runtime Data |
| `/api/auth/login` | `POST` | `login_user` | PASS | YES | YES | Runtime Data |
| `/api/auth/logout` | `POST` | `logout_user` | PASS | YES | YES | Runtime Data |
| `/api/auth/register` | `POST` | `register_user` | PASS | YES | YES | Runtime Data |
| `/api/auth/reset-password` | `POST` | `reset_password_endpoint` | PASS | YES | YES | Runtime Data |
| `/api/auth/verify-email` | `GET` | `verify_email` | PASS | YES | YES | Runtime Data |
| `/api/backtest/history` | `GET` | `get_backtest_history` | PASS | YES | YES | Runtime Data |
| `/api/backtest/run` | `POST` | `trigger_backtesting_job` | PASS | YES | YES | Runtime Data |
| `/api/blog` | `GET` | `list_blog_articles` | PASS | YES | YES | Runtime Data |
| `/api/blog/{article_id}` | `GET` | `get_blog_article` | PASS | YES | YES | Runtime Data |
| `/api/chat/assistant` | `POST` | `chatbot_assistant_explain` | PASS | YES | YES | Runtime Data |
| `/api/control` | `POST` | `execute_runtime_control` | PASS | YES | YES | Runtime Data |
| `/api/demo/report` | `GET` | `get_demo_report` | PASS | YES | YES | Runtime Data |
| `/api/demo/run` | `POST` | `run_demo_trading_scenario` | PASS | YES | YES | Runtime Data |
| `/api/demo/trades` | `GET` | `get_demo_trades` | PASS | YES | YES | Runtime Data |
| `/api/devops/metrics` | `GET` | `get_devops_metrics` | PASS | YES | YES | Runtime Data |
| `/api/devops/status` | `GET` | `get_devops_status` | PASS | YES | YES | Runtime Data |
| `/api/execution/confidence` | `GET` | `get_execution_confidence` | PASS | YES | YES | Runtime Data |
| `/api/execution/plans` | `GET` | `get_execution_plans` | PASS | YES | YES | Runtime Data |
| `/api/execution/reasoning` | `GET` | `get_execution_reasoning` | PASS | YES | YES | Runtime Data |
| `/api/growth/*` | `GET,POST` | `growth_api_router` | PASS | YES | YES | Runtime Data |
| `/api/intelligence/explain/{decision_id}` | `GET` | `explain_decision` | PASS | YES | YES | Runtime Data |
| `/api/intelligence/learning-matrix` | `GET` | `get_learning_matrix` | PASS | YES | YES | Runtime Data |
| `/api/intelligence/learning-report` | `GET` | `get_intelligence_learning_report` | PASS | YES | YES | Runtime Data |
| `/api/intelligence/multi-timeframe` | `GET` | `get_multi_timeframe` | PASS | YES | YES | Runtime Data |
| `/api/intelligence/status` | `GET` | `get_intelligence_status` | PASS | YES | YES | Runtime Data |
| `/api/liquidity/events` | `GET` | `get_liquidity_events` | PASS | YES | YES | Runtime Data |
| `/api/liquidity/map` | `GET` | `get_liquidity_map` | PASS | YES | YES | Runtime Data |
| `/api/mode` | `POST` | `transition_operating_mode` | PASS | YES | YES | Runtime Data |
| `/api/pattern/similarity` | `GET` | `get_pattern_similarity` | PASS | YES | YES | Runtime Data |
| `/api/portfolio/exposure` | `GET` | `get_portfolio_exposure` | PASS | YES | YES | Runtime Data |
| `/api/portfolio/risk` | `GET` | `get_portfolio_risk` | PASS | YES | YES | Runtime Data |
| `/api/production-readiness` | `GET` | `get_scorecard` | PASS | YES | YES | Runtime Data |
| `/api/public/business/catalog` | `GET` | `get_public_business_catalog` | PASS | YES | YES | Runtime Data |
| `/api/public/business/purchase` | `POST` | `initiate_purchase` | PASS | YES | YES | Runtime Data |
| `/api/public/markets` | `GET` | `get_supported_markets` | PASS | YES | YES | Runtime Data |
| `/api/public/metrics` | `GET` | `get_public_metrics` | PASS | YES | YES | Runtime Data |
| `/api/public/pricing` | `GET` | `get_pricing_tiers` | PASS | YES | YES | Runtime Data |
| `/api/public/subscription/plans` | `GET` | `get_subscription_plans` | PASS | YES | YES | Runtime Data |
| `/api/replay/error-analysis` | `GET` | `get_replay_error_analysis` | PASS | YES | YES | Runtime Data |
| `/api/replay/learning-status` | `GET` | `get_brain_learning_status` | PASS | YES | YES | Runtime Data |
| `/api/replay/training-monitor` | `GET` | `get_replay_training_monitor` | PASS | YES | YES | Runtime Data |
| `/api/research/current` | `GET` | `get_current_analysis` | PASS | YES | YES | Runtime Data |
| `/api/research/health` | `GET` | `get_research_health` | PASS | YES | YES | Runtime Data |
| `/api/research/history` | `GET` | `get_analysis_history` | PASS | YES | YES | Runtime Data |
| `/api/research/latest` | `GET` | `get_current_analysis` | PASS | YES | YES | Runtime Data |
| `/api/risk/emergency_stop` | `POST` | `trigger_emergency_stop` | PASS | YES | YES | Runtime Data |
| `/api/shadow/metrics` | `GET` | `get_shadow_trading_metrics` | PASS | YES | YES | Runtime Data |
| `/api/shadow/report` | `GET` | `get_shadow_report` | PASS | YES | YES | Runtime Data |
| `/api/structure/alignment` | `GET` | `get_structure_alignment` | PASS | YES | YES | Runtime Data |
| `/api/structure/map` | `GET` | `get_structure_map` | PASS | YES | YES | Runtime Data |
| `/api/structure/narrative` | `GET` | `get_structure_narrative` | PASS | YES | YES | Runtime Data |
| `/api/subscription/plans` | `GET` | `get_subscription_plans_endpoint` | PASS | YES | YES | Runtime Data |
| `/api/symbols` | `GET` | `list_symbol_administration` | PASS | YES | YES | Runtime Data |
| `/api/system/frontend-status` | `GET` | `get_system_frontend_status` | PASS | YES | YES | Runtime Data |
| `/api/user/billing/subscription` | `GET` | `get_user_subscription` | PASS | YES | YES | Runtime Data |
| `/api/user/equity-simulation` | `GET` | `simulate_equity_growth` | PASS | YES | YES | Runtime Data |
| `/api/user/fusion/{symbol}` | `GET` | `get_user_fusion` | PASS | YES | YES | Runtime Data |
| `/api/user/history` | `GET` | `get_user_signals_history` | PASS | YES | YES | Runtime Data |
| `/api/user/ledger/balance` | `GET` | `get_user_ledger_balance` | PASS | YES | YES | Runtime Data |
| `/api/user/markets` | `GET` | `get_user_markets` | PASS | YES | YES | Runtime Data |
| `/api/user/reports` | `GET` | `get_user_reports` | PASS | YES | YES | Runtime Data |
| `/api/user/sessions` | `GET` | `get_user_sessions` | PASS | YES | YES | Runtime Data |
| `/api/user/sessions/revoke` | `POST` | `revoke_user_session` | PASS | YES | YES | Runtime Data |
| `/api/user/signals` | `GET` | `get_user_signals` | PASS | YES | YES | Runtime Data |
| `/api/user/tickets` | `GET,POST` | `user_support_tickets` | PASS | YES | YES | Runtime Data |
| `/api/v1/health` | `GET` | `get_api_v1_health` | PASS | YES | YES | Runtime Data |
| `/api/validation/history` | `GET` | `get_validation_history` | PASS | YES | YES | Runtime Data |
| `/api/validation/reports/download` | `GET` | `download_validation_report` | PASS | YES | YES | Runtime Data |
| `/api/validation/run` | `POST` | `trigger_validation_run` | PASS | YES | YES | Runtime Data |
| `/api/validation/status` | `GET` | `get_validation_status` | PASS | YES | YES | Runtime Data |
| `/health` | `GET` | `get_production_health` | PASS | YES | YES | Runtime Data |
| `/health/live` | `GET` | `get_health_live` | PASS | YES | YES | Runtime Data |
| `/health/ready` | `GET` | `get_health_ready` | PASS | YES | YES | Runtime Data |
| `/v1/dashboard/cognitive` | `GET` | `get_dashboard_cognitive` | PASS | YES | YES | Runtime Data |
| `/v1/dashboard/live-research` | `GET` | `get_current_analysis` | PASS | YES | YES | Runtime Data |
| `/v1/dashboard/overview` | `GET` | `get_dashboard_overview` | PASS | YES | YES | Runtime Data |
| `/v1/health` | `GET` | `get_health_diagnostics` | PASS | YES | YES | Runtime Data |
| `/v1/metrics` | `GET` | `get_telemetry_metrics` | PASS | YES | YES | Runtime Data |
| `/v1/monitoring` | `GET` | `get_monitoring_alerts` | PASS | YES | YES | Runtime Data |
| `/v1/runtime` | `GET` | `get_runtime_status` | PASS | YES | YES | Runtime Data |

---

## Subsystem Functional Overview

1. **Core Public & Commercial APIs (`/api/public/*`, `/api/subscription/*`)**:
   - Delivers live pricing, subscription tiers, business catalog products, and checkout verification without code redeployment.
2. **User & Trading Signal APIs (`/api/user/*`, `/api/signals`)**:
   - Serves clean signals, multi-horizon filters, equity compounding projections, ledger balance tracking, and session management.
3. **Execution & Market Structure Intelligence APIs (`/api/execution/*`, `/api/structure/*`, `/api/liquidity/*`, `/api/pattern/*`, `/api/portfolio/*`)**:
   - Serves pure price-action market structure maps, order blocks, fair value gaps, liquidity sweep heatmaps, and portfolio heat evaluation.
4. **Simulation, Backtest & Demo Trading APIs (`/api/backtest/*`, `/api/demo/*`, `/api/shadow/*`)**:
   - Runs historical backtests, demo scenario executions, and paper trading reports.
5. **System SRE, Health & DevOps APIs (`/api/devops/*`, `/health/*`, `/api/validation/*`)**:
   - Provides live health checks (`/health/live`, `/health/ready`), background test runner, and system telemetry metrics.
6. **Growth & Research APIs (`/api/growth/*`, `/api/research/*`)**:
   - Serves real-time market snapshots, historical analysis records, and news headlines.

---

## Conclusion
All 80+ endpoints are operational, tested, and mapped across the YarTrader system architecture.
