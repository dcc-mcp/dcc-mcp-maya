"""Gateway election smoke tests under real mayapy (Rust server + Python thread).

These complement ``tests/test_gateway_promotion_maya.py`` (mocked maya) and
``dcc-mcp-core/tests/test_gateway_election_e2e.py`` (HTTP fake gateway): here we
assert that a normal ``MayaMcpServer.start()`` with a unique ``gateway_port``
actually wires ``DccGatewayElection`` and reports it as running.

The background-thread test guards the regression where ``DccGatewayElection``
invokes ``_upgrade_to_gateway`` from a daemon thread: interactive Maya must
marshal onto the main thread via ``maya.utils.executeInMainThreadWithResult``.

Run::

    mayapy -m pytest tests/e2e/test_gateway_failover_e2e.py -v
"""

from __future__ import annotations

import socket
import threading
from pathlib import Path
from unittest.mock import patch

import pytest


def _free_tcp_port() -> int:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])
    finally:
        s.close()


@pytest.mark.e2e
def test_gateway_election_thread_starts_with_isolated_registry(tmp_path: Path) -> None:
    """A lone mayapy instance should start failover election when gateway_port > 0."""
    import maya.standalone  # noqa: PLC0415

    maya.standalone.initialize(name="python")

    from dcc_mcp_maya.server import MayaMcpServer

    reg = tmp_path / "registry"
    reg.mkdir(parents=True, exist_ok=True)
    gw_port = _free_tcp_port()

    server = MayaMcpServer(
        port=0,
        gateway_port=gw_port,
        registry_dir=str(reg),
        enable_gateway_failover=True,
    )
    server.register_builtin_actions(minimal=True)
    try:
        server.start()
        status = server.get_gateway_election_status()
        assert status["enabled"] is True
        assert status["running"] is True
        assert isinstance(server.is_gateway, bool)
    finally:
        server.stop()


@pytest.mark.e2e
def test_maya_upgrade_from_background_thread_invokes_main_thread_utils(tmp_path: Path) -> None:
    """Regression: interactive Maya marshals promotion onto the main thread."""
    import maya.standalone  # noqa: PLC0415

    maya.standalone.initialize(name="python")

    import maya.cmds as cmds  # noqa: PLC0415
    from dcc_mcp_core.server_base import DccServerBase

    from dcc_mcp_maya.server import MayaMcpServer

    reg = tmp_path / "registry-mt"
    reg.mkdir(parents=True, exist_ok=True)

    server = MayaMcpServer(
        port=0,
        gateway_port=0,
        registry_dir=str(reg),
        enable_gateway_failover=False,
    )
    server.register_builtin_actions(minimal=True)
    server.start()
    try:
        batch = bool(cmds.about(batch=True))
        barrier = threading.Barrier(2)

        def _bg() -> None:
            barrier.wait()
            server._upgrade_to_gateway()

        with patch.object(DccServerBase, "_upgrade_to_gateway", return_value=True) as parent:
            with patch("maya.utils.executeInMainThreadWithResult", side_effect=lambda fn: fn()) as mu_exec:
                t = threading.Thread(target=_bg, name="promotion-probe", daemon=True)
                t.start()
                barrier.wait()
                t.join(timeout=10.0)
                assert not t.is_alive()

        assert parent.call_count == 1
        if batch:
            mu_exec.assert_not_called()
        else:
            mu_exec.assert_called_once()
    finally:
        server.stop()
