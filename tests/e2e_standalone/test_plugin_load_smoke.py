"""Plugin load smoke tests that exercise Maya's real cmds.loadPlugin path."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

pytestmark = pytest.mark.e2e


_LOCALE_ERROR_FRAGMENTS = (
    "lowestPriority",
    "must be passed for flag",
    "boolean argument",
    "必须为标志",
)


def _plugin_path() -> Path:
    mod_dir = os.environ.get("DCC_MCP_MAYA_MOD_DIR")
    if mod_dir:
        return Path(mod_dir) / "plug-ins" / "dcc_mcp_maya_plugin.py"
    return Path(__file__).parents[2] / "maya" / "plugin" / "dcc_mcp_maya_plugin.py"


def test_plugin_load_via_cmds_loadplugin(monkeypatch):
    from maya import cmds

    monkeypatch.setenv("DCC_MCP_MAYA_PORT", "0")
    monkeypatch.setenv("DCC_MCP_GATEWAY_PORT", "0")
    plugin_path = _plugin_path()

    if cmds.pluginInfo("dcc_mcp_maya_plugin", query=True, loaded=True):
        cmds.unloadPlugin("dcc_mcp_maya_plugin", force=True)

    try:
        cmds.loadPlugin(str(plugin_path), quiet=True)
        assert cmds.pluginInfo("dcc_mcp_maya_plugin", query=True, loaded=True)
    finally:
        if cmds.pluginInfo("dcc_mcp_maya_plugin", query=True, loaded=True):
            cmds.unloadPlugin("dcc_mcp_maya_plugin", force=True)


def test_interactive_initialize_path_has_no_async_thread_error(monkeypatch, capsys):
    import importlib.util

    plugin_path = _plugin_path()
    spec = importlib.util.spec_from_file_location("_dcc_mcp_maya_plugin_interactive_smoke", plugin_path)
    plugin = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(plugin)

    monkeypatch.setenv("DCC_MCP_MAYA_PORT", "0")
    monkeypatch.setenv("DCC_MCP_GATEWAY_PORT", "0")
    monkeypatch.setattr(plugin, "_is_interactive", lambda: True)
    monkeypatch.setattr(plugin, "_add_menu", lambda: None)

    class _FakePluginObject:
        pass

    class _FakeMFnPlugin:
        def __init__(self, *args, **kwargs):
            pass

    monkeypatch.setattr(plugin.om, "MFnPlugin", _FakeMFnPlugin)

    try:
        plugin.initializePlugin(_FakePluginObject())
    finally:
        try:
            plugin.uninitializePlugin(_FakePluginObject())
        except Exception:
            pass

    captured = capsys.readouterr()
    combined = captured.out + captured.err
    assert not any(fragment in combined for fragment in _LOCALE_ERROR_FRAGMENTS)
