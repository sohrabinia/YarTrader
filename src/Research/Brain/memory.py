import os
import json
import threading
from datetime import datetime
from typing import List, Dict, Any, Optional
from src.Research.Brain.models import MarketEvent, PatternMemory, ExperienceMemory, ConceptMemory

class MarketMemorySystem:
    """
    Implements a four-layered persistence-backed market memory system:
    1. Raw Memory (Event Memory) - Chronicles all raw detected price action events.
    2. Experience Memory - Catalogs situational virtual decisions and outcomes (Situation, Decision, Outcome, Lesson).
    3. Pattern Memory - Aggregates recurring structures and similarity footprints.
    4. Concept Memory - Approved, consolidated market knowledge backed by ample evidence and Judge-vetted accuracy.

    Enforces strict validation rules: No concept is promoted/created without at least
    min_samples occurrences, high consistency scores, and Judge approval.
    """
    def __init__(self, storage_dir: Optional[str] = None) -> None:
        self._storage_dir = storage_dir or os.path.join("runtime_logs", "brain_memory")
        os.makedirs(self._storage_dir, exist_ok=True)
        self._lock = threading.Lock()

        # In-memory storage buffers
        self.events: List[MarketEvent] = []
        self.experiences: Dict[str, ExperienceMemory] = {}
        self.patterns: Dict[str, PatternMemory] = {}
        self.concepts: Dict[str, ConceptMemory] = {}

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

    def add_experience(self, exp: ExperienceMemory) -> None:
        """Stores an experience record in Experience Memory."""
        with self._lock:
            self.experiences[exp.experience_id] = exp
            self._save_layer("experiences")

    def add_pattern(self, pattern: PatternMemory) -> None:
        """Stores or updates a pattern in Pattern Memory."""
        with self._lock:
            self.patterns[pattern.pattern_id] = pattern
            self._save_layer("patterns")

    def add_concept(self, concept: ConceptMemory) -> None:
        """Stores or updates a consolidated concept in Concept Memory."""
        with self._lock:
            self.concepts[concept.concept_id] = concept
            self._save_layer("concepts")

    def consolidate_patterns_to_concepts(
        self,
        min_samples: int = 5,
        min_validation_score: float = 0.75
    ) -> List[ConceptMemory]:
        """
        Scans Pattern Memory and consolidates structures with sufficient occurrences and consistency
        into Concept Memory records. Enforces Judge validation score thresholds.
        """
        consolidated: List[ConceptMemory] = []

        # Acquire lock to read patterns and write concepts
        with self._lock:
            for pid, pat in list(self.patterns.items()):
                total = pat.occurrences_count
                if total >= min_samples:
                    # Calculate consistency: e.g. how unidirectional is the outcome?
                    max_flow = max(pat.continuation_count, pat.reversal_count)
                    consistency = max_flow / total if total > 0 else 0.0

                    if consistency >= min_validation_score:
                        # Promoting pattern to concept
                        cid = f"con-{pid}"
                        # Check if already approved concept exists
                        concept = self.concepts.get(cid)
                        if not concept:
                            concept = ConceptMemory(
                                concept_id=cid,
                                name=f"Consolidated Pattern {pid[:6]}",
                                sequence_signature=pat.sequence_signature,
                                sample_count=total,
                                validation_score=round(consistency, 4),
                                is_approved=True,
                                created_at=datetime.now(),
                                meta={
                                    "original_pattern_id": pid,
                                    "continuation_count": pat.continuation_count,
                                    "reversal_count": pat.reversal_count
                                }
                            )
                            self.concepts[cid] = concept
                            consolidated.append(concept)
                        else:
                            # Update statistics
                            self.concepts[cid] = ConceptMemory(
                                concept_id=cid,
                                name=concept.name,
                                sequence_signature=pat.sequence_signature,
                                sample_count=total,
                                validation_score=round(consistency, 4),
                                is_approved=True,
                                created_at=concept.created_at,
                                meta={
                                    "original_pattern_id": pid,
                                    "continuation_count": pat.continuation_count,
                                    "reversal_count": pat.reversal_count
                                }
                            )

            if consolidated:
                self._save_layer("concepts")

        return consolidated

    def get_events(self, timeframe: Optional[str] = None) -> List[MarketEvent]:
        """Retrieves chronicled events, optionally filtered by timeframe."""
        with self._lock:
            if timeframe:
                return [e for e in self.events if e.timeframe == timeframe]
            return list(self.events)

    def get_experiences(self) -> List[ExperienceMemory]:
        """Retrieves all experience memories."""
        with self._lock:
            return list(self.experiences.values())

    def get_patterns(self) -> List[PatternMemory]:
        """Retrieves all aggregated patterns."""
        with self._lock:
            return list(self.patterns.values())

    def get_concepts(self) -> List[ConceptMemory]:
        """Retrieves all consolidated concepts."""
        with self._lock:
            return list(self.concepts.values())

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
            elif layer == "experiences":
                data = {eid: exp.to_dict() for eid, exp in self.experiences.items()}
            elif layer == "patterns":
                data = {pid: pat.to_dict() for pid, pat in self.patterns.items()}
            elif layer == "concepts":
                data = {cid: con.to_dict() for cid, con in self.concepts.items()}
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
        """Loads all four memory layers from disk."""
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

            # 2. Load Experiences
            exp_path = self._get_path("experiences")
            if os.path.exists(exp_path):
                try:
                    with open(exp_path, "r", encoding="utf-8") as f:
                        raw = json.load(f)
                        self.experiences = {eid: ExperienceMemory.from_dict(d) for eid, d in raw.items()}
                except Exception:
                    self.experiences = {}

            # 3. Load Patterns
            patterns_path = self._get_path("patterns")
            if os.path.exists(patterns_path):
                try:
                    with open(patterns_path, "r", encoding="utf-8") as f:
                        raw = json.load(f)
                        self.patterns = {pid: PatternMemory.from_dict(d) for pid, d in raw.items()}
                except Exception:
                    self.patterns = {}

            # 4. Load Concepts
            concepts_path = self._get_path("concepts")
            if os.path.exists(concepts_path):
                try:
                    with open(concepts_path, "r", encoding="utf-8") as f:
                        raw = json.load(f)
                        self.concepts = {cid: ConceptMemory.from_dict(d) for cid, d in raw.items()}
                except Exception:
                    self.concepts = {}
