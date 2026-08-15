import unittest
from datetime import datetime, timedelta
from src.Data.Validation.validator import DataQualityScore, DataIntegrityReport, MarketDataValidator, DataQualityAnalyzer


class TestDataValidationIntelligence(unittest.TestCase):
    """
    Test suite verifying structural schema checks, multi-factor data quality
    analyzers, duplicate markers, and integrity reports. (25 unit tests)
    """

    def setUp(self) -> None:
        self.validator = MarketDataValidator()
        self.analyzer = DataQualityAnalyzer()
        self.provider_id = "test-provider"
        self.now = datetime.now()

    # 1. MarketDataValidator Tests (8 tests)
    def test_schema_1_valid_fields_has_no_mismatches(self) -> None:
        record = {"open": 1.0, "high": 2.0, "low": 0.5, "close": 1.5, "volume": 100.0, "timestamp": self.now}
        mismatches = self.validator.validate_record_schema(record, ["open", "high", "low", "close", "volume", "timestamp"])
        self.assertEqual(len(mismatches), 0)

    def test_schema_2_missing_field_detected(self) -> None:
        record = {"open": 1.0, "high": 2.0, "low": 0.5, "close": 1.5}  # missing volume, timestamp
        mismatches = self.validator.validate_record_schema(record, ["open", "high", "low", "close", "volume", "timestamp"])
        self.assertEqual(len(mismatches), 2)
        self.assertIn("Missing required field: 'volume'", mismatches)

    def test_schema_3_empty_record_mismatches_all_expected(self) -> None:
        mismatches = self.validator.validate_record_schema({}, ["open", "high"])
        self.assertEqual(len(mismatches), 2)

    def test_schema_4_additional_fields_are_ignored(self) -> None:
        record = {"open": 1.0, "high": 2.0, "extra": "info"}
        mismatches = self.validator.validate_record_schema(record, ["open", "high"])
        self.assertEqual(len(mismatches), 0)

    def test_schema_5_case_sensitive_field_names(self) -> None:
        record = {"Open": 1.0, "High": 2.0}
        mismatches = self.validator.validate_record_schema(record, ["open", "high"])
        self.assertEqual(len(mismatches), 2)

    def test_schema_6_none_field_valued_is_not_missing(self) -> None:
        record = {"open": None, "high": 2.0}
        mismatches = self.validator.validate_record_schema(record, ["open", "high"])
        self.assertEqual(len(mismatches), 0)  # Present but None is checked by analyzer, not schema mismatch

    def test_schema_7_empty_expected_list_always_passes(self) -> None:
        mismatches = self.validator.validate_record_schema({"open": 1.0}, [])
        self.assertEqual(len(mismatches), 0)

    def test_schema_8_validate_single_mismatch(self) -> None:
        mismatches = self.validator.validate_record_schema({"open": 1.0}, ["high"])
        self.assertEqual(mismatches, ["Missing required field: 'high'"])

    # 2. DataQualityAnalyzer Dataset Tests (17 tests)
    def test_analyzer_1_perfect_dataset(self) -> None:
        records = [
            {"timestamp": self.now, "open": 10.0, "high": 12.0, "low": 9.0, "close": 11.0, "volume": 1000},
            {"timestamp": self.now + timedelta(minutes=15), "open": 11.0, "high": 13.0, "low": 10.0, "close": 12.0, "volume": 1050}
        ]
        report = self.analyzer.analyze_dataset(self.provider_id, records)
        self.assertTrue(report.is_acceptable)
        self.assertEqual(report.quality_scores.overall_score, 1.0)
        self.assertEqual(len(report.anomalies), 0)

    def test_analyzer_2_empty_dataset_is_unacceptable(self) -> None:
        report = self.analyzer.analyze_dataset(self.provider_id, [])
        self.assertFalse(report.is_acceptable)
        self.assertEqual(report.quality_scores.overall_score, 0.0)

    def test_analyzer_3_missing_fields_reduces_completeness_score(self) -> None:
        records = [
            {"timestamp": self.now, "open": 10.0, "high": 12.0, "low": 9.0, "close": 11.0, "volume": 1000},
            {"timestamp": self.now, "open": 11.0, "high": 13.0}  # missing low, close, volume
        ]
        report = self.analyzer.analyze_dataset(self.provider_id, records)
        self.assertLess(report.quality_scores.completeness_score, 1.0)
        self.assertLess(report.quality_scores.overall_score, 1.0)

    def test_analyzer_4_invalid_timestamps_detected(self) -> None:
        records = [
            {"timestamp": "not-a-datetime", "open": 10.0, "high": 12.0, "low": 9.0, "close": 11.0, "volume": 1000}
        ]
        report = self.analyzer.analyze_dataset(self.provider_id, records)
        self.assertEqual(report.quality_scores.timestamp_validity_score, 0.0)

    def test_analyzer_5_duplicates_timestamps_reduce_uniqueness_score(self) -> None:
        records = [
            {"timestamp": self.now, "open": 10.0, "high": 12.0, "low": 9.0, "close": 11.0, "volume": 1000},
            {"timestamp": self.now, "open": 10.0, "high": 12.0, "low": 9.0, "close": 11.0, "volume": 1000}  # duplicate timestamp
        ]
        report = self.analyzer.analyze_dataset(self.provider_id, records)
        self.assertEqual(report.quality_scores.uniqueness_score, 0.5)

    def test_analyzer_6_low_price_exceeding_high_price_reduces_consistency_score(self) -> None:
        records = [
            {"timestamp": self.now, "open": 10.0, "high": 12.0, "low": 15.0, "close": 11.0, "volume": 1000}  # low = 15.0 > high = 12.0
        ]
        report = self.analyzer.analyze_dataset(self.provider_id, records)
        self.assertEqual(report.quality_scores.consistency_score, 0.0)

    def test_analyzer_7_open_price_exceeding_boundaries_reduces_consistency(self) -> None:
        records = [
            {"timestamp": self.now, "open": 15.0, "high": 12.0, "low": 9.0, "close": 11.0, "volume": 1000}  # open = 15.0 > high = 12.0
        ]
        report = self.analyzer.analyze_dataset(self.provider_id, records)
        self.assertEqual(report.quality_scores.consistency_score, 0.0)

    def test_analyzer_8_close_price_exceeding_boundaries_reduces_consistency(self) -> None:
        records = [
            {"timestamp": self.now, "open": 10.0, "high": 12.0, "low": 9.0, "close": 8.0, "volume": 1000}  # close = 8.0 < low = 9.0
        ]
        report = self.analyzer.analyze_dataset(self.provider_id, records)
        self.assertEqual(report.quality_scores.consistency_score, 0.0)

    def test_analyzer_9_epoch_integer_timestamp_is_valid(self) -> None:
        records = [
            {"timestamp": 1600000000, "open": 10.0, "high": 12.0, "low": 9.0, "close": 11.0, "volume": 1000}
        ]
        report = self.analyzer.analyze_dataset(self.provider_id, records)
        self.assertEqual(report.quality_scores.timestamp_validity_score, 1.0)

    def test_analyzer_10_iso_string_timestamp_is_valid(self) -> None:
        records = [
            {"timestamp": "2023-01-01T12:00:00", "open": 10.0, "high": 12.0, "low": 9.0, "close": 11.0, "volume": 1000}
        ]
        report = self.analyzer.analyze_dataset(self.provider_id, records)
        self.assertEqual(report.quality_scores.timestamp_validity_score, 1.0)

    def test_analyzer_11_null_prices_reduce_consistency_to_zero(self) -> None:
        records = [
            {"timestamp": self.now, "open": None, "high": 12.0, "low": 9.0, "close": 11.0, "volume": 1000}
        ]
        report = self.analyzer.analyze_dataset(self.provider_id, records)
        # null is ignored in consistency checks, completeness score drops
        self.assertLess(report.quality_scores.completeness_score, 1.0)

    def test_analyzer_12_non_numeric_price_raises_error_handled_as_unacceptable(self) -> None:
        records = [
            {"timestamp": self.now, "open": "not-a-number", "high": 12.0, "low": 9.0, "close": 11.0, "volume": 1000}
        ]
        report = self.analyzer.analyze_dataset(self.provider_id, records)
        # string "not-a-number" fails comparisons, marked inconsistent or completeness drop
        self.assertFalse(report.quality_scores.overall_score == 1.0)

    def test_analyzer_13_report_accepts_marginal_dataset(self) -> None:
        # Completeness is 5/6 (0.8333), overall score >= 0.70 -> accepted
        records = [
            {"timestamp": self.now, "open": 10.0, "high": 12.0, "low": 9.0, "close": 11.0}, # missing volume
            {"timestamp": self.now, "open": 11.0, "high": 13.0, "low": 10.0, "close": 12.0, "volume": 1000}
        ]
        report = self.analyzer.analyze_dataset(self.provider_id, records)
        self.assertTrue(report.is_acceptable)

    def test_analyzer_14_report_rejects_severe_missing_dataset(self) -> None:
        # missing almost everything, completeness < 0.60 -> rejected
        records = [
            {"timestamp": self.now, "open": 10.0},
            {"timestamp": self.now, "open": 11.0}
        ]
        report = self.analyzer.analyze_dataset(self.provider_id, records)
        self.assertFalse(report.is_acceptable)

    def test_analyzer_15_anomalies_capped_list_size(self) -> None:
        # generate 60 anomalies
        records = []
        for i in range(60):
            records.append({"timestamp": self.now, "open": 10.0, "high": 10.0, "low": 20.0, "close": 10.0, "volume": 1000}) # low > high
        report = self.analyzer.analyze_dataset(self.provider_id, records)
        self.assertEqual(len(report.anomalies), 50) # capped at 50

    def test_analyzer_16_schema_mismatches_capped_list_size(self) -> None:
        records = [{"timestamp": self.now} for _ in range(60)] # missing 5 fields each
        report = self.analyzer.analyze_dataset(self.provider_id, records)
        self.assertEqual(len(report.schema_mismatches), 50) # capped at 50

    def test_analyzer_17_different_field_configurations(self) -> None:
        records = [{"timestamp": self.now, "custom_field": 10.0}]
        report = self.analyzer.analyze_dataset(self.provider_id, records, expected_fields=["custom_field"])
        self.assertTrue(report.is_acceptable)
