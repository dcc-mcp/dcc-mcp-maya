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
    def test_setup_executor_is_noop(self):
        """_setup_executor is a no-op placeholder in v0.12.10+ (DeferredExecutor removed)."""
        srv_mod = _import_server()
        server = srv_mod.MayaMcpServer(port=0, enable_main_thread_executor=False)
        server._setup_executor()
        # executor stays None — DeferredExecutor no longer exists in dcc_mcp_core._core
        assert server._executor is None

    def test_server_with_executor_enabled_no_crash(self):
        """enable_main_thread_executor=True with mocked Maya should not crash."""
        srv_mod = _import_server()
        server = srv_mod.MayaMcpServer(port=0, enable_main_thread_executor=True)
        assert server is not None


class TestPollCallback:
    def test_setup_poll_callback_disabled(self):
        """If enable_main_thread_executor=False, _setup_poll_callback is a no-op."""
        srv_mod = _import_server()
        server = srv_mod.MayaMcpServer(port=0, enable_main_thread_executor=False)
        server._setup_poll_callback()  # should not raise

    def test_setup_poll_callback_with_maya_available(self):
        """With maya.utils available and executor enabled, callback installs."""
        srv_mod = _import_server()
        server = srv_mod.MayaMcpServer(port=0, enable_main_thread_executor=True)
        server._setup_poll_callback()
        import maya.utils

        assert maya.utils.executeDeferred.called

    def test_setup_poll_callback_exception_handled(self):
        """If maya.utils raises, the error is caught."""
        srv_mod = _import_server()
        server = srv_mod.MayaMcpServer(port=0, enable_main_thread_executor=True)
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
        handle = server.start()  # noqa: F841
        assert server.mcp_url is not None
        assert "127.0.0.1" in server.mcp_url
        server.stop()
