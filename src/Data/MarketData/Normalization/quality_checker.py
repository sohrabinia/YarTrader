from typing import List
from src.Data.MarketData.Interfaces.interfaces import IDataQualityChecker
from src.Data.MarketData.Models.models import MarketDataPoint
from src.Data.Common.models import DataQualityReport
from src.Data.MarketData.Normalization.validator import MarketDataValidator

class DataQualityChecker(IDataQualityChecker):
    """
    Performs comprehensive data quality audits on lists of market records,
    tracking schema conformance and anomaly warnings.
    """
    def __init__(self) -> None:
        self._validator = MarketDataValidator()

    def check_quality(self, points: List[MarketDataPoint]) -> DataQualityReport:
        if not points:
            return DataQualityReport(
                TotalRecords=0,
                ValidRecords=0,
                InvalidRecords=0,
                Warnings=["Data point stream is empty"]
            )

        valid_cnt = 0
        invalid_cnt = 0
        warnings: List[str] = []

        for i, pt in enumerate(points):
            if self._validator.validate_single_point(pt):
                valid_cnt += 1
            else:
                invalid_cnt += 1
                warnings.append(
                    f"Invalid record detected at index {i} for asset '{pt.AssetId}' "
                    f"[O={pt.Open}, H={pt.High}, L={pt.Low}, C={pt.Close}, V={pt.Volume}]"
                )

        # Look for statistical outlier warnings (e.g., zero volume warnings)
        for i, pt in enumerate(points):
            if pt.Volume == 0:
                warnings.append(f"Warning: Zero volume recorded at index {i} for asset '{pt.AssetId}'.")

        return DataQualityReport(
            TotalRecords=len(points),
            ValidRecords=valid_cnt,
            InvalidRecords=invalid_cnt,
            Warnings=warnings
        )
