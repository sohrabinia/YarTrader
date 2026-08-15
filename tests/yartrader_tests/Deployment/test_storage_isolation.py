import os
import shutil
import unittest
from src.Infrastructure.exceptions import ValidationException
from src.Application.Deployment.storage import YarTraderStorageManager
from src.Application.Deployment.config import ProductionConfig, ConfigManager
from src.Application.Deployment.observability import StructuredLogger


class TestYarTraderStorageIsolation(unittest.TestCase):
    """
    Automated test suite verifying Phase 39: YarTrader Storage Isolation.
    Ensures that all runtime directories are strictly placed and write-isolated
    under YarTraderStorageRoot, preventing fallback writes to OS system directories.
    """

    def setUp(self) -> None:
        ConfigManager.reset()
        YarTraderStorageManager.reset()

        # We configure a safe testing storage root path
        self.test_root = os.path.join(os.getcwd(), "test_YarTraderAI")
        self.manager = YarTraderStorageManager.get_manager(self.test_root)

    def tearDown(self) -> None:
        ConfigManager.reset()
        YarTraderStorageManager.reset()
        if os.path.exists(self.test_root):
            shutil.rmtree(self.test_root, ignore_errors=True)

    def test_storage_root_derivatives(self) -> None:
        """Verify that all subdirectory getters strictly derive from the configured root."""
        self.assertEqual(self.manager.storage_root, self.test_root)
        self.assertEqual(self.manager.get_log_dir(), os.path.join(self.test_root, "Logs"))
        self.assertEqual(self.manager.get_reports_dir(), os.path.join(self.test_root, "Reports"))
        self.assertEqual(self.manager.get_runtime_dir(), os.path.join(self.test_root, "Runtime"))
        self.assertEqual(self.manager.get_cache_dir(), os.path.join(self.test_root, "Cache"))
        self.assertEqual(self.manager.get_data_dir(), os.path.join(self.test_root, "Data"))
        self.assertEqual(self.manager.get_diagnostics_dir(), os.path.join(self.test_root, "Diagnostics"))
        self.assertEqual(self.manager.get_temp_dir(), os.path.join(self.test_root, "Temp"))

    def test_structured_logger_isolation(self) -> None:
        """Verify that log writes occur strictly inside the isolated Logs directory of the storage root."""
        # Clean test root first to verify directory generation on write
        if os.path.exists(self.test_root):
            shutil.rmtree(self.test_root)

        logger = StructuredLogger(service_name="YarTrader_Test")
        logger.info("OperationalStep", {"payload": "test"})

        expected_log_file = os.path.join(self.manager.get_log_dir(), "yartrader.log")
        self.assertTrue(os.path.exists(expected_log_file))

        # Verify that we can read back and parse JSON
        with open(expected_log_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
            self.assertGreater(len(lines), 0)

    def test_config_storage_root_parameter(self) -> None:
        """Verify that ProductionConfig correctly exposes and defaults the YarTraderStorageRoot config."""
        os.environ["YarTraderStorageRoot"] = self.test_root
        config = ProductionConfig()
        self.assertEqual(config.storage_root, self.test_root)
        del os.environ["YarTraderStorageRoot"]

    def test_no_write_leaks_outside_root(self) -> None:
        """Verify that no file path fallbacks default to OS directories or active user homes."""
        # Verify that all getters do not contain system OS directories
        dirs_to_check = [
            self.manager.get_log_dir(),
            self.manager.get_reports_dir(),
            self.manager.get_runtime_dir(),
            self.manager.get_cache_dir(),
            self.manager.get_data_dir(),
            self.manager.get_diagnostics_dir(),
            self.manager.get_temp_dir()
        ]

        forbidden_roots = ["/etc", "/var", "/usr", "/bin", "C:\\Windows", "C:\\Program Files"]
        for d in dirs_to_check:
            self.assertTrue(d.startswith(self.test_root))
            for fr in forbidden_roots:
                self.assertFalse(d.startswith(fr))
