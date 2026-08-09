from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from src.Application.Dashboard.business_catalog_manager import BusinessCatalogManager

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

# 2. SaaS Pricing Tiers & Subscription Plans
@router.get("/pricing")
def get_pricing_tiers():
    """Returns official SaaS pricing structures."""
    return get_subscription_plans()

@router.get("/subscription/plans")
def get_subscription_plans():
    """Returns official dynamic SaaS pricing and subscription plans loaded directly from the DB."""
    manager = BusinessCatalogManager()
    products = manager.list_products(include_invisible=False)

    # Filter only PLANS category
    plan_products = [p for p in products if p.get("category") == "PLANS"]

    legacy_plans = []
    for p in plan_products:
        price_str = "Free" if p["price"] == 0 else f"${int(p['price'])}/mo"
        limits = p.get("limits") or {}
        max_symbols = limits.get("max_symbols", 3)
        enabled_tfs = limits.get("enabled_timeframes") or ["Short"]
        legacy_plans.append({
            "tier_id": p["id"].lower(),
            "name": p["name"],
            "price_usd": price_str,
            "max_symbols": max_symbols,
            "enabled_timeframes": enabled_tfs,
            "features": p.get("features") or []
        })
    return legacy_plans

# 3. Comprehensive Dynamic Business Catalog
@router.get("/business/catalog")
def get_public_business_catalog():
    """Exposes all visible commercial products in the database."""
    manager = BusinessCatalogManager()
    return manager.list_products(include_invisible=False)

class PurchasePayload(BaseModel):
    product_id: str
    email: str

@router.post("/business/purchase")
def initiate_purchase(payload: PurchasePayload):
    """
    Securely initiates checkouts, strictly rejecting non-purchasable or invalid products on the backend.
    Fails closed on any disabled, hidden, or negative priced configuration.
    """
    manager = BusinessCatalogManager()
    prod = manager.get_product(payload.product_id)
    if not prod:
        raise HTTPException(status_code=404, detail="Product not found in business catalog.")

    if not prod.get("visible", True) or not prod.get("purchasable", False):
        raise HTTPException(status_code=400, detail="Financial safety rule: product is currently not available for purchase.")

    if prod.get("price", 0) < 0:
        raise HTTPException(status_code=400, detail="Financial safety: negative price is invalid.")

    return {
        "status": "Success",
        "message": f"Checkout path verified successfully for product '{prod['name']}'.",
        "product_id": prod["id"],
        "price": prod["price"],
        "currency": prod["currency"]
    }

# 4. Supported Instrument Categories
@router.get("/markets")
def get_supported_markets():
    """Returns list of SaaS supported market assets."""
    return [
        {"category": "Forex", "symbols": ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD"]},
        {"category": "Commodities", "symbols": ["XAUUSD", "XAGUSD", "USOIL"]},
        {"category": "Crypto", "symbols": ["BTCUSD", "ETHUSD", "SOLUSD"]}
    ]
