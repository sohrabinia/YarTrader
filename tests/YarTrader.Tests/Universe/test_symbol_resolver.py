import unittest
from unittest.mock import MagicMock, patch
from src.Data.Providers.MT5.symbol_resolver import MT5SymbolResolver

class TestMT5SymbolResolver(unittest.TestCase):
    """
    Tests for Centralized MT5 Symbol Resolver:
    - Canonical symbol mapping
    - Broker suffix handling (e.g. 'EURUSDm', 'EURUSD.a')
    - Unavailable symbols return None / fail closed
    - Ambiguous or malformed inputs return None / fail closed
    """

    def setUp(self):
        MT5SymbolResolver._instance = None
        self.resolver = MT5SymbolResolver.get_instance()
        self.resolver.clear_cache()

    def test_canonical_resolution_exact_match(self):
        resolved = self.resolver.resolve_symbol("EURUSD")
        self.assertEqual(resolved, "EURUSD")

    def test_xauusd_resolution(self):
        resolved = self.resolver.resolve_symbol("XAUUSD")
        self.assertEqual(resolved, "XAUUSD")

    def test_btc_resolution(self):
        resolved = self.resolver.resolve_symbol("BTCUSD")
        self.assertEqual(resolved, "BTCUSD")

    def test_case_and_whitespace_insensitivity(self):
        resolved = self.resolver.resolve_symbol("  eurusd  ")
        self.assertEqual(resolved, "EURUSD")

    def test_suffix_resolution_mock(self):
        mock_mt5 = MagicMock()
        def mock_symbol_info(cand):
            if cand == "EURUSDm":
                sym = MagicMock()
                sym.name = "EURUSDm"
                return sym
            return None
        mock_mt5.symbol_info.side_effect = mock_symbol_info
        mock_mt5.symbols_get.return_value = []

        with patch.dict("sys.modules", {"MetaTrader5": mock_mt5}):
            self.resolver.clear_cache()
            resolved = self.resolver.resolve_symbol("EURUSD")
            self.assertEqual(resolved, "EURUSDm")

    def test_unavailable_symbol_fails_closed(self):
        resolved = self.resolver.resolve_symbol("UNAVAIL_XYZ_PAIR")
        self.assertIsNone(resolved, "Unavailable symbol must return None (fail closed)")

    def test_invalid_and_empty_symbol_input(self):
        self.assertIsNone(self.resolver.resolve_symbol(""))
        self.assertIsNone(self.resolver.resolve_symbol(None))
        self.assertIsNone(self.resolver.resolve_symbol(12345))

    def test_ambiguous_symbol_returns_none_if_unresolvable(self):
        resolved = self.resolver.resolve_symbol("NONEXISTENT_CRYPTO_TOKEN_999")
        self.assertIsNone(resolved)

if __name__ == "__main__":
    unittest.main()
