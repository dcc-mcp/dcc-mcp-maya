"""Integration tests for gateway cursor-safe tool-name wiring."""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from dcc_mcp_maya import _env
from dcc_mcp_maya.server import MayaMcpServer


@pytest.fixture
def clean_env():
    preserved = {k: v for k, v in os.environ.items() if not k.startswith("DCC_MCP_")}
    with patch.dict(os.environ, preserved, clear=True):
        yield


def test_env_cursor_safe_zero_disables(clean_env):
    os.environ[_env.ENV_CURSOR_SAFE_TOOL_NAMES] = "0"
    server = MayaMcpServer(port=0, gateway_port=0)
    assert server._config.gateway_cursor_safe_tool_names is False


def test_explicit_cursor_safe_kwarg_overrides(clean_env):
    os.environ[_env.ENV_CURSOR_SAFE_TOOL_NAMES] = "0"
    server = MayaMcpServer(port=0, gateway_port=0, cursor_safe_tool_names=True)
    assert server._config.gateway_cursor_safe_tool_names is True


def test_cursor_safe_unset_keeps_inner_default(clean_env):
    from dcc_mcp_core import McpHttpConfig

    baseline = McpHttpConfig().gateway_cursor_safe_tool_names
    server = MayaMcpServer(port=0, gateway_port=0)
    assert server._config.gateway_cursor_safe_tool_names == baseline
