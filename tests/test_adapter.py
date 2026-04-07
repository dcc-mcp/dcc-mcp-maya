"""Tests for MayaAdapter (runs outside Maya, uses mock)."""

# Import built-in modules
from unittest.mock import MagicMock
from unittest.mock import patch

# Import third-party modules
import pytest


class TestMayaAdapterInit:
    """Test MayaAdapter initialization without a real Maya connection."""

    def test_import(self):
        """MayaAdapter can be imported."""
        from dcc_mcp_maya.adapter import MayaAdapter
        assert MayaAdapter is not None

    def test_default_dcc_name(self):
        """MayaAdapter sets dcc_name to 'maya'."""
        from dcc_mcp_maya.adapter import MayaAdapter
        with patch("dcc_mcp_ipc.adapter.dcc.get_client", return_value=None):
            adapter = MayaAdapter()
        assert adapter.dcc_name == "maya"

    def test_custom_host_port(self):
        """MayaAdapter stores custom host and port."""
        from dcc_mcp_maya.adapter import MayaAdapter
        with patch("dcc_mcp_ipc.adapter.dcc.get_client", return_value=None):
            adapter = MayaAdapter(host="192.168.1.10", port=18812)
        assert adapter.host == "192.168.1.10"
        assert adapter.port == 18812

    def test_not_connected_returns_error_result(self):
        """Methods return failure ActionResultModel when not connected."""
        from dcc_mcp_maya.adapter import MayaAdapter
        with patch("dcc_mcp_ipc.adapter.dcc.get_client", return_value=None):
            adapter = MayaAdapter()
        adapter.client = None

        result = adapter.get_scene_info()
        assert result.success is False
        assert "connect" in result.message.lower() or "connect" in (result.error or "").lower()
