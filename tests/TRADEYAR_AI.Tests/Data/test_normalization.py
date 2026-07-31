import unittest
from datetime import datetime
from src.Data.Normalization.normalizer import NormalizedMarketRecord, NormalizationRules, DataNormalizer
from src.Infrastructure.exceptions import ValidationException


class TestDataNormalizationPipeline(unittest.TestCase):
    """
    Test suite verifying record conversions, timestamp normalizations,
    symbol mapping rule overrides, and source preservation. (20 unit tests)
    """

    def setUp(self) -> None:
        self.normalizer = DataNormalizer()
        self.now = datetime.now()

    # 1. NormalizationRules Tests (5 tests)
    def test_rules_1_default_constructor(self) -> None:
        rules = NormalizationRules()
        self.assertEqual(rules.default_symbol, "UNKNOWN")
        self.assertEqual(len(rules.symbol_mapping), 0)
        self.assertEqual(len(rules.field_mapping), 0)

    def test_rules_2_symbol_mapping_assignment(self) -> None:
        rules = NormalizationRules(symbol_mapping={"BTC": "BTCUSD"})
        self.assertEqual(rules.symbol_mapping["BTC"], "BTCUSD")

    def test_rules_3_field_mapping_assignment(self) -> None:
        rules = NormalizationRules(field_mapping={"open": "OpenPrice"})
        self.assertEqual(rules.field_mapping["open"], "OpenPrice")

    def test_rules_4_custom_default_symbol(self) -> None:
        rules = NormalizationRules(default_symbol="BTCUSD")
        self.assertEqual(rules.default_symbol, "BTCUSD")

    def test_rules_5_immutable_rules_properties(self) -> None:
        rules = NormalizationRules()
        with self.assertRaises(Exception):
            rules.default_symbol = "ETHUSD"  # frozen dataclass

    # 2. DataNormalizer Convert Records Tests (15 tests)
    def test_convert_1_standard_record_conversion(self) -> None:
        raw = [{"symbol": "AAPL", "timestamp": self.now, "open": 100.0, "high": 105.0, "low": 99.0, "close": 102.0, "volume": 5000.0}]
        norm = self.normalizer.normalize_records(raw, "source-1")
        self.assertEqual(len(norm), 1)
        self.assertEqual(norm[0].symbol, "AAPL")
        self.assertEqual(norm[0].open_price, 100.0)
        self.assertEqual(norm[0].original_source, "source-1")

    def test_convert_2_missing_timestamp_record_skipped_silently(self) -> None:
        raw = [{"symbol": "AAPL", "open": 100.0}]  # missing timestamp
        norm = self.normalizer.normalize_records(raw, "source-1")
        self.assertEqual(len(norm), 0)

    def test_convert_3_invalid_timestamp_record_skipped_silently(self) -> None:
        raw = [{"symbol": "AAPL", "timestamp": "invalid-datetime-format", "open": 100.0}]
        norm = self.normalizer.normalize_records(raw, "source-1")
        self.assertEqual(len(norm), 0)

    def test_convert_4_epoch_timestamp_is_normalized_to_datetime(self) -> None:
        raw = [{"symbol": "AAPL", "timestamp": 1600000000, "open": 100.0}]
        norm = self.normalizer.normalize_records(raw, "source-1")
        self.assertEqual(len(norm), 1)
        self.assertEqual(norm[0].timestamp, datetime.fromtimestamp(1600000000))

    def test_convert_5_iso_string_timestamp_is_normalized_to_datetime(self) -> None:
        raw = [{"symbol": "AAPL", "timestamp": "2023-01-01T12:00:00", "open": 100.0}]
        norm = self.normalizer.normalize_records(raw, "source-1")
        self.assertEqual(len(norm), 1)
        self.assertEqual(norm[0].timestamp, datetime.fromisoformat("2023-01-01T12:00:00"))

    def test_convert_6_symbol_normalized_by_rules_mapping(self) -> None:
        raw = [{"symbol": "BTC-USD", "timestamp": self.now, "open": 100.0}]
        rules = NormalizationRules(symbol_mapping={"BTC-USD": "BTCUSD"})
        norm = self.normalizer.normalize_records(raw, "source-1", rules)
        self.assertEqual(norm[0].symbol, "BTCUSD")

    def test_convert_7_unmapped_symbol_preserves_raw_value(self) -> None:
        raw = [{"symbol": "ETHUSD", "timestamp": self.now, "open": 100.0}]
        rules = NormalizationRules(symbol_mapping={"BTC-USD": "BTCUSD"})
        norm = self.normalizer.normalize_records(raw, "source-1", rules)
        self.assertEqual(norm[0].symbol, "ETHUSD")

    def test_convert_8_field_keys_normalized_by_mapping_rules(self) -> None:
        raw = [{"symbol": "AAPL", "timestamp": self.now, "OpenPrice": 100.0, "HighPrice": 102.0}]
        rules = NormalizationRules(field_mapping={"open": "OpenPrice", "high": "HighPrice"})
        norm = self.normalizer.normalize_records(raw, "source-1", rules)
        self.assertEqual(norm[0].open_price, 100.0)
        self.assertEqual(norm[0].high_price, 102.0)

    def test_convert_9_non_numeric_metrics_raise_validation_exception(self) -> None:
        raw = [{"symbol": "AAPL", "timestamp": self.now, "open": "not-numeric"}]
        with self.assertRaises(ValidationException) as ex:
            self.normalizer.normalize_records(raw, "source-1")
        self.assertIn("Could not convert metrics", str(ex.exception))

    def test_convert_10_missing_symbol_uses_default_symbol(self) -> None:
        raw = [{"timestamp": self.now, "open": 100.0}]
        rules = NormalizationRules(default_symbol="BTCUSD")
        norm = self.normalizer.normalize_records(raw, "source-1", rules)
        self.assertEqual(norm[0].symbol, "BTCUSD")

    def test_convert_11_original_source_preserved_in_record(self) -> None:
        raw = [{"symbol": "AAPL", "timestamp": self.now}]
        norm = self.normalizer.normalize_records(raw, "meta-trader")
        self.assertEqual(norm[0].original_source, "meta-trader")

    def test_convert_12_non_metric_fields_preserved_in_metadata(self) -> None:
        raw = [{"symbol": "AAPL", "timestamp": self.now, "open": 100.0, "provider_custom_tag": "val1", "server_id": 45}]
        norm = self.normalizer.normalize_records(raw, "source-1")
        self.assertEqual(norm[0].source_metadata["provider_custom_tag"], "val1")
        self.assertEqual(norm[0].source_metadata["server_id"], 45)

    def test_convert_13_volume_defaults_to_zero_price_if_missing(self) -> None:
        raw = [{"symbol": "AAPL", "timestamp": self.now, "open": 100.0}]  # missing volume
        norm = self.normalizer.normalize_records(raw, "source-1")
        self.assertEqual(norm[0].volume_size, 0.0)

    def test_convert_14_float_conversion_preserves_precision(self) -> None:
        raw = [{"symbol": "AAPL", "timestamp": self.now, "open": 100.1234567}]
        norm = self.normalizer.normalize_records(raw, "source-1")
        self.assertEqual(norm[0].open_price, 100.1234567)

    def test_convert_15_empty_list_returns_empty_normalized_list(self) -> None:
        norm = self.normalizer.normalize_records([], "source-1")
        self.assertEqual(len(norm), 0)
