"""UV readback regression against Maya's actual multi-set and coordinate behavior."""

from __future__ import annotations

import pytest

from ._support import _load_script, _new_scene, cmds

pytestmark = pytest.mark.e2e


def test_uv_reads_preserve_active_set_and_report_requested_bounds():
    _new_scene()
    mesh = cmds.polyPlane(name="uvReadback", subdivisionsX=1, subdivisionsY=1)[0]
    cmds.polyUVSet(mesh, copy=True, uvSet="map1", newUVSet="lightmap")
    cmds.polyUVSet(mesh, currentUVSet=True, uvSet="lightmap")
    cmds.polyEditUV(mesh + ".map[*]", relative=True, uValue=2.0, vValue=-3.0)
    cmds.polyUVSet(mesh, currentUVSet=True, uvSet="map1")
    cmds.select(mesh)
    before_selection = cmds.ls(selection=True, long=True)
    before_modified = cmds.file(query=True, modified=True)

    info = _load_script("maya-uv-ops", "get_uv_info").get_uv_info(mesh, uv_set="lightmap")
    assert info["success"], info
    assert info["context"]["uv_count"] == 4
    assert info["context"]["current_uv_set"] == "map1"
    result = _load_script("maya-uv-ops", "get_uv_shell_info").get_uv_shell_info(mesh, uv_set="lightmap")
    assert result["success"], result
    assert result["context"]["shell_count"] == 1
    shell = result["context"]["shells"][0]
    assert shell["uv_count"] == 4
    assert [shell[k] for k in ("u_min", "u_max", "v_min", "v_max")] == pytest.approx([2, 3, -3, -2])
    assert cmds.polyUVSet(mesh, query=True, currentUVSet=True) == ["map1"]
    assert cmds.ls(selection=True, long=True) == before_selection
    assert cmds.file(query=True, modified=True) == before_modified


def test_empty_uv_set_reads_as_zero():
    _new_scene()
    mesh = cmds.polyPlane(name="emptyUVs", subdivisionsX=1, subdivisionsY=1)[0]
    cmds.polyUVSet(mesh, create=True, uvSet="empty")
    info = _load_script("maya-uv-ops", "get_uv_info").get_uv_info(mesh, uv_set="empty")
    assert info["success"], info
    assert info["context"]["uv_count"] == 0
    result = _load_script("maya-uv-ops", "get_uv_shell_info").get_uv_shell_info(mesh, uv_set="empty")
    assert result["success"], result
    assert result["context"]["shell_count"] == 0
    assert cmds.polyUVSet(mesh, query=True, currentUVSet=True) == ["map1"]
