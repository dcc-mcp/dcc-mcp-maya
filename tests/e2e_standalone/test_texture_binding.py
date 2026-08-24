"""Real mayapy coverage for typed Arnold texture binding."""

from __future__ import annotations

import shutil

import pytest

from ._support import _load_script, _new_scene, cmds

pytestmark = pytest.mark.e2e


def _require_mtoa():
    try:
        if not cmds.pluginInfo("mtoa", query=True, loaded=True):
            cmds.loadPlugin("mtoa", quiet=True)
    except Exception as exc:
        pytest.skip("MtoA is unavailable: {}".format(exc))
    if not cmds.pluginInfo("mtoa", query=True, loaded=True):
        pytest.skip("MtoA is not loaded")


def test_texture_bind_reload_and_repath_round_trip_native_maya_graph(tmp_path):
    _new_scene()
    _require_mtoa()
    assign = _load_script("maya-material-library", "assign_texture")
    reload_tool = _load_script("maya-material-library", "reload_textures")
    repath = _load_script("maya-material-library", "repath_textures")
    material = cmds.shadingNode("aiStandardSurface", asShader=True, name="dccMcpTextureLook")
    old_root = tmp_path / "old"
    new_root = tmp_path / "new"
    old_root.mkdir()
    new_root.mkdir()
    maps = {
        "base_color": old_root / "base_color.png",
        "roughness": old_root / "roughness.png",
        "normal": old_root / "normal.png",
    }
    for path in maps.values():
        path.write_bytes(b"texture-map")

    results = {
        slot: assign.assign_texture(
            material_name=material,
            texture_path=str(path),
            slot=slot,
        )
        for slot, path in maps.items()
    }
    assert all(result["success"] for result in results.values()), results
    assert cmds.connectionInfo("{}.baseColor".format(material), sourceFromDestination=True).endswith(".outColor")
    assert cmds.connectionInfo("{}.specularRoughness".format(material), sourceFromDestination=True).endswith(
        ".outAlpha"
    )
    assert cmds.connectionInfo("{}.normalCamera".format(material), sourceFromDestination=True).endswith(".outValue")

    texture_nodes = [result["context"]["texture_node"] for result in results.values()]
    reloaded = reload_tool.reload_textures(texture_nodes=texture_nodes)
    assert reloaded["success"] is True, reloaded
    assert reloaded["context"]["reloaded_count"] == 3

    for path in maps.values():
        shutil.copy2(str(path), str(new_root / path.name))
    moved = repath.repath_textures(
        texture_nodes=texture_nodes,
        old_root=str(old_root),
        new_root=str(new_root),
    )
    assert moved["success"] is True, moved
    assert moved["context"]["changed_count"] == 3
    assert all(change["texture_path"].startswith(str(new_root)) for change in moved["context"]["changes"])
