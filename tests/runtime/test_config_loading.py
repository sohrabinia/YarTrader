import os
import unittest
from app.core.config import ProductionConfig, ConfigurationException

class TestConfigLoading(unittest.TestCase):
    def setUp(self) -> None:
        self.old_env = dict(os.environ)
        for key in list(os.environ.keys()):
            if "TRADEYAR_" in key or "RG_" in key:
                del os.environ[key]

    def tearDown(self) -> None:
        os.environ.clear()
        os.environ.update(self.old_env)

    def test_default_config_loading(self):
        """Verifies that default config is loaded correctly with standard values."""
        config = ProductionConfig()
        self.assertEqual(config.api_host, "127.0.0.1")
        self.assertEqual(config.api_port, 8000)
        self.assertEqual(config.mt5_symbol, "XAUUSD")
        self.assertEqual(config.mt5_timeframe, "H1")
        self.assertEqual(config.logging_level, "INFO")
        self.assertIsNone(config.mt5_password)
        self.assertIsNone(config.api_key)

    def test_env_override(self):
        """Checks that environment variables properly override default parameters."""
        os.environ["TRADEYAR_API_HOST"] = "0.0.0.0"
        os.environ["TRADEYAR_API_PORT"] = "9090"
        os.environ["TRADEYAR_MT5_SYMBOL"] = "GBPUSD"
        os.environ["TRADEYAR_LOG_LEVEL"] = "DEBUG"
        os.environ["TRADEYAR_MT5_PASSWORD"] = "secret_pass_123"
        os.environ["TRADEYAR_API_KEY"] = "api_key_777"

        config = ProductionConfig()
        self.assertEqual(config.api_host, "0.0.0.0")
        self.assertEqual(config.api_port, 9090)
        self.assertEqual(config.mt5_symbol, "GBPUSD")
        self.assertEqual(config.logging_level, "DEBUG")
        self.assertEqual(config.mt5_password, "secret_pass_123")
        self.assertEqual(config.api_key, "api_key_777")

    def test_invalid_port_validation(self):
        """Verifies that setting an invalid port raises a validation error."""
        os.environ["TRADEYAR_API_PORT"] = "-1"
        with self.assertRaises(ConfigurationException):
            ProductionConfig()

    def test_invalid_confidence_threshold(self):
        """Verifies that confidence threshold boundaries are validated."""
        os.environ["TRADEYAR_AI_CONFIDENCE_THRESHOLD"] = "150"
        with self.assertRaises(ConfigurationException):
            ProductionConfig()
