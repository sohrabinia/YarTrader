import os
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict

from src.Application.Deployment.storage import YarTraderStorageManager

logger = logging.getLogger("TradeJournal")


@dataclass
class TradeJournalRecord:
    """
    Immutable Trade Journal Record containing complete lifecycle facts,
    excursion metrics (MFE/MAE), decision evidence, and broker execution tickets.
    """
    decision_id: str
    trade_id: str
    cycle_id: str
    symbol: str
    timeframe: str
    direction: str
    planned_entry: float
    planned_sl: float
    planned_tp: float
    planned_rr: float
    actual_entry: float
    actual_exit: float
    volume: float
    confidence: float
    reasoning: List[str]
    evidence: Dict[str, Any]
    order_ticket: str
    deal_ticket: str
    open_time: str
    close_time: str
    exit_reason: str
    pnl: float
    pnl_percent: float
    mfe: float
    mae: float
    duration: float
    market_regime: str
    result: str  # WIN | LOSS | BREAKEVEN | PENDING
    configuration_version: str
    entry_efficiency_pct: float = 0.0
    exit_efficiency_pct: float = 0.0
    move_capture_ratio: float = 0.0
    brier_score_contribution: float = 0.0
    platform_provenance: str = "MT5"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "TradeJournalRecord":
        return cls(**d)


class TradeJournalManager:
    """
    Manages immutable trade journal persistence strictly under YarTraderStorageManager.
    """
    _instance: Optional["TradeJournalManager"] = None

    @classmethod
    def get_instance(cls) -> "TradeJournalManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self, journal_file: Optional[str] = None):
        storage_mgr = YarTraderStorageManager.get_manager()
        if journal_file:
            self.journal_file = journal_file
        else:
            self.journal_file = os.path.join(storage_mgr.get_logs_dir(), "trade_journal.json")

        os.makedirs(os.path.dirname(self.journal_file), exist_ok=True)
        self.records: List[TradeJournalRecord] = self._load_journal()

    def _load_journal(self) -> List[TradeJournalRecord]:
        if os.path.exists(self.journal_file):
            try:
                with open(self.journal_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return [TradeJournalRecord.from_dict(d) for d in data]
            except Exception as e:
                logger.warning(f"[TradeJournalManager] Error loading journal file: {e}")
                return []
        return []

    def save_journal(self) -> None:
        try:
            temp_path = self.journal_file + ".tmp"
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump([r.to_dict() for r in self.records], f, indent=2)
            os.replace(temp_path, self.journal_file)
        except Exception as e:
            logger.error(f"[TradeJournalManager] Failed to save journal: {e}")

    def add_record(self, record: TradeJournalRecord) -> None:
        """Adds a trade record if not already present, maintaining immutability for closed trades."""
        existing_ids = {r.trade_id for r in self.records}
        if record.trade_id not in existing_ids:
            self.records.append(record)
            self.save_journal()

    def update_record(self, record: TradeJournalRecord) -> None:
        """Updates an existing record (e.g. upon position closure)."""
        for i, r in enumerate(self.records):
            if r.trade_id == record.trade_id:
                self.records[i] = record
                self.save_journal()
                return
        self.add_record(record)

    def get_all_records(self) -> List[TradeJournalRecord]:
        return list(self.records)
