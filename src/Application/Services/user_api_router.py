import os
from fastapi import APIRouter, HTTPException, Header, Depends
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from src.ShadowTrading.Engine.PredictiveShadowEngine import PredictiveShadowEngine
from src.Application.Dashboard.auth_service import global_auth_service
from src.Growth.Agents.SecurityCostAgents import TierEntitlementMiddleware

router = APIRouter(prefix="/api/user", tags=["User Trading API"])

entitlement_middleware = TierEntitlementMiddleware()

def get_user_session_and_enforce_tier(authorization: Optional[str] = Header(None), horizon: Optional[str] = None) -> Dict[str, Any]:
    """
    FastAPI Router dependency that extracts active session token, retrieves trusted user
    subscription tier from server state, and verifies access boundaries against TierEntitlementMiddleware.
    """
    is_production = (os.environ.get("TRADEYAR_ENV") == "production" or
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
    from src.ShadowTrading.Engine.SymbolRegistry import SymbolRegistry
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


# 1. Clean User Signals (Micro, Short, Medium, Macro views)
@router.get("/signals")
def get_user_signals(market: Optional[str] = None, horizon: Optional[str] = None, session: Dict[str, Any] = Depends(get_user_session_and_enforce_tier)):
    """Exposes clean AI Signals filterable by asset and simplified horizons (Micro, Short, Medium, Macro)."""
    engine = PredictiveShadowEngine.get_instance()
    signals = engine.get_clean_signals()

    # Horizons map to custom tick frames:
    # Micro = [1], Short = [4], Medium = [16, 64], Macro = [256, 1024]
    allowed_frames = []
    if horizon:
        h_lower = horizon.lower()
        if "micro" in h_lower:
            allowed_frames = [1]
        elif "short" in h_lower:
            allowed_frames = [4]
        elif "medium" in h_lower:
            allowed_frames = [16, 64]
        elif "macro" in h_lower:
            allowed_frames = [256, 1024]

    mapped = []
    for s in signals:
        trade_id = s.get("shadow_trade_id")
        trade = next((t for t in engine.trades if t.trade_id == trade_id), None)

        # Filter Asset Category
        if market:
            m_lower = market.lower()
            if m_lower == "gold" and "XAU" not in s["symbol"]:
                continue
            if m_lower == "bitcoin" and "BTC" not in s["symbol"]:
                continue
            if m_lower == "euro" and "EUR" not in s["symbol"]:
                continue

        if allowed_frames and trade and trade.custom_time_structure not in allowed_frames:
            continue

        # Map to simplified horizon name
        tf = trade.custom_time_structure if trade else 64
        horizon_name = "Micro" if tf == 1 else ("Short" if tf == 4 else ("Medium" if tf in [16, 64] else "Macro"))

        mapped.append({
            "signal_id": s["signal_id"],
            "symbol": s["symbol"],
            "direction": s["direction"],
            "entry_zone": s["entry_zone"],
            "invalidation_level": s["invalidation_level"],
            "target_zone": s["target_zone"],
            "confidence": s["confidence"],
            "reason": s["reason"],
            "status": s["status"],
            "horizon": horizon_name
        })

    return mapped

# 2. Equity Growth Simulator
@router.get("/equity-simulation")
def simulate_equity_growth(initial_balance: float = 10000.0, monthly_growth_pct: float = 8.5, months: int = 6, session: Dict[str, Any] = Depends(get_user_session_and_enforce_tier)):
    """Generates sequential equity projection simulation records for SaaS dashboard charts."""
    series = []
    current = initial_balance
    series.append({
        "month": "M0",
        "balance": round(current, 2)
    })
    for i in range(1, months + 1):
        current *= (1.0 + (monthly_growth_pct / 100.0))
        series.append({
            "month": f"M{i}",
            "balance": round(current, 2)
        })
    return {
        "initial_balance": initial_balance,
        "final_balance": round(current, 2),
        "total_growth_pct": round(((current - initial_balance) / initial_balance * 100.0), 2),
        "projection": series
    }

# 3. Clean User Horizon Reports
@router.get("/reports")
def get_user_horizon_reports(market: Optional[str] = None, session: Dict[str, Any] = Depends(get_user_session_and_enforce_tier)):
    """Exposes simplified non-technical performance statistics per asset & horizon."""
    engine = PredictiveShadowEngine.get_instance()

    contexts_to_report = engine.contexts.values()
    if market:
        m_lower = market.lower()
        if m_lower == "gold":
            contexts_to_report = [c for c in contexts_to_report if "XAU" in c.symbol]
        elif m_lower == "bitcoin":
            contexts_to_report = [c for c in contexts_to_report if "BTC" in c.symbol]
        elif m_lower == "euro":
            contexts_to_report = [c for c in contexts_to_report if "EUR" in c.symbol]

    horizon_reports = []
    for ctx in contexts_to_report:
        stats = ctx.get_statistics()
        tf = ctx.timeframe
        horizon_name = "Micro" if tf == 1 else ("Short" if tf == 4 else ("Medium" if tf in [16, 64] else "Macro"))
        horizon_reports.append({
            "asset": ctx.symbol,
            "horizon": horizon_name,
            "win_rate": stats["win_rate_pct"],
            "total_cycles": stats["completed_trades"],
            "average_confidence": stats["average_confidence_pct"]
        })

    return horizon_reports

# 4. Multi-Timeframe Decision Fusion Signal
@router.get("/fusion/{symbol}")
def get_symbol_decision_fusion(symbol: str, session: Dict[str, Any] = Depends(get_user_session_and_enforce_tier)):
    """Synthesizes active multi-timeframe horizon alignment signals solely from internal frames."""
    engine = PredictiveShadowEngine.get_instance()
    try:
        fusion = engine.runtime_manager.synthesize_symbol_decision_fusion(symbol)
        return fusion
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
