"""Transactional and boundedness regressions for typed animation and rigging."""

# Import built-in modules
from copy import deepcopy
from unittest.mock import MagicMock

# Import third-party modules
import pytest

# Import local modules
from conftest import load_and_call


@pytest.mark.parametrize("restore_on_undo", [True, False])
def test_set_keyframes_reports_verified_rollback_only_after_complete_readback(restore_on_undo):
    cmds = MagicMock()
    cmds.objExists.return_value = True
    cmds.currentUnit.return_value = "film"
    cmds.undoInfo.return_value = True
    state = {"rotorA.rotateY": {}, "rotorB.rotateY": {}}
    before = deepcopy(state)

    def _keyframe(plug, **kwargs):
        if kwargs.get("query") and kwargs.get("name"):
            return [plug.replace(".", "_")] if state[plug] else []
        if kwargs.get("query") and kwargs.get("timeChange"):
            return sorted(state[plug])
        if kwargs.get("query") and kwargs.get("valueChange"):
            return [state[plug][time] for time in sorted(state[plug])]
        return []

    def _set_keyframe(plug, **kwargs):
        state[plug][float(kwargs["time"])] = float(kwargs["value"])
        if plug == "rotorB.rotateY":
            raise RuntimeError("later target failed")

    def _undo():
        if restore_on_undo:
            state.clear()
            state.update(deepcopy(before))

    cmds.keyframe.side_effect = _keyframe
    cmds.setKeyframe.side_effect = _set_keyframe
    cmds.undo.side_effect = _undo

    result = load_and_call(
        "maya-animation/scripts/set_keyframes.py",
        cmds,
        objects=["rotorA", "rotorB"],
        attribute="rotateY",
        keys=[{"time": 1.0, "value": 90.0}],
    )

    assert result["success"] is False
    assert result["context"]["rollback_attempted"] is True
    assert result["context"]["rollback_verified"] is restore_on_undo
    assert (state == before) is restore_on_undo
    cmds.undo.assert_called_once_with()


def test_set_keyframes_does_not_verify_rollback_when_tangent_shape_state_survives_undo():
    cmds = MagicMock()
    cmds.objExists.return_value = True
    cmds.currentUnit.return_value = "film"
    cmds.undoInfo.return_value = True
    original = {
        "value": 1.0,
        "in_type": "fixed",
        "out_type": "fixed",
        "in_angle": 12.0,
        "out_angle": 24.0,
        "in_weight": 0.5,
        "out_weight": 0.75,
        "weighted": True,
        "lock": True,
        "weight_lock": True,
    }
    states = {"rotorA.rotateY": deepcopy(original), "rotorB.rotateY": deepcopy(original)}

    def _keyframe(plug, **kwargs):
        if kwargs.get("name"):
            return [plug.replace(".", "_")]
        if kwargs.get("keyframeCount"):
            return 1
        if kwargs.get("timeChange"):
            return [1.0]
        if kwargs.get("valueChange"):
            return [states[plug]["value"]]
        return []

    tangent_fields = {
        "inTangentType": "in_type",
        "outTangentType": "out_type",
        "inAngle": "in_angle",
        "outAngle": "out_angle",
        "inWeight": "in_weight",
        "outWeight": "out_weight",
        "weightedTangents": "weighted",
        "lock": "lock",
        "weightLock": "weight_lock",
    }

    def _key_tangent(plug, **kwargs):
        if kwargs.get("query"):
            for flag, field in tangent_fields.items():
                if kwargs.get(flag):
                    return [states[plug][field]]
            return []
        if kwargs.get("edit"):
            if "inTangentType" in kwargs:
                states[plug]["in_type"] = kwargs["inTangentType"]
            if "outTangentType" in kwargs:
                states[plug]["out_type"] = kwargs["outTangentType"]
        return []

    def _set_keyframe(plug, **kwargs):
        states[plug]["value"] = float(kwargs["value"])
        states[plug]["in_angle"] = 0.0
        states[plug]["out_angle"] = 0.0
        states[plug]["in_weight"] = 1.0
        states[plug]["out_weight"] = 1.0
        states[plug]["weighted"] = False
        states[plug]["lock"] = False
        states[plug]["weight_lock"] = False
        if plug == "rotorB.rotateY":
            raise RuntimeError("later target failed")

    def _undo():
        for state in states.values():
            state["value"] = original["value"]
            state["in_type"] = original["in_type"]
            state["out_type"] = original["out_type"]

    cmds.keyframe.side_effect = _keyframe
    cmds.keyTangent.side_effect = _key_tangent
    cmds.setKeyframe.side_effect = _set_keyframe
    cmds.getAttr.return_value = 0
    cmds.undo.side_effect = _undo

    result = load_and_call(
        "maya-animation/scripts/set_keyframes.py",
        cmds,
        objects=["rotorA", "rotorB"],
        attribute="rotateY",
        keys=[{"time": 1.0, "value": 90.0, "in_tangent": "linear", "out_tangent": "linear"}],
    )

    assert result["success"] is False
    assert result["context"]["rollback_attempted"] is True
    assert result["context"]["rollback_verified"] is False
    assert states["rotorA.rotateY"] != original


@pytest.mark.parametrize("restore_on_undo", [True, False])
def test_set_skin_weights_reports_verified_rollback_only_after_complete_readback(restore_on_undo):
    cmds = MagicMock()
    cmds.objExists.return_value = True
    cmds.listHistory.return_value = ["bodySkin"]
    cmds.ls.return_value = ["bodySkin"]
    cmds.polyEvaluate.return_value = 2
    cmds.skinCluster.return_value = ["root_jnt", "tip_jnt"]
    cmds.undoInfo.return_value = True
    state = {
        "body_geo.vtx[0]": [1.0, 0.0],
        "body_geo.vtx[1]": [0.0, 1.0],
    }
    before = deepcopy(state)

    def _skin_percent(_cluster, component, **kwargs):
        if kwargs.get("query") and kwargs.get("value"):
            return list(state[component])
        if "transformValue" in kwargs:
            values = dict(kwargs["transformValue"])
            state[component] = [values.get("root_jnt", 0.0), values.get("tip_jnt", 0.0)]
            if component.endswith("[1]"):
                raise RuntimeError("later vertex failed")
        return None

    def _undo():
        if restore_on_undo:
            state.clear()
            state.update(deepcopy(before))

    cmds.skinPercent.side_effect = _skin_percent
    cmds.undo.side_effect = _undo

    result = load_and_call(
        "maya-rigging/scripts/set_skin_weights.py",
        cmds,
        mesh="body_geo",
        vertices=[
            {
                "vertex": 0,
                "weights": [{"influence": "root_jnt", "weight": 0.75}, {"influence": "tip_jnt", "weight": 0.25}],
            },
            {
                "vertex": 1,
                "weights": [{"influence": "root_jnt", "weight": 0.25}, {"influence": "tip_jnt", "weight": 0.75}],
            },
        ],
    )

    assert result["success"] is False
    assert result["context"]["rollback_attempted"] is True
    assert result["context"]["rollback_verified"] is restore_on_undo
    assert (state == before) is restore_on_undo
    cmds.undo.assert_called_once_with()


def test_export_rig_state_rejects_constraint_overflow_before_target_reads():
    cmds = MagicMock()

    def _ls(*_args, **kwargs):
        if kwargs.get("type") == "parentConstraint":
            return ["constraint{}".format(index) for index in range(1025)]
        return []

    cmds.ls.side_effect = _ls

    result = load_and_call("maya-rigging/scripts/export_rig_state.py", cmds)

    assert result["success"] is False
    assert "constraint" in str(result).lower()
    cmds.parentConstraint.assert_not_called()


def test_export_rig_state_canonicalizes_explicit_dag_relationships_for_joinable_identity():
    cmds = MagicMock()
    canonical = {
        "root_jnt": "|rig|root_jnt",
        "child_jnt": "|rig|root_jnt|child_jnt",
        "main_ctrl": "|rig|main_ctrl",
    }

    def _ls(*args, **kwargs):
        if kwargs.get("type") == "parentConstraint":
            return ["parentConstraint1"]
        if kwargs.get("type") in {
            "pointConstraint",
            "orientConstraint",
            "scaleConstraint",
            "aimConstraint",
            "poleVectorConstraint",
        }:
            return []
        if kwargs.get("long") and args:
            return [canonical[args[0]]]
        return []

    def _relatives(node, **kwargs):
        if kwargs.get("type") == "joint":
            if node in {"root_jnt", "|rig|root_jnt"}:
                return []
            return ["|rig|root_jnt"]
        if kwargs.get("shapes") and node in {"main_ctrl", "|rig|main_ctrl"}:
            return ["|rig|main_ctrl|main_ctrlShape"]
        return []

    cmds.ls.side_effect = _ls
    cmds.objExists.return_value = True
    cmds.nodeType.return_value = "joint"
    cmds.listRelatives.side_effect = _relatives
    cmds.parentConstraint.return_value = ["root_jnt"]

    result = load_and_call(
        "maya-rigging/scripts/export_rig_state.py",
        cmds,
        joints=["child_jnt", "root_jnt"],
        skin_clusters=[],
        controls=["main_ctrl"],
    )

    assert result["success"] is True, result
    context = result["context"]
    joint_names = {row["name"] for row in context["joints"]["nodes"]}
    assert joint_names == {"|rig|root_jnt", "|rig|root_jnt|child_jnt"}
    assert all(row["parent"] is None or row["parent"] in joint_names for row in context["joints"]["nodes"])
    assert context["constraints"]["nodes"][0]["targets"] == ["|rig|root_jnt"]
    assert context["controls"]["nodes"] == [{"name": "|rig|main_ctrl", "shapes": ["|rig|main_ctrl|main_ctrlShape"]}]


def test_get_anim_curves_rejects_key_count_before_native_array_reads():
    cmds = MagicMock()
    cmds.objExists.return_value = True
    cmds.currentUnit.return_value = "film"
    array_reads = []

    def _keyframe(target, **kwargs):
        if kwargs.get("name"):
            return ["{}_curve".format(target.replace(".", "_"))]
        if kwargs.get("keyframeCount"):
            return 4097
        if kwargs.get("timeChange") or kwargs.get("valueChange"):
            array_reads.append((target, dict(kwargs)))
            return []
        return []

    def _key_tangent(target, **kwargs):
        array_reads.append((target, dict(kwargs)))
        return []

    cmds.keyframe.side_effect = _keyframe
    cmds.keyTangent.side_effect = _key_tangent

    result = load_and_call(
        "maya-animation/scripts/get_anim_curves.py",
        cmds,
        targets=["rotorA.rotateY"],
    )

    assert result["success"] is False
    assert "key limit" in str(result).lower()
    assert array_reads == []


def test_set_keyframes_rejects_aggregate_snapshot_count_before_native_array_reads():
    cmds = MagicMock()
    cmds.objExists.return_value = True
    cmds.currentUnit.return_value = "film"
    array_reads = []

    def _keyframe(plug, **kwargs):
        if kwargs.get("name"):
            return [plug.replace(".", "_")]
        if kwargs.get("keyframeCount"):
            return 40000
        if kwargs.get("timeChange") or kwargs.get("valueChange"):
            array_reads.append((plug, dict(kwargs)))
            return []
        return []

    def _key_tangent(plug, **kwargs):
        array_reads.append((plug, dict(kwargs)))
        return []

    cmds.keyframe.side_effect = _keyframe
    cmds.keyTangent.side_effect = _key_tangent

    result = load_and_call(
        "maya-animation/scripts/set_keyframes.py",
        cmds,
        objects=["rotorA", "rotorB"],
        attribute="rotateY",
        keys=[{"time": 1.0, "value": 90.0}],
    )

    assert result["success"] is False
    assert "snapshot" in str(result).lower()
    assert array_reads == []
    cmds.setKeyframe.assert_not_called()


@pytest.mark.parametrize(
    "script",
    [
        "maya-rigging/scripts/get_skin_weights.py",
        "maya-rigging/scripts/set_skin_weights.py",
    ],
)
def test_skin_weight_tools_reject_ambiguous_history_before_native_reads(script):
    cmds = MagicMock()
    cmds.objExists.return_value = True
    cmds.listHistory.return_value = ["bodySkinA", "bodySkinB"]
    cmds.ls.return_value = ["bodySkinA", "bodySkinB"]

    kwargs = {"mesh": "body_geo"}
    if script.endswith("set_skin_weights.py"):
        kwargs["vertices"] = [
            {
                "vertex": 0,
                "weights": [{"influence": "root_jnt", "weight": 1.0}],
            }
        ]
    result = load_and_call(script, cmds, **kwargs)

    assert result["success"] is False
    assert "exactly one" in str(result).lower()
    cmds.skinCluster.assert_not_called()
    cmds.skinPercent.assert_not_called()
