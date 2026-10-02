from __future__ import annotations

import os

import json
import threading
import uuid
import hashlib
from datetime import datetime
from typing import TYPE_CHECKING, List, Dict, Any, Optional
from src.Research.Brain.models import MarketEvent, PatternMemory, ExperienceMemory, ConceptMemory

if TYPE_CHECKING:
    from src.Application.Deployment.artifact_store import YarTraderArtifactStore

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
    def __init__(self, storage_dir: Optional[str] = None, artifact_store: Optional[YarTraderArtifactStore] = None) -> None:
        self._storage_dir = storage_dir or os.path.join("runtime_logs", "brain_memory")
        os.makedirs(self._storage_dir, exist_ok=True)
        if artifact_store is None:
            from src.Application.Deployment.storage import YarTraderStorageManager
            artifact_store = YarTraderStorageManager.get_manager().get_artifact_store()
        self._artifact_store = artifact_store
        self._artifact_manifest_path = os.path.join(self._storage_dir, "artifact_manifest.json")
        self._lock = threading.Lock()
        self._event_keys = set()
        self._event_pending = 0
        self._event_save_every = 1

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
            # O(1) duplicate detection; historical runs can contain millions of events.
            key = (event.symbol, event.start_time, event.end_time, event.timeframe)
            if key not in self._event_keys:
                self.events.append(event)
                self._event_keys.add(key)
                self._event_pending += 1
                if self._event_pending >= self._event_save_every:
                    self._save_layer("events")
                    self._event_pending = 0

    def configure_event_persistence(self, save_every: int = 1) -> None:
        """Configure buffered raw-event persistence for historical workloads."""
        self._event_save_every = max(1, int(save_every))

    def flush_event_persistence(self) -> None:
        with self._lock:
            if self._event_pending:
                self._save_layer("events")
                self._event_pending = 0

    def add_experience(self, exp: ExperienceMemory) -> None:
        """Stores an experience record in Experience Memory."""
        with self._lock:
            if exp.experience_id in self.experiences:
                return
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

    def promote_raw_events_to_experiences(self, symbol: str, timeframe: str) -> List[ExperienceMemory]:
        """
        LAYER 1 -> LAYER 2 PROMOTION
        Processes raw MarketEvent entries from Event Memory and promotes them to ExperienceMemory.
        """
        promoted_exps: List[ExperienceMemory] = []
        with self._lock:
            unpromoted_events = [
                e for e in self.events
                if e.symbol == symbol and e.timeframe == timeframe and not e.meta.get("is_promoted_to_experience")
            ]

        for evt in unpromoted_events:
            reaction_end_raw = evt.meta.get("reaction_end_time")
            if reaction_end_raw:
                try:
                    reaction_end = datetime.fromisoformat(reaction_end_raw)
                    now = datetime.now(reaction_end.tzinfo) if reaction_end.tzinfo else datetime.now()
                    if reaction_end > now:
                        continue
                except (TypeError, ValueError):
                    continue
            signature = list(evt.meta.get("sequence_signature") or [])
            if not signature:
                signature = [evt.price_change, float(evt.duration_candles), evt.reaction_magnitude]
            base_action = "BUY" if evt.meta.get("direction") == "upward" else "SELL"
            is_continuation = evt.reaction_type == "extension"
            predicted_action = base_action if is_continuation else ("SELL" if base_action == "BUY" else "BUY")
            favorable_excursion = abs(evt.price_change) if is_continuation else abs(evt.reaction_magnitude)
            adverse_excursion = abs(evt.reaction_magnitude) if is_continuation else abs(evt.price_change)
            exp_id = f"exp-{uuid.uuid4().hex[:8]}"

            exp = ExperienceMemory(
                experience_id=exp_id,
                symbol=evt.symbol,
                timeframe=evt.timeframe,
                timestamp=evt.end_time,
                situation_signature=signature,
                decision_action="BUY" if evt.price_change > 0 else "SELL",
                outcome_result="SUCCESS" if evt.reaction_type == "extension" else "FAILURE",
                lesson_feedback=f"Promoted from raw event with reaction: {evt.reaction_type}",
                max_favorable_excursion=abs(evt.price_change),
                max_adverse_excursion=-abs(evt.reaction_magnitude),
                meta={
                    "raw_event_start": evt.start_time.isoformat(),
                    "pattern_symbol": evt.symbol.upper(),
                    "pattern_timeframe": evt.timeframe.upper(),
                    "timeframe_signature": [evt.timeframe.upper()],
                    "predicted_action": predicted_action,
                    "favorable_excursion": favorable_excursion,
                    "adverse_excursion": adverse_excursion,
                }
            )

            # Link/mark the raw event as promoted
            evt.meta["is_promoted_to_experience"] = True
            evt.meta["promoted_experience_id"] = exp_id

            self.add_experience(exp)
            promoted_exps.append(exp)

        if promoted_exps:
            with self._lock:
                self._save_layer("events")
        return promoted_exps

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
        exp_time = exp.timestamp
        if exp_time.tzinfo is not None and current_time.tzinfo is None:
            current_time = current_time.replace(tzinfo=exp_time.tzinfo)
        elif exp_time.tzinfo is None and current_time.tzinfo is not None:
            current_time = current_time.replace(tzinfo=None)
        diff_seconds = max(0.0, (current_time - exp_time).total_seconds())
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
        LAYER 2 -> LAYER 3 PROMOTION
        Promotes validated and high-quality experiences to Pattern Memory.
        Filters out low-quality or lucky decisions, and factors in confidence decay.
        """
        promoted_patterns: List[PatternMemory] = []
        with self._lock:
            # Filter validated or resolved experiences, and skip those flagged by Judge as Lucky Wins
            validated_exps = [
                exp for exp in self.experiences.values()
                if (exp.meta.get("is_validated") is True or exp.outcome_result in ["SUCCESS", "FAILURE"])
                and not exp.meta.get("is_lucky_win", False)
                and not exp.meta.get("is_promoted_to_pattern", False)
            ]

        for exp in validated_exps:
            sig = exp.situation_signature
            if not sig:
                continue
            scope_symbol = str(exp.meta.get("pattern_symbol", exp.symbol)).upper()
            scope_timeframe = str(exp.meta.get("pattern_timeframe", exp.timeframe)).upper()
            scope_tfs = sorted({str(tf).upper() for tf in exp.meta.get("timeframe_signature", [scope_timeframe]) if tf})
            scope_context_id = str(exp.meta.get("context_id", ""))
            scope_context_signature = exp.meta.get("context_signature", {}) or {}

            # Look for matching pattern in the exact market/timeframe scope.
            matched_pattern = None
            best_similarity = 0.0

            with self._lock:
                patterns_list = [
                    p for p in self.patterns.values()
                    if p.symbol.upper() == scope_symbol
                    and p.timeframe.upper() == scope_timeframe
                    and sorted(p.timeframe_signature or [p.timeframe.upper()]) == scope_tfs
                    and (not scope_context_id or not p.context_id or p.context_id == scope_context_id)
                    and p.status != "RETIRED"
                ]

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

            # Factor in confidence decay & Judge scores at promotion
            decay_weight = self.calculate_experience_weight(exp.experience_id, datetime.now(), sig)
            judge_score = exp.meta.get("judge_reasoning_score", 1.0)
            adjusted_confidence = decay_weight * judge_score

            if matched_pattern and best_similarity >= 0.85:
                # Update pattern
                with self._lock:
                    if any(out.get("experience_id") == exp.experience_id for out in matched_pattern.outcomes):
                        exp.meta["is_promoted_to_pattern"] = True
                        continue
                    matched_pattern.occurrences_count += 1
                    if is_success:
                        matched_pattern.continuation_count += 1
                    else:
                        matched_pattern.reversal_count += 1
                    # Append outcome detail linked with adjusted confidence and judge accuracy metrics
                    matched_pattern.outcomes.append({
                        "experience_id": exp.experience_id,
                        "timestamp": exp.timestamp.isoformat(),
                        "outcome": exp.outcome_result,
                        "adjusted_confidence": round(adjusted_confidence, 4),
                        "judge_vetted_accuracy": exp.meta.get("judge_accuracy", 1.0),
                        "favorable_excursion": float(exp.meta.get("favorable_excursion", exp.max_favorable_excursion)),
                        "adverse_excursion": float(exp.meta.get("adverse_excursion", abs(exp.max_adverse_excursion))),
                        "predicted_action": str(exp.meta.get("predicted_action", exp.decision_action)).upper(),
                    })
                    matched_pattern.last_validated_at = datetime.now()
                    self._refresh_pattern_lifecycle(matched_pattern)
                    self._save_layer("patterns")
                    promoted_patterns.append(matched_pattern)
            else:
                # Create a new pattern with occurrences count and linked metrics
                identity = json.dumps({
                    "symbol": scope_symbol,
                    "timeframe": scope_timeframe,
                    "timeframe_signature": scope_tfs,
                    "context_id": scope_context_id,
                    "signature": [round(float(v), 8) for v in sig],
                }, sort_keys=True, separators=(",", ":"))
                pid = f"pat-{hashlib.sha256(identity.encode("utf-8")).hexdigest()[:16]}"
                new_pat = PatternMemory(
                    pattern_id=pid,
                    sequence_signature=sig,
                    occurrences_count=1,
                    continuation_count=1 if is_success else 0,
                    reversal_count=0 if is_success else 1,
                    outcomes=[{
                        "experience_id": exp.experience_id,
                        "timestamp": exp.timestamp.isoformat(),
                        "outcome": exp.outcome_result,
                        "adjusted_confidence": round(adjusted_confidence, 4),
                        "judge_vetted_accuracy": exp.meta.get("judge_accuracy", 1.0),
                        "favorable_excursion": float(exp.meta.get("favorable_excursion", exp.max_favorable_excursion)),
                        "adverse_excursion": float(exp.meta.get("adverse_excursion", abs(exp.max_adverse_excursion))),
                        "predicted_action": str(exp.meta.get("predicted_action", exp.decision_action)).upper(),
                    }],
                    created_at=datetime.now(),
                    symbol=scope_symbol,
                    timeframe=scope_timeframe,
                    timeframe_signature=scope_tfs,
                    context_id=scope_context_id,
                    context_signature=scope_context_signature,
                    version=1,
                    status="ACTIVE",
                    family_id=pid,
                    last_validated_at=datetime.now()
                )
                with self._lock:
                    self.patterns[pid] = new_pat
                    self._save_layer("patterns")
                    promoted_patterns.append(new_pat)

        if validated_exps:
            with self._lock:
                for exp in validated_exps:
                    if exp.situation_signature:
                        exp.meta["is_promoted_to_pattern"] = True
                self._save_layer("experiences")

        return promoted_patterns

    def _refresh_pattern_lifecycle(self, pattern: PatternMemory) -> None:
        if pattern.occurrences_count < 5:
            pattern.status = "ACTIVE"
            return
        recent = pattern.outcomes[-20:]
        if not recent:
            return
        successes = sum(1 for out in recent if out.get("outcome") == "SUCCESS")
        rate = successes / len(recent)
        if rate < 0.30 and len(recent) >= 10:
            pattern.status = "RETIRED"
        elif rate < 0.45 and len(recent) >= 5:
            pattern.status = "DEGRADED"
        else:
            pattern.status = "ACTIVE"

    def consolidate_patterns_to_concepts(
        self,
        min_samples: int = 5,
        min_validation_score: float = 0.75
    ) -> List[ConceptMemory]:
        """
        LAYER 3 -> LAYER 4 PROMOTION
        Scans Pattern Memory and consolidates structures with sufficient occurrences and consistency
        into Concept Memory records. Enforces Judge validation score thresholds and Judge-vetted accuracy.
        """
        consolidated: List[ConceptMemory] = []

        with self._lock:
            for pid, pat in list(self.patterns.items()):
                total = pat.occurrences_count
                if total >= min_samples:
                    # Calculate consistency: e.g. how unidirectional is the outcome?
                    max_flow = max(pat.continuation_count, pat.reversal_count)
                    consistency = max_flow / total if total > 0 else 0.0

                    # Calculate average Judge-vetted accuracy across outcomes
                    vetted_accuracies = [out.get("judge_vetted_accuracy", 1.0) for out in pat.outcomes]
                    avg_vetted_accuracy = sum(vetted_accuracies) / len(vetted_accuracies) if vetted_accuracies else 1.0

                    # Standardize promotion: Enforce Judge-vetted accuracy must be high
                    if consistency >= min_validation_score and avg_vetted_accuracy >= 0.60:
                        cid = f"con-{pid}"
                        concept = self.concepts.get(cid)
                        if not concept:
                            concept = ConceptMemory(
                                concept_id=cid,
                                name=f"Consolidated Pattern {pid[:6]}",
                                sequence_signature=pat.sequence_signature,
                                sample_count=total,
                                validation_score=round(consistency * avg_vetted_accuracy, 4),
                                is_approved=True,
                                created_at=datetime.now(),
                                meta={
                                    "original_pattern_id": pid,
                                    "continuation_count": pat.continuation_count,
                                    "reversal_count": pat.reversal_count,
                                    "avg_vetted_accuracy": avg_vetted_accuracy
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
                                validation_score=round(consistency * avg_vetted_accuracy, 4),
                                is_approved=True,
                                created_at=concept.created_at,
                                meta={
                                    "original_pattern_id": pid,
                                    "continuation_count": pat.continuation_count,
                                    "reversal_count": pat.reversal_count,
                                    "avg_vetted_accuracy": avg_vetted_accuracy
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

    def create_snapshot(self, backup_tag: str) -> Dict[str, Any]:
        """
        Creates a validated backup snapshot of all active memory layers.
        Saves files to a dedicated snapshots folder with metadata and SHA-256 checksums.
        """
        import shutil
        import hashlib
        snapshot_dir = os.path.join(self._storage_dir, "snapshots", backup_tag)
        os.makedirs(snapshot_dir, exist_ok=True)

        metadata = {
            "backup_tag": backup_tag,
            "timestamp": datetime.now().isoformat(),
            "files": {}
        }

        layers = ["events", "experiences", "patterns", "concepts"]
        for layer in layers:
            src_path = self._get_path(layer)
            if os.path.exists(src_path):
                dest_path = os.path.join(snapshot_dir, f"{layer}_memory.json")
                shutil.copy2(src_path, dest_path)

                # Calculate checksum
                with open(dest_path, "rb") as f:
                    file_hash = hashlib.sha256(f.read()).hexdigest()
                metadata["files"][layer] = {
                    "filename": f"{layer}_memory.json",
                    "sha256": file_hash,
                    "size_bytes": os.path.getsize(dest_path)
                }

        metadata_path = os.path.join(snapshot_dir, "snapshot_metadata.json")
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=4)

        return metadata

    def restore_snapshot(self, backup_tag: str) -> bool:
        """
        Restores the memory layers from a validated backup snapshot.
        """
        import shutil
        snapshot_dir = os.path.join(self._storage_dir, "snapshots", backup_tag)
        if not os.path.exists(snapshot_dir):
            return False

        layers = ["events", "experiences", "patterns", "concepts"]
        for layer in layers:
            src_path = os.path.join(snapshot_dir, f"{layer}_memory.json")
            if os.path.exists(src_path):
                dest_path = self._get_path(layer)
                shutil.copy2(src_path, dest_path)

        # Force reload in-memory structures
        self.load_all()
        return True

    def get_latest_snapshot_tag(self) -> Optional[str]:
        """
        Scans the snapshots folder and returns the tag of the latest snapshot based on directory creation/timestamp.
        """
        snapshots_dir = os.path.join(self._storage_dir, "snapshots")
        if not os.path.exists(snapshots_dir):
            return None
        try:
            entries = os.listdir(snapshots_dir)
            if not entries:
                return None
            # Find metadata files to sort by timestamp
            candidates = []
            for entry in entries:
                meta_path = os.path.join(snapshots_dir, entry, "snapshot_metadata.json")
                if os.path.exists(meta_path):
                    try:
                        with open(meta_path, "r", encoding="utf-8") as f:
                            meta = json.load(f)
                            candidates.append((entry, meta.get("timestamp", "")))
                    except Exception:
                        pass
            if candidates:
                candidates.sort(key=lambda x: x[1], reverse=True)
                return candidates[0][0]
        except Exception:
            pass
        return None

    def _get_path(self, layer: str) -> str:
        return os.path.join(self._storage_dir, f"{layer}_memory.json")

    def _save_layer(self, layer: str) -> None:
        """Serializes and saves a memory layer atomically using the temp-swap pattern with JSON-validation check."""
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

            # Verification of written JSON validity to prevent half-written/empty corruption
            with open(temp_filepath, "r", encoding="utf-8") as f:
                json.load(f)

            # Atomic swap
            os.replace(temp_filepath, filepath)

            # Persist the serialized layer in the universal artifact store.
            # Legacy JSON remains as a compatibility mirror until migration is complete.
            artifact = self._artifact_store.put(
                json.dumps(data, indent=4).encode("utf-8"),
                media_type="application/json",
                filename=f"{layer}_memory.json",
                metadata={
                    "producer": "MarketMemorySystem",
                    "layer": layer,
                    "legacy_path": filepath,
                },
            )
            manifest = self._load_artifact_manifest()
            manifest[layer] = artifact["id"]
            tmp_manifest = self._artifact_manifest_path + ".tmp"
            with open(tmp_manifest, "w", encoding="utf-8") as manifest_file:
                json.dump(
                    manifest,
                    manifest_file,
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
            os.replace(tmp_manifest, self._artifact_manifest_path)
        except Exception:
            if os.path.exists(temp_filepath):
                try:
                    os.remove(temp_filepath)
                except OSError:
                    pass

    def _load_artifact_manifest(self) -> Dict[str, str]:
        if not os.path.exists(self._artifact_manifest_path):
            return {}
        try:
            with open(self._artifact_manifest_path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            return {str(k): str(v) for k, v in raw.items()}
        except (OSError, ValueError, TypeError):
            return {}

    def get_artifact_manifest(self) -> Dict[str, str]:
        """Return universal-storage artifact IDs for Brain memory layers."""
        return dict(self._load_artifact_manifest())

    def load_all(self) -> None:
        """
        Loads all four memory layers from disk with robust error-recovery.
        In case of reading errors or corrupt files, it triggers automatic snapshot recovery.
        """
        import logging
        logger = logging.getLogger("yartrader_memory")

        with self._lock:
            # 1. Load Events
            events_path = self._get_path("events")
            if os.path.exists(events_path):
                try:
                    with open(events_path, "r", encoding="utf-8") as f:
                        raw = json.load(f)
                        self.events = [MarketEvent.from_dict(d) for d in raw]
                        self._event_keys = {(e.symbol, e.start_time, e.end_time, e.timeframe) for e in self.events}
                except Exception as e:
                    logger.error(f"Corruption detected in events_memory.json: {e}")
                    self._attempt_emergency_recovery("events", e)

            # 2. Load Experiences
            exp_path = self._get_path("experiences")
            if os.path.exists(exp_path):
                try:
                    with open(exp_path, "r", encoding="utf-8") as f:
                        raw = json.load(f)
                        self.experiences = {eid: ExperienceMemory.from_dict(d) for eid, d in raw.items()}
                except Exception as e:
                    logger.error(f"Corruption detected in experiences_memory.json: {e}")
                    self._attempt_emergency_recovery("experiences", e)

            # 3. Load Patterns
            patterns_path = self._get_path("patterns")
            if os.path.exists(patterns_path):
                try:
                    with open(patterns_path, "r", encoding="utf-8") as f:
                        raw = json.load(f)
                        self.patterns = {pid: PatternMemory.from_dict(d) for pid, d in raw.items()}
                except Exception as e:
                    logger.error(f"Corruption detected in patterns_memory.json: {e}")
                    self._attempt_emergency_recovery("patterns", e)

            # 4. Load Concepts
            concepts_path = self._get_path("concepts")
            if os.path.exists(concepts_path):
                try:
                    with open(concepts_path, "r", encoding="utf-8") as f:
                        raw = json.load(f)
                        self.concepts = {cid: ConceptMemory.from_dict(d) for cid, d in raw.items()}
                except Exception as e:
                    logger.error(f"Corruption detected in concepts_memory.json: {e}")
                    self._attempt_emergency_recovery("concepts", e)

    def _attempt_emergency_recovery(self, failed_layer: str, exception: Exception) -> None:
        """
        Disaster recovery policy: tries to restore from the latest valid snapshot.
        Wiping or starting from scratch is strictly forbidden.
        """
        import logging
        logger = logging.getLogger("yartrader_memory")
        logger.critical(f"[CRITICAL_MEMORY_PROTECTION] Failed to load {failed_layer} memory: {exception}")

        latest_tag = self.get_latest_snapshot_tag()
        if latest_tag:
            logger.info(f"Attempting emergency recovery from latest valid snapshot: {latest_tag}")
            try:
                # To prevent infinite recursion, we temporally backup the corrupt file,
                # restore the latest snapshot, and load.
                corrupt_file = self._get_path(failed_layer)
                backup_corrupt = corrupt_file + ".corrupt"
                if os.path.exists(corrupt_file):
                    os.replace(corrupt_file, backup_corrupt)

                snapshot_dir = os.path.join(self._storage_dir, "snapshots", latest_tag)
                src_path = os.path.join(snapshot_dir, f"{failed_layer}_memory.json")
                if os.path.exists(src_path):
                    import shutil
                    shutil.copy2(src_path, corrupt_file)

                    # Reload the failed layer
                    with open(corrupt_file, "r", encoding="utf-8") as f:
                        raw = json.load(f)
                        if failed_layer == "events":
                            self.events = [MarketEvent.from_dict(d) for d in raw]
                        elif failed_layer == "experiences":
                            self.experiences = {eid: ExperienceMemory.from_dict(d) for eid, d in raw.items()}
                        elif failed_layer == "patterns":
                            self.patterns = {pid: PatternMemory.from_dict(d) for pid, d in raw.items()}
                        elif failed_layer == "concepts":
                            self.concepts = {cid: ConceptMemory.from_dict(d) for cid, d in raw.items()}
                    logger.info(f"Successfully recovered {failed_layer} memory from snapshot {latest_tag}")
                    return
            except Exception as rec_err:
                logger.critical(f"Emergency recovery failed to restore {failed_layer}: {rec_err}")

        # If no snapshot exists or restore failed, raise the error to alert SRE/DevOps
        raise RuntimeError(f"Memory layer {failed_layer} is corrupt, and emergency recovery was unable to restore any valid state.") from exception
