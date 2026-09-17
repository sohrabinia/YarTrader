import os
import unittest
from src.ShadowTrading.Engine.SymbolRegistry import SymbolRegistry, parse_market_universe_yaml

class TestUniverseSpecification(unittest.TestCase):
    """
    Tests enforcing the Exact 30-Instrument Universe Specification:
    - Exactly 15 FX/Metal instruments (XAUUSD included)
    - Exactly 15 Crypto instruments
    - Total = 30 logical instruments
    - No duplicates
    """

    def setUp(self):
        # Reset SymbolRegistry singleton state for clean isolation
        SymbolRegistry._instance = None
        self.registry = SymbolRegistry.get_instance()

    def test_exact_counts(self):
        registered = self.registry.get_all_registered()
        self.assertEqual(len(registered), 30, f"Expected exactly 30 registered instruments, got {len(registered)}")

        fx_metal = [s for s, info in registered.items() if info.get("asset_class") in ["Forex", "Commodities", "Metals"]]
        crypto = [s for s, info in registered.items() if info.get("asset_class") == "Crypto"]

        self.assertEqual(len(fx_metal), 15, f"Expected exactly 15 FX/Metal instruments, got {len(fx_metal)}")
        self.assertEqual(len(crypto), 15, f"Expected exactly 15 Crypto instruments, got {len(crypto)}")
        self.assertEqual(len(fx_metal) + len(crypto), 30, "Sum of FX/Metal and Crypto must equal 30")

    def test_xauusd_included(self):
        registered = self.registry.get_all_registered()
        self.assertIn("XAUUSD", registered, "Mandatory instrument XAUUSD must be included")
        self.assertIn("XAGUSD", registered, "XAGUSD must be included in FX/Metal group")

    def test_no_duplicate_symbols(self):
        registered = self.registry.get_all_registered()
        symbol_list = list(registered.keys())
        unique_symbols = set(symbol_list)
        self.assertEqual(len(symbol_list), len(unique_symbols), "All registered canonical symbols must be unique")

    def test_market_universe_yaml_parsing(self):
        yaml_path = "config/market_universe.yaml"
        self.assertTrue(os.path.exists(yaml_path), f"File {yaml_path} must exist")

        with open(yaml_path, "r", encoding="utf-8") as f:
            content = f.read()

        parsed = parse_market_universe_yaml(content)
        market_universe = parsed.get("market_universe", {})

        total_parsed = sum(len(syms) for syms in market_universe.values())
        self.assertEqual(total_parsed, 30, f"market_universe.yaml must parse to exactly 30 instruments, got {total_parsed}")

if __name__ == "__main__":
    unittest.main()
