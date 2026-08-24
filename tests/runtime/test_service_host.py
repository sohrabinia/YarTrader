import pytest
import threading
import time
from unittest.mock import MagicMock, patch
from app.workers.service import YarTraderServiceHost
from app.core.config import ProductionConfig

def test_service_host_initialization():
    config = ProductionConfig()
    host = YarTraderServiceHost(config=config)
    assert host.is_running is False
    assert host.fastapi_ready is False
    assert host.last_error is None

def test_service_host_socket_readiness_probe_failure():
    config = ProductionConfig()
    config.api_host = "127.0.0.1"
    config.api_port = 59999 # Port unlikely to be open
    host = YarTraderServiceHost(config=config)

    # Truthfulness test: socket probe fails if nothing is listening
    readiness = host._verify_uvicorn_readiness(timeout_sec=0.2)
    assert readiness is False
    assert host.fastapi_ready is False

def test_service_host_lifecycle():
    config = ProductionConfig()
    config.workers_research = False # Disable heavy worker threads during unit test
    host = YarTraderServiceHost(config=config)

    # Mock uvicorn server run to prevent actual blocking
    mock_server = MagicMock()
    mock_server.started = True

    with patch("uvicorn.Server", return_value=mock_server):
        host.start()
        assert host.is_running is True
        assert host.fastapi_ready is True

        host.stop()
        assert host.is_running is False
        assert host.fastapi_ready is False
