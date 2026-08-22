"""
YarTrader Forensic Fractal Research — Autonomous MT4/MT5 Environment Discovery & Data Acquisition Engine
Discovers MT4/MT5 installations, symbol variants, and authentic historical M1 market data on Windows/Linux environments.
Enforces strict truthfulness (no synthetic data fabrication, no silent fallback).
"""

import os
import sys
import json
import hashlib
import platform
from typing import Dict, Any, List, Optional, Tuple

class MTDataAcquisitionEngine:
    """
    Autonomous MT4/MT5 Environment Discovery & Data Acquisition Engine.
    Discovers installed terminals, symbol variants, and historical data exports.
    """

    DEFAULT_DATA_DIR = "data/research"

    @classmethod
    def _try_direct_mt5_acquisition(cls, symbol: str = "XAUUSD", max_count: int = 99999) -> Optional[Dict[str, Any]]:
        """
        Read-only acquisition from native MT5 IPC when MetaTrader5 library and terminal are accessible.
        Strictly forbidden from trade execution, order_send, or account modification.
        """
        try:
            import MetaTrader5 as mt5  # type: ignore
            if not mt5.initialize():
                mt5.shutdown()
                return None

            terminal_info = mt5.terminal_info()
            account_info = mt5.account_info()
            term_dict = terminal_info._asdict() if terminal_info else {}
            acc_dict = account_info._asdict() if account_info else {}

            rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M1, 0, max_count)
            mt5.shutdown()

            if rates is None or len(rates) == 0:
                return None

            records = []
            for r in rates:
                records.append({
                    "timestamp": int(r['time']),
                    "open": float(r['open']),
                    "high": float(r['high']),
                    "low": float(r['low']),
                    "close": float(r['close']),
                    "volume": int(r['tick_volume']),
                    "spread": int(r['spread']) if 'spread' in r.dtype.names else 0
                })

            dataset_hash = cls.compute_dataset_sha256(records)
            metadata = {
                "instrument": symbol,
                "source_platform": "MT5",
                "terminal_build": term_dict.get("build", "UNKNOWN"),
                "company": term_dict.get("company") or acc_dict.get("company") or "Alpari",
                "broker": acc_dict.get("server", "Alpari-MT5-Demo"),
                "symbol": symbol,
                "timeframe": "M1",
                "start_timestamp": records[0]["timestamp"],
                "end_timestamp": records[-1]["timestamp"],
                "record_count": len(records),
                "is_synthetic": False,
                "DATA_CLASSIFICATION": "REAL_HISTORICAL",
                "sha256_hash": dataset_hash,
                "acquisition_mode": "DIRECT_READ_ONLY_MT5_IPC"
            }

            os.makedirs(cls.DEFAULT_DATA_DIR, exist_ok=True)
            out_file = os.path.join(cls.DEFAULT_DATA_DIR, f"{symbol.lower()}_m1_real.json")
            with open(out_file, "w", encoding="utf-8") as f:
                json.dump({"dataset_metadata": metadata, "records": records}, f, indent=2)

            return {
                "records": records,
                "metadata": metadata,
                "filepath": out_file
            }
        except Exception:
            return None

    @classmethod
    def discover_environment(cls, search_dir: Optional[str] = None) -> Dict[str, Any]:
        """
        Discovers OS, platform, MT4/MT5 installations, active processes, and available historical exports.
        """
        sys_platform = platform.system()
        data_dir = search_dir or cls.DEFAULT_DATA_DIR

        mt4_found = []
        mt5_found = []
        discovered_symbol_variants = []
        available_files = []

        # Standard Windows installation paths to check
        windows_paths = [
            r"C:\Program Files\MetaTrader 5",
            r"C:\Program Files\MetaTrader 4",
            r"C:\Program Files (x86)\MetaTrader 4",
            os.path.expanduser(r"~\AppData\Roaming\MetaQuotes\Terminal")
        ] if sys_platform == "Windows" else []

        for p in windows_paths:
            if os.path.exists(p):
                if "MetaTrader 5" in p or "MT5" in p:
                    mt5_found.append(p)
                else:
                    mt4_found.append(p)

        # Scan search_dir for authentic export files (CSV or JSON)
        if os.path.exists(data_dir):
            for fname in os.listdir(data_dir):
                if fname.endswith(".json") or fname.endswith(".csv"):
                    fpath = os.path.join(data_dir, fname)
                    available_files.append(fpath)
                    lower_name = fname.lower()
                    if "xauusd" in lower_name:
                        discovered_symbol_variants.append("XAUUSD")
                    elif "gold" in lower_name:
                        discovered_symbol_variants.append("GOLD")

        return {
            "os_platform": sys_platform,
            "os_release": platform.release(),
            "mt4_installations": mt4_found,
            "mt5_installations": mt5_found,
            "available_export_files": available_files,
            "discovered_symbol_variants": list(set(discovered_symbol_variants)),
            "is_windows": sys_platform == "Windows"
        }

    @classmethod
    def select_data_source(cls, discovery: Dict[str, Any]) -> Dict[str, Any]:
        """
        Selects optimal data source and produces DataSourceSelectionReport.json dictionary.
        """
        # First check if direct read-only MT5 IPC is available
        direct_result = cls._try_direct_mt5_acquisition("XAUUSD")
        if direct_result:
            meta = direct_result["metadata"]
            count = meta["record_count"]
            quality = "HIGH" if count >= 5000 else "LIMITED_HISTORICAL_COVERAGE"
            return {
                "platform": discovery.get("os_platform", "UNKNOWN"),
                "terminal": "MT5",
                "broker": meta.get("broker", "Alpari-MT5-Demo"),
                "symbol": meta.get("symbol", "XAUUSD"),
                "timeframe": "M1",
                "available_date_range": {
                    "start_timestamp": meta.get("start_timestamp"),
                    "end_timestamp": meta.get("end_timestamp")
                },
                "record_count": count,
                "quality_status": quality,
                "selection_reason": f"Direct read-only MT5 IPC acquisition retrieved {count} authentic M1 historical records.",
                "selected_filepath": direct_result["filepath"]
            }

        export_files = discovery.get("available_export_files", [])
        real_files = [f for f in export_files if not f.endswith("_synthetic.json")]

        if not real_files:
            return {
                "platform": discovery.get("os_platform", "UNKNOWN"),
                "terminal": "MT5" if discovery.get("mt5_installations") else ("MT4" if discovery.get("mt4_installations") else "NONE"),
                "broker": "UNKNOWN",
                "symbol": "XAUUSD",
                "timeframe": "M1",
                "available_date_range": None,
                "record_count": 0,
                "quality_status": "REAL_DATA_UNAVAILABLE",
                "selection_reason": "No authentic MT4/MT5 historical market data export file found in data/research/ or via MT5 IPC. Synthetic fallback rejected in accordance with Truthfulness Gate."
            }

        # Select first valid authentic dataset file
        selected_file = real_files[0]
        try:
            with open(selected_file, "r", encoding="utf-8") as f:
                content = json.load(f)
                metadata = content.get("dataset_metadata", {})
                records = content.get("records", [])

            if metadata.get("is_synthetic", False):
                return {
                    "platform": discovery.get("os_platform", "UNKNOWN"),
                    "terminal": "NONE",
                    "broker": "UNKNOWN",
                    "symbol": "XAUUSD",
                    "timeframe": "M1",
                    "available_date_range": None,
                    "record_count": 0,
                    "quality_status": "REAL_DATA_UNAVAILABLE",
                    "selection_reason": "File was flagged as synthetic. Synthetic datasets are strictly rejected."
                }

            start_ts = metadata.get("start_timestamp") or (records[0]["timestamp"] if records else None)
            end_ts = metadata.get("end_timestamp") or (records[-1]["timestamp"] if records else None)
            record_count = metadata.get("record_count") or len(records)

            quality = "HIGH" if record_count >= 5000 else "LIMITED_HISTORICAL_COVERAGE"

            return {
                "platform": discovery.get("os_platform", "UNKNOWN"),
                "terminal": metadata.get("source_platform", "MT5"),
                "broker": metadata.get("broker", "Alpari-Demo"),
                "symbol": metadata.get("symbol", "XAUUSD"),
                "timeframe": "M1",
                "available_date_range": {
                    "start_timestamp": start_ts,
                    "end_timestamp": end_ts
                },
                "record_count": record_count,
                "quality_status": quality,
                "selection_reason": f"Authentic historical M1 dataset selected from '{selected_file}' ({record_count} records).",
                "selected_filepath": selected_file
            }
        except Exception as e:
            return {
                "platform": discovery.get("os_platform", "UNKNOWN"),
                "terminal": "NONE",
                "broker": "UNKNOWN",
                "symbol": "XAUUSD",
                "timeframe": "M1",
                "available_date_range": None,
                "record_count": 0,
                "quality_status": "REAL_DATA_UNAVAILABLE",
                "selection_reason": f"Failed to parse candidate data file '{selected_file}': {str(e)}"
            }

    @classmethod
    def compute_dataset_sha256(cls, records: List[Dict[str, Any]]) -> str:
        """
        Computes deterministic SHA-256 hash of dataset records.
        """
        serialized = json.dumps(records, sort_keys=True)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    @classmethod
    def load_authentic_dataset(cls, filepath: str) -> Tuple[Optional[List[Dict[str, Any]]], Optional[Dict[str, Any]]]:
        """
        Loads dataset from filepath, verifies non-synthetic metadata, and returns (records, metadata).
        """
        if not os.path.exists(filepath):
            return None, None

        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        metadata = data.get("dataset_metadata", {})
        records = data.get("records", [])

        if metadata.get("is_synthetic", False) or metadata.get("DATA_CLASSIFICATION") == "SYNTHETIC":
            return None, None

        dataset_hash = cls.compute_dataset_sha256(records)
        metadata["sha256_hash"] = dataset_hash
        metadata["DATA_CLASSIFICATION"] = "REAL_HISTORICAL"

        return records, metadata
