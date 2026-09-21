import unittest
from datetime import datetime, timedelta
from src.Data.Providers.MT5.mt5 import MT5DataProvider
from src.Data.External.models import ExternalDataRequest
from src.Application.Runtime.research_runtime import ResearchRuntime
from src.Data.Market.models import CompactMarketState
from src.Research.MarketAnalysis.Services.services import PrimitiveMarketResearchEngine, FeatureExtractionResearchEngine

class TestDataBoundaryAndMemorySafety(unittest.TestCase):
    """
    Tests enforcing Non-Negotiable Data Architecture & Memory Safety:
    - Bounded requests (~300-600 candles max lookback)
    - Zero technical indicators in CompactMarketState (NO volatility_atr, NO momentum_rsi)
    - 30-instrument path bypasses legacy FeatureExtractionResearchEngine and technical analysis pipeline
    - Strictly primitive market facts (current_price, high, low, volume, spread, timestamp, freshness, validity)
    - Zero bulk historical download pipeline / warehouse creation
    - Bounded memory footprint
    """

    def setUp(self):
        self.provider = MT5DataProvider()

    def test_canonical_exact_30_symbol_universe_invariant(self):
        from src.ShadowTrading.Engine.SymbolRegistry import SymbolRegistry, CANONICAL_30_SYMBOLS
        registry = SymbolRegistry.get_instance()
        registered = registry.get_all_registered()

        # Assert exact set equality
        registered_symbols = set(registered.keys())
        self.assertEqual(len(registered_symbols), 30)
        self.assertEqual(registered_symbols, CANONICAL_30_SYMBOLS)

        # Assert specific required symbols exist and extraneous symbols do not exist
        self.assertIn("XAUUSD", registered_symbols)
        self.assertIn("EURGBP", registered_symbols)
        self.assertIn("EURCHF", registered_symbols)
        self.assertIn("CADJPY", registered_symbols)
        self.assertNotIn("USOIL", registered_symbols)
        self.assertNotIn("NAS100", registered_symbols)

    def test_30_instrument_path_bypasses_legacy_technical_analysis_pipeline(self):
        from unittest.mock import patch

        runtime = ResearchRuntime(symbol="EURUSD", timeframe="H1")
        self.assertIsInstance(
            runtime.research_engine,
            PrimitiveMarketResearchEngine,
            "Default 30-instrument research engine MUST be PrimitiveMarketResearchEngine"
        )
        self.assertNotIsInstance(
            runtime.research_engine,
            FeatureExtractionResearchEngine,
            "30-instrument research path MUST NOT default to FeatureExtractionResearchEngine"
        )

        # Patch legacy TechnicalAnalysisEngine.analyze and FeatureExtractionResearchEngine.analyze_market to raise if invoked
        with patch("src.Research.analysis_pipeline.TechnicalAnalysisEngine.analyze", side_effect=AssertionError("LEGACY_PIPELINE_INVOKED")), \
             patch("src.Research.MarketAnalysis.Services.services.FeatureExtractionResearchEngine.analyze_market", side_effect=AssertionError("LEGACY_ENGINE_INVOKED")):
            res = runtime.run_once()

        self.assertIsNotNone(res)
        self.assertEqual(res.Request.Asset, "EURUSD")

        findings = res.Findings
        self.assertTrue(findings.get("indicator_independent"), "Findings must mark indicator_independent=True")

        prim_obs = findings.get("primitive_observation", {})
        self.assertIn("latest_price", prim_obs)
        self.assertIn("high", prim_obs)
        self.assertIn("low", prim_obs)
        self.assertIn("volume", prim_obs)
        self.assertNotIn("volatility_atr", prim_obs)
        self.assertNotIn("momentum_rsi", prim_obs)
        self.assertNotIn("price_trend", prim_obs)

    def test_legacy_feature_extraction_engine_preserved_when_explicitly_passed(self):
        # Legacy consumers can still explicitly pass FeatureExtractionResearchEngine
        legacy_engine = FeatureExtractionResearchEngine(data_provider=self.provider)
        runtime = ResearchRuntime(symbol="XAUUSD", timeframe="H1", research_engine=legacy_engine)
        self.assertIsInstance(runtime.research_engine, FeatureExtractionResearchEngine)

    def test_compact_market_state_has_no_technical_indicators(self):
        req = ExternalDataRequest(
            symbol="EURUSD",
            timeframe="H1",
            start_time=datetime.now() - timedelta(hours=5),
            end_time=datetime.now()
        )
        compact_state = self.provider.fetch_compact_market_state(req)
        self.assertIsInstance(compact_state, CompactMarketState)

        # Assert NO technical indicators exist in CompactMarketState fields
        self.assertFalse(hasattr(compact_state, "volatility_atr"), "CompactMarketState MUST NOT contain volatility_atr")
        self.assertFalse(hasattr(compact_state, "momentum_rsi"), "CompactMarketState MUST NOT contain momentum_rsi")
        self.assertFalse(hasattr(compact_state, "trend_state"), "CompactMarketState MUST NOT contain trend_state")

        # Assert primitive market facts exist
        self.assertTrue(hasattr(compact_state, "current_price"))
        self.assertTrue(hasattr(compact_state, "high"))
        self.assertTrue(hasattr(compact_state, "low"))
        self.assertTrue(hasattr(compact_state, "volume"))
        self.assertTrue(hasattr(compact_state, "spread"))
        self.assertTrue(hasattr(compact_state, "data_freshness_sec"))
        self.assertTrue(hasattr(compact_state, "is_valid"))

    def test_bounded_request_payload_size(self):
        now = datetime.now()
        req = ExternalDataRequest(
            symbol="EURUSD",
            timeframe="H1",
            start_time=now - timedelta(days=5),
            end_time=now
        )
        resp = self.provider.fetch_data(req)
        self.assertTrue(resp.is_success)
        self.assertLessEqual(len(resp.raw_data), 1000, "Fetch request payload must be strictly bounded")

    def test_stale_or_invalid_date_range_fails_closed(self):
        now = datetime.now()
        req = ExternalDataRequest(
            symbol="EURUSD",
            timeframe="H1",
            start_time=now,
            end_time=now - timedelta(days=1)
        )
        resp = self.provider.fetch_data(req)
        self.assertFalse(resp.is_success, "Invalid date range must fail closed")

    def test_disconnected_mt5_fails_closed(self):
        self.provider.set_connected(False)
        req = ExternalDataRequest(
            symbol="EURUSD",
            timeframe="H1",
            start_time=datetime.now() - timedelta(hours=5),
            end_time=datetime.now()
        )
        resp = self.provider.fetch_data(req)
        self.assertFalse(resp.is_success)
        self.assertTrue(
            "offline" in resp.error_message.lower() or "connection lost" in resp.error_message.lower(),
            f"Expected error message indicating offline/disconnected state, got: {resp.error_message}"
        )

if __name__ == "__main__":
    unittest.main()
