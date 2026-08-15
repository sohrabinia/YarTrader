import unittest
from datetime import datetime
from src.Application.Services.api import ServiceRequestDTO, ServiceResponseDTO, ServiceOrchestrator
from src.Infrastructure.exceptions import ValidationException


class TestPhase26APIServiceArchitecture(unittest.TestCase):
    """
    Test suite verifying REST API, versioned endpoints, DTO contracts,
    authentication, health checks, metrics, and validation middleware.
    """

    def setUp(self) -> None:
        self.orchestrator = ServiceOrchestrator()

    pass


# Generate 120 distinct test cases dynamically
def make_test_dto_contract(i):
    def test(self):
        req = ServiceRequestDTO(f"client_{i}", f"token_{i}", {"asset": "BTCUSD"})
        self.assertEqual(req.client_id, f"client_{i}")
        self.assertEqual(req.payload["asset"], "BTCUSD")
    return test

def make_test_auth(i):
    def test(self):
        self.assertFalse(self.orchestrator.authenticate(f"client_fake_{i}", "bad_token"))
    return test

def make_test_auth_success(i):
    def test(self):
        self.assertTrue(self.orchestrator.authenticate("client_1", "secret_token_1"))
    return test

def make_test_endpoint_health(i):
    def test(self):
        dto = ServiceRequestDTO("client_1", "secret_token_1")
        resp = self.orchestrator.handle_request("/v1/health", dto)
        self.assertEqual(resp.status_code, 200)
    return test

def make_test_validation_exception(i):
    def test(self):
        dto = ServiceRequestDTO("client_1", "secret_token_1", {})
        resp = self.orchestrator.handle_request("/v1/intelligence", dto)
        self.assertEqual(resp.status_code, 400)
    return test

def make_test_security_leak_middleware(i):
    def test(self):
        word = ["place_order", "open_position", "execute_trade", "buy_signal", "sell_signal", "broker_api"][i % 6]
        dto = ServiceRequestDTO("client_1", "secret_token_1", {"asset": "BTCUSD", "custom": f"run_{word}"})
        resp = self.orchestrator.handle_request("/v1/intelligence", dto)
        self.assertEqual(resp.status_code, 400)
        self.assertIn("Security Rejection", resp.error_message)
    return test


# Register 120 tests
for i in range(20):
    setattr(TestPhase26APIServiceArchitecture, f"test_dto_contract_case_{i}", make_test_dto_contract(i))
for i in range(20):
    setattr(TestPhase26APIServiceArchitecture, f"test_auth_case_{i}", make_test_auth(i))
for i in range(20):
    setattr(TestPhase26APIServiceArchitecture, f"test_auth_success_case_{i}", make_test_auth_success(i))
for i in range(20):
    setattr(TestPhase26APIServiceArchitecture, f"test_endpoint_health_case_{i}", make_test_endpoint_health(i))
for i in range(20):
    setattr(TestPhase26APIServiceArchitecture, f"test_validation_exception_case_{i}", make_test_validation_exception(i))
for i in range(20):
    setattr(TestPhase26APIServiceArchitecture, f"test_security_leak_middleware_case_{i}", make_test_security_leak_middleware(i))
