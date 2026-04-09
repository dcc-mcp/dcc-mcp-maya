"""Tests for Round 4 new actions: delete_keyframes, bake_simulation,
set_joint_orient, mirror_joints, create_ik_handle.

All tests mock maya.cmds so no real Maya installation is required.
"""

# Import future modules
from __future__ import annotations

# Import built-in modules
import sys
from unittest.mock import MagicMock, call, patch

# Import third-party modules
import pytest


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _reload():
    """Remove all dcc_mcp_maya modules so imports pick up fresh mocks."""
    for mod in list(sys.modules):
        if "dcc_mcp_maya" in mod:
            del sys.modules[mod]


def _no_maya():
    return patch.dict(sys.modules, {"maya": None, "maya.cmds": None})


@pytest.fixture()
def mock_maya():
    """Standard Maya mock with sane defaults."""
    cmds_mock = MagicMock()
    cmds_mock.objExists.return_value = True
    cmds_mock.objectType.return_value = "joint"
    cmds_mock.cutKey.return_value = 3
    cmds_mock.ls.return_value = ["pSphere1", "pCube1"]
    cmds_mock.mirrorJoint.return_value = ["R_shoulder", "R_elbow", "R_wrist"]
    cmds_mock.ikHandle.return_value = ["ikHandle1", "effector1"]

    with patch.dict(
        sys.modules,
        {
            "maya": MagicMock(cmds=cmds_mock, utils=MagicMock()),
            "maya.cmds": cmds_mock,
            "maya.utils": MagicMock(),
        },
    ):
        yield cmds_mock


# ===========================================================================
# delete_keyframes
# ===========================================================================

class TestDeleteKeyframes:
    def test_delete_all_keyframes(self, mock_maya):
        _reload()
        from dcc_mcp_maya.actions.animation import delete_keyframes

        result = delete_keyframes("pSphere1")
        assert result["success"] is True
        assert result["context"]["deleted_count"] == 3
        mock_maya.cutKey.assert_called_once_with("pSphere1", clear=True)

    def test_delete_with_frame_range(self, mock_maya):
        _reload()
        from dcc_mcp_maya.actions.animation import delete_keyframes

        result = delete_keyframes("pSphere1", start_frame=1.0, end_frame=30.0)
        assert result["success"] is True
        mock_maya.cutKey.assert_called_once_with(
            "pSphere1", clear=True, time=(1.0, 30.0)
        )

    def test_delete_with_start_only(self, mock_maya):
        _reload()
        from dcc_mcp_maya.actions.animation import delete_keyframes

        delete_keyframes("pSphere1", start_frame=10.0)
        call_kwargs = mock_maya.cutKey.call_args
        assert call_kwargs[1]["time"] == (10.0, 10.0)

    def test_delete_with_end_only(self, mock_maya):
        _reload()
        from dcc_mcp_maya.actions.animation import delete_keyframes

        delete_keyframes("pSphere1", end_frame=20.0)
        call_kwargs = mock_maya.cutKey.call_args
        assert call_kwargs[1]["time"] == (20.0, 20.0)

    def test_delete_with_attributes(self, mock_maya):
        _reload()
        from dcc_mcp_maya.actions.animation import delete_keyframes

        result = delete_keyframes("pSphere1", attributes=["tx", "ty"])
        assert result["success"] is True
        call_kwargs = mock_maya.cutKey.call_args
        assert call_kwargs[1]["attribute"] == ["tx", "ty"]

    def test_delete_object_not_found(self, mock_maya):
        _reload()
        mock_maya.objExists.return_value = False
        from dcc_mcp_maya.actions.animation import delete_keyframes

        result = delete_keyframes("ghost")
        assert result["success"] is False
        assert "ghost" in result["message"]

    def test_delete_exception(self, mock_maya):
        _reload()
        mock_maya.cutKey.side_effect = RuntimeError("locked curve")
        from dcc_mcp_maya.actions.animation import delete_keyframes

        result = delete_keyframes("pSphere1")
        assert result["success"] is False

    def test_delete_no_maya(self):
        _reload()
        with _no_maya():
            for mod in list(sys.modules):
                if "dcc_mcp_maya.actions" in mod:
                    del sys.modules[mod]
            from dcc_mcp_maya.actions.animation import delete_keyframes

            result = delete_keyframes("pSphere1")
        assert result["success"] is False
        assert "Maya not available" in result["message"]


# ===========================================================================
# bake_simulation
# ===========================================================================

class TestBakeSimulation:
    def test_bake_named_objects(self, mock_maya):
        _reload()
        from dcc_mcp_maya.actions.animation import bake_simulation

        result = bake_simulation(
            objects=["pSphere1", "pCube1"],
            start_frame=1.0,
            end_frame=50.0,
        )
        assert result["success"] is True
        assert result["context"]["object_count"] == 2
        mock_maya.bakeSimulation.assert_called_once()

    def test_bake_uses_selection_when_no_objects(self, mock_maya):
        _reload()
        mock_maya.ls.return_value = ["pSphere1"]
        from dcc_mcp_maya.actions.animation import bake_simulation

        result = bake_simulation()
        assert result["success"] is True
        assert result["context"]["objects"] == ["pSphere1"]

    def test_bake_custom_sample_by(self, mock_maya):
        _reload()
        from dcc_mcp_maya.actions.animation import bake_simulation

        bake_simulation(objects=["pSphere1"], sample_by=0.5)
        call_kwargs = mock_maya.bakeSimulation.call_args
        assert call_kwargs[1]["sampleBy"] == 0.5

    def test_bake_missing_object(self, mock_maya):
        _reload()
        mock_maya.objExists.return_value = False
        from dcc_mcp_maya.actions.animation import bake_simulation

        result = bake_simulation(objects=["ghost"])
        assert result["success"] is False
        assert "ghost" in result["message"]

    def test_bake_no_selection_and_no_objects(self, mock_maya):
        _reload()
        mock_maya.ls.return_value = []
        from dcc_mcp_maya.actions.animation import bake_simulation

        result = bake_simulation()
        assert result["success"] is False
        assert "No objects" in result["message"]

    def test_bake_exception(self, mock_maya):
        _reload()
        mock_maya.bakeSimulation.side_effect = RuntimeError("solver failed")
        from dcc_mcp_maya.actions.animation import bake_simulation

        result = bake_simulation(objects=["pSphere1"])
        assert result["success"] is False

    def test_bake_no_maya(self):
        _reload()
        with _no_maya():
            for mod in list(sys.modules):
                if "dcc_mcp_maya.actions" in mod:
                    del sys.modules[mod]
            from dcc_mcp_maya.actions.animation import bake_simulation

            result = bake_simulation(objects=["pSphere1"])
        assert result["success"] is False
        assert "Maya not available" in result["message"]


# ===========================================================================
# set_joint_orient
# ===========================================================================

class TestSetJointOrient:
    def test_set_orient_default(self, mock_maya):
        _reload()
        from dcc_mcp_maya.actions.rigging import set_joint_orient

        result = set_joint_orient("joint1")
        assert result["success"] is True
        assert result["context"]["orient"] == [0.0, 0.0, 0.0]

    def test_set_orient_custom(self, mock_maya):
        _reload()
        from dcc_mcp_maya.actions.rigging import set_joint_orient

        result = set_joint_orient("joint1", orient=[45.0, 0.0, 90.0])
        assert result["success"] is True
        assert result["context"]["orient"] == [45.0, 0.0, 90.0]
        mock_maya.setAttr.assert_any_call("joint1.jointOrientX", 45.0)
        mock_maya.setAttr.assert_any_call("joint1.jointOrientY", 0.0)
        mock_maya.setAttr.assert_any_call("joint1.jointOrientZ", 90.0)

    def test_set_orient_joint_not_found(self, mock_maya):
        _reload()
        mock_maya.objExists.return_value = False
        from dcc_mcp_maya.actions.rigging import set_joint_orient

        result = set_joint_orient("ghost")
        assert result["success"] is False

    def test_set_orient_not_a_joint(self, mock_maya):
        _reload()
        mock_maya.objectType.return_value = "transform"
        from dcc_mcp_maya.actions.rigging import set_joint_orient

        result = set_joint_orient("pSphere1")
        assert result["success"] is False
        assert "transform" in result["message"] or "joint" in result["message"]

    def test_set_orient_exception(self, mock_maya):
        _reload()
        mock_maya.setAttr.side_effect = RuntimeError("locked attr")
        from dcc_mcp_maya.actions.rigging import set_joint_orient

        result = set_joint_orient("joint1", orient=[10.0, 0.0, 0.0])
        assert result["success"] is False

    def test_set_orient_zero_scale_compensate(self, mock_maya):
        _reload()
        from dcc_mcp_maya.actions.rigging import set_joint_orient

        result = set_joint_orient("joint1", zero_scale_orient=True)
        assert result["success"] is True
        mock_maya.setAttr.assert_any_call("joint1.segmentScaleCompensate", True)

    def test_set_orient_no_maya(self):
        _reload()
        with _no_maya():
            for mod in list(sys.modules):
                if "dcc_mcp_maya.actions" in mod:
                    del sys.modules[mod]
            from dcc_mcp_maya.actions.rigging import set_joint_orient

            result = set_joint_orient("joint1")
        assert result["success"] is False
        assert "Maya not available" in result["message"]


# ===========================================================================
# mirror_joints
# ===========================================================================

class TestMirrorJoints:
    def test_mirror_default(self, mock_maya):
        _reload()
        from dcc_mcp_maya.actions.rigging import mirror_joints

        result = mirror_joints("L_shoulder")
        assert result["success"] is True
        assert result["context"]["source_joint"] == "L_shoulder"
        assert len(result["context"]["mirrored_joints"]) == 3

    def test_mirror_custom_axis_XY(self, mock_maya):
        _reload()
        from dcc_mcp_maya.actions.rigging import mirror_joints

        result = mirror_joints("L_shoulder", mirror_axis="XY")
        assert result["success"] is True
        call_kwargs = mock_maya.mirrorJoint.call_args
        assert call_kwargs[1].get("mirrorXY") is True

    def test_mirror_custom_search_replace(self, mock_maya):
        _reload()
        from dcc_mcp_maya.actions.rigging import mirror_joints

        mirror_joints("Left_hip", search_replace=["Left_", "Right_"])
        call_kwargs = mock_maya.mirrorJoint.call_args
        assert call_kwargs[1]["searchReplace"] == ["Left_", "Right_"]

    def test_mirror_joint_not_found(self, mock_maya):
        _reload()
        mock_maya.objExists.return_value = False
        from dcc_mcp_maya.actions.rigging import mirror_joints

        result = mirror_joints("ghost")
        assert result["success"] is False

    def test_mirror_invalid_axis(self, mock_maya):
        _reload()
        from dcc_mcp_maya.actions.rigging import mirror_joints

        result = mirror_joints("L_shoulder", mirror_axis="AB")
        assert result["success"] is False
        assert "mirror_axis" in result["message"] or "AB" in result["message"]

    def test_mirror_invalid_search_replace(self, mock_maya):
        _reload()
        from dcc_mcp_maya.actions.rigging import mirror_joints

        result = mirror_joints("L_shoulder", search_replace=["only_one"])
        assert result["success"] is False

    def test_mirror_empty_result(self, mock_maya):
        _reload()
        mock_maya.mirrorJoint.return_value = None
        from dcc_mcp_maya.actions.rigging import mirror_joints

        result = mirror_joints("L_shoulder")
        assert result["success"] is True
        assert result["context"]["mirrored_joints"] == []

    def test_mirror_exception(self, mock_maya):
        _reload()
        mock_maya.mirrorJoint.side_effect = RuntimeError("mirror error")
        from dcc_mcp_maya.actions.rigging import mirror_joints

        result = mirror_joints("L_shoulder")
        assert result["success"] is False

    def test_mirror_no_maya(self):
        _reload()
        with _no_maya():
            for mod in list(sys.modules):
                if "dcc_mcp_maya.actions" in mod:
                    del sys.modules[mod]
            from dcc_mcp_maya.actions.rigging import mirror_joints

            result = mirror_joints("L_shoulder")
        assert result["success"] is False
        assert "Maya not available" in result["message"]


# ===========================================================================
# create_ik_handle
# ===========================================================================

class TestCreateIkHandle:
    def test_create_ik_default(self, mock_maya):
        _reload()
        from dcc_mcp_maya.actions.rigging import create_ik_handle

        result = create_ik_handle("joint1", "joint3")
        assert result["success"] is True
        assert result["context"]["handle_name"] == "ikHandle1"
        assert result["context"]["effector_name"] == "effector1"
        assert result["context"]["solver"] == "ikRPsolver"

    def test_create_ik_sc_solver(self, mock_maya):
        _reload()
        from dcc_mcp_maya.actions.rigging import create_ik_handle

        result = create_ik_handle("joint1", "joint2", solver="ikSCsolver")
        assert result["success"] is True
        call_kwargs = mock_maya.ikHandle.call_args
        assert call_kwargs[1]["solver"] == "ikSCsolver"

    def test_create_ik_with_name(self, mock_maya):
        _reload()
        from dcc_mcp_maya.actions.rigging import create_ik_handle

        create_ik_handle("joint1", "joint3", name="arm_IK")
        call_kwargs = mock_maya.ikHandle.call_args
        assert call_kwargs[1]["name"] == "arm_IK"

    def test_create_ik_start_joint_not_found(self, mock_maya):
        _reload()
        mock_maya.objExists.side_effect = lambda x: x != "joint1"
        from dcc_mcp_maya.actions.rigging import create_ik_handle

        result = create_ik_handle("joint1", "joint3")
        assert result["success"] is False
        assert "joint1" in result["message"]

    def test_create_ik_end_joint_not_found(self, mock_maya):
        _reload()
        mock_maya.objExists.side_effect = lambda x: x != "joint3"
        from dcc_mcp_maya.actions.rigging import create_ik_handle

        result = create_ik_handle("joint1", "joint3")
        assert result["success"] is False
        assert "joint3" in result["message"]

    def test_create_ik_invalid_solver(self, mock_maya):
        _reload()
        from dcc_mcp_maya.actions.rigging import create_ik_handle

        result = create_ik_handle("joint1", "joint3", solver="badSolver")
        assert result["success"] is False
        assert "badSolver" in result["message"]

    def test_create_ik_exception(self, mock_maya):
        _reload()
        mock_maya.ikHandle.side_effect = RuntimeError("ik error")
        from dcc_mcp_maya.actions.rigging import create_ik_handle

        result = create_ik_handle("joint1", "joint3")
        assert result["success"] is False

    def test_create_ik_no_maya(self):
        _reload()
        with _no_maya():
            for mod in list(sys.modules):
                if "dcc_mcp_maya.actions" in mod:
                    del sys.modules[mod]
            from dcc_mcp_maya.actions.rigging import create_ik_handle

            result = create_ik_handle("joint1", "joint3")
        assert result["success"] is False
        assert "Maya not available" in result["message"]


# ===========================================================================
# register_all — ensure new actions are present
# ===========================================================================

class TestRegisterAllRound4:
    def test_all_new_actions_in_all(self):
        _reload()
        from dcc_mcp_maya.actions import __all__

        for name in (
            "delete_keyframes",
            "bake_simulation",
            "set_joint_orient",
            "mirror_joints",
            "create_ik_handle",
        ):
            assert name in __all__, "{} missing from __all__".format(name)

    def test_register_all_count_gte_51(self):
        _reload()
        registry = MagicMock()
        from dcc_mcp_maya.actions import register_all

        register_all(registry)
        assert registry.register.call_count >= 51
