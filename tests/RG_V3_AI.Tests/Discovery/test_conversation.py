import unittest
from datetime import datetime
from src.Research.MarketAnalysis.Discovery.models import (
    ConceptMemory,
    PatternMemory,
    ExperienceMemory,
    Hypothesis,
    CuriosityQuestion
)
from src.Research.MarketAnalysis.Discovery.brain import (
    MemorySystem,
    HypothesisEngine,
    CuriosityEngine
)
from src.Research.MarketAnalysis.Discovery.conversation import ConversationEngine


class TestMarketIntelligenceConversationLayer(unittest.TestCase):
    """
    Automated unit and integration test suite verifying the Conversation Layer,
    evidence-based structured response generation, anti-hallucination,
    traceability back to audit IDs, and strict read-only security limits.
    """

    def setUp(self) -> None:
        self.memory = MemorySystem()
        self.hyp_engine = HypothesisEngine()
        self.cur_engine = CuriosityEngine()
        self.chat = ConversationEngine()
        self.now = datetime.now()

    # 1. Test Unknown Handling
    def test_unknown_state_returned_when_evidence_is_insufficient(self) -> None:
        # Default state - no data saved in memory yet
        ans = self.chat.handle_user_query(
            question="What did you understand from market behavior?",
            memory=self.memory,
            hyp_engine=self.hyp_engine,
            cur_engine=self.cur_engine
        )
        self.assertEqual(ans["Current Understanding Status"], "UNKNOWN")
        self.assertIn("Evidence is currently insufficient", ans["Observation"])
        self.assertIn("insufficient", ans["Unknown Factors"])

    # 2. Test Evidence-Based Responses for Learned Concepts
    def test_concepts_query_returns_evidence_and_traceability(self) -> None:
        # Seed memory with a validated concept
        concept = ConceptMemory(
            ConceptId="concept-101",
            Description="Gold US session expansion behavior repeats",
            Confidence=0.85,
            ValidatedSamples=1240,
            LastValidatedAt=self.now
        )
        self.memory.save_concept(concept)

        ans = self.chat.handle_user_query(
            question="What learned concepts have you discovered?",
            memory=self.memory,
            hyp_engine=self.hyp_engine,
            cur_engine=self.cur_engine
        )

        self.assertEqual(ans["Current Understanding Status"], "VALIDATED")
        self.assertEqual(ans["Confidence Level"], "85%")
        self.assertEqual(ans["Historical Samples"], 1240)
        self.assertEqual(ans["EvidenceIds"], ["concept-101"])
        self.assertIn("concept-101", ans["Evidence"])

    # 3. Test Discovered Patterns Query
    def test_patterns_query_returns_correct_evidence(self) -> None:
        p = PatternMemory(PatternId="pat-202", Signature="upward_12")
        p.Occurrences = 50
        p.ContinuationCount = 35
        p.ReversalCount = 15
        self.memory.save_pattern(p)

        ans = self.chat.handle_user_query(
            question="What patterns have you discovered?",
            memory=self.memory,
            hyp_engine=self.hyp_engine,
            cur_engine=self.cur_engine
        )

        self.assertEqual(ans["Current Understanding Status"], "OBSERVED")
        self.assertEqual(ans["Confidence Level"], "70%")  # 35 / 50 = 70%
        self.assertEqual(ans["Historical Samples"], 50)
        self.assertEqual(ans["EvidenceIds"], ["pat-202"])

    # 4. Test Self Criticism and Mistakes Queries
    def test_self_criticism_and_losses_query(self) -> None:
        exp = ExperienceMemory(
            MemoryId="exp-loss-99", Timestamp=self.now,
            SituationSignature="downward_6", Decision="BUY",
            MaxFavorableMovement=2.0, MaxAdverseMovement=15.0,
            FinalResult="LOSS", Lesson="Buying during extreme point run is hazard"
        )
        self.memory.save_experience(exp)

        ans = self.chat.handle_user_query(
            question="Where are you wrong and what failed?",
            memory=self.memory,
            hyp_engine=self.hyp_engine,
            cur_engine=self.cur_engine
        )

        self.assertEqual(ans["Current Understanding Status"], "REJECTED")
        self.assertEqual(ans["EvidenceIds"], ["exp-loss-99"])
        self.assertIn("exp-loss-99", ans["Evidence"])

    # 5. Test Audit Trail Logging and Traceability
    def test_conversation_audit_logs_integrity(self) -> None:
        self.chat.handle_user_query(
            question="What are your curiosity research questions?",
            memory=self.memory,
            hyp_engine=self.hyp_engine,
            cur_engine=self.cur_engine
        )

        self.assertEqual(len(self.chat.audit_logs), 1)
        log = self.chat.audit_logs[0]
        self.assertEqual(log["User Question"], "What are your curiosity research questions?")
        self.assertIsNotNone(log["Timestamp"])
        self.assertIsNotNone(log["Generated Answer"])

    # 6. Test Security Enforcement (Strictly Read-Only)
    def test_conversation_layer_strict_read_only_safety(self) -> None:
        # Confirms the conversation interface has absolutely no modify or write operations
        self.assertFalse(hasattr(self.chat, "order_send"))
        self.assertFalse(hasattr(self.chat, "trade_send"))
        self.assertFalse(hasattr(self.chat, "positions_get"))
        self.assertFalse(hasattr(self.chat, "positions_modify"))
        self.assertFalse(hasattr(self.chat, "positions_close"))
        self.assertFalse(hasattr(self.chat, "save_concept"))
        self.assertFalse(hasattr(self.chat, "save_experience"))
