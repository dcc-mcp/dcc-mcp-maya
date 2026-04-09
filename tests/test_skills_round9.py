"""Round 9 skill tests: maya-animation (extended scripts).

All Maya API calls are mocked – no real Maya installation needed.
Scripts are loaded via importlib to handle hyphenated directory names.
"""

# Import future modules
from __future__ import annotations

# Import built-in modules
import importlib.util
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

_SKILLS_ROOT = Path(__file__).parent.parent / "src" / "dcc_mcp_maya" / "skills"

_MOD_COUNTER = [0]


def _load_script(skill_dir, script_name):
    """Load a skill script with a unique module name."""
    _MOD_COUNTER[0] += 1
    script_path = _SKILLS_ROOT / skill_dir / "scripts" / "{}.py".format(script_name)
    module_name = "skill_r9_{}_{}_{}".format(
        skill_dir.replace("-", "_"), script_name, _MOD_COUNTER[0]
    )
    spec = importlib.util.spec_from_file_location(module_name, str(script_path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _make_maya_env(**cmds_overrides):
    """Return (maya_mock, cmds_mock, modules_dict)."""
    maya_mock = MagicMock()
    cmds_mock = MagicMock()
    cmds_mock.objExists.return_value = True
    cmds_mock.ls.return_value = []
    cmds_mock.objectType.return_value = "transform"
    for k, v in cmds_overrides.items():
        setattr(cmds_mock, k, v)
    maya_mock.cmds = cmds_mock
    modules = {
        "maya": maya_mock,
        "maya.cmds": cmds_mock,
        "maya.api": MagicMock(),
        "maya.utils": MagicMock(),
        "maya.mel": MagicMock(),
    }
    return maya_mock, cmds_mock, modules


def _run_func(skill_dir, func_name, cmds_overrides=None, **kwargs):
    """Load + inject mocks + call the named function."""
    cmds_overrides = cmds_overrides or {}
    _, _, modules = _make_maya_env(**cmds_overrides)
    with patch.dict(sys.modules, modules):
        mod = _load_script(skill_dir, func_name)
        fn = getattr(mod, func_name)
        return fn(**kwargs)


# ===========================================================================
# maya-animation: set_current_time
# ===========================================================================


class TestSetCurrentTime:
    def test_set_frame(self):
        result = _run_func("maya-animation", "set_current_time", {}, frame=10.0)
        assert result["success"] is True
        assert result["context"]["current_time"] == 10.0

    def test_set_frame_zero(self):
        result = _run_func("maya-animation", "set_current_time", {}, frame=0.0)
        assert result["success"] is True

    def test_set_fractional_frame(self):
        result = _run_func("maya-animation", "set_current_time", {}, frame=2.5)
        assert result["success"] is True
        assert result["context"]["current_time"] == 2.5

    def test_exception(self):
        cmds_ov = {"currentTime": MagicMock(side_effect=RuntimeError("error"))}
        result = _run_func("maya-animation", "set_current_time", cmds_ov, frame=1.0)
        assert result["success"] is False

    def test_current_time_called(self):
        ct_mock = MagicMock()
        cmds_ov = {"currentTime": ct_mock}
        _run_func("maya-animation", "set_current_time", cmds_ov, frame=5.0)
        ct_mock.assert_called_once_with(5.0, update=True)


# ===========================================================================
# maya-animation: query_scene_time_info
# ===========================================================================


class TestQuerySceneTimeInfo:
    def test_basic_query(self):
        cmds_ov = {
            "currentUnit": MagicMock(return_value="film"),
            "playbackOptions": MagicMock(return_value=1.0),
            "currentTime": MagicMock(return_value=1.0),
        }
        result = _run_func("maya-animation", "query_scene_time_info", cmds_ov)
        assert result["success"] is True
        ctx = result["context"]
        assert "fps" in ctx
        assert "animation_start" in ctx
        assert "animation_end" in ctx
        assert "playback_start" in ctx
        assert "playback_end" in ctx
        assert "current_time" in ctx

    def test_fps_value(self):
        cmds_ov = {
            "currentUnit": MagicMock(return_value="ntsc"),
            "playbackOptions": MagicMock(return_value=24.0),
            "currentTime": MagicMock(return_value=1.0),
        }
        result = _run_func("maya-animation", "query_scene_time_info", cmds_ov)
        assert result["context"]["fps"] == "ntsc"

    def test_exception(self):
        cmds_ov = {"currentUnit": MagicMock(side_effect=RuntimeError("error"))}
        result = _run_func("maya-animation", "query_scene_time_info", cmds_ov)
        assert result["success"] is False


# ===========================================================================
# maya-animation: delete_keyframes
# ===========================================================================


class TestDeleteKeyframes:
    def test_delete_all_keyframes(self):
        cmds_ov = {"cutKey": MagicMock(return_value=5)}
        result = _run_func("maya-animation", "delete_keyframes", cmds_ov, object_name="pCube1")
        assert result["success"] is True
        assert result["context"]["deleted_count"] == 5

    def test_delete_with_range(self):
        cmds_ov = {"cutKey": MagicMock(return_value=2)}
        result = _run_func(
            "maya-animation", "delete_keyframes", cmds_ov,
            object_name="pCube1", start_frame=1.0, end_frame=10.0
        )
        assert result["success"] is True

    def test_delete_with_attributes(self):
        cmds_ov = {"cutKey": MagicMock(return_value=3)}
        result = _run_func(
            "maya-animation", "delete_keyframes", cmds_ov,
            object_name="pCube1", attributes=["tx", "ty"]
        )
        assert result["success"] is True

    def test_object_not_found(self):
        cmds_ov = {"objExists": MagicMock(return_value=False)}
        result = _run_func("maya-animation", "delete_keyframes", cmds_ov, object_name="missing")
        assert result["success"] is False

    def test_exception(self):
        cmds_ov = {"cutKey": MagicMock(side_effect=RuntimeError("error"))}
        result = _run_func("maya-animation", "delete_keyframes", cmds_ov, object_name="pCube1")
        assert result["success"] is False


# ===========================================================================
# maya-animation: list_animation_curves
# ===========================================================================


class TestListAnimationCurves:
    def test_no_curves(self):
        cmds_ov = {"listConnections": MagicMock(return_value=[])}
        result = _run_func("maya-animation", "list_animation_curves", cmds_ov, object_name="pCube1")
        assert result["success"] is True
        assert result["context"]["count"] == 0

    def test_with_curves(self):
        listConns_mock = MagicMock(side_effect=[
            ["pCube1_translateX"],   # listConnections for object
            ["pCube1.translateX"],   # listConnections for driven plugs
        ])
        cmds_ov = {
            "listConnections": listConns_mock,
            "objectType": MagicMock(return_value="animCurveTL"),
            "keyframe": MagicMock(return_value=3),
        }
        result = _run_func("maya-animation", "list_animation_curves", cmds_ov, object_name="pCube1")
        assert result["success"] is True
        assert result["context"]["count"] == 1

    def test_with_specific_attribute(self):
        cmds_ov = {"listConnections": MagicMock(return_value=[])}
        result = _run_func(
            "maya-animation", "list_animation_curves", cmds_ov,
            object_name="pCube1", attribute="tx"
        )
        assert result["success"] is True

    def test_object_not_found(self):
        cmds_ov = {"objExists": MagicMock(return_value=False)}
        result = _run_func("maya-animation", "list_animation_curves", cmds_ov, object_name="missing")
        assert result["success"] is False

    def test_curve_structure(self):
        listConns_mock = MagicMock(side_effect=[
            ["myCurve"],
            ["pCube1.translateX"],
        ])
        cmds_ov = {
            "listConnections": listConns_mock,
            "objectType": MagicMock(return_value="animCurveTL"),
            "keyframe": MagicMock(return_value=5),
        }
        result = _run_func("maya-animation", "list_animation_curves", cmds_ov, object_name="pCube1")
        if result["context"]["count"] > 0:
            curve = result["context"]["curves"][0]
            assert "name" in curve
            assert "type" in curve
            assert "key_count" in curve


# ===========================================================================
# maya-animation: set_animation_curve_tangent
# ===========================================================================


class TestSetAnimationCurveTangent:
    def test_set_auto_tangent(self):
        result = _run_func(
            "maya-animation", "set_animation_curve_tangent", {},
            object_name="pCube1", attribute="tx", tangent_type="auto"
        )
        assert result["success"] is True

    def test_set_linear_tangent(self):
        result = _run_func(
            "maya-animation", "set_animation_curve_tangent", {},
            object_name="pCube1", attribute="tx", tangent_type="linear"
        )
        assert result["success"] is True

    def test_invalid_tangent_type(self):
        result = _run_func(
            "maya-animation", "set_animation_curve_tangent", {},
            object_name="pCube1", attribute="tx", tangent_type="invalid"
        )
        assert result["success"] is False

    def test_object_not_found(self):
        cmds_ov = {"objExists": MagicMock(return_value=False)}
        result = _run_func(
            "maya-animation", "set_animation_curve_tangent", cmds_ov,
            object_name="missing", attribute="tx"
        )
        assert result["success"] is False

    def test_attribute_not_found(self):
        # objExists returns True for object but False for plug
        cmds_ov = {
            "objExists": MagicMock(side_effect=lambda x: "." not in x),
        }
        result = _run_func(
            "maya-animation", "set_animation_curve_tangent", cmds_ov,
            object_name="pCube1", attribute="tx"
        )
        assert result["success"] is False

    def test_with_specific_frame(self):
        result = _run_func(
            "maya-animation", "set_animation_curve_tangent", {},
            object_name="pCube1", attribute="tx", frame=5.0, tangent_type="flat"
        )
        assert result["success"] is True
        assert result["context"]["frame"] == 5.0

    def test_separate_in_out_tangent(self):
        result = _run_func(
            "maya-animation", "set_animation_curve_tangent", {},
            object_name="pCube1", attribute="tx",
            in_tangent_type="linear", out_tangent_type="flat"
        )
        assert result["success"] is True

    def test_exception(self):
        cmds_ov = {"keyTangent": MagicMock(side_effect=RuntimeError("error"))}
        result = _run_func(
            "maya-animation", "set_animation_curve_tangent", cmds_ov,
            object_name="pCube1", attribute="tx"
        )
        assert result["success"] is False


# ===========================================================================
# maya-animation: bake_simulation
# ===========================================================================


class TestBakeSimulation:
    def test_bake_with_objects(self):
        result = _run_func(
            "maya-animation", "bake_simulation", {},
            objects=["pCube1", "pSphere1"],
            start_frame=1.0, end_frame=50.0
        )
        assert result["success"] is True
        assert result["context"]["object_count"] == 2

    def test_bake_with_selection(self):
        cmds_ov = {"ls": MagicMock(return_value=["pCube1"])}
        result = _run_func("maya-animation", "bake_simulation", cmds_ov)
        assert result["success"] is True

    def test_bake_no_objects_or_selection(self):
        cmds_ov = {"ls": MagicMock(return_value=[])}
        result = _run_func("maya-animation", "bake_simulation", cmds_ov)
        assert result["success"] is False

    def test_bake_missing_object(self):
        cmds_ov = {"objExists": MagicMock(side_effect=lambda x: x != "missing")}
        result = _run_func(
            "maya-animation", "bake_simulation", cmds_ov,
            objects=["pCube1", "missing"]
        )
        assert result["success"] is False

    def test_exception(self):
        cmds_ov = {"bakeSimulation": MagicMock(side_effect=RuntimeError("error"))}
        result = _run_func(
            "maya-animation", "bake_simulation", cmds_ov,
            objects=["pCube1"]
        )
        assert result["success"] is False

    def test_context_has_frame_range(self):
        result = _run_func(
            "maya-animation", "bake_simulation", {},
            objects=["pCube1"], start_frame=5.0, end_frame=100.0
        )
        assert result["context"]["start_frame"] == 5.0
        assert result["context"]["end_frame"] == 100.0


# ===========================================================================
# maya-animation: bake_constraints
# ===========================================================================


class TestBakeConstraints:
    def test_bake_with_objects(self):
        result = _run_func(
            "maya-animation", "bake_constraints", {},
            objects=["pCube1"],
            start_frame=1.0, end_frame=24.0
        )
        assert result["success"] is True
        assert result["context"]["object_count"] == 1

    def test_bake_with_selection(self):
        cmds_ov = {"ls": MagicMock(return_value=["pSphere1"])}
        result = _run_func("maya-animation", "bake_constraints", cmds_ov)
        assert result["success"] is True

    def test_bake_no_targets(self):
        cmds_ov = {"ls": MagicMock(return_value=[])}
        result = _run_func("maya-animation", "bake_constraints", cmds_ov)
        assert result["success"] is False

    def test_bake_missing_object(self):
        cmds_ov = {"objExists": MagicMock(side_effect=lambda x: x != "noObj")}
        result = _run_func(
            "maya-animation", "bake_constraints", cmds_ov,
            objects=["pCube1", "noObj"]
        )
        assert result["success"] is False

    def test_remove_constraints(self):
        listRelatives_mock = MagicMock(return_value=["parentConstraint1"])
        cmds_ov = {
            "listRelatives": listRelatives_mock,
            "delete": MagicMock(),
        }
        result = _run_func(
            "maya-animation", "bake_constraints", cmds_ov,
            objects=["pCube1"], remove_constraints=True
        )
        assert result["success"] is True

    def test_exception(self):
        cmds_ov = {"bakeSimulation": MagicMock(side_effect=RuntimeError("error"))}
        result = _run_func(
            "maya-animation", "bake_constraints", cmds_ov,
            objects=["pCube1"]
        )
        assert result["success"] is False

    def test_removed_constraints_in_context(self):
        result = _run_func(
            "maya-animation", "bake_constraints", {},
            objects=["pCube1"], remove_constraints=False
        )
        assert "removed_constraints" in result["context"]


# ===========================================================================
# maya-animation: export_animation_curves
# ===========================================================================


class TestExportAnimationCurves:
    def test_export_success(self):
        cmds_ov = {
            "keyframe": MagicMock(return_value=["pCube1_tx"]),
            "playbackOptions": MagicMock(return_value=1.0),
            "file": MagicMock(),
        }
        result = _run_func(
            "maya-animation", "export_animation_curves", cmds_ov,
            object_name="pCube1", file_path="/tmp/anim.ma"
        )
        assert result["success"] is True
        assert result["context"]["curve_count"] == 1

    def test_no_curves(self):
        cmds_ov = {
            "keyframe": MagicMock(return_value=[]),
            "playbackOptions": MagicMock(return_value=1.0),
        }
        result = _run_func(
            "maya-animation", "export_animation_curves", cmds_ov,
            object_name="pCube1", file_path="/tmp/anim.ma"
        )
        assert result["success"] is False

    def test_object_not_found(self):
        cmds_ov = {"objExists": MagicMock(return_value=False)}
        result = _run_func(
            "maya-animation", "export_animation_curves", cmds_ov,
            object_name="missing", file_path="/tmp/anim.ma"
        )
        assert result["success"] is False

    def test_export_mb_format(self):
        cmds_ov = {
            "keyframe": MagicMock(return_value=["curve1"]),
            "playbackOptions": MagicMock(return_value=1.0),
            "file": MagicMock(),
        }
        result = _run_func(
            "maya-animation", "export_animation_curves", cmds_ov,
            object_name="pCube1", file_path="/tmp/anim.mb"
        )
        assert result["success"] is True

    def test_exception(self):
        cmds_ov = {
            "keyframe": MagicMock(return_value=["curve1"]),
            "playbackOptions": MagicMock(return_value=1.0),
            "file": MagicMock(side_effect=RuntimeError("permission denied")),
        }
        result = _run_func(
            "maya-animation", "export_animation_curves", cmds_ov,
            object_name="pCube1", file_path="/tmp/anim.ma"
        )
        assert result["success"] is False


# ===========================================================================
# maya-animation: import_animation_curves
# ===========================================================================


class TestImportAnimationCurves:
    def test_import_success(self):
        with patch("os.path.isfile", return_value=True):
            result = _run_func(
                "maya-animation", "import_animation_curves", {},
                file_path="/tmp/anim.ma"
            )
        assert result["success"] is True

    def test_file_not_found(self):
        with patch("os.path.isfile", return_value=False):
            result = _run_func(
                "maya-animation", "import_animation_curves", {},
                file_path="/tmp/nonexistent.ma"
            )
        assert result["success"] is False

    def test_import_with_target_object(self):
        cmds_ov = {
            "ls": MagicMock(return_value=["importedCurve"]),
            "listConnections": MagicMock(return_value=["pSphere1.translateX"]),
            "connectAttr": MagicMock(),
        }
        with patch("os.path.isfile", return_value=True):
            result = _run_func(
                "maya-animation", "import_animation_curves", cmds_ov,
                file_path="/tmp/anim.ma", target_object="pSphere1"
            )
        assert result["success"] is True
        assert result["context"]["target_object"] == "pSphere1"

    def test_exception(self):
        cmds_ov = {"file": MagicMock(side_effect=RuntimeError("error"))}
        with patch("os.path.isfile", return_value=True):
            result = _run_func(
                "maya-animation", "import_animation_curves", cmds_ov,
                file_path="/tmp/anim.ma"
            )
        assert result["success"] is False

    def test_merge_flag_in_context(self):
        with patch("os.path.isfile", return_value=True):
            result = _run_func(
                "maya-animation", "import_animation_curves", {},
                file_path="/tmp/anim.ma", merge=False
            )
        assert result["success"] is True
        assert result["context"]["merge"] is False
