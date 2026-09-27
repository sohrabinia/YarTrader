import os
import json
import threading
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict

JOURNAL_DIR = "runtime_logs/trade_journal"

@dataclass
class TradeJournalRecord:
    trade_id: str
    decision_id: str
    timestamp: str
    symbol: str
    timeframe: str
    direction: str
    strategy_id: str
    strategy_version: str
    entry_price: float
    requested_price: float
    actual_fill_price: float
    volume_lots: float
    account_balance: float
    account_equity: float
    risk_pct: float
    risk_budget_usd: float
    stop_loss: float
    take_profit: float
    risk_reward: float
    confidence: float
    decision_reason: str
    supporting_evidence: Dict[str, Any]
    research_snapshot_id: str
    broker_order_ticket: str
    broker_deal_ticket: str
    # Exit fields
    exit_timestamp: Optional[str] = None
    exit_price: Optional[float] = None
    realized_pnl: Optional[float] = None
    realized_pnl_pct: Optional[float] = None
    exit_reason: Optional[str] = None # TAKE_PROFIT, STOP_LOSS, REVERSAL, RISK_GUARD, DAILY_LOSS_GUARD, EOD_FLATTEN, MANUAL, BROKER_FORCED, EXECUTION_FAILURE, UNKNOWN
    closing_deal_ticket: Optional[str] = None
    duration_seconds: Optional[float] = None
    max_favorable_excursion: Optional[float] = None
    max_adverse_excursion: Optional[float] = None
    slippage: Optional[float] = None
    result_classification: Optional[str] = None # WIN, LOSS, BREAKEVEN
    post_trade_analysis: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class TradeJournalManager:
    """
    Manages structured, persistent, and auditable trade journal records.
    Every trade records why it was entered, the full market/structure context,
    fill details, exit reasons, realized P/L, and post-trade self-analysis.
    """
    _instance = None
    _lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> "TradeJournalManager":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def __init__(self, log_dir: Optional[str] = None) -> None:
        from src.Application.Deployment.storage import YarTraderStorageManager
        storage_mgr = YarTraderStorageManager.get_manager()
        self.log_dir = log_dir or os.path.join(storage_mgr.get_runtime_dir(), "trade_journal")
        os.makedirs(self.log_dir, exist_ok=True)
        self._journal_lock = threading.RLock()

    def record_entry(
        self,
        trade_id: str,
        decision_id: str,
        symbol: str,
        timeframe: str,
        direction: str,
        strategy_id: str,
        strategy_version: str,
        entry_price: float,
        requested_price: float,
        actual_fill_price: float,
        volume_lots: float,
        account_balance: float,
        account_equity: float,
        risk_pct: float,
        risk_budget_usd: float,
        stop_loss: float,
        take_profit: float,
        risk_reward: float,
        confidence: float,
        decision_reason: str,
        supporting_evidence: Dict[str, Any],
        research_snapshot_id: str,
        broker_order_ticket: str,
        broker_deal_ticket: str
    ) -> TradeJournalRecord:
        record = TradeJournalRecord(
            trade_id=trade_id,
            decision_id=decision_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            symbol=symbol.upper(),
            timeframe=timeframe.upper(),
            direction=direction.upper(),
            strategy_id=strategy_id,
            strategy_version=strategy_version,
            entry_price=entry_price,
            requested_price=requested_price,
            actual_fill_price=actual_fill_price,
            volume_lots=volume_lots,
            account_balance=account_balance,
            account_equity=account_equity,
            risk_pct=risk_pct,
            risk_budget_usd=risk_budget_usd,
            stop_loss=stop_loss,
            take_profit=take_profit,
            risk_reward=risk_reward,
            confidence=confidence,
            decision_reason=decision_reason,
            supporting_evidence=supporting_evidence,
            research_snapshot_id=research_snapshot_id,
            broker_order_ticket=broker_order_ticket,
            broker_deal_ticket=broker_deal_ticket
        )
        self._save_record(record)
        return record

    def record_exit(
        self,
        trade_id: str,
        exit_price: float,
        realized_pnl: float,
        exit_reason: str,
        closing_deal_ticket: str,
        duration_seconds: float,
        max_favorable_excursion: Optional[float] = None,
        max_adverse_excursion: Optional[float] = None
    ) -> Optional[TradeJournalRecord]:
        with self._journal_lock:
            record = self.get_trade(trade_id)
            if not record:
                return None

            valid_exit_reasons = {
                "TAKE_PROFIT", "STOP_LOSS", "REVERSAL", "RISK_GUARD",
                "DAILY_LOSS_GUARD", "EOD_FLATTEN", "MANUAL", "BROKER_FORCED",
                "EXECUTION_FAILURE", "UNKNOWN"
            }
            clean_exit_reason = exit_reason.upper() if exit_reason.upper() in valid_exit_reasons else "UNKNOWN"

            record.exit_timestamp = datetime.now(timezone.utc).isoformat()
            record.exit_price = exit_price
            record.realized_pnl = realized_pnl
            record.realized_pnl_pct = (realized_pnl / record.account_balance) * 100.0 if record.account_balance > 0 else 0.0
            record.exit_reason = clean_exit_reason
            record.closing_deal_ticket = closing_deal_ticket
            record.duration_seconds = duration_seconds
            record.max_favorable_excursion = max_favorable_excursion
            record.max_adverse_excursion = max_adverse_excursion
            record.slippage = abs(record.actual_fill_price - record.requested_price) if record.requested_price > 0 else 0.0

            if realized_pnl > 0.01:
                record.result_classification = "WIN"
            elif realized_pnl < -0.01:
                record.result_classification = "LOSS"
            else:
                record.result_classification = "BREAKEVEN"

            # Post-trade deterministic self-analysis
            record.post_trade_analysis = self._generate_post_trade_analysis(record)

            self._save_record(record)
            return record

    def _generate_post_trade_analysis(self, record: TradeJournalRecord) -> Dict[str, Any]:
        """Generates deterministic post-trade analysis explaining entry, exit, win/loss causality."""
        why_entered = f"Entered {record.direction} on {record.symbol} {record.timeframe} based on strategy {record.strategy_id} v{record.strategy_version}. Rationale: {record.decision_reason}"
        why_exited = f"Exited via {record.exit_reason} at price {record.exit_price}. Realized P/L: ${record.realized_pnl:.2f} ({record.realized_pnl_pct:.2f}%)."

        if record.result_classification == "WIN":
            causality = "TRADE_SUCCESS: Market moved in anticipated direction and reached exit target without hitting stop loss."
        elif record.result_classification == "LOSS":
            if record.exit_reason == "STOP_LOSS":
                causality = "STOP_LOSS_HIT: Market invalidated direction and reached stop loss level."
            elif record.exit_reason == "REVERSAL":
                causality = "REVERSAL_EXIT: Market structure flipped opposite to position prior to target reaching."
            elif record.exit_reason == "RISK_GUARD":
                causality = "RISK_GUARD_EXIT: Position closed early due to risk guard or drawdown limit."
            else:
                causality = f"TRADE_LOSS: Exited with negative P/L via {record.exit_reason}."
        else:
            causality = "BREAKEVEN_EXIT: Position exited with zero or minimal net gain/loss."

        return {
            "why_entered": why_entered,
            "why_exited": why_exited,
            "result_classification": record.result_classification,
            "causality_analysis": causality,
            "slippage_usd": record.slippage,
            "planned_rr": record.risk_reward,
            "realized_rr": round(record.realized_pnl / record.risk_budget_usd, 2) if record.risk_budget_usd > 0 else 0.0,
            "evidence_quality": "HIGH_CONFIDENCE" if record.supporting_evidence else "INSUFFICIENT_EVIDENCE"
        }

    def _save_record(self, record: TradeJournalRecord) -> None:
        filepath = os.path.join(self.log_dir, f"trade_{record.trade_id}.json")
        temp_filepath = filepath + ".tmp"
        with open(temp_filepath, "w", encoding="utf-8") as f:
            json.dump(record.to_dict(), f, indent=4)
        os.replace(temp_filepath, filepath)

    def get_trade(self, trade_id: str) -> Optional[TradeJournalRecord]:
        filepath = os.path.join(self.log_dir, f"trade_{trade_id}.json")
        if not os.path.exists(filepath):
            return None
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            return TradeJournalRecord(**data)
        except Exception:
            return None

    def get_all_trades(self) -> List[TradeJournalRecord]:
        trades = []
        if not os.path.exists(self.log_dir):
            return trades
        for fname in os.listdir(self.log_dir):
            if fname.startswith("trade_") and fname.endswith(".json") and not fname.endswith(".tmp"):
                trade_id = fname.replace("trade_", "").replace(".json", "")
                t = self.get_trade(trade_id)
                if t:
                    trades.append(t)
        return sorted(trades, key=lambda x: x.timestamp)
