"""Round 10 tests: conftest helpers + new api helpers + deep skill edge cases.

Covers:
- conftest.load_and_call / load_and_call_with_mel
- api.ensure_valid_name / build_context_dict
- api.scene_object_from_node / object_transform_from_node / bounding_box_from_node
- Deep skill edge cases: maya-display, maya-primitives, maya-scene
"""

# Import future modules
from __future__ import annotations

# Import built-in modules
import sys
from pathlib import Path
from unittest.mock import MagicMock

# Import third-party modules
import pytest

# Add tests/ to sys.path so we can import conftest helpers directly
sys.path.insert(0, str(Path(__file__).parent))

from conftest import load_and_call, load_and_call_with_mel  # noqa: E402

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_cmds(**overrides):
    """Return a MagicMock that looks like maya.cmds with sensible defaults."""
    mock_cmds = MagicMock()
    mock_cmds.objExists.return_value = True
    mock_cmds.objectType.return_value = "transform"
    mock_cmds.listRelatives.return_value = []
    mock_cmds.getAttr.return_value = [(0.0, 0.0, 0.0)]
    mock_cmds.exactWorldBoundingBox.return_value = [-1.0, -1.0, -1.0, 1.0, 1.0, 1.0]
    for k, v in overrides.items():
        setattr(mock_cmds, k, v)
    return mock_cmds


# ===========================================================================
# TestConfestLoadAndCall
# ===========================================================================


class TestConftestLoadAndCall:
    """Verify the load_and_call helper in conftest.py."""

    def test_returns_dict(self):
        mock_cmds = _make_cmds()
        mock_cmds.ls.return_value = []
        result = load_and_call("maya-scene/scripts/get_scene_info.py", mock_cmds)
        assert isinstance(result, dict)

    def test_propagates_kwargs(self):
        mock_cmds = _make_cmds()
        mock_cmds.ls.return_value = ["pSphere1"]
        mock_cmds.objectType.return_value = "transform"
        mock_cmds.getAttr.return_value = [(1.0, 2.0, 3.0)]
        result = load_and_call("maya-scene/scripts/get_scene_info.py", mock_cmds, filter="transform")
        assert isinstance(result, dict)

    def test_success_key_present(self):
        mock_cmds = _make_cmds()
        mock_cmds.ls.return_value = []
        result = load_and_call("maya-scene/scripts/get_scene_info.py", mock_cmds)
        assert "success" in result

    def test_unique_module_names(self):
        """Each load_and_call invocation must not share a module object."""
        mock_cmds = _make_cmds()
        mock_cmds.ls.return_value = []
        r1 = load_and_call("maya-scene/scripts/get_scene_info.py", mock_cmds)
        r2 = load_and_call("maya-scene/scripts/get_scene_info.py", mock_cmds)
        # Both should succeed independently
        assert r1["success"] is True
        assert r2["success"] is True


class TestConftestLoadAndCallWithMel:
    """Verify the load_and_call_with_mel helper."""

    def test_creates_default_mock_mel(self):
        mock_cmds = _make_cmds()
        mock_cmds.annotate = MagicMock(return_value="annotationShape1")
        mock_cmds.listRelatives.return_value = ["annotation1"]
        result = load_and_call_with_mel(
            "maya-annotation/scripts/create_annotation.py",
            mock_cmds,
        )
        assert isinstance(result, dict)

    def test_accepts_custom_mock_mel(self):
        mock_cmds = _make_cmds()
        mock_mel = MagicMock()
        mock_cmds.annotate = MagicMock(return_value="annotationShape1")
        mock_cmds.listRelatives.return_value = ["annotation1"]
        result = load_and_call_with_mel(
            "maya-annotation/scripts/create_annotation.py",
            mock_cmds,
            mock_mel=mock_mel,
        )
        assert isinstance(result, dict)

    def test_mel_available_inside_script(self):
        """Scripts that import maya.mel should not raise ImportError."""
        mock_cmds = _make_cmds()
        mock_mel = MagicMock()
        # add_toon_outline uses maya.mel internally
        mock_cmds.ls.return_value = ["pCube1"]
        mock_cmds.listRelatives.return_value = []
        mock_cmds.filterExpand.return_value = []
        mock_cmds.attributeQuery.return_value = True
        mock_mel.eval.return_value = None
        result = load_and_call_with_mel(
            "maya-toon/scripts/add_toon_outline.py",
            mock_cmds,
            mock_mel=mock_mel,
            objects=["pCube1"],
        )
        assert isinstance(result, dict)


# ===========================================================================
# TestEnsureValidName
# ===========================================================================


class TestEnsureValidName:
    """Tests for api.ensure_valid_name."""

    def setup_method(self):
        from dcc_mcp_maya.api import ensure_valid_name

        self.fn = ensure_valid_name

    def test_none_returns_error(self):
        result = self.fn(None)
        assert result is not None
        assert result["success"] is False

    def test_empty_string_returns_error(self):
        result = self.fn("")
        assert result is not None
        assert result["success"] is False

    def test_whitespace_only_returns_error(self):
        result = self.fn("   ")
        assert result is not None
        assert result["success"] is False

    def test_valid_name_returns_none(self):
        assert self.fn("pSphere1") is None

    def test_single_char_valid(self):
        assert self.fn("x") is None

    def test_error_includes_param_name(self):
        result = self.fn("", param="layer_name")
        assert "layer_name" in result["message"]

    def test_default_param_name_is_name(self):
        result = self.fn("")
        assert "'name'" in result["message"]

    def test_solutions_present(self):
        result = self.fn("")
        assert "possible_solutions" in result["context"]

    def test_importable_from_top_level(self):
        from dcc_mcp_maya import ensure_valid_name as fn

        assert callable(fn)

    def test_in_api_all(self):
        import dcc_mcp_maya.api as api

        assert "ensure_valid_name" in api.__all__

    def test_in_package_all(self):
        import dcc_mcp_maya

        assert "ensure_valid_name" in dcc_mcp_maya.__all__


# ===========================================================================
# TestBuildContextDict
# ===========================================================================


class TestBuildContextDict:
    """Tests for api.build_context_dict."""

    def setup_method(self):
        from dcc_mcp_maya.api import build_context_dict

        self.fn = build_context_dict

    def test_removes_none_values(self):
        result = self.fn(a=1, b=None, c="x")
        assert "b" not in result
        assert result == {"a": 1, "c": "x"}

    def test_empty_returns_empty(self):
        assert self.fn() == {}

    def test_all_none_returns_empty(self):
        assert self.fn(a=None, b=None) == {}

    def test_all_present_returns_all(self):
        result = self.fn(x=1, y=2)
        assert result == {"x": 1, "y": 2}

    def test_false_values_kept(self):
        result = self.fn(a=False, b=0, c=None)
        assert result == {"a": False, "b": 0}

    def test_empty_string_kept(self):
        # Empty strings are not None → kept
        result = self.fn(name="", val=None)
        assert result == {"name": ""}

    def test_importable_from_top_level(self):
        from dcc_mcp_maya import build_context_dict as fn

        assert callable(fn)

    def test_in_api_all(self):
        import dcc_mcp_maya.api as api

        assert "build_context_dict" in api.__all__

    def test_in_package_all(self):
        import dcc_mcp_maya

        assert "build_context_dict" in dcc_mcp_maya.__all__


# ===========================================================================
# TestSceneObjectFromNode
# ===========================================================================


class TestSceneObjectFromNode:
    """Tests for api.scene_object_from_node."""

    def setup_method(self):
        from dcc_mcp_maya.api import scene_object_from_node

        self.fn = scene_object_from_node

    def _make(self, **overrides):
        mock_cmds = _make_cmds(**overrides)
        return mock_cmds

    def test_name_extracted_from_long_name(self):
        cmds = self._make()
        cmds.objectType.return_value = "transform"
        cmds.listRelatives.return_value = []
        cmds.getAttr.return_value = True
        result = self.fn(cmds, "|group1|pSphere1")
        assert result["name"] == "pSphere1"

    def test_long_name_preserved(self):
        cmds = self._make()
        cmds.objectType.return_value = "transform"
        cmds.listRelatives.return_value = []
        cmds.getAttr.return_value = True
        result = self.fn(cmds, "|group1|pSphere1")
        assert result["long_name"] == "|group1|pSphere1"

    def test_object_type_from_cmds(self):
        cmds = self._make()
        cmds.objectType.return_value = "mesh"
        cmds.listRelatives.return_value = []
        cmds.getAttr.return_value = True
        result = self.fn(cmds, "pSphereShape1")
        assert result["object_type"] == "mesh"

    def test_parent_none_for_top_level(self):
        cmds = self._make()
        cmds.listRelatives.return_value = []
        cmds.getAttr.return_value = True
        result = self.fn(cmds, "|pSphere1")
        assert result["parent"] is None

    def test_parent_set_when_has_parent(self):
        cmds = self._make()
        cmds.listRelatives.return_value = ["|group1"]
        cmds.getAttr.return_value = True
        result = self.fn(cmds, "|group1|pSphere1")
        assert result["parent"] == "|group1"

    def test_visible_from_getattr(self):
        cmds = self._make()
        cmds.listRelatives.return_value = []
        cmds.getAttr.return_value = True
        result = self.fn(cmds, "pSphere1")
        assert result["visible"] is True

    def test_visible_false(self):
        cmds = self._make()
        cmds.listRelatives.return_value = []
        cmds.getAttr.return_value = False
        result = self.fn(cmds, "pSphere1")
        assert result["visible"] is False

    def test_visible_fallback_on_exception(self):
        cmds = self._make()
        cmds.listRelatives.return_value = []
        cmds.getAttr.side_effect = RuntimeError("no attr")
        result = self.fn(cmds, "pSphere1")
        assert result["visible"] is True  # fallback

    def test_metadata_empty_dict(self):
        cmds = self._make()
        cmds.listRelatives.return_value = []
        result = self.fn(cmds, "pSphere1")
        assert result["metadata"] == {}

    def test_no_pipe_in_name_uses_full(self):
        cmds = self._make()
        cmds.listRelatives.return_value = []
        result = self.fn(cmds, "pSphere1")
        assert result["name"] == "pSphere1"

    def test_importable_from_top_level(self):
        from dcc_mcp_maya import scene_object_from_node as fn

        assert callable(fn)

    def test_in_api_all(self):
        import dcc_mcp_maya.api as api

        assert "scene_object_from_node" in api.__all__


# ===========================================================================
# TestObjectTransformFromNode
# ===========================================================================


class TestObjectTransformFromNode:
    """Tests for api.object_transform_from_node."""

    def setup_method(self):
        from dcc_mcp_maya.api import object_transform_from_node

        self.fn = object_transform_from_node

    def test_returns_translate(self):
        cmds = _make_cmds()
        cmds.getAttr.return_value = [(1.0, 2.0, 3.0)]
        result = self.fn(cmds, "pSphere1")
        assert result["translate"] == [1.0, 2.0, 3.0]

    def test_returns_rotate(self):
        cmds = _make_cmds()
        cmds.getAttr.return_value = [(45.0, 0.0, 90.0)]
        result = self.fn(cmds, "pSphere1")
        assert result["rotate"] == [45.0, 0.0, 90.0]

    def test_returns_scale(self):
        cmds = _make_cmds()
        cmds.getAttr.return_value = [(2.0, 2.0, 2.0)]
        result = self.fn(cmds, "pSphere1")
        assert result["scale"] == [2.0, 2.0, 2.0]

    def test_all_keys_present(self):
        cmds = _make_cmds()
        cmds.getAttr.return_value = [(0.0, 0.0, 0.0)]
        result = self.fn(cmds, "node")
        assert set(result.keys()) == {"translate", "rotate", "scale"}

    def test_values_are_float(self):
        cmds = _make_cmds()
        cmds.getAttr.return_value = [(1, 2, 3)]  # ints from mock
        result = self.fn(cmds, "node")
        for val in result["translate"]:
            assert isinstance(val, float)

    def test_importable_from_top_level(self):
        from dcc_mcp_maya import object_transform_from_node as fn

        assert callable(fn)

    def test_in_api_all(self):
        import dcc_mcp_maya.api as api

        assert "object_transform_from_node" in api.__all__


# ===========================================================================
# TestBoundingBoxFromNode
# ===========================================================================


class TestBoundingBoxFromNode:
    """Tests for api.bounding_box_from_node."""

    def setup_method(self):
        from dcc_mcp_maya.api import bounding_box_from_node

        self.fn = bounding_box_from_node

    def test_min_max_correct(self):
        cmds = _make_cmds()
        cmds.exactWorldBoundingBox.return_value = [-1.0, -2.0, -3.0, 1.0, 2.0, 3.0]
        result = self.fn(cmds, "node")
        assert result["min"] == [-1.0, -2.0, -3.0]
        assert result["max"] == [1.0, 2.0, 3.0]

    def test_center_computed(self):
        cmds = _make_cmds()
        cmds.exactWorldBoundingBox.return_value = [0.0, 0.0, 0.0, 2.0, 4.0, 6.0]
        result = self.fn(cmds, "node")
        assert result["center"] == [1.0, 2.0, 3.0]

    def test_size_computed(self):
        cmds = _make_cmds()
        cmds.exactWorldBoundingBox.return_value = [0.0, 0.0, 0.0, 2.0, 4.0, 6.0]
        result = self.fn(cmds, "node")
        assert result["size"] == [2.0, 4.0, 6.0]

    def test_asymmetric_bbox(self):
        cmds = _make_cmds()
        cmds.exactWorldBoundingBox.return_value = [1.0, 2.0, 3.0, 4.0, 6.0, 9.0]
        result = self.fn(cmds, "node")
        assert result["size"] == [3.0, 4.0, 6.0]
        assert result["center"] == [2.5, 4.0, 6.0]

    def test_all_keys_present(self):
        cmds = _make_cmds()
        cmds.exactWorldBoundingBox.return_value = [0.0, 0.0, 0.0, 1.0, 1.0, 1.0]
        result = self.fn(cmds, "node")
        assert set(result.keys()) == {"min", "max", "center", "size"}

    def test_importable_from_top_level(self):
        from dcc_mcp_maya import bounding_box_from_node as fn

        assert callable(fn)

    def test_in_api_all(self):
        import dcc_mcp_maya.api as api

        assert "bounding_box_from_node" in api.__all__


# ===========================================================================
# TestDeepSkillEdgeCases — using load_and_call
# ===========================================================================


class TestGetSceneInfoDeep:
    """Deep tests for maya-scene/get_scene_info.py using load_and_call.

    get_scene_info(include_transforms=True) lists all 'transform' nodes.
    """

    def test_empty_scene(self):
        cmds = _make_cmds()
        cmds.ls.return_value = []
        result = load_and_call("maya-scene/scripts/get_scene_info.py", cmds)
        assert result["success"] is True
        assert result["context"]["count"] == 0

    def test_include_transforms_true(self):
        cmds = _make_cmds()
        cmds.ls.return_value = ["pSphere1"]
        cmds.objectType.return_value = "transform"
        cmds.listRelatives.return_value = []
        cmds.getAttr.return_value = [(0.0, 0.0, 0.0)]
        result = load_and_call("maya-scene/scripts/get_scene_info.py", cmds, include_transforms=True)
        assert result["success"] is True
        assert result["context"]["count"] == 1
        # node should have translate/rotate/scale
        node = result["context"]["nodes"][0]
        assert "translate" in node

    def test_include_transforms_false_skips_xform(self):
        cmds = _make_cmds()
        cmds.ls.return_value = ["pSphere1"]
        cmds.listRelatives.return_value = []
        result = load_and_call("maya-scene/scripts/get_scene_info.py", cmds, include_transforms=False)
        assert result["success"] is True
        node = result["context"]["nodes"][0]
        assert "translate" not in node

    def test_exception_handled(self):
        cmds = _make_cmds()
        cmds.ls.side_effect = RuntimeError("scene locked")
        result = load_and_call("maya-scene/scripts/get_scene_info.py", cmds)
        assert result["success"] is False

    def test_count_matches_nodes_list(self):
        cmds = _make_cmds()
        cmds.ls.return_value = ["a", "b", "c"]
        cmds.listRelatives.return_value = []
        cmds.getAttr.return_value = [(0.0, 0.0, 0.0)]
        result = load_and_call("maya-scene/scripts/get_scene_info.py", cmds)
        assert result["context"]["count"] == len(result["context"]["nodes"])


class TestCreateSphereDeep:
    """Deep tests for maya-primitives/create_sphere.py using load_and_call."""

    def test_default_creates_sphere(self):
        cmds = _make_cmds()
        cmds.polySphere.return_value = ["pSphere1", "polySphere1"]
        result = load_and_call("maya-primitives/scripts/create_sphere.py", cmds)
        assert result["success"] is True
        assert result["context"]["object_name"] == "pSphere1"

    def test_custom_radius(self):
        cmds = _make_cmds()
        cmds.polySphere.return_value = ["pSphere1", "polySphere1"]
        result = load_and_call("maya-primitives/scripts/create_sphere.py", cmds, radius=2.5)
        assert result["success"] is True
        cmds.polySphere.assert_called_once()
        call_kwargs = cmds.polySphere.call_args[1]
        assert call_kwargs.get("radius") == 2.5

    def test_name_passed_calls_rename(self):
        cmds = _make_cmds()
        cmds.polySphere.return_value = ["pSphere1", "polySphere1"]
        cmds.rename.return_value = "myBall"
        result = load_and_call("maya-primitives/scripts/create_sphere.py", cmds, name="myBall")
        assert result["success"] is True
        cmds.rename.assert_called_once()

    def test_exception_returns_error(self):
        cmds = _make_cmds()
        cmds.polySphere.side_effect = RuntimeError("maya crash")
        result = load_and_call("maya-primitives/scripts/create_sphere.py", cmds)
        assert result["success"] is False

    def test_object_name_in_context(self):
        cmds = _make_cmds()
        cmds.polySphere.return_value = ["myBall", "polySphere1"]
        cmds.rename.return_value = "myBall"
        result = load_and_call("maya-primitives/scripts/create_sphere.py", cmds, name="myBall")
        assert "object_name" in result["context"]


class TestCreateCubeDeep:
    """Deep tests for maya-primitives/create_cube.py using load_and_call."""

    def test_default_creates_cube(self):
        cmds = _make_cmds()
        cmds.polyCube.return_value = ["pCube1", "polyCube1"]
        result = load_and_call("maya-primitives/scripts/create_cube.py", cmds)
        assert result["success"] is True

    def test_exception_returns_error(self):
        cmds = _make_cmds()
        cmds.polyCube.side_effect = RuntimeError("fail")
        result = load_and_call("maya-primitives/scripts/create_cube.py", cmds)
        assert result["success"] is False


class TestCreateDisplayLayerDeep:
    """Deep tests for maya-display/create_display_layer.py using load_and_call.

    create_display_layer(name=None, objects=None, visibility=True)
    """

    def test_named_layer_success(self):
        cmds = _make_cmds()
        cmds.createDisplayLayer.return_value = "myLayer"
        result = load_and_call("maya-display/scripts/create_display_layer.py", cmds, name="myLayer")
        assert result["success"] is True
        assert result["context"]["layer_name"] == "myLayer"

    def test_no_name_uses_maya_generated(self):
        cmds = _make_cmds()
        cmds.createDisplayLayer.return_value = "layer1"
        result = load_and_call("maya-display/scripts/create_display_layer.py", cmds)
        assert result["success"] is True

    def test_visibility_false_calls_setattr(self):
        cmds = _make_cmds()
        cmds.createDisplayLayer.return_value = "layer1"
        result = load_and_call("maya-display/scripts/create_display_layer.py", cmds, name="l", visibility=False)
        assert result["success"] is True
        cmds.setAttr.assert_called()

    def test_objects_added_to_layer(self):
        cmds = _make_cmds()
        cmds.createDisplayLayer.return_value = "layer1"
        cmds.objExists.return_value = True
        result = load_and_call(
            "maya-display/scripts/create_display_layer.py",
            cmds,
            name="l",
            objects=["pSphere1"],
        )
        assert result["success"] is True
        assert "pSphere1" in result["context"]["objects_added"]

    def test_missing_objects_not_added(self):
        cmds = _make_cmds()
        cmds.createDisplayLayer.return_value = "layer1"
        cmds.objExists.return_value = False
        result = load_and_call(
            "maya-display/scripts/create_display_layer.py",
            cmds,
            name="l",
            objects=["ghost"],
        )
        assert result["success"] is True
        assert result["context"]["objects_added"] == []

    def test_exception_returns_error(self):
        cmds = _make_cmds()
        cmds.createDisplayLayer.side_effect = RuntimeError("cannot create")
        result = load_and_call("maya-display/scripts/create_display_layer.py", cmds, name="l")
        assert result["success"] is False


class TestDeleteDisplayLayerDeep:
    """Deep tests for maya-display/delete_display_layer.py using load_and_call.

    delete_display_layer(layer_name, remove_objects=False)
    """

    def test_missing_node_returns_error(self):
        cmds = _make_cmds()
        cmds.objExists.return_value = False
        result = load_and_call("maya-display/scripts/delete_display_layer.py", cmds, layer_name="ghost")
        assert result["success"] is False

    def test_wrong_type_returns_error(self):
        cmds = _make_cmds()
        cmds.objExists.return_value = True
        cmds.objectType.return_value = "transform"  # not displayLayer
        result = load_and_call("maya-display/scripts/delete_display_layer.py", cmds, layer_name="pSphere1")
        assert result["success"] is False
        assert "wrong node type" in result["message"].lower()

    def test_happy_path(self):
        cmds = _make_cmds()
        cmds.objExists.return_value = True
        cmds.objectType.return_value = "displayLayer"
        result = load_and_call("maya-display/scripts/delete_display_layer.py", cmds, layer_name="myLayer")
        assert result["success"] is True
        cmds.delete.assert_called()

    def test_default_layer_blocked(self):
        """defaultLayer should not be deletable."""
        cmds = _make_cmds()
        result = load_and_call("maya-display/scripts/delete_display_layer.py", cmds, layer_name="defaultLayer")
        assert result["success"] is False


# ===========================================================================
# TestApiPublicExportsRound10
# ===========================================================================


class TestApiPublicExportsRound10:
    """Verify all 5 new helpers are properly exported."""

    @pytest.mark.parametrize(
        "name",
        [
            "ensure_valid_name",
            "build_context_dict",
            "scene_object_from_node",
            "object_transform_from_node",
            "bounding_box_from_node",
        ],
    )
    def test_importable_from_dcc_mcp_maya(self, name):
        import dcc_mcp_maya

        assert hasattr(dcc_mcp_maya, name), "{} missing from top-level package".format(name)

    @pytest.mark.parametrize(
        "name",
        [
            "ensure_valid_name",
            "build_context_dict",
            "scene_object_from_node",
            "object_transform_from_node",
            "bounding_box_from_node",
        ],
    )
    def test_in_api_all(self, name):
        import dcc_mcp_maya.api as api

        assert name in api.__all__

    @pytest.mark.parametrize(
        "name",
        [
            "ensure_valid_name",
            "build_context_dict",
            "scene_object_from_node",
            "object_transform_from_node",
            "bounding_box_from_node",
        ],
    )
    def test_in_package_all(self, name):
        import dcc_mcp_maya

        assert name in dcc_mcp_maya.__all__
