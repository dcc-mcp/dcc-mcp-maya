"""Contract tests for the Maya cross-DCC modeling validation skill."""

from __future__ import annotations

from unittest.mock import MagicMock

from conftest import load_and_call


def _export_cmds():
    cmds = MagicMock()

    def _ls(*args, **kwargs):
        if kwargs.get("type") == "mesh":
            return ["|asset|bodyShape"]
        return ["|asset|body"]

    def _node_type(node):
        if str(node).endswith("Shape"):
            return "mesh"
        if str(node) == "polyBevel1":
            return "polyBevel3"
        return "transform"

    def _list_relatives(node, **kwargs):
        if kwargs.get("parent"):
            return ["|asset|body"]
        if kwargs.get("type") == "mesh":
            return ["|asset|bodyShape"]
        return []

    def _poly_evaluate(_node, **kwargs):
        return {
            "vertex": 8,
            "edge": 12,
            "face": 6,
            "uvcoord": 14,
        }.get(next(iter(kwargs)), 0)

    def _list_connections(node, **kwargs):
        if str(node).endswith(".instObjGroups"):
            return ["bodySG"]
        if str(node).endswith(".surfaceShader"):
            return ["bodyMaterial"]
        return []

    def _get_attr(attribute):
        if attribute == "|asset|body.scale":
            return [(1.0, 1.0, 1.0)]
        if attribute.endswith(".offset"):
            return 0.25
        if attribute.endswith(".segments"):
            return 2
        return 0

    cmds.ls.side_effect = _ls
    cmds.nodeType.side_effect = _node_type
    cmds.listRelatives.side_effect = _list_relatives
    cmds.polyEvaluate.side_effect = _poly_evaluate
    cmds.polyUVSet.return_value = ["map1"]
    cmds.listConnections.side_effect = _list_connections
    cmds.polyInfo.return_value = None
    cmds.exactWorldBoundingBox.return_value = [-1.0, 0.0, -1.0, 1.0, 2.0, 1.0]
    cmds.xform.side_effect = lambda _node, **kwargs: (
        [0.0, 1.0, 0.0]
        if kwargs.get("translation")
        else [0.0, 0.0, 0.0]
        if kwargs.get("rotation")
        else [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        if kwargs.get("pivots")
        else None
    )
    cmds.listHistory.return_value = ["polyBevel1"]
    cmds.getAttr.side_effect = _get_attr
    return cmds


def test_export_model_state_has_versioned_core_shape_and_native_evidence():
    cmds = _export_cmds()
    result = load_and_call(
        "maya-modeling-validation/scripts/export_model_state.py",
        cmds,
        object_names=["body"],
    )

    assert result["success"] is True, result
    state = result["context"]["state"]
    assert state["schema_name"] == "dcc-mcp/model-state"
    assert state["schema_version"] == 1
    assert state["parts"] == ["body"]
    assert state["meshes"][0]["vertex_count"] == 8
    assert state["meshes"][0]["uv_sets"] == 1
    assert state["meshes"][0]["material"] == "bodyMaterial"
    assert state["meshes"][0]["is_non_manifold"] is False
    assert state["objects"][0]["native_history"][0]["type"] == "polyBevel3"


def test_export_model_state_marks_unavailable_non_manifold_evidence():
    cmds = _export_cmds()
    cmds.polyInfo.side_effect = RuntimeError("native query unavailable")

    result = load_and_call(
        "maya-modeling-validation/scripts/export_model_state.py",
        cmds,
        object_names=["body"],
    )

    assert result["success"] is True, result
    state = result["context"]["state"]
    assert state["partial"] is True
    assert "non_manifold" in state["unavailable"]


def test_align_reference_is_read_only_until_apply_is_requested():
    cmds = MagicMock()
    cmds.objExists.return_value = True
    cmds.exactWorldBoundingBox.side_effect = [
        [-1.0, -1.0, -1.0, 1.0, 1.0, 1.0],
        [0.0, 0.0, 0.0, 4.0, 4.0, 4.0],
    ]

    result = load_and_call(
        "maya-modeling-validation/scripts/align_reference.py",
        cmds,
        object_name="model",
        reference_object="reference",
        apply=False,
    )

    assert result["success"] is True, result
    assert result["context"]["applied"] is False
    assert result["context"]["scale_ratio"] == 2.0
    cmds.scale.assert_not_called()
    cmds.move.assert_not_called()


def test_verify_modeling_operation_reads_native_parameters():
    cmds = MagicMock()
    cmds.objExists.return_value = True
    cmds.listHistory.return_value = ["bevel1"]
    cmds.nodeType.return_value = "polyBevel3"
    cmds.getAttr.side_effect = lambda attr: 0.25 if attr.endswith(".offset") else 2

    result = load_and_call(
        "maya-modeling-validation/scripts/verify_modeling_operation.py",
        cmds,
        object_name="body",
        operation="bevel",
        expected={"offset": 0.25, "segments": 2},
    )

    assert result["success"] is True, result
    assert result["context"]["status"] == "pass"
    assert result["context"]["evidence"]["native_history"][0]["type"] == "polyBevel3"


def test_verify_modeling_operation_reports_unknown_when_pivot_readback_is_missing():
    cmds = MagicMock()
    cmds.objExists.return_value = True
    cmds.xform.return_value = None

    result = load_and_call(
        "maya-modeling-validation/scripts/verify_modeling_operation.py",
        cmds,
        object_name="body",
        operation="pivot",
    )

    assert result["success"] is True, result
    assert result["context"]["status"] == "unknown"
    assert result["context"]["actionable_error"]
