"""Tests for dynamic scene and version metadata updates without restart."""

from __future__ import annotations

import time
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from dcc_mcp_maya.server import MayaMcpServer

pytestmark = pytest.mark.integration


class _Handle:
    def __init__(self) -> None:
        self.calls = []

    def update_scene(self, scene, version, documents, display_name):
        self.calls.append(
            {
                "scene": scene,
                "version": version,
                "documents": documents,
                "display_name": display_name,
            }
        )


def _server(scene="/path/to/initial_scene.ma", version="2025"):
    server = object.__new__(MayaMcpServer)
    server._dcc_name = "maya"
    server._config = SimpleNamespace(gateway_port=9765, scene=scene, dcc_version=version)
    server._handle = _Handle()
    return server


def test_scene_update_basic():
    """Scene metadata updates the live config and the running handle."""
    server = _server()

    assert server.update_gateway_metadata(scene="/path/to/new_scene.ma") is True

    assert server._config.scene == "/path/to/new_scene.ma"
    assert server._handle.calls[-1]["scene"] == "/path/to/new_scene.ma"


def test_version_update():
    """Version metadata can change without rebuilding the server."""
    server = _server(version="2025")

    assert server.update_gateway_metadata(version="2024") is True

    assert server._config.dcc_version == "2024"
    assert server._handle.calls[-1]["version"] == "2024"


def test_concurrent_scene_updates():
    """Multiple instances keep their own scene metadata isolated."""
    servers = [_server(scene=f"/path/to/scene_{i}.ma") for i in range(3)]

    for index, server in enumerate(servers):
        assert server.update_gateway_metadata(scene=f"/path/to/updated_scene_{index}.ma") is True

    assert [server._config.scene for server in servers] == [
        "/path/to/updated_scene_0.ma",
        "/path/to/updated_scene_1.ma",
        "/path/to/updated_scene_2.ma",
    ]


def test_scene_update_performance():
    """Metadata update is an in-process config/handle update, not a restart."""
    server = _server()

    start = time.perf_counter()
    result = server.update_gateway_metadata(scene="/path/to/test_scene.ma")
    elapsed_ms = (time.perf_counter() - start) * 1000

    assert result is True
    assert elapsed_ms < 100


def test_scene_update_no_restart_required():
    """The existing handle remains attached after a scene metadata update."""
    server = _server()
    original_handle = server._handle

    assert server.update_gateway_metadata(scene="/new/scene.ma") is True

    assert server._handle is original_handle
    assert server.is_running is True


def test_scene_update_visibility_latency():
    """The next gateway read sees the handle-published scene immediately in-process."""
    server = _server(scene="/path/to/initial.ma")
    gateway_client = MagicMock()
    gateway_client.list_instances.side_effect = lambda _dcc: [{"scene": server._config.scene}]

    start = time.perf_counter()
    assert server.update_gateway_metadata(scene="/path/to/updated_final.ma") is True
    instances = gateway_client.list_instances("maya")
    latency_ms = (time.perf_counter() - start) * 1000

    assert instances[0]["scene"] == "/path/to/updated_final.ma"
    assert latency_ms < 100
