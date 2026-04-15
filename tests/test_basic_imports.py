"""Basic import and structure tests (no mayapy required)."""

import pytest


def test_gateway_election_imports():
    """Verify GatewayElection can be imported."""
    from dcc_mcp_maya.gateway_election import GatewayElection
    assert GatewayElection is not None


def test_hotreload_imports():
    """Verify MayaSkillHotReloader can be imported."""
    from dcc_mcp_maya.hotreload import MayaSkillHotReloader
    assert MayaSkillHotReloader is not None


def test_server_has_gateway_failover():
    """Verify MayaMcpServer accepts enable_gateway_failover parameter."""
    import inspect

    from dcc_mcp_maya.server import MayaMcpServer

    # Check __init__ signature
    sig = inspect.signature(MayaMcpServer.__init__)
    assert "enable_gateway_failover" in sig.parameters


def test_server_has_update_gateway_metadata():
    """Verify MayaMcpServer has update_gateway_metadata method."""
    from dcc_mcp_maya.server import MayaMcpServer

    assert hasattr(MayaMcpServer, "update_gateway_metadata")


def test_server_has_get_gateway_election_status():
    """Verify MayaMcpServer has get_gateway_election_status method."""
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


def test_gateway_election_attributes():
    """Verify GatewayElection has expected attributes and methods."""

    from dcc_mcp_maya.gateway_election import GatewayElection

    # Get all methods
    methods = [m for m in dir(GatewayElection) if not m.startswith("_")]

    assert "start" in methods
    assert "stop" in methods
    assert "is_running" in methods or "_is_running" in dir(GatewayElection)


def test_hotreload_attributes():
    """Verify MayaSkillHotReloader has expected methods."""

    from dcc_mcp_maya.hotreload import MayaSkillHotReloader

    methods = [m for m in dir(MayaSkillHotReloader) if not m.startswith("_")]

    assert "enable" in methods
    assert "disable" in methods
    assert "reload_now" in methods


def test_start_server_has_enable_gateway_failover():
    """Verify start_server() function accepts enable_gateway_failover parameter."""
    import inspect

    from dcc_mcp_maya import start_server

    sig = inspect.signature(start_server)
    assert "enable_gateway_failover" in sig.parameters
    assert sig.parameters["enable_gateway_failover"].default is True


def test_config_has_gateway_fields():
    """Verify McpHttpConfig supports gateway configuration."""
    from dcc_mcp_core import McpHttpConfig

    config = McpHttpConfig(port=8765)

    # Should have gateway-related fields
    assert hasattr(config, "gateway_port")
    assert hasattr(config, "registry_dir")
    assert hasattr(config, "dcc_type")
    assert hasattr(config, "dcc_version")
    assert hasattr(config, "scene")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
