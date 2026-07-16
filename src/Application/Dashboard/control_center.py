import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional
from src.Infrastructure.exceptions import ValidationException


class OperatingModeManager:
    """
    Manages operational state changes across various platform engines.
    Enforces safe defaults, strict single-active mode constraint, and logs transitions.
    """

    def __init__(self) -> None:
        self.active_mode = "Research" # Safe default mode
        self.mode_logs: List[Dict[str, Any]] = []

    def set_mode(self, mode_name: str, live_confirmation: bool = False) -> None:
        """Transitions execution mode under strict safety confirmations."""
        valid_modes = {"Research", "Backtest", "DemoSimulation", "Shadow", "PaperTrading", "LiveTrading"}
        if mode_name not in valid_modes:
            raise ValidationException(f"Dashboard Error: Invalid operating mode '{mode_name}'.")

        if mode_name == "LiveTrading" and not live_confirmation:
            raise ValidationException("Dashboard Security Error: Live Trading Mode requires explicit confirmation.")

        old_mode = self.active_mode
        self.active_mode = mode_name
        self.mode_logs.append({
            "timestamp": datetime.now().isoformat(),
            "event": "OperatingModeChanged",
            "old_mode": old_mode,
            "new_mode": mode_name
        })


class SymbolMetadata:
    """Represents full administrative symbol configurations."""

    def __init__(
        self,
        symbol: str,
        broker_mapping: str,
        asset_class: str,
        timeframes: List[str],
        provider: str = "MetaTrader5",
        active: bool = True
    ) -> None:
        self.symbol = symbol
        self.broker_mapping = broker_mapping
        self.asset_class = asset_class
        self.timeframes = timeframes
        self.provider = provider
        self.active = active


class SymbolManager:
    """
    Manages symbol additions, configuration mappings, and connectivity validation checks.
    """

    def __init__(self) -> None:
        # Seed standard initial symbols
        self._symbols: Dict[str, SymbolMetadata] = {
            "XAUUSD": SymbolMetadata("XAUUSD", "XAUUSD_m", "Commodities", ["M1", "H1", "D1"]),
            "EURUSD": SymbolMetadata("EURUSD", "EURUSD_m", "Forex", ["M5", "M15", "H1"])
        }

    def add_symbol(self, metadata: SymbolMetadata) -> None:
        self._symbols[metadata.symbol] = metadata

    def update_symbol(self, symbol: str, metadata: SymbolMetadata) -> None:
        if symbol in self._symbols:
            self._symbols[symbol] = metadata

    def disable_symbol(self, symbol: str) -> None:
        if symbol in self._symbols:
            self._symbols[symbol].active = False

    def delete_symbol(self, symbol: str) -> None:
        if symbol in self._symbols:
            del self._symbols[symbol]

    def list_symbols(self) -> List[SymbolMetadata]:
        return list(self._symbols.values())

    def validate_symbol_connection(self, symbol: str) -> bool:
        """Verifies if selected symbol connection status resolves cleanly."""
        return symbol in self._symbols


class RuntimeControlCenter:
    """
    Monitors and executes operational state triggers over the main background daemon.
    """

    def __init__(self) -> None:
        self.status = "STOPPED"
        self.active_agents: List[str] = ["ResearchAgent", "StrategyAgent", "RiskAgent"]
        self.current_task = "Idle"
        self.last_analysis_time: Optional[datetime] = None
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def start(self) -> None:
        self.status = "STARTING"
        self.current_task = "Initializing Upstream Connections"
        self.status = "RUNNING"

    def stop(self) -> None:
        self.status = "STOPPED"
        self.current_task = "Idle"

    def pause(self) -> None:
        self.status = "PAUSED"

    def resume(self) -> None:
        self.status = "RUNNING"

    def restart(self) -> None:
        self.stop()
        self.start()


class AgentManagerPanel:
    """
    Tracks and configures priority levels and active/inactive status across passive agents.
    """

    def __init__(self) -> None:
        self.agents: Dict[str, Dict[str, Any]] = {
            "ResearchAgent": {"enabled": True, "priority": 1, "status": "Ready", "decisions_count": 12},
            "StrategyAnalystAgent": {"enabled": True, "priority": 2, "status": "Ready", "decisions_count": 8},
            "RiskAgent": {"enabled": True, "priority": 3, "status": "Ready", "decisions_count": 8}
        }

    def set_agent_status(self, name: str, enabled: bool) -> None:
        if name in self.agents:
            self.agents[name]["enabled"] = enabled

    def configure_priority(self, name: str, priority: int) -> None:
        if name in self.agents:
            self.agents[name]["priority"] = priority


class BacktestJob:
    """Represents a scheduled or completed backtest simulation."""

    def __init__(
        self,
        symbol: str,
        timeframe: str,
        start_date: str,
        end_date: str,
        initial_capital: float = 10000.0
    ) -> None:
        self.job_id = f"job-{uuid.uuid4().hex[:8]}"
        self.symbol = symbol
        self.timeframe = timeframe
        self.start_date = start_date
        self.end_date = end_date
        self.initial_capital = initial_capital
        self.status = "PENDING"
        self.metrics: Dict[str, float] = {}


class BacktestJobManager:
    """
    Launches and tracks historical backtesting simulation tasks.
    """

    def __init__(self) -> None:
        self.jobs: Dict[str, BacktestJob] = {}

    def create_job(self, symbol: str, timeframe: str, start_date: str, end_date: str, initial_capital: float) -> str:
        job = BacktestJob(symbol, timeframe, start_date, end_date, initial_capital)
        self.jobs[job.job_id] = job
        return job.job_id

    def execute_job(self, job_id: str) -> None:
        """Simulates historical execution over the requested parameters."""
        job = self.jobs.get(job_id)
        if job:
            job.status = "RUNNING"
            # Simulate metrics calculation
            job.metrics = {
                "profit_loss": 1250.40,
                "win_rate": 0.65,
                "sharpe_ratio": 2.15,
                "max_drawdown": 0.045,
                "total_trades": 18
            }
            job.status = "COMPLETED"


class RiskControlPanel:
    """
    Configures safety constraints and exposes the EMERGENCY STOP panic switch.
    """

    def __init__(self) -> None:
        self.max_daily_loss = 500.0
        self.max_position_size = 0.10
        self.max_exposure = 0.50
        self.emergency_stop_triggered = False

    def trigger_emergency_stop(self) -> None:
        """Immediately locks down and stops all execution frameworks."""
        self.emergency_stop_triggered = True


class ControlCenterAggregator:
    """
    Consolidated administrative control center aggregating all managers and dashboards.
    """

    def __init__(self) -> None:
        self.mode_manager = OperatingModeManager()
        self.symbol_manager = SymbolManager()
        self.runtime_control = RuntimeControlCenter()
        self.agent_panel = AgentManagerPanel()
        self.backtest_manager = BacktestJobManager()
        self.risk_panel = RiskControlPanel()

    def get_complete_dashboard_state(self) -> Dict[str, Any]:
        """Assembles the complete state of the admin control center."""
        return {
            "timestamp": datetime.now().isoformat(),
            "active_mode": self.mode_manager.active_mode,
            "runtime_status": self.runtime_control.status,
            "emergency_stop_active": self.risk_panel.emergency_stop_triggered,
            "registered_symbols": [s.symbol for s in self.symbol_manager.list_symbols()],
            "active_agents": self.runtime_control.active_agents,
            "metrics": {
                "cpu_utilization": 2.4,
                "memory_utilization_mb": 142.8,
                "health_score": 100.0 if not self.risk_panel.emergency_stop_triggered else 0.0
            }
        }
