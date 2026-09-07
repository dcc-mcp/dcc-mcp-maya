"""UV reads must respect the requested set, coordinate layout and read-only contract."""

import sys
from types import ModuleType
from unittest.mock import MagicMock

import pytest
from conftest import load_and_call


def _cmds():
    cmds = MagicMock()
    cmds.objExists.return_value = True
    cmds.polyUVSet.side_effect = lambda *a, **kw: ["map1", "lightmap"] if kw.get("allUVSets") else ["map1"]
    return cmds


@pytest.fixture
def mesh_api(monkeypatch):
    api = ModuleType("maya.api")
    api.OpenMaya = MagicMock()
    monkeypatch.setitem(sys.modules, "maya.api", api)
    return api.OpenMaya.MFnMesh.return_value


@pytest.mark.parametrize("count", [0, 4, 100_000])
def test_uv_count_uses_requested_set_without_fetching_coordinates(count):
    cmds = _cmds()
    cmds.polyEvaluate.return_value = count
    result = load_and_call("maya-uv-ops/scripts/get_uv_info.py", cmds, object_name="mesh", uv_set="lightmap")
    assert result["success"], result
    assert result["context"]["uv_count"] == count
    assert result["context"]["current_uv_set"] == "map1"
    cmds.polyEvaluate.assert_called_once_with("mesh", uvcoord=True, uvSetName="lightmap")
    cmds.polyEditUV.assert_not_called()
    assert all(call.kwargs.get("query") for call in cmds.polyUVSet.call_args_list)


def test_shell_bounds_use_named_coordinates_without_switching_set(mesh_api):
    cmds = _cmds()
    mesh_api.getUvShellsIds.return_value = (2, [0, 0, 1, 1])
    mesh_api.getUVs.return_value = ([2.0, 4.0, 10.0, 11.0], [-3.0, -1.0, 20.0, 22.0])
    result = load_and_call("maya-uv-ops/scripts/get_uv_shell_info.py", cmds, object_name="mesh", uv_set="lightmap")
    assert result["success"], result
    assert result["context"]["uv_set"] == "lightmap"
    assert result["context"]["shell_count"] == 2
    assert result["context"]["shells"][0] == {
        "shell_id": 0,
        "uv_count": 2,
        "u_min": 2.0,
        "u_max": 4.0,
        "v_min": -3.0,
        "v_max": -1.0,
    }
    assert result["context"]["shells"][1]["v_max"] == 22.0
    mesh_api.getUvShellsIds.assert_called_once_with("lightmap")
    mesh_api.getUVs.assert_called_once_with("lightmap")
    cmds.polyEditUV.assert_not_called()
    assert all(call.kwargs.get("query") for call in cmds.polyUVSet.call_args_list)


def test_shell_read_failure_does_not_change_active_set(mesh_api):
    cmds = _cmds()
    mesh_api.getUvShellsIds.side_effect = RuntimeError("mesh read failed")
    result = load_and_call("maya-uv-ops/scripts/get_uv_shell_info.py", cmds, object_name="mesh", uv_set="lightmap")
    assert not result["success"]
    assert all(call.kwargs.get("query") for call in cmds.polyUVSet.call_args_list)


def test_shell_readback_rejects_misaligned_coordinates(mesh_api):
    cmds = _cmds()
    mesh_api.getUvShellsIds.return_value = (1, [0, 0])
    mesh_api.getUVs.return_value = ([1.0], [2.0])
    result = load_and_call("maya-uv-ops/scripts/get_uv_shell_info.py", cmds, object_name="mesh", uv_set="lightmap")
    assert not result["success"]


@pytest.mark.parametrize("tool", ["get_uv_info", "get_uv_shell_info"])
def test_unknown_set_fails_before_uv_reads(tool):
    cmds = _cmds()
    result = load_and_call("maya-uv-ops/scripts/{}.py".format(tool), cmds, object_name="mesh", uv_set="missing")
    assert not result["success"]
    cmds.polyEvaluate.assert_not_called()
    cmds.polyEditUV.assert_not_called()
