# Import built-in modules
from pathlib import Path
from unittest.mock import MagicMock

# Import third-party modules
import yaml

# Import local modules
from conftest import load_and_call

SKILLS_ROOT = Path(__file__).parent.parent / "src" / "dcc_mcp_maya" / "skills"


def _tool(skill_name, tool_name):
    tools_path = SKILLS_ROOT / skill_name / "tools.yaml"
    tools = yaml.safe_load(tools_path.read_text(encoding="utf-8"))["tools"]
    return next(tool for tool in tools if tool["name"] == tool_name)


def test_typed_animation_and_rigging_tools_declare_complete_execution_contracts():
    declarations = (
        ("maya-animation", "set_keyframes", False, True),
        ("maya-animation", "get_anim_curves", True, False),
        ("maya-rigging", "get_skin_weights", True, False),
        ("maya-rigging", "set_skin_weights", False, True),
        ("maya-rigging", "export_rig_state", True, False),
    )
    for skill_name, tool_name, read_only, destructive in declarations:
        spec = _tool(skill_name, tool_name)
        assert spec["execution"] == "async"
        assert spec["affinity"] == "main"
        assert spec["timeout_hint_secs"] > 0
        assert spec["annotations"]["read_only_hint"] is read_only
        assert spec["annotations"]["destructive_hint"] is destructive
        assert spec["annotations"]["open_world_hint"] is False


def test_set_keyframes_batches_multiple_objects_and_reads_back_values():
    spec = _tool("maya-animation", "set_keyframes")
    assert spec["affinity"] == "main"
    assert spec["input_schema"]["properties"]["objects"]["maxItems"] == 32
    assert spec["input_schema"]["properties"]["keys"]["maxItems"] == 512

    cmds = MagicMock()
    cmds.objExists.return_value = True
    cmds.currentUnit.return_value = "film"

    def _keyframe(_target, **kwargs):
        if kwargs.get("name"):
            return ["{}_rotateY".format(_target.split(".")[0])]
        if kwargs.get("query") and kwargs.get("timeChange"):
            return [1.0, 24.0]
        if kwargs.get("query") and kwargs.get("valueChange"):
            return [0.0, 360.0]
        return []

    cmds.keyframe.side_effect = _keyframe
    cmds.keyTangent.return_value = ["linear"]
    cmds.getAttr.return_value = 0

    result = load_and_call(
        "maya-animation/scripts/set_keyframes.py",
        cmds,
        objects=["rotorA", "rotorB"],
        attribute="rotateY",
        keys=[
            {"time": 1.0, "value": 0.0, "in_tangent": "linear", "out_tangent": "linear"},
            {"time": 24.0, "value": 360.0, "in_tangent": "linear", "out_tangent": "linear"},
        ],
    )

    assert result["success"] is True, result
    assert result["context"]["schema"] == "dcc-mcp/anim-curves@1"
    assert result["context"]["fps"] == 24.0
    assert [curve["target"] for curve in result["context"]["curves"]] == [
        "rotorA.rotateY",
        "rotorB.rotateY",
    ]
    assert all(curve["key_count"] == 2 for curve in result["context"]["curves"])
    assert all(curve["pre_infinity"] == "constant" for curve in result["context"]["curves"])
    assert all(curve["post_infinity"] == "constant" for curve in result["context"]["curves"])
    assert cmds.setKeyframe.call_count == 4


def test_set_keyframes_fails_closed_when_native_readback_differs():
    cmds = MagicMock()
    cmds.objExists.return_value = True
    cmds.keyframe.side_effect = lambda _target, **kwargs: [1.0] if kwargs.get("timeChange") else [2.0]

    result = load_and_call(
        "maya-animation/scripts/set_keyframes.py",
        cmds,
        objects=["rotorA"],
        attribute="rotateY",
        keys=[{"time": 1.0, "value": 1.0}],
    )

    assert result["success"] is False, result
    assert "readback" in str(result).lower()


def test_set_keyframes_fails_closed_on_non_finite_native_readback():
    cmds = MagicMock()
    cmds.objExists.return_value = True
    cmds.currentUnit.return_value = "film"

    def _keyframe(_target, **kwargs):
        if kwargs.get("name"):
            return ["rotorA_rotateY"]
        if kwargs.get("timeChange"):
            return [1.0]
        if kwargs.get("valueChange"):
            return [float("nan")]
        return []

    cmds.keyframe.side_effect = _keyframe
    cmds.keyTangent.return_value = ["linear"]
    cmds.getAttr.return_value = 0

    result = load_and_call(
        "maya-animation/scripts/set_keyframes.py",
        cmds,
        objects=["rotorA"],
        attribute="rotateY",
        keys=[{"time": 1.0, "value": 1.0}],
    )

    assert result["success"] is False, result
    assert "non-finite" in str(result)


def test_get_anim_curves_returns_values_tangents_and_infinity():
    spec = _tool("maya-animation", "get_anim_curves")
    assert spec["annotations"]["read_only_hint"] is True
    assert spec["input_schema"]["properties"]["targets"]["maxItems"] == 128

    cmds = MagicMock()
    cmds.objExists.return_value = True
    cmds.currentUnit.return_value = "film"

    def _keyframe(_target, **kwargs):
        if kwargs.get("name"):
            return ["rotorA_rotateY"]
        if kwargs.get("timeChange"):
            return [1.0, 24.0]
        if kwargs.get("valueChange"):
            return [0.0, 360.0]
        return []

    def _key_tangent(_target, **kwargs):
        if kwargs.get("inTangentType"):
            return ["linear", "linear"]
        if kwargs.get("outTangentType"):
            return ["linear", "linear"]
        return []

    cmds.keyframe.side_effect = _keyframe
    cmds.keyTangent.side_effect = _key_tangent
    cmds.getAttr.side_effect = lambda plug: 0 if plug.endswith(".preInfinity") else 2

    result = load_and_call(
        "maya-animation/scripts/get_anim_curves.py",
        cmds,
        targets=["rotorA.rotateY"],
    )

    assert result["success"] is True, result
    assert result["context"]["schema"] == "dcc-mcp/anim-curves@1"
    assert result["context"]["fps"] == 24.0
    assert result["context"]["curves"] == [
        {
            "target": "rotorA.rotateY",
            "keys": [
                {"t": 1.0, "v": 0.0, "in": "linear", "out": "linear"},
                {"t": 24.0, "v": 360.0, "in": "linear", "out": "linear"},
            ],
            "pre_infinity": "constant",
            "post_infinity": "cycle",
            "key_count": 2,
        }
    ]


def test_get_anim_curves_fails_closed_on_misaligned_native_arrays():
    cmds = MagicMock()
    cmds.objExists.return_value = True
    cmds.currentUnit.return_value = "film"

    def _keyframe(_target, **kwargs):
        if kwargs.get("name"):
            return ["rotorA_rotateY"]
        if kwargs.get("timeChange"):
            return [1.0, 24.0]
        if kwargs.get("valueChange"):
            return [0.0]
        return []

    cmds.keyframe.side_effect = _keyframe
    cmds.keyTangent.return_value = ["linear", "linear"]
    cmds.getAttr.return_value = 0

    result = load_and_call(
        "maya-animation/scripts/get_anim_curves.py",
        cmds,
        targets=["rotorA.rotateY"],
    )

    assert result["success"] is False, result
    assert "misaligned" in result["message"].lower() or "misaligned" in str(result).lower()


def test_get_anim_curves_fails_closed_on_non_finite_native_values():
    cmds = MagicMock()
    cmds.objExists.return_value = True
    cmds.currentUnit.return_value = "film"

    def _keyframe(_target, **kwargs):
        if kwargs.get("name"):
            return ["rotorA_rotateY"]
        if kwargs.get("timeChange"):
            return [1.0]
        if kwargs.get("valueChange"):
            return [float("nan")]
        return []

    cmds.keyframe.side_effect = _keyframe
    cmds.keyTangent.return_value = ["linear"]
    cmds.getAttr.return_value = 0

    result = load_and_call(
        "maya-animation/scripts/get_anim_curves.py",
        cmds,
        targets=["rotorA.rotateY"],
    )

    assert result["success"] is False, result
    assert "non-finite" in str(result)


def test_get_skin_weights_returns_per_vertex_normalization_evidence():
    spec = _tool("maya-rigging", "get_skin_weights")
    assert spec["annotations"]["read_only_hint"] is True
    assert spec["input_schema"]["properties"]["vertices"]["maxItems"] == 4096

    cmds = MagicMock()
    cmds.objExists.return_value = True
    cmds.nodeType.return_value = "transform"
    cmds.listHistory.return_value = ["bodySkin"]
    cmds.ls.return_value = ["bodySkin"]
    cmds.polyEvaluate.return_value = 2

    def _skin_cluster(_node, **kwargs):
        if kwargs.get("query") and kwargs.get("influence"):
            return ["root_jnt", "tip_jnt"]
        return []

    def _skin_percent(_cluster, component, **kwargs):
        if kwargs.get("query") and kwargs.get("value"):
            return [0.75, 0.25] if component.endswith("[0]") else [0.2, 0.8]
        return None

    cmds.skinCluster.side_effect = _skin_cluster
    cmds.skinPercent.side_effect = _skin_percent

    result = load_and_call(
        "maya-rigging/scripts/get_skin_weights.py",
        cmds,
        mesh="body_geo",
    )

    assert result["success"] is True, result
    assert result["context"]["schema"] == "dcc-mcp/skin-weights@1"
    assert result["context"]["skin_cluster"] == "bodySkin"
    assert result["context"]["vertex_count"] == 2
    assert result["context"]["unnormalized_vertices"] == 0
    assert result["context"]["vertices"][0] == {
        "vertex": 0,
        "weights": [
            {"influence": "root_jnt", "weight": 0.75},
            {"influence": "tip_jnt", "weight": 0.25},
        ],
        "total_weight": 1.0,
    }


def test_get_skin_weights_rejects_oversized_weight_matrix_before_native_reads():
    cmds = MagicMock()
    cmds.objExists.return_value = True
    cmds.listHistory.return_value = ["bodySkin"]
    cmds.ls.return_value = ["bodySkin"]
    cmds.polyEvaluate.return_value = 300
    cmds.skinCluster.return_value = ["joint_{}".format(index) for index in range(256)]

    result = load_and_call(
        "maya-rigging/scripts/get_skin_weights.py",
        cmds,
        mesh="body_geo",
    )

    assert result["success"] is False, result
    assert "weight-value limit" in str(result)
    cmds.skinPercent.assert_not_called()


def test_set_skin_weights_replaces_rows_and_verifies_native_readback():
    spec = _tool("maya-rigging", "set_skin_weights")
    assert spec["affinity"] == "main"
    assert spec["input_schema"]["properties"]["vertices"]["maxItems"] == 4096

    cmds = MagicMock()
    cmds.objExists.return_value = True
    cmds.nodeType.return_value = "transform"
    cmds.listHistory.return_value = ["bodySkin"]
    cmds.ls.return_value = ["bodySkin"]
    cmds.polyEvaluate.return_value = 2
    cmds.skinCluster.return_value = ["root_jnt", "tip_jnt"]
    written = {}

    def _skin_percent(_cluster, component, **kwargs):
        if "transformValue" in kwargs:
            written[component] = dict(kwargs["transformValue"])
            return None
        if kwargs.get("query") and kwargs.get("value"):
            row = written[component]
            return [row["root_jnt"], row["tip_jnt"]]
        return None

    cmds.skinPercent.side_effect = _skin_percent

    result = load_and_call(
        "maya-rigging/scripts/set_skin_weights.py",
        cmds,
        mesh="body_geo",
        vertices=[
            {
                "vertex": 0,
                "weights": [
                    {"influence": "root_jnt", "weight": 0.75},
                    {"influence": "tip_jnt", "weight": 0.25},
                ],
            },
            {
                "vertex": 1,
                "weights": [
                    {"influence": "root_jnt", "weight": 0.2},
                    {"influence": "tip_jnt", "weight": 0.8},
                ],
            },
        ],
    )

    assert result["success"] is True, result
    assert result["context"]["schema"] == "dcc-mcp/skin-weights@1"
    assert result["context"]["verified_vertex_count"] == 2
    assert result["context"]["unnormalized_vertices"] == 0
    assert cmds.skinPercent.call_count == 4
    first_write = cmds.skinPercent.call_args_list[0]
    assert first_write[1]["normalize"] is True
    assert first_write[1]["zeroRemainingInfluences"] is True


def test_set_skin_weights_rejects_untyped_values_before_mutation():
    cmds = MagicMock()
    cmds.objExists.return_value = True
    cmds.listHistory.return_value = ["bodySkin"]
    cmds.ls.return_value = ["bodySkin"]
    cmds.polyEvaluate.return_value = 2
    cmds.skinCluster.return_value = ["root_jnt", "tip_jnt"]

    result = load_and_call(
        "maya-rigging/scripts/set_skin_weights.py",
        cmds,
        mesh="body_geo",
        vertices=[
            {
                "vertex": 0,
                "weights": [
                    {"influence": "root_jnt", "weight": "0.5"},
                    {"influence": "tip_jnt", "weight": 0.5},
                ],
            }
        ],
    )

    assert result["success"] is False, result
    assert "numbers" in str(result)
    cmds.skinPercent.assert_not_called()


def test_set_skin_weights_fails_closed_when_native_readback_differs():
    cmds = MagicMock()
    cmds.objExists.return_value = True
    cmds.listHistory.return_value = ["bodySkin"]
    cmds.ls.return_value = ["bodySkin"]
    cmds.polyEvaluate.return_value = 1
    cmds.skinCluster.return_value = ["root_jnt", "tip_jnt"]
    cmds.skinPercent.side_effect = [None, [0.5, 0.5]]

    result = load_and_call(
        "maya-rigging/scripts/set_skin_weights.py",
        cmds,
        mesh="body_geo",
        vertices=[
            {
                "vertex": 0,
                "weights": [
                    {"influence": "root_jnt", "weight": 0.75},
                    {"influence": "tip_jnt", "weight": 0.25},
                ],
            }
        ],
    )

    assert result["success"] is False, result
    assert "verification" in str(result).lower()


def test_export_rig_state_reports_hierarchy_constraints_controls_and_skin_health():
    spec = _tool("maya-rigging", "export_rig_state")
    assert spec["annotations"]["read_only_hint"] is True
    assert spec["input_schema"]["properties"]["joints"]["maxItems"] == 4096

    cmds = MagicMock()

    def _ls(*_args, **kwargs):
        node_type = kwargs.get("type")
        return {
            "joint": ["root_jnt", "tip_jnt"],
            "skinCluster": ["bodySkin"],
            "parentConstraint": ["hand_parentConstraint"],
            "pointConstraint": [],
            "orientConstraint": [],
            "scaleConstraint": [],
            "aimConstraint": [],
            "poleVectorConstraint": [],
            "nurbsCurve": ["hand_ctrlShape"],
        }.get(node_type, [])

    def _relatives(node, **kwargs):
        if kwargs.get("parent") and kwargs.get("type") == "joint":
            return ["root_jnt"] if node == "tip_jnt" else []
        if kwargs.get("parent") and node == "hand_ctrlShape":
            return ["hand_ctrl"]
        if kwargs.get("shapes") and node == "hand_ctrl":
            return ["hand_ctrlShape"]
        return []

    def _skin_cluster(_node, **kwargs):
        if kwargs.get("influence"):
            return ["root_jnt", "tip_jnt"]
        if kwargs.get("geometry"):
            return ["body_geo"]
        return []

    cmds.ls.side_effect = _ls
    cmds.listRelatives.side_effect = _relatives
    cmds.skinCluster.side_effect = _skin_cluster
    cmds.parentConstraint.return_value = ["root_jnt"]
    cmds.polyEvaluate.return_value = 2
    cmds.skinPercent.side_effect = lambda _cluster, component, **_kwargs: (
        [0.75, 0.25] if component.endswith("[0]") else [0.2, 0.8]
    )

    result = load_and_call(
        "maya-rigging/scripts/export_rig_state.py",
        cmds,
    )

    assert result["success"] is True, result
    state = result["context"]
    assert state["schema"] == "dcc-mcp/rig-state@1"
    assert state["joints"]["count"] == 2
    assert state["joints"]["nodes"][1]["parent"] == "root_jnt"
    assert state["constraints"]["nodes"][0]["targets"] == ["root_jnt"]
    assert state["controls"]["nodes"] == [{"name": "hand_ctrl", "shapes": ["hand_ctrlShape"]}]
    assert state["skins"][0]["unnormalized_vertices"] == 0
