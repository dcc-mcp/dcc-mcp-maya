"""Unit tests for the Bifrost simulation tools (cache + polygon conversion)."""

from __future__ import annotations

import pytest
from conftest import load_and_call

from dcc_mcp_maya.bifrost import (
    CACHE_FORMATS,
    CONVERT_MODES,
    BifrostContractError,
    convert_to_polygons,
    ensure_bifrost_plugins,
    write_simulation_cache,
)


class _FakeCmds:
    """Minimal ``maya.cmds`` stand-in for Bifrost simulation calls."""

    def __init__(self, existing=None):
        self.existing = dict(existing or {"bifrostGraphShape1": "bifrostGraphShape"})
        self.calls = []
        self._counts = {}
        self._created = {}
        self.loaded_plugins = set()

    def objExists(self, node):
        return node in self.existing or node in self._created

    def nodeType(self, node):
        return self.existing.get(node) or self._created.get(node) or "transform"

    def listRelatives(self, node, **_kwargs):
        return ["|bifrostGraph1"]

    def playbackOptions(self, **kwargs):
        return 1.0 if kwargs.get("minTime") else 100.0

    def pluginInfo(self, plugin, **kwargs):
        if kwargs.get("loaded"):
            return plugin in self.loaded_plugins
        if kwargs.get("version"):
            return "Bifrost 2.6.0.0"
        return None

    def loadPlugin(self, plugin, **_kwargs):
        self.loaded_plugins.add(plugin)
        return [plugin]

    def convertBifrostToPolygons(self, graph, **kwargs):
        self.calls.append(("convertBifrostToPolygons", graph, kwargs))
        self._counts["mesh"] = self._counts.get("mesh", 0) + 1
        name = kwargs.get("name") or "meshShape{}".format(self._counts["mesh"])
        self._created[name] = "mesh"
        return [name]

    def cacheFile(self, **kwargs):
        self.calls.append(("cacheFile", kwargs))
        self._created["cacheFile1"] = "cacheFile"
        return ["cacheFile1"]


def _calls(cmds, name):
    return [call for call in cmds.calls if call[0] == name]


# ---------------------------------------------------------------------------
# ensure_bifrost_plugins
# ---------------------------------------------------------------------------


def test_ensure_bifrost_plugins_loads_missing_plugins():
    cmds = _FakeCmds()

    result = ensure_bifrost_plugins(cmds)

    assert result["plugins"] == ["mayaVnnPlugin", "bifrostGraph"]
    assert result["loaded_now"] == ["mayaVnnPlugin", "bifrostGraph"]
    assert result["bifrost_version"] == "Bifrost 2.6.0.0"


def test_ensure_bifrost_plugins_skips_already_loaded():
    cmds = _FakeCmds()
    cmds.loaded_plugins = {"mayaVnnPlugin", "bifrostGraph"}

    result = ensure_bifrost_plugins(cmds)

    assert result["loaded_now"] == []


# ---------------------------------------------------------------------------
# convert_to_polygons
# ---------------------------------------------------------------------------


def test_convert_to_polygons_uses_triangulate_by_default():
    cmds = _FakeCmds()

    result = convert_to_polygons(cmds, graph="bifrostGraphShape1")

    assert result["mode"] == "triangulate"
    assert result["meshes"] == ["meshShape1"]
    assert result["transforms"] == ["|bifrostGraph1"]
    _op, graph, kwargs = _calls(cmds, "convertBifrostToPolygons")[0]
    assert graph == "bifrostGraphShape1"
    assert kwargs["blend"] == 1.0


def test_convert_to_polygons_quad_mode_sets_quad_flag():
    cmds = _FakeCmds()

    result = convert_to_polygons(cmds, graph="bifrostGraphShape1", mode="quad", name="liquid", threshold=0.25)

    assert result["mode"] == "quad"
    kwargs = _calls(cmds, "convertBifrostToPolygons")[0][2]
    assert kwargs["quad"] is True
    assert kwargs["name"] == "liquid"
    assert kwargs["threshold"] == 0.25


def test_convert_to_polygons_rejects_unknown_mode():
    with pytest.raises(BifrostContractError, match="mode must be one of"):
        convert_to_polygons(_FakeCmds(), graph="bifrostGraphShape1", mode="hex")


def test_convert_to_polygons_rejects_non_graph_node():
    cmds = _FakeCmds(existing={"pCube1": "mesh"})
    with pytest.raises(BifrostContractError, match="expected one of"):
        convert_to_polygons(cmds, graph="pCube1")


def test_convert_modes_match_the_maya_surface():
    assert set(CONVERT_MODES) == {"triangulate", "quad", "voronoi"}


# ---------------------------------------------------------------------------
# write_simulation_cache
# ---------------------------------------------------------------------------


def test_write_simulation_cache_uses_scene_range():
    cmds = _FakeCmds()

    result = write_simulation_cache(cmds, graph="bifrostGraphShape1", directory="/tmp/bifrost")

    assert result["frame_range"] == [1.0, 100.0]
    assert result["cache_node"] == "cacheFile1"
    kwargs = _calls(cmds, "cacheFile")[0][1]
    assert kwargs["directory"] == "/tmp/bifrost"
    assert kwargs["format"] == "OneFile"
    assert kwargs["points"] == "|bifrostGraph1"


def test_write_simulation_cache_honours_explicit_frames_and_name():
    cmds = _FakeCmds()

    result = write_simulation_cache(
        cmds,
        graph="bifrostGraphShape1",
        directory="/tmp/bifrost",
        file_name="foam",
        start_frame=10,
        end_frame=48,
        cache_format="OneFilePerFrame",
    )

    assert result["file_name"] == "foam"
    assert result["frame_range"] == [10, 48]
    kwargs = _calls(cmds, "cacheFile")[0][1]
    assert kwargs["format"] == "OneFilePerFrame"
    assert kwargs["startTime"] == 10
    assert kwargs["endTime"] == 48


def test_write_simulation_cache_requires_directory():
    with pytest.raises(BifrostContractError, match="directory is required"):
        write_simulation_cache(_FakeCmds(), graph="bifrostGraphShape1", directory=" ")


def test_write_simulation_cache_rejects_unknown_format():
    with pytest.raises(BifrostContractError, match="cache_format must be one of"):
        write_simulation_cache(_FakeCmds(), graph="bifrostGraphShape1", directory="/tmp", cache_format="mcc")


def test_write_simulation_cache_rejects_inverted_range():
    with pytest.raises(BifrostContractError, match="end_frame .* must be >= start_frame"):
        write_simulation_cache(
            _FakeCmds(),
            graph="bifrostGraphShape1",
            directory="/tmp",
            start_frame=50,
            end_frame=1,
        )


def test_cache_formats_match_the_maya_surface():
    assert set(CACHE_FORMATS) == {"OneFile", "OneFilePerFrame"}


# ---------------------------------------------------------------------------
# Skill entry points
# ---------------------------------------------------------------------------


def test_skill_cache_bifrost_simulation_returns_success():
    cmds = _FakeCmds()

    result = load_and_call(
        "maya-bifrost/scripts/cache_bifrost_simulation.py",
        cmds,
        "main",
        graph="bifrostGraphShape1",
        directory="/tmp/bifrost",
        start_frame=1,
        end_frame=24,
    )

    assert result["success"] is True, result
    assert result["context"]["cache_node"] == "cacheFile1"
    assert result["context"]["runtime"]["plugins"] == ["mayaVnnPlugin", "bifrostGraph"]


def test_skill_cache_bifrost_simulation_requires_graph():
    result = load_and_call(
        "maya-bifrost/scripts/cache_bifrost_simulation.py",
        _FakeCmds(),
        "main",
        directory="/tmp/bifrost",
    )

    assert result["success"] is False


def test_skill_cache_bifrost_simulation_requires_directory():
    result = load_and_call(
        "maya-bifrost/scripts/cache_bifrost_simulation.py",
        _FakeCmds(),
        "main",
        graph="bifrostGraphShape1",
    )

    assert result["success"] is False


def test_skill_convert_bifrost_to_polygons_returns_meshes():
    cmds = _FakeCmds()

    result = load_and_call(
        "maya-bifrost/scripts/convert_bifrost_to_polygons.py",
        cmds,
        "main",
        graph="bifrostGraphShape1",
        mode="triangulate",
    )

    assert result["success"] is True, result
    assert result["context"]["meshes"] == ["meshShape1"]


def test_skill_convert_bifrost_to_polygons_requires_graph():
    result = load_and_call("maya-bifrost/scripts/convert_bifrost_to_polygons.py", _FakeCmds(), "main")

    assert result["success"] is False


def test_skill_convert_bifrost_to_polygons_rejects_bad_mode():
    result = load_and_call(
        "maya-bifrost/scripts/convert_bifrost_to_polygons.py",
        _FakeCmds(),
        "main",
        graph="bifrostGraphShape1",
        mode="hex",
    )

    assert result["success"] is False
