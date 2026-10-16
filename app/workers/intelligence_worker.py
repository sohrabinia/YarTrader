"""Active, persistence-backed Brain maintenance worker.

This worker never fabricates market data or submits broker orders. It refreshes
canonical memory from disk, promotes only recorded outcomes, consolidates
Judge-vetted patterns, and persists auditable active-learning priorities.
"""
from __future__ import annotations

import json
import logging
import os
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from src.Application.Runtime.runtime_state import central_runtime_state

logger = logging.getLogger("YarTrader.IntelligenceWorker")


class IntelligenceWorker:
    """Runs real, read-only intelligence maintenance against shared Brain memory."""

    def __init__(self, interval_sec: float = 300.0, memory_system: Optional[Any] = None,
                 report_path: Optional[str] = None) -> None:
        self.interval_sec = max(30.0, float(interval_sec))
        self.memory_system = memory_system
        self.report_path = Path(report_path) if report_path else (Path("runtime_logs") / "brain_memory" / "active_learning_priorities.json")
        self.is_running = False
        self.thread: Optional[threading.Thread] = None
        self.last_run_time: Optional[datetime] = None
        self.status = "IDLE"
        self.loop_count = 0
        self.last_error: Optional[str] = None
        self.last_report: Dict[str, Any] = {}
        central_runtime_state.update_state("intelligence_status", "Stopped")

    def _get_memory(self):
        if self.memory_system is not None:
            return self.memory_system
        # Resolve lazily to avoid a module import cycle during service startup.
        from src.Application.Services.web_dashboard import global_memory_system
        self.memory_system = global_memory_system
        return self.memory_system

    def run_cycle(self) -> Dict[str, Any]:
        """Refresh persisted evidence and perform one genuine learning-maintenance cycle."""
        from src.Research.Brain.active_learning import ActiveLearningEngine

        memory = self._get_memory()
        # Other authorized workers may have added outcomes since the API booted.
        # Reload the atomic JSON mirrors before calculating any learning updates.
        memory.load_all()
        before = memory.get_learning_statistics()
        promoted = memory.promote_experiences_to_patterns()
        consolidated = memory.consolidate_patterns_to_concepts(
            min_samples=4,
            min_validation_score=0.70,
        )
        priorities = ActiveLearningEngine().analyze_weaknesses_and_set_priorities(
            memory.get_patterns()
        )
        after = memory.get_learning_statistics()

        report: Dict[str, Any] = {
            "timestamp": datetime.now().isoformat(),
            "cycle": self.loop_count + 1,
            "status": "COMPLETED",
            "data_source": "PERSISTED_BRAIN_MEMORY",
            "market_data_fabricated": False,
            "broker_orders_submitted": 0,
            "before": before,
            "after": after,
            "new_patterns_promoted": len(promoted),
            "concepts_consolidated": len(consolidated),
            "priority_count": len(priorities),
            "top_priorities": priorities[:25],
        }
        report_path = self.report_path
        report_path.parent.mkdir(parents=True, exist_ok=True)
        # Use a per-process/thread temporary file so concurrent maintenance attempts
        # cannot overwrite one another's staging file on Windows.
        temp_path = report_path.with_name(
            f"{report_path.name}.{os.getpid()}.{threading.get_ident()}.tmp"
        )
        report_json = json.dumps(report, ensure_ascii=False, indent=2)
        temp_path.write_text(report_json, encoding="utf-8")
        try:
            # Windows readers/scanners may deny delete-sharing on the destination even
            # when writes are allowed. Retry atomic replacement first, then persist the
            # already-staged complete report directly as a compatibility fallback.
            replaced = False
            for attempt in range(5):
                try:
                    os.replace(temp_path, report_path)
                    replaced = True
                    break
                except PermissionError:
                    if attempt == 4:
                        break
                    time.sleep(0.1 * (attempt + 1))
            if not replaced:
                report_path.write_text(report_json, encoding="utf-8")
        finally:
            if temp_path.exists():
                try:
                    temp_path.unlink()
                except OSError:
                    pass
        self.last_run_time = datetime.now()
        self.loop_count += 1
        self.last_error = None
        self.last_report = report
        # A long persisted-memory cycle can finish after stop() is requested.
        # Never let that late completion overwrite the authoritative STOPPED state.
        if self.thread is not None and not self.is_running:
            self.status = "STOPPED"
            central_runtime_state.update_state("intelligence_status", "Stopped")
            return report
        central_runtime_state.update_multiple({
            "intelligence_status": "Running",
            "intelligence_last_cycle_time": self.last_run_time.isoformat(),
            "intelligence_cycle_count": self.loop_count,
            "intelligence_last_error": None,
            "intelligence_memory_experiences": after.get("total_experiences", 0),
            "intelligence_memory_patterns": after.get("patterns_created", 0),
            "intelligence_memory_concepts": after.get("concepts_learned", 0),
            "intelligence_priority_count": len(priorities),
        })
        logger.info(
            "Intelligence cycle complete: experiences=%s patterns=%s concepts=%s promoted=%s consolidated=%s priorities=%s",
            after.get("total_experiences", 0), after.get("patterns_created", 0),
            after.get("concepts_learned", 0), len(promoted), len(consolidated), len(priorities),
        )
        return report

    def start(self) -> None:
        if self.is_running:
            return
        self.is_running = True
        self.status = "RUNNING"
        central_runtime_state.update_state("intelligence_status", "Starting")
        self.thread = threading.Thread(target=self._run_loop, daemon=True, name="IntelligenceWorker")
        self.thread.start()

    def stop(self) -> None:
        self.is_running = False
        self.status = "STOPPED"
        central_runtime_state.update_state("intelligence_status", "Stopped")
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5.0)

    def _run_loop(self) -> None:
        while self.is_running:
            try:
                self.status = "RUNNING"
                self.run_cycle()
                if not self.is_running:
                    self.status = "STOPPED"
                    central_runtime_state.update_state("intelligence_status", "Stopped")
                    break
            except Exception as exc:
                # A cycle may fail after stop() is requested; STOPPED must remain authoritative.
                if not self.is_running:
                    self.status = "STOPPED"
                    central_runtime_state.update_state("intelligence_status", "Stopped")
                    break
                self.status = "RECOVERING"
                self.last_error = f"{type(exc).__name__}: {exc}"
                central_runtime_state.update_multiple({
                    "intelligence_status": "Recovering",
                    "intelligence_last_error": self.last_error[:500],
                })
                logger.exception("Intelligence cycle failed; will retry after interval")
            elapsed = 0.0
            while elapsed < self.interval_sec and self.is_running:
                time.sleep(min(1.0, self.interval_sec - elapsed))
                elapsed += 1.0
