import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional


class ConversationEngine:
    """
    Market Intelligence Conversation Layer & Analyst Brain Interface.
    A secure, read-only conversational research interface allowing humans to
    query the Market Discovery Brain. Strictly forbids memory or state updates.
    """
    def __init__(self) -> None:
        self.audit_logs: List[Dict[str, Any]] = []

    def handle_user_query(
        self,
        question: str,
        memory: Any,  # MemorySystem
        hyp_engine: Any,  # HypothesisEngine
        cur_engine: Optional[Any] = None,  # CuriosityEngine
        judge_brain: Optional[Any] = None  # IndependentJudgeBrain
    ) -> Dict[str, Any]:
        """
        Parses questions and retrieves evidence-based responses directly from read-only memory layers.
        Logs every question and output answer in an immutable audit trail.
        """
        q_lower = question.lower()
        timestamp = datetime.now()
        requested_sources = []

        # Default State: Insufficient data/Unknown
        observation = "Unknown - Evidence is currently insufficient to formulate an understanding."
        evidence_desc = "None"
        historical_samples = 0
        success_failure_dist = "N/A"
        confidence_level = "0.0% (Unknown State)"
        contradicting_evidence = "None"
        unknown_factors = "Data is currently insufficient. More observation is required."
        understanding_status = "UNKNOWN"
        evidence_ids = []

        # 1. Topic: Learned Concepts
        if "learned concepts" in q_lower or "what did you understand" in q_lower:
            requested_sources.append("ConceptMemory")
            if memory.concept_memory:
                concepts_list = list(memory.concept_memory.values())
                c = concepts_list[-1]  # Get latest
                observation = f"Discovered concept: {c.Description}"
                evidence_desc = f"Concept ID: {c.ConceptId}"
                historical_samples = c.ValidatedSamples
                success_failure_dist = f"Validated Samples: {c.ValidatedSamples}"
                confidence_level = f"{int(c.Confidence * 100)}%"
                contradicting_evidence = "No validated contradictions exist in current memory."
                unknown_factors = "Behavior under unvalidated highly volatile regimes remains untested."
                understanding_status = "VALIDATED"
                evidence_ids = [c.ConceptId]
            else:
                unknown_factors = "No concepts have been validated yet. Evidence is insufficient. System remains in default 'Unknown' state."

        # 2. Topic: Discovered Patterns
        elif "discovered patterns" in q_lower or "what patterns" in q_lower:
            requested_sources.append("PatternMemory")
            if memory.patterns_memory:
                patterns_list = list(memory.patterns_memory.values())
                p = patterns_list[-1]
                observation = f"Discovered price run signature: {p.Signature}"
                evidence_desc = f"Pattern ID: {p.PatternId}"
                historical_samples = p.Occurrences
                success_failure_dist = f"Continuation: {p.ContinuationCount}, Reversal: {p.ReversalCount}"
                confidence_level = f"{int(p.continuation_probability * 100)}%"
                contradicting_evidence = f"Pattern was rejected in {p.ReversalCount} occurrences."
                unknown_factors = "Structural timeframe nested relationships remain unproven."
                understanding_status = "TESTING" if p.Occurrences < 5 else "OBSERVED"
                evidence_ids = [p.PatternId]
            else:
                unknown_factors = "No recurring structural patterns have been recorded yet."

        # 3. Topic: Experience & Failures (Self-Criticism)
        elif "mistakes" in q_lower or "where are you wrong" in q_lower or "what failed" in q_lower:
            requested_sources.append("ExperienceMemory")
            failures = [exp for exp in memory.experience_memory if exp.FinalResult == "LOSS"]
            if failures:
                f = failures[-1]
                observation = f"Identified learning mistake during simulated context: {f.SituationSignature}"
                evidence_desc = f"Experience ID: {f.MemoryId}, Lesson: {f.Lesson}"
                historical_samples = len(failures)
                success_failure_dist = f"Losses: {len(failures)} / Total Trades: {len(memory.experience_memory)}"
                confidence_level = "N/A"
                contradicting_evidence = "Trade resulted in direct loss due to SL boundary breach."
                unknown_factors = f"Pattern correction underway for signature {f.SituationSignature}."
                understanding_status = "REJECTED"
                evidence_ids = [f.MemoryId]
            else:
                unknown_factors = "No learning failures or losses have been recorded in Experience Memory yet."

        # 4. Topic: Curiosity & Research Questions
        elif "curiosity" in q_lower or "research questions" in q_lower:
            requested_sources.append("CuriosityQuestion")
            if cur_engine and cur_engine.questions:
                q = cur_engine.questions[-1]
                observation = f"Active research question: {q.TargetBehavior}"
                evidence_desc = f"Question ID: {q.QuestionId}, Gap: {q.UnderstandingGap}"
                historical_samples = len(cur_engine.questions)
                success_failure_dist = "N/A"
                confidence_level = "Unknown (Awaiting empirical tests)"
                contradicting_evidence = "None"
                unknown_factors = q.UnderstandingGap
                understanding_status = "HYPOTHESIS"
                evidence_ids = [q.QuestionId]
            else:
                unknown_factors = "No active curiosity questions are currently formulated."

        # 5. Topic: Active Hypotheses
        elif "hypotheses" in q_lower or "active hypothesis" in q_lower:
            requested_sources.append("HypothesisEngine")
            if hyp_engine and hyp_engine.hypotheses:
                h = list(hyp_engine.hypotheses.values())[-1]
                observation = f"Active hypothesis: {h.Description}"
                evidence_desc = f"Hypothesis ID: {h.HypothesisId}, Evidence count: {len(h.EvidenceObservationIds)}"
                historical_samples = len(h.EvidenceObservationIds)
                success_failure_dist = f"Evidence count: {len(h.EvidenceObservationIds)}"
                confidence_level = f"{int(h.Confidence * 100)}%"
                contradicting_evidence = "Contradicting out-of-sample data is under active test cycle."
                unknown_factors = "OOS repeatability remains unproven."
                understanding_status = h.Status
                evidence_ids = [h.HypothesisId]
            else:
                unknown_factors = "No active scientific hypotheses are currently in testing state."

        # Assemble evidence-based structured response
        answer = {
            "Observation": observation,
            "Evidence": evidence_desc,
            "Historical Samples": historical_samples,
            "Success / Failure Distribution": success_failure_dist,
            "Confidence Level": confidence_level,
            "Contradicting Evidence": contradicting_evidence,
            "Unknown Factors": unknown_factors,
            "Current Understanding Status": understanding_status,
            "EvidenceIds": evidence_ids
        }

        # Log into the secure audit trail
        self.audit_logs.append({
            "User Question": question,
            "Timestamp": timestamp.isoformat(),
            "Requested Data Sources": requested_sources,
            "Generated Answer": answer,
            "Evidence References": evidence_ids
        })

        return answer
