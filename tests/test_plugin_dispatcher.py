"""Tests for plugin host-dispatcher resolution (PIP-2570)."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import sys
import types
from unittest.mock import MagicMock, patch

# Import third-party modules
import pytest

from dcc_mcp_maya._plugin_dispatcher import (
    PluginDispatcherError,
    resolve_plugin_host_startup,
)


class TestResolvePluginHostStartup:
    def test_uses_core_queue_dispatcher_when_callable(self):
        dispatcher_instance = MagicMock(name="queue-dispatcher")
        host_mod = types.ModuleType("dcc_mcp_core.host")
        host_mod.BlockingDispatcher = MagicMock(name="BlockingDispatcher")
        host_mod.QueueDispatcher = MagicMock(return_value=dispatcher_instance)

        with patch.dict(
            sys.modules,
            {
                "dcc_mcp_core.host": host_mod,
            },
        ):
            startup = resolve_plugin_host_startup(is_batch=False)

        assert startup.dispatcher is dispatcher_instance
        assert startup.host is not None
        assert startup.ui_pump is None
        assert startup.backend == "core-rust"
        host_mod.QueueDispatcher.assert_called_once_with()

    def test_falls_back_when_core_dispatcher_is_none(self):
        host_mod = types.ModuleType("dcc_mcp_core.host")
        host_mod.BlockingDispatcher = MagicMock(name="BlockingDispatcher")
        host_mod.QueueDispatcher = None

        ui_dispatcher = MagicMock(name="MayaUiDispatcher")
        ui_pump = MagicMock(name="MayaUiPump")

        with patch.dict(sys.modules, {"dcc_mcp_core.host": host_mod}), patch(
            "dcc_mcp_maya.dispatcher.create_dispatcher",
            return_value=(ui_dispatcher, ui_pump),
        ):
            type(ui_dispatcher).__name__ = "MayaUiDispatcher"
            startup = resolve_plugin_host_startup(is_batch=False)

        assert startup.dispatcher is ui_dispatcher
        assert startup.ui_pump is ui_pump
        assert startup.host is None
        assert startup.backend == "python-fallback"

    def test_falls_back_to_standalone_in_batch_mode(self):
        host_mod = types.ModuleType("dcc_mcp_core.host")
        host_mod.BlockingDispatcher = None
        host_mod.QueueDispatcher = MagicMock(name="QueueDispatcher")

        standalone = MagicMock(name="MayaStandaloneDispatcher")
        type(standalone).__name__ = "MayaStandaloneDispatcher"

        with patch.dict(sys.modules, {"dcc_mcp_core.host": host_mod}), patch(
            "dcc_mcp_maya.dispatcher.create_dispatcher",
            return_value=(standalone, None),
        ):
            startup = resolve_plugin_host_startup(is_batch=True)

        assert startup.dispatcher is standalone
        assert startup.host is None
        assert startup.ui_pump is None
        assert startup.backend == "python-fallback"

    def test_fail_fast_when_core_and_fallback_unavailable(self):
        host_mod = types.ModuleType("dcc_mcp_core.host")
        host_mod.BlockingDispatcher = None
        host_mod.QueueDispatcher = None

        with patch.dict(sys.modules, {"dcc_mcp_core.host": host_mod}), patch(
            "dcc_mcp_maya.dispatcher.create_dispatcher",
            side_effect=RuntimeError("maya.cmds missing"),
        ):
            with pytest.raises(PluginDispatcherError) as excinfo:
                resolve_plugin_host_startup(is_batch=False)

        err = excinfo.value
        detail = err.as_dict()
        assert detail["error"] == "dispatcher-unavailable"
        assert detail["context"]["core_version"] not in ("", "unknown")
        assert detail["context"]["possible_solutions"]
