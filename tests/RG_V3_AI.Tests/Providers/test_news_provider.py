import unittest
from datetime import datetime
from src.Data.Providers.News.news import NewsDataProvider, NewsRecord, NewsMetadata
from src.Data.External.models import ExternalDataRequest, ExternalDataResponse, ProviderHealthStatus
from src.Infrastructure.exceptions import ValidationException


class TestNewsDataProvider(unittest.TestCase):
    """
    Test suite verifying news record creation, metadata validation, missing
    fields, and parsing. (30 unit tests)
    """

    def setUp(self) -> None:
        self.provider = NewsDataProvider(provider_id="news-test")
        self.now = datetime.now()

    # 1. News Record Construction (10 tests)
    def test_record_1_standard_creation(self) -> None:
        meta = NewsMetadata("Chronicle", "Author", "en", "http://example.com")
        rec = NewsRecord("art-1", "Headline", self.now, "FOMC", "Summary", meta)
        self.assertEqual(rec.article_id, "art-1")
        self.assertEqual(rec.headline, "Headline")

    def test_record_2_optional_fields_are_none_by_default(self) -> None:
        meta = NewsMetadata("Chronicle")
        self.assertIsNone(meta.author)
        self.assertEqual(meta.language, "en")
        self.assertIsNone(meta.url)

    def test_record_3_article_id_required(self) -> None:
        meta = NewsMetadata("Chronicle")
        rec = NewsRecord("art-1", "Headline", self.now, "FOMC", "Summary", meta)
        self.assertEqual(rec.article_id, "art-1")

    def test_record_4_category_FOMC_assigned(self) -> None:
        meta = NewsMetadata("Chronicle")
        rec = NewsRecord("art-1", "Headline", self.now, "FOMC", "Summary", meta)
        self.assertEqual(rec.category, "FOMC")

    def test_record_5_category_Regulation_assigned(self) -> None:
        meta = NewsMetadata("Chronicle")
        rec = NewsRecord("art-1", "Headline", self.now, "Regulation", "Summary", meta)
        self.assertEqual(rec.category, "Regulation")

    def test_record_6_headline_preserved(self) -> None:
        meta = NewsMetadata("Chronicle")
        rec = NewsRecord("art-1", "Headline Text", self.now, "FOMC", "Summary", meta)
        self.assertEqual(rec.headline, "Headline Text")

    def test_record_7_timestamp_preserved(self) -> None:
        meta = NewsMetadata("Chronicle")
        rec = NewsRecord("art-1", "Headline", self.now, "FOMC", "Summary", meta)
        self.assertEqual(rec.timestamp, self.now)

    def test_record_8_summary_preserved(self) -> None:
        meta = NewsMetadata("Chronicle")
        rec = NewsRecord("art-1", "Headline", self.now, "FOMC", "Summary Content", meta)
        self.assertEqual(rec.summary, "Summary Content")

    def test_record_9_supported_symbols_assigned(self) -> None:
        self.assertIn("FOMC_NEWS", self.provider.metadata.supported_symbols)
        self.assertIn("REG_NEWS", self.provider.metadata.supported_symbols)

    def test_record_10_provider_id_assigned(self) -> None:
        self.assertEqual(self.provider.metadata.provider_id, "news-test")

    # 2. Ingestion Fetching Tests (10 tests)
    def test_fetch_1_unhealthy_fetch_fails(self) -> None:
        self.provider.set_health(ProviderHealthStatus.UNHEALTHY)
        req = ExternalDataRequest("FOMC_NEWS", "M15", self.now, self.now)
        resp = self.provider.fetch_data(req)
        self.assertFalse(resp.is_success)

    def test_fetch_2_fomc_news_loaded_correctly(self) -> None:
        req = ExternalDataRequest("FOMC_NEWS", "M15", self.now, self.now)
        resp = self.provider.fetch_data(req)
        self.assertTrue(resp.is_success)
        self.assertEqual(resp.raw_data[0]["article_id"], "news-fomc-1")
        self.assertEqual(resp.raw_data[0]["category"], "FOMC")

    def test_fetch_3_reg_news_loaded_correctly(self) -> None:
        req = ExternalDataRequest("REG_NEWS", "M15", self.now, self.now)
        resp = self.provider.fetch_data(req)
        self.assertTrue(resp.is_success)
        self.assertEqual(resp.raw_data[0]["article_id"], "news-reg-1")
        self.assertEqual(resp.raw_data[0]["category"], "Regulation")

    def test_fetch_4_generic_news_record_loaded(self) -> None:
        req = ExternalDataRequest("CORP_EARNINGS", "M15", self.now, self.now)
        resp = self.provider.fetch_data(req)
        self.assertTrue(resp.is_success)
        self.assertEqual(resp.raw_data[0]["category"], "MarketUpdate")

    def test_fetch_5_news_parsing_typed_records(self) -> None:
        req = ExternalDataRequest("FOMC_NEWS", "M15", self.now, self.now)
        records = self.provider.fetch_news_records(req)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].headline, "Fed Holds Rates Steady at FOMC Meeting")
        self.assertEqual(records[0].meta.source_name, "Financial Chronicle")

    def test_fetch_6_news_parsing_missing_data_returns_empty_list_if_fetch_fails(self) -> None:
        self.provider.set_health(ProviderHealthStatus.UNHEALTHY)
        req = ExternalDataRequest("FOMC_NEWS", "M15", self.now, self.now)
        records = self.provider.fetch_news_records(req)
        self.assertEqual(len(records), 0)

    def test_fetch_7_reg_raw_mapping(self) -> None:
        req = ExternalDataRequest("REG_NEWS", "M15", self.now, self.now)
        records = self.provider.fetch_news_records(req)
        self.assertEqual(records[0].article_id, "news-reg-1")

    def test_fetch_8_parsed_news_timestamp_matching(self) -> None:
        req = ExternalDataRequest("FOMC_NEWS", "M15", self.now, self.now)
        records = self.provider.fetch_news_records(req)
        self.assertEqual(records[0].timestamp, self.now)

    def test_fetch_9_news_metadata_language_default(self) -> None:
        req = ExternalDataRequest("FOMC_NEWS", "M15", self.now, self.now)
        records = self.provider.fetch_news_records(req)
        self.assertEqual(records[0].meta.language, "en")

    def test_fetch_10_news_metadata_author_retrieved(self) -> None:
        req = ExternalDataRequest("FOMC_NEWS", "M15", self.now, self.now)
        records = self.provider.fetch_news_records(req)
        self.assertEqual(records[0].meta.author, "J. Doe")

    # 3. Parsing Validation Scenarios (10 tests)
    def test_validation_1_invalid_timestamp_throws_exception(self) -> None:
        class BrokenTimestampNewsProvider(NewsDataProvider):
            def fetch_data(self, r):
                return ExternalDataResponse("id", "news", [{"article_id": "art-1", "headline": "Text", "timestamp": "invalid-datetime", "category": "FOMC", "summary": "Text", "source": "Chronicle"}])

        p = BrokenTimestampNewsProvider()
        req = ExternalDataRequest("FOMC_NEWS", "M15", self.now, self.now)
        with self.assertRaises(ValidationException):
            p.fetch_news_records(req)

    def test_validation_2_missing_article_id_causes_exception(self) -> None:
        class BrokenArticleIdNewsProvider(NewsDataProvider):
            def fetch_data(self, r):
                return ExternalDataResponse("id", "news", [{"headline": "Text", "timestamp": "2023-01-01T12:00:00", "category": "FOMC", "summary": "Text", "source": "Chronicle"}])

        p = BrokenArticleIdNewsProvider()
        req = ExternalDataRequest("FOMC_NEWS", "M15", self.now, self.now)
        with self.assertRaises(Exception):
            p.fetch_news_records(req)

    def test_validation_3_missing_headline_causes_exception(self) -> None:
        class BrokenHeadlineNewsProvider(NewsDataProvider):
            def fetch_data(self, r):
                return ExternalDataResponse("id", "news", [{"article_id": "art-1", "timestamp": "2023-01-01T12:00:00", "category": "FOMC", "summary": "Text", "source": "Chronicle"}])

        p = BrokenHeadlineNewsProvider()
        req = ExternalDataRequest("FOMC_NEWS", "M15", self.now, self.now)
        with self.assertRaises(Exception):
            p.fetch_news_records(req)

    def test_validation_4_missing_category_causes_exception(self) -> None:
        class BrokenCategoryNewsProvider(NewsDataProvider):
            def fetch_data(self, r):
                return ExternalDataResponse("id", "news", [{"article_id": "art-1", "headline": "Text", "timestamp": "2023-01-01T12:00:00", "summary": "Text", "source": "Chronicle"}])

        p = BrokenCategoryNewsProvider()
        req = ExternalDataRequest("FOMC_NEWS", "M15", self.now, self.now)
        with self.assertRaises(Exception):
            p.fetch_news_records(req)

    def test_validation_5_missing_summary_causes_exception(self) -> None:
        class BrokenSummaryNewsProvider(NewsDataProvider):
            def fetch_data(self, r):
                return ExternalDataResponse("id", "news", [{"article_id": "art-1", "headline": "Text", "timestamp": "2023-01-01T12:00:00", "category": "FOMC", "source": "Chronicle"}])

        p = BrokenSummaryNewsProvider()
        req = ExternalDataRequest("FOMC_NEWS", "M15", self.now, self.now)
        with self.assertRaises(Exception):
            p.fetch_news_records(req)

    def test_validation_6_missing_source_causes_exception(self) -> None:
        class BrokenSourceNewsProvider(NewsDataProvider):
            def fetch_data(self, r):
                return ExternalDataResponse("id", "news", [{"article_id": "art-1", "headline": "Text", "timestamp": "2023-01-01T12:00:00", "category": "FOMC", "summary": "Text"}])

        p = BrokenSourceNewsProvider()
        req = ExternalDataRequest("FOMC_NEWS", "M15", self.now, self.now)
        with self.assertRaises(Exception):
            p.fetch_news_records(req)

    def test_validation_7_optional_url_mapping(self) -> None:
        meta = NewsMetadata("Chronicle", url="http://example.com")
        self.assertEqual(meta.url, "http://example.com")

    def test_validation_8_optional_author_mapping(self) -> None:
        meta = NewsMetadata("Chronicle", author="Writer")
        self.assertEqual(meta.author, "Writer")

    def test_validation_9_optional_language_mapping(self) -> None:
        meta = NewsMetadata("Chronicle", language="fr")
        self.assertEqual(meta.language, "fr")

    def test_validation_10_set_health_reported_healthy_by_default(self) -> None:
        self.assertEqual(self.provider.check_health(), ProviderHealthStatus.HEALTHY)
