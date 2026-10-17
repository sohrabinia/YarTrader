import os
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict

from src.Application.Deployment.storage import YarTraderStorageManager
from src.Application.Deployment.sqlite_event_store import SQLiteEventStore

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
    platform_provenance: str = "UNKNOWN"
    # Context needed to compare DEMO, backtest, and research results honestly.
    trade_type: str = "UNKNOWN"  # DEMO | BACKTEST | PAPER | LIVE | RESEARCH; never infer silently
    strategy_style: str = "UNKNOWN"
    decision_timeframe: str = "UNKNOWN"
    setup_timeframe: str = "UNKNOWN"
    entry_timeframe: str = "UNKNOWN"
    execution_timeframe: str = "UNKNOWN"
    context_timeframes: List[str] = None
    entry_session: str = "UNKNOWN"
    entry_weekday: str = "UNKNOWN"
    entry_day_of_month: int = 0
    entry_month: int = 0
    entry_year: int = 0
    entry_time_utc: str = ""
    entry_time_local: str = ""
    timezone_name: str = "UTC"
    setup_description: str = ""
    invalidation_reason: str = ""
    management_notes: List[str] = None
    style_transitions: List[Dict[str, Any]] = None
    exit_analysis: str = ""
    lessons_learned: str = ""
    alternative_entry_analysis: str = ""
    conclusion: str = ""
    model_version: str = "UNKNOWN"
    strategy_version: str = "UNKNOWN"
    code_version: str = "UNKNOWN"
    data_source: str = "UNKNOWN"
    costs: Dict[str, Any] = None
    data_quality: Dict[str, Any] = None
    # Multi-timeframe structure and historical reaction evidence captured at decision time.
    historical_structure_analysis: Dict[str, Any] = None
    structural_levels: List[Dict[str, Any]] = None
    structural_hierarchy: Dict[str, Any] = None
    level_reaction_evidence: Dict[str, Any] = None
    entry_level_context: Dict[str, Any] = None
    breakout_rejection_outcome: Dict[str, Any] = None

    def __post_init__(self) -> None:
        self.context_timeframes = list(self.context_timeframes or [])
        self.management_notes = list(self.management_notes or [])
        self.style_transitions = list(self.style_transitions or [])
        self.costs = dict(self.costs or {})
        self.data_quality = dict(self.data_quality or {})
        self.historical_structure_analysis = dict(self.historical_structure_analysis or {})
        self.structural_levels = list(self.structural_levels or [])
        self.structural_hierarchy = dict(self.structural_hierarchy or {})
        self.level_reaction_evidence = dict(self.level_reaction_evidence or {})
        self.entry_level_context = dict(self.entry_level_context or {})
        self.breakout_rejection_outcome = dict(self.breakout_rejection_outcome or {})
        timestamp = self.entry_time_utc or self.open_time
        try:
            dt = datetime.fromisoformat(str(timestamp).replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            dt = dt.astimezone(timezone.utc)
            self.entry_time_utc = dt.isoformat()
            self.entry_weekday = self.entry_weekday if self.entry_weekday != "UNKNOWN" else dt.strftime("%A")
            self.entry_day_of_month = self.entry_day_of_month or dt.day
            self.entry_month = self.entry_month or dt.month
            self.entry_year = self.entry_year or dt.year
            if self.entry_session == "UNKNOWN":
                minute = dt.hour * 60 + dt.minute
                if minute < 7 * 60:
                    self.entry_session = "ASIA"
                elif minute < 12 * 60:
                    self.entry_session = "LONDON"
                elif minute < 16 * 60:
                    self.entry_session = "NEW_YORK_OVERLAP"
                elif minute < 21 * 60:
                    self.entry_session = "NEW_YORK"
                else:
                    self.entry_session = "LATE_US_OR_ROLLOVER"
        except (TypeError, ValueError, OverflowError):
            pass

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
        self._custom_journal_file = bool(journal_file)
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
                # A corrupt journal is not an empty journal. Fail closed so a later
                # save cannot silently replace the only surviving trade history.
                logger.exception("[TradeJournalManager] Journal load failed; refusing to treat it as empty.")
                raise RuntimeError(
                    f"Trade journal could not be loaded safely: {self.journal_file}. "
                    "Preserve/repair the file before writing new records."
                ) from e
        return []

    @property
    def events_file(self) -> str:
        # Production DEMO and backtest workers share one chronological event stream.
        # Explicit test/custom journals remain isolated beside their custom record file.
        if self._custom_journal_file:
            return os.path.join(os.path.dirname(self.journal_file), "trade_journal_events_v2.jsonl")
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
        return os.path.join(project_root, "runtime_logs", "trade_journal_events_v2.jsonl")

    @property
    def event_store_path(self) -> str:
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
        return os.path.join(project_root, "runtime_logs", "yartrader_events.sqlite3")

    def append_event(self, event: Dict[str, Any]) -> None:
        """Durably append one lifecycle event without rewriting prior evidence."""
        payload = dict(event)
        payload.setdefault("event", "journal_record_event")
        payload.setdefault("symbol", "UNKNOWN")
        payload.setdefault("strategy_style", "UNKNOWN")
        now = datetime.now(timezone.utc)
        payload.setdefault("timestamp_utc", now.isoformat())
        payload.setdefault("trade_type", "UNKNOWN")
        payload.setdefault("weekday_utc", now.strftime("%A"))
        payload.setdefault("day_of_month_utc", now.day)
        payload.setdefault("month_utc", now.month)
        payload.setdefault("year_utc", now.year)
        minute = now.hour * 60 + now.minute
        payload.setdefault("session_utc", (
            "ASIA" if minute < 420 else "LONDON" if minute < 720 else
            "NEW_YORK_OVERLAP" if minute < 960 else "NEW_YORK" if minute < 1260
            else "LATE_US_OR_ROLLOVER"
        ))
        if self._custom_journal_file:
            # Isolated tests and explicit custom journals keep their text fixture contract.
            os.makedirs(os.path.dirname(self.events_file), exist_ok=True)
            with open(self.events_file, "a", encoding="utf-8") as handle:
                handle.write(json.dumps(payload, ensure_ascii=False, default=str, sort_keys=True) + "\n")
                handle.flush()
                os.fsync(handle.fileno())
            return
        # Production lifecycle events have one canonical, deduplicated durable destination.
        SQLiteEventStore(self.event_store_path).append_event(payload, source="trade_journal")

    def save_journal(self) -> None:
        try:
            temp_path = self.journal_file + ".tmp"
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump([r.to_dict() for r in self.records], f, indent=2)
            os.replace(temp_path, self.journal_file)
        except Exception as e:
            logger.exception("[TradeJournalManager] Failed to save journal; caller must treat persistence as failed.")
            raise RuntimeError(f"Trade journal persistence failed: {self.journal_file}") from e

    def add_record(self, record: TradeJournalRecord) -> None:
        """Adds a trade record if not already present, maintaining immutability for closed trades."""
        existing_ids = {r.trade_id for r in self.records}
        if record.trade_id not in existing_ids:
            self.append_event({
                "event": "trade_record_created",
                "trade_type": record.trade_type,
                "trade_id": record.trade_id,
                "decision_id": record.decision_id,
                "symbol": record.symbol,
                "strategy_style": record.strategy_style,
                "record": record.to_dict(),
            })
            self.records.append(record)
            self.save_journal()

    def update_record(self, record: TradeJournalRecord) -> None:
        """Update the queryable snapshot while preserving the previous version in the event ledger."""
        for i, previous in enumerate(self.records):
            if previous.trade_id == record.trade_id:
                old_data = previous.to_dict()
                new_data = record.to_dict()
                changed_fields = sorted(
                    key for key in set(old_data) | set(new_data)
                    if old_data.get(key) != new_data.get(key)
                )
                self.append_event({
                    "event": "trade_record_updated",
                    "trade_type": record.trade_type,
                    "trade_id": record.trade_id,
                    "changed_fields": changed_fields,
                    "previous_record": old_data,
                    "updated_record": new_data,
                })
                self.records[i] = record
                self.save_journal()
                return
        self.add_record(record)

    def get_all_records(self) -> List[TradeJournalRecord]:
        return list(self.records)
