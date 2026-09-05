import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from src.Application.Services.web_dashboard import app, generate_active_ohlcv_candles

class TestExecutionIntelligenceEndpoints(unittest.TestCase):
    """
    Integration testing suite for the Execution Intelligence REST endpoints.
    Verifies schemas, routing paths, parameters, and successful JSON serialization
    under both online (mocked real candles) and offline (degraded) conditions.
    """

    def setUp(self) -> None:
        self.client = TestClient(app)
        self.sample_candles = generate_active_ohlcv_candles("XAUUSD", "H1")

    def test_get_execution_plans(self) -> None:
        with patch("src.Application.Services.web_dashboard.fetch_production_market_candles", return_value=self.sample_candles):
            response = self.client.get("/api/execution/plans?symbol=XAUUSD&timeframe=H1&lang=fa")
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertIn("action", data)
            self.assertIn("entry", data)
            self.assertIn("stop_loss", data)
            self.assertIn("take_profit", data)
            self.assertIn("reasoning", data)

    def test_get_execution_plans_degraded_when_offline(self) -> None:
        with patch("src.Application.Services.web_dashboard.fetch_production_market_candles", return_value=[]):
            response = self.client.get("/api/execution/plans?symbol=XAUUSD&timeframe=H1&lang=fa")
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data["action"], "WAIT")
            self.assertEqual(data["decision"], "NO_TRADE")
            self.assertEqual(data["data_mode"], "UNAVAILABLE")

    def test_get_execution_confidence(self) -> None:
        with patch("src.Application.Services.web_dashboard.fetch_production_market_candles", return_value=self.sample_candles):
            response = self.client.get("/api/execution/confidence?symbol=XAUUSD&timeframe=H1")
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data["symbol"], "XAUUSD")
            self.assertIn("confidence", data)

    def test_get_execution_reasoning(self) -> None:
        with patch("src.Application.Services.web_dashboard.fetch_production_market_candles", return_value=self.sample_candles):
            response = self.client.get("/api/execution/reasoning?symbol=XAUUSD&timeframe=H1&lang=en")
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertIn("reasoning", data)
            self.assertIsInstance(data["reasoning"], list)

    def test_get_structure_map(self) -> None:
        with patch("src.Application.Services.web_dashboard.fetch_production_market_candles", return_value=self.sample_candles):
            response = self.client.get("/api/structure/map?symbol=XAUUSD&timeframe=H1")
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data["symbol"], "XAUUSD")
            self.assertIn("swings", data)
            self.assertIn("order_blocks", data)
            self.assertIn("fair_value_gaps", data)

    def test_get_structure_alignment(self) -> None:
        with patch("src.Application.Services.web_dashboard.fetch_production_market_candles", return_value=self.sample_candles):
            response = self.client.get("/api/structure/alignment?symbol=XAUUSD")
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data["symbol"], "XAUUSD")
            self.assertIn("alignment", data)
            self.assertIn("confidence", data)

    def test_get_structure_narrative(self) -> None:
        with patch("src.Application.Services.web_dashboard.fetch_production_market_candles", return_value=self.sample_candles):
            response = self.client.get("/api/structure/narrative?symbol=XAUUSD&timeframe=H1")
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertIn("state", data)
            self.assertIn("trend", data)

    def test_get_liquidity_map(self) -> None:
        with patch("src.Application.Services.web_dashboard.fetch_production_market_candles", return_value=self.sample_candles):
            response = self.client.get("/api/liquidity/map?symbol=XAUUSD&timeframe=H1")
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertIn("resting_bsl", data)
            self.assertIn("resting_ssl", data)

    def test_get_liquidity_events(self) -> None:
        with patch("src.Application.Services.web_dashboard.fetch_production_market_candles", return_value=self.sample_candles):
            response = self.client.get("/api/liquidity/events?symbol=XAUUSD&timeframe=H1")
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertIn("sweeps", data)
            self.assertIn("voids", data)

    def test_get_pattern_similarity(self) -> None:
        with patch("src.Application.Services.web_dashboard.fetch_production_market_candles", return_value=self.sample_candles):
            response = self.client.get("/api/pattern/similarity?symbol=XAUUSD&timeframe=H1")
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertIn("similar_pattern_found", data)
            self.assertIn("best_match", data)

    def test_get_portfolio_risk(self) -> None:
        response = self.client.get("/api/portfolio/risk")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("portfolio_heat_pct", data)
        self.assertIn("approved", data)

    def test_get_portfolio_exposure(self) -> None:
        response = self.client.get("/api/portfolio/exposure")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("total_exposure", data)
        self.assertIn("asset_concentrations_pct", data)
