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
    return [
        {
            "tier_id": "basic",
            "name": "Basic Researcher",
            "price_usd": "Free",
            "features": ["3 Active Symbols", "Short Horizon Signals", "Read-only access to custom frames"]
        },
        {
            "tier_id": "pro",
            "name": "Professional Analyst",
            "price_usd": "79/mo",
            "features": ["15 Active Symbols", "Short & Medium Horizon Signals", "Full read-only custom frames", "Conversational AI Assistant"]
        },
        {
            "tier_id": "institutional",
            "name": "Institutional SCM Terminal",
            "price_usd": "299/mo",
            "features": ["30 Active Symbols", "All Horizon Signals (Micro to Macro)", "Unlimited custom frames", "Priority SRE support & dedicated server access"]
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
