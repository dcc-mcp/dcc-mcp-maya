"""Round 7 skill tests: maya-cameras / maya-constraints / maya-display / maya-lighting.

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
    module_name = "skill_r7_{}_{}_{}".format(skill_dir.replace("-", "_"), script_name, _MOD_COUNTER[0])
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
# maya-cameras – create_camera
# ===========================================================================


class TestCreateCamera:
    def test_success_default(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.camera.return_value = ["camera1", "cameraShape1"]
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-cameras", "create_camera")
            result = mod.create_camera()
        assert result["success"] is True
        assert result["context"]["transform"] == "camera1"
        assert result["context"]["shape"] == "cameraShape1"
        assert result["context"]["focal_length"] == 35.0

    def test_success_named(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.camera.return_value = ["camera1", "cameraShape1"]
        cmds_mock.rename.return_value = "myCam"
        cmds_mock.listRelatives.return_value = ["myCamShape"]
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-cameras", "create_camera")
            result = mod.create_camera(name="myCam", focal_length=50.0)
        assert result["success"] is True
        assert result["context"]["transform"] == "myCam"

    def test_success_with_position_and_rotation(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.camera.return_value = ["camera1", "cameraShape1"]
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-cameras", "create_camera")
            result = mod.create_camera(
                position=[10.0, 5.0, 0.0],
                rotation=[0.0, -45.0, 0.0],
            )
        assert result["success"] is True
        cmds_mock.move.assert_called_once()
        cmds_mock.rotate.assert_called_once()

    def test_exception_propagates(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.camera.side_effect = RuntimeError("fail")
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-cameras", "create_camera")
            result = mod.create_camera()
        assert result["success"] is False


# ===========================================================================
# maya-cameras – get_camera_info
# ===========================================================================


class TestGetCameraInfo:
    def test_success_transform(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.objExists.return_value = True
        cmds_mock.objectType.return_value = "transform"
        cmds_mock.listRelatives.return_value = ["cameraShape1"]

        def get_attr_side(attr_str):
            if "translate" in attr_str or "rotate" in attr_str:
                return [(0.0, 0.0, 0.0)]
            return 35.0

        cmds_mock.getAttr.side_effect = get_attr_side
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-cameras", "get_camera_info")
            result = mod.get_camera_info("camera1")
        assert result["success"] is True

    def test_success_shape_node(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.objExists.return_value = True
        cmds_mock.objectType.return_value = "camera"
        cmds_mock.listRelatives.return_value = ["camera1"]

        def get_attr_side(attr_str):
            if "translate" in attr_str or "rotate" in attr_str:
                return [(0.0, 0.0, 0.0)]
            return 50.0

        cmds_mock.getAttr.side_effect = get_attr_side
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-cameras", "get_camera_info")
            result = mod.get_camera_info("cameraShape1")
        assert result["success"] is True

    def test_camera_not_found(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.objExists.return_value = False
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-cameras", "get_camera_info")
            result = mod.get_camera_info("missing")
        assert result["success"] is False

    def test_transform_no_camera_shape(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.objExists.return_value = True
        cmds_mock.objectType.return_value = "transform"
        cmds_mock.listRelatives.return_value = []
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-cameras", "get_camera_info")
            result = mod.get_camera_info("notACamera")
        assert result["success"] is False


# ===========================================================================
# maya-cameras – list_all_cameras
# ===========================================================================


class TestListAllCameras:
    def test_success_empty(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.ls.return_value = []
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-cameras", "list_all_cameras")
            result = mod.list_all_cameras()
        assert result["success"] is True
        assert result["context"]["count"] == 0

    def test_success_with_cameras(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.ls.return_value = ["perspShape", "cameraShape1"]
        cmds_mock.listRelatives.side_effect = lambda s, **kw: [s.replace("Shape", "")]
        cmds_mock.getAttr.return_value = 35.0
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-cameras", "list_all_cameras")
            result = mod.list_all_cameras()
        assert result["success"] is True
        assert result["context"]["count"] == 2

    def test_exclude_default_cameras(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.ls.return_value = ["perspShape", "myShape"]
        # persp → excluded (default); myShape → kept
        cmds_mock.listRelatives.side_effect = lambda s, **kw: ["persp"] if s == "perspShape" else ["myCamera"]
        cmds_mock.getAttr.return_value = 35.0
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-cameras", "list_all_cameras")
            result = mod.list_all_cameras(include_default=False)
        assert result["success"] is True
        assert result["context"]["count"] == 1


# ===========================================================================
# maya-cameras – set_active_camera
# ===========================================================================


class TestSetActiveCamera:
    def _run(self, cmds_overrides=None, **kwargs):
        return _run_func("maya-cameras", "set_active_camera", cmds_overrides, **kwargs)

    def test_success_with_panel(self):
        result = self._run(camera_name="myCam", panel="modelPanel1")
        assert result["success"] is True
        assert result["context"]["panel"] == "modelPanel1"
        assert result["context"]["camera_name"] == "myCam"

    def test_success_auto_panel(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.objExists.return_value = True
        cmds_mock.getPanel.return_value = ["modelPanel1"]
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-cameras", "set_active_camera")
            result = mod.set_active_camera("myCam")
        assert result["success"] is True

    def test_camera_not_found(self):
        result = self._run({"objExists": MagicMock(return_value=False)}, camera_name="missing")
        assert result["success"] is False

    def test_no_model_panel(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.objExists.return_value = True
        cmds_mock.getPanel.return_value = []
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-cameras", "set_active_camera")
            result = mod.set_active_camera("myCam")
        assert result["success"] is False
        assert "no model panel" in result["message"].lower()


# ===========================================================================
# maya-cameras – set_camera_attribute
# ===========================================================================


class TestSetCameraAttribute:
    def _run(self, cmds_overrides=None, **kwargs):
        return _run_func("maya-cameras", "set_camera_attribute", cmds_overrides, **kwargs)

    def test_success_shape_node(self):
        result = self._run(
            {"objectType": MagicMock(return_value="camera")},
            camera_name="cameraShape1",
            attribute="focalLength",
            value=50.0,
        )
        assert result["success"] is True

    def test_success_transform_node(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.objExists.return_value = True
        cmds_mock.objectType.return_value = "transform"
        cmds_mock.listRelatives.return_value = ["cameraShape1"]
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-cameras", "set_camera_attribute")
            result = mod.set_camera_attribute("camera1", "focalLength", 85.0)
        assert result["success"] is True

    def test_camera_not_found(self):
        result = self._run(
            {"objExists": MagicMock(return_value=False)}, camera_name="missing", attribute="focalLength", value=50.0
        )
        assert result["success"] is False

    def test_transform_no_camera_shape(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.objExists.return_value = True
        cmds_mock.objectType.return_value = "transform"
        cmds_mock.listRelatives.return_value = []
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-cameras", "set_camera_attribute")
            result = mod.set_camera_attribute("notCam", "focalLength", 50.0)
        assert result["success"] is False
        assert "no camera shape" in result["message"].lower()

    def test_exception_propagates(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.objExists.return_value = True
        cmds_mock.objectType.return_value = "camera"
        cmds_mock.setAttr.side_effect = RuntimeError("locked")
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-cameras", "set_camera_attribute")
            result = mod.set_camera_attribute("cameraShape1", "focalLength", 50.0)
        assert result["success"] is False


# ===========================================================================
# maya-constraints – add_constraint
# ===========================================================================


class TestAddConstraint:
    def _run(self, cmds_overrides=None, **kwargs):
        return _run_func("maya-constraints", "add_constraint", cmds_overrides, **kwargs)

    def test_success_parent_constraint(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.objExists.return_value = True
        cmds_mock.parentConstraint.return_value = ["pCube1_parentConstraint1"]
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-constraints", "add_constraint")
            result = mod.add_constraint("parent", "pSphere1", "pCube1")
        assert result["success"] is True
        assert result["context"]["constraint_node"] == "pCube1_parentConstraint1"
        assert result["context"]["constraint_type"] == "parent"

    def test_success_point_constraint(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.objExists.return_value = True
        cmds_mock.pointConstraint.return_value = ["target_pointConstraint1"]
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-constraints", "add_constraint")
            result = mod.add_constraint("point", "src", "tgt")
        assert result["success"] is True

    def test_invalid_constraint_type(self):
        result = self._run(constraint_type="bogus", source="a", target="b")
        assert result["success"] is False
        assert "unknown constraint type" in result["message"].lower()

    def test_source_not_found(self):
        call_count = [0]

        def obj_exists(name):
            call_count[0] += 1
            return False  # first call (source) fails

        result = self._run({"objExists": obj_exists}, constraint_type="parent", source="missing", target="pCube1")
        assert result["success"] is False

    def test_target_not_found(self):
        call_count = [0]

        def obj_exists(name):
            call_count[0] += 1
            return call_count[0] == 1  # source exists; target missing

        result = self._run({"objExists": obj_exists}, constraint_type="orient", source="pSphere1", target="missing")
        assert result["success"] is False

    def test_exception_propagates(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.objExists.return_value = True
        cmds_mock.parentConstraint.side_effect = RuntimeError("boom")
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-constraints", "add_constraint")
            result = mod.add_constraint("parent", "a", "b")
        assert result["success"] is False


# ===========================================================================
# maya-constraints – list_constraints
# ===========================================================================


class TestListConstraints:
    def test_success_empty(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.objExists.return_value = True
        cmds_mock.listRelatives.return_value = []
        cmds_mock.listConnections.return_value = []
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-constraints", "list_constraints")
            result = mod.list_constraints("pCube1")
        assert result["success"] is True
        assert result["context"]["count"] == 0

    def test_success_with_constraints(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.objExists.return_value = True
        # First type (parentConstraint) returns a node
        call_count = [0]

        def list_relatives(target, **kw):
            call_count[0] += 1
            if call_count[0] == 1:
                return ["pCube1_parentConstraint1"]
            return []

        cmds_mock.listRelatives = list_relatives
        cmds_mock.listConnections.return_value = []
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-constraints", "list_constraints")
            result = mod.list_constraints("pCube1")
        assert result["success"] is True
        assert result["context"]["count"] >= 1

    def test_target_not_found(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.objExists.return_value = False
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-constraints", "list_constraints")
            result = mod.list_constraints("missing")
        assert result["success"] is False


# ===========================================================================
# maya-constraints – remove_constraint
# ===========================================================================


class TestRemoveConstraint:
    def test_success_no_constraints(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.objExists.return_value = True
        cmds_mock.listRelatives.return_value = []
        cmds_mock.listConnections.return_value = []
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-constraints", "remove_constraint")
            result = mod.remove_constraint("pCube1")
        assert result["success"] is True
        assert result["context"]["removed"] == []

    def test_success_removes_constraints(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.objExists.return_value = True
        call_count = [0]

        def list_relatives(target, **kw):
            call_count[0] += 1
            if call_count[0] == 1:
                return ["|pCube1_parentConstraint1"]
            return []

        cmds_mock.listRelatives = list_relatives
        cmds_mock.listConnections.return_value = []
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-constraints", "remove_constraint")
            result = mod.remove_constraint("pCube1")
        assert result["success"] is True
        assert len(result["context"]["removed"]) >= 1

    def test_target_not_found(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.objExists.return_value = False
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-constraints", "remove_constraint")
            result = mod.remove_constraint("missing")
        assert result["success"] is False

    def test_filter_by_type(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.objExists.return_value = True
        cmds_mock.listRelatives.return_value = []
        cmds_mock.listConnections.return_value = []
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-constraints", "remove_constraint")
            result = mod.remove_constraint("pCube1", constraint_type="parentConstraint")
        assert result["success"] is True


# ===========================================================================
# maya-constraints – create_constraint_weighted
# ===========================================================================


class TestCreateConstraintWeighted:
    def test_success_two_sources(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.objExists.return_value = True
        cmds_mock.parentConstraint.return_value = ["tgt_parentConstraint1"]
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-constraints", "create_constraint_weighted")
            result = mod.create_constraint_weighted("parent", ["src1", "src2"], "tgt", weights=[0.7, 0.3])
        assert result["success"] is True
        assert len(result["context"]["source_weights"]) == 2

    def test_success_default_weights(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.objExists.return_value = True
        cmds_mock.pointConstraint.return_value = ["tgt_pointConstraint1"]
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-constraints", "create_constraint_weighted")
            result = mod.create_constraint_weighted("point", ["srcA", "srcB"], "tgtC")
        assert result["success"] is True

    def test_invalid_type(self):
        _, _, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-constraints", "create_constraint_weighted")
            result = mod.create_constraint_weighted("bogus", ["a"], "b")
        assert result["success"] is False

    def test_source_not_found(self):
        call_count = [0]

        def obj_exists(name):
            call_count[0] += 1
            return False

        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.objExists = obj_exists
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-constraints", "create_constraint_weighted")
            result = mod.create_constraint_weighted("parent", ["missing"], "tgt")
        assert result["success"] is False


# ===========================================================================
# maya-display – create_display_layer
# ===========================================================================


class TestCreateDisplayLayer:
    def test_success_empty(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.createDisplayLayer.return_value = "layer1"
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-display", "create_display_layer")
            result = mod.create_display_layer()
        assert result["success"] is True
        assert result["context"]["layer_name"] == "layer1"

    def test_success_named_with_objects(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.createDisplayLayer.return_value = "myLayer"
        cmds_mock.objExists.return_value = True
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-display", "create_display_layer")
            result = mod.create_display_layer(name="myLayer", objects=["pSphere1", "pCube1"])
        assert result["success"] is True
        assert result["context"]["objects_added"] == ["pSphere1", "pCube1"]

    def test_success_hidden(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.createDisplayLayer.return_value = "hiddenLayer"
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-display", "create_display_layer")
            result = mod.create_display_layer(visibility=False)
        assert result["success"] is True
        assert result["context"]["visibility"] is False

    def test_objects_not_found_skipped(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.createDisplayLayer.return_value = "layer1"
        cmds_mock.objExists.return_value = False
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-display", "create_display_layer")
            result = mod.create_display_layer(objects=["ghost"])
        assert result["success"] is True
        assert result["context"]["objects_added"] == []

    def test_exception_propagates(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.createDisplayLayer.side_effect = RuntimeError("fail")
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-display", "create_display_layer")
            result = mod.create_display_layer()
        assert result["success"] is False


# ===========================================================================
# maya-display – delete_display_layer
# ===========================================================================


class TestDeleteDisplayLayer:
    def _run(self, cmds_overrides=None, **kwargs):
        return _run_func("maya-display", "delete_display_layer", cmds_overrides, **kwargs)

    def test_success(self):
        result = self._run({"objectType": MagicMock(return_value="displayLayer")}, layer_name="myLayer")
        assert result["success"] is True
        assert result["context"]["layer_name"] == "myLayer"

    def test_cannot_delete_default_layer(self):
        result = self._run(layer_name="defaultLayer")
        assert result["success"] is False
        assert "cannot delete defaultlayer" in result["message"].lower()

    def test_layer_not_found(self):
        result = self._run({"objExists": MagicMock(return_value=False)}, layer_name="missing")
        assert result["success"] is False

    def test_not_a_display_layer(self):
        result = self._run({"objectType": MagicMock(return_value="transform")}, layer_name="pSphere1")
        assert result["success"] is False
        assert result["message"].lower().startswith("wrong node type")

    def test_success_remove_objects(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.objectType.return_value = "displayLayer"
        cmds_mock.editDisplayLayerMembers.return_value = ["pSphere1", "pCube1"]
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-display", "delete_display_layer")
            result = mod.delete_display_layer("myLayer", remove_objects=True)
        assert result["success"] is True
        assert result["context"]["objects_deleted"] == ["pSphere1", "pCube1"]


# ===========================================================================
# maya-display – list_display_layers
# ===========================================================================


class TestListDisplayLayers:
    def test_success_empty(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.ls.return_value = []
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-display", "list_display_layers")
            result = mod.list_display_layers()
        assert result["success"] is True
        assert result["context"]["count"] == 0

    def test_success_with_layers(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.ls.return_value = ["defaultLayer", "myLayer"]
        cmds_mock.getAttr.return_value = True
        cmds_mock.editDisplayLayerMembers.return_value = ["pSphere1"]
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-display", "list_display_layers")
            result = mod.list_display_layers()
        assert result["success"] is True
        assert result["context"]["count"] == 2

    def test_exception_propagates(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.ls.side_effect = RuntimeError("fail")
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-display", "list_display_layers")
            result = mod.list_display_layers()
        assert result["success"] is False


# ===========================================================================
# maya-display – set_display_layer
# ===========================================================================


class TestSetDisplayLayer:
    def _run(self, cmds_overrides=None, **kwargs):
        return _run_func("maya-display", "set_display_layer", cmds_overrides, **kwargs)

    def test_success_all_found(self):
        result = self._run(layer_name="myLayer", objects=["pSphere1", "pCube1"])
        assert result["success"] is True
        assert result["context"]["assigned"] == ["pSphere1", "pCube1"]
        assert result["context"]["missing"] == []

    def test_layer_not_found(self):
        result = self._run({"objExists": MagicMock(return_value=False)}, layer_name="missing", objects=["pSphere1"])
        assert result["success"] is False

    def test_partial_objects_missing(self):
        call_count = [0]

        def obj_exists(name):
            # First call: layer exists; subsequent: alternating
            call_count[0] += 1
            return call_count[0] in (1, 2)  # layer + first obj exist; second obj missing

        result = self._run({"objExists": obj_exists}, layer_name="myLayer", objects=["pSphere1", "ghost"])
        assert result["success"] is True
        assert len(result["context"]["assigned"]) == 1
        assert "ghost" in result["context"]["missing"]


# ===========================================================================
# maya-lighting – create_light
# ===========================================================================


class TestCreateLight:
    def test_success_point(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.pointLight.return_value = "pointLightShape1"
        cmds_mock.listRelatives.return_value = ["pointLight1"]
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-lighting", "create_light")
            result = mod.create_light(light_type="point")
        assert result["success"] is True
        assert result["context"]["light_type"] == "point"

    def test_success_spot_with_options(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.spotLight.return_value = "spotLightShape1"
        cmds_mock.listRelatives.return_value = ["spotLight1"]
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-lighting", "create_light")
            result = mod.create_light(
                light_type="spot",
                intensity=2.0,
                color=[1.0, 0.9, 0.8],
                position=[0.0, 10.0, 0.0],
                rotation=[-90.0, 0.0, 0.0],
            )
        assert result["success"] is True
        assert result["context"]["intensity"] == 2.0

    def test_invalid_light_type(self):
        _, _, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-lighting", "create_light")
            result = mod.create_light(light_type="bogus")
        assert result["success"] is False
        assert "unknown light type" in result["message"].lower()

    def test_success_named(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.directionalLight.return_value = "directionalLightShape1"
        cmds_mock.listRelatives.side_effect = [
            ["directionalLight1"],  # first call: parent
            ["sunShape"],  # second call: after rename
        ]
        cmds_mock.rename.return_value = "sun"
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-lighting", "create_light")
            result = mod.create_light(light_type="directional", name="sun")
        assert result["success"] is True

    def test_exception_propagates(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.pointLight.side_effect = RuntimeError("fail")
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-lighting", "create_light")
            result = mod.create_light(light_type="point")
        assert result["success"] is False


# ===========================================================================
# maya-lighting – delete_light
# ===========================================================================


class TestDeleteLight:
    def _run(self, cmds_overrides=None, **kwargs):
        return _run_func("maya-lighting", "delete_light", cmds_overrides, **kwargs)

    def test_success_transform(self):
        result = self._run({"objectType": MagicMock(return_value="transform")}, light_name="pointLight1")
        assert result["success"] is True
        assert result["context"]["light_name"] == "pointLight1"

    def test_success_shape_node_resolves_to_transform(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.objExists.return_value = True
        cmds_mock.objectType.return_value = "pointLight"
        cmds_mock.listRelatives.return_value = ["pointLight1"]
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-lighting", "delete_light")
            result = mod.delete_light("pointLightShape1")
        assert result["success"] is True

    def test_light_not_found(self):
        result = self._run({"objExists": MagicMock(return_value=False)}, light_name="missing")
        assert result["success"] is False
        assert "not found" in result["message"].lower()

    def test_exception_propagates(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.objExists.return_value = True
        cmds_mock.objectType.return_value = "transform"
        cmds_mock.delete.side_effect = RuntimeError("cannot delete")
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-lighting", "delete_light")
            result = mod.delete_light("pointLight1")
        assert result["success"] is False


# ===========================================================================
# maya-lighting – list_lights
# ===========================================================================


class TestListLights:
    def test_success_empty(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.ls.return_value = []
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-lighting", "list_lights")
            result = mod.list_lights()
        assert result["success"] is True
        assert result["context"]["count"] == 0

    def test_success_with_lights(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.ls.return_value = ["pointLightShape1"]
        cmds_mock.listRelatives.return_value = ["pointLight1"]
        cmds_mock.objectType.return_value = "pointLight"
        cmds_mock.getAttr.return_value = 2.0
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-lighting", "list_lights")
            result = mod.list_lights()
        assert result["success"] is True
        assert result["context"]["count"] == 1
        light = result["context"]["lights"][0]
        assert light["transform"] == "pointLight1"
        assert light["intensity"] == 2.0

    def test_exception_propagates(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.ls.side_effect = RuntimeError("fail")
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-lighting", "list_lights")
            result = mod.list_lights()
        assert result["success"] is False


# ===========================================================================
# maya-lighting – set_light_attribute
# ===========================================================================


class TestSetLightAttribute:
    def _run(self, cmds_overrides=None, **kwargs):
        return _run_func("maya-lighting", "set_light_attribute", cmds_overrides, **kwargs)

    def test_success_shape_node(self):
        result = self._run(
            {"objectType": MagicMock(return_value="pointLight")},
            light_name="pointLightShape1",
            attribute="intensity",
            value=3.0,
        )
        assert result["success"] is True
        assert result["context"]["value"] == 3.0

    def test_success_transform_node(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.objExists.return_value = True
        cmds_mock.objectType.return_value = "transform"
        cmds_mock.listRelatives.return_value = ["pointLightShape1"]
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-lighting", "set_light_attribute")
            result = mod.set_light_attribute("pointLight1", "intensity", 5.0)
        assert result["success"] is True

    def test_light_not_found(self):
        result = self._run(
            {"objExists": MagicMock(return_value=False)}, light_name="missing", attribute="intensity", value=1.0
        )
        assert result["success"] is False

    def test_transform_no_shape(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.objExists.return_value = True
        cmds_mock.objectType.return_value = "transform"
        cmds_mock.listRelatives.return_value = []
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-lighting", "set_light_attribute")
            result = mod.set_light_attribute("emptyGroup", "intensity", 1.0)
        assert result["success"] is False

    def test_list_value(self):
        result = self._run(
            {"objectType": MagicMock(return_value="pointLight")},
            light_name="pLightShape1",
            attribute="shadowColor",
            value=[0.0, 0.0, 0.0],
        )
        assert result["success"] is True

    def test_exception_propagates(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.objExists.return_value = True
        cmds_mock.objectType.return_value = "pointLight"
        cmds_mock.setAttr.side_effect = RuntimeError("locked")
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-lighting", "set_light_attribute")
            result = mod.set_light_attribute("pLightShape1", "intensity", 1.0)
        assert result["success"] is False
