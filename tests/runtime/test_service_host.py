import pytest
import threading
import time
import socket
from unittest.mock import MagicMock, patch
from app.workers.service import YarTraderServiceHost
from app.core.config import ProductionConfig

def test_service_host_initialization():
    config = ProductionConfig()
    host = YarTraderServiceHost(config=config)
    assert host.is_running is False
    assert host.fastapi_ready is False
    assert host.last_error is None

def test_service_host_duplicate_startup_prevention():
    config = ProductionConfig()
    config.workers_research = False
    host = YarTraderServiceHost(config=config)

    mock_server = MagicMock()
    mock_server.started = True

    with patch("uvicorn.Server", return_value=mock_server):
        host.start()
        assert host.is_running is True
        initial_thread = host.uvicorn_thread

        # Attempt duplicate startup while already running
        host.start()
        # Thread and server instance must remain identical (no duplicate processes/threads spawned)
        assert host.uvicorn_thread is initial_thread

        host.stop()
        assert host.is_running is False

def test_service_host_socket_readiness_probe_failure():
    config = ProductionConfig()
    config.api_host = "127.0.0.1"
    config.api_port = 59999 # Port unlikely to be open
    host = YarTraderServiceHost(config=config)

    # Truthfulness test: socket probe fails if nothing is listening
    readiness = host._verify_uvicorn_readiness(timeout_sec=0.2)
    assert readiness is False
    assert host.fastapi_ready is False

def test_service_host_port_binding_failure():
    config = ProductionConfig()
    config.workers_research = False
    config.api_host = "127.0.0.1"
    config.api_port = 59998
    host = YarTraderServiceHost(config=config)

    # Simulate Uvicorn throwing an exception during run
    mock_server = MagicMock()
    def _raise_bind_error():
        raise OSError("Address already in use / Port binding failure")

    mock_server.run = _raise_bind_error
    mock_server.started = False

    with patch("uvicorn.Server", return_value=mock_server):
        host.start()
        # Allow background thread to execute crash handler
        time.sleep(0.1)
        assert host.fastapi_ready is False
        assert host.last_error is not None
        assert "Port binding failure" in host.last_error or "Address already in use" in host.last_error

        host.stop()

def test_service_host_shutdown_and_restart():
    config = ProductionConfig()
    config.workers_research = False
    host = YarTraderServiceHost(config=config)

    mock_server = MagicMock()
    mock_server.started = True

    with patch("uvicorn.Server", return_value=mock_server):
        # 1. First Start
        host.start()
        assert host.is_running is True
        assert host.fastapi_ready is True

        # 2. Stop
        host.stop()
        assert host.is_running is False
        assert host.fastapi_ready is False

        # 3. Restart
        host.start()
        assert host.is_running is True
        assert host.fastapi_ready is True

        host.stop()
        assert host.is_running is False

def test_service_host_truthfulness_rule():
    """Verifies that is_running=True (service state) does NOT automatically imply fastapi_ready=True."""
    config = ProductionConfig()
    config.workers_research = False
    host = YarTraderServiceHost(config=config)

    # Server started is False
    mock_server = MagicMock()
    mock_server.started = False

    with patch("uvicorn.Server", return_value=mock_server):
        # Mock probe to return False (simulating port 8000 not bound)
        with patch.object(host, "_verify_uvicorn_readiness", return_value=False):
            host.start()
            assert host.is_running is True
            assert host.fastapi_ready is False # Service is running, but API is NOT ready
            host.stop()
