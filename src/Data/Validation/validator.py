from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class DataQualityScore:
    completeness_score: float  # 0.0 to 1.0
    timestamp_validity_score: float  # 0.0 to 1.0
    uniqueness_score: float  # 0.0 to 1.0
    consistency_score: float  # 0.0 to 1.0
    overall_score: float  # Weighted or average score


@dataclass(frozen=True)
class DataIntegrityReport:
    report_id: str
    provider_id: str
    analyzed_at: datetime
    quality_scores: DataQualityScore
    anomalies: List[str] = field(default_factory=list)
    schema_mismatches: List[str] = field(default_factory=list)
    is_acceptable: bool = True


class MarketDataValidator:
    """Performs core schema-level check on incoming records."""
    def validate_record_schema(self, record: Dict[str, Any], expected_fields: List[str]) -> List[str]:
        mismatches = []
        for f in expected_fields:
            if f not in record:
                mismatches.append(f"Missing required field: '{f}'")
        return mismatches


class DataQualityAnalyzer:
    """Analyzes multiple indicators of incoming external records to build a DataIntegrityReport."""
    def analyze_dataset(
        self,
        provider_id: str,
        records: List[Dict[str, Any]],
        expected_fields: Optional[List[str]] = None
    ) -> DataIntegrityReport:
        expected_fields = expected_fields or ["timestamp", "open", "high", "low", "close", "volume"]
        report_id = f"dir-{datetime.now().timestamp()}"

        if not records:
            scores = DataQualityScore(0.0, 0.0, 0.0, 0.0, 0.0)
            return DataIntegrityReport(
                report_id=report_id,
                provider_id=provider_id,
                analyzed_at=datetime.now(),
                quality_scores=scores,
                anomalies=["Dataset is completely empty."],
                is_acceptable=False
            )

        anomalies = []
        schema_mismatches = []

        # Track statistics
        missing_count = 0
        invalid_ts_count = 0
        seen_timestamps = set()
        duplicate_count = 0
        inconsistency_count = 0

        # Validator instance
        validator = MarketDataValidator()

        for idx, r in enumerate(records):
            # 1. Schema check
            mismatches = validator.validate_record_schema(r, expected_fields)
            if mismatches:
                schema_mismatches.extend([f"Record {idx}: {f}" for f in mismatches])
                missing_count += len(mismatches)

            # count present but None fields as missing/incomplete
            for f in expected_fields:
                if f not in mismatches and r.get(f) is None:
                    missing_count += 1

            # 2. Timestamp check
            ts = r.get("timestamp")
            if ts is None:
                invalid_ts_count += 1
            else:
                try:
                    if isinstance(ts, (int, float)):
                        datetime.fromtimestamp(ts)
                    elif isinstance(ts, str):
                        datetime.fromisoformat(ts)
                    elif isinstance(ts, datetime):
                        pass
                    else:
                        raise ValueError()
                except Exception:
                    invalid_ts_count += 1
                    anomalies.append(f"Record {idx}: Invalid timestamp type/value '{ts}'")

            # 3. Duplicate check
            if ts is not None:
                if ts in seen_timestamps:
                    duplicate_count += 1
                else:
                    seen_timestamps.add(ts)

            # 4. Consistency check (e.g. low <= high, open/close within high/low range)
            o = r.get("open")
            h = r.get("high")
            l = r.get("low")
            c = r.get("close")
            if o is not None and h is not None and l is not None and c is not None:
                try:
                    o_f, h_f, l_f, c_f = float(o), float(h), float(l), float(c)
                    if l_f > h_f:
                        inconsistency_count += 1
                        anomalies.append(f"Record {idx}: Low price {l_f} exceeds High price {h_f}.")
                    if o_f < l_f or o_f > h_f or c_f < l_f or c_f > h_f:
                        inconsistency_count += 1
                        anomalies.append(f"Record {idx}: Open or Close prices exceed high/low boundaries.")
                except Exception:
                    inconsistency_count += 1
                    anomalies.append(f"Record {idx}: Non-numeric price encountered.")

        # Compute Scores
        total_records = len(records)
        expected_total_fields = total_records * len(expected_fields)
        completeness = max(0.0, 1.0 - (missing_count / expected_total_fields))
        ts_validity = max(0.0, 1.0 - (invalid_ts_count / total_records))
        uniqueness = max(0.0, 1.0 - (duplicate_count / total_records))
        consistency = max(0.0, 1.0 - (inconsistency_count / total_records))

        overall = (completeness * 0.3) + (ts_validity * 0.2) + (uniqueness * 0.2) + (consistency * 0.3)

        scores = DataQualityScore(
            completeness_score=round(completeness, 4),
            timestamp_validity_score=round(ts_validity, 4),
            uniqueness_score=round(uniqueness, 4),
            consistency_score=round(consistency, 4),
            overall_score=round(overall, 4)
        )

        # Enforce price consistency, uniqueness, and completeness limits
        is_acceptable = overall >= 0.80 and completeness >= 0.80 and consistency >= 0.80

        return DataIntegrityReport(
            report_id=report_id,
            provider_id=provider_id,
            analyzed_at=datetime.now(),
            quality_scores=scores,
            anomalies=anomalies[:50],  # cap list size
            schema_mismatches=schema_mismatches[:50],
            is_acceptable=is_acceptable
        )
