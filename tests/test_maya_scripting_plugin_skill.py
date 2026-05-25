"""Unit tests for maya-scripting plug-in lifecycle tools."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock

import yaml

from tests.conftest import load_and_call


def _plugin_info_mock(loaded: Dict[str, bool], autoload: Dict[str, bool]):
    def _plugin_info(*args: Any, **kwargs: Any) -> Any:
        plugin = str(args[0]) if args else ""
        if kwargs.get("query") and kwargs.get("listPlugins"):
            return ["fbxmaya", "mtoa", "AbcExport"]
        if kwargs.get("query") and kwargs.get("loaded"):
            return loaded.get(plugin, False)
        if kwargs.get("query") and kwargs.get("autoload"):
            return autoload.get(plugin, False)
        if kwargs.get("query") and kwargs.get("registered"):
            return plugin in loaded or plugin in autoload
        if kwargs.get("query") and kwargs.get("path"):
            return "/maya/plugins/{}.mll".format(plugin)
        if kwargs.get("query") and kwargs.get("version"):
            return "1.0"
        if kwargs.get("query") and kwargs.get("vendor"):
            return "Autodesk"
        if kwargs.get("query") and kwargs.get("apiVersion"):
            return "20260000"
        if kwargs.get("query") and kwargs.get("unloadOk"):
            return True
        if kwargs.get("edit") and "autoload" in kwargs:
            autoload[plugin] = bool(kwargs["autoload"])
            return None
        raise AssertionError("Unexpected pluginInfo call: args={!r} kwargs={!r}".format(args, kwargs))

    return _plugin_info


def test_list_plugins_filters_and_returns_details():
    loaded = {"fbxmaya": True, "mtoa": True, "AbcExport": True}
    autoload = {"fbxmaya": False, "mtoa": True, "AbcExport": False}
    mock_cmds = MagicMock()
    mock_cmds.pluginInfo.side_effect = _plugin_info_mock(loaded, autoload)

    out = load_and_call(
        "maya-scripting/scripts/list_plugins.py",
        mock_cmds,
        pattern="fbx",
        include_details=True,
    )

    assert out.get("success") is True
    ctx = out.get("context") or {}
    assert ctx.get("count") == 1
    record = ctx["plugins"][0]
    assert record["name"] == "fbxmaya"
    assert record["loaded"] is True
    assert record["autoload"] is False
    assert record["path"].endswith("fbxmaya.mll")
    assert record["api_version"] == "20260000"


def test_load_plugin_loads_and_sets_autoload():
    loaded = {"fbxmaya": False}
    autoload = {"fbxmaya": False}
    mock_cmds = MagicMock()
    mock_cmds.pluginInfo.side_effect = _plugin_info_mock(loaded, autoload)

    def _load_plugin(plugin: str, quiet: bool = True):
        assert plugin == "fbxmaya"
        assert quiet is True
        loaded[plugin] = True
        return [plugin]

    mock_cmds.loadPlugin.side_effect = _load_plugin

    out = load_and_call(
        "maya-scripting/scripts/load_plugin.py",
        mock_cmds,
        plugin="fbxmaya",
        set_autoload=True,
    )

    assert out.get("success") is True
    ctx = out.get("context") or {}
    assert ctx["loaded"] is True
    assert ctx["loaded_before"] is False
    assert ctx["loaded_plugins"] == ["fbxmaya"]
    assert ctx["autoload"] is True
    assert autoload["fbxmaya"] is True


def test_unload_plugin_unloads_and_clears_autoload():
    loaded = {"fbxmaya": True}
    autoload = {"fbxmaya": True}
    mock_cmds = MagicMock()
    mock_cmds.pluginInfo.side_effect = _plugin_info_mock(loaded, autoload)

    def _unload_plugin(plugin: str, force: bool = False):
        assert plugin == "fbxmaya"
        assert force is True
        loaded[plugin] = False

    mock_cmds.unloadPlugin.side_effect = _unload_plugin

    out = load_and_call(
        "maya-scripting/scripts/unload_plugin.py",
        mock_cmds,
        plugin="fbxmaya",
        force=True,
        remove_autoload=True,
    )

    assert out.get("success") is True
    ctx = out.get("context") or {}
    assert ctx["loaded_before"] is True
    assert ctx["loaded"] is False
    assert ctx["autoload"] is False
    assert autoload["fbxmaya"] is False


def test_unload_plugin_skips_when_not_loaded_ok():
    loaded = {"fbxmaya": False}
    autoload = {"fbxmaya": False}
    mock_cmds = MagicMock()
    mock_cmds.pluginInfo.side_effect = _plugin_info_mock(loaded, autoload)

    out = load_and_call(
        "maya-scripting/scripts/unload_plugin.py",
        mock_cmds,
        plugin="fbxmaya",
        not_loaded_ok=True,
    )

    assert out.get("success") is True
    assert (out.get("context") or {})["loaded_before"] is False
    mock_cmds.unloadPlugin.assert_not_called()


def test_plugin_lifecycle_tools_are_declared_in_core_group():
    skill_dir = Path(__file__).parent.parent / "src" / "dcc_mcp_maya" / "skills" / "maya-scripting"
    tools = yaml.safe_load((skill_dir / "tools.yaml").read_text(encoding="utf-8"))["tools"]
    groups = yaml.safe_load((skill_dir / "groups.yaml").read_text(encoding="utf-8"))["groups"]
    tool_names = {tool["name"]: tool for tool in tools}
    core_group = next(group for group in groups if group["name"] == "core")

    for name in ("list_plugins", "load_plugin", "unload_plugin"):
        assert name in tool_names
        assert name in core_group["tools"]
        assert tool_names[name]["affinity"] == "main"

    assert tool_names["list_plugins"]["annotations"]["read_only_hint"] is True
    assert tool_names["load_plugin"]["annotations"]["idempotent_hint"] is True
    assert tool_names["unload_plugin"]["annotations"]["destructive_hint"] is True
