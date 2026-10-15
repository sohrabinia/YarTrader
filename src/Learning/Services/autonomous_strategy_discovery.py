"""Durable trade-lifecycle audit and evidence-gated strategy-style discovery.

Discovery is deliberately research-only: it can identify hypotheses from outcomes,
but cannot promote a discovered style to execution without out-of-sample validation.
"""
from __future__ import annotations
import json
import math
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping
from datetime import datetime, timezone


class AutonomousStrategyDiscovery:
    def __init__(self, root: Path | str):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.deals_path = self.root / "trade_lifecycle_audit.jsonl"
        self.positions_path = self.root / "open_position_snapshots.json"
        self.report_path = self.root / "autonomous_strategy_discovery.json"

    @staticmethod
    def _value(row: Any, key: str, default: Any = None) -> Any:
        try:
            return row[key]
        except (KeyError, TypeError, IndexError, ValueError):
            return getattr(row, key, default)

    @classmethod
    def _is_yartrader_entry(cls, deal: Any) -> bool:
        """Identify bot ownership from the opening deal, never from a close deal alone."""
        try:
            magic = int(cls._value(deal, "magic", 0) or 0)
        except (TypeError, ValueError, OverflowError):
            magic = 0
        comment = str(cls._value(deal, "comment", "") or "").strip().lower()
        return magic in {100001, 143056} or comment.startswith("yarbase") or "yartrader" in comment

    def _existing_deal_ids(self) -> set[str]:
        ids: set[str] = set()
        if not self.deals_path.exists():
            return ids
        try:
            with self.deals_path.open("r", encoding="utf-8") as stream:
                for line in stream:
                    try:
                        event = json.loads(line)
                        if event.get("deal_ticket") is not None:
                            ids.add(str(event["deal_ticket"]))
                    except (ValueError, TypeError):
                        continue
        except OSError:
            pass
        return ids

    def sync_history(self, deals: Iterable[Any], mt5: Any, symbol: str | None = None) -> Dict[str, Any]:
        """Append each unseen broker deal; broker deal tickets are idempotency keys."""
        existing = self._existing_deal_ids()
        entry_in = int(getattr(mt5, "DEAL_ENTRY_IN", 0))
        entry_out = int(getattr(mt5, "DEAL_ENTRY_OUT", 1))
        entry_out_by = int(getattr(mt5, "DEAL_ENTRY_OUT_BY", 3))
        rows = list(deals or [])
        # Recent history windows may contain a close without its opening deal.
        # Recover opening-deal ownership from the append-only audit before classifying
        # new closes; otherwise personal/manual trades can be learned as bot trades.
        entries: Dict[int, Any] = {}
        if self.deals_path.exists():
            try:
                with self.deals_path.open("r", encoding="utf-8") as stream:
                    for line in stream:
                        try:
                            event = json.loads(line)
                            if int(event.get("entry_kind", -1)) == entry_in:
                                position_id = int(event.get("position_id", 0) or 0)
                                if position_id > 0:
                                    entries[position_id] = event
                        except (ValueError, TypeError):
                            continue
            except OSError:
                pass
        for deal in rows:
            try:
                if int(self._value(deal, "entry", -1)) == entry_in:
                    entries[int(self._value(deal, "position_id", 0) or 0)] = deal
            except (TypeError, ValueError, OverflowError):
                continue
        added = 0
        self.deals_path.parent.mkdir(parents=True, exist_ok=True)
        for deal in sorted(rows, key=lambda d: int(self._value(d, "time_msc", 0) or 0)):
            try:
                ticket = int(self._value(deal, "ticket", 0) or 0)
                if ticket <= 0 or str(ticket) in existing:
                    continue
                deal_symbol = str(self._value(deal, "symbol", "")).upper()
                if symbol and deal_symbol != symbol.upper():
                    continue
                entry_kind = int(self._value(deal, "entry", -1))
                position_id = int(self._value(deal, "position_id", 0) or 0)
                entry_deal = entries.get(position_id)
                # Only the opening deal establishes ownership. Exit deals often have
                # magic=0 and an empty comment, so filtering each deal independently
                # would either lose bot exits or absorb unrelated manual trades.
                if not entry_deal or not self._is_yartrader_entry(entry_deal):
                    continue
                entry_comment = str(self._value(entry_deal, "comment", "") or "")
                entry_magic = int(self._value(entry_deal, "magic", 0) or 0)
                strategy = entry_comment.split(":", 1)[1].upper() if ":" in entry_comment else "BASE_HIERARCHY"
                pnl = sum(float(self._value(deal, k, 0.0) or 0.0) for k in ("profit", "commission", "swap", "fee"))
                if not math.isfinite(pnl):
                    continue
                event = {
                    "event": "BROKER_DEAL", "deal_ticket": ticket, "position_id": position_id,
                    "order_ticket": int(self._value(deal, "order", 0) or 0), "symbol": deal_symbol,
                    "strategy": strategy, "entry_kind": entry_kind,
                    "magic": int(self._value(deal, "magic", 0) or 0),
                    "entry_magic": entry_magic,
                    "entry_comment": entry_comment,
                    "is_close_deal": entry_kind in (entry_out, entry_out_by),
                    "entry_deal_ticket": int(self._value(entry_deal, "ticket", 0) or 0) if entry_deal else None,
                    "entry_price": float(self._value(entry_deal, "price", 0.0) or 0.0) if entry_deal else None,
                    "exit_price": float(self._value(deal, "price", 0.0) or 0.0),
                    "volume": float(self._value(deal, "volume", 0.0) or 0.0),
                    "profit": float(self._value(deal, "profit", 0.0) or 0.0),
                    "commission": float(self._value(deal, "commission", 0.0) or 0.0),
                    "swap": float(self._value(deal, "swap", 0.0) or 0.0),
                    "fee": float(self._value(deal, "fee", 0.0) or 0.0),
                    "net_pnl": pnl, "reason": int(self._value(deal, "reason", -1) or 0),
                    "time": int(self._value(deal, "time", 0) or 0),
                    "time_msc": int(self._value(deal, "time_msc", 0) or 0),
                    "comment": str(self._value(deal, "comment", "") or ""),
                    "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
                }
                with self.deals_path.open("a", encoding="utf-8") as stream:
                    stream.write(json.dumps(event, ensure_ascii=False, default=str) + "\n")
                existing.add(str(ticket)); added += 1
            except (TypeError, ValueError, OverflowError, OSError):
                continue
        return {"new_deals_recorded": added, "total_seen": len(existing), "path": str(self.deals_path)}

    def snapshot_positions(self, positions: Iterable[Any], now_utc: str | None = None) -> None:
        """Atomically retain the latest broker-authoritative open-position state."""
        snapshots = []
        for p in positions or []:
            try:
                comment = str(self._value(p, "comment", "") or "")
                snapshots.append({
                    "ticket": int(self._value(p, "ticket", 0) or 0),
                    "position_id": int(self._value(p, "identifier", self._value(p, "ticket", 0)) or 0),
                    "symbol": str(self._value(p, "symbol", "")).upper(),
                    "strategy": comment.split(":", 1)[1].upper() if ":" in comment else "BASE_HIERARCHY",
                    "comment": comment, "magic": int(self._value(p, "magic", 0) or 0),
                    "direction_type": int(self._value(p, "type", -1)),
                    "volume": float(self._value(p, "volume", 0.0) or 0.0),
                    "entry_price": float(self._value(p, "price_open", 0.0) or 0.0),
                    "current_price": float(self._value(p, "price_current", 0.0) or 0.0),
                    "stop_loss": float(self._value(p, "sl", 0.0) or 0.0),
                    "take_profit": float(self._value(p, "tp", 0.0) or 0.0),
                    "profit": float(self._value(p, "profit", 0.0) or 0.0),
                    "opened_at": int(self._value(p, "time", 0) or 0),
                })
            except (TypeError, ValueError, OverflowError):
                continue
        payload = {"updated_at_utc": now_utc or datetime.now(timezone.utc).isoformat(),
                   "open_positions_count": len(snapshots), "positions": snapshots}
        temp = self.positions_path.with_suffix(".json.tmp")
        temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        temp.replace(self.positions_path)

    def build_discovery_report(self) -> Dict[str, Any]:
        """Mine position-level cohorts; partial close deals are never counted as trades."""
        events: List[Dict[str, Any]] = []
        if self.deals_path.exists():
            try:
                with self.deals_path.open("r", encoding="utf-8") as stream:
                    events = [json.loads(line) for line in stream if line.strip()]
            except (OSError, ValueError):
                events = []
        # Rebuild ownership from opening deals so legacy reports containing manual
        # account trades are filtered too; do not trust a close deal's blank comment.
        entry_by_position: Dict[tuple[str, int], Dict[str, Any]] = {}
        for event in events:
            try:
                if int(event.get("entry_kind", -1)) == 0:
                    key = (str(event.get("symbol", "UNKNOWN")).upper(),
                           int(event.get("position_id", 0) or 0))
                    if key[1] > 0:
                        entry_by_position[key] = event
            except (TypeError, ValueError, OverflowError):
                continue
        closed_deals = []
        for event in events:
            if not (event.get("is_close_deal")
                    and isinstance(event.get("net_pnl"), (int, float))):
                continue
            try:
                key = (str(event.get("symbol", "UNKNOWN")).upper(),
                       int(event.get("position_id", 0) or 0))
            except (TypeError, ValueError, OverflowError):
                continue
            opening = entry_by_position.get(key)
            if not opening or not self._is_yartrader_entry(opening):
                continue
            # Use the strategy captured on the opening deal, not a close deal's
            # fallback label, which may have been written before ownership filtering.
            event = dict(event)
            event["strategy"] = opening.get("strategy") or (
                str(opening.get("comment", "")).split(":", 1)[1].upper()
                if ":" in str(opening.get("comment", "")) else "BASE_HIERARCHY"
            )
            closed_deals.append(event)
        by_position: Dict[str, List[Dict[str, Any]]] = {}
        for event in closed_deals:
            key = f"{event.get('symbol','UNKNOWN')}|{event.get('strategy','UNKNOWN')}|{event.get('position_id',0)}"
            by_position.setdefault(key, []).append(event)
        positions: Dict[str, List[Dict[str, Any]]] = {}
        for key, rows in by_position.items():
            first = min(rows, key=lambda e: int(e.get("time_msc", 0) or 0))
            net = sum(float(e.get("net_pnl", 0.0) or 0.0) for e in rows)
            trade = {"symbol": first.get("symbol", "UNKNOWN"),
                     "strategy": first.get("strategy", "UNKNOWN"),
                     "position_id": first.get("position_id", 0),
                     "net_pnl": net, "close_deal_count": len(rows),
                     "last_close_time": max(int(e.get("time_msc", 0) or 0) for e in rows)}
            positions.setdefault(f"{trade['symbol']}|{trade['strategy']}", []).append(trade)
        cohorts = []
        for key, trades in sorted(positions.items()):
            pnls = [float(t["net_pnl"]) for t in trades]
            wins = [v for v in pnls if v > 0]
            losses = [v for v in pnls if v < 0]
            gross_profit, gross_loss = sum(wins), abs(sum(losses))
            expectancy = sum(pnls)/len(pnls) if pnls else 0.0
            pf = gross_profit/gross_loss if gross_loss > 0 else (float("inf") if gross_profit > 0 else 0.0)
            status = "INSUFFICIENT_SAMPLE_RESEARCH_ONLY"
            if len(pnls) >= 30 and expectancy > 0 and pf >= 1.15:
                status = "PROMISING_HYPOTHESIS_REQUIRES_WALK_FORWARD"
            cohorts.append({"cohort": key, "closed_position_count": len(pnls),
                            "closed_deal_count": sum(t["close_deal_count"] for t in trades),
                            "win_rate": round(len(wins)/len(pnls), 4) if pnls else 0.0,
                            "net_expectancy_per_position": round(expectancy, 6),
                            "profit_factor": round(pf, 4) if math.isfinite(pf) else None,
                            "status": status, "activation_allowed": False,
                            "note": "Statistics aggregate partial closes by broker position_id; promotion still requires walk-forward/out-of-sample validation and paper trading."})
        report = {"generated_at_utc": datetime.now(timezone.utc).isoformat(),
                  "closed_deal_records": len(closed_deals),
                  "closed_position_count": len(by_position), "cohorts": cohorts,
                  "discovery_policy": "Compare strategy outcomes by symbol and strategy on position-level net PnL; require walk-forward/out-of-sample validation and paper trading before promotion.",
                  "auto_promotion_enabled": False}
        temp = self.report_path.with_suffix(".json.tmp")
        temp.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
        temp.replace(self.report_path)
        return report
