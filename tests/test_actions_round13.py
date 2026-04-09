"""Round 13 tests: UV ops, vertex color, texture bake & color management."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import sys
from types import ModuleType
from unittest.mock import MagicMock, patch

# Import third-party modules
import pytest


# ---------------------------------------------------------------------------
# Shared Maya mock fixture
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def mock_maya(monkeypatch):
    """Inject a minimal mock Maya environment."""
    cmds = MagicMock()

    # polyUVSet / polyColorSet query helpers
    cmds.objExists.return_value = True
    cmds.polyUVSet.return_value = ["map1", "map2"]
    cmds.polyColorSet.return_value = ["colorSet1"]
    cmds.polyEvaluate.return_value = 100
    cmds.polyEditUV.return_value = [0.0, 0.5, 1.0]
    cmds.polyColorPerVertex.return_value = None
    cmds.transferAttributes.return_value = None
    cmds.polyProjection.return_value = None
    cmds.select.return_value = None
    cmds.convertSolidTx.return_value = None
    cmds.colorManagementPrefs.return_value = True

    maya_mod = ModuleType("maya")
    maya_cmds_mod = ModuleType("maya.cmds")

    for attr in dir(cmds):
        if not attr.startswith("_"):
            setattr(maya_cmds_mod, attr, getattr(cmds, attr))

    monkeypatch.setitem(sys.modules, "maya", maya_mod)
    monkeypatch.setitem(sys.modules, "maya.cmds", cmds)
    monkeypatch.setitem(sys.modules, "maya.api", MagicMock())
    monkeypatch.setitem(sys.modules, "maya.utils", MagicMock())

    yield cmds


# ---------------------------------------------------------------------------
# Mock dcc_mcp_core helpers
# ---------------------------------------------------------------------------

class _Result:
    def __init__(self, success, message, **ctx):
        self._d = {"success": success, "message": message, "context": ctx}

    def to_dict(self):
        return self._d


def _success(msg, **kw):
    return _Result(True, msg, **kw)


def _error(msg, detail=""):
    return _Result(False, msg)


@pytest.fixture(autouse=True)
def mock_core(monkeypatch):
    core = MagicMock()
    core.success_result.side_effect = _success
    core.error_result.side_effect = _error
    monkeypatch.setitem(sys.modules, "dcc_mcp_core", core)
    yield core


# ===========================================================================
# UV Ops
# ===========================================================================

class TestGetUvInfo:
    def test_basic(self, mock_maya):
        mock_maya.polyUVSet.return_value = ["map1", "map2"]
        from dcc_mcp_maya.actions.uv_ops import get_uv_info
        r = get_uv_info("pSphere1")
        assert r["success"] is True
        assert r["context"]["uv_set_count"] == 2

    def test_object_not_found(self, mock_maya):
        mock_maya.objExists.return_value = False
        from dcc_mcp_maya.actions.uv_ops import get_uv_info
        r = get_uv_info("missing")
        assert r["success"] is False

    def test_with_uv_set(self, mock_maya):
        mock_maya.polyUVSet.return_value = ["map1"]
        mock_maya.polyEditUV.return_value = [0.1, 0.5]
        from dcc_mcp_maya.actions.uv_ops import get_uv_info
        r = get_uv_info("pSphere1", uv_set="map1")
        assert r["success"] is True
        assert "uv_count" in r["context"]

    def test_uv_set_not_found(self, mock_maya):
        mock_maya.polyUVSet.return_value = ["map1"]
        from dcc_mcp_maya.actions.uv_ops import get_uv_info
        r = get_uv_info("pSphere1", uv_set="nonexistent")
        assert r["success"] is False

    def test_import_error(self, monkeypatch):
        monkeypatch.setitem(sys.modules, "maya.cmds", None)
        import importlib
        import dcc_mcp_maya.actions.uv_ops as mod
        importlib.reload(mod)
        with patch.dict(sys.modules, {"maya.cmds": None}):
            from dcc_mcp_maya.actions.uv_ops import get_uv_info
            r = get_uv_info("obj")
            # Either succeeds with mock or fails with ImportError — just no crash
            assert "success" in r

    def test_exception_handling(self, mock_maya):
        mock_maya.polyUVSet.side_effect = RuntimeError("cmds error")
        from dcc_mcp_maya.actions.uv_ops import get_uv_info
        r = get_uv_info("pSphere1")
        assert r["success"] is False


class TestCreateUvSet:
    def test_create_new(self, mock_maya):
        mock_maya.polyUVSet.return_value = ["map1"]
        from dcc_mcp_maya.actions.uv_ops import create_uv_set
        r = create_uv_set("pSphere1", "map2")
        assert r["success"] is True
        assert r["context"]["uv_set_name"] == "map2"

    def test_duplicate_name(self, mock_maya):
        mock_maya.polyUVSet.return_value = ["map1"]
        from dcc_mcp_maya.actions.uv_ops import create_uv_set
        r = create_uv_set("pSphere1", "map1")
        assert r["success"] is False

    def test_copy_from(self, mock_maya):
        mock_maya.polyUVSet.return_value = ["map1"]
        from dcc_mcp_maya.actions.uv_ops import create_uv_set
        r = create_uv_set("pSphere1", "map2", copy_from="map1")
        assert r["success"] is True
        assert r["context"]["copied_from"] == "map1"

    def test_copy_source_missing(self, mock_maya):
        mock_maya.polyUVSet.return_value = ["map1"]
        from dcc_mcp_maya.actions.uv_ops import create_uv_set
        r = create_uv_set("pSphere1", "map2", copy_from="mapX")
        assert r["success"] is False

    def test_object_not_found(self, mock_maya):
        mock_maya.objExists.return_value = False
        from dcc_mcp_maya.actions.uv_ops import create_uv_set
        r = create_uv_set("missing", "map2")
        assert r["success"] is False


class TestDeleteUvSet:
    def test_delete(self, mock_maya):
        mock_maya.polyUVSet.return_value = ["map1", "map2"]
        from dcc_mcp_maya.actions.uv_ops import delete_uv_set
        r = delete_uv_set("pSphere1", "map2")
        assert r["success"] is True

    def test_only_set_protected(self, mock_maya):
        mock_maya.polyUVSet.return_value = ["map1"]
        from dcc_mcp_maya.actions.uv_ops import delete_uv_set
        r = delete_uv_set("pSphere1", "map1")
        assert r["success"] is False

    def test_not_found(self, mock_maya):
        mock_maya.polyUVSet.return_value = ["map1", "map2"]
        from dcc_mcp_maya.actions.uv_ops import delete_uv_set
        r = delete_uv_set("pSphere1", "mapX")
        assert r["success"] is False

    def test_object_missing(self, mock_maya):
        mock_maya.objExists.return_value = False
        from dcc_mcp_maya.actions.uv_ops import delete_uv_set
        r = delete_uv_set("missing", "map1")
        assert r["success"] is False


class TestProjectUvs:
    def test_planar(self, mock_maya):
        from dcc_mcp_maya.actions.uv_ops import project_uvs
        r = project_uvs("pSphere1", "planar", "y")
        assert r["success"] is True
        assert r["context"]["projection_type"] == "planar"

    def test_cylindrical(self, mock_maya):
        from dcc_mcp_maya.actions.uv_ops import project_uvs
        r = project_uvs("pSphere1", "cylindrical", "z")
        assert r["success"] is True

    def test_spherical(self, mock_maya):
        from dcc_mcp_maya.actions.uv_ops import project_uvs
        r = project_uvs("pSphere1", "spherical", "y")
        assert r["success"] is True

    def test_invalid_type(self, mock_maya):
        from dcc_mcp_maya.actions.uv_ops import project_uvs
        r = project_uvs("pSphere1", "cubic", "y")
        assert r["success"] is False

    def test_invalid_axis(self, mock_maya):
        from dcc_mcp_maya.actions.uv_ops import project_uvs
        r = project_uvs("pSphere1", "planar", "w")
        assert r["success"] is False

    def test_object_not_found(self, mock_maya):
        mock_maya.objExists.return_value = False
        from dcc_mcp_maya.actions.uv_ops import project_uvs
        r = project_uvs("missing", "planar")
        assert r["success"] is False


class TestCopyUvs:
    def test_basic(self, mock_maya):
        from dcc_mcp_maya.actions.uv_ops import copy_uvs
        r = copy_uvs("pSphere1", "pCube1")
        assert r["success"] is True

    def test_with_sets(self, mock_maya):
        from dcc_mcp_maya.actions.uv_ops import copy_uvs
        r = copy_uvs("pSphere1", "pCube1", source_uv_set="map1", target_uv_set="map2")
        assert r["success"] is True
        assert r["context"]["source_uv_set"] == "map1"

    def test_source_missing(self, mock_maya):
        mock_maya.objExists.side_effect = lambda n: n != "missing_src"
        from dcc_mcp_maya.actions.uv_ops import copy_uvs
        r = copy_uvs("missing_src", "pCube1")
        assert r["success"] is False

    def test_target_missing(self, mock_maya):
        mock_maya.objExists.side_effect = lambda n: n != "missing_tgt"
        from dcc_mcp_maya.actions.uv_ops import copy_uvs
        r = copy_uvs("pSphere1", "missing_tgt")
        assert r["success"] is False


# ===========================================================================
# Vertex Color
# ===========================================================================

class TestSetVertexColor:
    def test_all_vertices(self, mock_maya):
        mock_maya.polyEvaluate.return_value = 50
        from dcc_mcp_maya.actions.vertex_color import set_vertex_color
        r = set_vertex_color("pSphere1", (1.0, 0.0, 0.0))
        assert r["success"] is True
        assert r["context"]["colored_count"] == 50

    def test_specific_vertices(self, mock_maya):
        from dcc_mcp_maya.actions.vertex_color import set_vertex_color
        r = set_vertex_color("pSphere1", (0.0, 1.0, 0.0), vertices=[0, 1, 2])
        assert r["success"] is True
        assert r["context"]["colored_count"] == 3

    def test_with_color_set(self, mock_maya):
        from dcc_mcp_maya.actions.vertex_color import set_vertex_color
        r = set_vertex_color("pSphere1", (0.5, 0.5, 0.5), color_set="mySet")
        assert r["success"] is True

    def test_object_not_found(self, mock_maya):
        mock_maya.objExists.return_value = False
        from dcc_mcp_maya.actions.vertex_color import set_vertex_color
        r = set_vertex_color("missing", (1.0, 1.0, 1.0))
        assert r["success"] is False

    def test_exception(self, mock_maya):
        mock_maya.polyColorPerVertex.side_effect = RuntimeError("cmds fail")
        from dcc_mcp_maya.actions.vertex_color import set_vertex_color
        r = set_vertex_color("pSphere1", (1.0, 0.0, 0.0))
        assert r["success"] is False


class TestGetVertexColor:
    def test_summary(self, mock_maya):
        mock_maya.polyColorSet.return_value = ["colorSet1", "colorSet2"]
        from dcc_mcp_maya.actions.vertex_color import get_vertex_color
        r = get_vertex_color("pSphere1")
        assert r["success"] is True
        assert "color_sets" in r["context"]

    def test_specific_vertex(self, mock_maya):
        mock_maya.polyColorPerVertex.return_value = [0.5, 0.5, 0.5, 1.0]
        from dcc_mcp_maya.actions.vertex_color import get_vertex_color
        r = get_vertex_color("pSphere1", vertex_index=0)
        assert r["success"] is True
        assert "color" in r["context"]
        assert r["context"]["vertex_index"] == 0

    def test_vertex_not_found(self, mock_maya):
        # objExists returns False only for the component
        mock_maya.objExists.side_effect = lambda n: "vtx" not in n
        from dcc_mcp_maya.actions.vertex_color import get_vertex_color
        r = get_vertex_color("pSphere1", vertex_index=999)
        assert r["success"] is False

    def test_object_not_found(self, mock_maya):
        mock_maya.objExists.return_value = False
        from dcc_mcp_maya.actions.vertex_color import get_vertex_color
        r = get_vertex_color("missing")
        assert r["success"] is False

    def test_rgba_too_short(self, mock_maya):
        # polyColorPerVertex returns None or []
        mock_maya.polyColorPerVertex.return_value = []
        from dcc_mcp_maya.actions.vertex_color import get_vertex_color
        r = get_vertex_color("pSphere1", vertex_index=0)
        assert r["success"] is True
        assert r["context"]["color"] == [1.0, 1.0, 1.0]


class TestCreateColorSet:
    def test_create(self, mock_maya):
        mock_maya.polyColorSet.return_value = []
        from dcc_mcp_maya.actions.vertex_color import create_color_set
        r = create_color_set("pSphere1", "myColors")
        assert r["success"] is True
        assert r["context"]["color_set_name"] == "myColors"

    def test_duplicate(self, mock_maya):
        mock_maya.polyColorSet.return_value = ["myColors"]
        from dcc_mcp_maya.actions.vertex_color import create_color_set
        r = create_color_set("pSphere1", "myColors")
        assert r["success"] is False

    def test_invalid_representation(self, mock_maya):
        from dcc_mcp_maya.actions.vertex_color import create_color_set
        r = create_color_set("pSphere1", "cs", representation="CMYK")
        assert r["success"] is False

    def test_rgb_representation(self, mock_maya):
        mock_maya.polyColorSet.return_value = []
        from dcc_mcp_maya.actions.vertex_color import create_color_set
        r = create_color_set("pSphere1", "rgbSet", representation="RGB")
        assert r["success"] is True

    def test_object_not_found(self, mock_maya):
        mock_maya.objExists.return_value = False
        from dcc_mcp_maya.actions.vertex_color import create_color_set
        r = create_color_set("missing", "cs")
        assert r["success"] is False


class TestRemoveVertexColors:
    def test_remove_specific(self, mock_maya):
        mock_maya.polyColorSet.return_value = ["colorSet1"]
        from dcc_mcp_maya.actions.vertex_color import remove_vertex_colors
        r = remove_vertex_colors("pSphere1", color_set="colorSet1")
        assert r["success"] is True
        assert "colorSet1" in r["context"]["removed_color_sets"]

    def test_remove_all(self, mock_maya):
        mock_maya.polyColorSet.return_value = ["cs1", "cs2"]
        from dcc_mcp_maya.actions.vertex_color import remove_vertex_colors
        r = remove_vertex_colors("pSphere1")
        assert r["success"] is True
        assert len(r["context"]["removed_color_sets"]) == 2

    def test_color_set_not_found(self, mock_maya):
        mock_maya.polyColorSet.return_value = ["cs1"]
        from dcc_mcp_maya.actions.vertex_color import remove_vertex_colors
        r = remove_vertex_colors("pSphere1", color_set="nonexistent")
        assert r["success"] is False

    def test_object_not_found(self, mock_maya):
        mock_maya.objExists.return_value = False
        from dcc_mcp_maya.actions.vertex_color import remove_vertex_colors
        r = remove_vertex_colors("missing")
        assert r["success"] is False


# ===========================================================================
# Texture Bake
# ===========================================================================

class TestBakeTextures:
    def test_basic(self, mock_maya):
        from dcc_mcp_maya.actions.texture_bake import bake_textures
        r = bake_textures(["pSphere1"], "/tmp/bake")
        assert r["success"] is True
        assert r["context"]["bake_type"] == "diffuse"

    def test_full_render(self, mock_maya):
        from dcc_mcp_maya.actions.texture_bake import bake_textures
        r = bake_textures(["pSphere1", "pCube1"], "/tmp/bake", bake_type="full_render")
        assert r["success"] is True

    def test_invalid_bake_type(self, mock_maya):
        from dcc_mcp_maya.actions.texture_bake import bake_textures
        r = bake_textures(["pSphere1"], "/tmp/bake", bake_type="shadow")
        assert r["success"] is False

    def test_invalid_renderer(self, mock_maya):
        from dcc_mcp_maya.actions.texture_bake import bake_textures
        r = bake_textures(["pSphere1"], "/tmp/bake", renderer="vray")
        assert r["success"] is False

    def test_empty_objects(self, mock_maya):
        from dcc_mcp_maya.actions.texture_bake import bake_textures
        r = bake_textures([], "/tmp/bake")
        assert r["success"] is False

    def test_object_not_found(self, mock_maya):
        mock_maya.objExists.return_value = False
        from dcc_mcp_maya.actions.texture_bake import bake_textures
        r = bake_textures(["missing"], "/tmp/bake")
        assert r["success"] is False

    def test_invalid_resolution(self, mock_maya):
        from dcc_mcp_maya.actions.texture_bake import bake_textures
        r = bake_textures(["pSphere1"], "/tmp/bake", resolution=0)
        assert r["success"] is False

    def test_normals_bake(self, mock_maya):
        from dcc_mcp_maya.actions.texture_bake import bake_textures
        r = bake_textures(["pSphere1"], "/tmp/bake", bake_type="normals", resolution=1024)
        assert r["success"] is True
        assert r["context"]["resolution"] == 1024


class TestSetColorManagement:
    def test_enable(self, mock_maya):
        mock_maya.colorManagementPrefs.return_value = True
        from dcc_mcp_maya.actions.texture_bake import set_color_management
        r = set_color_management(enabled=True)
        assert r["success"] is True

    def test_disable(self, mock_maya):
        mock_maya.colorManagementPrefs.return_value = False
        from dcc_mcp_maya.actions.texture_bake import set_color_management
        r = set_color_management(enabled=False)
        assert r["success"] is True

    def test_set_rendering_space(self, mock_maya):
        from dcc_mcp_maya.actions.texture_bake import set_color_management
        r = set_color_management(enabled=True, rendering_space="ACEScg")
        assert r["success"] is True

    def test_set_input_color_space(self, mock_maya):
        from dcc_mcp_maya.actions.texture_bake import set_color_management
        r = set_color_management(enabled=True, input_color_space="sRGB")
        assert r["success"] is True

    def test_set_output_transform(self, mock_maya):
        from dcc_mcp_maya.actions.texture_bake import set_color_management
        r = set_color_management(enabled=True, output_transform="sRGB gamma")
        assert r["success"] is True

    def test_all_params(self, mock_maya):
        from dcc_mcp_maya.actions.texture_bake import set_color_management
        r = set_color_management(
            enabled=True,
            input_color_space="sRGB",
            rendering_space="ACEScg",
            output_transform="Rec.709",
        )
        assert r["success"] is True

    def test_maya_not_available(self, monkeypatch):
        monkeypatch.setitem(sys.modules, "maya.cmds", None)
        import importlib
        import dcc_mcp_maya.actions.texture_bake as mod
        importlib.reload(mod)
        with patch.dict(sys.modules, {"maya.cmds": None}):
            from dcc_mcp_maya.actions.texture_bake import set_color_management
            r = set_color_management(enabled=True)
            assert "success" in r


class TestListColorSpaces:
    def test_basic(self, mock_maya):
        mock_maya.colorManagementPrefs.return_value = ["sRGB", "ACEScg"]
        from dcc_mcp_maya.actions.texture_bake import list_color_spaces
        r = list_color_spaces()
        assert r["success"] is True
        assert "input_color_spaces" in r["context"]

    def test_query_failure_graceful(self, mock_maya):
        mock_maya.colorManagementPrefs.side_effect = RuntimeError("not available")
        from dcc_mcp_maya.actions.texture_bake import list_color_spaces
        r = list_color_spaces()
        # Either returns empty lists or fails gracefully
        assert "success" in r

    def test_object_not_found_returns_empty(self, mock_maya):
        # colorManagementPrefs returns [] for all queries
        mock_maya.colorManagementPrefs.return_value = []
        from dcc_mcp_maya.actions.texture_bake import list_color_spaces
        r = list_color_spaces()
        assert r["success"] is True
        assert isinstance(r["context"]["input_color_spaces"], list)


# ===========================================================================
# register_all coverage
# ===========================================================================

class TestRegisterAllRound13:
    def test_total_action_count(self):
        from dcc_mcp_maya.actions import __all__
        # Should be >= 131 (119 + 12 new — copy_uvs reuses transferAttributes internally)
        assert len(__all__) >= 131

    def test_new_actions_in_all(self):
        from dcc_mcp_maya.actions import __all__
        new_actions = [
            "get_uv_info", "create_uv_set", "delete_uv_set", "project_uvs", "copy_uvs",
            "set_vertex_color", "get_vertex_color", "create_color_set", "remove_vertex_colors",
            "bake_textures", "set_color_management", "list_color_spaces",
        ]
        for action in new_actions:
            assert action in __all__, "Missing: {}".format(action)
