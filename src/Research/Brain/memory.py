import os
import json
import threading
from datetime import datetime
from typing import List, Dict, Any, Optional
from src.Research.Brain.models import MarketEvent, PatternMemory, ExperienceMemory

class MarketMemorySystem:
    """
    Implements a three-layered persistence-backed market memory system:
    1. Event Memory - Chronicles all raw detected price action events.
    2. Pattern Memory - Aggregates recurring structures and similarity footprints.
    3. Experience Memory - Catalogs situational virtual decisions and outcomes (Situation, Decision, Outcome, Lesson).
    """
    def __init__(self, storage_dir: Optional[str] = None) -> None:
        self._storage_dir = storage_dir or os.path.join("runtime_logs", "brain_memory")
        os.makedirs(self._storage_dir, exist_ok=True)
        self._lock = threading.Lock()

        # In-memory storage buffers
        self.events: List[MarketEvent] = []
        self.patterns: Dict[str, PatternMemory] = {}
        self.experiences: Dict[str, ExperienceMemory] = {}

        # Load existing data on initialization
        self.load_all()

    def add_event(self, event: MarketEvent) -> None:
        """Stores an observed raw market event in Event Memory."""
        with self._lock:
            # Check for duplication using timestamp bounds
            exists = any(
                e.start_time == event.start_time and e.end_time == event.end_time and e.timeframe == event.timeframe
                for e in self.events
            )
            if not exists:
                self.events.append(event)
                self._save_layer("events")

    def add_pattern(self, pattern: PatternMemory) -> None:
        """Stores or updates a pattern in Pattern Memory."""
        with self._lock:
            self.patterns[pattern.pattern_id] = pattern
            self._save_layer("patterns")

    def add_experience(self, exp: ExperienceMemory) -> None:
        """Stores an experience record in Experience Memory."""
        with self._lock:
            self.experiences[exp.experience_id] = exp
            self._save_layer("experiences")

    def get_events(self, timeframe: Optional[str] = None) -> List[MarketEvent]:
        """Retrieves chronicled events, optionally filtered by timeframe."""
        with self._lock:
            if timeframe:
                return [e for e in self.events if e.timeframe == timeframe]
            return list(self.events)

    def get_patterns(self) -> List[PatternMemory]:
        """Retrieves all aggregated patterns."""
        with self._lock:
            return list(self.patterns.values())

    def get_experiences(self) -> List[ExperienceMemory]:
        """Retrieves all experience memories."""
        with self._lock:
            return list(self.experiences.values())

    # --- Persistence Helpers ---

    def _get_path(self, layer: str) -> str:
        return os.path.join(self._storage_dir, f"{layer}_memory.json")

    def _save_layer(self, layer: str) -> None:
        """Serializes and saves a memory layer atomically using the temp-swap pattern."""
        filepath = self._get_path(layer)
        temp_filepath = filepath + ".tmp"

        try:
            if layer == "events":
                data = [e.to_dict() for e in self.events]
            elif layer == "patterns":
                data = {pid: pat.to_dict() for pid, pat in self.patterns.items()}
            elif layer == "experiences":
                data = {eid: exp.to_dict() for eid, exp in self.experiences.items()}
            else:
                return

            with open(temp_filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)

            # Atomic swap
            os.replace(temp_filepath, filepath)
        except Exception:
            if os.path.exists(temp_filepath):
                try:
                    os.remove(temp_filepath)
                except OSError:
                    pass

    def load_all(self) -> None:
        """Loads all three memory layers from disk."""
        with self._lock:
            # 1. Load Events
            events_path = self._get_path("events")
            if os.path.exists(events_path):
                try:
                    with open(events_path, "r", encoding="utf-8") as f:
                        raw = json.load(f)
                        self.events = [MarketEvent.from_dict(d) for d in raw]
                except Exception:
                    self.events = []

            # 2. Load Patterns
            patterns_path = self._get_path("patterns")
            if os.path.exists(patterns_path):
                try:
                    with open(patterns_path, "r", encoding="utf-8") as f:
                        raw = json.load(f)
                        self.patterns = {pid: PatternMemory.from_dict(d) for pid, d in raw.items()}
                except Exception:
                    self.patterns = {}

            # 3. Load Experiences
            exp_path = self._get_path("experiences")
            if os.path.exists(exp_path):
                try:
                    with open(exp_path, "r", encoding="utf-8") as f:
                        raw = json.load(f)
                        self.experiences = {eid: ExperienceMemory.from_dict(d) for eid, d in raw.items()}
                except Exception:
                    self.experiences = {}
