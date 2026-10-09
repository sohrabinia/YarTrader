import os
import json
import re
import time
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
    # Tier limits apply to symbols enabled for current research/execution,
    # not the full 30-symbol catalog. Counting every registered symbol blocked
    # FREE users even though only two symbols are currently enabled.
    symbol_count = sum(
        1 for info in registry.get_all_registered().values()
        if bool(info.get("active", info.get("enabled", False)))
    )

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
    from src.Application.Deployment.storage import YarTraderStorageManager, is_research_snapshot_fresh
    snapshot_dir = YarTraderStorageManager.get_manager().get_research_snapshots_dir()
    if not os.path.exists(snapshot_dir): return []
    market_symbols = {"gold":{"XAUUSD"},"bitcoin":{"BTCUSD"},"euro":{"EURUSD"},"pound":{"GBPUSD"}}
    horizon_map = {"micro":{"M1"},"short":{"M5","M15","H1"},"medium":{"H4","D1"},"macro":{"W1","MN1"}}
    allowed_symbols = market_symbols.get((market or "").lower()) if market else None
    allowed_tfs = horizon_map.get((horizon or "").lower()) if horizon else None
    try:
        max_age_by_timeframe = {
            "M1": 5 * 60, "M5": 15 * 60, "M15": 45 * 60, "M30": 90 * 60,
            "H1": 3 * 3600, "H4": 12 * 3600, "D1": 3 * 86400,
            "W1": 14 * 86400, "MN1": 45 * 86400,
        }
        now_epoch = time.time()
        files = []
        for name in os.listdir(snapshot_dir):
            if not name.endswith(".json"):
                continue
            match = re.match(r"rpt-([A-Z0-9]+)-([A-Z0-9]+)-snapshot_", name)
            if match:
                file_symbol, file_timeframe = match.group(1), match.group(2)
                if allowed_symbols and file_symbol not in allowed_symbols:
                    continue
                if allowed_tfs and file_timeframe not in allowed_tfs:
                    continue
                path = os.path.join(snapshot_dir, name)
                try:
                    if now_epoch - os.path.getmtime(path) > max_age_by_timeframe.get(file_timeframe, 3 * 3600):
                        continue
                except OSError:
                    continue
                files.append(path)
            else:
                files.append(os.path.join(snapshot_dir, name))
        files.sort(key=lambda path: os.path.getmtime(path), reverse=True)
    except OSError:
        return []
    latest_by_key = {}
    processed_keys = set()
    for path in files:
        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            if not is_research_snapshot_fresh(data):
                continue
            symbol = str(data.get("symbol") or data.get("asset") or "").upper()
            timeframe = str(data.get("timeframe") or "H1").upper()
            if allowed_symbols and symbol not in allowed_symbols:
                continue
            if allowed_tfs and timeframe not in allowed_tfs:
                continue
            key = (symbol, timeframe)
            if key in processed_keys:
                continue
            # The newest fresh snapshot wins even when its decision is WAIT; never resurrect an older signal.
            processed_keys.add(key)
            findings = data.get("findings", {}) or {}
            decision = findings.get("autonomous_decision", {}) or {}
            intel_plan = (findings.get("intel_summary", {}) or {}).get("plan", {}) or {}
            brain = findings.get("newborn_brain_report", {}) or {}
            hypotheses = brain.get("active_hypotheses", []) if isinstance(brain, dict) else []
            hypothesis = hypotheses[0] if hypotheses and isinstance(hypotheses[0], dict) else {}
            action = str(decision.get("action", "WAIT")).upper()
            brain_action = str(intel_plan.get("brain_suggested_action") or hypothesis.get("suggested_virtual_action") or "WAIT").upper()
            brain_confidence = float(hypothesis.get("hypothesis_confidence", 0.0) or 0.0)
            blocked_action = str(hypothesis.get("blocked_direction") or "WAIT").upper()
            blocked_confidence = float(hypothesis.get("blocked_direction_confidence", 0.0) or 0.0)
            evidence_status = str(hypothesis.get("evidence_status", "NO_OUTCOME_LABELS"))
            successful_outcomes = int(hypothesis.get("successful_outcomes", 0) or 0)
            failed_outcomes = int(hypothesis.get("failed_outcomes", 0) or 0)
            outcome_success_rate = hypothesis.get("outcome_success_rate_pct")
            success_rate_label = (
                f"{float(outcome_success_rate):.1f}%"
                if isinstance(outcome_success_rate, (int, float)) and not isinstance(outcome_success_rate, bool)
                else "unknown"
            )
            brain_consumed = bool(intel_plan.get("brain_report_consumed"))
            has_brain_evidence = bool(hypotheses or brain_consumed)
            trade_params = hypothesis.get("trade_parameters", {}) or {}
            entry = decision.get("entry", decision.get("entry_price"))
            stop_loss = decision.get("stop_loss")
            take_profit = decision.get("take_profit")
            confidence = float(decision.get("confidence", 0.0) or 0.0)
            reason = decision.get("reasoning", []) or []

            if action not in {"BUY", "SELL"}:
                direction = blocked_action if blocked_action in {"BUY", "SELL"} else brain_action
                if direction not in {"BUY", "SELL"} or not brain_consumed:
                    continue
                action = direction
                entry = trade_params.get("entry")
                stop_loss = trade_params.get("stop_loss")
                take_profit = trade_params.get("take_profit")
                if evidence_status != "VALIDATED_OUTCOMES" or successful_outcomes < 3:
                    confidence = blocked_confidence if blocked_action in {"BUY", "SELL"} else brain_confidence
                    status = "BLOCKED"
                    reason = list(reason) + [
                        f"Blocked: historical evidence is {evidence_status} ({successful_outcomes} successes, {failed_outcomes} failures; success rate {success_rate_label}). Actionable signals require VALIDATED_OUTCOMES, at least 3 successes, and a success rate of at least 50%."
                    ]
                elif brain_confidence >= 50.0:
                    confidence = brain_confidence
                    status = "CANDIDATE"
                    reason = list(reason) + [
                        "Candidate only: learned entry/stop-loss/take-profit parameters are missing or did not pass the execution planner."
                    ]
                else:
                    continue
            else:
                rr = float(decision.get("risk_reward", 0.0) or 0.0)
                valid_levels = all(
                    value is not None and float(value) > 0.0
                    for value in (entry, stop_loss, take_profit)
                )
                evidence_ok = not has_brain_evidence or (evidence_status == "VALIDATED_OUTCOMES" and successful_outcomes >= 3)
                if not evidence_ok:
                    status = "BLOCKED"
                    reason = list(reason) + [
                        f"Blocked: historical evidence is {evidence_status} ({successful_outcomes} successes, {failed_outcomes} failures; success rate {success_rate_label}). Actionable signals require VALIDATED_OUTCOMES, at least 3 successes, and a success rate of at least 50%."
                    ]
                else:
                    status = "ACTIVE" if valid_levels and confidence >= 50.0 and rr >= 1.5 else "CANDIDATE"
                    if status == "CANDIDATE":
                        reason = list(reason) + ["Candidate only: executable risk parameters or minimum risk/reward did not pass validation."]

            latest_by_key[key] = {
                "signal_id": decision.get("decision_id") or data.get("report_id") or f"research-{symbol}-{timeframe}",
                "symbol": symbol,
                "direction": action,
                "entry_zone": entry,
                "invalidation_level": stop_loss,
                "target_zone": take_profit,
                "confidence": confidence,
                "reason": reason,
                "status": status,
                "execution_action": str(decision.get("action", "WAIT")).upper(),
                "timeframe": timeframe,
                "timestamp": data.get("timestamp") or data.get("created_at"),
                "evidence_state": {
                    "ACTIVE": "REAL_RESEARCH_SNAPSHOT",
                    "CANDIDATE": "REAL_RESEARCH_SNAPSHOT_CANDIDATE",
                    "BLOCKED": "REAL_RESEARCH_SNAPSHOT_BLOCKED",
                }.get(status, "REAL_RESEARCH_SNAPSHOT_BLOCKED"),
            }
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            continue
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
    data = LedgerManager().get_account_statement(f"{email}:USDT")
    return {
        "email": email,
        "balance_micro_usdt": data["balance"],
        "balance_usdt": round(data["balance"] / 1_000_000.0, 6),
        "currency": "USDT",
        "transactions": data["transactions"],
    }

@router.get("/billing/invoices")
def get_billing_invoices(session: Dict[str, Any] = Depends(get_user_session_and_enforce_tier)):
    from src.Application.Dashboard.billing_manager import BillingManager
    return {"invoices": BillingManager().get_user_invoices(session["email"])}


class UsdtDepositPayload(BaseModel):
    network: str
    tx_hash: str
    amount_usdt: float

@router.get("/wallet/deposits")
def get_my_deposits(session: Dict[str, Any] = Depends(get_user_session_and_enforce_tier)):
    from src.Application.Dashboard.deposit_manager import DepositManager
    return {"deposits": DepositManager().list_user(session["email"])}

@router.post("/wallet/deposits")
def submit_deposit(payload: UsdtDepositPayload, session: Dict[str, Any] = Depends(get_user_session_and_enforce_tier)):
    from src.Application.Dashboard.deposit_manager import DepositManager
    try:
        return DepositManager().create(session["email"],payload.network,payload.tx_hash,payload.amount_usdt)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


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
