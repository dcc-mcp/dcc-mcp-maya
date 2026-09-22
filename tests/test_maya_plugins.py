"""Unit tests for the plug-in contract and the maya-plugins skill.

Rejection branches are covered deliberately: prior review findings on this
issue all came from only testing the happy path.  The fake ``cmds`` here
mirrors real Maya behaviour verified on 2025 - in particular that
``pluginInfo`` metadata flags only answer while a plug-in is loaded.
"""

from __future__ import annotations

import os

import pytest
from conftest import load_and_call

from dcc_mcp_maya.plugins import (
    LOADED_ONLY_FLAGS,
    PLUGIN_PATH_ENV,
    PluginContractError,
    diagnose_plugin,
    find_plugin_file,
    known_plugin_names,
    list_plugins,
    load_plugin,
    plugin_record,
    plugin_search_path,
    unload_plugin,
)


class _FakeCmds:
    """Stand-in for ``maya.cmds`` whose pluginInfo mirrors Maya 2025."""

    def __init__(self, known=None, loaded=None, unload_ok=True, files=None):
        # `known` is every plug-in Maya can address; `loaded` is the subset
        # currently loaded; `registered` is the subset Maya has ever registered
        # (only those expose commands and node types). pluginInfo exposes
        # listPlugins as loaded-only - verified on Maya 2025.
        self.known = set(known or [])
        self.loaded = set(loaded or [])
        self.registered = set(self.loaded) | set(self.known)
        self.unload_ok = unload_ok
        self.files = files or {}
        self.calls = []
        self.autoload = set()

    def pluginInfo(self, plugin=None, **kwargs):
        self.calls.append(("pluginInfo", plugin, dict(kwargs)))
        if kwargs.get("listPlugins"):
            # Real Maya lists only LOADED plug-ins here.
            return sorted(self.loaded)
        if kwargs.get("query"):
            for flag, value in kwargs.items():
                if value is not True or flag in ("query",):
                    continue
                if flag == "loaded":
                    return plugin in self.loaded
                if flag == "autoload":
                    return plugin in self.autoload
                if flag == "registered":
                    return plugin in self.registered
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
        self.registered.add(plugin)
        self.known.add(plugin)
        return [plugin]

    def unloadPlugin(self, plugin, **kwargs):
        self.calls.append(("unloadPlugin", plugin, dict(kwargs)))
        if plugin not in self.loaded:
            raise RuntimeError("not loaded")
        self.loaded.discard(plugin)
        self.known.discard(plugin)
        return True


def _path_with(names, tmp_path, stale=0):
    """Build a plugin_search_path-shaped dict backed by real temp files."""
    entries = []
    missing = []
    for name in names:
        (tmp_path / (name + ".mll")).write_text("", encoding="utf-8")
        entries.append(str(tmp_path))
    for index in range(stale):
        entries.append(str(tmp_path / ("stale{}".format(index))))
        missing.append(str(tmp_path / ("stale{}".format(index))))
    return {"env_var": PLUGIN_PATH_ENV, "raw": "", "entries": entries, "count": len(entries), "missing": missing}


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
    # The requested name is always reported, even for an unloaded plug-in.
    assert record["name"] == "mtoa"
    assert set(LOADED_ONLY_FLAGS) - {"name"} <= set(record["unavailable_flags"])


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


def test_list_plugins_includes_unloaded_plugins(tmp_path):
    """pluginInfo(listPlugins=True) omits unloaded plug-ins, so the inventory
    must come from the search path."""
    cmds = _FakeCmds(known={"mtoa", "unloadedOne"}, loaded={"mtoa"})
    path = _path_with(["mtoa", "unloadedOne"], tmp_path)

    result = list_plugins(cmds, search_path=path)

    names = {item["name"] for item in result["plugins"]}
    assert names == {"mtoa", "unloadedOne"}
    states = {item["name"]: item["loaded"] for item in result["plugins"]}
    assert states == {"mtoa": True, "unloadedOne": False}


def test_load_plugin_autoload_failure_does_not_fail_the_load():
    """The plug-in IS loaded; only the preference failed. Say so."""
    cmds = _FakeCmds(known={"mtoa"})

    def _boom(plugin, **_kwargs):
        raise RuntimeError("cannot write prefs")

    cmds.pluginInfo = _boom

    result = load_plugin(cmds, "mtoa", autoload=True)

    assert result["loaded"] is True
    assert result["autoload"] is False
    assert result["autoload_error"]


def test_list_plugins_filters_and_counts(tmp_path):
    cmds = _FakeCmds(known={"mtoa", "fbxmaya", "objExport"}, loaded={"mtoa", "fbxmaya"})
    path = _path_with(["mtoa", "fbxmaya", "objExport"], tmp_path)

    result = list_plugins(cmds, pattern="maya", search_path=path)

    assert [item["name"] for item in result["plugins"]] == ["fbxmaya"]
    assert result["loaded_count"] == 1


def test_list_plugins_loaded_only(tmp_path):
    cmds = _FakeCmds(known={"a", "b"}, loaded={"b"})
    path = _path_with(["a", "b"], tmp_path)

    result = list_plugins(cmds, loaded_only=True, search_path=path)

    assert [item["name"] for item in result["plugins"]] == ["b"]


def test_list_plugins_truncates_and_flags_it(tmp_path):
    cmds = _FakeCmds(known={"a", "b", "c"})
    path = _path_with(["a", "b", "c"], tmp_path)

    result = list_plugins(cmds, limit=2, search_path=path)

    assert result["count"] == 2
    assert result["total_matches"] == 3
    assert result["truncated"] is True


def test_list_plugins_clamps_a_zero_limit(tmp_path):
    cmds = _FakeCmds(known={"a", "b"})
    path = _path_with(["a", "b"], tmp_path)

    result = list_plugins(cmds, limit=0, search_path=path)

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


def test_unload_plugin_rejects_not_loaded(tmp_path):
    cmds = _FakeCmds(known={"mtoa"})
    path = _path_with(["mtoa"], tmp_path)

    with pytest.raises(PluginContractError, match="already unloaded|nothing to unload"):
        unload_plugin(cmds, "mtoa", search_path=path)


# ---------------------------------------------------------------------------
# Diagnosis
# ---------------------------------------------------------------------------


def test_find_plugin_file_accepts_an_injected_search_path(tmp_path):
    """Resolution must not depend on the ambient machine's search path."""
    (tmp_path / "mtoa.mll").write_text("", encoding="utf-8")
    path = {"entries": [str(tmp_path)], "count": 1, "missing": []}

    result = find_plugin_file("mtoa", search_path=path)

    assert result["found"] is True
    assert result["candidates"] == [str(tmp_path / "mtoa.mll")]


def test_find_plugin_file_accepts_a_bare_name_without_extension(tmp_path):
    (tmp_path / "customPlugin").write_text("", encoding="utf-8")
    path = {"entries": [str(tmp_path)], "count": 1, "missing": []}

    assert find_plugin_file("customPlugin", search_path=path)["found"] is True


def test_diagnose_reports_a_healthy_loaded_plugin(tmp_path):
    """A usable plug-in is healthy regardless of stale path entries.

    Stale search-path directories are environment hygiene and are reported as
    ``warnings``; they must not make a working plug-in look unhealthy. The
    search path is injected so the result does not depend on the machine.
    """
    (tmp_path / "mtoa.mll").write_text("", encoding="utf-8")
    cmds = _FakeCmds(known={"mtoa"}, loaded={"mtoa"})
    path = {
        "entries": [str(tmp_path), str(tmp_path / "stale")],
        "count": 2,
        "missing": [str(tmp_path / "stale")],
    }

    result = diagnose_plugin(cmds, "mtoa", search_path=path)

    assert result["known"] is True
    assert result["loaded"] is True
    assert result["file_found"] is True
    assert result["healthy"] is True
    assert result["problems"] == []
    # The stale directory is a warning, not a verdict on the plug-in.
    assert result["warnings"]
    assert all(PLUGIN_PATH_ENV in item for item in result["warnings"])


def test_diagnose_healthy_is_false_when_a_plugin_problem_exists():
    cmds = _FakeCmds(known={"mtoa"}, loaded={"mtoa"})

    broken = diagnose_plugin(cmds, "definitely_not_a_real_plugin_xyz")

    assert broken["healthy"] is False
    assert broken["problems"]


def test_diagnose_explains_an_unknown_plugin():
    cmds = _FakeCmds(known=set())

    result = diagnose_plugin(cmds, "definitely_not_a_real_plugin_xyz")

    assert result["healthy"] is False
    assert result["known"] is False
    assert result["file_found"] is False
    assert result["problems"]
    assert result["suggestions"]


def test_diagnose_explains_a_registered_but_unloaded_plugin(tmp_path):
    cmds = _FakeCmds(known={"mtoa"})
    path = _path_with(["mtoa"], tmp_path)

    result = diagnose_plugin(cmds, "mtoa", search_path=path)

    assert result["healthy"] is False
    assert result["known"] is True
    assert result["loaded"] is False
    assert any("not loaded" in problem for problem in result["problems"])


def test_inventory_excludes_directories_on_the_search_path(tmp_path):
    """Extensionless directories sit on the path and are not plug-ins."""
    (tmp_path / "realPlugin.mll").write_text("", encoding="utf-8")
    (tmp_path / "notAPluginDir").mkdir()
    path = {"env_var": PLUGIN_PATH_ENV, "raw": "", "entries": [str(tmp_path)], "count": 1, "missing": []}

    names = known_plugin_names(_FakeCmds(), search_path=path)

    assert "realPlugin" in names
    assert "notAPluginDir" not in names


def test_inventory_includes_macos_bundle_directories(tmp_path):
    """On macOS a plug-in ships as a .bundle directory, not as a file."""
    (tmp_path / "MacPlugin.bundle").mkdir()
    (tmp_path / "notAPluginDir").mkdir()
    path = {"env_var": PLUGIN_PATH_ENV, "raw": "", "entries": [str(tmp_path)], "count": 1, "missing": []}

    names = known_plugin_names(_FakeCmds(), search_path=path)

    assert "MacPlugin" in names
    assert "notAPluginDir" not in names


def test_inventory_excludes_directories_wearing_a_plugin_extension(tmp_path):
    """A directory named `stale.mll` is not a plug-in.

    Only .bundle may also be a directory (macOS bundles); every other
    extension must be a file. Skipping the file test for all known extensions
    let these phantom entries into list_plugins.
    """
    (tmp_path / "stale.mll").mkdir()
    (tmp_path / "old.so").mkdir()
    (tmp_path / "dead.py").mkdir()
    # Valid neighbours that must survive the fix unchanged.
    (tmp_path / "win.mll").write_text("", encoding="utf-8")
    (tmp_path / "linux.so").write_text("", encoding="utf-8")
    (tmp_path / "script.py").write_text("", encoding="utf-8")
    (tmp_path / "weird.bundle").write_text("", encoding="utf-8")  # .bundle as a FILE
    (tmp_path / "MacPlugin.bundle").mkdir()  # .bundle as a DIRECTORY
    (tmp_path / "bareplugin").write_text("", encoding="utf-8")  # extensionless file
    (tmp_path / "notAPluginDir").mkdir()
    path = {"env_var": PLUGIN_PATH_ENV, "raw": "", "entries": [str(tmp_path)], "count": 1, "missing": []}

    names = known_plugin_names(_FakeCmds(), search_path=path)

    for phantom in ("stale", "old", "dead"):
        assert phantom not in names, phantom
    for valid in ("win", "linux", "script", "weird", "MacPlugin", "bareplugin"):
        assert valid in names, valid
    assert "notAPluginDir" not in names


def test_inventory_excludes_broken_symlinks(tmp_path):
    """A dangling .bundle symlink is neither a file nor a directory.

    The .bundle exemption used to skip the file test entirely, so a broken
    `old.bundle` symlink was reported as a plug-in Maya cannot open.
    """
    os.symlink(str(tmp_path / "missing-target"), str(tmp_path / "old.bundle"))
    # A symlink pointing at a real plug-in file is still a plug-in.
    (tmp_path / "win.mll").write_text("", encoding="utf-8")
    os.symlink(str(tmp_path / "win.mll"), str(tmp_path / "goodlink.mll"))
    path = {"env_var": PLUGIN_PATH_ENV, "raw": "", "entries": [str(tmp_path)], "count": 1, "missing": []}

    names = known_plugin_names(_FakeCmds(), search_path=path)

    assert "old" not in names
    assert "goodlink" in names
    assert "win" in names


def test_diagnose_flags_a_file_that_maya_never_registered(tmp_path):
    """On the search path but unregistered means its commands do not exist."""
    (tmp_path / "ghost.mll").write_text("", encoding="utf-8")
    # On the search path but never loaded, so Maya has not registered it.
    cmds = _FakeCmds()
    cmds.registered = set()
    path = _path_with(["ghost"], tmp_path)

    result = diagnose_plugin(cmds, "ghost", search_path=path)

    assert result["known"] is True
    assert result["registered"] is False
    assert result["healthy"] is False
    assert any("not registered" in problem for problem in result["problems"])


class _RegisteredWithoutFile(_FakeCmds):
    """Maya registered the plug-in this session, but its file is not on the
    search path - e.g. it was loaded and then the directory was removed.

    ``registered`` is an always-valid flag and answers True here, while the
    path enumeration reports the plug-in as unknown.
    """

    def __init__(self):
        super().__init__(known=set(), loaded=set())
        self.registered = {"orphan"}

    def pluginInfo(self, plugin=None, **kwargs):
        if kwargs.get("query") and kwargs.get("registered"):
            return plugin in self.registered
        return super().pluginInfo(plugin, **kwargs)


def test_diagnose_does_not_claim_never_registered_when_it_is():
    """A false "never registered" is indistinguishable from a true one if the
    wording depends on ``known`` rather than Maya's registration state."""
    empty = {
        "env_var": PLUGIN_PATH_ENV,
        "raw": "",
        "entries": [],
        "count": 0,
        "missing": [],
    }

    result = diagnose_plugin(_RegisteredWithoutFile(), "orphan", search_path=empty)

    assert result["known"] is False
    assert result["file_found"] is False
    assert result["registered"] is True
    assert all("never registered" not in item for item in result["suggestions"])


def test_diagnose_keeps_never_registered_when_it_is_true():
    """Control case: the claim must still appear when it is actually true."""
    empty = {
        "env_var": PLUGIN_PATH_ENV,
        "raw": "",
        "entries": [],
        "count": 0,
        "missing": [],
    }

    result = diagnose_plugin(_FakeCmds(known=set()), "orphan", search_path=empty)

    assert result["registered"] is False
    assert any("never registered" in item for item in result["suggestions"])


def test_diagnose_requires_a_name():
    with pytest.raises(PluginContractError, match="non-empty"):
        diagnose_plugin(_FakeCmds(), "")


# ---------------------------------------------------------------------------
# Skill entry points
# ---------------------------------------------------------------------------


def _call(script, cmds, **kwargs):
    return load_and_call("maya-plugins/scripts/{}.py".format(script), cmds, "main", **kwargs)


def test_skill_list_plugins_reports_counts(tmp_path):
    cmds = _FakeCmds(known={"mtoa", "fbxmaya"}, loaded={"mtoa"})
    path = _path_with(["mtoa", "fbxmaya"], tmp_path)

    result = _call("list_plugins", cmds, search_path=path)

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
