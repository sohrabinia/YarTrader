import os
import json
import uuid
import queue
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from src.ShadowTrading.Engine.SymbolTimeContext import SymbolTimeContext
from src.ShadowTrading.Engine.SymbolRuntimeManager import SymbolRuntimeManager
from src.ShadowTrading.Engine.BaseNodeDetector import BaseNodeDetector, BaseStructure, NodeStructure

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
        volume: float = 1.0,
        evidence: Optional[Dict[str, Any]] = None
    ) -> None:
        self.trade_id = trade_id or f"strade-{uuid.uuid4().hex[:6]}"
        self.symbol = symbol.upper()
        self.direction = direction.upper()  # LONG or SHORT
        self.entry = float(entry)
        self.stop = float(stop)
        self.target = float(target)
        self.confidence = float(confidence)
        self.reason = reason
        from src.Core.timeframes import TimeframeNormalizer
        self.custom_time_structure = TimeframeNormalizer.normalize(custom_time_structure)
        self.base_id = base_id or "B-None"
        self.node_id = node_id or "N-None"
        self.pattern = pattern
        self.volume = float(volume)
        self.evidence = evidence if isinstance(evidence, dict) else {}

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
            "evidence": self.evidence,
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
            volume=d.get("volume", 1.0),
            evidence=d.get("evidence", {})
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
    Overhauled main orchestrator for TradeYar AI v8.0.
    Delegates hierarchical multi-asset context processing to the parent SymbolRuntimeManager.
    Enforces maximum limits dynamically.
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

        # Instantiate global SymbolRuntimeManager
        self.runtime_manager = SymbolRuntimeManager(max_active_symbols=self.max_symbols_limit)
        self.detector = BaseNodeDetector()

        # Database File Paths (Consolidated memory indices)
        self.trades_file = "runtime_logs/shadow_trades.json"
        self.bases_file = "runtime_logs/base_memory.json"
        self.nodes_file = "runtime_logs/node_memory.json"
        self.patterns_file = "runtime_logs/pattern_outcomes.json"
        self.learning_file = "runtime_logs/learning_history.json"
        self.signals_file = "runtime_logs/signal_history.json"

        os.makedirs("runtime_logs", exist_ok=True)

        # Core lists for serialization
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

    @property
    def contexts(self) -> Dict[str, SymbolTimeContext]:
        """Exposes flat dictionary view of all registered contexts for compatibility."""
        flat_map = {}
        for sym, frames in self.runtime_manager.symbol_brains.items():
            for tf, ctx in frames.items():
                flat_map[f"{sym}_{tf}"] = ctx
        return flat_map

    @contexts.setter
    def contexts(self, val: Dict[str, SymbolTimeContext]) -> None:
        """Allows resetting contexts list directly for test setup compatibility."""
        self.runtime_manager.reset_brains()

    def _get_or_create_context_bypassing_limits(self, symbol: str, timeframe: Any) -> SymbolTimeContext:
        """Retrieves or creates context bypassing limits (used on startup hydration)."""
        return self.runtime_manager.get_or_create_context_bypassing_limits(symbol, timeframe)

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

    def get_or_create_context(self, symbol: str, timeframe: Any) -> SymbolTimeContext:
        """Retrieves or instantiates an isolated context in SymbolRuntimeManager."""
        return self.runtime_manager.get_or_create_context(symbol, timeframe)

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
        pattern: str = "Base Expansion Continuation",
        evidence: Optional[Dict[str, Any]] = None
    ) -> ShadowTrade:
        """Registers a predictive shadow order in its isolated SymbolTimeContext."""
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
            pattern=pattern,
            evidence=evidence
        )

        ctx.trades.append(trade)
        self.trades.append(trade)
        self._save_trades()

        self.generate_user_signal(trade)
        return trade

    def update_market_ticks(self, symbol: str, current_price: float) -> List[ShadowTrade]:
        """Updates floating states across contexts of a symbol."""
        closed_trades = []
        symbol_upper = symbol.upper()

        # M5 candle close detection
        current_time = datetime.now()
        m5_bucket = current_time.replace(minute=(current_time.minute // 5) * 5, second=0, microsecond=0)

        if not hasattr(self, 'last_m5_bucket'):
            self.last_m5_bucket = m5_bucket

        m5_closed = False
        if m5_bucket > self.last_m5_bucket:
            m5_closed = True
            self.last_m5_bucket = m5_bucket

        # Trigger M5 candle close evaluation
        if m5_closed:
            logger.info("M5 candle close triggered. Running active shadow position evaluations.")
            # Evaluate timeouts / rules for running trades
            for trade in self.trades:
                if trade.status in ["CREATED", "RUNNING"]:
                    act_time = trade.activation_time or trade.creation_time
                    elapsed_minutes = (current_time - act_time).total_seconds() / 60.0
                    elapsed_candles = int(elapsed_minutes / 5)
                    if elapsed_candles >= 24: # Timeout after 24 M5 candles (2 hours)
                        trade.status = "TIME_EXPIRED"
                        trade.result = "TIME_EXPIRED"
                        trade.exit_reason = "Time Expired"
                        trade.close_time = current_time
                        closed_trades.append(trade)

                        # Find corresponding context to record outcome
                        ctx = self.get_or_create_context(trade.symbol, trade.custom_time_structure)
                        self._record_pattern_outcome_context(ctx, trade)
                        self._update_learning_history_context(ctx, trade)
                        self._sync_user_signal(trade)

        if symbol_upper in self.runtime_manager.symbol_brains:
            brains = self.runtime_manager.symbol_brains[symbol_upper]
            for ctx in brains.values():
                ctx.tick_buffer.append({"price": current_price, "timestamp": datetime.now().isoformat()})
                if len(ctx.tick_buffer) > 5000:
                    ctx.tick_buffer.pop(0)

                # Automatic Base/Node Detection at runtime
                base_struct = self.detector.detect_base(symbol_upper, ctx.tick_buffer)
                if base_struct:
                    # Check if base high/low boundaries already exist
                    exists = any(abs(b["high"] - base_struct.high) < 0.01 and abs(b["low"] - base_struct.low) < 0.01 for b in ctx.bases)
                    if not exists:
                        self.add_base(symbol_upper, ctx.timeframe, base_struct.to_dict())
                        logger.info(f"Automatically detected Base for {symbol_upper} @ high={base_struct.high}, low={base_struct.low}")

                node_struct = self.detector.detect_node(ctx.tick_buffer)
                if node_struct:
                    exists = any(abs(n["price_level"] - node_struct.price_level) < 0.01 for n in ctx.nodes)
                    if not exists:
                        self.add_node(symbol_upper, ctx.timeframe, node_struct.to_dict())
                        logger.info(f"Automatically detected Node for {symbol_upper} @ price={node_struct.price_level}")

                for trade in ctx.trades:
                    if trade.status in ["CREATED", "RUNNING"]:
                        trade.update_price_tick(current_price)
                        if trade.status in ["TARGET_HIT", "STOP_HIT", "TIMEOUT", "INVALIDATED"]:
                            if trade.status == "TIMEOUT":
                                trade.status = "TIME_EXPIRED"
                                trade.result = "TIME_EXPIRED"
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
        evidence = trade.evidence if isinstance(trade.evidence, dict) else {}
        hier_ctx = evidence.get("hierarchical_context", {}) if isinstance(evidence, dict) else {}
        if not hier_ctx and isinstance(evidence, dict) and "evidence" in evidence:
            # check inside nested evidence
            hier_ctx = evidence.get("evidence", {}).get("hierarchical_context", {})

        macro_bias_d1 = hier_ctx.get("macro_bias", {}).get("D1", "Bullish") if isinstance(hier_ctx, dict) else "Bullish"
        macro_bias_h4 = hier_ctx.get("macro_bias", {}).get("H4", "Bullish") if isinstance(hier_ctx, dict) else "Bullish"
        m15_setup = hier_ctx.get("primary_decision", {}).get("setup", "Long Reversal") if isinstance(hier_ctx, dict) else "Long Reversal"
        m5_trigger = hier_ctx.get("primary_execution", {}).get("trigger", "Breakout Confirmation") if isinstance(hier_ctx, dict) else "Breakout Confirmation"

        # Win/Loss
        win_loss = "Win" if trade.status == "TARGET_HIT" else "Loss"

        # Max R:R achieved (MFE vs Stop distance)
        stop_dist = abs(trade.entry - trade.stop) if abs(trade.entry - trade.stop) > 0.0001 else 1.0
        max_rr = round(trade.mfe / stop_dist, 2) if trade.mfe > 0 else 0.0

        # Build Multi-dimensional Context Pattern Key
        execution_tf = "M5"
        decision_tf = "M15"
        context_tfs = "H4D1"
        pattern_type = trade.pattern.replace(" ", "")

        reg_and_str = hier_ctx.get("regime_and_structure", {}) if isinstance(hier_ctx, dict) else {}
        h4_regime = reg_and_str.get("H4", "Accumulation") if isinstance(reg_and_str, dict) else "Accumulation"
        market_regime = h4_regime.replace(" ", "")
        pattern_key = f"{trade.symbol}_{execution_tf}_{decision_tf}_{context_tfs}_{pattern_type}_{market_regime}"

        # Populate pre-trade context data with realistic metrics or resolved values
        pre_trade_context = {
            "candle_structure": {
                "body_size": float(evidence.get("body_size", 1.25)),
                "wick_ratio": float(evidence.get("wick_ratio", 0.35)),
                "state": evidence.get("state", "compression")
            },
            "volatility_metrics": {
                "atr_state": evidence.get("atr_state", "normal"),
                "spread_change": float(evidence.get("spread_change", 0.05)),
                "volume_spike": bool(evidence.get("volume_spike", False))
            },
            "structure_alignment": {
                "swing_proximity": float(evidence.get("swing_proximity", 15.0)),
                "order_block_present": bool(evidence.get("order_block_present", True)),
                "fvg_present": bool(evidence.get("fvg_present", True)),
                "higher_tf_alignment": bool(evidence.get("higher_tf_alignment", True))
            }
        }

        # Calculate exact duration
        duration_candles = 12
        if trade.activation_time and trade.close_time:
            diff = trade.close_time - trade.activation_time
            duration_candles = max(1, int(diff.total_seconds() / 300)) # approximate closed M5 candles
        elif len(ctx.tick_buffer) > 0:
            duration_candles = max(1, len(ctx.tick_buffer) // 100)

        # Populate post-trade outcome data
        post_trade_outcome = {
            "max_favorable_excursion": trade.mfe,
            "max_adverse_excursion": trade.mae,
            "duration_candles": duration_candles,
            "explicit_failure_success_reason": trade.status  # TARGET_HIT, STOP_HIT, etc.
        }

        # Calculate historical win-rate for this specific combination
        matching_patterns = [
            p for p in self.patterns
            if p.get("macro_bias_d1") == macro_bias_d1
            and p.get("macro_bias_h4") == macro_bias_h4
            and p.get("m15_setup") == m15_setup
            and p.get("m5_trigger") == m5_trigger
        ]
        prev_wins = sum(1 for p in matching_patterns if p.get("win_loss") == "Win")
        total_with_current = len(matching_patterns) + 1
        current_win_val = 1 if win_loss == "Win" else 0
        historical_win_rate = round((prev_wins + current_win_val) / total_with_current * 100.0, 2)

        outcome = {
            "trade_id": trade.trade_id,
            "symbol": trade.symbol,
            "timeframe": trade.custom_time_structure,
            "pattern": trade.pattern,
            "pattern_key": pattern_key,
            "result": trade.status,
            "win_loss": win_loss,
            "mae": trade.mae,
            "mfe": trade.mfe,
            "max_rr_achieved": max_rr,
            "macro_bias_d1": macro_bias_d1,
            "macro_bias_h4": macro_bias_h4,
            "m15_setup": m15_setup,
            "m5_trigger": m5_trigger,
            "historical_win_rate_pct": historical_win_rate,
            "pre_trade_context": pre_trade_context,
            "post_trade_outcome": post_trade_outcome,
            "timestamp": datetime.now().isoformat()
        }
        ctx.patterns.append(outcome)
        self.patterns.append(outcome)
        self._save_generic(self.patterns_file, self.patterns)

        # Store multi-timeframe pattern snapshots into runtime_logs/brain_memory/
        brain_memory_dir = "runtime_logs/brain_memory"
        os.makedirs(brain_memory_dir, exist_ok=True)
        snapshot_filepath = os.path.join(brain_memory_dir, f"pattern_{trade.trade_id}.json")
        try:
            with open(snapshot_filepath, "w", encoding="utf-8") as f:
                json.dump(outcome, f, indent=4)
        except Exception as e:
            logger.error(f"Failed to write snapshot to brain_memory: {e}")

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
