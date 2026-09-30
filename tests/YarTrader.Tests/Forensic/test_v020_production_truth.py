import pathlib
import unittest


class TestV020ProductionTruth(unittest.TestCase):
    def test_canonical_runtime_has_no_shadow_dependency(self):
        root = pathlib.Path(__file__).resolve().parents[3]
        production_files = [
            root / "app/workers/research_worker.py",
            root / "src/Application/Runtime/research_runtime.py",
            root / "src/Application/Services/user_api_router.py",
            root / "src/Application/Services/admin_api_router.py",
            root / "src/Application/Services/web_dashboard.py",
        ]
        for path in production_files:
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("src.ShadowTrading", text, str(path))
            self.assertNotIn("PredictiveShadowEngine", text, str(path))

    def test_customer_auth_ui_contains_no_password_field(self):
        path = pathlib.Path(__file__).resolve().parents[3] / "trader-terminal/src/App.jsx"
        text = path.read_text(encoding="utf-8")
        self.assertNotIn('type="password"', text)
        self.assertIn("/api/auth/google", text)


if __name__ == "__main__":
    unittest.main()

