from datetime import datetime
from typing import List, Tuple
from src.Data.External.models import ExternalDataRequest, ExternalDataResponse
from src.Data.Gateway.gateway import ExternalDataGateway
from src.Data.Validation.validator import DataQualityAnalyzer, DataIntegrityReport, DataQualityScore
from src.Data.Normalization.normalizer import DataNormalizer, NormalizedMarketRecord
from src.Data.Reliability.reliability import DataSourceReliabilityTracker
from src.Infrastructure.exceptions import ValidationException


class ExternalDataPipelineConnector:
    """
    Core integration pipeline connecting external data retrieval to the internal platform.
    Sequence: Gateway -> Validation -> Normalization -> Reliability.
    """
    def __init__(self) -> None:
        self.gateway = ExternalDataGateway()
        self.analyzer = DataQualityAnalyzer()
        self.normalizer = DataNormalizer()
        self.reliability_tracker = DataSourceReliabilityTracker()

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

        # 1. Fetch raw response via Gateway
        try:
            resp = self.gateway.fetch(request)
        except Exception as e:
            # Handle failure
            self.reliability_tracker.record_metrics(
                provider_id=provider_id,
                availability=0.0,
                error_rate=1.0,
                consistency=0.0,
                completeness=0.0
            )
            # Create a completely failed report
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

        if not resp.is_success:
            # Record failed availability
            self.reliability_tracker.record_metrics(
                provider_id=resp.provider_id,
                availability=0.0,
                error_rate=1.0,
                consistency=0.0,
                completeness=0.0
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
            completeness=report.quality_scores.completeness_score
        )

        if not report.is_acceptable:
            # Reject corrupted dataset
            return [], report

        # 4. Normalize records
        normalized_records = self.normalizer.normalize_records(resp.raw_data, resp.provider_id)
        return normalized_records, report
