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
