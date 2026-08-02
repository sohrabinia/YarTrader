from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List, Optional

router = APIRouter(prefix="/api/public", tags=["Public SaaS API"])

class SocialLoginPayload(BaseModel):
    email: str
    provider_id: str
    name: Optional[str] = ""

# 1. Supported Markets & Stats
@router.get("/metrics")
def get_public_metrics():
    """Returns compliant SaaS platform metrics and performance stats."""
    return {
        "symbols_active": 50,
        "timeframes_active": 4,
        "research_contexts": 200,
        "providers": {
            "mt5": "CONNECTED",
            "crypto_provider": "CONNECTED"
        },
        "runtime_mode": "PRODUCTION",
        "active_markets_count": 30,
        "historical_simulated_trades": 125420,
        "platform_uptime_pct": 99.9,
        "apes_fin_compliant": True,
        "compliance_disclaimer": "Simulated performance results have certain inherent limitations. Unlike an actual performance record, simulated results do not represent actual trading."
    }

# 2. SaaS Pricing Tiers
@router.get("/pricing")
def get_pricing_tiers():
    """Returns official SaaS pricing structures."""
    return get_subscription_plans()

@router.get("/subscription/plans")
def get_subscription_plans():
    """Returns official dynamic SaaS pricing and subscription plans."""
    return [
        {
            "tier_id": "free",
            "name": "Free Researcher",
            "price_usd": "Free",
            "max_symbols": 3,
            "enabled_timeframes": ["Short"],
            "features": ["3 Active Symbols", "Short Horizon Signals", "Read-only access to custom frames"]
        },
        {
            "tier_id": "daily",
            "name": "Daily Pulse Plan",
            "price_usd": "$29/mo",
            "max_symbols": 10,
            "enabled_timeframes": ["Short", "Medium"],
            "features": ["10 Active Symbols", "Daily intelligence updates", "Daily cognitive insights"]
        },
        {
            "tier_id": "pro",
            "name": "Professional Analyst",
            "price_usd": "$79/mo",
            "max_symbols": 15,
            "enabled_timeframes": ["Short", "Medium"],
            "features": ["15 Active Symbols", "Short & Medium Horizon Signals", "Full read-only custom frames", "Conversational AI Assistant"]
        },
        {
            "tier_id": "institutional",
            "name": "Institutional SCM Terminal",
            "price_usd": "$299/mo",
            "max_symbols": 50,
            "enabled_timeframes": ["Micro", "Short", "Medium", "Macro"],
            "features": ["50 Active Symbols", "All Horizon Signals (Micro to Macro)", "Unlimited custom frames", "Priority SRE support & dedicated server access"]
        }
    ]

# 3. Supported Instrument Categories
@router.get("/markets")
def get_supported_markets():
    """Returns list of SaaS supported market assets."""
    return [
        {"category": "Forex", "symbols": ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD"]},
        {"category": "Commodities", "symbols": ["XAUUSD", "XAGUSD", "USOIL"]},
        {"category": "Crypto", "symbols": ["BTCUSD", "ETHUSD", "SOLUSD"]}
    ]
