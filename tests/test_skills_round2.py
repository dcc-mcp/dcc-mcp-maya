"""Unit tests for Round 2 skill scripts: display, cameras, attributes, constraints,
lighting, and render settings.

All tests mock maya.cmds to avoid requiring a real Maya environment.
Scripts are loaded via importlib to handle hyphenated skill directory names.
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
    """Load a skill script from its file path with a unique module name."""
    _MOD_COUNTER[0] += 1
    script_path = _SKILLS_ROOT / skill_dir / "scripts" / "{}.py".format(script_name)
    module_name = "skill_r2_{}_{}_{}".format(skill_dir.replace("-", "_"), script_name, _MOD_COUNTER[0])
    spec = importlib.util.spec_from_file_location(module_name, str(script_path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _make_maya_env(**cmds_overrides):
    """Return (maya_mock, cmds_mock, modules_dict) with mocks wired correctly."""
    maya_mock = MagicMock()
    cmds_mock = MagicMock()
    cmds_mock.objExists.return_value = True
    cmds_mock.ls.return_value = []
    for k, v in cmds_overrides.items():
        setattr(cmds_mock, k, v)
    maya_mock.cmds = cmds_mock
    modules = {
        "maya": maya_mock,
        "maya.cmds": cmds_mock,
        "maya.api": MagicMock(),
        "maya.utils": MagicMock(),
    }
    return maya_mock, cmds_mock, modules


# ---------------------------------------------------------------------------
# maya-display
# ---------------------------------------------------------------------------


class TestCreateDisplayLayer:
    def test_create_basic(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.createDisplayLayer.return_value = "layer1"
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-display", "create_display_layer")
            result = mod.create_display_layer()
        assert result["success"] is True
        assert result["context"]["layer_name"] == "layer1"

    def test_create_with_name_and_objects(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.createDisplayLayer.return_value = "myLayer"
        cmds_mock.objExists.return_value = True
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-display", "create_display_layer")
            result = mod.create_display_layer(name="myLayer", objects=["pSphere1", "pCube1"], visibility=True)
        assert result["success"] is True
        assert result["context"]["objects_added"] == ["pSphere1", "pCube1"]

    def test_create_hidden_layer(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.createDisplayLayer.return_value = "hiddenLayer"
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-display", "create_display_layer")
            result = mod.create_display_layer(name="hiddenLayer", visibility=False)
        assert result["success"] is True
        cmds_mock.setAttr.assert_called_once_with("hiddenLayer.visibility", 0)

    def test_create_exception(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.createDisplayLayer.side_effect = RuntimeError("Maya error")
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-display", "create_display_layer")
            result = mod.create_display_layer()
        assert result["success"] is False


class TestSetDisplayLayer:
    def test_assign_objects(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.objExists.return_value = True
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-display", "set_display_layer")
            result = mod.set_display_layer("layer1", ["pSphere1", "pCube1"])
        assert result["success"] is True
        assert result["context"]["assigned"] == ["pSphere1", "pCube1"]

    def test_layer_not_found(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.objExists.return_value = False
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-display", "set_display_layer")
            result = mod.set_display_layer("nonexistent", ["pSphere1"])
        assert result["success"] is False

    def test_missing_objects_skipped(self):
        _, cmds_mock, modules = _make_maya_env()
        # layer exists but object doesn't
        cmds_mock.objExists.side_effect = lambda x: x == "layer1"
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-display", "set_display_layer")
            result = mod.set_display_layer("layer1", ["pMissing"])
        assert result["success"] is True
        assert result["context"]["missing"] == ["pMissing"]
        assert result["context"]["assigned"] == []


class TestListDisplayLayers:
    def test_list_layers(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.ls.return_value = ["defaultLayer", "layer1"]
        cmds_mock.getAttr.return_value = 1
        cmds_mock.listRelatives.return_value = ["pSphere1"]
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-display", "list_display_layers")
            result = mod.list_display_layers()
        assert result["success"] is True

    def test_empty_scene(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.ls.return_value = []
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-display", "list_display_layers")
            result = mod.list_display_layers()
        assert result["success"] is True
        assert result["context"]["count"] == 0


# ---------------------------------------------------------------------------
# maya-cameras
# ---------------------------------------------------------------------------


class TestCreateCamera:
    def test_create_default(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.camera.return_value = ("camera1", "cameraShape1")
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-cameras", "create_camera")
            result = mod.create_camera()
        assert result["success"] is True
        assert result["context"]["transform"] == "camera1"
        assert result["context"]["shape"] == "cameraShape1"

    def test_create_with_name(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.camera.return_value = ("camera1", "cameraShape1")
        cmds_mock.rename.return_value = "shotCam"
        cmds_mock.listRelatives.return_value = ["shotCamShape"]
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-cameras", "create_camera")
            result = mod.create_camera(name="shotCam", focal_length=85.0)
        assert result["success"] is True
        assert result["context"]["transform"] == "shotCam"

    def test_create_with_position_and_rotation(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.camera.return_value = ("camera1", "cameraShape1")
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-cameras", "create_camera")
            result = mod.create_camera(position=[0.0, 10.0, 20.0], rotation=[-30.0, 0.0, 0.0])
        assert result["success"] is True
        cmds_mock.move.assert_called_once()
        cmds_mock.rotate.assert_called_once()

    def test_create_exception(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.camera.side_effect = RuntimeError("failed")
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-cameras", "create_camera")
            result = mod.create_camera()
        assert result["success"] is False


class TestSetCameraAttribute:
    def test_set_focal_length(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.objectType.return_value = "camera"
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-cameras", "set_camera_attribute")
            result = mod.set_camera_attribute("cameraShape1", "focalLength", 50.0)
        assert result["success"] is True

    def test_set_via_transform(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.objectType.return_value = "transform"
        cmds_mock.listRelatives.return_value = ["cameraShape1"]
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-cameras", "set_camera_attribute")
            result = mod.set_camera_attribute("camera1", "focalLength", 85.0)
        assert result["success"] is True
        assert result["context"]["camera_name"] == "cameraShape1"

    def test_camera_not_found(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.objExists.return_value = False
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-cameras", "set_camera_attribute")
            result = mod.set_camera_attribute("badCam", "focalLength", 35.0)
        assert result["success"] is False

    def test_transform_no_camera_shape(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.objectType.return_value = "transform"
        cmds_mock.listRelatives.return_value = []
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-cameras", "set_camera_attribute")
            result = mod.set_camera_attribute("emptyTransform", "focalLength", 35.0)
        assert result["success"] is False


class TestGetCameraInfo:
    def _camera_getattr(self, attr):
        """Simulate getAttr: scalar for most, tuple-list for translate/rotate."""
        if ".translate" in attr or ".rotate" in attr:
            return [(0.0, 0.0, 0.0)]
        return 35.0

    def test_get_info_from_shape(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.objectType.return_value = "camera"
        cmds_mock.listRelatives.return_value = ["camera1"]
        cmds_mock.getAttr.side_effect = self._camera_getattr
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-cameras", "get_camera_info")
            result = mod.get_camera_info("cameraShape1")
        assert result["success"] is True
        assert "focal_length" in result["context"]

    def test_get_info_from_transform(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.objectType.return_value = "transform"
        cmds_mock.listRelatives.return_value = ["cameraShape1"]
        cmds_mock.getAttr.side_effect = self._camera_getattr
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-cameras", "get_camera_info")
            result = mod.get_camera_info("camera1")
        assert result["success"] is True

    def test_camera_not_found(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.objExists.return_value = False
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-cameras", "get_camera_info")
            result = mod.get_camera_info("ghost")
        assert result["success"] is False


# ---------------------------------------------------------------------------
# maya-attributes
# ---------------------------------------------------------------------------


class TestGetAttribute:
    def test_get_scalar(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.getAttr.return_value = 5.0
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-attributes", "get_attribute")
            result = mod.get_attribute("pSphere1", "translateX")
        assert result["success"] is True
        assert result["context"]["value"] == 5.0

    def test_get_compound_flattened(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.getAttr.return_value = [(1.0, 2.0, 3.0)]
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-attributes", "get_attribute")
            result = mod.get_attribute("pSphere1", "translate")
        assert result["success"] is True
        assert result["context"]["value"] == [1.0, 2.0, 3.0]

    def test_node_not_found(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.objExists.side_effect = lambda x: x != "pSphere1"
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-attributes", "get_attribute")
            result = mod.get_attribute("pSphere1", "translateX")
        assert result["success"] is False

    def test_attribute_not_found(self):
        _, cmds_mock, modules = _make_maya_env()
        # node exists, attribute doesn't
        cmds_mock.objExists.side_effect = lambda x: x == "pSphere1"
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-attributes", "get_attribute")
            result = mod.get_attribute("pSphere1", "bogusAttr")
        assert result["success"] is False


class TestSetAttribute:
    def test_set_scalar(self):
        _, cmds_mock, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-attributes", "set_attribute")
            result = mod.set_attribute("pSphere1", "translateX", 10.0)
        assert result["success"] is True

    def test_set_string(self):
        _, cmds_mock, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-attributes", "set_attribute")
            result = mod.set_attribute("pSphere1", "notes", "my note")
        assert result["success"] is True
        cmds_mock.setAttr.assert_called_with("pSphere1.notes", "my note", type="string")

    def test_set_list(self):
        _, cmds_mock, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-attributes", "set_attribute")
            result = mod.set_attribute("pSphere1", "translate", [1.0, 2.0, 3.0])
        assert result["success"] is True
        cmds_mock.setAttr.assert_called_with("pSphere1.translate", 1.0, 2.0, 3.0)

    def test_node_not_found(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.objExists.return_value = False
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-attributes", "set_attribute")
            result = mod.set_attribute("ghost", "translateX", 1.0)
        assert result["success"] is False


class TestAddAttribute:
    def test_add_float(self):
        _, cmds_mock, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-attributes", "add_attribute")
            result = mod.add_attribute("pSphere1", "myFloat", "float", 0.0)
        assert result["success"] is True
        assert result["context"]["attribute"] == "myFloat"

    def test_add_string_type(self):
        _, cmds_mock, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-attributes", "add_attribute")
            result = mod.add_attribute("pSphere1", "myStr", "string")
        assert result["success"] is True

    def test_invalid_type(self):
        _, cmds_mock, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-attributes", "add_attribute")
            result = mod.add_attribute("pSphere1", "x", "invalidType")
        assert result["success"] is False

    def test_node_not_found(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.objExists.return_value = False
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-attributes", "add_attribute")
            result = mod.add_attribute("ghost", "x", "float")
        assert result["success"] is False

    def test_add_with_min_max(self):
        _, cmds_mock, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-attributes", "add_attribute")
            result = mod.add_attribute(
                "pSphere1", "clampedVal", "float", default_value=0.5, min_value=0.0, max_value=1.0
            )
        assert result["success"] is True


class TestDeleteAttribute:
    def test_delete_user_attr(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.attributeQuery.return_value = True
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-attributes", "delete_attribute")
            result = mod.delete_attribute("pSphere1", "myFloat")
        assert result["success"] is True

    def test_builtin_attr_rejected(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.attributeQuery.return_value = False
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-attributes", "delete_attribute")
            result = mod.delete_attribute("pSphere1", "translateX")
        assert result["success"] is False

    def test_node_not_found(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.objExists.return_value = False
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-attributes", "delete_attribute")
            result = mod.delete_attribute("ghost", "x")
        assert result["success"] is False


class TestListAttributes:
    def test_list_all(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.listAttr.return_value = ["translateX", "translateY", "translateZ"]
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-attributes", "list_attributes")
            result = mod.list_attributes("pSphere1")
        assert result["success"] is True
        assert result["context"]["count"] == 3

    def test_list_empty(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.listAttr.return_value = None
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-attributes", "list_attributes")
            result = mod.list_attributes("pSphere1")
        assert result["success"] is True
        assert result["context"]["count"] == 0

    def test_node_not_found(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.objExists.return_value = False
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-attributes", "list_attributes")
            result = mod.list_attributes("ghost")
        assert result["success"] is False

    def test_keyable_only_flag(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.listAttr.return_value = ["translateX"]
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-attributes", "list_attributes")
            result = mod.list_attributes("pSphere1", keyable_only=True)
        assert result["success"] is True
        cmds_mock.listAttr.assert_called_once_with("pSphere1", keyable=True)


# ---------------------------------------------------------------------------
# maya-constraints
# ---------------------------------------------------------------------------


class TestAddConstraint:
    def test_add_parent_constraint(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.parentConstraint.return_value = ["pSphere1_parentConstraint1"]
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-constraints", "add_constraint")
            result = mod.add_constraint("parent", "pSphere1", "pCube1")
        assert result["success"] is True
        assert result["context"]["constraint_node"] == "pSphere1_parentConstraint1"

    def test_invalid_constraint_type(self):
        _, cmds_mock, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-constraints", "add_constraint")
            result = mod.add_constraint("bogus", "pSphere1", "pCube1")
        assert result["success"] is False

    def test_source_not_found(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.objExists.side_effect = lambda x: x != "pSphere1"
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-constraints", "add_constraint")
            result = mod.add_constraint("point", "pSphere1", "pCube1")
        assert result["success"] is False

    def test_target_not_found(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.objExists.side_effect = lambda x: x != "pCube1"
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-constraints", "add_constraint")
            result = mod.add_constraint("point", "pSphere1", "pCube1")
        assert result["success"] is False

    def test_aim_constraint(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.aimConstraint.return_value = ["aimConst1"]
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-constraints", "add_constraint")
            result = mod.add_constraint("aim", "locator1", "camera1", weight=0.5)
        assert result["success"] is True


class TestRemoveConstraint:
    def test_remove_all(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.listRelatives.return_value = []
        cmds_mock.listConnections.return_value = ["pCube1_parentConstraint1"]
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-constraints", "remove_constraint")
            result = mod.remove_constraint("pCube1")
        assert result["success"] is True

    def test_remove_none_found(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.listRelatives.return_value = []
        cmds_mock.listConnections.return_value = []
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-constraints", "remove_constraint")
            result = mod.remove_constraint("pCube1")
        assert result["success"] is True
        assert result["context"]["removed"] == []

    def test_target_not_found(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.objExists.return_value = False
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-constraints", "remove_constraint")
            result = mod.remove_constraint("ghost")
        assert result["success"] is False


class TestListConstraints:
    def test_list_with_constraint(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.listRelatives.return_value = []
        # return parentConstraint node on first ctype query
        call_count = [0]

        def list_connections_side(node, **kwargs):
            ctype = kwargs.get("type", "")
            if ctype == "parentConstraint" and call_count[0] == 0:
                call_count[0] += 1
                return ["pCube1_parentConstraint1"]
            return []

        cmds_mock.listConnections.side_effect = list_connections_side
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-constraints", "list_constraints")
            result = mod.list_constraints("pCube1")
        assert result["success"] is True

    def test_list_empty(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.listRelatives.return_value = []
        cmds_mock.listConnections.return_value = []
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-constraints", "list_constraints")
            result = mod.list_constraints("pCube1")
        assert result["success"] is True
        assert result["context"]["count"] == 0

    def test_target_not_found(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.objExists.return_value = False
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-constraints", "list_constraints")
            result = mod.list_constraints("ghost")
        assert result["success"] is False


# ---------------------------------------------------------------------------
# maya-lighting
# ---------------------------------------------------------------------------


class TestCreateLight:
    def test_create_point_light(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.pointLight.return_value = "pointLightShape1"
        cmds_mock.listRelatives.return_value = ["pointLight1"]
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-lighting", "create_light")
            result = mod.create_light("point")
        assert result["success"] is True
        assert result["context"]["light_type"] == "point"

    def test_create_with_name_and_color(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.directionalLight.return_value = "directionalLightShape1"
        cmds_mock.listRelatives.return_value = ["directionalLight1"]
        cmds_mock.rename.return_value = "sunLight"
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-lighting", "create_light")
            result = mod.create_light("directional", name="sunLight", color=[1.0, 0.9, 0.7])
        assert result["success"] is True

    def test_invalid_light_type(self):
        _, cmds_mock, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-lighting", "create_light")
            result = mod.create_light("laser")
        assert result["success"] is False

    def test_create_with_position(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.spotLight.return_value = "spotLightShape1"
        cmds_mock.listRelatives.return_value = ["spotLight1"]
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-lighting", "create_light")
            result = mod.create_light("spot", position=[0.0, 5.0, 0.0], rotation=[-45.0, 0.0, 0.0])
        assert result["success"] is True
        cmds_mock.move.assert_called_once()
        cmds_mock.rotate.assert_called_once()

    def test_create_exception(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.pointLight.side_effect = RuntimeError("oops")
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-lighting", "create_light")
            result = mod.create_light("point")
        assert result["success"] is False


class TestSetLightAttribute:
    def test_set_intensity_on_shape(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.objectType.return_value = "pointLight"
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-lighting", "set_light_attribute")
            result = mod.set_light_attribute("pointLightShape1", "intensity", 3.0)
        assert result["success"] is True

    def test_set_via_transform(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.objectType.return_value = "transform"
        cmds_mock.listRelatives.return_value = ["pointLightShape1"]
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-lighting", "set_light_attribute")
            result = mod.set_light_attribute("pointLight1", "intensity", 2.0)
        assert result["success"] is True
        assert result["context"]["light_name"] == "pointLightShape1"

    def test_light_not_found(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.objExists.return_value = False
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-lighting", "set_light_attribute")
            result = mod.set_light_attribute("ghost", "intensity", 1.0)
        assert result["success"] is False

    def test_transform_no_shape(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.objectType.return_value = "transform"
        cmds_mock.listRelatives.return_value = []
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-lighting", "set_light_attribute")
            result = mod.set_light_attribute("emptyGroup", "intensity", 1.0)
        assert result["success"] is False


class TestListLights:
    def test_list_lights(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.ls.return_value = ["pointLightShape1"]
        cmds_mock.listRelatives.return_value = ["pointLight1"]
        cmds_mock.objectType.return_value = "pointLight"
        cmds_mock.getAttr.return_value = 1.0
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-lighting", "list_lights")
            result = mod.list_lights()
        assert result["success"] is True
        assert result["context"]["count"] == 1
        assert result["context"]["lights"][0]["type"] == "pointLight"

    def test_empty_scene(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.ls.return_value = []
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-lighting", "list_lights")
            result = mod.list_lights()
        assert result["success"] is True
        assert result["context"]["count"] == 0


# ---------------------------------------------------------------------------
# maya-render
# ---------------------------------------------------------------------------


class TestSetRenderSettings:
    def test_set_resolution(self):
        _, cmds_mock, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-render", "set_render_settings")
            result = mod.set_render_settings(width=1920, height=1080)
        assert result["success"] is True
        assert result["context"]["width"] == 1920
        assert result["context"]["height"] == 1080

    def test_set_renderer(self):
        _, cmds_mock, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-render", "set_render_settings")
            result = mod.set_render_settings(renderer="arnold")
        assert result["success"] is True
        assert result["context"]["renderer"] == "arnold"

    def test_set_image_format_png(self):
        _, cmds_mock, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-render", "set_render_settings")
            result = mod.set_render_settings(image_format="png")
        assert result["success"] is True
        cmds_mock.setAttr.assert_any_call("defaultRenderGlobals.imageFormat", 32)

    def test_set_frame_range(self):
        _, cmds_mock, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-render", "set_render_settings")
            result = mod.set_render_settings(start_frame=1.0, end_frame=120.0)
        assert result["success"] is True
        assert result["context"]["start_frame"] == 1.0

    def test_no_settings_error(self):
        _, cmds_mock, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-render", "set_render_settings")
            result = mod.set_render_settings()
        assert result["success"] is False

    def test_exception(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.setAttr.side_effect = RuntimeError("locked")
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-render", "set_render_settings")
            result = mod.set_render_settings(width=1920)
        assert result["success"] is False


class TestGetRenderSettings:
    def test_get_settings(self):
        _, cmds_mock, modules = _make_maya_env()

        def getattr_side(attr):
            mapping = {
                "defaultResolution.width": 1920,
                "defaultResolution.height": 1080,
                "defaultRenderGlobals.startFrame": 1.0,
                "defaultRenderGlobals.endFrame": 100.0,
                "defaultRenderGlobals.currentRenderer": "mayaSoftware",
                "defaultRenderGlobals.imageFormat": 32,
                "defaultRenderGlobals.imageFilePrefix": "",
            }
            return mapping.get(attr, 0)

        cmds_mock.getAttr.side_effect = getattr_side
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-render", "get_render_settings")
            result = mod.get_render_settings()
        assert result["success"] is True
        assert result["context"]["width"] == 1920
        assert result["context"]["image_format"] == "png"

    def test_exception(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.getAttr.side_effect = RuntimeError("no node")
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-render", "get_render_settings")
            result = mod.get_render_settings()
        assert result["success"] is False


class TestPlayblast:
    def test_playblast_success(self):
        """Test playblast returns base64 image when file is found."""
        import base64
        import os
        import tempfile

        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.currentTime.return_value = 1.0

        # Create a real temp file to simulate the playblast output
        tmp_dir = tempfile.mkdtemp()
        fake_img_path = os.path.join(tmp_dir, "mcp_blast_.0001.png")
        fake_png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
        with open(fake_img_path, "wb") as fh:
            fh.write(fake_png)

        def fake_playblast(**kwargs):
            pass  # mock does nothing — we set up the file manually

        cmds_mock.playblast.side_effect = fake_playblast

        # Patch NamedTemporaryFile to return our controlled path
        import builtins

        original_open = builtins.open

        class FakeTmpFile:
            name = os.path.join(tmp_dir, "mcp_blast_.png")

            def __enter__(self):
                return self

            def __exit__(self, *a):
                pass

        with patch.dict(sys.modules, modules):
            with patch("tempfile.NamedTemporaryFile", return_value=FakeTmpFile()):
                with patch("os.path.exists", side_effect=lambda p: p == fake_img_path):
                    with patch(
                        "builtins.open",
                        side_effect=lambda p, *a, **kw: (
                            original_open(p, *a, **kw) if p == fake_img_path else original_open(p, *a, **kw)
                        ),
                    ):
                        mod = _load_script("maya-render", "playblast")
                        result = mod.playblast(width=1280, height=720)

        # cleanup
        try:
            os.unlink(fake_img_path)
            os.rmdir(tmp_dir)
        except OSError:
            pass

        assert result["success"] is True
        assert "image" in result["context"]
        decoded = base64.b64decode(result["context"]["image"])
        assert decoded[:8] == b"\x89PNG\r\n\x1a\n"

    def test_playblast_file_not_found(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.currentTime.return_value = 1.0

        with patch.dict(sys.modules, modules):
            with patch("os.path.exists", return_value=False):
                mod = _load_script("maya-render", "playblast")
                result = mod.playblast()

        assert result["success"] is False

    def test_playblast_exception(self):
        _, cmds_mock, modules = _make_maya_env()
        cmds_mock.currentTime.return_value = 1.0
        cmds_mock.playblast.side_effect = RuntimeError("no display")
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-render", "playblast")
            result = mod.playblast()
        assert result["success"] is False
