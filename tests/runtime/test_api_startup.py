import unittest
from fastapi.testclient import TestClient
from src.Application.Services.web_dashboard import app

class TestApiStartup(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_dashboard_routes_exist(self):
        """Checks that key dashboard routing endpoints return 200 OK."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

        response = self.client.get("/v1/runtime")
        self.assertEqual(response.status_code, 200)

        response = self.client.get("/api/symbols")
        self.assertEqual(response.status_code, 200)
