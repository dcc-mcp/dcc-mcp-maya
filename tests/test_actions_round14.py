"""Round 14 tests: UV shells, unfold/normalize UVs, blend-shape target, SDK, object colour, GPU override."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import sys
from types import ModuleType
from unittest.mock import MagicMock

# Import third-party modules
import pytest


# ---------------------------------------------------------------------------
# Mock helpers
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


@pytest.fixture(autouse=True)
def mock_maya(monkeypatch):
    """Inject a minimal mock Maya environment for Round 14 tests."""
    cmds = MagicMock()

    # Default return values
    cmds.objExists.return_value = True
    cmds.objectType.return_value = "blendShape"
    cmds.polyUVSet.return_value = ["map1", "map2"]
    cmds.polyEvaluate.return_value = [0, 0, 0, 1, 1, 1]
    cmds.polyEditUV.return_value = [0.0, 0.5, 1.0, 0.2, 0.8, 0.6]
    cmds.u3dUnfold.return_value = None
    cmds.u3dOptimize.return_value = None
    cmds.polyNormalizeUV.return_value = None
    cmds.blendShape.return_value = 2
    cmds.setAttr.return_value = None
    cmds.getAttr.return_value = 0.0
    cmds.setDrivenKeyframe.return_value = None

    maya_mod = ModuleType("maya")
    monkeypatch.setitem(sys.modules, "maya", maya_mod)
    monkeypatch.setitem(sys.modules, "maya.cmds", cmds)
    monkeypatch.setitem(sys.modules, "maya.api", MagicMock())
    monkeypatch.setitem(sys.modules, "maya.utils", MagicMock())

    yield cmds


# ---------------------------------------------------------------------------
# TestGetUvShellInfo
# ---------------------------------------------------------------------------

class TestGetUvShellInfo:
    def test_happy_path_default_uv_set(self, mock_maya):
        mock_maya.polyUVSet.side_effect = [
            ["map1", "map2"],   # allUVSets query
            ["map1"],           # currentUVSet query
        ]
        mock_maya.polyEvaluate.return_value = [0, 0, 0, 1, 1, 1]
        mock_maya.polyEditUV.side_effect = [
            [0.0, 0.5, 1.0, 0.2, 0.8, 0.6],
            [0.0, 0.3, 0.7, 0.1, 0.9, 0.5],
        ]
        from dcc_mcp_maya.actions.uv_ops import get_uv_shell_info
        result = get_uv_shell_info("pSphere1")
        assert result["success"] is True
        assert "shell_count" in result["context"]
        assert result["context"]["shell_count"] == 2

    def test_explicit_uv_set(self, mock_maya):
        mock_maya.polyUVSet.side_effect = [
            ["map1", "map2"],   # allUVSets
            None,               # set currentUVSet
            ["map2"],           # currentUVSet query
        ]
        mock_maya.polyEvaluate.return_value = [0, 1]
        mock_maya.polyEditUV.side_effect = [
            [0.1, 0.9],
            [0.2, 0.8],
        ]
        from dcc_mcp_maya.actions.uv_ops import get_uv_shell_info
        result = get_uv_shell_info("pSphere1", uv_set="map2")
        assert result["success"] is True

    def test_object_not_found(self, mock_maya):
        mock_maya.objExists.return_value = False
        from dcc_mcp_maya.actions.uv_ops import get_uv_shell_info
        result = get_uv_shell_info("nonExistent")
        assert result["success"] is False
        assert "not found" in result["message"].lower()

    def test_uv_set_not_found(self, mock_maya):
        mock_maya.polyUVSet.return_value = ["map1"]
        from dcc_mcp_maya.actions.uv_ops import get_uv_shell_info
        result = get_uv_shell_info("pSphere1", uv_set="missing_set")
        assert result["success"] is False

    def test_import_error(self, monkeypatch):
        monkeypatch.setitem(sys.modules, "maya.cmds", None)
        from dcc_mcp_maya.actions.uv_ops import get_uv_shell_info
        result = get_uv_shell_info("pSphere1")
        assert result["success"] is False

    def test_exception_handling(self, mock_maya):
        mock_maya.polyEvaluate.side_effect = RuntimeError("cmds error")
        from dcc_mcp_maya.actions.uv_ops import get_uv_shell_info
        result = get_uv_shell_info("pSphere1")
        assert result["success"] is False


# ---------------------------------------------------------------------------
# TestUnfoldUVs
# ---------------------------------------------------------------------------

class TestUnfoldUVs:
    def test_happy_path_default(self, mock_maya):
        from dcc_mcp_maya.actions.uv_ops import unfold_uvs
        result = unfold_uvs("pSphere1")
        assert result["success"] is True
        assert result["context"]["iterations"] == 1
        mock_maya.u3dUnfold.assert_called_once()
        mock_maya.u3dOptimize.assert_called_once()

    def test_custom_iterations(self, mock_maya):
        from dcc_mcp_maya.actions.uv_ops import unfold_uvs
        result = unfold_uvs("pSphere1", iterations=5)
        assert result["success"] is True
        assert result["context"]["iterations"] == 5

    def test_no_optimize(self, mock_maya):
        from dcc_mcp_maya.actions.uv_ops import unfold_uvs
        result = unfold_uvs("pSphere1", optimize_scale=False)
        assert result["success"] is True
        mock_maya.u3dOptimize.assert_not_called()

    def test_invalid_iterations_low(self, mock_maya):
        from dcc_mcp_maya.actions.uv_ops import unfold_uvs
        result = unfold_uvs("pSphere1", iterations=0)
        assert result["success"] is False

    def test_invalid_iterations_high(self, mock_maya):
        from dcc_mcp_maya.actions.uv_ops import unfold_uvs
        result = unfold_uvs("pSphere1", iterations=101)
        assert result["success"] is False

    def test_object_not_found(self, mock_maya):
        mock_maya.objExists.return_value = False
        from dcc_mcp_maya.actions.uv_ops import unfold_uvs
        result = unfold_uvs("nonExistent")
        assert result["success"] is False

    def test_import_error(self, monkeypatch):
        monkeypatch.setitem(sys.modules, "maya.cmds", None)
        from dcc_mcp_maya.actions.uv_ops import unfold_uvs
        result = unfold_uvs("pSphere1")
        assert result["success"] is False

    def test_exception_handling(self, mock_maya):
        mock_maya.u3dUnfold.side_effect = RuntimeError("unfold failed")
        from dcc_mcp_maya.actions.uv_ops import unfold_uvs
        result = unfold_uvs("pSphere1")
        assert result["success"] is False


# ---------------------------------------------------------------------------
# TestNormalizeUVs
# ---------------------------------------------------------------------------

class TestNormalizeUVs:
    def test_happy_path_default(self, mock_maya):
        from dcc_mcp_maya.actions.uv_ops import normalize_uvs
        result = normalize_uvs("pSphere1")
        assert result["success"] is True
        mock_maya.polyNormalizeUV.assert_called_once()

    def test_custom_layout(self, mock_maya):
        from dcc_mcp_maya.actions.uv_ops import normalize_uvs
        result = normalize_uvs("pSphere1", layout_u=0.5, layout_v=0.5)
        assert result["success"] is True
        assert result["context"]["layout_u"] == 0.5

    def test_invalid_layout_u_zero(self, mock_maya):
        from dcc_mcp_maya.actions.uv_ops import normalize_uvs
        result = normalize_uvs("pSphere1", layout_u=0.0)
        assert result["success"] is False

    def test_invalid_layout_v_over_one(self, mock_maya):
        from dcc_mcp_maya.actions.uv_ops import normalize_uvs
        result = normalize_uvs("pSphere1", layout_v=1.5)
        assert result["success"] is False

    def test_object_not_found(self, mock_maya):
        mock_maya.objExists.return_value = False
        from dcc_mcp_maya.actions.uv_ops import normalize_uvs
        result = normalize_uvs("nonExistent")
        assert result["success"] is False

    def test_import_error(self, monkeypatch):
        monkeypatch.setitem(sys.modules, "maya.cmds", None)
        from dcc_mcp_maya.actions.uv_ops import normalize_uvs
        result = normalize_uvs("pSphere1")
        assert result["success"] is False

    def test_exception_handling(self, mock_maya):
        mock_maya.polyNormalizeUV.side_effect = RuntimeError("cmds error")
        from dcc_mcp_maya.actions.uv_ops import normalize_uvs
        result = normalize_uvs("pSphere1")
        assert result["success"] is False


# ---------------------------------------------------------------------------
# TestBlendShapeAddTarget
# ---------------------------------------------------------------------------

class TestBlendShapeAddTarget:
    def test_happy_path_auto_index(self, mock_maya):
        mock_maya.objectType.return_value = "blendShape"
        mock_maya.blendShape.side_effect = [2, ["pSphere1"], None]
        from dcc_mcp_maya.actions.rigging import blend_shape_add_target
        result = blend_shape_add_target("blendShape1", "pSphere2")
        assert result["success"] is True
        assert result["context"]["blend_shape"] == "blendShape1"
        assert result["context"]["target_mesh"] == "pSphere2"
        assert result["context"]["target_index"] == 2

    def test_explicit_index(self, mock_maya):
        mock_maya.objectType.return_value = "blendShape"
        # When index is explicit, no weightCount call — only geometry + edit
        mock_maya.blendShape.side_effect = [["pSphere1"], None]
        from dcc_mcp_maya.actions.rigging import blend_shape_add_target
        result = blend_shape_add_target("blendShape1", "pSphere2", index=5)
        assert result["success"] is True
        assert result["context"]["target_index"] == 5

    def test_invalid_weight(self, mock_maya):
        from dcc_mcp_maya.actions.rigging import blend_shape_add_target
        result = blend_shape_add_target("blendShape1", "pSphere2", weight=1.5)
        assert result["success"] is False

    def test_blend_shape_not_found(self, mock_maya):
        mock_maya.objExists.side_effect = [False, True]
        from dcc_mcp_maya.actions.rigging import blend_shape_add_target
        result = blend_shape_add_target("nonExistent", "pSphere2")
        assert result["success"] is False

    def test_wrong_node_type(self, mock_maya):
        mock_maya.objectType.return_value = "transform"
        from dcc_mcp_maya.actions.rigging import blend_shape_add_target
        result = blend_shape_add_target("pSphere1", "pSphere2")
        assert result["success"] is False

    def test_target_mesh_not_found(self, mock_maya):
        mock_maya.objectType.return_value = "blendShape"
        mock_maya.objExists.side_effect = [True, False]
        from dcc_mcp_maya.actions.rigging import blend_shape_add_target
        result = blend_shape_add_target("blendShape1", "nonExistent")
        assert result["success"] is False

    def test_import_error(self, monkeypatch):
        monkeypatch.setitem(sys.modules, "maya.cmds", None)
        from dcc_mcp_maya.actions.rigging import blend_shape_add_target
        result = blend_shape_add_target("blendShape1", "pSphere2")
        assert result["success"] is False

    def test_exception_handling(self, mock_maya):
        mock_maya.objectType.return_value = "blendShape"
        mock_maya.blendShape.side_effect = RuntimeError("cmds error")
        from dcc_mcp_maya.actions.rigging import blend_shape_add_target
        result = blend_shape_add_target("blendShape1", "pSphere2")
        assert result["success"] is False


# ---------------------------------------------------------------------------
# TestSetDrivenKey
# ---------------------------------------------------------------------------

class TestSetDrivenKey:
    def test_happy_path_single_key(self, mock_maya):
        from dcc_mcp_maya.actions.rigging import set_driven_key
        result = set_driven_key(
            driver_attr="ctrl.rotateY",
            driven_attrs=["joint1.translateX"],
            driver_values=[0.0],
            driven_values=[[0.0]],
        )
        assert result["success"] is True
        assert result["context"]["key_count"] == 1
        assert result["context"]["keys_set"] == 1

    def test_multiple_keys_multiple_driven(self, mock_maya):
        from dcc_mcp_maya.actions.rigging import set_driven_key
        result = set_driven_key(
            driver_attr="ctrl.rotateY",
            driven_attrs=["joint1.tx", "joint1.tz"],
            driver_values=[0.0, 90.0],
            driven_values=[[0.0, 0.0], [1.0, -1.0]],
        )
        assert result["success"] is True
        assert result["context"]["keys_set"] == 4

    def test_empty_driver_values(self, mock_maya):
        from dcc_mcp_maya.actions.rigging import set_driven_key
        result = set_driven_key(
            driver_attr="ctrl.rotateY",
            driven_attrs=["joint1.tx"],
            driver_values=[],
            driven_values=[],
        )
        assert result["success"] is False

    def test_mismatched_value_counts(self, mock_maya):
        from dcc_mcp_maya.actions.rigging import set_driven_key
        result = set_driven_key(
            driver_attr="ctrl.rotateY",
            driven_attrs=["joint1.tx"],
            driver_values=[0.0, 90.0],
            driven_values=[[0.0]],
        )
        assert result["success"] is False

    def test_invalid_tangent_type(self, mock_maya):
        from dcc_mcp_maya.actions.rigging import set_driven_key
        result = set_driven_key(
            driver_attr="ctrl.rotateY",
            driven_attrs=["joint1.tx"],
            driver_values=[0.0],
            driven_values=[[0.0]],
            tangent_type="invalid",
        )
        assert result["success"] is False

    def test_driver_object_not_found(self, mock_maya):
        mock_maya.objExists.side_effect = [False]
        from dcc_mcp_maya.actions.rigging import set_driven_key
        result = set_driven_key(
            driver_attr="nonExistent.rotateY",
            driven_attrs=["joint1.tx"],
            driver_values=[0.0],
            driven_values=[[0.0]],
        )
        assert result["success"] is False

    def test_driven_object_not_found(self, mock_maya):
        mock_maya.objExists.side_effect = [True, False]
        from dcc_mcp_maya.actions.rigging import set_driven_key
        result = set_driven_key(
            driver_attr="ctrl.rotateY",
            driven_attrs=["nonExistent.tx"],
            driver_values=[0.0],
            driven_values=[[0.0]],
        )
        assert result["success"] is False

    def test_tangent_smooth(self, mock_maya):
        from dcc_mcp_maya.actions.rigging import set_driven_key
        result = set_driven_key(
            driver_attr="ctrl.rotateY",
            driven_attrs=["joint1.tx"],
            driver_values=[0.0],
            driven_values=[[0.0]],
            tangent_type="smooth",
        )
        assert result["success"] is True
        assert result["context"]["tangent_type"] == "smooth"

    def test_import_error(self, monkeypatch):
        monkeypatch.setitem(sys.modules, "maya.cmds", None)
        from dcc_mcp_maya.actions.rigging import set_driven_key
        result = set_driven_key(
            driver_attr="ctrl.rotateY",
            driven_attrs=["joint1.tx"],
            driver_values=[0.0],
            driven_values=[[0.0]],
        )
        assert result["success"] is False

    def test_exception_handling(self, mock_maya):
        mock_maya.setAttr.side_effect = RuntimeError("cmds error")
        from dcc_mcp_maya.actions.rigging import set_driven_key
        result = set_driven_key(
            driver_attr="ctrl.rotateY",
            driven_attrs=["joint1.tx"],
            driver_values=[0.0],
            driven_values=[[0.0]],
        )
        assert result["success"] is False


# ---------------------------------------------------------------------------
# TestSetObjectColor
# ---------------------------------------------------------------------------

class TestSetObjectColor:
    def test_happy_path_set_color(self, mock_maya):
        from dcc_mcp_maya.actions.scene_utils import set_object_color
        result = set_object_color("pSphere1", color_index=14)
        assert result["success"] is True
        assert result["context"]["color_index"] == 14
        assert result["context"]["use_default"] is False

    def test_use_default_flag(self, mock_maya):
        from dcc_mcp_maya.actions.scene_utils import set_object_color
        result = set_object_color("pSphere1", color_index=14, use_default=True)
        assert result["success"] is True
        assert result["context"]["color_index"] == 0

    def test_color_index_zero_resets(self, mock_maya):
        from dcc_mcp_maya.actions.scene_utils import set_object_color
        result = set_object_color("pSphere1", color_index=0)
        assert result["success"] is True
        assert result["context"]["color_index"] == 0

    def test_max_valid_index(self, mock_maya):
        from dcc_mcp_maya.actions.scene_utils import set_object_color
        result = set_object_color("pSphere1", color_index=31)
        assert result["success"] is True

    def test_invalid_color_index_negative(self, mock_maya):
        from dcc_mcp_maya.actions.scene_utils import set_object_color
        result = set_object_color("pSphere1", color_index=-1)
        assert result["success"] is False

    def test_invalid_color_index_too_high(self, mock_maya):
        from dcc_mcp_maya.actions.scene_utils import set_object_color
        result = set_object_color("pSphere1", color_index=32)
        assert result["success"] is False

    def test_object_not_found(self, mock_maya):
        mock_maya.objExists.return_value = False
        from dcc_mcp_maya.actions.scene_utils import set_object_color
        result = set_object_color("nonExistent", color_index=5)
        assert result["success"] is False

    def test_import_error(self, monkeypatch):
        monkeypatch.setitem(sys.modules, "maya.cmds", None)
        from dcc_mcp_maya.actions.scene_utils import set_object_color
        result = set_object_color("pSphere1", color_index=5)
        assert result["success"] is False

    def test_exception_handling(self, mock_maya):
        mock_maya.setAttr.side_effect = RuntimeError("cmds error")
        from dcc_mcp_maya.actions.scene_utils import set_object_color
        result = set_object_color("pSphere1", color_index=5)
        assert result["success"] is False


# ---------------------------------------------------------------------------
# TestToggleGpuOverride
# ---------------------------------------------------------------------------

class TestToggleGpuOverride:
    def test_enable_gpu_override(self, mock_maya):
        from dcc_mcp_maya.actions.scene_utils import toggle_gpu_override
        result = toggle_gpu_override("pSphere1", enabled=True)
        assert result["success"] is True
        assert result["context"]["enabled"] is True
        assert result["context"]["display_type"] == 2

    def test_disable_gpu_override(self, mock_maya):
        from dcc_mcp_maya.actions.scene_utils import toggle_gpu_override
        result = toggle_gpu_override("pSphere1", enabled=False)
        assert result["success"] is True
        assert result["context"]["enabled"] is False
        assert result["context"]["display_type"] == 0

    def test_default_enabled(self, mock_maya):
        from dcc_mcp_maya.actions.scene_utils import toggle_gpu_override
        result = toggle_gpu_override("pSphere1")
        assert result["success"] is True
        assert result["context"]["enabled"] is True

    def test_object_not_found(self, mock_maya):
        mock_maya.objExists.return_value = False
        from dcc_mcp_maya.actions.scene_utils import toggle_gpu_override
        result = toggle_gpu_override("nonExistent")
        assert result["success"] is False

    def test_import_error(self, monkeypatch):
        monkeypatch.setitem(sys.modules, "maya.cmds", None)
        from dcc_mcp_maya.actions.scene_utils import toggle_gpu_override
        result = toggle_gpu_override("pSphere1")
        assert result["success"] is False

    def test_exception_handling(self, mock_maya):
        mock_maya.setAttr.side_effect = RuntimeError("cmds error")
        from dcc_mcp_maya.actions.scene_utils import toggle_gpu_override
        result = toggle_gpu_override("pSphere1")
        assert result["success"] is False


# ---------------------------------------------------------------------------
# TestRegisterAllRound14
# ---------------------------------------------------------------------------

class TestRegisterAllRound14:
    def test_register_all_has_new_actions(self):
        from dcc_mcp_maya.actions import __all__ as all_actions
        new_actions = [
            "get_uv_shell_info",
            "unfold_uvs",
            "normalize_uvs",
            "blend_shape_add_target",
            "set_driven_key",
            "set_object_color",
            "toggle_gpu_override",
        ]
        for action in new_actions:
            assert action in all_actions, "{} not found in __all__".format(action)

    def test_total_action_count(self):
        from dcc_mcp_maya.actions import __all__ as all_actions
        assert len(all_actions) >= 138, "Expected at least 138 actions, got {}".format(
            len(all_actions)
        )
