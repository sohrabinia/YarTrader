import os
import json
import threading
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from src.Infrastructure.exceptions import ValidationException
from src.Application.Deployment.storage import YarTraderStorageManager

VALID_CATEGORIES = {
    "PLANS", "AI", "TRADING", "RESEARCH", "ANALYTICS", "PROP",
    "TOOLS", "EDUCATION", "REPORTS", "DATA", "SERVICES", "ENTERPRISE", "API"
}

VALID_STATUSES = {
    "DRAFT", "VISIBLE", "COMING_SOON", "ACTIVE", "PAUSED", "DISABLED", "ARCHIVED"
}

VALID_PRODUCT_TYPES = {
    "FREE", "SUBSCRIPTION", "ONE_TIME", "SERVICE", "CREDIT_PACKAGE", "ENTERPRISE", "COMING_SOON"
}

class BusinessCatalogManager:
    """
    Manages the authoritative YarTrader Business & Monetization Product Catalog.
    Provides thread-safe persistence, seed preservation of legacy pricing,
    comprehensive field validation, and secure administrative mutations.
    """
    def __init__(self, filepath: Optional[str] = None, audit_filepath: Optional[str] = None) -> None:
        storage_mgr = YarTraderStorageManager.get_manager()
        filepath = filepath or os.path.join(storage_mgr.get_runtime_dir(), "business_catalog.json")
        audit_filepath = audit_filepath or os.path.join(storage_mgr.get_runtime_dir(), "business_audit.json")
        self.filepath = filepath
        self.audit_filepath = audit_filepath
        self.lock = threading.RLock()
        os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
        os.makedirs(os.path.dirname(self.audit_filepath), exist_ok=True)
        self._ensure_file()

    def _ensure_file(self) -> None:
        with self.lock:
            if not os.path.exists(self.filepath):
                self._save(self._get_default_seeds())

    def _load(self) -> Dict[str, Any]:
        with self.lock:
            try:
                if os.path.exists(self.filepath):
                    with open(self.filepath, "r", encoding="utf-8") as f:
                        return json.load(f)
            except Exception:
                pass
            return {"products": {}}

    def _save(self, data: Dict[str, Any]) -> None:
        with self.lock:
            tmp_file = self.filepath + ".tmp"
            try:
                with open(tmp_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=4)
                os.replace(tmp_file, self.filepath)
            except Exception as e:
                if os.path.exists(tmp_file):
                    try:
                        os.remove(tmp_file)
                    except Exception:
                        pass
                raise e

    def _get_default_seeds(self) -> Dict[str, Any]:
        """Provides default plans and strategic future product seeds to represent the entire commercial ecosystem."""
        products = {
            "free": {
                "id": "free",
                "slug": "free",
                "name": "Free Researcher",
                "short_description": "Entry-level market data access.",
                "long_description": "Perfect for retail traders exploring high-level signals with basic structural analysis.",
                "category": "PLANS",
                "subcategory": None,
                "product_type": "FREE",
                "price": 0.0,
                "currency": "USD",
                "billing_period": "one-time",
                "features": ["3 Active Symbols", "Short Horizon Signals", "Read-only access to custom frames"],
                "limits": {"max_symbols": 3, "enabled_timeframes": ["Short"]},
                "visible": True,
                "purchasable": True,
                "status": "ACTIVE",
                "badge": "FREE",
                "cta_label": "Start Free",
                "display_order": 1,
                "featured": False
            },
            "daily": {
                "id": "daily",
                "slug": "daily",
                "name": "Daily Pulse Plan",
                "short_description": "Active intra-day intelligence updates.",
                "long_description": "Provides continuous updates to your dashboard with medium horizon perspectives.",
                "category": "PLANS",
                "subcategory": None,
                "product_type": "SUBSCRIPTION",
                "price": 29.0,
                "currency": "USD",
                "billing_period": "monthly",
                "features": ["10 Active Symbols", "Daily intelligence updates", "Daily cognitive insights"],
                "limits": {"max_symbols": 10, "enabled_timeframes": ["Short", "Medium"]},
                "visible": True,
                "purchasable": True,
                "status": "ACTIVE",
                "badge": "POPULAR",
                "cta_label": "Subscribe Daily",
                "display_order": 2,
                "featured": False
            },
            "pro": {
                "id": "pro",
                "slug": "pro",
                "name": "Professional Analyst",
                "short_description": "The professional standard for individual analysts.",
                "long_description": "Expands limits to 15 concurrent symbols and unlocks conversational SRE assistance.",
                "category": "PLANS",
                "subcategory": None,
                "product_type": "SUBSCRIPTION",
                "price": 79.0,
                "currency": "USD",
                "billing_period": "monthly",
                "features": ["15 Active Symbols", "Short & Medium Horizon Signals", "Full read-only custom frames", "Conversational AI Assistant"],
                "limits": {"max_symbols": 15, "enabled_timeframes": ["Short", "Medium"]},
                "visible": True,
                "purchasable": True,
                "status": "ACTIVE",
                "badge": "RECOMMENDED",
                "cta_label": "Subscribe Pro",
                "display_order": 3,
                "featured": True
            },
            "institutional": {
                "id": "institutional",
                "slug": "institutional",
                "name": "Institutional SCM Terminal",
                "short_description": "The complete cognitive trading workspace.",
                "long_description": "Uncapped 50 symbols workspace, including macro/micro timeframes, and dedicated priority support.",
                "category": "PLANS",
                "subcategory": None,
                "product_type": "SUBSCRIPTION",
                "price": 299.0,
                "currency": "USD",
                "billing_period": "monthly",
                "features": ["50 Active Symbols", "All Horizon Signals (Micro to Macro)", "Unlimited custom frames", "Priority SRE support & dedicated server access"],
                "limits": {"max_symbols": 50, "enabled_timeframes": ["Micro", "Short", "Medium", "Macro"]},
                "visible": True,
                "purchasable": True,
                "status": "ACTIVE",
                "badge": "ENTERPRISE",
                "cta_label": "Go Institutional",
                "display_order": 4,
                "featured": False
            },
            "ai-analyst-pro": {
                "id": "ai-analyst-pro",
                "slug": "ai-analyst-pro",
                "name": "AI Analyst Pro Module",
                "short_description": "Autonomous deep-learning analyst agent.",
                "long_description": "A standalone cognitive background agent that performs continuous correlation reviews.",
                "category": "AI",
                "subcategory": "ANALYSIS",
                "product_type": "COMING_SOON",
                "price": 49.0,
                "currency": "USD",
                "billing_period": "monthly",
                "features": ["Autonomous correlation scanning", "Instant PDF intelligence reports", "Continuous background SRE audit logs"],
                "limits": {},
                "visible": True,
                "purchasable": False,
                "status": "COMING_SOON",
                "badge": "COMING SOON",
                "cta_label": "Coming Soon",
                "display_order": 5,
                "featured": False
            },
            "prop-assistant": {
                "id": "prop-assistant",
                "slug": "prop-assistant",
                "name": "Prop Challenge Assistant",
                "short_description": "Evaluation rules and drawdown advisory guide.",
                "long_description": "Guides you through prop firm rules, tracking live exposures and alerting on drawdown risk.",
                "category": "PROP",
                "subcategory": "EVALUATION",
                "product_type": "COMING_SOON",
                "price": 99.0,
                "currency": "USD",
                "billing_period": "monthly",
                "features": ["Factual rule imports", "Daily drawdown warning gates", "Psychological performance scorecard"],
                "limits": {},
                "visible": True,
                "purchasable": False,
                "status": "COMING_SOON",
                "badge": "COMING SOON",
                "cta_label": "Coming Soon",
                "display_order": 6,
                "featured": False
            },
            "strategy-lab": {
                "id": "strategy-lab",
                "slug": "strategy-lab",
                "name": "Strategy Lab & Backtester",
                "short_description": "Advanced historical strategy testing lab.",
                "long_description": "Sandbox to code, dry-run, and optimize custom timeframes and indicator weights safely.",
                "category": "TOOLS",
                "subcategory": "BACKTEST",
                "product_type": "COMING_SOON",
                "price": 119.0,
                "currency": "USD",
                "billing_period": "monthly",
                "features": ["Multi-timeframe historical sandbox", "Weight optimization advisor", "Risk decay simulation logs"],
                "limits": {},
                "visible": True,
                "purchasable": False,
                "status": "COMING_SOON",
                "badge": "COMING SOON",
                "cta_order": 7,
                "featured": False
            }
        }
        return {"products": products}

    def list_products(self, include_invisible: bool = False) -> List[Dict[str, Any]]:
        with self.lock:
            data = self._load()
            prods = list(data.get("products", {}).values())
            if not include_invisible:
                prods = [p for p in prods if p.get("visible", True)]
            prods.sort(key=lambda x: x.get("display_order", 999))
            return prods

    def get_product(self, product_id: str) -> Optional[Dict[str, Any]]:
        with self.lock:
            data = self._load()
            return data.get("products", {}).get(product_id)

    def validate_product(self, product: Dict[str, Any]) -> None:
        """Enforces strict financial, type, and state-combination validation rules."""
        required = ["id", "slug", "name", "category", "price", "currency", "status"]
        for field in required:
            if field not in product or product[field] is None:
                raise ValidationException(f"Missing required product field: {field}")

        # Validate types & prices
        if not isinstance(product["price"], (int, float)):
            raise ValidationException("Price must be a valid numerical value.")
        if product["price"] < 0:
            raise ValidationException("Financial safety rule violation: negative prices are strictly forbidden.")

        if not product["currency"] or not isinstance(product["currency"], str):
            raise ValidationException("Invalid currency designation.")

        # Validate categorizations
        category = product["category"].upper()
        if category not in VALID_CATEGORIES:
            raise ValidationException(f"Invalid category: {product['category']}. Must be one of {VALID_CATEGORIES}")

        status = product["status"].upper()
        if status not in VALID_STATUSES:
            raise ValidationException(f"Invalid status: {product['status']}. Must be one of {VALID_STATUSES}")

        # State combinations enforcement
        visible = product.get("visible", True)
        purchasable = product.get("purchasable", False)

        if status == "COMING_SOON" and purchasable:
            raise ValidationException("Invalid state combination: product cannot be both COMING_SOON and purchasable.")

        if status == "DRAFT" and (visible or purchasable):
            raise ValidationException("Invalid state combination: draft products must be hidden and non-purchasable.")

        if status == "DISABLED" and purchasable:
            raise ValidationException("Invalid state combination: disabled products must be non-purchasable.")

    def save_product(self, product: Dict[str, Any], admin_email: str = "sre-admin@yartrader.app") -> Dict[str, Any]:
        """
        Atomically saves or updates a product inside the catalog.
        Validates data first and writes secure audit logs for critical commercial changes.
        """
        self.validate_product(product)
        product_id = product["id"]

        with self.lock:
            data = self._load()
            old_product = data.get("products", {}).get(product_id)

            # Enforce audit logs for modified fields
            fields_to_audit = ["price", "visible", "purchasable", "status"]
            if old_product:
                for field in fields_to_audit:
                    old_val = old_product.get(field)
                    new_val = product.get(field)
                    if old_val != new_val:
                        self._write_audit(admin_email, product_id, field, old_val, new_val)
            else:
                # Log creation
                self._write_audit(admin_email, product_id, "lifecycle", None, "CREATED")

            # Update datetime stamps
            now_iso = datetime.now(timezone.utc).isoformat()
            if not old_product:
                product["created_at"] = now_iso
            else:
                product["created_at"] = old_product.get("created_at", now_iso)
            product["updated_at"] = now_iso

            data["products"][product_id] = product
            self._save(data)
            return product

    def delete_product(self, product_id: str, admin_email: str = "sre-admin@yartrader.app") -> bool:
        """Deletes a product from the database safely and logs SRE audit trail."""
        with self.lock:
            data = self._load()
            if product_id not in data.get("products", {}):
                return False

            self._write_audit(admin_email, product_id, "lifecycle", "ACTIVE", "DELETED")
            del data["products"][product_id]
            self._save(data)
            return True

    def _write_audit(self, admin_email: str, product_id: str, field: str, old_value: Any, new_value: Any) -> None:
        """Writes secure transaction audit trail records to prevent database spoofing."""
        audit_record = {
            "admin": admin_email,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "product_id": product_id,
            "field": field,
            "old_value": old_value,
            "new_value": new_value
        }
        with self.lock:
            try:
                logs = []
                if os.path.exists(self.audit_filepath):
                    with open(self.audit_filepath, "r", encoding="utf-8") as f:
                        logs = json.load(f)
                logs.append(audit_record)

                tmp_audit = self.audit_filepath + ".tmp"
                with open(tmp_audit, "w", encoding="utf-8") as f:
                    json.dump(logs, f, indent=4)
                os.replace(tmp_audit, self.audit_filepath)
            except Exception:
                pass
