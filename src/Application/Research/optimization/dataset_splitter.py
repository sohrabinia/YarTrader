import hashlib
import json
from typing import List, Dict, Any, Tuple

class DatasetSplitter:
    """
    Deterministic historical-data splitter for YarTrader Research.
    Splits candles chronologically into Train, Validation, and Test sets without random shuffling or future leakage.
    """
    @staticmethod
    def calculate_dataset_hash(candles: List[Dict[str, Any]]) -> str:
        """Computes SHA-256 hash of dataset to guarantee provenance."""
        if not candles:
            return "empty-dataset"
        first_ts = str(candles[0].get("timestamp", ""))
        last_ts = str(candles[-1].get("timestamp", ""))
        payload = f"len:{len(candles)}-first:{first_ts}-last:{last_ts}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]

    @classmethod
    def split_chronological(
        self,
        candles: List[Dict[str, Any]],
        train_ratio: float = 0.60,
        val_ratio: float = 0.20,
        test_ratio: float = 0.20
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Splits candles array strictly chronologically.
        Default: Train 60%, Validation 20%, Test 20%.
        """
        total = len(candles)
        if total == 0:
            return {"train": [], "validation": [], "test": []}

        # Normalize ratios to sum to 1.0
        s = train_ratio + val_ratio + test_ratio
        tr = train_ratio / s
        vr = val_ratio / s

        train_end = int(total * tr)
        val_end = train_end + int(total * vr)

        train_set = candles[:train_end]
        val_set = candles[train_end:val_end]
        test_set = candles[val_end:]

        return {
            "train": train_set,
            "validation": val_set,
            "test": test_set,
            "hash": self.calculate_dataset_hash(candles)
        }
