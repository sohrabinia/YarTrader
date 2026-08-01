import os
import json
import uuid
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

logger = logging.getLogger("PredictiveShadowEngine")

class ShadowTrade:
    """
    Represents a virtual predictive shadow order and its position lifecycle.
    """
    def __init__(
        self,
        symbol: str,
        direction: str,  # LONG or SHORT
        entry: float,
        stop: float,
        target: float,
        confidence: float,
        reason: str = "",
        custom_time_structure: int = 64,
        base_id: Optional[str] = None,
        node_id: Optional[str] = None,
        pattern: str = "Base Expansion Continuation",
        trade_id: Optional[str] = None,
        volume: float = 1.0
    ) -> None:
        self.trade_id = trade_id or f"strade-{uuid.uuid4().hex[:6]}"
        self.symbol = symbol
        self.direction = direction.upper()  # LONG or SHORT
        self.entry = float(entry)
        self.stop = float(stop)
        self.target = float(target)
        self.confidence = float(confidence)
        self.reason = reason
        self.custom_time_structure = int(custom_time_structure)
        self.base_id = base_id or "B-None"
        self.node_id = node_id or "N-None"
        self.pattern = pattern
        self.volume = float(volume)

        # Performance/Excursion metrics
        self.floating_pnl = 0.0
        self.mae = 0.0  # Max Adverse Excursion
        self.mfe = 0.0  # Max Favorable Excursion
        self.exit_reason = ""
        self.result = "PENDING"  # TARGET_HIT, STOP_HIT, TIMEOUT, INVALIDATED
        self.status = "CREATED"  # CREATED, RUNNING, TARGET_HIT, STOP_HIT, TIMEOUT, INVALIDATED

        self.creation_time = datetime.now()
        self.decision_time = datetime.now()
        self.activation_time: Optional[datetime] = None
        self.close_time: Optional[datetime] = None

    def update_price_tick(self, current_price: float) -> None:
        """
        Processes a raw tick update and transitions the position lifecycle.
        """
        # 1. Trigger pending order if price hits entry
        if self.status == "CREATED":
            triggered = False
            if self.direction == "LONG":
                # Entry trigger condition: price touches or crosses entry from below
                if current_price >= self.entry:
                    triggered = True
            else: # SHORT
                if current_price <= self.entry:
                    triggered = True

            if triggered:
                self.status = "RUNNING"
                self.activation_time = datetime.now()
                logger.info(f"Predictive shadow order triggered: {self.trade_id} @ {self.entry}")

        # 2. If running, evaluate floating profit, MAE, MFE, and TP/SL breaches
        if self.status == "RUNNING":
            # standard PnL multiplier representation
            multiplier = 100.0 if "XAU" in self.symbol else 10000.0

            if self.direction == "LONG":
                pnl = (current_price - self.entry) * multiplier * self.volume
            else:
                pnl = (self.entry - current_price) * multiplier * self.volume

            self.floating_pnl = round(pnl, 2)

            # Update MAE (minimum P/L seen, so max negative displacement)
            if self.floating_pnl < self.mae:
                self.mae = self.floating_pnl

            # Update MFE (maximum P/L seen, so max positive displacement)
            if self.floating_pnl > self.mfe:
                self.mfe = self.floating_pnl

            # Check Stop Loss / Take Profit
            if self.direction == "LONG":
                if current_price >= self.target:
                    self.status = "TARGET_HIT"
                    self.result = "TARGET_HIT"
                    self.exit_reason = "Take Profit Hit"
                    self.close_time = datetime.now()
                elif current_price <= self.stop:
                    self.status = "STOP_HIT"
                    self.result = "STOP_HIT"
                    self.exit_reason = "Stop Loss Hit"
                    self.close_time = datetime.now()
            else: # SHORT
                if current_price <= self.target:
                    self.status = "TARGET_HIT"
                    self.result = "TARGET_HIT"
                    self.exit_reason = "Take Profit Hit"
                    self.close_time = datetime.now()
                elif current_price >= self.stop:
                    self.status = "STOP_HIT"
                    self.result = "STOP_HIT"
                    self.exit_reason = "Stop Loss Hit"
                    self.close_time = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trade_id": self.trade_id,
            "symbol": self.symbol,
            "direction": self.direction,
            "entry": self.entry,
            "stop": self.stop,
            "target": self.target,
            "confidence": self.confidence,
            "reason": self.reason,
            "custom_time_structure": self.custom_time_structure,
            "base_id": self.base_id,
            "node_id": self.node_id,
            "pattern": self.pattern,
            "volume": self.volume,
            "floating_pnl": self.floating_pnl,
            "mae": self.mae,
            "mfe": self.mfe,
            "exit_reason": self.exit_reason,
            "result": self.result,
            "status": self.status,
            "creation_time": self.creation_time.isoformat() if isinstance(self.creation_time, datetime) else str(self.creation_time),
            "decision_time": self.decision_time.isoformat() if isinstance(self.decision_time, datetime) else str(self.decision_time),
            "activation_time": self.activation_time.isoformat() if self.activation_time else None,
            "close_time": self.close_time.isoformat() if self.close_time else None
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ShadowTrade":
        st = cls(
            symbol=d["symbol"],
            direction=d["direction"],
            entry=d["entry"],
            stop=d["stop"],
            target=d["target"],
            confidence=d["confidence"],
            reason=d.get("reason", ""),
            custom_time_structure=d.get("custom_time_structure", 64),
            base_id=d.get("base_id"),
            node_id=d.get("node_id"),
            pattern=d.get("pattern", "Base Expansion Continuation"),
            trade_id=d["trade_id"],
            volume=d.get("volume", 1.0)
        )
        st.floating_pnl = d.get("floating_pnl", 0.0)
        st.mae = d.get("mae", 0.0)
        st.mfe = d.get("mfe", 0.0)
        st.exit_reason = d.get("exit_reason", "")
        st.result = d.get("result", "PENDING")
        st.status = d.get("status", "CREATED")
        if d.get("creation_time"):
            st.creation_time = datetime.fromisoformat(d["creation_time"])
        if d.get("decision_time"):
            st.decision_time = datetime.fromisoformat(d["decision_time"])
        if d.get("activation_time"):
            st.activation_time = datetime.fromisoformat(d["activation_time"])
        if d.get("close_time"):
            st.close_time = datetime.fromisoformat(d["close_time"])
        return st


class PredictiveShadowEngine:
    """
    Main orchestrator for managing predictive virtual order placement, lifecycles,
    and history database persistence (never deleting data).
    """
    _instance: Optional["PredictiveShadowEngine"] = None

    @classmethod
    def get_instance(cls) -> "PredictiveShadowEngine":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        self.trades_file = "runtime_logs/shadow_trades.json"
        self.bases_file = "runtime_logs/base_memory.json"
        self.nodes_file = "runtime_logs/node_memory.json"
        self.patterns_file = "runtime_logs/pattern_outcomes.json"
        self.learning_file = "runtime_logs/learning_history.json"
        self.signals_file = "runtime_logs/signal_history.json"

        # Ensure directories exist
        os.makedirs("runtime_logs", exist_ok=True)

        # Load existing datasets or initialize empty ones
        self.trades: List[ShadowTrade] = self._load_trades()
        self.bases: List[Dict[str, Any]] = self._load_generic(self.bases_file)
        self.nodes: List[Dict[str, Any]] = self._load_generic(self.nodes_file)
        self.patterns: List[Dict[str, Any]] = self._load_generic(self.patterns_file)
        self.learning: List[Dict[str, Any]] = self._load_generic(self.learning_file)
        self.signals: List[Dict[str, Any]] = self._load_generic(self.signals_file)

    def create_predictive_order(
        self,
        symbol: str,
        direction: str,
        entry: float,
        stop: float,
        target: float,
        confidence: float,
        reason: str = "",
        custom_time_structure: int = 64,
        base_id: Optional[str] = None,
        node_id: Optional[str] = None,
        pattern: str = "Base Expansion Continuation"
    ) -> ShadowTrade:
        """
        Registers a predictive shadow order before price actually triggers it.
        """
        trade = ShadowTrade(
            symbol=symbol,
            direction=direction,
            entry=entry,
            stop=stop,
            target=target,
            confidence=confidence,
            reason=reason,
            custom_time_structure=custom_time_structure,
            base_id=base_id,
            node_id=node_id,
            pattern=pattern
        )
        self.trades.append(trade)
        self._save_trades()

        # Whenever a shadow trade is created, map it to a clean user signal
        self.generate_user_signal(trade)
        return trade

    def update_market_ticks(self, symbol: str, current_price: float) -> List[ShadowTrade]:
        """
        Updates floating P/L, handles SL/TP breaches, and runs post-trade memory learning triggers.
        """
        closed_trades = []
        for trade in self.trades:
            if trade.symbol == symbol and trade.status in ["CREATED", "RUNNING"]:
                old_status = trade.status
                trade.update_price_tick(current_price)
                if trade.status in ["TARGET_HIT", "STOP_HIT", "TIMEOUT", "INVALIDATED"]:
                    closed_trades.append(trade)
                    # Trigger memory learning and outcome recording
                    self._record_pattern_outcome(trade)
                    self._update_learning_history(trade)
                    # Synchronize clean user signals
                    self._sync_user_signal(trade)

        if closed_trades:
            self._save_trades()
        return closed_trades

    def generate_user_signal(self, trade: ShadowTrade) -> Dict[str, Any]:
        """
        Converts a ShadowTrade into a clean user signal (hiding internal calculations).
        """
        sig = {
            "signal_id": f"sig-{trade.trade_id[7:] if trade.trade_id.startswith('strade-') else trade.trade_id}",
            "shadow_trade_id": trade.trade_id,
            "symbol": trade.symbol,
            "direction": trade.direction,
            "entry_zone": trade.entry,
            "invalidation_level": trade.stop,
            "target_zone": trade.target,
            "confidence": trade.confidence,
            "reason": trade.reason or "Market Structure Expansion",
            "status": "ACTIVE" if trade.status in ["CREATED", "RUNNING"] else trade.status,
            "timestamp": datetime.now().isoformat()
        }
        self.signals.append(sig)
        self._save_generic(self.signals_file, self.signals)
        return sig

    def get_clean_signals(self) -> List[Dict[str, Any]]:
        """Returns clean user signals only."""
        return self.signals

    def add_base(self, base: Dict[str, Any]) -> None:
        self.bases.append(base)
        self._save_generic(self.bases_file, self.bases)

    def add_node(self, node: Dict[str, Any]) -> None:
        self.nodes.append(node)
        self._save_generic(self.nodes_file, self.nodes)

    def _sync_user_signal(self, trade: ShadowTrade) -> None:
        """Updates user signal status on shadow close."""
        for sig in self.signals:
            if sig.get("shadow_trade_id") == trade.trade_id:
                sig["status"] = trade.status
        self._save_generic(self.signals_file, self.signals)

    def _record_pattern_outcome(self, trade: ShadowTrade) -> None:
        """Updates pattern statistics on disk."""
        outcome = {
            "trade_id": trade.trade_id,
            "pattern": trade.pattern,
            "result": trade.status,
            "mae": trade.mae,
            "mfe": trade.mfe,
            "timestamp": datetime.now().isoformat()
        }
        self.patterns.append(outcome)
        self._save_generic(self.patterns_file, self.patterns)

    def _update_learning_history(self, trade: ShadowTrade) -> None:
        """Logs a cognitive update reflecting how the judge/brain is updated from this trade."""
        record = {
            "update_id": f"learn-{uuid.uuid4().hex[:6]}",
            "trade_id": trade.trade_id,
            "pattern": trade.pattern,
            "success": trade.status == "TARGET_HIT",
            "confidence_shift": -0.05 if trade.status == "STOP_HIT" else 0.05,
            "timestamp": datetime.now().isoformat()
        }
        self.learning.append(record)
        self._save_generic(self.learning_file, self.learning)

    # File storage helpers
    def _load_trades(self) -> List[ShadowTrade]:
        if not os.path.exists(self.trades_file):
            return []
        try:
            with open(self.trades_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return [ShadowTrade.from_dict(d) for d in data]
        except Exception:
            return []

    def _save_trades(self) -> None:
        with open(self.trades_file, "w", encoding="utf-8") as f:
            json.dump([t.to_dict() for t in self.trades], f, indent=4)

    def _load_generic(self, filepath: str) -> List[Dict[str, Any]]:
        if not os.path.exists(filepath):
            return []
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def _save_generic(self, filepath: str, data: List[Dict[str, Any]]) -> None:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
