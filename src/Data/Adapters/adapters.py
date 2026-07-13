import csv
import io
import json
import math
from datetime import datetime
from typing import Dict, List, Optional, Union

from src.Infrastructure.exceptions import ValidationException
from src.Data.MarketData.Interfaces.interfaces import IMarketDataProvider
from src.Data.MarketData.Models.models import MarketDataRequest, MarketDataResponse, MarketDataPoint
from src.Data.Models.models import (
    HistoricalRecord,
    DatasetMetadata,
    HistoricalDataset,
    MarketDataBatch
)


class HistoricalDataValidator:
    """Validator for historical datasets and records, ensuring integrity and logical correctness."""

    @staticmethod
    def validate_record(record: HistoricalRecord) -> None:
        """Validates a single HistoricalRecord. Raises ValidationException on failure."""
        if not record.AssetId or not record.AssetId.strip():
            raise ValidationException("Validation Error: Asset identifier cannot be empty or blank.")

        if record.Timestamp is None:
            raise ValidationException("Validation Error: Timestamp cannot be missing or null.")

        # Prices cannot be negative, NaN, or infinite
        for name, val in [("Open", record.Open), ("High", record.High), ("Low", record.Low), ("Close", record.Close)]:
            if val is None or math.isnan(val) or math.isinf(val) or val < 0:
                raise ValidationException(f"Validation Error: '{name}' price must be non-negative and valid. Value={val}")

        # Volume must be non-negative and valid
        if record.Volume is None or math.isnan(record.Volume) or math.isinf(record.Volume) or record.Volume < 0:
            raise ValidationException(f"Validation Error: Volume must be non-negative and valid. Value={record.Volume}")

        # Logical boundary checks
        if record.Low > record.High:
            raise ValidationException(f"Validation Error: Low price ({record.Low}) cannot be higher than High price ({record.High}).")

        if record.Open > record.High:
            raise ValidationException(f"Validation Error: Open price ({record.Open}) cannot be higher than High price ({record.High}).")

        if record.Close > record.High:
            raise ValidationException(f"Validation Error: Close price ({record.Close}) cannot be higher than High price ({record.High}).")

        if record.Low > record.Open:
            raise ValidationException(f"Validation Error: Low price ({record.Low}) cannot be higher than Open price ({record.Open}).")

        if record.Low > record.Close:
            raise ValidationException(f"Validation Error: Low price ({record.Low}) cannot be higher than Close price ({record.Close}).")

    @classmethod
    def validate_dataset(cls, dataset: HistoricalDataset) -> None:
        """Validates a complete HistoricalDataset. Raises ValidationException on failure."""
        if dataset.Metadata is None:
            raise ValidationException("Validation Error: Dataset metadata cannot be null.")

        if not dataset.Records:
            raise ValidationException("Validation Error: Dataset must not be empty.")

        for i, record in enumerate(dataset.Records):
            try:
                cls.validate_record(record)
            except ValidationException as e:
                raise ValidationException(f"Validation Error in record {i}: {str(e)}") from e


class MarketDataLoader:
    """Responsible for reading and parsing CSV or JSON dataset sources."""

    def load_from_csv(
        self,
        source: str,
        is_filepath: bool = True,
        asset_id_override: Optional[str] = None,
        timeframe: str = "H1"
    ) -> List[HistoricalRecord]:
        """Reads CSV dataset source and parses it into standard HistoricalRecords."""
        try:
            if is_filepath:
                with open(source, mode='r', encoding='utf-8') as f:
                    content = f.read()
            else:
                content = source
        except Exception as e:
            raise ValidationException(f"Failed to read CSV source: {str(e)}") from e

        if not content or not content.strip():
            raise ValidationException("Validation Error: CSV dataset is empty.")

        records: List[HistoricalRecord] = []
        try:
            reader = csv.DictReader(io.StringIO(content.strip()))

            fieldnames = reader.fieldnames
            if not fieldnames:
                raise ValidationException("Validation Error: CSV file has no headers.")

            header_map = {}
            for f in fieldnames:
                f_lower = f.strip().lower()
                header_map[f_lower] = f

            # Map column names case-insensitively or with common variants
            timestamp_key = header_map.get("timestamp") or header_map.get("t") or header_map.get("date") or header_map.get("time")
            open_key = header_map.get("open") or header_map.get("o")
            high_key = header_map.get("high") or header_map.get("h")
            low_key = header_map.get("low") or header_map.get("l")
            close_key = header_map.get("close") or header_map.get("c")
            volume_key = header_map.get("volume") or header_map.get("v")
            asset_key = header_map.get("asset_id") or header_map.get("assetid") or header_map.get("asset") or header_map.get("symbol")

            # Validate that essential columns are present
            if not timestamp_key:
                raise ValidationException("Validation Error: CSV lacks a timestamp/time column.")
            if not open_key:
                raise ValidationException("Validation Error: CSV lacks an Open price column.")
            if not high_key:
                raise ValidationException("Validation Error: CSV lacks a High price column.")
            if not low_key:
                raise ValidationException("Validation Error: CSV lacks a Low price column.")
            if not close_key:
                raise ValidationException("Validation Error: CSV lacks a Close price column.")
            if not volume_key:
                raise ValidationException("Validation Error: CSV lacks a Volume column.")

            for row_idx, row in enumerate(reader, start=1):
                # Ensure all values are present in row
                for key in (timestamp_key, open_key, high_key, low_key, close_key, volume_key):
                    if row.get(key) is None or row[key].strip() == "":
                        raise ValidationException(f"Row {row_idx}: Missing required data field.")

                raw_ts = row[timestamp_key].strip()
                raw_open = row[open_key].strip()
                raw_high = row[high_key].strip()
                raw_low = row[low_key].strip()
                raw_close = row[close_key].strip()
                raw_volume = row[volume_key].strip()

                # Parse timestamp
                try:
                    if raw_ts.isdigit():
                        ts = datetime.fromtimestamp(int(raw_ts))
                    else:
                        try:
                            ts = datetime.fromisoformat(raw_ts)
                        except ValueError:
                            # Try general formats
                            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d", "%m/%d/%Y %H:%M:%S", "%d/%m/%Y %H:%M:%S"):
                                try:
                                    ts = datetime.strptime(raw_ts, fmt)
                                    break
                                except ValueError:
                                    continue
                            else:
                                raise ValueError(f"Unrecognized datetime format: {raw_ts}")
                except Exception as e:
                    raise ValidationException(f"Row {row_idx}: Invalid timestamp '{raw_ts}': {str(e)}")

                # Parse prices & volume
                try:
                    o = float(raw_open)
                    h = float(raw_high)
                    l = float(raw_low)
                    c = float(raw_close)
                    v = float(raw_volume)
                except ValueError as e:
                    raise ValidationException(f"Row {row_idx}: Non-numeric price/volume: {str(e)}")

                # Resolve asset ID
                resolved_asset = asset_id_override
                if not resolved_asset:
                    if asset_key and row.get(asset_key):
                        resolved_asset = row[asset_key].strip()
                    else:
                        resolved_asset = "UNKNOWN"

                record = HistoricalRecord(
                    AssetId=resolved_asset,
                    Timestamp=ts,
                    Open=o,
                    High=h,
                    Low=l,
                    Close=c,
                    Volume=v
                )
                records.append(record)

        except ValidationException:
            raise
        except Exception as e:
            raise ValidationException(f"Validation Error: Corrupted or unparseable CSV data: {str(e)}") from e

        return records

    def load_from_json(
        self,
        source: str,
        is_filepath: bool = True,
        asset_id_override: Optional[str] = None,
        timeframe: str = "H1"
    ) -> List[HistoricalRecord]:
        """Reads JSON dataset source and parses it into standard HistoricalRecords."""
        try:
            if is_filepath:
                with open(source, mode='r', encoding='utf-8') as f:
                    data = json.load(f)
            else:
                data = json.loads(source)
        except Exception as e:
            raise ValidationException(f"Failed to read/parse JSON source: {str(e)}") from e

        if data is None:
            raise ValidationException("Validation Error: JSON dataset is empty.")

        # Determine if JSON is wrapped in a metadata object or directly is a list
        records_list = []
        if isinstance(data, list):
            records_list = data
        elif isinstance(data, dict):
            # Might have a key like "records" or "data" or "data_points"
            for k in ("records", "data", "data_points"):
                if k in data and isinstance(data[k], list):
                    records_list = data[k]
                    break
            else:
                # If it's a dict but doesn't have an obvious list key, maybe it is a single record?
                records_list = [data]
        else:
            raise ValidationException("Validation Error: JSON dataset format must be list or object.")

        if not records_list:
            raise ValidationException("Validation Error: JSON records list is empty.")

        records: List[HistoricalRecord] = []
        for idx, item in enumerate(records_list, start=1):
            if not isinstance(item, dict):
                raise ValidationException(f"Record {idx}: Must be a JSON object (dictionary).")

            # Resolve key variations
            item_lower = {k.lower(): v for k, v in item.items()}

            timestamp_val = item_lower.get("timestamp") or item_lower.get("t") or item_lower.get("date") or item_lower.get("time")
            open_val = item_lower.get("open") or item_lower.get("o")
            high_val = item_lower.get("high") or item_lower.get("h")
            low_val = item_lower.get("low") or item_lower.get("l")
            close_val = item_lower.get("close") or item_lower.get("c")
            volume_val = item_lower.get("volume") or item_lower.get("v")
            asset_val = item_lower.get("asset_id") or item_lower.get("assetid") or item_lower.get("asset") or item_lower.get("symbol")

            # Check that all fields are present
            if timestamp_val is None:
                raise ValidationException(f"Record {idx}: Missing timestamp field.")
            if open_val is None:
                raise ValidationException(f"Record {idx}: Missing Open price.")
            if high_val is None:
                raise ValidationException(f"Record {idx}: Missing High price.")
            if low_val is None:
                raise ValidationException(f"Record {idx}: Missing Low price.")
            if close_val is None:
                raise ValidationException(f"Record {idx}: Missing Close price.")
            if volume_val is None:
                raise ValidationException(f"Record {idx}: Missing Volume.")

            # Parse timestamp
            try:
                if isinstance(timestamp_val, (int, float)):
                    ts = datetime.fromtimestamp(int(timestamp_val))
                else:
                    raw_ts = str(timestamp_val).strip()
                    try:
                        ts = datetime.fromisoformat(raw_ts)
                    except ValueError:
                        # Try fallback formats
                        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d", "%m/%d/%Y %H:%M:%S", "%d/%m/%Y %H:%M:%S"):
                            try:
                                ts = datetime.strptime(raw_ts, fmt)
                                break
                            except ValueError:
                                continue
                        else:
                            raise ValueError(f"Unrecognized datetime format: {raw_ts}")
            except Exception as e:
                raise ValidationException(f"Record {idx}: Invalid timestamp '{timestamp_val}': {str(e)}")

            # Parse prices & volume
            try:
                o = float(open_val)
                h = float(high_val)
                l = float(low_val)
                c = float(close_val)
                v = float(volume_val)
            except (ValueError, TypeError) as e:
                raise ValidationException(f"Record {idx}: Non-numeric price/volume: {str(e)}")

            # Resolve asset ID
            resolved_asset = asset_id_override
            if not resolved_asset:
                if asset_val:
                    resolved_asset = str(asset_val).strip()
                else:
                    resolved_asset = "UNKNOWN"

            record = HistoricalRecord(
                AssetId=resolved_asset,
                Timestamp=ts,
                Open=o,
                High=h,
                Low=l,
                Close=c,
                Volume=v
            )
            records.append(record)

        return records


class DatasetRepository:
    """Manages the in-memory lifecycle and metadata of historical datasets."""

    def __init__(self) -> None:
        self._datasets: Dict[str, HistoricalDataset] = {}

    def add_dataset(self, dataset: HistoricalDataset) -> None:
        """Stores or updates a historical dataset."""
        if dataset.Metadata is None:
            raise ValidationException("Validation Error: Dataset metadata cannot be null.")
        self._datasets[dataset.Metadata.DatasetId] = dataset

    def get_dataset(self, dataset_id: str) -> Optional[HistoricalDataset]:
        """Retrieves a historical dataset by its unique ID."""
        return self._datasets.get(dataset_id)

    def get_dataset_by_asset(self, asset_id: str) -> Optional[HistoricalDataset]:
        """Retrieves a historical dataset by asset identifier."""
        for ds in self._datasets.values():
            if ds.Metadata.AssetId == asset_id:
                return ds
        return None

    def list_datasets(self) -> List[DatasetMetadata]:
        """Retrieves metadata of all available datasets."""
        return [ds.Metadata for ds in self._datasets.values()]

    def delete_dataset(self, dataset_id: str) -> bool:
        """Deletes a dataset from the repository. Returns True if deleted, False otherwise."""
        if dataset_id in self._datasets:
            del self._datasets[dataset_id]
            return True
        return False

    def clear(self) -> None:
        """Clears all datasets from the repository."""
        self._datasets.clear()


class HistoricalDataAdapter(IMarketDataProvider):
    """
    Historical data intelligence adapter coordinating between DatasetRepository,
    MarketDataLoader, and validation engines. Implements standard IMarketDataProvider.
    """

    def __init__(
        self,
        repository: Optional[DatasetRepository] = None,
        loader: Optional[MarketDataLoader] = None
    ) -> None:
        self._repository = repository or DatasetRepository()
        self._loader = loader or MarketDataLoader()

    @property
    def repository(self) -> DatasetRepository:
        return self._repository

    @property
    def loader(self) -> MarketDataLoader:
        return self._loader

    def load_and_register_dataset(
        self,
        dataset_id: str,
        name: str,
        asset_id: str,
        timeframe: str,
        source: str,
        format: str = "CSV",
        is_filepath: bool = True
    ) -> HistoricalDataset:
        """
        Loads a dataset using MarketDataLoader, validates it, and registers it in DatasetRepository.
        """
        if format.upper() == "CSV":
            records = self._loader.load_from_csv(source, is_filepath, asset_id, timeframe)
        elif format.upper() == "JSON":
            records = self._loader.load_from_json(source, is_filepath, asset_id, timeframe)
        else:
            raise ValidationException(f"Unsupported format: {format}")

        metadata = DatasetMetadata(
            DatasetId=dataset_id,
            Name=name,
            AssetId=asset_id,
            Timeframe=timeframe,
            Format=format,
            RecordCount=len(records),
            FilePath=source if is_filepath else None
        )

        dataset = HistoricalDataset(Metadata=metadata, Records=records)

        # Validate complete dataset using HistoricalDataValidator
        HistoricalDataValidator.validate_dataset(dataset)

        # Store in repository
        self._repository.add_dataset(dataset)
        return dataset

    def retrieve_market_data(self, request: MarketDataRequest) -> MarketDataResponse:
        """
        Retrieves historical data points converted to MarketDataPoint domain models
        for the given asset and timeframe within start and end time boundaries.
        """
        dataset = self._repository.get_dataset_by_asset(request.Asset)
        if not dataset:
            raise ValidationException(f"Validation Error: No historical dataset found for asset {request.Asset}.")

        # Filter records based on start/end times
        filtered_points = []
        for record in dataset.Records:
            if request.StartTime <= record.Timestamp <= request.EndTime:
                pt = MarketDataPoint(
                    AssetId=record.AssetId,
                    Timestamp=record.Timestamp,
                    Open=record.Open,
                    High=record.High,
                    Low=record.Low,
                    Close=record.Close,
                    Volume=record.Volume
                )
                filtered_points.append(pt)

        return MarketDataResponse(
            Request=request,
            DataPoints=filtered_points,
            RetrievedAt=datetime.now()
        )

    def retrieve_market_data_batch(self, asset_id: str) -> MarketDataBatch:
        """Retrieves a packaged batch of all historical records for an asset."""
        dataset = self._repository.get_dataset_by_asset(asset_id)
        if not dataset:
            raise ValidationException(f"Validation Error: No historical dataset found for asset {asset_id}.")
        return MarketDataBatch(AssetId=asset_id, Records=dataset.Records)
