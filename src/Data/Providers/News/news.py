from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from src.Data.External.interfaces import IDataProvider
from src.Data.External.models import DataSourceType, DataProviderMetadata, ExternalDataRequest, ExternalDataResponse, ProviderHealthStatus
from src.Infrastructure.exceptions import ValidationException


@dataclass(frozen=True)
class NewsMetadata:
    source_name: str
    author: Optional[str] = None
    language: str = "en"
    url: Optional[str] = None


@dataclass(frozen=True)
class NewsRecord:
    article_id: str
    headline: str
    timestamp: datetime
    category: str  # e.g., FOMC, Regulation, Tech, Earnings
    summary: str
    meta: NewsMetadata


class NewsDataProvider(IDataProvider):
    """
    Ingestion Provider for financial news and analyst insights.
    Stores and indexes text items passively. Contains zero automated trading indicators.
    """
    def __init__(self, provider_id: str = "news-provider") -> None:
        self._metadata = DataProviderMetadata(
            provider_id=provider_id,
            source_type=DataSourceType.NEWS_PROVIDER,
            supported_symbols=["FOMC_NEWS", "REG_NEWS", "CORP_EARNINGS"]
        )
        self._health = ProviderHealthStatus.HEALTHY

    @property
    def metadata(self) -> DataProviderMetadata:
        return self._metadata

    def set_health(self, health: ProviderHealthStatus) -> None:
        self._health = health

    def check_health(self) -> ProviderHealthStatus:
        return self._health

    def fetch_data(self, request: ExternalDataRequest) -> ExternalDataResponse:
        if self._health == ProviderHealthStatus.UNHEALTHY:
            return ExternalDataResponse(
                request_id=request.request_id or "id",
                provider_id=self._metadata.provider_id,
                raw_data=[],
                is_success=False,
                error_message="News Provider connection offline."
            )

        # Simulate fetching news articles
        articles = []
        curr = request.start_time

        if request.symbol == "FOMC_NEWS":
            articles.append({
                "article_id": "news-fomc-1",
                "headline": "Fed Holds Rates Steady at FOMC Meeting",
                "timestamp": curr.isoformat(),
                "category": "FOMC",
                "summary": "The Federal Open Market Committee voted unanimously to keep interest rate bands unchanged.",
                "source": "Financial Chronicle",
                "author": "J. Doe",
                "language": "en"
            })
        elif request.symbol == "REG_NEWS":
            articles.append({
                "article_id": "news-reg-1",
                "headline": "New Regulatory Thresholds Issued for Digital Assets",
                "timestamp": curr.isoformat(),
                "category": "Regulation",
                "summary": "SEC updates compliance reporting bounds for crypto assets.",
                "source": "RegWatch",
                "language": "en"
            })
        else:
            articles.append({
                "article_id": f"news-{request.symbol.lower()}-1",
                "headline": f"Insight update: {request.symbol}",
                "timestamp": curr.isoformat(),
                "category": "MarketUpdate",
                "summary": "Passive reporting index details published.",
                "source": "Financial Feed",
                "language": "en"
            })

        return ExternalDataResponse(
            request_id=request.request_id or "id",
            provider_id=self._metadata.provider_id,
            raw_data=articles,
            is_success=True
        )

    def fetch_news_records(self, request: ExternalDataRequest) -> List[NewsRecord]:
        resp = self.fetch_data(request)
        if not resp.is_success:
            return []

        parsed_news = []
        for r in resp.raw_data:
            try:
                meta = NewsMetadata(
                    source_name=r["source"],
                    author=r.get("author"),
                    language=r.get("language", "en"),
                    url=r.get("url")
                )
                rec = NewsRecord(
                    article_id=r["article_id"],
                    headline=r["headline"],
                    timestamp=datetime.fromisoformat(r["timestamp"]),
                    category=r["category"],
                    summary=r["summary"],
                    meta=meta
                )
                parsed_news.append(rec)
            except Exception as e:
                raise ValidationException(f"News Parsing Error: Failed to parse news record. Details: {e}")
        return parsed_news
