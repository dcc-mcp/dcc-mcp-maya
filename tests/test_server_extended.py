"""Extended tests for server.py — covers edge cases and lifecycle."""

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


class TestServerStopEdgeCases:
    def test_stop_when_not_running(self):
        """stop() on a server that was never started is safe."""
        srv_mod = _import_server()
        server = srv_mod.MayaMcpServer(port=0)
        server.stop()  # handle is None — should not raise
        assert not server.is_running

    def test_stop_server_when_none(self):
        """stop_server() when singleton is None is a no-op."""
        srv_mod = _import_server()
        # Fresh import yields a fresh closure-local holder set to ``None``;
        # calling stop_server must simply return without raising.
        srv_mod.stop_server()

    def test_mcp_url_property_running(self):
        """mcp_url property returns URL when running."""
        srv_mod = _import_server()
        server = srv_mod.MayaMcpServer(port=0)
        handle = server.start()  # noqa: F841
        assert server.mcp_url is not None
        assert "127.0.0.1" in server.mcp_url
        server.stop()
