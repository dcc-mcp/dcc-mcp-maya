"""Basic import and structure tests (no mayapy required)."""

import pytest


def test_gateway_election_importable_from_core():
    """GatewayElection moved to dcc_mcp_core.gateway_election (DccGatewayElection)."""
    from dcc_mcp_core.gateway_election import DccGatewayElection

    assert DccGatewayElection is not None


def test_hotreload_importable_from_core():
    """HotReloader moved to dcc_mcp_core.hotreload (DccSkillHotReloader)."""
    from dcc_mcp_core.hotreload import DccSkillHotReloader

    assert DccSkillHotReloader is not None


def test_server_has_gateway_failover():
    """Verify MayaMcpServer accepts enable_gateway_failover parameter."""
    import inspect

    from dcc_mcp_maya.server import MayaMcpServer

    sig = inspect.signature(MayaMcpServer.__init__)
    assert "enable_gateway_failover" in sig.parameters


def test_server_has_update_gateway_metadata():
    """Verify MayaMcpServer has update_gateway_metadata method (inherited)."""
    from dcc_mcp_maya.server import MayaMcpServer

    assert hasattr(MayaMcpServer, "update_gateway_metadata")


def test_server_has_get_gateway_election_status():
    """Verify MayaMcpServer has get_gateway_election_status method (inherited)."""
    from dcc_mcp_maya.server import MayaMcpServer

    assert hasattr(MayaMcpServer, "get_gateway_election_status")


def test_maya_instance_manager_imports():
    """Verify MayaInstanceManager can be imported."""
    from tests.fixtures.maya_instances import MayaInstanceConfig, MayaInstanceManager

    assert MayaInstanceManager is not None
    assert MayaInstanceConfig is not None


def test_gateway_test_client_imports():
    """Verify GatewayTestClient can be imported from conftest."""
    from tests.conftest import GatewayTestClient

    assert GatewayTestClient is not None


def test_gateway_election_attributes_on_core_class():
    """DccGatewayElection (core) has same start/stop interface."""
    from dcc_mcp_core.gateway_election import DccGatewayElection

    methods = [m for m in dir(DccGatewayElection) if not m.startswith("_")]

    assert "start" in methods
    assert "stop" in methods
    assert "is_running" in methods


def test_hotreload_attributes_on_core_class():
    """DccSkillHotReloader (core) has same enable/disable/reload_now interface."""
    from dcc_mcp_core.hotreload import DccSkillHotReloader

    methods = [m for m in dir(DccSkillHotReloader) if not m.startswith("_")]

    assert "enable" in methods
    assert "disable" in methods
    assert "reload_now" in methods


def test_start_server_has_enable_gateway_failover():
    """Verify start_server() forwards enable_gateway_failover through to MayaMcpServer.

    ``start_server`` is generated via ``dcc_mcp_core.factory.make_start_stop``
    and accepts arbitrary ``**kwargs`` forwarded to ``MayaMcpServer.__init__``.
    The gateway-failover keyword must therefore be accepted, and the Maya
    server constructor must still expose it with default ``True``.
    """
    import inspect

    from dcc_mcp_maya import start_server
    from dcc_mcp_maya.server import MayaMcpServer

    start_sig = inspect.signature(start_server)
    assert any(p.kind is inspect.Parameter.VAR_KEYWORD for p in start_sig.parameters.values()), (
        "start_server must accept **kwargs so gateway params pass through to MayaMcpServer"
    )

    srv_sig = inspect.signature(MayaMcpServer.__init__)
    assert "enable_gateway_failover" in srv_sig.parameters
    assert srv_sig.parameters["enable_gateway_failover"].default is True


def test_config_has_gateway_fields():
    """Verify McpHttpConfig supports gateway configuration."""
    from dcc_mcp_core import McpHttpConfig

    config = McpHttpConfig(port=8765)

    assert hasattr(config, "gateway_port")
    assert hasattr(config, "registry_dir")
    assert hasattr(config, "dcc_type")
    assert hasattr(config, "dcc_version")
    assert hasattr(config, "scene")


def test_maya_mcp_server_inherits_dcc_server_base():
    """MayaMcpServer must be a subclass of DccServerBase."""
    from dcc_mcp_core.server_base import DccServerBase

    from dcc_mcp_maya.server import MayaMcpServer

    assert issubclass(MayaMcpServer, DccServerBase)


def test_enable_hot_reload_on_server():
    """MayaMcpServer.enable_hot_reload is inherited from DccServerBase."""
    from dcc_mcp_maya.server import MayaMcpServer

    assert hasattr(MayaMcpServer, "enable_hot_reload")
    assert hasattr(MayaMcpServer, "disable_hot_reload")
    assert hasattr(MayaMcpServer, "is_hot_reload_enabled")
    assert hasattr(MayaMcpServer, "hot_reload_stats")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
