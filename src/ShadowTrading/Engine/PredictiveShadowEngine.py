import os
import json
import uuid
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from src.ShadowTrading.Engine.SymbolTimeContext import SymbolTimeContext

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
        self.symbol = symbol.upper()
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
        if self.status == "CREATED":
            triggered = False
            if self.direction == "LONG":
                if current_price >= self.entry:
                    triggered = True
            else: # SHORT
                if current_price <= self.entry:
                    triggered = True

            if triggered:
                self.status = "RUNNING"
                self.activation_time = datetime.now()
                logger.info(f"Predictive shadow order triggered: {self.trade_id} @ {self.entry}")

        if self.status == "RUNNING":
            multiplier = 100.0 if "XAU" in self.symbol else 10000.0

            if self.direction == "LONG":
                pnl = (current_price - self.entry) * multiplier * self.volume
            else:
                pnl = (self.entry - current_price) * multiplier * self.volume

            self.floating_pnl = round(pnl, 2)

            if self.floating_pnl < self.mae:
                self.mae = self.floating_pnl
            if self.floating_pnl > self.mfe:
                self.mfe = self.floating_pnl

            # Check SL/TP
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
    Overhauled main orchestrator for TradeYar AI v3.3.
    Manages multi-asset and multi-resolution isolated contexts.
    Enforces standard limit of max 30 concurrent symbols.
    """
    _instance: Optional["PredictiveShadowEngine"] = None

    @classmethod
    def get_instance(cls) -> "PredictiveShadowEngine":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        self.max_symbols_limit = 30
        self._load_limits_config()

        # Database File Paths (Consolidated memory indices)
        self.trades_file = "runtime_logs/shadow_trades.json"
        self.bases_file = "runtime_logs/base_memory.json"
        self.nodes_file = "runtime_logs/node_memory.json"
        self.patterns_file = "runtime_logs/pattern_outcomes.json"
        self.learning_file = "runtime_logs/learning_history.json"
        self.signals_file = "runtime_logs/signal_history.json"

        os.makedirs("runtime_logs", exist_ok=True)

        # Isolated Context Map: context_id (e.g. BTCUSD_256) -> SymbolTimeContext
        self.contexts: Dict[str, SymbolTimeContext] = {}

        # Core lists for serialization / global fallback queries
        self.trades: List[ShadowTrade] = self._load_trades()
        self.bases: List[Dict[str, Any]] = self._load_generic(self.bases_file)
        self.nodes: List[Dict[str, Any]] = self._load_generic(self.nodes_file)
        self.patterns: List[Dict[str, Any]] = self._load_generic(self.patterns_file)
        self.learning: List[Dict[str, Any]] = self._load_generic(self.learning_file)
        self.signals: List[Dict[str, Any]] = self._load_generic(self.signals_file)

        # Initialize existing records into corresponding contexts
        self._hydrate_contexts()

    def _load_limits_config(self) -> None:
        yaml_path = "config/system_limits.yaml"
        if os.path.exists(yaml_path):
            try:
                import yaml
                with open(yaml_path, "r", encoding="utf-8") as f:
                    limits = yaml.safe_load(f)
                    self.max_symbols_limit = limits.get("system_limits", {}).get("max_active_symbols", 30)
            except Exception:
                self.max_symbols_limit = 30

    def _get_or_create_context_bypassing_limits(self, symbol: str, timeframe: int) -> SymbolTimeContext:
        """Retrieves or creates context without SRE limits verification (used on startup hydration)."""
        symbol_upper = symbol.upper()
        tf_int = int(timeframe)
        context_id = f"{symbol_upper}_{tf_int}"

        if context_id in self.contexts:
            return self.contexts[context_id]

        ctx = SymbolTimeContext(symbol_upper, tf_int)
        self.contexts[context_id] = ctx
        return ctx

    def _hydrate_contexts(self) -> None:
        """Hydrates isolated contexts from loaded persistent data, bypassing limits checks."""
        # 1. Hydrate Trades
        for trade in self.trades:
            ctx = self._get_or_create_context_bypassing_limits(trade.symbol, trade.custom_time_structure)
            ctx.trades.append(trade)

        # 2. Hydrate Bases
        for base in self.bases:
            ctx = self._get_or_create_context_bypassing_limits(base["symbol"], base.get("timeframe", 64))
            ctx.bases.append(base)

        # 3. Hydrate Nodes
        for node in self.nodes:
            ctx = self._get_or_create_context_bypassing_limits(node.get("symbol", "XAUUSD"), node.get("timeframe", 64))
            ctx.nodes.append(node)

        # 4. Hydrate Patterns
        for pat in self.patterns:
            symbol = pat.get("symbol", "XAUUSD")
            tf = pat.get("timeframe", 64)
            ctx = self._get_or_create_context_bypassing_limits(symbol, tf)
            ctx.patterns.append(pat)

        # 5. Hydrate Learning histories
        for learn in self.learning:
            symbol = learn.get("symbol", "XAUUSD")
            tf = learn.get("timeframe", 64)
            ctx = self._get_or_create_context_bypassing_limits(symbol, tf)
            ctx.learning.append(learn)

    def get_or_create_context(self, symbol: str, timeframe: int) -> SymbolTimeContext:
        """
        Retrieves or instantiates an isolated SymbolTimeContext.
        Enforces maximum active symbols operational limits during active runs.
        """
        symbol_upper = symbol.upper()
        tf_int = int(timeframe)
        context_id = f"{symbol_upper}_{tf_int}"

        if context_id in self.contexts:
            return self.contexts[context_id]

        # Limit Check: Count unique active symbols across registered contexts
        active_symbols = set(ctx.symbol for ctx in self.contexts.values())
        if len(active_symbols) >= self.max_symbols_limit and symbol_upper not in active_symbols:
            raise ValueError(f"Hard SRE limit reached: Maximum {self.max_symbols_limit} active symbols allowed concurrent execution.")

        ctx = SymbolTimeContext(symbol_upper, tf_int)
        self.contexts[context_id] = ctx
        return ctx

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
        Registers a predictive shadow order in its isolated SymbolTimeContext.
        """
        # Resolve Context & check limits
        ctx = self.get_or_create_context(symbol, custom_time_structure)

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

        ctx.trades.append(trade)
        self.trades.append(trade)
        self._save_trades()

        # Build sanitized user signal from the newly created ShadowTrade
        self.generate_user_signal(trade)
        return trade

    def update_market_ticks(self, symbol: str, current_price: float) -> List[ShadowTrade]:
        """
        Updates floating state, SL/TP triggers across contexts of a specific symbol.
        """
        closed_trades = []
        symbol_upper = symbol.upper()

        # Iterate all contexts of this symbol
        matching_contexts = [ctx for ctx in self.contexts.values() if ctx.symbol == symbol_upper]
        for ctx in matching_contexts:
            # Append current tick
            ctx.tick_buffer.append({"price": current_price, "timestamp": datetime.now().isoformat()})
            if len(ctx.tick_buffer) > 5000:
                ctx.tick_buffer.pop(0)

            # Update trades in context
            for trade in ctx.trades:
                if trade.status in ["CREATED", "RUNNING"]:
                    trade.update_price_tick(current_price)
                    if trade.status in ["TARGET_HIT", "STOP_HIT", "TIMEOUT", "INVALIDATED"]:
                        closed_trades.append(trade)
                        self._record_pattern_outcome_context(ctx, trade)
                        self._update_learning_history_context(ctx, trade)
                        self._sync_user_signal(trade)

        if closed_trades:
            self._save_trades()
        return closed_trades

    def generate_user_signal(self, trade: ShadowTrade) -> Dict[str, Any]:
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
        return self.signals

    def add_base(self, symbol: str, timeframe: int, base: Dict[str, Any]) -> None:
        ctx = self.get_or_create_context(symbol, timeframe)
        base["symbol"] = symbol
        base["timeframe"] = timeframe
        ctx.bases.append(base)
        self.bases.append(base)
        self._save_generic(self.bases_file, self.bases)

    def add_node(self, symbol: str, timeframe: int, node: Dict[str, Any]) -> None:
        ctx = self.get_or_create_context(symbol, timeframe)
        node["symbol"] = symbol
        node["timeframe"] = timeframe
        ctx.nodes.append(node)
        self.nodes.append(node)
        self._save_generic(self.nodes_file, self.nodes)

    def _sync_user_signal(self, trade: ShadowTrade) -> None:
        for sig in self.signals:
            if sig.get("shadow_trade_id") == trade.trade_id:
                sig["status"] = trade.status
        self._save_generic(self.signals_file, self.signals)

    def _record_pattern_outcome_context(self, ctx: SymbolTimeContext, trade: ShadowTrade) -> None:
        outcome = {
            "trade_id": trade.trade_id,
            "symbol": trade.symbol,
            "timeframe": trade.custom_time_structure,
            "pattern": trade.pattern,
            "result": trade.status,
            "mae": trade.mae,
            "mfe": trade.mfe,
            "timestamp": datetime.now().isoformat()
        }
        ctx.patterns.append(outcome)
        self.patterns.append(outcome)
        self._save_generic(self.patterns_file, self.patterns)

    def _update_learning_history_context(self, ctx: SymbolTimeContext, trade: ShadowTrade) -> None:
        record = {
            "update_id": f"learn-{uuid.uuid4().hex[:6]}",
            "trade_id": trade.trade_id,
            "symbol": trade.symbol,
            "timeframe": trade.custom_time_structure,
            "pattern": trade.pattern,
            "success": trade.status == "TARGET_HIT",
            "confidence_shift": -0.05 if trade.status == "STOP_HIT" else 0.05,
            "timestamp": datetime.now().isoformat()
        }
        ctx.learning.append(record)
        self.learning.append(record)
        self._save_generic(self.learning_file, self.learning)

    # Persistence Load & Saves
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
