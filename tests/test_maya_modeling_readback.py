"""Regression tests for existing modeling-adjacent verbs that lacked readback."""

from __future__ import annotations

from unittest.mock import MagicMock

from conftest import load_and_call


def test_mirror_mesh_fails_when_polygon_topology_does_not_change():
    cmds = MagicMock()
    cmds.objExists.return_value = True
    cmds.polyEvaluate.side_effect = [12, 12]

    result = load_and_call(
        "maya-mesh-ops/scripts/mirror_mesh.py",
        cmds,
        "main",
        object_name="halfBody",
    )

    assert result["success"] is False
    assert "verification" in result["message"].lower()


def test_freeze_transforms_reads_back_identity_values():
    cmds = MagicMock()
    cmds.objExists.return_value = True
    cmds.getAttr.side_effect = [
        [(0.0, 0.0, 0.0)],
        [(0.0, 0.0, 0.0)],
        [(1.0, 1.0, 1.0)],
    ]

    result = load_and_call(
        "maya-scene/scripts/freeze_transforms.py",
        cmds,
        "main",
        object_name="body",
    )

    assert result["success"] is True, result
    assert result["context"]["verified_transform"]["scale"] == [1.0, 1.0, 1.0]


def test_freeze_transforms_fails_when_scale_is_not_identity():
    cmds = MagicMock()
    cmds.objExists.return_value = True
    cmds.getAttr.side_effect = [
        [(0.0, 0.0, 0.0)],
        [(0.0, 0.0, 0.0)],
        [(2.0, 1.0, 1.0)],
    ]

    result = load_and_call(
        "maya-scene/scripts/freeze_transforms.py",
        cmds,
        "main",
        object_name="body",
    )

    assert result["success"] is False
    assert "verification" in result["message"].lower()


def test_delete_history_fails_when_upstream_nodes_remain():
    cmds = MagicMock()
    cmds.objExists.return_value = True
    cmds.listRelatives.return_value = ["bodyShape"]
    cmds.listHistory.side_effect = [
        ["bodyShape", "polyExtrude1"],
        ["bodyShape", "polyExtrude1"],
    ]

    result = load_and_call(
        "maya-node-graph/scripts/delete_history.py",
        cmds,
        "main",
        object_name="body",
    )

    assert result["success"] is False
    assert result["context"]["remaining_history"] == ["polyExtrude1"]


def test_delete_history_ignores_shape_path_spelling_during_readback():
    cmds = MagicMock()
    cmds.objExists.return_value = True
    cmds.listRelatives.return_value = ["|body|bodyShape"]
    cmds.listHistory.side_effect = [["bodyShape", "polyExtrude1"], ["bodyShape"]]

    result = load_and_call(
        "maya-node-graph/scripts/delete_history.py",
        cmds,
        "main",
        object_name="|body",
    )

    assert result["success"] is True, result
    assert result["context"]["removed_history"] == ["polyExtrude1"]
