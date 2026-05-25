from unittest.mock import MagicMock

from conftest import load_and_call, load_and_call_with_mel


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
