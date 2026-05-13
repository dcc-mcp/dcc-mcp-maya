"""Gateway promotion must marshal onto the Maya main thread (interactive)."""

from __future__ import annotations

import sys
import types
from unittest.mock import MagicMock, patch

import pytest


def _install_fake_maya(*, batch: bool) -> None:
    cmds_mod = types.ModuleType("maya.cmds")
    cmds_mod.about = MagicMock(return_value=batch)
    utils_mod = types.ModuleType("maya.utils")
    utils_mod.executeInMainThreadWithResult = MagicMock(side_effect=lambda fn: fn())
    maya_mod = types.ModuleType("maya")
    sys.modules["maya"] = maya_mod
    sys.modules["maya.cmds"] = cmds_mod
    sys.modules["maya.utils"] = utils_mod


def _teardown_fake_maya() -> None:
    for name in ("maya.utils", "maya.cmds", "maya"):
        sys.modules.pop(name, None)


@pytest.fixture
def fake_maya_interactive():
    _install_fake_maya(batch=False)
    yield
    _teardown_fake_maya()


@pytest.fixture
def fake_maya_batch():
    _install_fake_maya(batch=True)
    yield
    _teardown_fake_maya()


def test_upgrade_to_gateway_uses_main_thread_when_interactive(fake_maya_interactive) -> None:
    from dcc_mcp_core.server_base import DccServerBase

    from dcc_mcp_maya.server import MayaMcpServer

    utils_mod = sys.modules["maya.utils"]
    server = MayaMcpServer(port=0)
    try:
        with patch.object(DccServerBase, "_upgrade_to_gateway", return_value=True) as parent:
            assert server._upgrade_to_gateway() is True
        parent.assert_called_once()
        utils_mod.executeInMainThreadWithResult.assert_called_once()
    finally:
        try:
            server.stop()
        except Exception:  # noqa: BLE001
            pass


def test_upgrade_to_gateway_skips_main_thread_marshal_in_batch(fake_maya_batch) -> None:
    from dcc_mcp_core.server_base import DccServerBase

    from dcc_mcp_maya.server import MayaMcpServer

    utils_mod = sys.modules["maya.utils"]
    server = MayaMcpServer(port=0)
    try:
        with patch.object(DccServerBase, "_upgrade_to_gateway", return_value=True) as parent:
            assert server._upgrade_to_gateway() is True
        parent.assert_called_once()
        utils_mod.executeInMainThreadWithResult.assert_not_called()
    finally:
        try:
            server.stop()
        except Exception:  # noqa: BLE001
            pass
