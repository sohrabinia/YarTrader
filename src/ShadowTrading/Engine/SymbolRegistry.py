import os
import json
from typing import Dict, List, Any, Tuple

REGISTRY_FILE = "runtime_logs/symbols_registry.json"

class SymbolRegistry:
    """
    Manages active symbols and their assigned timeframes dynamically.
    Enforces maximum 30 active symbols limit.
    Persists config cleanly across restarts.
    """
    _instance = None

    @classmethod
    def get_instance(cls) -> "SymbolRegistry":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        self.max_symbols = 30
        self.registry: Dict[str, Dict[str, Any]] = {}
        os.makedirs("runtime_logs", exist_ok=True)
        self.load_registry()

    def load_registry(self) -> None:
        if os.path.exists(REGISTRY_FILE):
            try:
                with open(REGISTRY_FILE, "r", encoding="utf-8") as f:
                    self.registry = json.load(f)
                return
            except Exception:
                pass

        # Load default registry configuration
        self.registry = {
            "XAUUSD": {"active": True, "timeframes": ["H1", "H4"]},
            "EURUSD": {"active": True, "timeframes": ["H1"]},
            "GBPUSD": {"active": True, "timeframes": ["H1"]},
            "BTCUSD": {"active": True, "timeframes": ["H1"]},
            "ETHUSD": {"active": True, "timeframes": ["H1"]}
        }
        self.save_registry()

    def save_registry(self) -> None:
        with open(REGISTRY_FILE, "w", encoding="utf-8") as f:
            json.dump(self.registry, f, indent=4)

    def get_all_registered(self) -> Dict[str, Dict[str, Any]]:
        return self.registry

    def get_active_matrix(self) -> List[Tuple[str, str]]:
        matrix = []
        active_count = 0
        for symbol, info in sorted(self.registry.items()):
            if info.get("active", True):
                if active_count >= self.max_symbols:
                    break
                active_count += 1
                for tf in info.get("timeframes", ["H1"]):
                    matrix.append((symbol, tf))
        return matrix

    def register_symbol(self, symbol: str, timeframes: List[str]) -> None:
        symbol_upper = symbol.upper()
        # Enforce max 30 symbols ceiling
        active_count = sum(1 for sym, info in self.registry.items() if info.get("active", True) and sym != symbol_upper)
        if active_count >= self.max_symbols:
            raise ValueError(f"Hard SRE limit reached: Maximum {self.max_symbols} active symbols allowed concurrent execution.")

        self.registry[symbol_upper] = {
            "active": True,
            "timeframes": timeframes
        }
        self.save_registry()

    def set_symbol_active(self, symbol: str, active: bool) -> None:
        symbol_upper = symbol.upper()
        if symbol_upper in self.registry:
            if active:
                # Enforce max 30 symbols ceiling
                active_count = sum(1 for sym, info in self.registry.items() if info.get("active", True) and sym != symbol_upper)
                if active_count >= self.max_symbols:
                    raise ValueError(f"Hard SRE limit reached: Maximum {self.max_symbols} active symbols allowed concurrent execution.")
            self.registry[symbol_upper]["active"] = active
            self.save_registry()
