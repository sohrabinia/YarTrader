import unittest
from datetime import datetime
from src.Data.Reliability.reliability import SourceQualityScore, DataSourceReliabilityTracker
from src.Infrastructure.exceptions import ValidationException


class TestDataSourceReliability(unittest.TestCase):
    """
    Test suite verifying chronological reliability score records,
    multi-dimensional quality logs, and historical averages. (15 unit tests)
    """

    def setUp(self) -> None:
        self.tracker = DataSourceReliabilityTracker()
        self.provider_id = "primary-feed"

    # 1. SourceQualityScore Tests (5 tests)
    def test_score_1_valid_parameters(self) -> None:
        score = SourceQualityScore(self.provider_id, 1.0, 0.0, 1.0, 1.0)
        self.assertEqual(score.provider_id, self.provider_id)
        self.assertEqual(score.availability, 1.0)

    def test_score_2_composite_calculation_perfect_score(self) -> None:
        score = SourceQualityScore(self.provider_id, 1.0, 0.0, 1.0, 1.0)
        # availability*0.3 + (1-err)*0.3 + consistency*0.2 + completeness*0.2
        # = 1.0*0.3 + 1.0*0.3 + 1.0*0.2 + 1.0*0.2 = 1.0
        self.assertEqual(score.composite_score, 1.0)

    def test_score_3_composite_calculation_partial_score(self) -> None:
        score = SourceQualityScore(self.provider_id, 0.8, 0.2, 0.9, 0.7)
        # = 0.8*0.3 + 0.8*0.3 + 0.9*0.2 + 0.7*0.2
        # = 0.24 + 0.24 + 0.18 + 0.14 = 0.80
        self.assertAlmostEqual(score.composite_score, 0.80)

    def test_score_4_default_timestamp_created(self) -> None:
        score = SourceQualityScore(self.provider_id, 1.0, 0.0, 1.0, 1.0)
        self.assertTrue(isinstance(score.timestamp, datetime))

    def test_score_5_immutable_properties(self) -> None:
        score = SourceQualityScore(self.provider_id, 1.0, 0.0, 1.0, 1.0)
        with self.assertRaises(Exception):
            score.availability = 0.5

    # 2. DataSourceReliabilityTracker Tests (10 tests)
    def test_tracker_1_record_metric_valid_entry(self) -> None:
        score = self.tracker.record_metrics(self.provider_id, 1.0, 0.0, 1.0, 1.0)
        self.assertEqual(score.provider_id, self.provider_id)
        self.assertEqual(len(self.tracker.get_history(self.provider_id)), 1)

    def test_tracker_2_get_history_returns_empty_list_for_unknown(self) -> None:
        self.assertEqual(len(self.tracker.get_history("unknown")), 0)

    def test_tracker_3_record_empty_provider_id_fails(self) -> None:
        with self.assertRaises(ValidationException):
            self.tracker.record_metrics("", 1.0, 0.0, 1.0, 1.0)

    def test_tracker_4_record_invalid_metric_low_fails(self) -> None:
        with self.assertRaises(ValidationException):
            self.tracker.record_metrics(self.provider_id, -0.1, 0.0, 1.0, 1.0)

    def test_tracker_5_record_invalid_metric_high_fails(self) -> None:
        with self.assertRaises(ValidationException):
            self.tracker.record_metrics(self.provider_id, 1.0, 1.1, 1.0, 1.0)

    def test_tracker_6_get_average_scores_unregistered_defaults_to_perfect(self) -> None:
        avg = self.tracker.get_average_scores("unknown")
        self.assertEqual(avg["composite_score"], 1.0)
        self.assertEqual(avg["error_rate"], 0.0)

    def test_tracker_7_get_average_scores_computes_exact_averages(self) -> None:
        self.tracker.record_metrics(self.provider_id, 1.0, 0.0, 1.0, 1.0)
        self.tracker.record_metrics(self.provider_id, 0.8, 0.2, 0.8, 0.8)
        avg = self.tracker.get_average_scores(self.provider_id)
        self.assertEqual(avg["availability"], 0.9)
        self.assertEqual(avg["error_rate"], 0.1)
        self.assertEqual(avg["consistency"], 0.9)
        self.assertEqual(avg["completeness"], 0.9)
        self.assertEqual(avg["composite_score"], 0.9)

    def test_tracker_8_clear_wipes_all_histories(self) -> None:
        self.tracker.record_metrics(self.provider_id, 1.0, 0.0, 1.0, 1.0)
        self.tracker.clear()
        self.assertEqual(len(self.tracker.get_history(self.provider_id)), 0)

    def test_tracker_9_multiple_providers_tracked_independently(self) -> None:
        self.tracker.record_metrics("p1", 1.0, 0.0, 1.0, 1.0)
        self.tracker.record_metrics("p2", 0.5, 0.5, 0.5, 0.5)
        self.assertEqual(len(self.tracker.get_history("p1")), 1)
        self.assertEqual(len(self.tracker.get_history("p2")), 1)
        self.assertEqual(self.tracker.get_average_scores("p1")["composite_score"], 1.0)
        self.assertEqual(self.tracker.get_average_scores("p2")["composite_score"], 0.5)

    def test_tracker_10_chronological_ordering_preserved(self) -> None:
        s1 = self.tracker.record_metrics(self.provider_id, 1.0, 0.0, 1.0, 1.0)
        s2 = self.tracker.record_metrics(self.provider_id, 0.8, 0.1, 0.9, 0.9)
        history = self.tracker.get_history(self.provider_id)
        self.assertEqual(history[0], s1)
        self.assertEqual(history[1], s2)
