"""MT4 historical HST reader for backtesting.

Reads the terminal's local HST history directly; no MT5 API is touched.
Missing/unsupported history is reported as unavailable, never synthesized.
"""
from datetime import datetime, timezone
from pathlib import Path
from struct import unpack
from typing import List

from src.Data.External.interfaces import IDataProvider
from src.Data.External.models import (
    DataProviderMetadata, DataSourceType, ExternalDataRequest,
    ExternalDataResponse, ProviderHealthStatus,
)


class MT4HistoricalDataProvider(IDataProvider):
    TIMEFRAME_MINUTES = {"M1": 1, "M5": 5, "M15": 15, "M30": 30, "H1": 60, "H4": 240, "D1": 1440}

    def __init__(self, data_root: str | None = None):
        root = data_root or __import__("os").getenv("YARTRADER_MT4_DATA_ROOT", "")
        if root:
            self.data_root = Path(root)
        else:
            candidates = list(Path(r"C:\\Users").glob(r"*\\AppData\\Roaming\\MetaQuotes\\Terminal\\*"))
            self.data_root = next((p for p in candidates if (p / "history").exists() and (p / "MQL4").exists()), Path())

    @property
    def metadata(self) -> DataProviderMetadata:
        return DataProviderMetadata("mt4_historical", DataSourceType.MT4, [], 0)

    def _history_file(self, symbol: str, timeframe: str) -> Path:
        minutes = self.TIMEFRAME_MINUTES.get(str(timeframe).upper())
        if minutes is None:
            return Path()
        root = self.data_root / "history"
        matches = list(root.glob(f"**/{symbol.upper()}{minutes}.hst"))
        return matches[0] if matches else Path()

    def _supported_symbols(self) -> List[str]:
        root = self.data_root / "history"
        if not root.exists():
            return []
        result = set()
        for p in root.glob("**/*.hst"):
            for tf in self.TIMEFRAME_MINUTES.values():
                suffix = f"{tf}.hst"
                if p.name.endswith(suffix):
                    result.add(p.name[:-len(suffix)].upper())
        return sorted(result)

    def check_health(self) -> ProviderHealthStatus:
        return ProviderHealthStatus.HEALTHY if self.data_root.exists() and self._supported_symbols() else ProviderHealthStatus.UNHEALTHY

    def fetch_data(self, request: ExternalDataRequest) -> ExternalDataResponse:
        path = self._history_file(request.symbol, request.timeframe)
        if not path.exists():
            return ExternalDataResponse(request_id=request.request_id or "id", provider_id=self.metadata.provider_id,
                                        raw_data=[], is_success=False,
                                        error_message=f"MT4 history unavailable: {request.symbol} {request.timeframe}")
        try:
            rows = self._read_hst(path)
            start_ts = request.start_time.timestamp()
            end_ts = request.end_time.timestamp()
            filtered = [r for r in rows if start_ts <= r["time"] <= end_ts]
            return ExternalDataResponse(request_id=request.request_id or "id", provider_id=self.metadata.provider_id,
                                        raw_data=filtered, is_success=True)
        except Exception as exc:
            return ExternalDataResponse(request_id=request.request_id or "id", provider_id=self.metadata.provider_id,
                                        raw_data=[], is_success=False, error_message=f"MT4 HST read failed: {exc}")
    @staticmethod
    def _read_hst(path: Path) -> List[dict]:
        raw = path.read_bytes()
        if len(raw) < 148:
            return []
        # MT4 HST v401 records are 60 bytes: time, open/high/low/close,
        # tick volume, spread, real volume. Older v400 records are 44 bytes.
        version = unpack("<i", raw[0:4])[0]
        offset = 148
        record_size = 60 if version >= 401 else 44
        rows = []
        while offset + record_size <= len(raw):
            if record_size == 60:
                t, o, h, l, c, tick_volume, spread, real_volume = unpack("<qddddqiq", raw[offset:offset+60])
            else:
                t, o, h, l, c, volume, _ = unpack("<iddddii", raw[offset:offset+44])
                tick_volume, spread, real_volume = volume, 0, volume
            if t > 0 and h >= max(o, c, l) and l <= min(o, c, h):
                rows.append({
                    "timestamp": int(t), "time": int(t), "open": float(o), "high": float(h), "low": float(l),
                    "close": float(c), "volume": float(tick_volume), "tick_volume": float(tick_volume),
                    "spread": int(spread), "real_volume": float(real_volume),
                })
            offset += record_size
        return rows
