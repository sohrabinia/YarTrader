from dataclasses import dataclass, field
from typing import List

@dataclass(frozen=True)
class DataQualityReport:
    """Represents the outcome of a quality evaluation audit on a set of market records."""
    TotalRecords: int
    ValidRecords: int
    InvalidRecords: int
    Warnings: List[str] = field(default_factory=list)

    @property
    def total_records(self) -> int:
        return self.TotalRecords

    @property
    def valid_records(self) -> int:
        return self.ValidRecords

    @property
    def invalid_records(self) -> int:
        return self.InvalidRecords

    @property
    def warnings(self) -> List[str]:
        return self.Warnings
