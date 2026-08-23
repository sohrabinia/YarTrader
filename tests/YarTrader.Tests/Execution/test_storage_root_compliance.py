import os
import pytest
from src.Application.Deployment.storage import YarTraderStorageManager


def test_storage_root_compliance():
    mgr = YarTraderStorageManager.get_manager()
    storage_root = mgr.storage_root
    assert os.path.exists(storage_root) or storage_root.startswith("/tmp/")
    assert mgr.get_logs_dir().startswith(storage_root)
    assert mgr.get_reports_dir().startswith(storage_root)
