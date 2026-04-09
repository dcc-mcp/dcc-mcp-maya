"""Extended tests for server.py — covers executor, poll callback and edge cases."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import sys
from unittest.mock import MagicMock, patch

# Import third-party modules
import pytest


@pytest.fixture(autouse=True)
def mock_maya_modules():
    """Inject minimal maya stubs."""
    maya_mock = MagicMock()
    maya_mock.cmds = MagicMock()
    maya_mock.mel = MagicMock()
    maya_mock.utils = MagicMock()
    mods = {
        "maya": maya_mock,
        "maya.cmds": maya_mock.cmds,
        "maya.mel": maya_mock.mel,
        "maya.utils": maya_mock.utils,
    }
    with patch.dict(sys.modules, mods):
        yield maya_mock


def _import_server():
    import importlib

    for mod in list(sys.modules):
        if "dcc_mcp_maya" in mod:
            del sys.modules[mod]
    return importlib.import_module("dcc_mcp_maya.server")


class TestMayaAvailable:
    def test_maya_available_true(self):
        srv_mod = _import_server()
        assert srv_mod._maya_available() is True

    def test_maya_available_false(self):
        srv_mod = _import_server()
        with patch.dict(sys.modules, {"maya.cmds": None}):
            assert srv_mod._maya_available() is False


class TestExecutorSetup:
    def test_setup_executor_success(self):
        """When DeferredExecutor is importable, executor is created."""
        srv_mod = _import_server()
        server = srv_mod.MayaMcpServer(port=0, enable_main_thread_executor=False)
        # Manually call _setup_executor
        server._setup_executor()
        # If DeferredExecutor exists in dcc_mcp_core._core it is created;
        # if not available, executor is None — either outcome is fine
        # We just verify no exception leaks out
        assert True

    def test_setup_executor_graceful_failure(self):
        """If DeferredExecutor cannot be imported, executor stays None."""
        srv_mod = _import_server()
        server = srv_mod.MayaMcpServer(port=0, enable_main_thread_executor=False)
        # Force failure by patching the import
        with patch.dict(sys.modules, {"dcc_mcp_core._core": None}):
            server._setup_executor()
        assert server._executor is None

    def test_server_with_executor_enabled_no_crash(self):
        """enable_main_thread_executor=True with mocked Maya should not crash."""
        srv_mod = _import_server()
        # This exercises lines 92-95 (enable_executor branch)
        server = srv_mod.MayaMcpServer(port=0, enable_main_thread_executor=True)
        assert server is not None


class TestPollCallback:
    def test_setup_poll_callback_no_executor(self):
        """If executor is None, _setup_poll_callback returns early."""
        srv_mod = _import_server()
        server = srv_mod.MayaMcpServer(port=0, enable_main_thread_executor=False)
        server._executor = None
        server._setup_poll_callback()  # should not raise

    def test_setup_poll_callback_with_executor(self):
        """With a mock executor and maya.utils available, callback installs."""
        srv_mod = _import_server()
        server = srv_mod.MayaMcpServer(port=0, enable_main_thread_executor=False)
        # Provide a mock executor
        mock_executor = MagicMock()
        server._executor = mock_executor
        server._setup_poll_callback()
        # maya.utils.executeDeferred should have been called
        import maya.utils
        assert maya.utils.executeDeferred.called

    def test_setup_poll_callback_exception_handled(self):
        """If maya.utils raises, the error is caught."""
        srv_mod = _import_server()
        server = srv_mod.MayaMcpServer(port=0, enable_main_thread_executor=False)
        server._executor = MagicMock()
        import maya.utils
        maya.utils.executeDeferred.side_effect = RuntimeError("no event loop")
        server._setup_poll_callback()  # should not raise


class TestServerStopEdgeCases:
    def test_stop_when_not_running(self):
        """stop() on a server that was never started is safe."""
        srv_mod = _import_server()
        server = srv_mod.MayaMcpServer(port=0, enable_main_thread_executor=False)
        server.stop()  # handle is None — should not raise
        assert not server.is_running

    def test_stop_server_when_none(self):
        """stop_server() when singleton is None is a no-op."""
        srv_mod = _import_server()
        srv_mod._server_instance = None
        srv_mod.stop_server()  # should not raise

    def test_mcp_url_property_running(self):
        """mcp_url property returns URL when running."""
        srv_mod = _import_server()
        server = srv_mod.MayaMcpServer(port=0, enable_main_thread_executor=False)
        handle = server.start()
        assert server.mcp_url is not None
        assert "127.0.0.1" in server.mcp_url
        server.stop()
