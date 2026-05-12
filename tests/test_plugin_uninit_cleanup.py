"""Tests for ``uninitializePlugin`` cleanup robustness (issue #126).

Verifies that ``_stop_blocking()`` is always invoked from the ``finally``
block — even when an earlier cleanup step raises — so the FileRegistry
entry is never leaked on partial shutdowns.

See: https://github.com/loonghao/dcc-mcp-maya/issues/126
"""

# Import future modules
from __future__ import annotations

# Import built-in modules
import importlib.util
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# Import third-party modules
import pytest


def _load_plugin_module():
    """Load the Maya plugin file as a module with ``maya.*`` mocked."""
    plugin_path = Path(__file__).resolve().parents[1] / "maya" / "plugin" / "dcc_mcp_maya_plugin.py"
    assert plugin_path.is_file(), plugin_path

    fake_maya = MagicMock(name="maya")
    fake_cmds = MagicMock(name="maya.cmds")
    fake_om = MagicMock(name="maya.api.OpenMaya")
    fake_om.MFnPlugin = MagicMock(return_value=MagicMock())
    modules = {
        "maya": fake_maya,
        "maya.cmds": fake_cmds,
        "maya.api": MagicMock(),
        "maya.api.OpenMaya": fake_om,
        "maya.utils": MagicMock(),
    }
    with patch.dict(sys.modules, modules):
        spec = importlib.util.spec_from_file_location("_dcc_mcp_maya_plugin_under_test", plugin_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    return module, fake_om


@pytest.fixture()
def plugin_module():
    module, fake_om = _load_plugin_module()
    yield module, fake_om
    sys.modules.pop("_dcc_mcp_maya_plugin_under_test", None)


class TestUninitializePluginCleanup:
    """Cleanup must always release the server, even on partial failures."""

    def test_stop_called_even_when_menu_removal_raises(self, plugin_module):
        module, _ = plugin_module
        with patch.object(module, "_is_interactive", return_value=True), patch.object(
            module, "_remove_menu", side_effect=RuntimeError("ui kaboom")
        ) as remove_menu, patch.object(module, "_stop_blocking") as stop_blocking:
            module.uninitializePlugin(plugin=MagicMock())
        remove_menu.assert_called_once()
        stop_blocking.assert_called_once()

    def test_stop_called_when_menu_removal_succeeds(self, plugin_module):
        module, _ = plugin_module
        with patch.object(module, "_is_interactive", return_value=True), patch.object(
            module, "_remove_menu"
        ) as remove_menu, patch.object(module, "_stop_blocking") as stop_blocking:
            module.uninitializePlugin(plugin=MagicMock())
        remove_menu.assert_called_once()
        stop_blocking.assert_called_once()

    def test_stop_called_in_batch_mode(self, plugin_module):
        """Non-interactive (mayapy / batch) → no menu, but still stop the server."""
        module, _ = plugin_module
        with patch.object(module, "_is_interactive", return_value=False), patch.object(
            module, "_remove_menu"
        ) as remove_menu, patch.object(module, "_stop_blocking") as stop_blocking:
            module.uninitializePlugin(plugin=MagicMock())
        remove_menu.assert_not_called()
        stop_blocking.assert_called_once()

    def test_stop_failure_is_swallowed(self, plugin_module):
        """A stop_blocking failure must not bubble out of uninitializePlugin."""
        module, _ = plugin_module
        with patch.object(module, "_is_interactive", return_value=False), patch.object(
            module, "_stop_blocking", side_effect=RuntimeError("server kaboom")
        ) as stop_blocking:
            # Must not raise.
            module.uninitializePlugin(plugin=MagicMock())
        stop_blocking.assert_called_once()


class TestInitializePluginStaleScan:
    """At startup, plugin best-effort runs hygiene checks."""

    def test_stale_scan_and_log_prune_invoked_after_start(self, plugin_module):
        module, _ = plugin_module
        with patch.object(module, "_print_startup_info"), patch.object(module, "_install_shutdown_safety"):
            with patch("dcc_mcp_maya._log_hygiene.prune_maya_logs") as prune, patch(
                "dcc_mcp_maya._stale_cleanup.warn_if_too_many_stale"
            ) as warn:
                module._post_start({})
        prune.assert_called_once()
        warn.assert_called_once()

    def test_stale_scan_failure_does_not_break_init(self, plugin_module):
        module, _ = plugin_module
        with patch.object(module, "_print_startup_info"), patch.object(module, "_install_shutdown_safety"):
            with patch("dcc_mcp_maya._log_hygiene.prune_maya_logs"), patch(
                "dcc_mcp_maya._stale_cleanup.warn_if_too_many_stale",
                side_effect=RuntimeError("scan boom"),
            ):
                # Must not raise.
                module._post_start({})
