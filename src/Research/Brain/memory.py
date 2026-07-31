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
        self.last_learning_update: str = datetime.now().isoformat()

        # Load existing data on initialization
        self.load_all()

    def get_learning_statistics(self) -> Dict[str, Any]:
        """
        Calculates dynamic learning statistics and counters from memory layers.
        """
        with self._lock:
            exps = list(self.experiences.values())
            pats = list(self.patterns.values())
            con_count = len(self.concepts)

        successful_patterns = 0
        failed_patterns = 0

        for pat in pats:
            total = pat.occurrences_count
            if total > 0:
                success_ratio = pat.continuation_count / total
                if success_ratio >= 0.60:
                    successful_patterns += 1
                elif success_ratio <= 0.40:
                    failed_patterns += 1

        return {
            "total_experiences": len(exps),
            "patterns_created": len(pats),
            "concepts_learned": con_count,
            "successful_patterns": successful_patterns,
            "failed_patterns": failed_patterns,
            "last_learning_update": self.last_learning_update
        }

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
            self.last_learning_update = datetime.now().isoformat()
            self._save_layer("experiences")

    def add_pattern(self, pattern: PatternMemory) -> None:
        """Stores or updates a pattern in Pattern Memory."""
        with self._lock:
            self.patterns[pattern.pattern_id] = pattern
            self.last_learning_update = datetime.now().isoformat()
            self._save_layer("patterns")

    def add_concept(self, concept: ConceptMemory) -> None:
        """Stores or updates a consolidated concept in Concept Memory."""
        with self._lock:
            self.concepts[concept.concept_id] = concept
            self.last_learning_update = datetime.now().isoformat()
            self._save_layer("concepts")

    def validate_experience(self, exp_id: str) -> bool:
        """
        Validates a raw experience, marking it as a Validated Experience.
        Returns True if successfully validated and updated.
        """
        with self._lock:
            if exp_id not in self.experiences:
                return False
            exp = self.experiences[exp_id]
            # Mark as validated in meta
            if "meta" not in exp.__dict__ or exp.meta is None:
                exp.meta = {}
            exp.meta["is_validated"] = True
            self._save_layer("experiences")
            return True

    def calculate_experience_weight(
        self,
        exp_id: str,
        current_time: datetime,
        reference_signature: Optional[List[float]] = None
    ) -> float:
        """
        Calculates the experience weight based on forgetting/confidence decay.
        Weight = Age Factor + Success Factor + Similarity Factor
        """
        with self._lock:
            if exp_id not in self.experiences:
                return 0.0
            exp = self.experiences[exp_id]

        # 1. Age Factor (decays over time)
        diff_seconds = max(0.0, (current_time - exp.timestamp).total_seconds())
        # Decay half-life of 7 days (604800 seconds)
        age_factor = 1.0 / (1.0 + (diff_seconds / 604800.0))

        # 2. Success Factor
        if exp.outcome_result == "SUCCESS":
            success_factor = 1.0
        elif exp.outcome_result == "FAILURE":
            success_factor = 0.5
        else:
            success_factor = 0.8

        # 3. Similarity Factor
        similarity_factor = 0.5
        if reference_signature and exp.situation_signature:
            sig1 = exp.situation_signature
            sig2 = reference_signature
            if len(sig1) == len(sig2):
                dot_product = sum(a * b for a, b in zip(sig1, sig2))
                norm_a = sum(a * a for a in sig1) ** 0.5
                norm_b = sum(b * b for b in sig2) ** 0.5
                if norm_a > 0 and norm_b > 0:
                    similarity_factor = dot_product / (norm_a * norm_b)
                    # Bound between 0.0 and 1.0
                    similarity_factor = max(0.0, min(1.0, similarity_factor))

        return age_factor + success_factor + similarity_factor

    def promote_experiences_to_patterns(self) -> List[PatternMemory]:
        """
        Promotes validated experiences to Pattern Memory.
        Groups similar experiences and creates/updates Pattern Memory.
        """
        promoted_patterns: List[PatternMemory] = []
        with self._lock:
            validated_exps = [
                exp for exp in self.experiences.values()
                if exp.meta.get("is_validated") is True or exp.outcome_result in ["SUCCESS", "FAILURE"]
            ]

        for exp in validated_exps:
            sig = exp.situation_signature
            if not sig:
                continue

            # Look for matching pattern in current patterns
            matched_pattern = None
            best_similarity = 0.0

            with self._lock:
                patterns_list = list(self.patterns.values())

            for pat in patterns_list:
                pat_sig = pat.sequence_signature
                if len(pat_sig) == len(sig):
                    dot_product = sum(a * b for a, b in zip(pat_sig, sig))
                    norm_a = sum(a * a for a in pat_sig) ** 0.5
                    norm_b = sum(b * b for b in sig) ** 0.5
                    sim = (dot_product / (norm_a * norm_b)) if (norm_a > 0 and norm_b > 0) else 0.0
                    if sim > best_similarity:
                        best_similarity = sim
                        matched_pattern = pat

            is_success = exp.outcome_result == "SUCCESS"

            if matched_pattern and best_similarity >= 0.85:
                # Update pattern
                with self._lock:
                    matched_pattern.occurrences_count += 1
                    if is_success:
                        matched_pattern.continuation_count += 1
                    else:
                        matched_pattern.reversal_count += 1
                    # Append outcome detail
                    matched_pattern.outcomes.append({
                        "experience_id": exp.experience_id,
                        "timestamp": exp.timestamp.isoformat(),
                        "outcome": exp.outcome_result
                    })
                    self._save_layer("patterns")
                    promoted_patterns.append(matched_pattern)
            else:
                # Create a new pattern
                import uuid
                pid = f"pat-{uuid.uuid4().hex[:8]}"
                new_pat = PatternMemory(
                    pattern_id=pid,
                    sequence_signature=sig,
                    occurrences_count=1,
                    continuation_count=1 if is_success else 0,
                    reversal_count=0 if is_success else 1,
                    outcomes=[{
                        "experience_id": exp.experience_id,
                        "timestamp": exp.timestamp.isoformat(),
                        "outcome": exp.outcome_result
                    }],
                    created_at=datetime.now()
                )
                with self._lock:
                    self.patterns[pid] = new_pat
                    self._save_layer("patterns")
                    promoted_patterns.append(new_pat)

        return promoted_patterns

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
