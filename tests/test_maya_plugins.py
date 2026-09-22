"""Unit tests for the plug-in contract and the maya-plugins skill.

Rejection branches are covered deliberately: prior review findings on this
issue all came from only testing the happy path.  The fake ``cmds`` here
mirrors real Maya behaviour verified on 2025 - in particular that
``pluginInfo`` metadata flags only answer while a plug-in is loaded.
"""

from __future__ import annotations

import pytest
from conftest import load_and_call

from dcc_mcp_maya.plugins import (
    LOADED_ONLY_FLAGS,
    PLUGIN_PATH_ENV,
    PluginContractError,
    diagnose_plugin,
    find_plugin_file,
    list_plugins,
    load_plugin,
    plugin_record,
    plugin_search_path,
    unload_plugin,
)


class _FakeCmds:
    """Stand-in for ``maya.cmds`` whose pluginInfo mirrors Maya 2025."""

    def __init__(self, known=None, loaded=None, unload_ok=True, files=None):
        self.known = set(known or [])
        self.loaded = set(loaded or [])
        self.unload_ok = unload_ok
        self.files = files or {}
        self.calls = []
        self.autoload = set()

    def pluginInfo(self, plugin=None, **kwargs):
        self.calls.append(("pluginInfo", plugin, dict(kwargs)))
        if kwargs.get("listPlugins"):
            return sorted(self.known)
        if kwargs.get("query"):
            for flag, value in kwargs.items():
                if value is not True or flag in ("query",):
                    continue
                if flag == "loaded":
                    return plugin in self.loaded
                if flag == "autoload":
                    return plugin in self.autoload
                if flag == "registered":
                    return plugin in self.known
                # Metadata flags only answer while loaded - Maya raises otherwise.
                if plugin not in self.loaded:
                    raise RuntimeError("invalid object or value")
                if flag == "unloadOk":
                    return self.unload_ok
                if flag == "path":
                    return self.files.get(plugin, "/plug-ins/{}.mll".format(plugin))
                if flag == "version":
                    return "1.2.3"
                if flag == "vendor":
                    return "Example"
                if flag == "apiVersion":
                    return "20250000"
                if flag == "name":
                    return plugin
                raise RuntimeError("invalid flag")
        if kwargs.get("edit") and kwargs.get("autoload"):
            self.autoload.add(plugin)
            return True
        return None

    def loadPlugin(self, plugin, **_kwargs):
        self.calls.append(("loadPlugin", plugin))
        if plugin not in self.known:
            # Maya raises even with quiet=True.
            raise RuntimeError('Plug-in "{}" not found on MAYA_PLUG_IN_PATH.'.format(plugin))
        self.loaded.add(plugin)
        return [plugin]

    def unloadPlugin(self, plugin, **kwargs):
        self.calls.append(("unloadPlugin", plugin, dict(kwargs)))
        if plugin not in self.loaded:
            raise RuntimeError("not loaded")
        self.loaded.discard(plugin)
        self.known.discard(plugin)
        return True


# ---------------------------------------------------------------------------
# Search path
# ---------------------------------------------------------------------------


def test_plugin_search_path_splits_on_the_platform_separator():
    result = plugin_search_path()

    assert result["env_var"] == PLUGIN_PATH_ENV
    assert isinstance(result["entries"], list)
    assert result["count"] == len(result["entries"])
    assert set(result.keys()) >= {"raw", "entries", "count", "missing"}


def test_find_plugin_file_requires_a_name():
    with pytest.raises(PluginContractError, match="must be a non-empty plug-in name"):
        find_plugin_file(" ")


def test_find_plugin_file_reports_not_found_without_raising():
    result = find_plugin_file("definitely_not_a_real_plugin_xyz")

    assert result["found"] is False
    assert result["candidates"] == []


# ---------------------------------------------------------------------------
# Records
# ---------------------------------------------------------------------------


def test_unloaded_plugin_reports_metadata_as_unavailable():
    """Maya raises for metadata flags on an unloaded plug-in."""
    cmds = _FakeCmds(known={"mtoa"})

    record = plugin_record(cmds, "mtoa")

    assert record["loaded"] is False
    assert record["metadata_available"] is False
    assert record["version"] is None
    assert record["reason"]
    assert set(LOADED_ONLY_FLAGS).issubset(set(record["unavailable_flags"]))


def test_loaded_plugin_reports_full_metadata():
    cmds = _FakeCmds(known={"mtoa"}, loaded={"mtoa"})

    record = plugin_record(cmds, "mtoa")

    assert record["loaded"] is True
    assert record["metadata_available"] is True
    assert record["version"] == "1.2.3"
    assert record["vendor"] == "Example"
    assert record["unavailable_flags"] == []


def test_plugin_record_requires_a_name():
    with pytest.raises(PluginContractError, match="non-empty"):
        plugin_record(_FakeCmds(), " ")


# ---------------------------------------------------------------------------
# Listing
# ---------------------------------------------------------------------------


def test_list_plugins_filters_and_counts():
    cmds = _FakeCmds(known={"mtoa", "fbxmaya", "objExport"}, loaded={"mtoa", "fbxmaya"})

    result = list_plugins(cmds, pattern="maya")

    assert [item["name"] for item in result["plugins"]] == ["fbxmaya"]
    assert result["loaded_count"] == 1


def test_list_plugins_loaded_only():
    cmds = _FakeCmds(known={"a", "b"}, loaded={"b"})

    result = list_plugins(cmds, loaded_only=True)

    assert [item["name"] for item in result["plugins"]] == ["b"]


def test_list_plugins_truncates_and_flags_it():
    cmds = _FakeCmds(known={"a", "b", "c"})

    result = list_plugins(cmds, limit=2)

    assert result["count"] == 2
    assert result["total_matches"] == 3
    assert result["truncated"] is True


def test_list_plugins_clamps_a_zero_limit():
    cmds = _FakeCmds(known={"a", "b"})

    result = list_plugins(cmds, limit=0)

    assert result["count"] == 1


# ---------------------------------------------------------------------------
# Load / unload
# ---------------------------------------------------------------------------


def test_load_plugin_loads_and_reads_metadata():
    cmds = _FakeCmds(known={"mtoa"}, loaded={"mtoa"})

    result = load_plugin(cmds, "mtoa")

    assert result["loaded"] is True
    assert result["was_loaded"] is True
    assert result["record"]["version"] == "1.2.3"


def test_load_plugin_records_when_it_was_not_already_loaded():
    cmds = _FakeCmds(known={"mtoa"})

    result = load_plugin(cmds, "mtoa")

    assert result["was_loaded"] is False


def test_load_plugin_fails_closed_with_the_search_path_in_the_error():
    """A missing plug-in must be an actionable error, never a silent no-op."""
    cmds = _FakeCmds(known=set())

    with pytest.raises(PluginContractError) as excinfo:
        load_plugin(cmds, "definitely_not_a_real_plugin_xyz")

    message = str(excinfo.value)
    assert "definitely_not_a_real_plugin_xyz" in message
    assert PLUGIN_PATH_ENV in message


def test_load_plugin_requires_a_name():
    with pytest.raises(PluginContractError, match="non-empty"):
        load_plugin(_FakeCmds(), " ")


def test_load_plugin_can_set_autoload():
    cmds = _FakeCmds(known={"mtoa"})

    result = load_plugin(cmds, "mtoa", autoload=True)

    assert result["autoload"] is True
    assert "mtoa" in cmds.autoload


def test_unload_plugin_unloads():
    cmds = _FakeCmds(known={"mtoa"}, loaded={"mtoa"})

    result = unload_plugin(cmds, "mtoa")

    assert result["loaded"] is False
    assert "mtoa" not in cmds.loaded


def test_unload_plugin_refuses_when_maya_says_it_cannot_unload():
    cmds = _FakeCmds(known={"mtoa"}, loaded={"mtoa"}, unload_ok=False)

    with pytest.raises(PluginContractError, match="cannot be unloaded"):
        unload_plugin(cmds, "mtoa")

    assert "mtoa" in cmds.loaded


def test_unload_plugin_force_overrides_unload_ok():
    cmds = _FakeCmds(known={"mtoa"}, loaded={"mtoa"}, unload_ok=False)

    result = unload_plugin(cmds, "mtoa", force=True)

    assert result["forced"] is True


def test_unload_plugin_rejects_unknown_plugin():
    with pytest.raises(PluginContractError, match="does not know"):
        unload_plugin(_FakeCmds(known=set()), "nope")


def test_unload_plugin_rejects_not_loaded():
    cmds = _FakeCmds(known={"mtoa"})

    with pytest.raises(PluginContractError, match="nothing to unload"):
        unload_plugin(cmds, "mtoa")


# ---------------------------------------------------------------------------
# Diagnosis
# ---------------------------------------------------------------------------


def test_diagnose_reports_a_healthy_loaded_plugin():
    cmds = _FakeCmds(known={"mtoa"}, loaded={"mtoa"}, files={"mtoa": "/p/mtoa.mll"})

    result = diagnose_plugin(cmds, "mtoa")

    assert result["known"] is True
    assert result["loaded"] is True
    assert result["healthy"] is True
    assert result["problems"] == []


def test_diagnose_explains_an_unknown_plugin():
    cmds = _FakeCmds(known=set())

    result = diagnose_plugin(cmds, "definitely_not_a_real_plugin_xyz")

    assert result["healthy"] is False
    assert result["known"] is False
    assert result["file_found"] is False
    assert result["problems"]
    assert result["suggestions"]


def test_diagnose_explains_a_registered_but_unloaded_plugin():
    cmds = _FakeCmds(known={"mtoa"})

    result = diagnose_plugin(cmds, "mtoa")

    assert result["healthy"] is False
    assert result["known"] is True
    assert result["loaded"] is False
    assert any("not loaded" in problem for problem in result["problems"])


def test_diagnose_requires_a_name():
    with pytest.raises(PluginContractError, match="non-empty"):
        diagnose_plugin(_FakeCmds(), "")


# ---------------------------------------------------------------------------
# Skill entry points
# ---------------------------------------------------------------------------


def _call(script, cmds, **kwargs):
    return load_and_call("maya-plugins/scripts/{}.py".format(script), cmds, "main", **kwargs)


def test_skill_list_plugins_reports_counts():
    cmds = _FakeCmds(known={"mtoa", "fbxmaya"}, loaded={"mtoa"})

    result = _call("list_plugins", cmds)

    assert result["success"] is True, result
    assert result["context"]["count"] == 2
    assert result["context"]["loaded_count"] == 1


def test_skill_load_plugin_returns_metadata():
    cmds = _FakeCmds(known={"mtoa"}, loaded={"mtoa"})

    result = _call("load_plugin", cmds, plugin="mtoa")

    assert result["success"] is True, result
    assert result["context"]["version"] == "1.2.3"


def test_skill_load_plugin_fails_closed_with_suggestions():
    cmds = _FakeCmds(known=set())

    result = _call("load_plugin", cmds, plugin="definitely_not_a_real_plugin_xyz")

    assert result["success"] is False
    assert PLUGIN_PATH_ENV in " ".join(result["context"].get("possible_solutions") or [])


def test_skill_unload_plugin_succeeds():
    cmds = _FakeCmds(known={"mtoa"}, loaded={"mtoa"})

    result = _call("unload_plugin", cmds, plugin="mtoa")

    assert result["success"] is True, result


def test_skill_unload_plugin_refuses_when_not_unloadable():
    cmds = _FakeCmds(known={"mtoa"}, loaded={"mtoa"}, unload_ok=False)

    result = _call("unload_plugin", cmds, plugin="mtoa")

    assert result["success"] is False
    assert "mtoa" in cmds.loaded


def test_skill_diagnose_plugin_reports_problems():
    cmds = _FakeCmds(known=set())

    result = _call("diagnose_plugin", cmds, plugin="definitely_not_a_real_plugin_xyz")

    assert result["success"] is True, result
    assert result["context"]["healthy"] is False
    assert result["context"]["problems"]


def test_skill_diagnose_plugin_rejects_empty_name():
    result = _call("diagnose_plugin", _FakeCmds(), plugin="")

    assert result["success"] is False


def test_skill_get_plugin_path_lists_entries():
    result = _call("get_plugin_path", _FakeCmds())

    assert result["success"] is True, result
    assert "count" in result["context"]


def test_skill_get_plugin_path_resolves_a_name():
    result = _call("get_plugin_path", _FakeCmds(), plugin="mtoa")

    assert result["success"] is True, result
    assert result["context"]["plugin"] == "mtoa"
    assert "found" in result["context"]
