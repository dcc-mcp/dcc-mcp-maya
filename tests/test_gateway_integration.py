"""Tests for MayaMcpServer gateway integration (dcc-mcp-core v0.12.22+).

Covers:
- gateway_port parameter → McpHttpConfig.gateway_port set
- registry_dir / dcc_version / scene propagation
- DCC_MCP_GATEWAY_PORT / DCC_MCP_REGISTRY_DIR env var fallback
- gateway_port=0 (disabled) → McpHttpConfig.gateway_port NOT set
- is_gateway property delegates to handle.is_gateway
- gateway_url returns correct URL or None
- start_server() passes all new params through
"""

# Import future modules
from __future__ import annotations

# Import built-in modules
import importlib
import sys
from unittest.mock import MagicMock, patch

# ── helpers ────────────────────────────────────────────────────────────────────


def _import_server():
    """Fresh import of server module (clears cached dcc_mcp_maya modules)."""
    for mod in list(sys.modules):
        if "dcc_mcp_maya" in mod:
            del sys.modules[mod]
    return importlib.import_module("dcc_mcp_maya.server")


def _make_maya_mock():
    maya_mock = MagicMock()
    maya_mock.cmds = MagicMock()
    return {
        "maya": maya_mock,
        "maya.cmds": maya_mock.cmds,
        "maya.mel": MagicMock(),
        "maya.utils": MagicMock(),
    }


# ── McpHttpConfig gateway_port propagation ────────────────────────────────────


class TestGatewayPortConfig:
    """McpHttpConfig.gateway_port is set when gateway_port > 0."""

    def test_gateway_port_set_on_config(self):
        srv_mod = _import_server()
        options = srv_mod.MayaServerOptions(port=0, gateway_port=9765).to_core_options()

        assert options.gateway.port == 9765

    def test_dcc_type_set_to_maya_when_gateway_enabled(self):
        srv_mod = _import_server()
        options = srv_mod.MayaServerOptions(port=0, gateway_port=9765).to_core_options()

        assert options.dcc_name == "maya"

    def test_gateway_port_zero_does_not_set_config(self):
        """gateway_port=0 disables gateway binding in the core options."""
        srv_mod = _import_server()
        options = srv_mod.MayaServerOptions(port=0, gateway_port=0).to_core_options()

        assert options.gateway.port == 0

    def test_dcc_version_set_when_provided(self):
        srv_mod = _import_server()
        options = srv_mod.MayaServerOptions(port=0, gateway_port=9765, dcc_version="2025").to_core_options()

        assert options.gateway.dcc_version == "2025"

    def test_scene_set_when_provided(self):
        srv_mod = _import_server()
        options = srv_mod.MayaServerOptions(port=0, gateway_port=9765, scene="/proj/shot.ma").to_core_options()

        assert options.gateway.scene == "/proj/shot.ma"

    def test_registry_dir_set_when_provided(self):
        srv_mod = _import_server()
        options = srv_mod.MayaServerOptions(port=0, gateway_port=9765, registry_dir="/tmp/reg").to_core_options()

        assert options.gateway.registry_dir == "/tmp/reg"

    def test_dcc_version_not_set_when_none(self):
        """dcc_version=None remains absent from the gateway metadata."""
        srv_mod = _import_server()
        options = srv_mod.MayaServerOptions(port=0, gateway_port=9765).to_core_options()

        assert options.gateway.dcc_version is None


# ── Environment variable fallback ─────────────────────────────────────────────


class TestGatewayEnvVars:
    def test_env_var_gateway_port_used_when_param_is_none(self):
        srv_mod = _import_server()
        env = {"DCC_MCP_GATEWAY_PORT": "9765"}
        with patch.dict("os.environ", env, clear=False):
            options = srv_mod.MayaServerOptions(port=0).to_core_options()

        assert options.gateway.port == 9765

    def test_explicit_param_overrides_env_var(self):
        srv_mod = _import_server()
        env = {"DCC_MCP_GATEWAY_PORT": "8888"}
        with patch.dict("os.environ", env, clear=False):
            options = srv_mod.MayaServerOptions(port=0, gateway_port=9765).to_core_options()

        assert options.gateway.port == 9765

    def test_env_var_zero_disables_gateway(self):
        srv_mod = _import_server()
        env = {"DCC_MCP_GATEWAY_PORT": "0"}
        with patch.dict("os.environ", env, clear=False):
            options = srv_mod.MayaServerOptions(port=0).to_core_options()

        assert options.gateway.port == 0

    def test_registry_dir_env_var_used_when_param_is_none(self):
        srv_mod = _import_server()
        env = {"DCC_MCP_GATEWAY_PORT": "9765", "DCC_MCP_REGISTRY_DIR": "/tmp/myreg"}
        with patch.dict("os.environ", env, clear=False):
            options = srv_mod.MayaServerOptions(port=0).to_core_options()

        assert options.gateway.registry_dir == "/tmp/myreg"


# ── is_gateway / gateway_url properties ───────────────────────────────────────


class TestGatewayProperties:
    def _make_server_with_handle(self, is_gateway_val, gateway_port=9765):
        with patch.dict(sys.modules, _make_maya_mock()):
            srv_mod = _import_server()
            mock_config = MagicMock()
            mock_config.gateway_port = gateway_port
            mock_server = MagicMock()
            with patch("dcc_mcp_core.McpHttpConfig", return_value=mock_config):
                with patch("dcc_mcp_core.create_skill_server", return_value=mock_server):
                    server = srv_mod.MayaMcpServer(port=0, gateway_port=gateway_port)

        mock_handle = MagicMock()
        mock_handle.is_gateway = is_gateway_val
        server._handle = mock_handle
        server._config.gateway_port = gateway_port  # Re-assert after __init__ may reset it
        return server

    def test_is_gateway_true_when_handle_is_gateway(self):
        server = self._make_server_with_handle(True)
        assert server.is_gateway is True

    def test_is_gateway_false_when_handle_is_not_gateway(self):
        server = self._make_server_with_handle(False)
        assert server.is_gateway is False

    def test_is_gateway_false_when_no_handle(self):
        with patch.dict(sys.modules, _make_maya_mock()):
            srv_mod = _import_server()
            mock_config = MagicMock()
            mock_server = MagicMock()
            with patch("dcc_mcp_core.McpHttpConfig", return_value=mock_config):
                with patch("dcc_mcp_core.create_skill_server", return_value=mock_server):
                    server = srv_mod.MayaMcpServer(port=0, gateway_port=9765)

        assert server.is_gateway is False

    def test_gateway_url_returns_url_when_is_gateway(self):
        server = self._make_server_with_handle(True, gateway_port=9765)
        assert server.gateway_url == "http://127.0.0.1:9765/mcp"

    def test_gateway_url_none_when_not_gateway(self):
        server = self._make_server_with_handle(False, gateway_port=9765)
        assert server.gateway_url is None

    def test_gateway_url_none_when_no_handle(self):
        with patch.dict(sys.modules, _make_maya_mock()):
            srv_mod = _import_server()
            mock_config = MagicMock()
            mock_server = MagicMock()
            with patch("dcc_mcp_core.McpHttpConfig", return_value=mock_config):
                with patch("dcc_mcp_core.create_skill_server", return_value=mock_server):
                    server = srv_mod.MayaMcpServer(port=0, gateway_port=9765)

        assert server.gateway_url is None


# ── start_server() parameter propagation ──────────────────────────────────────


class TestStartServerGatewayParams:
    def test_start_server_passes_gateway_port(self):
        with patch.dict(sys.modules, _make_maya_mock()):
            srv_mod = _import_server()
            mock_instance = MagicMock()
            mock_instance.is_running = False
            mock_instance.register_builtin_actions.return_value = mock_instance
            mock_instance.start.return_value = MagicMock()

            with patch.object(srv_mod, "MayaMcpServer", return_value=mock_instance) as mock_cls:
                with patch.object(srv_mod, "_server_instance", None):
                    srv_mod._instance_holder[0] = None
                    srv_mod.start_server(port=0, gateway_port=9765, dcc_version="2025")

        call_kwargs = mock_cls.call_args[1] if mock_cls.call_args[1] else {}
        assert call_kwargs.get("gateway_port") == 9765
        assert call_kwargs.get("dcc_version") == "2025"

    def test_start_server_passes_registry_dir_and_scene(self):
        with patch.dict(sys.modules, _make_maya_mock()):
            srv_mod = _import_server()
            mock_instance = MagicMock()
            mock_instance.is_running = False
            mock_instance.register_builtin_actions.return_value = mock_instance
            mock_instance.start.return_value = MagicMock()

            with patch.object(srv_mod, "MayaMcpServer", return_value=mock_instance) as mock_cls:
                with patch.object(srv_mod, "_server_instance", None):
                    srv_mod._instance_holder[0] = None
                    srv_mod.start_server(
                        port=0,
                        gateway_port=9765,
                        registry_dir="/tmp/reg",
                        scene="/proj/shot.ma",
                    )

        call_kwargs = mock_cls.call_args[1] if mock_cls.call_args[1] else {}
        assert call_kwargs.get("registry_dir") == "/tmp/reg"
        assert call_kwargs.get("scene") == "/proj/shot.ma"
