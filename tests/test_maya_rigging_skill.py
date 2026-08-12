import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock, patch

import yaml
from conftest import load_and_call, load_and_call_with_mel, load_skill_script


def test_create_curve_contract_remains_backward_compatible():
    cmds = MagicMock()
    cmds.curve.return_value = "legacy_curve"

    result = load_and_call(
        "maya-rigging/scripts/create_curve.py",
        cmds,
        points=[[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]],
        degree=1,
    )

    assert result["success"] is True, result
    assert result["context"]["object_name"] == "legacy_curve"
    assert result["context"]["point_count"] == 2
    cmds.curve.assert_called_once_with(
        point=[(0.0, 0.0, 0.0), (1.0, 0.0, 0.0)],
        degree=1,
        periodic=0,
    )


def test_create_guide_curve_schema_is_bounded_and_has_no_arbitrary_metadata():
    tools_path = Path(__file__).parent.parent / "src" / "dcc_mcp_maya" / "skills" / "maya-rigging" / "tools.yaml"
    tools = yaml.safe_load(tools_path.read_text(encoding="utf-8"))["tools"]
    spec = next(tool for tool in tools if tool["name"] == "create_guide_curve")
    schema = spec["input_schema"]

    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == {"points", "cluster_id", "display_color_rgb"}
    assert "metadata" not in schema["properties"]
    assert schema["properties"]["cluster_id"]["maxLength"] == 64
    assert schema["properties"]["display_color_rgb"]["items"] == {
        "type": "number",
        "minimum": 0.0,
        "maximum": 1.0,
    }
    assert schema["properties"]["root_to_tip"]["enum"] == [True]
    assert schema["properties"]["length_tolerance_ratio"]["maximum"] == 0.1


def test_create_guide_curve_sets_solid_rgb_and_typed_cluster_metadata():
    cmds = MagicMock()
    cmds.curve.return_value = "leftGuide01"
    cmds.listRelatives.return_value = ["leftGuide01Shape"]
    cmds.ls.return_value = []
    cmds.attributeQuery.return_value = False
    cmds.arclen.return_value = 10.0

    result = load_and_call(
        "maya-rigging/scripts/create_guide_curve.py",
        cmds,
        points=[[0.0, 0.0, 0.0], [0.0, 5.0, 0.0], [0.0, 10.0, 0.0]],
        cluster_id="left_green",
        display_color_rgb=[0.2, 1.0, 0.2],
        name="leftGuide01",
        degree=2,
        source_view="left",
        dominant_clump="left_sweep",
    )

    assert result["success"] is True, result
    typed = result["context"]["typed_result"]
    assert typed["transform"] == "leftGuide01"
    assert typed["shape"] == "leftGuide01Shape"
    assert typed["cluster_id"] == "left_green"
    assert typed["display_color_rgb"] == [0.2, 1.0, 0.2]
    assert typed["root_to_tip"] is True
    assert typed["root_position"] == [0.0, 0.0, 0.0]
    assert typed["tip_position"] == [0.0, 10.0, 0.0]
    assert typed["arc_length"] == 10.0
    assert typed["cluster_median_arc_length"] == 10.0
    assert typed["length_deviation_ratio"] == 0.0
    assert typed["root_projection_distance"] is None
    assert typed["source_view"] == "left"
    assert typed["dominant_clump"] == "left_sweep"
    cmds.setAttr.assert_any_call("leftGuide01Shape.overrideEnabled", True)
    cmds.setAttr.assert_any_call("leftGuide01Shape.overrideRGBColors", True)
    cmds.setAttr.assert_any_call("leftGuide01Shape.overrideColorRGB", 0.2, 1.0, 0.2)
    cmds.setAttr.assert_any_call("leftGuide01.dccGuideClusterId", "left_green", type="string")
    cmds.setAttr.assert_any_call("leftGuide01.dccGuideRootToTip", True)


def test_create_guide_curve_rejects_non_root_to_tip_before_scene_mutation():
    cmds = MagicMock()

    result = load_and_call(
        "maya-rigging/scripts/create_guide_curve.py",
        cmds,
        points=[[0.0, 0.0, 0.0], [0.0, 1.0, 0.0]],
        cluster_id="front_red",
        display_color_rgb=[1.0, 0.2, 0.2],
        degree=1,
        root_to_tip=False,
    )

    assert result["success"] is False, result
    cmds.curve.assert_not_called()


def test_create_guide_curve_rolls_back_length_outlier():
    cmds = MagicMock()
    cmds.curve.return_value = "outlierGuide"
    cmds.ls.return_value = ["existingGuideA", "existingGuideB"]
    cmds.getAttr.return_value = "crown_cyan"
    cmds.arclen.side_effect = lambda curve: 12.0 if curve == "outlierGuide" else 10.0

    result = load_and_call(
        "maya-rigging/scripts/create_guide_curve.py",
        cmds,
        points=[[0.0, 0.0, 0.0], [0.0, 12.0, 0.0]],
        cluster_id="crown_cyan",
        display_color_rgb=[0.2, 1.0, 1.0],
        degree=1,
    )

    assert result["success"] is False, result
    assert "10%" in result["message"]
    cmds.delete.assert_called_once_with("outlierGuide")


def test_create_guide_curve_accepts_exact_ten_percent_length_boundary():
    cmds = MagicMock()
    cmds.curve.return_value = "boundaryGuide"
    cmds.ls.return_value = ["existingGuideA", "existingGuideB"]
    cmds.getAttr.return_value = "crown_cyan"
    cmds.arclen.side_effect = lambda curve: 11.0 if curve == "boundaryGuide" else 10.0
    cmds.listRelatives.side_effect = lambda node, **_kwargs: ["boundaryGuideShape"] if node == "boundaryGuide" else []
    cmds.attributeQuery.return_value = False

    result = load_and_call(
        "maya-rigging/scripts/create_guide_curve.py",
        cmds,
        points=[[0.0, 0.0, 0.0], [0.0, 11.0, 0.0]],
        cluster_id="crown_cyan",
        display_color_rgb=[0.2, 1.0, 1.0],
        degree=1,
    )

    assert result["success"] is True, result
    assert result["context"]["typed_result"]["length_deviation_ratio"] <= 0.1 + 1e-12


def test_create_guide_curve_rejects_color_drift_within_cluster():
    cmds = MagicMock()
    cmds.ls.return_value = ["existingGuide"]
    cmds.listRelatives.return_value = ["existingGuideShape"]
    cmds.arclen.return_value = 10.0
    cmds.getAttr.side_effect = lambda plug: "left_green" if plug.endswith(".dccGuideClusterId") else [(0.2, 1.0, 0.2)]

    result = load_and_call(
        "maya-rigging/scripts/create_guide_curve.py",
        cmds,
        points=[[0.0, 0.0, 0.0], [0.0, 10.0, 0.0]],
        cluster_id="left_green",
        display_color_rgb=[1.0, 0.2, 0.2],
        degree=1,
    )

    assert result["success"] is False, result
    assert "color" in result["message"].lower() or "color" in result.get("error", "").lower()
    cmds.curve.assert_not_called()


def test_root_projection_distance_uses_explicit_mesh_world_space():
    module = load_skill_script("maya-rigging", "create_guide_curve")
    cmds = MagicMock()
    cmds.objExists.return_value = True
    cmds.nodeType.side_effect = lambda node: "mesh" if node.endswith("scalpShape") else "transform"
    cmds.listRelatives.return_value = ["|character:head|scalpShape"]

    selection = MagicMock()
    delta = MagicMock()
    delta.length.return_value = 0.25
    root_point = MagicMock()
    closest_point = MagicMock()
    closest_point.__sub__.return_value = delta
    mesh_fn = MagicMock()
    mesh_fn.getClosestPoint.return_value = (closest_point, 7)
    om = MagicMock()
    om.MSelectionList.return_value = selection
    om.MFnMesh.return_value = mesh_fn
    om.MPoint.return_value = root_point
    om.MSpace.kWorld = 4
    maya_module = ModuleType("maya")
    maya_api_module = ModuleType("maya.api")
    maya_api_module.OpenMaya = om
    maya_module.api = maya_api_module

    with patch.dict(sys.modules, {"maya": maya_module, "maya.api": maya_api_module}):
        distance, mesh_shape = module._root_projection_distance(
            cmds,
            "|character:head|scalp",
            [0.0, 1.0, 0.0],
        )

    assert distance == 0.25
    assert mesh_shape == "|character:head|scalpShape"
    selection.add.assert_called_once_with("|character:head|scalpShape")
    mesh_fn.getClosestPoint.assert_called_once_with(root_point, 4)


def test_create_root_joint_passes_an_empty_selection_for_maya_2024():
    cmds = MagicMock()
    cmds.joint.return_value = "root_jnt"

    result = load_and_call(
        "maya-rigging/scripts/create_joint.py",
        cmds,
        name="root_jnt",
        position=[0.0, 0.0, 0.0],
    )

    assert result["success"] is True, result
    cmds.select.assert_called_once_with([], clear=True)


def _rig_node_summary_mock(cmds: MagicMock, long_name: str = "|arm_ctrl", uuid: str = "uuid-arm-ctrl") -> None:
    def _ls(*args, **kwargs):
        if kwargs.get("uuid"):
            return [uuid]
        if kwargs.get("long"):
            return [long_name]
        if kwargs.get("type") == "skinCluster":
            return ["skinCluster1"]
        return [str(args[0])] if args else []

    def _get_attr(plug):
        if plug.endswith(".translate"):
            return [(0.0, 0.0, 0.0)]
        if plug.endswith(".rotate"):
            return [(0.0, 0.0, 0.0)]
        if plug.endswith(".scale"):
            return [(1.0, 1.0, 1.0)]
        if plug.endswith(".visibility"):
            return True
        return 1

    cmds.ls.side_effect = _ls
    cmds.objExists.return_value = True
    cmds.nodeType.return_value = "transform"
    cmds.objectType.return_value = "transform"
    cmds.getAttr.side_effect = _get_attr
    cmds.listRelatives.return_value = ["arm_ctrlShape"]
    cmds.exactWorldBoundingBox.return_value = [-1.0, -1.0, -1.0, 1.0, 1.0, 1.0]
    cmds.file.return_value = "C:/show/rig.ma"


def test_detect_rig_frameworks_uses_available_mel_signal():
    cmds = MagicMock()
    mel = MagicMock()
    mel.eval.return_value = "Mel procedure found in: MGToolsLoader"

    result = load_and_call_with_mel(
        "maya-rigging/scripts/detect_rig_frameworks.py",
        cmds,
        mel,
        frameworks=["mgtools"],
        include_unavailable=True,
    )

    assert result["success"] is True, result
    frameworks = result["context"]["frameworks"]
    assert frameworks[0]["name"] == "mgtools"
    assert frameworks[0]["available"] is True
    assert frameworks[0]["signals"]["mel_commands"] == ["MGToolsAutoLoader"]


def test_create_rig_control_builds_offset_group_and_constraint():
    cmds = MagicMock()
    _rig_node_summary_mock(cmds)
    cmds.curve.return_value = "arm_ctrl"
    cmds.group.return_value = "arm_ctrl_zero"
    cmds.parentConstraint.return_value = ["arm_parentConstraint1"]

    def _xform(*_args, **kwargs):
        if kwargs.get("query") and kwargs.get("matrix"):
            return [1.0, 0.0, 0.0, 0.0] * 4
        return None

    cmds.xform.side_effect = _xform

    result = load_and_call(
        "maya-rigging/scripts/create_rig_control.py",
        cmds,
        name="arm_ctrl",
        shape="square",
        size=2.0,
        target="arm_jnt",
        offset_groups=1,
        color_index=17,
        constrain_target=True,
    )

    assert result["success"] is True, result
    assert result["context"]["control"] == "arm_ctrl"
    assert result["context"]["top_node"] == "arm_ctrl_zero"
    assert result["context"]["constraints"] == ["arm_parentConstraint1"]
    cmds.curve.assert_called_once()
    cmds.group.assert_called_once_with(empty=True, name="arm_ctrl_zero")
    cmds.parent.assert_called_once_with("arm_ctrl", "arm_ctrl_zero")
    cmds.parentConstraint.assert_called_once_with("arm_ctrl", "arm_jnt", maintainOffset=True)
    cmds.setAttr.assert_any_call("arm_ctrlShape.overrideEnabled", True)
    cmds.setAttr.assert_any_call("arm_ctrlShape.overrideColor", 17)


def test_create_constraint_dispatches_parent_constraint():
    cmds = MagicMock()
    cmds.objExists.return_value = True
    cmds.parentConstraint.return_value = ["parentConstraint1"]

    result = load_and_call(
        "maya-rigging/scripts/create_constraint.py",
        cmds,
        drivers=["ctrlA", "ctrlB"],
        driven="joint1",
        constraint_type="parent",
        maintain_offset=False,
        weight=0.5,
        name="joint1_parentConstraint",
    )

    assert result["success"] is True, result
    assert result["context"]["constraints"] == ["parentConstraint1"]
    cmds.parentConstraint.assert_called_once_with(
        "ctrlA",
        "ctrlB",
        "joint1",
        weight=0.5,
        name="joint1_parentConstraint",
        maintainOffset=False,
    )


def test_query_skin_cluster_returns_influences_and_settings():
    cmds = MagicMock()
    cmds.objExists.return_value = True
    cmds.nodeType.return_value = "transform"
    cmds.listHistory.return_value = ["skinCluster1"]
    cmds.ls.return_value = ["skinCluster1"]

    def _skin_cluster(*_args, **kwargs):
        if kwargs.get("query") and kwargs.get("influence"):
            return ["root_jnt", "tip_jnt"]
        if kwargs.get("query") and kwargs.get("geometry"):
            return ["body_geoShape"]
        return []

    cmds.skinCluster.side_effect = _skin_cluster
    cmds.getAttr.side_effect = lambda plug: 4 if plug.endswith(".maxInfluences") else 1

    result = load_and_call(
        "maya-rigging/scripts/query_skin_cluster.py",
        cmds,
        node="body_geo",
    )

    assert result["success"] is True, result
    assert result["context"]["skin_cluster"] == "skinCluster1"
    assert result["context"]["influences"] == ["root_jnt", "tip_jnt"]
    assert result["context"]["max_influences"] == 4


def test_copy_skin_weights_finds_clusters_and_normalizes_target():
    cmds = MagicMock()
    cmds.objExists.return_value = True
    cmds.nodeType.return_value = "transform"
    cmds.listHistory.side_effect = lambda node: ["sourceSkin"] if node == "source_geo" else ["targetSkin"]
    cmds.ls.side_effect = lambda nodes, **kwargs: list(nodes) if kwargs.get("type") == "skinCluster" else []

    result = load_and_call(
        "maya-rigging/scripts/copy_skin_weights.py",
        cmds,
        source_mesh="source_geo",
        target_mesh="target_geo",
        mirror=True,
        mirror_mode="XZ",
    )

    assert result["success"] is True, result
    assert result["context"]["source_skin_cluster"] == "sourceSkin"
    assert result["context"]["target_skin_cluster"] == "targetSkin"
    cmds.copySkinWeights.assert_called_once_with(
        sourceSkin="sourceSkin",
        destinationSkin="targetSkin",
        noMirror=False,
        mirrorMode="XZ",
        surfaceAssociation="closestPoint",
        influenceAssociation=["closestJoint", "oneToOne", "name"],
    )
    cmds.skinCluster.assert_called_once_with("targetSkin", edit=True, forceNormalizeWeights=True)
