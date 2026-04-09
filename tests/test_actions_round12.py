"""Tests for Round 12 actions: lighting, cameras, mesh_ops."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import sys
from unittest.mock import MagicMock, patch

# Import third-party modules
import pytest


# ---------------------------------------------------------------------------
# Shared fixture — mock maya.cmds + dcc_mcp_core
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def mock_maya(monkeypatch):
    """Provide a mock maya.cmds environment for all tests in this module."""
    mock_cmds = MagicMock()

    # Default side-effects
    mock_cmds.ls.return_value = []
    mock_cmds.objExists.return_value = True
    mock_cmds.objectType.return_value = "transform"
    mock_cmds.listRelatives.return_value = []

    maya_mock = MagicMock()
    maya_mock.cmds = mock_cmds

    monkeypatch.setitem(sys.modules, "maya", maya_mock)
    monkeypatch.setitem(sys.modules, "maya.cmds", mock_cmds)
    monkeypatch.setitem(sys.modules, "maya.api", MagicMock())
    monkeypatch.setitem(sys.modules, "maya.utils", MagicMock())

    # Patch dcc_mcp_core result helpers
    def _ok(msg, **ctx):
        m = MagicMock()
        m.to_dict.return_value = {"success": True, "message": msg, "context": ctx}
        return m

    def _err(msg, detail=""):
        m = MagicMock()
        m.to_dict.return_value = {"success": False, "message": msg, "detail": detail}
        return m

    monkeypatch.setitem(sys.modules, "dcc_mcp_core", MagicMock(
        success_result=_ok,
        error_result=_err,
    ))

    # Reload modules to pick up mocks
    for mod_name in list(sys.modules.keys()):
        if mod_name.startswith("dcc_mcp_maya"):
            del sys.modules[mod_name]

    yield mock_cmds


# ===========================================================================
# TestCreateLight
# ===========================================================================

class TestCreateLight:
    def test_create_point_light_default(self, mock_maya):
        mock_maya.pointLight.return_value = "pointLightShape1"
        mock_maya.listRelatives.return_value = ["pointLight1"]

        from dcc_mcp_maya.actions.lighting import create_light
        result = create_light(light_type="point")

        assert result["success"] is True
        mock_maya.pointLight.assert_called_once()

    def test_create_spot_light(self, mock_maya):
        mock_maya.spotLight.return_value = "spotLightShape1"
        mock_maya.listRelatives.return_value = ["spotLight1"]

        from dcc_mcp_maya.actions.lighting import create_light
        result = create_light(light_type="spot", intensity=2.5)

        assert result["success"] is True
        mock_maya.spotLight.assert_called_once()

    def test_create_directional_light_with_name(self, mock_maya):
        mock_maya.directionalLight.return_value = "directionalLightShape1"
        mock_maya.listRelatives.return_value = ["myLight"]

        from dcc_mcp_maya.actions.lighting import create_light
        result = create_light(light_type="directional", name="myLight")

        assert result["success"] is True

    def test_create_light_with_color_and_position(self, mock_maya):
        mock_maya.pointLight.return_value = "pointLightShape1"
        mock_maya.listRelatives.return_value = ["pointLight1"]

        from dcc_mcp_maya.actions.lighting import create_light
        result = create_light(
            light_type="point",
            color=[1.0, 0.5, 0.0],
            position=[0.0, 10.0, 0.0],
        )

        assert result["success"] is True
        mock_maya.setAttr.assert_called()

    def test_create_light_invalid_type(self, mock_maya):
        from dcc_mcp_maya.actions.lighting import create_light
        result = create_light(light_type="laser")

        assert result["success"] is False
        assert "Unsupported" in result["message"]

    def test_create_light_area(self, mock_maya):
        mock_maya.areaLight.return_value = "areaLightShape1"
        mock_maya.listRelatives.return_value = ["areaLight1"]

        from dcc_mcp_maya.actions.lighting import create_light
        result = create_light(light_type="area")

        assert result["success"] is True

    def test_create_light_ambient(self, mock_maya):
        mock_maya.ambientLight.return_value = "ambientLightShape1"
        mock_maya.listRelatives.return_value = ["ambientLight1"]

        from dcc_mcp_maya.actions.lighting import create_light
        result = create_light(light_type="ambient")

        assert result["success"] is True

    def test_create_light_import_error(self, monkeypatch):
        import sys
        # Remove maya from modules to simulate ImportError
        for k in list(sys.modules.keys()):
            if k.startswith("maya") or k.startswith("dcc_mcp_maya"):
                del sys.modules[k]

        def _err(msg, detail=""):
            m = MagicMock()
            m.to_dict.return_value = {"success": False, "message": msg}
            return m

        monkeypatch.setitem(sys.modules, "dcc_mcp_core", MagicMock(
            success_result=MagicMock(),
            error_result=_err,
        ))

        from dcc_mcp_maya.actions.lighting import create_light
        result = create_light()
        assert result["success"] is False


# ===========================================================================
# TestSetLightAttribute
# ===========================================================================

class TestSetLightAttribute:
    def test_set_intensity(self, mock_maya):
        mock_maya.objExists.return_value = True
        mock_maya.listRelatives.return_value = ["pointLightShape1"]

        from dcc_mcp_maya.actions.lighting import set_light_attribute
        result = set_light_attribute("pointLight1", "intensity", 3.0)

        assert result["success"] is True
        mock_maya.setAttr.assert_called()

    def test_set_color_as_vector(self, mock_maya):
        mock_maya.objExists.return_value = True
        mock_maya.listRelatives.return_value = ["pointLightShape1"]

        from dcc_mcp_maya.actions.lighting import set_light_attribute
        result = set_light_attribute("pointLight1", "color", [1.0, 0.0, 0.0])

        assert result["success"] is True

    def test_light_not_found(self, mock_maya):
        mock_maya.objExists.return_value = False

        from dcc_mcp_maya.actions.lighting import set_light_attribute
        result = set_light_attribute("nonExistentLight", "intensity", 1.0)

        assert result["success"] is False
        assert "not found" in result["message"]

    def test_attribute_not_found(self, mock_maya):
        mock_maya.objExists.side_effect = [True, False, False]
        mock_maya.listRelatives.return_value = ["pointLightShape1"]

        from dcc_mcp_maya.actions.lighting import set_light_attribute
        result = set_light_attribute("pointLight1", "bogusAttr", 1.0)

        assert result["success"] is False

    def test_set_string_attribute(self, mock_maya):
        mock_maya.objExists.return_value = True
        mock_maya.listRelatives.return_value = ["spotLightShape1"]

        from dcc_mcp_maya.actions.lighting import set_light_attribute
        result = set_light_attribute("spotLight1", "notes", "key light")

        assert result["success"] is True

    def test_set_attribute_exception(self, mock_maya):
        mock_maya.objExists.return_value = True
        mock_maya.listRelatives.return_value = ["pointLightShape1"]
        mock_maya.setAttr.side_effect = RuntimeError("locked")

        from dcc_mcp_maya.actions.lighting import set_light_attribute
        result = set_light_attribute("pointLight1", "intensity", 5.0)

        assert result["success"] is False


# ===========================================================================
# TestListLights
# ===========================================================================

class TestListLights:
    def test_list_lights_empty(self, mock_maya):
        mock_maya.ls.return_value = []

        from dcc_mcp_maya.actions.lighting import list_lights
        result = list_lights()

        assert result["success"] is True
        assert result["context"]["count"] == 0

    def test_list_lights_with_shapes(self, mock_maya):
        mock_maya.ls.side_effect = lambda **kw: (
            ["pointLightShape1"] if kw.get("type") == "light" else []
        )
        mock_maya.listRelatives.return_value = ["pointLight1"]
        mock_maya.getAttr.return_value = [(1.0, 1.0, 1.0)]
        mock_maya.objectType.return_value = "pointLight"

        from dcc_mcp_maya.actions.lighting import list_lights
        result = list_lights()

        assert result["success"] is True

    def test_list_lights_skips_defaultLight(self, mock_maya):
        mock_maya.ls.return_value = ["defaultLight"]
        mock_maya.listRelatives.return_value = ["defaultLight"]
        mock_maya.objectType.return_value = "pointLight"

        from dcc_mcp_maya.actions.lighting import list_lights
        result = list_lights(include_default=False)

        assert result["success"] is True
        assert result["context"]["count"] == 0

    def test_list_lights_include_default(self, mock_maya):
        mock_maya.ls.return_value = ["defaultLight"]
        mock_maya.listRelatives.return_value = ["defaultLight"]
        mock_maya.objectType.return_value = "pointLight"
        mock_maya.getAttr.return_value = 1.0

        from dcc_mcp_maya.actions.lighting import list_lights
        result = list_lights(include_default=True)

        assert result["success"] is True


# ===========================================================================
# TestDeleteLight
# ===========================================================================

class TestDeleteLight:
    def test_delete_existing_light(self, mock_maya):
        mock_maya.objExists.return_value = True
        mock_maya.objectType.return_value = "transform"

        from dcc_mcp_maya.actions.lighting import delete_light
        result = delete_light("pointLight1")

        assert result["success"] is True
        mock_maya.delete.assert_called_once_with("pointLight1")

    def test_delete_by_shape_resolves_transform(self, mock_maya):
        mock_maya.objExists.return_value = True
        mock_maya.objectType.return_value = "pointLight"
        mock_maya.listRelatives.return_value = ["pointLight1"]

        from dcc_mcp_maya.actions.lighting import delete_light
        result = delete_light("pointLightShape1")

        assert result["success"] is True

    def test_delete_not_found(self, mock_maya):
        mock_maya.objExists.return_value = False

        from dcc_mcp_maya.actions.lighting import delete_light
        result = delete_light("ghost")

        assert result["success"] is False
        assert "not found" in result["message"]

    def test_delete_exception(self, mock_maya):
        mock_maya.objExists.return_value = True
        mock_maya.objectType.return_value = "transform"
        mock_maya.delete.side_effect = RuntimeError("cannot delete")

        from dcc_mcp_maya.actions.lighting import delete_light
        result = delete_light("pointLight1")

        assert result["success"] is False


# ===========================================================================
# TestCreateCamera
# ===========================================================================

class TestCreateCamera:
    def test_create_default_camera(self, mock_maya):
        mock_maya.camera.return_value = ("camera1", "cameraShape1")
        mock_maya.listRelatives.return_value = ["cameraShape1"]

        from dcc_mcp_maya.actions.cameras import create_camera
        result = create_camera()

        assert result["success"] is True
        mock_maya.camera.assert_called_once()

    def test_create_camera_with_name(self, mock_maya):
        mock_maya.camera.return_value = ("camera1", "cameraShape1")
        mock_maya.rename.return_value = "shotCam"
        mock_maya.listRelatives.return_value = ["shotCamShape"]

        from dcc_mcp_maya.actions.cameras import create_camera
        result = create_camera(name="shotCam", focal_length=50.0)

        assert result["success"] is True
        mock_maya.rename.assert_called_once()

    def test_create_camera_with_position_and_rotation(self, mock_maya):
        mock_maya.camera.return_value = ("camera1", "cameraShape1")
        mock_maya.listRelatives.return_value = []

        from dcc_mcp_maya.actions.cameras import create_camera
        result = create_camera(position=[0.0, 5.0, 10.0], rotation=[-30.0, 0.0, 0.0])

        assert result["success"] is True
        mock_maya.setAttr.assert_called()

    def test_create_camera_exception(self, mock_maya):
        mock_maya.camera.side_effect = RuntimeError("failed")

        from dcc_mcp_maya.actions.cameras import create_camera
        result = create_camera()

        assert result["success"] is False

    def test_create_camera_import_error(self, monkeypatch):
        for k in list(sys.modules.keys()):
            if k.startswith("maya") or k.startswith("dcc_mcp_maya"):
                del sys.modules[k]

        def _err(msg, detail=""):
            m = MagicMock()
            m.to_dict.return_value = {"success": False, "message": msg}
            return m

        monkeypatch.setitem(sys.modules, "dcc_mcp_core", MagicMock(
            success_result=MagicMock(),
            error_result=_err,
        ))

        from dcc_mcp_maya.actions.cameras import create_camera
        result = create_camera()
        assert result["success"] is False


# ===========================================================================
# TestSetCameraAttribute
# ===========================================================================

class TestSetCameraAttribute:
    def test_set_focal_length(self, mock_maya):
        mock_maya.objExists.return_value = True
        mock_maya.listRelatives.return_value = ["cameraShape1"]

        from dcc_mcp_maya.actions.cameras import set_camera_attribute
        result = set_camera_attribute("camera1", "focalLength", 85.0)

        assert result["success"] is True

    def test_set_attribute_string(self, mock_maya):
        mock_maya.objExists.return_value = True
        mock_maya.listRelatives.return_value = ["cameraShape1"]

        from dcc_mcp_maya.actions.cameras import set_camera_attribute
        result = set_camera_attribute("camera1", "notes", "main cam")

        assert result["success"] is True

    def test_camera_not_found(self, mock_maya):
        mock_maya.objExists.return_value = False

        from dcc_mcp_maya.actions.cameras import set_camera_attribute
        result = set_camera_attribute("ghost", "focalLength", 35.0)

        assert result["success"] is False

    def test_attribute_not_found_on_camera(self, mock_maya):
        mock_maya.objExists.side_effect = [True, False, False]
        mock_maya.listRelatives.return_value = ["cameraShape1"]

        from dcc_mcp_maya.actions.cameras import set_camera_attribute
        result = set_camera_attribute("camera1", "bogus", 1.0)

        assert result["success"] is False

    def test_set_attribute_exception(self, mock_maya):
        mock_maya.objExists.return_value = True
        mock_maya.listRelatives.return_value = ["cameraShape1"]
        mock_maya.setAttr.side_effect = RuntimeError("read only")

        from dcc_mcp_maya.actions.cameras import set_camera_attribute
        result = set_camera_attribute("camera1", "focalLength", 35.0)

        assert result["success"] is False


# ===========================================================================
# TestGetCameraInfo
# ===========================================================================

class TestGetCameraInfo:
    def test_get_camera_info_basic(self, mock_maya):
        mock_maya.objExists.return_value = True
        mock_maya.listRelatives.return_value = ["cameraShape1"]
        mock_maya.getAttr.return_value = 35.0

        from dcc_mcp_maya.actions.cameras import get_camera_info
        result = get_camera_info("camera1")

        assert result["success"] is True

    def test_camera_not_found(self, mock_maya):
        mock_maya.objExists.return_value = False

        from dcc_mcp_maya.actions.cameras import get_camera_info
        result = get_camera_info("ghost")

        assert result["success"] is False

    def test_not_a_camera(self, mock_maya):
        mock_maya.objExists.return_value = True
        mock_maya.listRelatives.return_value = []
        mock_maya.objectType.return_value = "mesh"

        from dcc_mcp_maya.actions.cameras import get_camera_info
        result = get_camera_info("pSphere1")

        assert result["success"] is False

    def test_camera_as_shape_input(self, mock_maya):
        mock_maya.objExists.return_value = True
        mock_maya.listRelatives.return_value = ["camera1"]
        mock_maya.objectType.return_value = "camera"
        mock_maya.getAttr.return_value = 50.0

        from dcc_mcp_maya.actions.cameras import get_camera_info
        result = get_camera_info("cameraShape1")

        assert result["success"] is True

    def test_getAttr_error_returns_none(self, mock_maya):
        mock_maya.objExists.return_value = True
        mock_maya.listRelatives.return_value = ["cameraShape1"]
        mock_maya.getAttr.side_effect = RuntimeError("bad attr")

        from dcc_mcp_maya.actions.cameras import get_camera_info
        result = get_camera_info("camera1")

        # Even if attrs fail, success is True (graceful)
        assert result["success"] is True


# ===========================================================================
# TestListAllCameras
# ===========================================================================

class TestListAllCameras:
    def test_list_cameras_empty(self, mock_maya):
        mock_maya.ls.return_value = []

        from dcc_mcp_maya.actions.cameras import list_all_cameras
        result = list_all_cameras()

        assert result["success"] is True
        assert result["context"]["count"] == 0

    def test_list_cameras_filters_defaults(self, mock_maya):
        mock_maya.ls.return_value = ["perspShape", "topShape"]
        mock_maya.listRelatives.side_effect = [["persp"], ["top"]]

        from dcc_mcp_maya.actions.cameras import list_all_cameras
        result = list_all_cameras(include_default=False)

        assert result["success"] is True
        assert result["context"]["count"] == 0

    def test_list_cameras_includes_defaults(self, mock_maya):
        mock_maya.ls.return_value = ["perspShape"]
        mock_maya.listRelatives.return_value = ["persp"]
        mock_maya.getAttr.return_value = 35.0

        from dcc_mcp_maya.actions.cameras import list_all_cameras
        result = list_all_cameras(include_default=True)

        assert result["success"] is True
        assert result["context"]["count"] == 1

    def test_list_cameras_exception(self, mock_maya):
        mock_maya.ls.side_effect = RuntimeError("crash")

        from dcc_mcp_maya.actions.cameras import list_all_cameras
        result = list_all_cameras()

        assert result["success"] is False


# ===========================================================================
# TestGetPolyCount
# ===========================================================================

class TestGetPolyCount:
    def test_get_poly_count_specific_object(self, mock_maya):
        mock_maya.objExists.return_value = True
        mock_maya.polyEvaluate.side_effect = lambda obj, **kw: (
            100 if kw.get("face") else
            80 if kw.get("vertex") else
            200 if kw.get("edge") else
            200 if kw.get("triangle") else 0
        )

        from dcc_mcp_maya.actions.mesh_ops import get_poly_count
        result = get_poly_count("pSphere1")

        assert result["success"] is True
        assert result["context"]["faces"] == 100

    def test_get_poly_count_scene_wide(self, mock_maya):
        mock_maya.ls.return_value = ["pSphereShape1", "pCubeShape1"]
        mock_maya.polyEvaluate.return_value = 50

        from dcc_mcp_maya.actions.mesh_ops import get_poly_count
        result = get_poly_count()

        assert result["success"] is True
        assert result["context"]["faces"] >= 0

    def test_object_not_found(self, mock_maya):
        mock_maya.objExists.return_value = False

        from dcc_mcp_maya.actions.mesh_ops import get_poly_count
        result = get_poly_count("ghost")

        assert result["success"] is False

    def test_polyEvaluate_returns_non_int(self, mock_maya):
        mock_maya.objExists.return_value = True
        mock_maya.polyEvaluate.return_value = "N/A"

        from dcc_mcp_maya.actions.mesh_ops import get_poly_count
        result = get_poly_count("pSphere1")

        assert result["success"] is True
        assert result["context"]["faces"] == 0

    def test_exception_handling(self, mock_maya):
        mock_maya.objExists.return_value = True
        mock_maya.polyEvaluate.side_effect = RuntimeError("crash")

        from dcc_mcp_maya.actions.mesh_ops import get_poly_count
        result = get_poly_count("pSphere1")

        # polyEvaluate exception is caught per-object, not overall
        assert result["success"] is True
        assert result["context"]["faces"] == 0


# ===========================================================================
# TestApplySubdivision
# ===========================================================================

class TestApplySubdivision:
    def test_preview_subdivision(self, mock_maya):
        mock_maya.objExists.return_value = True
        mock_maya.listRelatives.return_value = ["pSphereShape1"]
        mock_maya.objectType.return_value = "mesh"

        from dcc_mcp_maya.actions.mesh_ops import apply_subdivision
        result = apply_subdivision("pSphere1", level=2, method="preview")

        assert result["success"] is True
        mock_maya.setAttr.assert_called()

    def test_destructive_subdivision(self, mock_maya):
        mock_maya.objExists.return_value = True
        mock_maya.listRelatives.return_value = ["pCubeShape1"]

        from dcc_mcp_maya.actions.mesh_ops import apply_subdivision
        result = apply_subdivision("pCube1", level=1, method="subdivide")

        assert result["success"] is True
        mock_maya.polySubdivideFacet.assert_called_once()

    def test_invalid_method(self, mock_maya):
        from dcc_mcp_maya.actions.mesh_ops import apply_subdivision
        result = apply_subdivision("pSphere1", method="nurbs")

        assert result["success"] is False

    def test_object_not_found(self, mock_maya):
        mock_maya.objExists.return_value = False

        from dcc_mcp_maya.actions.mesh_ops import apply_subdivision
        result = apply_subdivision("ghost")

        assert result["success"] is False

    def test_no_mesh_shape(self, mock_maya):
        mock_maya.objExists.return_value = True
        mock_maya.listRelatives.return_value = []
        mock_maya.objectType.return_value = "joint"

        from dcc_mcp_maya.actions.mesh_ops import apply_subdivision
        result = apply_subdivision("joint1")

        assert result["success"] is False

    def test_shape_is_mesh_itself(self, mock_maya):
        mock_maya.objExists.return_value = True
        mock_maya.listRelatives.return_value = []
        mock_maya.objectType.return_value = "mesh"

        from dcc_mcp_maya.actions.mesh_ops import apply_subdivision
        result = apply_subdivision("pSphereShape1", method="preview")

        assert result["success"] is True


# ===========================================================================
# TestMergeVertices
# ===========================================================================

class TestMergeVertices:
    def test_merge_vertices_basic(self, mock_maya):
        mock_maya.objExists.return_value = True
        mock_maya.polyEvaluate.side_effect = [100, 95]

        from dcc_mcp_maya.actions.mesh_ops import merge_vertices
        result = merge_vertices("pSphere1", threshold=0.001)

        assert result["success"] is True
        assert result["context"]["merged_count"] == 5
        mock_maya.polyMergeVertex.assert_called_once()

    def test_merge_vertices_none_merged(self, mock_maya):
        mock_maya.objExists.return_value = True
        mock_maya.polyEvaluate.side_effect = [50, 50]

        from dcc_mcp_maya.actions.mesh_ops import merge_vertices
        result = merge_vertices("pSphere1")

        assert result["success"] is True
        assert result["context"]["merged_count"] == 0

    def test_object_not_found(self, mock_maya):
        mock_maya.objExists.return_value = False

        from dcc_mcp_maya.actions.mesh_ops import merge_vertices
        result = merge_vertices("ghost")

        assert result["success"] is False

    def test_polyEvaluate_returns_non_int(self, mock_maya):
        mock_maya.objExists.return_value = True
        mock_maya.polyEvaluate.return_value = "N/A"

        from dcc_mcp_maya.actions.mesh_ops import merge_vertices
        result = merge_vertices("pSphere1")

        assert result["success"] is True
        assert result["context"]["merged_count"] == 0

    def test_exception_handling(self, mock_maya):
        mock_maya.objExists.return_value = True
        mock_maya.polyEvaluate.side_effect = RuntimeError("fail")

        from dcc_mcp_maya.actions.mesh_ops import merge_vertices
        result = merge_vertices("pSphere1")

        assert result["success"] is False


# ===========================================================================
# TestTriangulate
# ===========================================================================

class TestTriangulate:
    def test_triangulate_basic(self, mock_maya):
        mock_maya.objExists.return_value = True
        mock_maya.polyEvaluate.side_effect = [100, 200]

        from dcc_mcp_maya.actions.mesh_ops import triangulate
        result = triangulate("pCube1")

        assert result["success"] is True
        assert result["context"]["face_count_before"] == 100
        assert result["context"]["face_count_after"] == 200
        mock_maya.polyTriangulate.assert_called_once()

    def test_object_not_found(self, mock_maya):
        mock_maya.objExists.return_value = False

        from dcc_mcp_maya.actions.mesh_ops import triangulate
        result = triangulate("ghost")

        assert result["success"] is False

    def test_exception_propagates(self, mock_maya):
        mock_maya.objExists.return_value = True
        mock_maya.polyEvaluate.side_effect = RuntimeError("fail")

        from dcc_mcp_maya.actions.mesh_ops import triangulate
        result = triangulate("pSphere1")

        assert result["success"] is False

    def test_non_int_polyEvaluate(self, mock_maya):
        mock_maya.objExists.return_value = True
        mock_maya.polyEvaluate.return_value = "N/A"

        from dcc_mcp_maya.actions.mesh_ops import triangulate
        result = triangulate("pSphere1")

        assert result["success"] is True
        assert result["context"]["face_count_before"] == 0


# ===========================================================================
# TestCleanupMesh
# ===========================================================================

class TestCleanupMesh:
    def test_cleanup_defaults(self, mock_maya):
        mock_maya.objExists.return_value = True

        from dcc_mcp_maya.actions.mesh_ops import cleanup_mesh
        result = cleanup_mesh("pSphere1")

        assert result["success"] is True
        mock_maya.polyClean.assert_called_once()

    def test_cleanup_selective_flags(self, mock_maya):
        mock_maya.objExists.return_value = True

        from dcc_mcp_maya.actions.mesh_ops import cleanup_mesh
        result = cleanup_mesh("pSphere1", non_manifold=True, lamina_faces=False, invalid_components=True)

        assert result["success"] is True

    def test_object_not_found(self, mock_maya):
        mock_maya.objExists.return_value = False

        from dcc_mcp_maya.actions.mesh_ops import cleanup_mesh
        result = cleanup_mesh("ghost")

        assert result["success"] is False

    def test_exception_handling(self, mock_maya):
        mock_maya.objExists.return_value = True
        mock_maya.polyClean.side_effect = RuntimeError("fail")

        from dcc_mcp_maya.actions.mesh_ops import cleanup_mesh
        result = cleanup_mesh("pSphere1")

        assert result["success"] is False


# ===========================================================================
# TestRegisterAllRound12
# ===========================================================================

class TestRegisterAllRound12:
    def test_register_all_contains_new_actions(self):
        import importlib
        for k in list(sys.modules.keys()):
            if k.startswith("dcc_mcp_maya"):
                del sys.modules[k]

        mock_registry = MagicMock()
        mock_core = MagicMock()
        sys.modules["dcc_mcp_core"] = mock_core

        from dcc_mcp_maya.actions import register_all
        register_all(mock_registry)

        registered_names = [call.args[0] for call in mock_registry.register.call_args_list]
        for action in (
            "create_light", "set_light_attribute", "list_lights", "delete_light",
            "create_camera", "set_camera_attribute", "get_camera_info", "list_all_cameras",
            "get_poly_count", "apply_subdivision", "merge_vertices", "triangulate", "cleanup_mesh",
        ):
            assert action in registered_names, "Missing: {}".format(action)

    def test_total_action_count_round12(self):
        for k in list(sys.modules.keys()):
            if k.startswith("dcc_mcp_maya"):
                del sys.modules[k]

        mock_registry = MagicMock()
        sys.modules["dcc_mcp_core"] = MagicMock()

        from dcc_mcp_maya.actions import register_all
        register_all(mock_registry)

        assert mock_registry.register.call_count >= 119


# ===========================================================================
# TestCreateLightEdgeCases (coverage gaps: line 63, 90-92)
# ===========================================================================

class TestCreateLightEdgeCases:
    def test_shape_returned_as_list(self, mock_maya):
        """Cover line 63: shape returned as list [shape, transform]."""
        mock_maya.pointLight.return_value = ["pointLightShape1", "pointLight1"]
        mock_maya.listRelatives.return_value = ["pointLight1"]

        from dcc_mcp_maya.actions.lighting import create_light
        result = create_light(light_type="point")

        assert result["success"] is True

    def test_listRelatives_returns_empty_uses_shape_as_transform(self, mock_maya):
        """Cover line 90-92: listRelatives returns None → transform = shape."""
        mock_maya.pointLight.return_value = "pointLightShape1"
        mock_maya.listRelatives.return_value = None

        from dcc_mcp_maya.actions.lighting import create_light
        result = create_light(light_type="point")

        assert result["success"] is True

    def test_create_light_exception_in_setAttr(self, mock_maya):
        """Cover exception path in create_light."""
        mock_maya.pointLight.return_value = "pointLightShape1"
        mock_maya.listRelatives.return_value = ["pointLight1"]
        mock_maya.setAttr.side_effect = RuntimeError("locked")

        from dcc_mcp_maya.actions.lighting import create_light
        result = create_light(light_type="point")

        assert result["success"] is False


# ===========================================================================
# TestListLightsEdgeCases (coverage gaps: getAttr exception paths 191-192, 200-201)
# ===========================================================================

class TestListLightsEdgeCases:
    def test_getAttr_intensity_exception(self, mock_maya):
        """Cover lines 191-192: intensity getAttr raises."""
        mock_maya.ls.side_effect = lambda **kw: (
            ["pointLightShape1"] if kw.get("type") == "light" else []
        )
        mock_maya.listRelatives.return_value = ["pointLight1"]
        mock_maya.objectType.return_value = "pointLight"

        def _getattr_side(attr):
            if "intensity" in attr:
                raise RuntimeError("no intensity")
            if "color" in attr:
                return [(1.0, 1.0, 1.0)]
            return True

        mock_maya.getAttr.side_effect = _getattr_side

        from dcc_mcp_maya.actions.lighting import list_lights
        result = list_lights()

        assert result["success"] is True
        assert result["context"]["lights"][0]["intensity"] is None

    def test_getAttr_visibility_exception(self, mock_maya):
        """Cover lines 200-201: visibility getAttr raises."""
        mock_maya.ls.side_effect = lambda **kw: (
            ["pointLightShape1"] if kw.get("type") == "light" else []
        )
        mock_maya.listRelatives.return_value = ["pointLight1"]
        mock_maya.objectType.return_value = "pointLight"

        call_count = [0]

        def _getattr_side(attr):
            call_count[0] += 1
            if "visibility" in attr:
                raise RuntimeError("no vis")
            if "color" in attr:
                return [(1.0, 1.0, 1.0)]
            return 1.0

        mock_maya.getAttr.side_effect = _getattr_side

        from dcc_mcp_maya.actions.lighting import list_lights
        result = list_lights()

        assert result["success"] is True
        assert result["context"]["lights"][0]["visible"] is True

    def test_list_lights_exception(self, mock_maya):
        """Cover exception path in list_lights."""
        mock_maya.ls.side_effect = RuntimeError("crash")

        from dcc_mcp_maya.actions.lighting import list_lights
        result = list_lights()

        assert result["success"] is False


# ===========================================================================
# TestSetCameraAttributeEdgeCases (coverage gaps: line 115 vector path)
# ===========================================================================

class TestSetCameraAttributeEdgeCases:
    def test_set_camera_attribute_vector(self, mock_maya):
        """Cover line 114-115: value is 3-tuple."""
        mock_maya.objExists.return_value = True
        mock_maya.listRelatives.return_value = ["cameraShape1"]

        from dcc_mcp_maya.actions.cameras import set_camera_attribute
        result = set_camera_attribute("camera1", "someVec", [1.0, 2.0, 3.0])

        assert result["success"] is True
        # setAttr should have been called with double3 type
        call_args = mock_maya.setAttr.call_args
        assert "double3" in str(call_args)

    def test_list_all_cameras_getAttr_exception(self, mock_maya):
        """Cover lines 219-221: getAttr raises inside list_all_cameras."""
        mock_maya.ls.return_value = ["myCustomShape"]
        mock_maya.listRelatives.return_value = ["myCustomCam"]
        mock_maya.getAttr.side_effect = RuntimeError("locked")

        from dcc_mcp_maya.actions.cameras import list_all_cameras
        result = list_all_cameras(include_default=True)

        assert result["success"] is True
        # focalLength should be None since getAttr failed
        cam = result["context"]["cameras"][0]
        assert cam["focalLength"] is None

    def test_list_all_cameras_listRelatives_empty(self, mock_maya):
        """Cover line 212: listRelatives returns empty → use shape as transform."""
        mock_maya.ls.return_value = ["cameraShape1"]
        mock_maya.listRelatives.return_value = None
        mock_maya.getAttr.return_value = 35.0

        from dcc_mcp_maya.actions.cameras import list_all_cameras
        result = list_all_cameras(include_default=True)

        assert result["success"] is True
        # transform should fall back to shape name
        assert result["context"]["cameras"][0]["name"] == "cameraShape1"


# ===========================================================================
# TestMeshOpsEdgeCases (coverage gaps: mesh_ops lines 76-80, 137-141)
# ===========================================================================

class TestMeshOpsEdgeCases:
    def test_get_poly_count_scene_no_meshes(self, mock_maya):
        """Cover scene-wide path when ls returns empty list."""
        mock_maya.ls.return_value = []

        from dcc_mcp_maya.actions.mesh_ops import get_poly_count
        result = get_poly_count()

        assert result["success"] is True
        assert result["context"]["faces"] == 0

    def test_get_poly_count_polyEvaluate_per_object_exception(self, mock_maya):
        """Cover lines 76-80: per-object polyEvaluate exception."""
        mock_maya.ls.return_value = ["pSphereShape1"]
        mock_maya.polyEvaluate.side_effect = RuntimeError("fail")

        from dcc_mcp_maya.actions.mesh_ops import get_poly_count
        result = get_poly_count()

        assert result["success"] is True
        assert result["context"]["faces"] == 0

    def test_apply_subdivision_preview_on_shape_with_no_relatives(self, mock_maya):
        """Cover lines 137-141: shape found via objectType fallback."""
        mock_maya.objExists.return_value = True
        mock_maya.listRelatives.return_value = []
        mock_maya.objectType.return_value = "mesh"

        from dcc_mcp_maya.actions.mesh_ops import apply_subdivision
        result = apply_subdivision("pSphereShape1", method="preview")

        assert result["success"] is True
