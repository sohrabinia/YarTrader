import os
import json
from typing import Dict, List, Any, Tuple

REGISTRY_FILE = "runtime_logs/symbols_registry.json"

def parse_market_universe_yaml(content: str) -> Dict[str, Any]:
    """Pure-Python YAML parser for market_universe.yaml mapping."""
    result = {}
    current_category = None
    for line in content.splitlines():
        strip_line = line.strip()
        if not strip_line or strip_line.startswith("#"):
            continue

        indent = len(line) - len(line.lstrip())
        if indent == 0:
            continue # ignore market_universe root tag
        elif indent == 2:
            current_category = strip_line.replace(":", "").strip()
            result[current_category] = {}
        elif indent == 4:
            if ":" in strip_line:
                symbol, payload_str = strip_line.split(":", 1)
                symbol = symbol.strip()
                payload_str = payload_str.strip()

                try:
                    # Clean up JSON-like format
                    json_str = payload_str
                    # Ensure keys are quoted
                    for key in ["provider", "enabled", "timeframes"]:
                        json_str = json_str.replace(key, f'"{key}"')
                    # Convert python boolean strings to json
                    json_str = json_str.replace("true", "true").replace("false", "false")
                    info = json.loads(json_str)
                except Exception:
                    # Fallback manual extraction
                    provider = "MT5"
                    if "Crypto" in payload_str:
                        provider = "Crypto"
                    enabled = "enabled: false" not in payload_str
                    timeframes = ["H1", "H4"]
                    if "[" in payload_str:
                        tf_part = payload_str.split("[", 1)[1].split("]", 1)[0]
                        timeframes = [t.strip().replace('"', '').replace("'", "") for t in tf_part.split(",")]
                    info = {"provider": provider, "enabled": enabled, "timeframes": timeframes}

                if current_category:
                    result[current_category][symbol] = info
    return {"market_universe": result}


class SymbolRegistry:
    """
    Manages active symbols, their asset class classification, and assigned timeframes dynamically.
    Enforces maximum 50 active symbols universe limit.
    Persists config cleanly across restarts.
    """
    _instance = None

    @classmethod
    def get_instance(cls) -> "SymbolRegistry":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        self.max_symbols = 50
        self.registry: Dict[str, Dict[str, Any]] = {}
        os.makedirs("runtime_logs", exist_ok=True)
        self.load_registry()

    def load_registry(self) -> None:
        # Check if saved registry config file exists
        if os.path.exists(REGISTRY_FILE):
            try:
                with open(REGISTRY_FILE, "r", encoding="utf-8") as f:
                    self.registry = json.load(f)
                return
            except Exception:
                pass

        # Load from config/market_universe.yaml if exists
        yaml_path = "config/market_universe.yaml"
        if os.path.exists(yaml_path):
            try:
                with open(yaml_path, "r", encoding="utf-8") as f:
                    content = f.read()
                universe_data = parse_market_universe_yaml(content)

                market_data = universe_data.get("market_universe", {})
                for asset_class, symbols in market_data.items():
                    for sym, info in symbols.items():
                        self.registry[sym.upper()] = {
                            "active": info.get("enabled", True),
                            "asset_class": asset_class,
                            "provider": info.get("provider", "MT5"),
                            "timeframes": info.get("timeframes", ["H1", "H4"])
                        }
                self.save_registry()
                return
            except Exception as e:
                print(f"Warning: Failed to load market_universe.yaml: {e}")

        # Default fallback registry configuration
        self.registry = {
            "XAUUSD": {"active": True, "asset_class": "Commodities", "provider": "MT5", "timeframes": ["H1", "H4"]},
            "EURUSD": {"active": True, "asset_class": "Forex", "provider": "MT5", "timeframes": ["H1"]},
            "GBPUSD": {"active": True, "asset_class": "Forex", "provider": "MT5", "timeframes": ["H1"]},
            "BTCUSD": {"active": True, "asset_class": "Crypto", "provider": "Crypto", "timeframes": ["H1", "H4"]},
            "ETHUSD": {"active": True, "asset_class": "Crypto", "provider": "Crypto", "timeframes": ["H1", "H4"]}
        }
        self.save_registry()

    def save_registry(self) -> None:
        with open(REGISTRY_FILE, "w", encoding="utf-8") as f:
            json.dump(self.registry, f, indent=4)

    def get_all_registered(self) -> Dict[str, Dict[str, Any]]:
        return self.registry

    def get_timeframe_policy(self, asset_class: str) -> List[str]:
        """Resolves timeframe policies per asset class."""
        ac_lower = asset_class.lower()
        if "forex" in ac_lower:
            return ["M15", "H1", "H4", "D1"]
        elif "commodity" in ac_lower:
            return ["M15", "H1", "H4", "D1"]
        elif "indices" in ac_lower or "index" in ac_lower:
            return ["M5", "M15", "H1", "H4", "D1"]
        elif "crypto" in ac_lower:
            return ["M15", "H1", "H4", "D1"]
        return ["H1"]

    def get_active_matrix(self) -> List[Tuple[str, str, str, str]]:
        """Resolves execution matrix tuples of (symbol, timeframe, asset_class, provider)"""
        matrix = []
        active_count = 0
        for symbol, info in sorted(self.registry.items()):
            if info.get("active", True):
                if active_count >= self.max_symbols:
                    break
                active_count += 1
                asset_class = info.get("asset_class", "Forex")
                provider = info.get("provider", "MT5")
                tfs = info.get("timeframes") or self.get_timeframe_policy(asset_class)
                for tf in tfs:
                    matrix.append((symbol, tf, asset_class, provider))
        return matrix

    def register_symbol(self, symbol: str, timeframes: List[str], asset_class: str = "Forex", provider: str = "MT5") -> None:
        symbol_upper = symbol.upper()
        active_count = sum(1 for sym, info in self.registry.items() if info.get("active", True) and sym != symbol_upper)
        if active_count >= self.max_symbols:
            raise ValueError(f"Hard SRE limit reached: Maximum {self.max_symbols} active symbols allowed concurrent execution.")

        self.registry[symbol_upper] = {
            "active": True,
            "asset_class": asset_class,
            "provider": provider,
            "timeframes": timeframes
        }
        self.save_registry()

    def set_symbol_active(self, symbol: str, active: bool) -> None:
        symbol_upper = symbol.upper()
        if symbol_upper in self.registry:
            if active:
                active_count = sum(1 for sym, info in self.registry.items() if info.get("active", True) and sym != symbol_upper)
                if active_count >= self.max_symbols:
                    raise ValueError(f"Hard SRE limit reached: Maximum {self.max_symbols} active symbols allowed concurrent execution.")
            self.registry[symbol_upper]["active"] = active
            self.save_registry()
