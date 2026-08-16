import os
from fastapi import APIRouter, HTTPException, Depends, Query, Request
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from src.ShadowTrading.Engine.PredictiveShadowEngine import PredictiveShadowEngine

router = APIRouter(prefix="/api/admin", tags=["Admin SRE Operations API"])

# Import secure shared global auth service to prevent state isolation leaks
from src.Application.Dashboard.auth_service import global_auth_service

def enforce_admin_token(token: Optional[str] = None):
    """Enforces strict role-based access control, rejecting non-ADMIN accounts with 403 Forbidden."""
    is_production = os.environ.get("YARTRADER_ENV") == "production" or os.environ.get("TRADEYAR_ENV") == "production" or os.environ.get("RG_ENV") == "production"
    from app.core.logging import log_security

    log_token = f"{token[:8]}..." if token else None

    if not token:
        if is_production:
            log_security("AUTHORIZATION_DENIED", reason="Authentication token is missing")
            raise HTTPException(status_code=401, detail="Authentication token is missing")
        # Fallback testing mode override
        return {"email": "test-admin@yartrader.app", "role": "ADMIN"}

    if token == "mock_social_token":
        if is_production:
            log_security("AUTHORIZATION_DENIED", token=log_token, reason="Mock social token forbidden in production")
            raise HTTPException(status_code=403, detail="Forbidden: Administrator privilege required")
        else:
            return {"email": "test-admin@yartrader.app", "role": "ADMIN"}

    session = global_auth_service.validate_session(token)
    if not session or session.get("role") != "ADMIN":
        log_security("AUTHORIZATION_DENIED", token=log_token, email=session.get("email") if session else None)
        raise HTTPException(status_code=403, detail="Forbidden: Administrator privilege required")
    return session

# 1. Active Symbol Management (Bounded to max 30)
@router.get("/symbols")
def get_admin_symbols(token: Optional[str] = None):
    """Lists currently registered active symbols and validates maximum limits ceiling."""
    enforce_admin_token(token)
    from src.ShadowTrading.Engine.SymbolRegistry import SymbolRegistry
    registry_inst = SymbolRegistry.get_instance()
    registry = registry_inst.get_all_registered()
    active_symbols = sorted([sym for sym, info in registry.items() if info.get("active", True)])

    return {
        "active_symbols": active_symbols,
        "count": len(active_symbols),
        "max_limit": registry_inst.max_symbols,
        "max_active_symbols_limit": registry_inst.max_symbols,
        "system_ceiling_enforced": True,
        "registered_symbols": [
            {
                "symbol": symbol,
                "active": info.get("active", True),
                "timeframes": info.get("timeframes", ["H1"]),
                "configuration_state": "ACTIVE" if info.get("active", True) else "DISABLED"
            }
            for symbol, info in sorted(registry.items())
        ]
    }

# 2. Add New Active Symbol Context (Validates 30 limit)
class SymbolRegistration(BaseModel):
    symbol: str
    timeframe: Optional[int] = 64
    timeframes: Optional[List[str]] = None

@router.post("/symbols")
def register_new_active_symbol_context(payload: SymbolRegistration, token: Optional[str] = None):
    """SRE administrative action to dynamically spin up a new SymbolTimeContext."""
    session = enforce_admin_token(token)
    admin_email = session.get("email", "sre-admin@yartrader.app")
    from src.ShadowTrading.Engine.SymbolRegistry import SymbolRegistry
    registry_inst = SymbolRegistry.get_instance()
    engine = PredictiveShadowEngine.get_instance()
    try:
        symbol_upper = payload.symbol.upper()
        tfs = payload.timeframes or ["H1"]
        registry_inst.register_symbol(symbol_upper, tfs)

        tf_int = payload.timeframe if payload.timeframe is not None else 64
        ctx = engine.get_or_create_context(symbol_upper, tf_int)

        from app.core.logging import log_audit
        log_audit("SYMBOL_REGISTRY_CHANGE", action="REGISTER", symbol=symbol_upper, timeframes=tfs, actor=admin_email)

        return {
            "status": "Success",
            "message": f"Successfully created isolated cognitive context: {ctx.context_id}",
            "context": ctx.to_dict()
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

# 3. Independent Per-Context Reporting & Analytics
@router.get("/reports")
def get_admin_reports(symbol: Optional[str] = None, timeframe: Optional[Any] = None, token: Optional[str] = None):
    """Generates distinct separate reports per timeframe and symbol without mixing statistics."""
    enforce_admin_token(token)
    engine = PredictiveShadowEngine.get_instance()

    target_symbol = symbol.upper() if symbol else "XAUUSD"

    from src.Core.timeframes import TimeframeNormalizer
    contexts_to_report = []

    if target_symbol in engine.runtime_manager.symbol_brains:
        brains = engine.runtime_manager.symbol_brains[target_symbol]
        unique_contexts = {}
        for tf, ctx in brains.items():
            try:
                tf_canon = TimeframeNormalizer.normalize(tf)
            except Exception:
                tf_canon = tf

            if timeframe is not None:
                try:
                    filter_tf_canon = TimeframeNormalizer.normalize(timeframe)
                except Exception:
                    filter_tf_canon = timeframe
                if tf_canon != filter_tf_canon:
                    continue

            if tf_canon not in unique_contexts:
                unique_contexts[tf_canon] = ctx
            else:
                import logging
                logger = logging.getLogger("AdminReportsAPI")
                logger.warning(
                    f"SRE DATA PROBLEM DETECTED: Duplicate context found for symbol={target_symbol}, "
                    f"timeframe={tf_canon}. Original: {unique_contexts[tf_canon].context_id}, "
                    f"Duplicate: {ctx.context_id}"
                )

        contexts_to_report = list(unique_contexts.values())

    def sort_key(ctx):
        tf = ctx.timeframe
        if isinstance(tf, int):
            return (0, tf)
        return (1, str(tf))

    contexts_to_report.sort(key=sort_key)
    reports = [ctx.get_statistics() for ctx in contexts_to_report]

    return {
        "symbol": target_symbol,
        "count": len(reports),
        "reports": reports
    }

# 4. SRE Backup snapshot operation
@router.post("/backup")
def trigger_backup_snapshot(token: Optional[str] = None):
    """SRE administrative action to trigger an atomic snapshot backup of persistent state."""
    session = enforce_admin_token(token)
    admin_email = session.get("email", "sre-admin@yartrader.app")
    from src.Application.Runtime.backup_manager import BackupManager
    manager = BackupManager()
    try:
        res = manager.create_backup()
        from app.core.logging import log_audit
        log_audit("ADMIN_ACTION", action="BACKUP", result="SUCCESS", actor=admin_email)
        return res
    except Exception as e:
        from app.core.logging import log_audit
        log_audit("ADMIN_ACTION", action="BACKUP", result="FAILED", error=str(e), actor=admin_email)
        raise HTTPException(status_code=500, detail=str(e))

# 5. SRE Restore operation
class RestorePayload(BaseModel):
    filename: str

@router.post("/restore")
def trigger_restore(payload: RestorePayload, token: Optional[str] = None):
    """SRE administrative action to safely restore persistent state from a backup archive."""
    session = enforce_admin_token(token)
    admin_email = session.get("email", "sre-admin@yartrader.app")
    from src.Application.Runtime.backup_manager import BackupManager
    manager = BackupManager()
    try:
        res = manager.restore_backup(payload.filename)
        from app.core.logging import log_audit
        log_audit("ADMIN_ACTION", action="RESTORE", filename=payload.filename, result="SUCCESS", actor=admin_email)
        return res
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==============================================================================
# P2-1 — DOUBLE-ENTRY FINANCIAL LEDGER ADMIN ENDPOINTS
# ==============================================================================
class LedgerEntry(BaseModel):
    account_id: str
    type: str  # "debit" or "credit"
    amount: int  # integer cents

class LedgerTransactionPayload(BaseModel):
    idempotency_key: str
    description: str
    currency: Optional[str] = "USD"
    entries: List[LedgerEntry]

class LedgerReversalPayload(BaseModel):
    original_transaction_id: str
    idempotency_key: str
    reason: str

@router.post("/ledger/transaction")
def admin_post_transaction(payload: LedgerTransactionPayload, token: Optional[str] = None):
    """Posts a balanced double-entry transaction atomically."""
    enforce_admin_token(token)
    from src.Application.Dashboard.ledger_manager import LedgerManager
    manager = LedgerManager()
    entries_dict = [entry.dict() for entry in payload.entries]
    try:
        return manager.post_transaction(
            idempotency_key=payload.idempotency_key,
            entries=entries_dict,
            description=payload.description,
            currency=payload.currency
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/ledger/reverse")
def admin_reverse_transaction(payload: LedgerReversalPayload, token: Optional[str] = None):
    """Performs a reversal compensating transaction to correct a posted ledger transaction."""
    enforce_admin_token(token)
    from src.Application.Dashboard.ledger_manager import LedgerManager
    manager = LedgerManager()
    try:
        return manager.reverse_transaction(
            original_tx_id=payload.original_transaction_id,
            idempotency_key=payload.idempotency_key,
            reason=payload.reason
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==============================================================================
# P2-2 — SaaS BILLING & INVOICING WEBHOOKS
# ==============================================================================
@router.post("/billing/webhook")
async def payment_gateway_webhook(request: Request):
    """
    Idempotent Webhook endpoint ingesting Stripe or cryptographic gateway payment events.
    Verifies authenticity and integrity signatures strictly before executing state machine.
    """
    body_bytes = await request.body()
    signature = request.headers.get("X-Gateway-Signature", "")

    # Retrieve webhook secret from environment config safely
    webhook_secret = os.environ.get("BILLING_WEBHOOK_SECRET")
    if not webhook_secret:
        raise HTTPException(status_code=500, detail="Billing webhook secret is not configured in production.")

    from src.Application.Dashboard.billing_manager import BillingManager
    manager = BillingManager()
    try:
        return manager.process_signed_webhook(
            payload_bytes=body_bytes,
            signature=signature,
            webhook_secret=webhook_secret
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==============================================================================
# P2-3 — SUPPORT TICKETING ADMIN ENDPOINTS
# ==============================================================================
class AdminReplyPayload(BaseModel):
    message: str

class TicketStatusPayload(BaseModel):
    status: str
    priority: Optional[str] = None

@router.get("/tickets")
def admin_list_tickets(page: int = Query(1, ge=1), limit: int = Query(20, le=50), token: Optional[str] = None):
    """Lists all support tickets globally for administrative action."""
    enforce_admin_token(token)
    from src.Application.Dashboard.ticket_manager import TicketManager
    manager = TicketManager()
    return manager.list_all_tickets_admin(page=page, limit=limit)

@router.post("/tickets/{ticket_id}/reply")
def admin_reply_to_ticket(ticket_id: str, payload: AdminReplyPayload, token: Optional[str] = None):
    """Appends an administrative SRE response reply message to the support ticket."""
    enforce_admin_token(token)
    from src.Application.Dashboard.ticket_manager import TicketManager
    manager = TicketManager()
    try:
        return manager.add_reply(
            ticket_id=ticket_id,
            email="sre-support@yartrader.app",
            message=payload.message,
            is_admin=True
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/tickets/{ticket_id}/status")
def admin_update_ticket_status(ticket_id: str, payload: TicketStatusPayload, token: Optional[str] = None):
    """Updates status or priority of a support ticket administratively."""
    enforce_admin_token(token)
    from src.Application.Dashboard.ticket_manager import TicketManager
    manager = TicketManager()
    try:
        return manager.update_status(
            ticket_id=ticket_id,
            status=payload.status,
            priority=payload.priority
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==============================================================================
# P2-5 — REVENUE BUSINESS ANALYTICS ADMIN ENDPOINTS
# ==============================================================================
@router.get("/analytics/revenue")
def get_revenue_business_analytics(token: Optional[str] = None):
    """
    Computes real, non-synthetic revenue and SaaS business analytics metrics
    derived dynamically from actual, persisted billing data.
    """
    enforce_admin_token(token)
    from src.Application.Dashboard.billing_manager import BillingManager
    manager = BillingManager()

    # Dynamic computation of SaaS metrics directly from source of truth
    data = manager._load()

    active_subscriptions_count = 0
    mrr_cents = 0
    cancelled_count = 0
    total_count = 0

    # Calculate MRR from active subscriptions
    for email, sub in data.get("subscriptions", {}).items():
        total_count += 1
        status = sub.get("status", "")
        if status == "ACTIVE":
            active_subscriptions_count += 1
            tier = sub.get("tier_id", "FREE")
            # Derived plan pricing matching standard pricing plans
            if tier == "DAILY":
                mrr_cents += 2900
            elif tier == "PRO":
                mrr_cents += 7900
            elif tier == "INSTITUTIONAL":
                mrr_cents += 29900
        elif status == "CANCELLED":
            cancelled_count += 1

    mrr_usd = round(mrr_cents / 100.0, 2)
    arr_usd = round(mrr_usd * 12.0, 2)

    # Calculate churn rate: cancelled / total active and cancelled
    churn_rate = 0.0
    if total_count > 0:
        churn_rate = round((cancelled_count / total_count) * 100.0, 2)

    # Invoices aggregate
    total_invoiced_cents = sum(inv.get("amount_cents", 0) for inv in data.get("invoices", []))
    total_payments = len(data.get("invoices", []))
    total_invoiced_usd = round(total_invoiced_cents / 100.0, 2)

    # Calculate LTV: average revenue per active customer
    ltv_usd = 0.0
    if active_subscriptions_count > 0:
        ltv_usd = round(total_invoiced_usd / active_subscriptions_count, 2)

    return {
        "mrr_usd": mrr_usd,
        "arr_usd": arr_usd,
        "active_subscriptions": active_subscriptions_count,
        "churn_rate_pct": churn_rate,
        "total_revenue_usd": total_invoiced_usd,
        "total_payments_count": total_payments,
        "ltv_usd": ltv_usd,
        "currency": "USD"
    }


# ==============================================================================
# SRE ADMIN BUSINESS CATALOG ENDPOINTS
# ==============================================================================
class AdminProductPayload(BaseModel):
    id: str
    slug: str
    name: str
    short_description: str
    long_description: str
    category: str
    subcategory: Optional[str] = None
    product_type: str
    price: float
    currency: str
    billing_period: str
    features: List[str] = []
    limits: Dict[str, Any] = {}
    visible: bool = True
    purchasable: bool = False
    status: str
    badge: Optional[str] = None
    cta_label: Optional[str] = None
    display_order: int = 999
    featured: bool = False

@router.get("/business/catalog")
def admin_get_business_catalog(token: Optional[str] = None):
    """Retrieves all products from the Business Catalog, including invisible/draft ones."""
    session = enforce_admin_token(token)
    from src.Application.Dashboard.business_catalog_manager import BusinessCatalogManager
    manager = BusinessCatalogManager()
    return manager.list_products(include_invisible=True)

@router.post("/business/catalog")
def admin_save_product(payload: AdminProductPayload, token: Optional[str] = None):
    """Creates or updates a product in the authoritative Business Catalog."""
    session = enforce_admin_token(token)
    admin_email = session.get("email", "sre-admin@yartrader.app")
    from src.Application.Dashboard.business_catalog_manager import BusinessCatalogManager
    manager = BusinessCatalogManager()
    try:
        updated = manager.save_product(payload.dict(), admin_email=admin_email)
        return {
            "status": "Success",
            "message": f"Successfully updated product '{updated['name']}' in the Business Catalog.",
            "product": updated
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/business/catalog/{product_id}")
def admin_delete_product(product_id: str, token: Optional[str] = None):
    """Deletes/archives a product from the Business Catalog."""
    session = enforce_admin_token(token)
    admin_email = session.get("email", "sre-admin@yartrader.app")
    from src.Application.Dashboard.business_catalog_manager import BusinessCatalogManager
    manager = BusinessCatalogManager()
    success = manager.delete_product(product_id, admin_email=admin_email)
    if not success:
        raise HTTPException(status_code=404, detail="Product not found in Business Catalog.")
    return {
        "status": "Success",
        "message": f"Successfully deleted product '{product_id}' from the Business Catalog."
    }
