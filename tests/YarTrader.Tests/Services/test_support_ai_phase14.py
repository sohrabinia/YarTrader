import unittest
from unittest.mock import patch
from datetime import datetime
from fastapi.testclient import TestClient

from src.Application.Services.web_dashboard import app
from src.Application.Support.support_ai_engine import SupportAIEngine, SupportQuery, SupportResponse
from src.Application.Services.support_ai_service import SupportAIService
from src.Infrastructure.exceptions import ValidationException


class TestSupportAIPhase14(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)
        self.engine = SupportAIEngine()
        self.service = SupportAIService(support_engine=self.engine)

    def test_1_valid_query_validation(self) -> None:
        query = SupportQuery(message="  سلام YarTrader  ", symbol="XAUUSD")
        query.validate()
        self.assertEqual(query.message, "  سلام YarTrader  ")

    def test_2_empty_query_raises_validation_exception(self) -> None:
        query = SupportQuery(message="   ")
        with self.assertRaises(ValidationException):
            query.validate()

    def test_3_overlength_query_raises_validation_exception(self) -> None:
        long_msg = "x" * 1001
        query = SupportQuery(message=long_msg)
        with self.assertRaises(ValidationException):
            query.validate()

    def test_4_unauthenticated_balance_query_returns_limit(self) -> None:
        query = SupportQuery(message="موجودی حساب من چقدر است؟", lang="fa")
        resp = self.engine.generate_response(query)
        self.assertEqual(resp.status, "UNAUTHENTICATED_ACCESS_LIMIT")
        self.assertIn("اطلاعات حساب کاربری در دسترس نیست", resp.response_text)

    def test_5_authenticated_balance_query_with_data(self) -> None:
        user_ctx = {"authenticated": True, "balance": 500000}
        query = SupportQuery(message="موجودی حساب", lang="fa", user_context=user_ctx)
        resp = self.engine.generate_response(query)
        self.assertEqual(resp.status, "ACCOUNT_CONTEXT_PROVIDED")
        self.assertIn("500000", resp.response_text)

    def test_6_authenticated_balance_query_without_balance_data(self) -> None:
        user_ctx = {"authenticated": True, "balance": None}
        query = SupportQuery(message="balance check", lang="en", user_context=user_ctx)
        resp = self.engine.generate_response(query)
        self.assertEqual(resp.status, "DATA_UNAVAILABLE_LIMIT")

    def test_7_governance_foundation_explanation(self) -> None:
        foundation_data = {
            "governance": {"governance_state": "APPROVED", "evidence_quality": "HIGH"}
        }
        query = SupportQuery(message="وضعیت حاکمیت چیست؟", symbol="XAUUSD", lang="fa")
        resp = self.engine.generate_response(query, foundation_data=foundation_data)
        self.assertEqual(resp.status, "GOVERNANCE_EXPLAINED")
        self.assertIn("APPROVED", resp.response_text)

    def test_8_intelligence_foundation_explanation(self) -> None:
        foundation_data = {
            "intelligence": {"decision_readiness_state": "READY", "context_sufficiency_score": 0.95}
        }
        query = SupportQuery(message="هوش ارزیابی چطور است؟", lang="fa")
        resp = self.engine.generate_response(query, foundation_data=foundation_data)
        self.assertEqual(resp.status, "INTELLIGENCE_EXPLAINED")
        self.assertIn("READY", resp.response_text)

    def test_9_general_why_trade_explanation(self) -> None:
        query = SupportQuery(message="چرا معامله باز شد؟", strategy="SPIKE", lang="fa")
        resp = self.engine.generate_response(query)
        self.assertEqual(resp.status, "GENERAL_EXPLANATION_PROVIDED")
        self.assertIn("SPIKE", resp.response_text)

    def test_10_learning_concept_explanation(self) -> None:
        query = SupportQuery(message="سیستم چه چیزی یاد می‌گیرد؟", lang="fa")
        resp = self.engine.generate_response(query)
        self.assertEqual(resp.status, "GENERAL_EXPLANATION_PROVIDED")
        self.assertIn("Phase 11", resp.response_text)

    def test_11_why_no_trade_explanation(self) -> None:
        query = SupportQuery(message="چرا معامله نکرد؟", lang="fa")
        resp = self.engine.generate_response(query)
        self.assertEqual(resp.status, "GENERAL_EXPLANATION_PROVIDED")
        self.assertIn("Phase 16", resp.response_text)

    def test_12_english_language_response(self) -> None:
        query = SupportQuery(message="Why this decision?", strategy="TREND", lang="en")
        resp = self.engine.generate_response(query)
        self.assertEqual(resp.status, "GENERAL_EXPLANATION_PROVIDED")
        self.assertIn("TREND strategy evaluates market structure", resp.response_text)

    def test_13_service_process_chat_message_valid(self) -> None:
        result = self.service.process_chat_message(message="سلام YarTrader", lang="fa")
        self.assertIn("response", result)
        self.assertIn("status", result)
        self.assertIn("timestamp", result)

    def test_14_service_invalid_empty_message_raises(self) -> None:
        with self.assertRaises(ValidationException):
            self.service.process_chat_message(message="")

    def test_15_api_post_assistant_anonymous(self) -> None:
        resp = self.client.post("/api/chat/assistant?lang=fa", json={"message": "سیستم چطور کار می‌کند؟"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("response", data)
        self.assertIn("status", data)
        self.assertIn("timestamp", data)

    def test_16_api_post_assistant_privacy_gating(self) -> None:
        resp = self.client.post("/api/chat/assistant?lang=fa", json={"message": "موجودی حساب من چقدره؟"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "UNAUTHENTICATED_ACCESS_LIMIT")

    def test_17_no_order_execution_capability(self) -> None:
        # Verify SupportAIEngine has no order submission methods
        self.assertFalse(hasattr(self.engine, "execute_trade"))
        self.assertFalse(hasattr(self.engine, "place_order"))

    def test_18_no_wallet_ledger_mutation(self) -> None:
        # Verify SupportAIEngine does not mutate balance or ledger files
        self.assertFalse(hasattr(self.engine, "mutate_ledger"))
        self.assertFalse(hasattr(self.engine, "add_credit"))

    def test_19_no_payment_subscription_mutation(self) -> None:
        # Verify SupportAIEngine cannot initiate subscriptions or webhooks
        self.assertFalse(hasattr(self.engine, "create_subscription"))

    def test_20_no_strategy_engine_mutation(self) -> None:
        # Verify SupportAIEngine cannot modify strategy parameters
        self.assertFalse(hasattr(self.engine, "update_strategy_config"))

    def test_21_support_query_immutability(self) -> None:
        query = SupportQuery(message="test")
        with self.assertRaises(AttributeError):
            query.message = "modified"  # type: ignore

    def test_22_support_response_to_dict_keys(self) -> None:
        resp = SupportResponse(response_text="ok", status="TEST")
        d = resp.to_dict()
        self.assertEqual(set(d.keys()), {"response", "status", "timestamp"})

    def test_23_api_chat_assistant_preserves_schema(self) -> None:
        resp = self.client.post("/api/chat/assistant", json={"message": "test contract"})
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertIn("response", body)
        self.assertIn("status", body)
        self.assertIn("timestamp", body)

    def test_24_fallback_default_explanation(self) -> None:
        query = SupportQuery(message="کلمات نامشخص ۱۲۳۴۵", lang="fa")
        resp = self.engine.generate_response(query)
        self.assertEqual(resp.status, "GENERAL_EXPLANATION_PROVIDED")
        self.assertIn("YarTrader", resp.response_text)

    def test_25_end_to_end_support_ai_path(self) -> None:
        user_ctx = {"authenticated": True, "balance": 10000}
        res = self.service.process_chat_message(message="موجودی", user_context=user_ctx)
        self.assertEqual(res["status"], "ACCOUNT_CONTEXT_PROVIDED")
        self.assertIn("10000", res["response"])


if __name__ == "__main__":
    unittest.main()
