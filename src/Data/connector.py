import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from src.Data.External.models import ExternalDataRequest, ExternalDataResponse, ProviderHealthStatus
from src.Data.Gateway.gateway import ExternalDataGateway
from src.Data.Validation.validator import DataQualityAnalyzer, DataIntegrityReport, DataQualityScore
from src.Data.Normalization.normalizer import DataNormalizer, NormalizedMarketRecord
from src.Data.Reliability.reliability import DataSourceReliabilityTracker
from src.Data.Market.models import MarketInstrument, CandleRecord, MarketDataMetadata, MarketDataRequest, MarketDataResponse
from src.Data.Providers.MT5.mt5 import MT5DataProvider
from src.Data.Providers.Economic.economic import EconomicDataProvider, EconomicEvent
from src.Data.Providers.News.news import NewsDataProvider, NewsRecord
from src.Infrastructure.exceptions import ValidationException


class ExternalDataPipelineConnector:
    """
    Advanced real market data intelligence pipeline coordinator.
    Sequence: Ingestion -> Gateway -> Validation -> Normalization -> Reliability.
    Ties MT5, Economic, and News providers into standard passive pipelines.
    """
    def __init__(self) -> None:
        self.gateway = ExternalDataGateway()
        self.analyzer = DataQualityAnalyzer()
        self.normalizer = DataNormalizer()
        self.reliability_tracker = DataSourceReliabilityTracker()

        # Register standard providers
        self.mt5_provider = MT5DataProvider()
        self.economic_provider = EconomicDataProvider()
        self.news_provider = NewsDataProvider()

        self.gateway.registry.register_provider(self.mt5_provider)
        self.gateway.registry.register_provider(self.economic_provider)
        self.gateway.registry.register_provider(self.news_provider)

    def retrieve_and_process(
        self,
        request: ExternalDataRequest
    ) -> Tuple[List[NormalizedMarketRecord], DataIntegrityReport]:
        """
        Retrieves raw data, validates, and normalizes.
        Logs metrics in reliability tracker automatically.
        """
        provider_id = "unknown"
        resolved_p = self.gateway.resolver.resolve_provider(request.symbol)
        if resolved_p:
            provider_id = resolved_p.metadata.provider_id

        start_time = time.time()
        # 1. Fetch raw response via Gateway
        try:
            resp = self.gateway.fetch(request)
        except Exception as e:
            self.reliability_tracker.record_metrics(
                provider_id=provider_id,
                availability=0.0,
                error_rate=1.0,
                consistency=0.0,
                completeness=0.0,
                latency_ms=(time.time() - start_time) * 1000.0,
                error_msg=str(e)
            )
            empty_score = DataQualityScore(0.0, 0.0, 0.0, 0.0, 0.0)
            failed_report = DataIntegrityReport(
                report_id="failed",
                provider_id=provider_id,
                analyzed_at=datetime.now(),
                quality_scores=empty_score,
                anomalies=[f"Fetch exception: {e}"],
                is_acceptable=False
            )
            return [], failed_report

        latency_ms = (time.time() - start_time) * 1000.0

        if not resp.is_success:
            self.reliability_tracker.record_metrics(
                provider_id=resp.provider_id,
                availability=0.0,
                error_rate=1.0,
                consistency=0.0,
                completeness=0.0,
                latency_ms=latency_ms,
                error_msg=resp.error_message
            )
            empty_score = DataQualityScore(0.0, 0.0, 0.0, 0.0, 0.0)
            failed_report = DataIntegrityReport(
                report_id=resp.request_id,
                provider_id=resp.provider_id,
                analyzed_at=resp.retrieved_at,
                quality_scores=empty_score,
                anomalies=[resp.error_message or "Unknown provider error."],
                is_acceptable=False
            )
            return [], failed_report

        # 2. Validate Quality and Integrity
        report = self.analyzer.analyze_dataset(resp.provider_id, resp.raw_data)

        # 3. Record Reliability Metric chronological records
        error_rate = 0.0 if report.is_acceptable else 0.5
        self.reliability_tracker.record_metrics(
            provider_id=resp.provider_id,
            availability=1.0,
            error_rate=error_rate,
            consistency=report.quality_scores.consistency_score,
            completeness=report.quality_scores.completeness_score,
            latency_ms=latency_ms,
            error_msg=None if report.is_acceptable else f"Validation failed with overall score: {report.quality_scores.overall_score}"
        )

        if not report.is_acceptable:
            return [], report

        # 4. Normalize records
        normalized_records = self.normalizer.normalize_records(resp.raw_data, resp.provider_id)
        return normalized_records, report

    def retrieve_market_data(self, request: MarketDataRequest) -> MarketDataResponse:
        """Ties MT5 adapter fetch into the pipeline and scores reliability."""
        start_time = time.time()

        # Ingest via typed adapter
        resp = self.mt5_provider.fetch_market_data(request)
        latency_ms = (time.time() - start_time) * 1000.0

        # Validate candle quality using standard Analyzer mapping to raw records
        raw_candles = [
            {
                "timestamp": c.timestamp,
                "open": c.open,
                "high": c.high,
                "low": c.low,
                "close": c.close,
                "volume": c.volume
            }
            for c in resp.candles
        ]

        if not resp.is_success:
            self.reliability_tracker.record_metrics(
                provider_id=self.mt5_provider.metadata.provider_id,
                availability=0.0,
                error_rate=1.0,
                consistency=0.0,
                completeness=0.0,
                latency_ms=latency_ms,
                error_msg=resp.error_message
            )
            return resp

        # Perform Validation
        quality_report = self.analyzer.analyze_dataset(self.mt5_provider.metadata.provider_id, raw_candles)

        # Record health metrics
        error_rate = 0.0 if quality_report.is_acceptable else 0.5
        self.reliability_tracker.record_metrics(
            provider_id=self.mt5_provider.metadata.provider_id,
            availability=1.0,
            error_rate=error_rate,
            consistency=quality_report.quality_scores.consistency_score,
            completeness=quality_report.quality_scores.completeness_score,
            latency_ms=latency_ms,
            error_msg=None if quality_report.is_acceptable else "Candle consistency checks failed."
        )

        if not quality_report.is_acceptable:
            return MarketDataResponse(
                request=request,
                candles=[],
                metadata=resp.metadata,
                is_success=False,
                error_message="Validation of received candles failed constraints."
            )

        return resp

    def retrieve_economic_events(self, request: ExternalDataRequest) -> List[EconomicEvent]:
        """Ties Economic provider fetch into the pipeline and scores reliability."""
        start_time = time.time()

        events = self.economic_provider.fetch_calendar_events(request)
        latency_ms = (time.time() - start_time) * 1000.0

        is_success = len(events) > 0 or self.economic_provider.check_health() == ProviderHealthStatus.HEALTHY
        availability = 1.0 if is_success else 0.0
        error_rate = 0.0 if is_success else 1.0

        self.reliability_tracker.record_metrics(
            provider_id=self.economic_provider.metadata.provider_id,
            availability=availability,
            error_rate=error_rate,
            consistency=1.0 if is_success else 0.0,
            completeness=1.0 if is_success else 0.0,
            latency_ms=latency_ms,
            error_msg=None if is_success else "Economic calendar fetch failed."
        )

        return events

    def retrieve_news_records(self, request: ExternalDataRequest) -> List[NewsRecord]:
        """Ties News provider fetch into the pipeline and scores reliability."""
        start_time = time.time()

        records = self.news_provider.fetch_news_records(request)
        latency_ms = (time.time() - start_time) * 1000.0

        is_success = len(records) > 0 or self.news_provider.check_health() == ProviderHealthStatus.HEALTHY
        availability = 1.0 if is_success else 0.0
        error_rate = 0.0 if is_success else 1.0

        self.reliability_tracker.record_metrics(
            provider_id=self.news_provider.metadata.provider_id,
            availability=availability,
            error_rate=error_rate,
            consistency=1.0 if is_success else 0.0,
            completeness=1.0 if is_success else 0.0,
            latency_ms=latency_ms,
            error_msg=None if is_success else "News records fetch failed."
        )

        return records
