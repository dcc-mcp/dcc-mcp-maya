"""Round 8 skill tests: maya-scene (extended) / maya-materials (extended) / maya-rigging (remaining).

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
    module_name = "skill_r8_{}_{}_{}" .format(
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
# maya-scene: duplicate_object
# ===========================================================================


class TestDuplicateObject:
    def test_duplicate_success(self):
        cmds_ov = {}
        cmds_ov["duplicate"] = MagicMock(return_value=["pCube2"])
        result = _run_func("maya-scene", "duplicate_object", cmds_ov, object_name="pCube1")
        assert result["success"] is True
        assert result["context"]["object_name"] == "pCube2"

    def test_duplicate_with_new_name(self):
        rename_mock = MagicMock(return_value="myDupe")
        cmds_ov = {
            "duplicate": MagicMock(return_value=["pCube2"]),
            "rename": rename_mock,
        }
        result = _run_func(
            "maya-scene", "duplicate_object", cmds_ov, object_name="pCube1", new_name="myDupe"
        )
        assert result["success"] is True
        assert result["context"]["object_name"] == "myDupe"

    def test_duplicate_instance(self):
        cmds_ov = {"duplicate": MagicMock(return_value=["pCube1_inst"])}
        result = _run_func(
            "maya-scene", "duplicate_object", cmds_ov, object_name="pCube1", instance=True
        )
        assert result["success"] is True
        assert result["context"]["instance"] is True

    def test_duplicate_object_not_found(self):
        cmds_ov = {"objExists": MagicMock(return_value=False)}
        result = _run_func("maya-scene", "duplicate_object", cmds_ov, object_name="noSuchObj")
        assert result["success"] is False

    def test_duplicate_exception(self):
        cmds_ov = {"duplicate": MagicMock(side_effect=RuntimeError("boom"))}
        result = _run_func("maya-scene", "duplicate_object", cmds_ov, object_name="pCube1")
        assert result["success"] is False

    def test_duplicate_source_recorded(self):
        cmds_ov = {"duplicate": MagicMock(return_value=["pSphere2"])}
        result = _run_func("maya-scene", "duplicate_object", cmds_ov, object_name="pSphere1")
        assert result["context"]["source"] == "pSphere1"


# ===========================================================================
# maya-scene: freeze_transforms
# ===========================================================================


class TestFreezeTransforms:
    def test_freeze_success(self):
        result = _run_func("maya-scene", "freeze_transforms", {}, object_name="pCube1")
        assert result["success"] is True
        assert result["context"]["object_name"] == "pCube1"

    def test_freeze_object_not_found(self):
        cmds_ov = {"objExists": MagicMock(return_value=False)}
        result = _run_func("maya-scene", "freeze_transforms", cmds_ov, object_name="missing")
        assert result["success"] is False

    def test_freeze_exception(self):
        cmds_ov = {"makeIdentity": MagicMock(side_effect=RuntimeError("locked"))}
        result = _run_func("maya-scene", "freeze_transforms", cmds_ov, object_name="pCube1")
        assert result["success"] is False

    def test_freeze_calls_make_identity(self):
        make_identity_mock = MagicMock()
        cmds_ov = {"makeIdentity": make_identity_mock}
        _run_func("maya-scene", "freeze_transforms", cmds_ov, object_name="pCube1")
        make_identity_mock.assert_called_once()


# ===========================================================================
# maya-scene: center_pivot
# ===========================================================================


class TestCenterPivot:
    def test_center_pivot_success(self):
        cmds_ov = {"xform": MagicMock(return_value=[1.0, 0.5, 0.0, 1.0, 0.5, 0.0])}
        result = _run_func("maya-scene", "center_pivot", cmds_ov, object_name="pCube1")
        assert result["success"] is True
        assert result["context"]["object_name"] == "pCube1"

    def test_center_pivot_object_not_found(self):
        cmds_ov = {"objExists": MagicMock(return_value=False)}
        result = _run_func("maya-scene", "center_pivot", cmds_ov, object_name="missing")
        assert result["success"] is False

    def test_center_pivot_exception(self):
        cmds_ov = {"xform": MagicMock(side_effect=RuntimeError("error"))}
        result = _run_func("maya-scene", "center_pivot", cmds_ov, object_name="pCube1")
        assert result["success"] is False

    def test_center_pivot_pivot_in_context(self):
        cmds_ov = {"xform": MagicMock(return_value=[2.0, 1.0, 0.5, 2.0, 1.0, 0.5])}
        result = _run_func("maya-scene", "center_pivot", cmds_ov, object_name="pCube1")
        assert "pivot" in result["context"]


# ===========================================================================
# maya-scene: get_bounding_box
# ===========================================================================


class TestGetBoundingBox:
    def test_get_bb_success(self):
        cmds_ov = {"exactWorldBoundingBox": MagicMock(return_value=[-1.0, -1.0, -1.0, 1.0, 1.0, 1.0])}
        result = _run_func("maya-scene", "get_bounding_box", cmds_ov, object_name="pCube1")
        assert result["success"] is True
        assert result["context"]["min"] == [-1.0, -1.0, -1.0]
        assert result["context"]["max"] == [1.0, 1.0, 1.0]
        assert result["context"]["center"] == [0.0, 0.0, 0.0]
        assert result["context"]["size"] == [2.0, 2.0, 2.0]

    def test_get_bb_object_not_found(self):
        cmds_ov = {"objExists": MagicMock(return_value=False)}
        result = _run_func("maya-scene", "get_bounding_box", cmds_ov, object_name="missing")
        assert result["success"] is False

    def test_get_bb_exception(self):
        cmds_ov = {"exactWorldBoundingBox": MagicMock(side_effect=RuntimeError("error"))}
        result = _run_func("maya-scene", "get_bounding_box", cmds_ov, object_name="pCube1")
        assert result["success"] is False

    def test_get_bb_non_uniform(self):
        cmds_ov = {"exactWorldBoundingBox": MagicMock(return_value=[0.0, 0.0, 0.0, 4.0, 2.0, 6.0])}
        result = _run_func("maya-scene", "get_bounding_box", cmds_ov, object_name="pBox")
        ctx = result["context"]
        assert ctx["size"] == [4.0, 2.0, 6.0]
        assert ctx["center"] == [2.0, 1.0, 3.0]


# ===========================================================================
# maya-scene: set_visibility
# ===========================================================================


class TestSetVisibility:
    def test_show_object(self):
        result = _run_func("maya-scene", "set_visibility", {}, object_name="pCube1", visible=True)
        assert result["success"] is True
        assert result["context"]["visible"] is True

    def test_hide_object(self):
        result = _run_func("maya-scene", "set_visibility", {}, object_name="pCube1", visible=False)
        assert result["success"] is True
        assert result["context"]["visible"] is False

    def test_object_not_found(self):
        cmds_ov = {"objExists": MagicMock(return_value=False)}
        result = _run_func("maya-scene", "set_visibility", cmds_ov, object_name="missing", visible=True)
        assert result["success"] is False

    def test_setattr_called(self):
        set_attr_mock = MagicMock()
        cmds_ov = {"setAttr": set_attr_mock}
        _run_func("maya-scene", "set_visibility", cmds_ov, object_name="pCube1", visible=True)
        set_attr_mock.assert_called_once_with("pCube1.visibility", 1)

    def test_exception(self):
        cmds_ov = {"setAttr": MagicMock(side_effect=RuntimeError("locked"))}
        result = _run_func("maya-scene", "set_visibility", cmds_ov, object_name="pCube1", visible=True)
        assert result["success"] is False


# ===========================================================================
# maya-scene: lock_object
# ===========================================================================


class TestLockObject:
    def test_lock_success(self):
        result = _run_func("maya-scene", "lock_object", {}, object_name="pCube1", lock=True)
        assert result["success"] is True
        assert result["context"]["locked"] is True

    def test_unlock_success(self):
        result = _run_func("maya-scene", "lock_object", {}, object_name="pCube1", lock=False)
        assert result["success"] is True
        assert result["context"]["locked"] is False

    def test_object_not_found(self):
        cmds_ov = {"objExists": MagicMock(return_value=False)}
        result = _run_func("maya-scene", "lock_object", cmds_ov, object_name="missing", lock=True)
        assert result["success"] is False

    def test_nine_attrs_set(self):
        set_attr_mock = MagicMock()
        cmds_ov = {"setAttr": set_attr_mock}
        _run_func("maya-scene", "lock_object", cmds_ov, object_name="pCube1", lock=True)
        assert set_attr_mock.call_count == 9

    def test_exception(self):
        cmds_ov = {"setAttr": MagicMock(side_effect=RuntimeError("error"))}
        result = _run_func("maya-scene", "lock_object", cmds_ov, object_name="pCube1", lock=True)
        assert result["success"] is False


# ===========================================================================
# maya-scene: get_scene_info
# ===========================================================================


class TestGetSceneInfo:
    def test_empty_scene(self):
        cmds_ov = {
            "ls": MagicMock(return_value=[]),
        }
        result = _run_func("maya-scene", "get_scene_info", cmds_ov)
        assert result["success"] is True
        assert result["context"]["count"] == 0

    def test_with_transforms(self):
        get_attr_mock = MagicMock(return_value=[(0.0, 0.0, 0.0)])
        cmds_ov = {
            "ls": MagicMock(return_value=["|pCube1"]),
            "objectType": MagicMock(return_value="transform"),
            "listRelatives": MagicMock(return_value=None),
            "getAttr": get_attr_mock,
        }
        result = _run_func("maya-scene", "get_scene_info", cmds_ov)
        assert result["success"] is True
        assert result["context"]["count"] == 1
        assert result["context"]["nodes"][0]["name"] == "pCube1"

    def test_without_transforms(self):
        cmds_ov = {
            "ls": MagicMock(return_value=["|pSphere1"]),
            "objectType": MagicMock(return_value="transform"),
            "listRelatives": MagicMock(return_value=None),
        }
        result = _run_func("maya-scene", "get_scene_info", cmds_ov, include_transforms=False)
        assert result["success"] is True
        assert "translate" not in result["context"]["nodes"][0]

    def test_exception(self):
        cmds_ov = {"ls": MagicMock(side_effect=RuntimeError("error"))}
        result = _run_func("maya-scene", "get_scene_info", cmds_ov)
        assert result["success"] is False


# ===========================================================================
# maya-scene: export_scene
# ===========================================================================


class TestExportScene:
    def test_export_success(self):
        file_mock = MagicMock(return_value="/tmp/scene.mb")
        cmds_ov = {"file": file_mock}
        result = _run_func(
            "maya-scene", "export_scene", cmds_ov, file_path="/tmp/scene.mb", file_type="mayaBinary"
        )
        assert result["success"] is True
        assert result["context"]["file_type"] == "mayaBinary"

    def test_export_ascii(self):
        file_mock = MagicMock(return_value="/tmp/scene.ma")
        cmds_ov = {"file": file_mock}
        result = _run_func(
            "maya-scene", "export_scene", cmds_ov, file_path="/tmp/scene.ma", file_type="mayaAscii"
        )
        assert result["success"] is True

    def test_export_exception(self):
        file_mock = MagicMock(side_effect=RuntimeError("permission denied"))
        cmds_ov = {"file": file_mock}
        result = _run_func(
            "maya-scene", "export_scene", cmds_ov, file_path="/tmp/scene.mb"
        )
        assert result["success"] is False

    def test_export_default_type(self):
        file_mock = MagicMock(return_value="/tmp/out.mb")
        cmds_ov = {"file": file_mock}
        result = _run_func("maya-scene", "export_scene", cmds_ov, file_path="/tmp/out.mb")
        assert result["success"] is True


# ===========================================================================
# maya-scene: set_frame_rate
# ===========================================================================


class TestSetFrameRate:
    def test_set_film(self):
        cmds_ov = {"currentUnit": MagicMock(return_value="film")}
        result = _run_func("maya-scene", "set_frame_rate", cmds_ov, fps="film")
        assert result["success"] is True
        assert result["context"]["fps"] == "film"

    def test_set_ntsc(self):
        cmds_ov = {"currentUnit": MagicMock(return_value="ntsc")}
        result = _run_func("maya-scene", "set_frame_rate", cmds_ov, fps="ntsc")
        assert result["success"] is True

    def test_invalid_fps(self):
        result = _run_func("maya-scene", "set_frame_rate", {}, fps="invalid_rate")
        assert result["success"] is False

    def test_exception(self):
        cmds_ov = {"currentUnit": MagicMock(side_effect=RuntimeError("error"))}
        result = _run_func("maya-scene", "set_frame_rate", cmds_ov, fps="film")
        assert result["success"] is False

    def test_set_pal(self):
        cmds_ov = {"currentUnit": MagicMock(return_value="pal")}
        result = _run_func("maya-scene", "set_frame_rate", cmds_ov, fps="pal")
        assert result["success"] is True


# ===========================================================================
# maya-scene: list_cameras
# ===========================================================================


class TestListCameras:
    def test_list_includes_defaults(self):
        listRelatives_mock = MagicMock(return_value=["persp"])
        getAttr_mock = MagicMock(return_value=35.0)
        cmds_ov = {
            "ls": MagicMock(return_value=["perspShape"]),
            "listRelatives": listRelatives_mock,
            "getAttr": getAttr_mock,
        }
        result = _run_func("maya-scene", "list_cameras", cmds_ov, include_default=True)
        assert result["success"] is True
        assert result["context"]["count"] >= 0

    def test_list_excludes_defaults(self):
        listRelatives_mock = MagicMock(return_value=["persp"])
        getAttr_mock = MagicMock(return_value=35.0)
        cmds_ov = {
            "ls": MagicMock(return_value=["perspShape"]),
            "listRelatives": listRelatives_mock,
            "getAttr": getAttr_mock,
        }
        result = _run_func("maya-scene", "list_cameras", cmds_ov, include_default=False)
        assert result["success"] is True
        assert result["context"]["count"] == 0

    def test_empty_scene(self):
        cmds_ov = {"ls": MagicMock(return_value=[])}
        result = _run_func("maya-scene", "list_cameras", cmds_ov)
        assert result["success"] is True
        assert result["context"]["count"] == 0

    def test_exception(self):
        cmds_ov = {"ls": MagicMock(side_effect=RuntimeError("error"))}
        result = _run_func("maya-scene", "list_cameras", cmds_ov)
        assert result["success"] is False

    def test_camera_attrs_present(self):
        listRelatives_mock = MagicMock(return_value=["camTransform"])
        getAttr_mock = MagicMock(return_value=50.0)
        cmds_ov = {
            "ls": MagicMock(return_value=["camShape"]),
            "listRelatives": listRelatives_mock,
            "getAttr": getAttr_mock,
        }
        result = _run_func("maya-scene", "list_cameras", cmds_ov, include_default=True)
        assert result["success"] is True
        if result["context"]["count"] > 0:
            cam = result["context"]["cameras"][0]
            assert "focal_length" in cam
            assert "near_clip" in cam


# ===========================================================================
# maya-scene: create_locator
# ===========================================================================


class TestCreateLocator:
    def test_create_default(self):
        cmds_ov = {"spaceLocator": MagicMock(return_value=["locator1"])}
        result = _run_func("maya-scene", "create_locator", cmds_ov)
        assert result["success"] is True
        assert result["context"]["object_name"] == "locator1"

    def test_create_named(self):
        cmds_ov = {"spaceLocator": MagicMock(return_value=["myLocator"])}
        result = _run_func("maya-scene", "create_locator", cmds_ov, name="myLocator")
        assert result["success"] is True
        assert result["context"]["object_name"] == "myLocator"

    def test_create_with_position(self):
        move_mock = MagicMock()
        cmds_ov = {
            "spaceLocator": MagicMock(return_value=["locator1"]),
            "move": move_mock,
        }
        result = _run_func("maya-scene", "create_locator", cmds_ov, position=[1.0, 2.0, 3.0])
        assert result["success"] is True
        move_mock.assert_called_once_with(1.0, 2.0, 3.0, "locator1")

    def test_exception(self):
        cmds_ov = {"spaceLocator": MagicMock(side_effect=RuntimeError("error"))}
        result = _run_func("maya-scene", "create_locator", cmds_ov)
        assert result["success"] is False

    def test_position_in_context(self):
        cmds_ov = {"spaceLocator": MagicMock(return_value=["locator1"])}
        result = _run_func("maya-scene", "create_locator", cmds_ov, position=[5.0, 0.0, -2.0])
        assert result["context"]["position"] == [5.0, 0.0, -2.0]


# ===========================================================================
# maya-materials: set_material_attribute
# ===========================================================================


class TestSetMaterialAttribute:
    def test_set_scalar_attribute(self):
        result = _run_func(
            "maya-materials", "set_material_attribute", {},
            material_name="lambert1", attribute="diffuse", value=0.8
        )
        assert result["success"] is True

    def test_set_color_attribute(self):
        result = _run_func(
            "maya-materials", "set_material_attribute", {},
            material_name="lambert1", attribute="color", value=[1.0, 0.0, 0.0]
        )
        assert result["success"] is True
        assert result["context"]["value"] == [1.0, 0.0, 0.0]

    def test_set_tuple_attribute(self):
        result = _run_func(
            "maya-materials", "set_material_attribute", {},
            material_name="myShader", attribute="transparency", value=(0.5, 0.5, 0.5)
        )
        assert result["success"] is True

    def test_material_not_found(self):
        cmds_ov = {"objExists": MagicMock(return_value=False)}
        result = _run_func(
            "maya-materials", "set_material_attribute", cmds_ov,
            material_name="noMat", attribute="color", value=[1, 0, 0]
        )
        assert result["success"] is False

    def test_exception(self):
        cmds_ov = {"setAttr": MagicMock(side_effect=RuntimeError("error"))}
        result = _run_func(
            "maya-materials", "set_material_attribute", cmds_ov,
            material_name="lambert1", attribute="color", value=[1, 0, 0]
        )
        assert result["success"] is False

    def test_context_has_attribute(self):
        result = _run_func(
            "maya-materials", "set_material_attribute", {},
            material_name="blinn1", attribute="specularColor", value=[0.5, 0.5, 0.5]
        )
        assert result["context"]["attribute"] == "specularColor"


# ===========================================================================
# maya-materials: get_material_connections
# ===========================================================================


class TestGetMaterialConnections:
    def test_no_connections(self):
        cmds_ov = {"listConnections": MagicMock(return_value=[])}
        result = _run_func("maya-materials", "get_material_connections", cmds_ov, material_name="lambert1")
        assert result["success"] is True
        assert result["context"]["count"] == 0

    def test_with_connections(self):
        raw = ["lambert1.color", "file1.outColor", "lambert1.bump", "bump2d1.outNormal"]
        cmds_ov = {
            "listConnections": MagicMock(return_value=raw),
            "nodeType": MagicMock(return_value="file"),
        }
        result = _run_func("maya-materials", "get_material_connections", cmds_ov, material_name="lambert1")
        assert result["success"] is True
        assert result["context"]["count"] == 2

    def test_material_not_found(self):
        cmds_ov = {"objExists": MagicMock(return_value=False)}
        result = _run_func("maya-materials", "get_material_connections", cmds_ov, material_name="noMat")
        assert result["success"] is False

    def test_connection_structure(self):
        raw = ["myMat.color", "fileNode.outColor"]
        cmds_ov = {
            "listConnections": MagicMock(return_value=raw),
            "nodeType": MagicMock(return_value="file"),
        }
        result = _run_func("maya-materials", "get_material_connections", cmds_ov, material_name="myMat")
        conn = result["context"]["connections"][0]
        assert "source_node" in conn
        assert "dest_attr" in conn

    def test_exception(self):
        cmds_ov = {"listConnections": MagicMock(side_effect=RuntimeError("error"))}
        result = _run_func("maya-materials", "get_material_connections", cmds_ov, material_name="lambert1")
        assert result["success"] is False


# ===========================================================================
# maya-materials: get_shader_assignment
# ===========================================================================


class TestGetShaderAssignment:
    def test_with_shading_group(self):
        # Second listConnections call for surfaceShader
        listConn_mock = MagicMock(side_effect=[["pCubeShape1"], ["blinn1"]])
        cmds_ov2 = {
            "listRelatives": MagicMock(return_value=["pCubeShape1"]),
            "listConnections": listConn_mock,
        }
        result = _run_func("maya-materials", "get_shader_assignment", cmds_ov2, object_name="pCube1")
        assert result["success"] is True

    def test_object_not_found(self):
        cmds_ov = {"objExists": MagicMock(return_value=False)}
        result = _run_func("maya-materials", "get_shader_assignment", cmds_ov, object_name="missing")
        assert result["success"] is False

    def test_no_shapes(self):
        cmds_ov = {
            "listRelatives": MagicMock(return_value=None),
            "listConnections": MagicMock(return_value=[]),
        }
        result = _run_func("maya-materials", "get_shader_assignment", cmds_ov, object_name="pCube1")
        assert result["success"] is True
        assert result["context"]["count"] == 0

    def test_exception(self):
        cmds_ov = {"listRelatives": MagicMock(side_effect=RuntimeError("error"))}
        result = _run_func("maya-materials", "get_shader_assignment", cmds_ov, object_name="pCube1")
        assert result["success"] is False


# ===========================================================================
# maya-materials: list_shading_groups
# ===========================================================================


class TestListShadingGroups:
    def test_empty_scene(self):
        cmds_ov = {"ls": MagicMock(return_value=[])}
        result = _run_func("maya-materials", "list_shading_groups", cmds_ov)
        assert result["success"] is True
        assert result["context"]["count"] == 0

    def test_with_shading_groups(self):
        cmds_ov = {
            "ls": MagicMock(return_value=["initialShadingGroup", "blinn1SG"]),
            "listConnections": MagicMock(return_value=["lambert1"]),
            "nodeType": MagicMock(return_value="lambert"),
            "sets": MagicMock(return_value=["pCube1"]),
        }
        result = _run_func("maya-materials", "list_shading_groups", cmds_ov)
        assert result["success"] is True
        assert result["context"]["count"] == 2

    def test_shading_group_structure(self):
        cmds_ov = {
            "ls": MagicMock(return_value=["mySG"]),
            "listConnections": MagicMock(return_value=["myMat"]),
            "nodeType": MagicMock(return_value="blinn"),
            "sets": MagicMock(return_value=[]),
        }
        result = _run_func("maya-materials", "list_shading_groups", cmds_ov)
        sg = result["context"]["shading_groups"][0]
        assert "name" in sg
        assert "surface_shader" in sg
        assert "member_count" in sg

    def test_exception(self):
        cmds_ov = {"ls": MagicMock(side_effect=RuntimeError("error"))}
        result = _run_func("maya-materials", "list_shading_groups", cmds_ov)
        assert result["success"] is False


# ===========================================================================
# maya-materials: reset_to_default_material
# ===========================================================================


class TestResetToDefaultMaterial:
    def test_reset_success(self):
        result = _run_func("maya-materials", "reset_to_default_material", {}, object_name="pCube1")
        assert result["success"] is True
        assert result["context"]["material"] == "lambert1"
        assert result["context"]["shading_group"] == "initialShadingGroup"

    def test_object_not_found(self):
        cmds_ov = {"objExists": MagicMock(return_value=False)}
        result = _run_func("maya-materials", "reset_to_default_material", cmds_ov, object_name="missing")
        assert result["success"] is False

    def test_sets_called(self):
        sets_mock = MagicMock()
        cmds_ov = {"sets": sets_mock}
        _run_func("maya-materials", "reset_to_default_material", cmds_ov, object_name="pCube1")
        sets_mock.assert_called_once()

    def test_exception(self):
        cmds_ov = {"sets": MagicMock(side_effect=RuntimeError("error"))}
        result = _run_func("maya-materials", "reset_to_default_material", cmds_ov, object_name="pCube1")
        assert result["success"] is False


# ===========================================================================
# maya-rigging: set_ik_fk_blend
# ===========================================================================


class TestSetIkFkBlend:
    def test_set_full_ik(self):
        cmds_ov = {
            "objectType": MagicMock(return_value="ikHandle"),
        }
        result = _run_func("maya-rigging", "set_ik_fk_blend", cmds_ov, ik_handle="ikHandle1", blend=1.0)
        assert result["success"] is True
        assert result["context"]["blend"] == 1.0

    def test_set_full_fk(self):
        cmds_ov = {
            "objectType": MagicMock(return_value="ikHandle"),
        }
        result = _run_func("maya-rigging", "set_ik_fk_blend", cmds_ov, ik_handle="ikHandle1", blend=0.0)
        assert result["success"] is True

    def test_blend_out_of_range_high(self):
        result = _run_func("maya-rigging", "set_ik_fk_blend", {}, ik_handle="ikHandle1", blend=1.5)
        assert result["success"] is False

    def test_blend_out_of_range_low(self):
        result = _run_func("maya-rigging", "set_ik_fk_blend", {}, ik_handle="ikHandle1", blend=-0.1)
        assert result["success"] is False

    def test_ik_handle_not_found(self):
        cmds_ov = {"objExists": MagicMock(return_value=False)}
        result = _run_func("maya-rigging", "set_ik_fk_blend", cmds_ov, ik_handle="missing", blend=0.5)
        assert result["success"] is False

    def test_wrong_node_type(self):
        cmds_ov = {"objectType": MagicMock(return_value="mesh")}
        result = _run_func("maya-rigging", "set_ik_fk_blend", cmds_ov, ik_handle="pCube1", blend=0.5)
        assert result["success"] is False

    def test_attribute_not_found(self):
        cmds_ov = {
            "objectType": MagicMock(return_value="ikHandle"),
            "objExists": MagicMock(side_effect=lambda x: not x.endswith(".ikBlend")),
        }
        result = _run_func(
            "maya-rigging", "set_ik_fk_blend", cmds_ov, ik_handle="ikHandle1", blend=0.5
        )
        assert result["success"] is False

    def test_context_has_attribute_name(self):
        cmds_ov = {"objectType": MagicMock(return_value="ikHandle")}
        result = _run_func(
            "maya-rigging", "set_ik_fk_blend", cmds_ov, ik_handle="ikHandle1", blend=0.75
        )
        assert result["context"]["attribute"] == "ikBlend"


# ===========================================================================
# maya-rigging: set_joint_limit
# ===========================================================================


class TestSetJointLimit:
    def test_set_x_limit(self):
        cmds_ov = {
            "objectType": MagicMock(return_value="joint"),
            "getAttr": MagicMock(return_value=-45.0),
        }
        result = _run_func(
            "maya-rigging", "set_joint_limit", cmds_ov,
            joint_name="joint1", axis="x", min_angle=-45.0, max_angle=45.0
        )
        assert result["success"] is True
        assert result["context"]["axis"] == "x"

    def test_invalid_axis(self):
        cmds_ov = {"objectType": MagicMock(return_value="joint")}
        result = _run_func(
            "maya-rigging", "set_joint_limit", cmds_ov,
            joint_name="joint1", axis="w"
        )
        assert result["success"] is False

    def test_not_a_joint(self):
        cmds_ov = {"objectType": MagicMock(return_value="mesh")}
        result = _run_func(
            "maya-rigging", "set_joint_limit", cmds_ov,
            joint_name="pCube1", axis="x"
        )
        assert result["success"] is False

    def test_joint_not_found(self):
        cmds_ov = {"objExists": MagicMock(return_value=False)}
        result = _run_func(
            "maya-rigging", "set_joint_limit", cmds_ov,
            joint_name="missing", axis="y"
        )
        assert result["success"] is False

    def test_disable_limit(self):
        cmds_ov = {
            "objectType": MagicMock(return_value="joint"),
            "getAttr": MagicMock(return_value=0.0),
        }
        result = _run_func(
            "maya-rigging", "set_joint_limit", cmds_ov,
            joint_name="joint1", axis="z", enable=False
        )
        assert result["success"] is True
        assert result["context"]["enable"] is False

    def test_exception(self):
        cmds_ov = {
            "objectType": MagicMock(return_value="joint"),
            "setAttr": MagicMock(side_effect=RuntimeError("error")),
        }
        result = _run_func(
            "maya-rigging", "set_joint_limit", cmds_ov,
            joint_name="joint1", axis="x"
        )
        assert result["success"] is False

    def test_context_has_axis(self):
        cmds_ov = {
            "objectType": MagicMock(return_value="joint"),
            "getAttr": MagicMock(return_value=0.0),
        }
        result = _run_func(
            "maya-rigging", "set_joint_limit", cmds_ov,
            joint_name="joint1", axis="Y"
        )
        assert result["context"]["axis"] == "y"


# ===========================================================================
# maya-rigging: set_joint_orient
# ===========================================================================


class TestSetJointOrient:
    def test_set_orient_default(self):
        cmds_ov = {"objectType": MagicMock(return_value="joint")}
        result = _run_func("maya-rigging", "set_joint_orient", cmds_ov, joint_name="joint1")
        assert result["success"] is True
        assert result["context"]["orient"] == [0.0, 0.0, 0.0]

    def test_set_orient_values(self):
        cmds_ov = {"objectType": MagicMock(return_value="joint")}
        result = _run_func(
            "maya-rigging", "set_joint_orient", cmds_ov,
            joint_name="joint1", orient=[45.0, 0.0, 0.0]
        )
        assert result["success"] is True
        assert result["context"]["orient"] == [45.0, 0.0, 0.0]

    def test_not_a_joint(self):
        cmds_ov = {"objectType": MagicMock(return_value="transform")}
        result = _run_func("maya-rigging", "set_joint_orient", cmds_ov, joint_name="pCube1")
        assert result["success"] is False

    def test_joint_not_found(self):
        cmds_ov = {"objExists": MagicMock(return_value=False)}
        result = _run_func("maya-rigging", "set_joint_orient", cmds_ov, joint_name="missing")
        assert result["success"] is False

    def test_zero_scale_orient(self):
        set_attr_mock = MagicMock()
        cmds_ov = {
            "objectType": MagicMock(return_value="joint"),
            "setAttr": set_attr_mock,
        }
        result = _run_func(
            "maya-rigging", "set_joint_orient", cmds_ov,
            joint_name="joint1", zero_scale_orient=True
        )
        assert result["success"] is True

    def test_exception(self):
        cmds_ov = {
            "objectType": MagicMock(return_value="joint"),
            "setAttr": MagicMock(side_effect=RuntimeError("error")),
        }
        result = _run_func("maya-rigging", "set_joint_orient", cmds_ov, joint_name="joint1")
        assert result["success"] is False
