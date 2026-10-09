import os

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
    """Return live registry counts and never invent historical or uptime metrics."""
    from src.Market.Universe.symbol_registry import SymbolRegistry

    disclaimer = (
        "Simulated performance results have inherent limitations and do not represent "
        "actual trading. Historical trade counts and uptime are omitted unless measured."
    )
    try:
        registry = SymbolRegistry.get_instance()
        registered = registry.get_all_registered()
        active = {
            symbol: info for symbol, info in registered.items()
            if bool(info.get("active", info.get("enabled", False)))
        }
        matrix = registry.get_active_matrix()
        active_providers = {
            str(info.get("provider", "MT5")).upper() for info in active.values()
        }
        supported_count = len(registered)
        return {
            "symbols_active": len(active),
            "symbols_supported_count": supported_count,
            "timeframes_active": len({str(item[1]).upper() for item in matrix}),
            "research_contexts": len(matrix),
            "providers": {
                "mt5": "ENABLED" if "MT5" in active_providers else "DISABLED",
                "crypto_provider": "ENABLED" if any("CRYPTO" in p for p in active_providers) else "DISABLED",
            },
            "runtime_mode": os.getenv("RG_ENV", os.getenv("YARTRADER_ENV", "production")).upper(),
            # This card is labelled "Supported Market Symbols", not "currently active".
            "active_markets_count": supported_count,
            "historical_simulated_trades": None,
            "platform_uptime_pct": None,
            "apes_fin_compliant": None,
            "metrics_status": "LIVE_REGISTRY",
            "compliance_disclaimer": disclaimer,
        }
    except Exception:
        return {
            "symbols_active": 0,
            "symbols_supported_count": 0,
            "timeframes_active": 0,
            "research_contexts": 0,
            "providers": {"mt5": "UNKNOWN", "crypto_provider": "UNKNOWN"},
            "runtime_mode": os.getenv("RG_ENV", os.getenv("YARTRADER_ENV", "production")).upper(),
            "active_markets_count": 0,
            "historical_simulated_trades": None,
            "platform_uptime_pct": None,
            "apes_fin_compliant": None,
            "metrics_status": "DATA_UNAVAILABLE",
            "compliance_disclaimer": disclaimer,
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

    if prod.get("status", "ACTIVE") != "ACTIVE":
        raise HTTPException(status_code=400, detail="Financial safety rule: product status is not active.")

    if prod.get("price", 0) < 0:
        raise HTTPException(status_code=400, detail="Financial safety: negative price is invalid.")

    # Secure boundary conversion from catalog presentation float to transactional integer cents
    cents = int(prod["price"] * 100)

    return {
        "status": "Success",
        "message": f"Checkout path verified successfully for product '{prod['name']}'.",
        "product_id": prod["id"],
        "price_cents": cents,
        "price": prod["price"],
        "currency": prod["currency"]
    }

# 4. Supported Instrument Categories
@router.get("/markets")
def get_supported_markets():
    """Return the canonical supported universe with current enablement separated."""
    from src.Market.Universe.symbol_registry import SymbolRegistry

    registry = SymbolRegistry.get_instance()
    grouped: Dict[str, Dict[str, List[str]]] = {}
    for symbol, info in registry.get_all_registered().items():
        category = str(info.get("asset_class", "Forex"))
        group = grouped.setdefault(category, {"symbols": [], "active_symbols": []})
        group["symbols"].append(str(symbol).upper())
        if bool(info.get("active", info.get("enabled", False))):
            group["active_symbols"].append(str(symbol).upper())

    return [
        {
            "category": category,
            "symbols": sorted(values["symbols"]),
            "active_symbols": sorted(values["active_symbols"]),
        }
        for category, values in sorted(grouped.items())
    ]
