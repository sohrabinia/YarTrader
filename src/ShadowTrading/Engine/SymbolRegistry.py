import os
import json
import threading
from typing import Dict, List, Any, Tuple

REGISTRY_FILE = "runtime_logs/symbols_registry.json"

CANONICAL_30_SYMBOLS = {
    "XAUUSD", "XAGUSD", "EURUSD", "USDJPY", "GBPUSD", "USDCHF", "AUDUSD", "USDCAD",
    "NZDUSD", "EURJPY", "GBPJPY", "EURGBP", "AUDJPY", "EURCHF", "CADJPY",
    "BTCUSD", "ETHUSD", "SOLUSD", "BNBUSD", "XRPUSD", "ADAUSD", "DOGEUSD", "AVAXUSD",
    "DOTUSD", "LINKUSD", "LTCUSD", "BCHUSD", "NEARUSD", "UNIUSD", "ATOMUSD"
}

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
    Enforces canonical exact 30-symbol set invariant. Fails closed if market universe configuration
    is missing, malformed, or violates exact 30-symbol set equality.
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
        os.makedirs("runtime_logs", exist_ok=True)
        self.load_registry()

    def _validate_canonical_30_invariant(self, symbols_dict: Dict[str, Any]) -> None:
        """Enforces exact set equality with CANONICAL_30_SYMBOLS."""
        loaded_symbols = set(sym.upper() for sym in symbols_dict.keys())
        if loaded_symbols != CANONICAL_30_SYMBOLS:
            missing = CANONICAL_30_SYMBOLS - loaded_symbols
            extra = loaded_symbols - CANONICAL_30_SYMBOLS
            raise ValueError(
                f"Market universe canonical exact-30 invariant violated! "
                f"Count: {len(loaded_symbols)}/30. Missing: {missing}. Extra: {extra}."
            )

    def load_registry(self) -> None:
        with self.lock:
            yaml_path = "config/market_universe.yaml"
            if not os.path.exists(yaml_path):
                raise RuntimeError(f"Fail Closed: Configuration file '{yaml_path}' is missing.")

            try:
                with open(yaml_path, "r", encoding="utf-8") as f:
                    content = f.read()
                universe_data = parse_market_universe_yaml(content)

                market_data = universe_data.get("market_universe", {})
                yaml_registry = {}
                for asset_class, symbols in market_data.items():
                    for sym, info in symbols.items():
                        yaml_registry[sym.upper()] = {
                            "active": info.get("enabled", True),
                            "asset_class": asset_class,
                            "provider": info.get("provider", "MT5"),
                            "timeframes": info.get("timeframes", ["M15", "H1", "H4", "D1"])
                        }

                # Validate canonical 30 invariant on loaded YAML configuration
                self._validate_canonical_30_invariant(yaml_registry)
            except Exception as e:
                raise RuntimeError(f"Fail Closed: Failed to load/validate '{yaml_path}': {e}") from e

            # Check if saved registry state exists, but ensure canonical 30 set is preserved
            if os.path.exists(REGISTRY_FILE):
                try:
                    with open(REGISTRY_FILE, "r", encoding="utf-8") as f:
                        persisted_data = json.load(f)

                    # Persisted data must match exact 30 canonical symbols
                    persisted_set = set(k.upper() for k in persisted_data.keys())
                    if persisted_set == CANONICAL_30_SYMBOLS:
                        self.registry = persisted_data
                        self.save_registry()
                        return
                    else:
                        print("Warning: Stale persisted registry mismatched canonical 30 symbols. Overwriting with YAML baseline.")
                except Exception:
                    pass

            self.registry = yaml_registry
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
            if symbol_upper not in CANONICAL_30_SYMBOLS:
                raise ValueError(f"Symbol '{symbol_upper}' is not part of canonical 30 symbol universe.")

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
                self.registry[symbol_upper]["active"] = active
                self.save_registry()
