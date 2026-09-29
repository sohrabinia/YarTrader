import os
from fastapi import APIRouter, HTTPException, Header, Depends, Query
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from src.Application.Dashboard.auth_service import global_auth_service
from src.Growth.Agents.SecurityCostAgents import TierEntitlementMiddleware

router = APIRouter(prefix="/api/user", tags=["User Trading API"])

entitlement_middleware = TierEntitlementMiddleware()

def get_user_session_and_enforce_tier(authorization: Optional[str] = Header(None), horizon: Optional[str] = None) -> Dict[str, Any]:
    """
    FastAPI Router dependency that extracts active session token, retrieves trusted user
    subscription tier from server state, and verifies access boundaries against TierEntitlementMiddleware.
    """
    is_production = (os.environ.get("YARTRADER_ENV") == "production" or
                     os.environ.get("TRADEYAR_ENV") == "production" or
                     os.environ.get("RG_ENV") == "production")

    if not authorization:
        if is_production:
            raise HTTPException(status_code=401, detail="Authentication token required: Authorization header is missing.")
        # Dev/sandbox mode fallback
        return {"email": "guest@yartrader.app", "role": "USER", "tier": "FREE"}

    token = authorization.replace("Bearer ", "").strip()
    session = global_auth_service.validate_session(token)
    if not session:
        raise HTTPException(status_code=401, detail="Invalid or expired session token.")

    user_tier = session.get("tier", "FREE")

    # Fetch active symbol limit
    from src.Market.Universe.symbol_registry import SymbolRegistry
    registry = SymbolRegistry.get_instance()
    symbol_count = len(registry.get_all_registered())

    # Map target timeframe
    timeframe = "H1"
    h_val = horizon.upper() if horizon else "SHORT"
    if h_val == "MICRO":
        timeframe = "M1"
    elif h_val == "SHORT":
        timeframe = "H1"
    elif h_val == "MEDIUM":
        timeframe = "H1"
    elif h_val == "MACRO":
        timeframe = "D1"

    # Validate tier limits
    res = entitlement_middleware.verify_access(user_tier, symbol_count, h_val, timeframe)
    if not res["access_granted"]:
        raise HTTPException(status_code=403, detail=f"Access Denied: {', '.join(res['reasons'])}")

    return session


# 1. Canonical User Signals

def _snapshot_signals(market: Optional[str] = None, horizon: Optional[str] = None) -> List[Dict[str, Any]]:
    """Build customer-facing signals from persisted ResearchRuntime snapshots only."""
    snapshot_dir = "runtime_logs/research_snapshots"
    if not os.path.exists(snapshot_dir): return []
    market_symbols = {"gold":{"XAUUSD"},"bitcoin":{"BTCUSD"},"euro":{"EURUSD"},"pound":{"GBPUSD"}}
    horizon_map = {"micro":{"M1"},"short":{"M5","M15","H1"},"medium":{"H4","D1"},"macro":{"W1","MN1"}}
    allowed_symbols = market_symbols.get((market or "").lower()) if market else None
    allowed_tfs = horizon_map.get((horizon or "").lower()) if horizon else None
    try:
        files=[os.path.join(snapshot_dir,f) for f in os.listdir(snapshot_dir) if f.endswith(".json")]
        files.sort(key=lambda path: os.path.getmtime(path), reverse=True)
    except OSError: return []
    latest_by_key={}
    for path in files:
        try:
            with open(path,"r",encoding="utf-8") as fh: data=json.load(fh)
            symbol=str(data.get("symbol") or data.get("asset") or "").upper()
            timeframe=str(data.get("timeframe") or "H1").upper()
            if allowed_symbols and symbol not in allowed_symbols: continue
            if allowed_tfs and timeframe not in allowed_tfs: continue
            decision=(data.get("findings",{}) or {}).get("autonomous_decision",{}) or {}
            action=str(decision.get("action","WAIT")).upper()
            if action not in {"BUY","SELL"}: continue
            key=(symbol,timeframe)
            if key in latest_by_key: continue
            latest_by_key[key]={"signal_id":decision.get("decision_id") or data.get("report_id") or f"research-{symbol}-{timeframe}","symbol":symbol,"direction":action,"entry_zone":decision.get("entry_price"),"invalidation_level":decision.get("stop_loss"),"target_zone":decision.get("take_profit"),"confidence":decision.get("confidence",0),"reason":decision.get("reasoning",[]),"status":"ACTIVE","timeframe":timeframe,"timestamp":data.get("timestamp") or data.get("created_at"),"evidence_state":"REAL_RESEARCH_SNAPSHOT"}
        except (OSError,ValueError,TypeError,json.JSONDecodeError): continue
    return list(latest_by_key.values())

@router.get("/signals")
def get_user_signals(market: Optional[str] = None, horizon: Optional[str] = None, session: Dict[str, Any] = Depends(get_user_session_and_enforce_tier)):
    """Exposes real research decisions; no Shadow engine is consulted."""
    return _snapshot_signals(market, horizon)

@router.get("/equity-simulation")
def simulate_equity_growth(initial_balance: float = 10000.0, monthly_growth_pct: float = 8.5, months: int = 6, session: Dict[str, Any] = Depends(get_user_session_and_enforce_tier)):
    """User-controlled hypothetical projection; never presented as historical performance."""
    if initial_balance <= 0 or months < 0 or months > 120: raise HTTPException(status_code=400, detail="Invalid simulation parameters")
    series=[{"month":"M0","balance":round(initial_balance,2)}]; current=initial_balance
    for i in range(1,months+1): current*=1.0+(monthly_growth_pct/100.0); series.append({"month":f"M{i}","balance":round(current,2)})
    return {"simulation":True,"initial_balance":initial_balance,"final_balance":round(current,2),"total_growth_pct":round(((current-initial_balance)/initial_balance*100.0),2),"projection":series}

@router.get("/reports")
def get_user_horizon_reports(market: Optional[str] = None, session: Dict[str, Any] = Depends(get_user_session_and_enforce_tier)):
    signals=_snapshot_signals(market=market); grouped={}
    for signal in signals:
        key=(signal["symbol"],signal["timeframe"]); item=grouped.setdefault(key,{"asset":signal["symbol"],"timeframe":signal["timeframe"],"signals":0,"confidence_sum":0.0}); item["signals"]+=1; item["confidence_sum"]+=float(signal.get("confidence") or 0.0)
    return [{"asset":v["asset"],"horizon":v["timeframe"],"signal_count":v["signals"],"average_confidence":round(v["confidence_sum"]/v["signals"],2) if v["signals"] else None,"win_rate":None,"data_state":"REAL_RESEARCH_ONLY"} for v in grouped.values()]

@router.get("/fusion/{symbol}")
def get_symbol_decision_fusion(symbol: str, session: Dict[str, Any] = Depends(get_user_session_and_enforce_tier)):
    """Returns the latest canonical research decision without Shadow runtime state."""
    from src.Application.Services.web_dashboard import get_current_analysis
    analysis=get_current_analysis(symbol=symbol.upper(),timeframe="H1")
    return {"symbol":symbol.upper(),"action":analysis.get("bias","WAIT"),"confidence":analysis.get("confidence",0),"reasoning":analysis.get("reasoning",[]),"timestamp":analysis.get("timestamp"),"evidence_state":"REAL_RESEARCH_SNAPSHOT" if analysis.get("status")!="degraded" else "INSUFFICIENT_EVIDENCE"}

@router.get("/history")
def get_user_signals_history(market: Optional[str] = None, session: Dict[str, Any] = Depends(get_user_session_and_enforce_tier)):
    return _snapshot_signals(market=market)

# ==============================================================================
@router.get("/ledger/balance")
def get_ledger_balance(session: Dict[str, Any] = Depends(get_user_session_and_enforce_tier)):
    """Returns the user's secure ledger account balance (in cents; no floats)."""
    from src.Application.Dashboard.ledger_manager import LedgerManager
    manager = LedgerManager()
    email = session["email"].lower()
    balance = manager.get_account_balance(email)
    return {
        "email": email,
        "balance_cents": balance,
        "balance_usd": round(balance / 100.0, 2),
        "currency": "USD"
    }


# ==============================================================================
# P2-2 — SaaS BILLING & INVOICING ENDPOINTS
# ==============================================================================
@router.get("/billing/subscription")
def get_billing_subscription(session: Dict[str, Any] = Depends(get_user_session_and_enforce_tier)):
    """Returns the user's active billing subscription state from server-side state."""
    from src.Application.Dashboard.billing_manager import BillingManager
    manager = BillingManager()
    email = session["email"].lower()
    return manager.get_subscription(email)



@router.get("/ledger/statement")
def get_ledger_statement(session: Dict[str, Any] = Depends(get_user_session_and_enforce_tier)):
    from src.Application.Dashboard.ledger_manager import LedgerManager
    email = session["email"].lower()
    data = LedgerManager().get_account_statement(email)
    return {"email":email,"balance_cents":data["balance"],"balance_usd":round(data["balance"]/100.0,2),"currency":"USD","transactions":data["transactions"]}

@router.get("/billing/invoices")
def get_billing_invoices(session: Dict[str, Any] = Depends(get_user_session_and_enforce_tier)):
    from src.Application.Dashboard.billing_manager import BillingManager
    return {"invoices": BillingManager().get_user_invoices(session["email"])}


# ==============================================================================
# RECEIVE-ONLY USDT WALLET
# ==============================================================================
@router.get("/wallet/receive")
def get_receive_wallet(session: Dict[str, Any] = Depends(get_user_session_and_enforce_tier)):
    """Returns configured public USDT receive addresses. No withdrawal or signing capability exists."""
    from src.Application.Dashboard.receive_wallet_manager import ReceiveWalletManager
    return ReceiveWalletManager().public_config()


# ==============================================================================
# P2-3 — SUPPORT TICKETING SYSTEM ENDPOINTS
# ==============================================================================
class CreateTicketPayload(BaseModel):
    subject: str
    category: str
    priority: str
    message: str

class ReplyTicketPayload(BaseModel):
    message: str

@router.get("/tickets")
def list_my_tickets(page: int = Query(1, ge=1), limit: int = Query(10, le=50), session: Dict[str, Any] = Depends(get_user_session_and_enforce_tier)):
    """Returns a paginated list of tickets owned by the authenticated user."""
    from src.Application.Dashboard.ticket_manager import TicketManager
    manager = TicketManager()
    return manager.list_user_tickets(session["email"], page=page, limit=limit)

@router.post("/tickets")
def create_new_ticket(payload: CreateTicketPayload, session: Dict[str, Any] = Depends(get_user_session_and_enforce_tier)):
    """Creates a new support ticket securely bound to the authenticated user."""
    from src.Application.Dashboard.ticket_manager import TicketManager
    manager = TicketManager()
    return manager.create_ticket(
        email=session["email"],
        subject=payload.subject,
        category=payload.category,
        priority=payload.priority,
        message=payload.message
    )

@router.post("/tickets/{ticket_id}/reply")
def reply_to_ticket(ticket_id: str, payload: ReplyTicketPayload, session: Dict[str, Any] = Depends(get_user_session_and_enforce_tier)):
    """Appends a reply message to the support ticket with strict ownership checks."""
    from src.Application.Dashboard.ticket_manager import TicketManager
    manager = TicketManager()
    try:
        return manager.add_reply(
            ticket_id=ticket_id,
            email=session["email"],
            message=payload.message,
            is_admin=False
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==============================================================================
# P2-4 — LOGIN DEVICE sessionS TRACKING ENDPOINTS
# ==============================================================================
class RevokeSessionPayload(BaseModel):
    token: str

@router.get("/sessions")
def list_my_sessions(session: Dict[str, Any] = Depends(get_user_session_and_enforce_tier)):
    """Lists all active login sessions/devices for the authenticated user."""
    from src.Application.Dashboard.device_tracker import DeviceTracker
    tracker = DeviceTracker()
    return tracker.list_active_sessions(session["email"])

@router.post("/sessions/revoke")
def revoke_active_session(payload: RevokeSessionPayload, session: Dict[str, Any] = Depends(get_user_session_and_enforce_tier)):
    """Securely revokes an active login session with strict user boundary validation."""
    from src.Application.Dashboard.device_tracker import DeviceTracker
    tracker = DeviceTracker()
    try:
        tracker.revoke_session(payload.token, session["email"])
        return {"status": "Success", "message": "Session revoked successfully."}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
