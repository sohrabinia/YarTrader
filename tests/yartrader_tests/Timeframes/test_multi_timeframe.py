import unittest
from fastapi.testclient import TestClient
from src.Application.Services.web_dashboard import app
from src.Intelligence.Execution.alignment import MultiTimeframeAlignmentEngine
from src.Application.Runtime.research_runtime import ResearchRuntime
from src.Core.timeframes import SUPPORTED_TIMEFRAMES

class TestMultiTimeframeSupport(unittest.TestCase):
    """
    Standard Engineering test cases validating complete Multi-Timeframe support (v8.1).
    Ensures that all layers support M1, M5, M15, H1, H4, D1, W1, MN1 cleanly.
    """

    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_registry_all_required_timeframes_exist(self) -> None:
        # 1. Assert directly against the single source-of-truth registry (Test 1)
        expected_tfs = ["M1", "M5", "M15", "H1", "H4", "D1", "W1", "MN1"]
        for tf in expected_tfs:
            self.assertIn(tf, SUPPORTED_TIMEFRAMES)
            self.assertIn("minutes", SUPPORTED_TIMEFRAMES[tf])
            self.assertIn("category", SUPPORTED_TIMEFRAMES[tf])

        # 2. Check that Health API exposes all 8 official timeframes
        response = self.client.get("/api/v1/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertIn("timeframes", data)
        timeframes = data["timeframes"]
        for tf in expected_tfs:
            self.assertIn(tf, timeframes)
            self.assertEqual(timeframes[tf], "ready")

        # 3. Assert all background workers are Running (Test 5)
        self.assertIn("subsystems", data)
        subsystems = data["subsystems"]
        self.assertEqual(subsystems["research_worker"], "Running")
        self.assertEqual(subsystems["intelligence_worker"], "Running")
        self.assertEqual(subsystems["shadow_worker"], "Running")

    def test_alignment_sorting_weights(self) -> None:
        engine = MultiTimeframeAlignmentEngine()
        # Verify custom and standard weights sorting
        sorted_frames = sorted(
            ["H1", "MN1", "M5", "D1", "W1", "H4", "M15", "M1"],
            key=engine._frame_sort_weight,
            reverse=True
        )
        self.assertEqual(sorted_frames, ["MN1", "W1", "D1", "H4", "H1", "M15", "M5", "M1"])

    def test_research_runtime_all_timeframes_execution(self) -> None:
        """
        Verify that ResearchRuntime and the feature extraction pipeline support
        all 8 timeframes (M1, M5, M15, H1, H4, D1, W1, MN1) successfully (Test 2 & 3).
        """
        timeframes = ["M1", "M5", "M15", "H1", "H4", "D1", "W1", "MN1"]
        for tf in timeframes:
            # Create a research runtime context
            runtime = ResearchRuntime(
                symbol="XAUUSD",
                timeframe=tf,
                evidence_dir="test_timeframe_logs"
            )
            # Run the analytical pipeline and assert success
            res = runtime.run_once()
            self.assertIsNotNone(res)
            self.assertIn("feature_set", res.Findings)
            # Assert feature generation completeness
            self.assertIn("observation_summary", res.Findings)

            # Verify Phase 9 logging outputs structure
            po = res.Findings.get("pipeline_outputs", {})
            self.assertIn("smart_interpretation", po)
