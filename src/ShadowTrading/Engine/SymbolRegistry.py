import os
import json
from typing import Dict, List, Any, Tuple
from src.Application.Deployment.storage import YarTraderStorageManager

REGISTRY_FILE = os.path.join(YarTraderStorageManager.get_manager().get_runtime_dir(), "symbols_registry.json")

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


import threading

class SymbolRegistry:
    """
    Manages active symbols, their asset class classification, and assigned timeframes dynamically.
    Enforces maximum active symbols universe limit dynamically resolved from system_limits.yaml.
    Persists config cleanly across restarts.
    """
    _instance = None
    _singleton_lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> "SymbolRegistry":
        with cls._singleton_lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def _load_max_symbols(self) -> int:
        yaml_path = "config/system_limits.yaml"
        if os.path.exists(yaml_path):
            try:
                with open(yaml_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("max_active_symbols:"):
                            val_str = line.split(":", 1)[1].strip()
                            return int(val_str)
            except Exception:
                pass
        return 30

    def __init__(self) -> None:
        self.max_symbols = self._load_max_symbols()
        self.registry: Dict[str, Dict[str, Any]] = {}
        self.lock = threading.RLock()
        os.makedirs(YarTraderStorageManager.get_manager().get_runtime_dir(), exist_ok=True)
        self.load_registry()

    def _enforce_max_active_limit(self) -> None:
        """Enforces that the total active symbols in the registry does not exceed max_symbols limit."""
        core_priorities = {"XAUUSD", "EURUSD", "GBPUSD", "BTCUSD", "ETHUSD"}
        active_symbols = [sym for sym, info in self.registry.items() if info.get("active", True)]

        if len(active_symbols) > self.max_symbols:
            non_core_actives = [sym for sym in active_symbols if sym not in core_priorities]
            to_deactivate_count = len(active_symbols) - self.max_symbols
            # Deactivate from the end of non_core list to bring total active to max_symbols
            for sym in non_core_actives[-to_deactivate_count:]:
                self.registry[sym]["active"] = False

    def load_registry(self) -> None:
        with self.lock:
            # Check if saved registry config file exists
            if os.path.exists(REGISTRY_FILE):
                try:
                    with open(REGISTRY_FILE, "r", encoding="utf-8") as f:
                        self.registry = json.load(f)
                    self._enforce_max_active_limit()
                    self.save_registry()
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
                self._enforce_max_active_limit()
                self.save_registry()
                return
            except Exception as e:
                print(f"Warning: Failed to load market_universe.yaml: {e}")

        # Default fallback registry configuration
        self.registry = {
            "XAUUSD": {"active": True, "asset_class": "Commodities", "provider": "MT5", "timeframes": ["Tick", "M1", "M5", "M15", "H1", "H4", "D1", "W1", "MN1"]},
            "EURUSD": {"active": True, "asset_class": "Forex", "provider": "MT5", "timeframes": ["Tick", "M1", "M5", "M15", "H1", "H4", "D1", "W1", "MN1"]},
            "GBPUSD": {"active": True, "asset_class": "Forex", "provider": "MT5", "timeframes": ["Tick", "M1", "M5", "M15", "H1", "H4", "D1", "W1", "MN1"]},
            "BTCUSD": {"active": True, "asset_class": "Crypto", "provider": "Crypto", "timeframes": ["Tick", "M1", "M5", "M15", "H1", "H4", "D1", "W1", "MN1"]},
            "ETHUSD": {"active": True, "asset_class": "Crypto", "provider": "Crypto", "timeframes": ["Tick", "M1", "M5", "M15", "H1", "H4", "D1", "W1", "MN1"]}
        }
        self.save_registry()

    def save_registry(self) -> None:
        with self.lock:
            with open(REGISTRY_FILE, "w", encoding="utf-8") as f:
                json.dump(self.registry, f, indent=4)

    def get_all_registered(self) -> Dict[str, Dict[str, Any]]:
        with self.lock:
            return self.registry.copy()

    def get_timeframe_policy(self, asset_class: str) -> List[str]:
        """Resolves timeframe policies per asset class. Returns all 9 timeframes."""
        from src.Infrastructure.Configuration.config import ConfigurationManager
        config = ConfigurationManager.get_config()
        if not config.tick_chart_analysis_enabled:
            return ["M1", "M5", "M15", "H1", "H4", "D1", "W1", "MN1"]
        return ["Tick", "M1", "M5", "M15", "H1", "H4", "D1", "W1", "MN1"]

    def get_active_matrix(self) -> List[Tuple[str, str, str, str]]:
        """Resolves execution matrix tuples of (symbol, timeframe, asset_class, provider)"""
        from src.Infrastructure.Configuration.config import ConfigurationManager
        config = ConfigurationManager.get_config()
        with self.lock:
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
                        if tf == "Tick" and not config.tick_chart_analysis_enabled:
                            continue
                        matrix.append((symbol, tf, asset_class, provider))
            return matrix

    def register_symbol(self, symbol: str, timeframes: List[str], asset_class: str = "Forex", provider: str = "MT5") -> None:
        with self.lock:
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
        with self.lock:
            symbol_upper = symbol.upper()
            if symbol_upper in self.registry:
                if active:
                    active_count = sum(1 for sym, info in self.registry.items() if info.get("active", True) and sym != symbol_upper)
                    if active_count >= self.max_symbols:
                        raise ValueError(f"Hard SRE limit reached: Maximum {self.max_symbols} active symbols allowed concurrent execution.")
                self.registry[symbol_upper]["active"] = active
                self.save_registry()
