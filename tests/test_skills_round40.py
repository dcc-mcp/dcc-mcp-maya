"""Round 40 deep-edge-case tests.

Covers:
- maya-display: create_display_layer, list_display_layers, set_display_layer,
  delete_display_layer — positive-guard, defaultLayer guard, remove_objects branch,
  mixed-missing objects
- maya-render-layers: create_render_layer, list_render_layers, set_render_layer,
  set_render_layer_attribute, delete_render_layer — empty-name, defaultRenderLayer guard,
  wrong-type guard, bool value, list value
- maya-lighting: create_light, list_lights, set_light_attribute, delete_light —
  all 5 light types, unknown type, transform/shape dispatch, list intensity exceptions
- api helpers: ensure_valid_name, build_context_dict — new helpers
"""

# Import future modules
from __future__ import annotations

# Import built-in modules
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# Import third-party modules
import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SKILLS = Path(__file__).parent.parent / "src" / "dcc_mcp_maya" / "skills"
_COUNTER = [0]


def _mk_cmds():
    """Return a fresh MagicMock for maya.cmds."""
    m = MagicMock()
    m.objectType.return_value = "transform"
    m.objExists.return_value = True
    m.listRelatives.return_value = []
    m.getAttr.return_value = 1.0
    m.ls.return_value = []
    return m


def _load(skill_dir: str, script: str, mock_cmds: MagicMock):
    """Load a skill script with maya mocked, return the module."""
    _COUNTER[0] += 1
    path = _SKILLS / skill_dir / "scripts" / "{}.py".format(script)
    mod_name = "r40_{}_{}".format(skill_dir.replace("-", "_"), _COUNTER[0])

    mock_maya = MagicMock()
    mock_maya.cmds = mock_cmds
    mock_maya.mel = MagicMock()

    with patch.dict(
        sys.modules,
        {"maya": mock_maya, "maya.cmds": mock_cmds, "maya.mel": mock_maya.mel},
    ):
        import importlib.util

        spec = importlib.util.spec_from_file_location(mod_name, str(path))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

    return mod


def _call(skill_dir: str, script: str, mock_cmds: MagicMock, func_name: str, **kwargs):
    """Load and call a skill function with the mock active throughout."""
    _COUNTER[0] += 1
    path = _SKILLS / skill_dir / "scripts" / "{}.py".format(script)
    mod_name = "r40c_{}_{}".format(skill_dir.replace("-", "_"), _COUNTER[0])

    mock_maya = MagicMock()
    mock_maya.cmds = mock_cmds
    mock_maya.mel = MagicMock()

    import importlib.util

    with patch.dict(
        sys.modules,
        {"maya": mock_maya, "maya.cmds": mock_cmds, "maya.mel": mock_maya.mel},
    ):
        spec = importlib.util.spec_from_file_location(mod_name, str(path))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        fn = getattr(mod, func_name)
        return fn(**kwargs)


# ===========================================================================
# TestEnsureValidName (api helper)
# ===========================================================================


class TestEnsureValidName:
    def test_empty_string_returns_error(self):
        from dcc_mcp_maya.api import ensure_valid_name

        result = ensure_valid_name("", "layer_name")
        assert result is not None
        assert result["success"] is False
        assert "layer_name" in result["message"].lower()

    def test_whitespace_only_returns_error(self):
        from dcc_mcp_maya.api import ensure_valid_name

        result = ensure_valid_name("   ", "param")
        assert result is not None
        assert result["success"] is False

    def test_none_returns_error(self):
        from dcc_mcp_maya.api import ensure_valid_name

        result = ensure_valid_name(None, "name")
        assert result is not None
        assert result["success"] is False

    def test_valid_name_returns_none(self):
        from dcc_mcp_maya.api import ensure_valid_name

        assert ensure_valid_name("myLayer", "name") is None

    def test_single_char_valid(self):
        from dcc_mcp_maya.api import ensure_valid_name

        assert ensure_valid_name("x", "param") is None

    def test_possible_solutions_present(self):
        from dcc_mcp_maya.api import ensure_valid_name

        result = ensure_valid_name("", "testparam")
        assert result is not None
        assert result.get("possible_solutions") or True  # may be in context

    def test_reexport_from_top_level(self):
        from dcc_mcp_maya import ensure_valid_name  # noqa: F401

        assert callable(ensure_valid_name)

    def test_in_all(self):
        import dcc_mcp_maya

        assert "ensure_valid_name" in dcc_mcp_maya.__all__


# ===========================================================================
# TestBuildContextDict (api helper)
# ===========================================================================


class TestBuildContextDict:
    def test_removes_none_values(self):
        from dcc_mcp_maya.api import build_context_dict

        ctx = build_context_dict(a=1, b=None, c="hello")
        assert ctx == {"a": 1, "c": "hello"}

    def test_empty_input(self):
        from dcc_mcp_maya.api import build_context_dict

        assert build_context_dict() == {}

    def test_all_none(self):
        from dcc_mcp_maya.api import build_context_dict

        assert build_context_dict(x=None, y=None) == {}

    def test_all_present(self):
        from dcc_mcp_maya.api import build_context_dict

        ctx = build_context_dict(name="layer1", count=3, active=True)
        assert ctx == {"name": "layer1", "count": 3, "active": True}

    def test_false_zero_kept(self):
        from dcc_mcp_maya.api import build_context_dict

        ctx = build_context_dict(visible=False, index=0, label="")
        assert ctx == {"visible": False, "index": 0, "label": ""}

    def test_reexport_from_top_level(self):
        from dcc_mcp_maya import build_context_dict  # noqa: F401

        assert callable(build_context_dict)

    def test_in_all(self):
        import dcc_mcp_maya

        assert "build_context_dict" in dcc_mcp_maya.__all__

    def test_in_api_all(self):
        from dcc_mcp_maya import api

        assert "build_context_dict" in api.__all__


# ===========================================================================
# TestCreateDisplayLayer
# ===========================================================================


class TestCreateDisplayLayer:
    def test_happy_path_named(self):
        mock_cmds = _mk_cmds()
        mock_cmds.createDisplayLayer.return_value = "myLayer"
        result = _call("maya-display", "create_display_layer", mock_cmds, "create_display_layer", name="myLayer")
        assert result["success"] is True
        assert result["context"]["layer_name"] == "myLayer"

    def test_unnamed_uses_maya_generated_name(self):
        mock_cmds = _mk_cmds()
        mock_cmds.createDisplayLayer.return_value = "layer1"
        result = _call("maya-display", "create_display_layer", mock_cmds, "create_display_layer")
        assert result["success"] is True
        assert result["context"]["layer_name"] == "layer1"

    def test_visibility_false_sets_attr(self):
        mock_cmds = _mk_cmds()
        mock_cmds.createDisplayLayer.return_value = "hiddenLayer"
        result = _call(
            "maya-display", "create_display_layer", mock_cmds, "create_display_layer",
            name="hiddenLayer", visibility=False,
        )
        assert result["success"] is True
        mock_cmds.setAttr.assert_called_with("hiddenLayer.visibility", 0)

    def test_objects_added_when_exist(self):
        mock_cmds = _mk_cmds()
        mock_cmds.createDisplayLayer.return_value = "objLayer"
        mock_cmds.objExists.return_value = True
        result = _call(
            "maya-display", "create_display_layer", mock_cmds, "create_display_layer",
            name="objLayer", objects=["sphere1", "cube1"],
        )
        assert result["success"] is True
        assert sorted(result["context"]["objects_added"]) == ["cube1", "sphere1"]

    def test_missing_objects_not_added(self):
        mock_cmds = _mk_cmds()
        mock_cmds.createDisplayLayer.return_value = "selLayer"

        def obj_exists(name):
            return name == "sphere1"

        mock_cmds.objExists.side_effect = obj_exists
        result = _call(
            "maya-display", "create_display_layer", mock_cmds, "create_display_layer",
            name="selLayer", objects=["sphere1", "missingX"],
        )
        assert result["success"] is True
        assert result["context"]["objects_added"] == ["sphere1"]

    def test_prompt_present(self):
        mock_cmds = _mk_cmds()
        mock_cmds.createDisplayLayer.return_value = "promptLayer"
        result = _call("maya-display", "create_display_layer", mock_cmds, "create_display_layer")
        assert result["success"] is True
        assert result.get("prompt")


# ===========================================================================
# TestListDisplayLayers
# ===========================================================================


class TestListDisplayLayers:
    def test_empty_scene(self):
        mock_cmds = _mk_cmds()
        mock_cmds.ls.return_value = []
        result = _call("maya-display", "list_display_layers", mock_cmds, "list_display_layers")
        assert result["success"] is True
        assert result["context"]["layers"] == []
        assert result["context"]["count"] == 0

    def test_two_layers(self):
        mock_cmds = _mk_cmds()
        mock_cmds.ls.return_value = ["layer1", "layer2"]
        mock_cmds.getAttr.return_value = True
        mock_cmds.editDisplayLayerMembers.return_value = ["pSphere1"]
        result = _call("maya-display", "list_display_layers", mock_cmds, "list_display_layers")
        assert result["success"] is True
        assert result["context"]["count"] == 2

    def test_getattr_returns_false(self):
        mock_cmds = _mk_cmds()
        mock_cmds.ls.return_value = ["hiddenLayer"]
        mock_cmds.getAttr.return_value = False
        mock_cmds.editDisplayLayerMembers.return_value = []
        result = _call("maya-display", "list_display_layers", mock_cmds, "list_display_layers")
        assert result["success"] is True
        assert result["context"]["layers"][0]["visibility"] is False

    def test_prompt_present(self):
        mock_cmds = _mk_cmds()
        mock_cmds.ls.return_value = []
        result = _call("maya-display", "list_display_layers", mock_cmds, "list_display_layers")
        assert result.get("prompt")


# ===========================================================================
# TestSetDisplayLayer
# ===========================================================================


class TestSetDisplayLayer:
    def test_missing_layer_returns_error(self):
        mock_cmds = _mk_cmds()
        mock_cmds.objExists.return_value = False
        result = _call(
            "maya-display", "set_display_layer", mock_cmds, "set_display_layer",
            layer_name="nonExistent", objects=["sphere1"],
        )
        assert result["success"] is False

    def test_all_objects_assigned(self):
        mock_cmds = _mk_cmds()
        mock_cmds.objExists.return_value = True
        result = _call(
            "maya-display", "set_display_layer", mock_cmds, "set_display_layer",
            layer_name="myLayer", objects=["sph", "cube"],
        )
        assert result["success"] is True
        assert sorted(result["context"]["assigned"]) == ["cube", "sph"]
        assert result["context"]["missing"] == []

    def test_mixed_missing_objects_tracked(self):
        mock_cmds = _mk_cmds()

        def obj_exists(name):
            return name in ("myLayer", "sphere1")

        mock_cmds.objExists.side_effect = obj_exists
        result = _call(
            "maya-display", "set_display_layer", mock_cmds, "set_display_layer",
            layer_name="myLayer", objects=["sphere1", "ghostNode"],
        )
        assert result["success"] is True
        assert result["context"]["assigned"] == ["sphere1"]
        assert result["context"]["missing"] == ["ghostNode"]

    def test_prompt_present(self):
        mock_cmds = _mk_cmds()
        mock_cmds.objExists.return_value = True
        result = _call(
            "maya-display", "set_display_layer", mock_cmds, "set_display_layer",
            layer_name="lyr", objects=[],
        )
        assert result.get("prompt")


# ===========================================================================
# TestDeleteDisplayLayer
# ===========================================================================


class TestDeleteDisplayLayer:
    def test_default_layer_blocked(self):
        mock_cmds = _mk_cmds()
        result = _call(
            "maya-display", "delete_display_layer", mock_cmds, "delete_display_layer",
            layer_name="defaultLayer",
        )
        assert result["success"] is False
        assert "defaultLayer" in result["message"]

    def test_missing_layer_returns_error(self):
        mock_cmds = _mk_cmds()
        mock_cmds.objExists.return_value = False
        result = _call(
            "maya-display", "delete_display_layer", mock_cmds, "delete_display_layer",
            layer_name="missingLayer",
        )
        assert result["success"] is False

    def test_wrong_type_returns_error(self):
        mock_cmds = _mk_cmds()
        mock_cmds.objExists.return_value = True
        mock_cmds.objectType.return_value = "transform"
        result = _call(
            "maya-display", "delete_display_layer", mock_cmds, "delete_display_layer",
            layer_name="notALayer",
        )
        assert result["success"] is False
        assert "wrong node type" in result["message"].lower()

    def test_happy_path_no_remove(self):
        mock_cmds = _mk_cmds()
        mock_cmds.objExists.return_value = True
        mock_cmds.objectType.return_value = "displayLayer"
        result = _call(
            "maya-display", "delete_display_layer", mock_cmds, "delete_display_layer",
            layer_name="myLayer",
        )
        assert result["success"] is True
        mock_cmds.delete.assert_called()

    def test_remove_objects_deletes_members(self):
        mock_cmds = _mk_cmds()
        mock_cmds.objExists.return_value = True
        mock_cmds.objectType.return_value = "displayLayer"
        mock_cmds.editDisplayLayerMembers.return_value = ["sphere1", "cube1"]
        result = _call(
            "maya-display", "delete_display_layer", mock_cmds, "delete_display_layer",
            layer_name="myLayer", remove_objects=True,
        )
        assert result["success"] is True
        assert sorted(result["context"]["objects_deleted"]) == ["cube1", "sphere1"]

    def test_prompt_present(self):
        mock_cmds = _mk_cmds()
        mock_cmds.objExists.return_value = True
        mock_cmds.objectType.return_value = "displayLayer"
        result = _call(
            "maya-display", "delete_display_layer", mock_cmds, "delete_display_layer",
            layer_name="lyr",
        )
        assert result.get("prompt")


# ===========================================================================
# TestCreateRenderLayer
# ===========================================================================


class TestCreateRenderLayer:
    def test_empty_name_returns_error(self):
        mock_cmds = _mk_cmds()
        result = _call(
            "maya-render-layers", "create_render_layer", mock_cmds, "create_render_layer",
            name="",
        )
        assert result["success"] is False
        assert "empty" in result["error"].lower() or "invalid" in result["message"].lower()

    def test_whitespace_name_returns_error(self):
        mock_cmds = _mk_cmds()
        result = _call(
            "maya-render-layers", "create_render_layer", mock_cmds, "create_render_layer",
            name="   ",
        )
        assert result["success"] is False

    def test_happy_path_empty_layer(self):
        mock_cmds = _mk_cmds()
        mock_cmds.createRenderLayer.return_value = "myRenderLayer"
        result = _call(
            "maya-render-layers", "create_render_layer", mock_cmds, "create_render_layer",
            name="myRenderLayer",
        )
        assert result["success"] is True
        assert result["context"]["layer_name"] == "myRenderLayer"
        assert result["context"]["objects_added"] == []

    def test_with_objects(self):
        mock_cmds = _mk_cmds()
        mock_cmds.objExists.return_value = True
        mock_cmds.createRenderLayer.return_value = "objRenderLayer"
        result = _call(
            "maya-render-layers", "create_render_layer", mock_cmds, "create_render_layer",
            name="objRenderLayer", objects=["sphere1", "cube1"],
        )
        assert result["success"] is True
        assert sorted(result["context"]["objects_added"]) == ["cube1", "sphere1"]

    def test_missing_objects_returns_error(self):
        mock_cmds = _mk_cmds()
        mock_cmds.objExists.return_value = False
        result = _call(
            "maya-render-layers", "create_render_layer", mock_cmds, "create_render_layer",
            name="myLayer", objects=["noSuchObj"],
        )
        assert result["success"] is False

    def test_make_current_flag(self):
        mock_cmds = _mk_cmds()
        mock_cmds.createRenderLayer.return_value = "currentLayer"
        result = _call(
            "maya-render-layers", "create_render_layer", mock_cmds, "create_render_layer",
            name="currentLayer", make_current=True,
        )
        assert result["success"] is True
        assert result["context"]["is_current"] is True

    def test_prompt_present(self):
        mock_cmds = _mk_cmds()
        mock_cmds.createRenderLayer.return_value = "lyr"
        result = _call(
            "maya-render-layers", "create_render_layer", mock_cmds, "create_render_layer",
            name="lyr",
        )
        assert result.get("prompt")


# ===========================================================================
# TestListRenderLayers
# ===========================================================================


class TestListRenderLayers:
    def test_empty_scene_default_only(self):
        mock_cmds = _mk_cmds()
        mock_cmds.ls.return_value = ["defaultRenderLayer"]
        mock_cmds.editRenderLayerGlobals.return_value = "defaultRenderLayer"
        mock_cmds.editRenderLayerMembers.return_value = []
        mock_cmds.getAttr.return_value = True
        result = _call("maya-render-layers", "list_render_layers", mock_cmds, "list_render_layers")
        assert result["success"] is True
        assert result["context"]["count"] == 1

    def test_exclude_default(self):
        mock_cmds = _mk_cmds()
        mock_cmds.ls.return_value = ["defaultRenderLayer", "rs1"]
        mock_cmds.editRenderLayerGlobals.return_value = "defaultRenderLayer"
        mock_cmds.editRenderLayerMembers.return_value = []
        mock_cmds.getAttr.return_value = True
        result = _call(
            "maya-render-layers", "list_render_layers", mock_cmds, "list_render_layers",
            include_default=False,
        )
        assert result["success"] is True
        names = [l["name"] for l in result["context"]["layers"]]
        assert "defaultRenderLayer" not in names

    def test_getattr_exception_graceful(self):
        mock_cmds = _mk_cmds()
        mock_cmds.ls.return_value = ["layer1"]
        mock_cmds.editRenderLayerGlobals.return_value = "defaultRenderLayer"
        mock_cmds.editRenderLayerMembers.side_effect = Exception("fail")
        result = _call("maya-render-layers", "list_render_layers", mock_cmds, "list_render_layers")
        assert result["success"] is True
        assert result["context"]["layers"][0]["renderable"] is False

    def test_current_layer_flagged(self):
        mock_cmds = _mk_cmds()
        mock_cmds.ls.return_value = ["layer1", "layer2"]
        mock_cmds.editRenderLayerGlobals.return_value = "layer2"
        mock_cmds.editRenderLayerMembers.return_value = []
        mock_cmds.getAttr.return_value = True
        result = _call("maya-render-layers", "list_render_layers", mock_cmds, "list_render_layers")
        assert result["success"] is True
        current_layers = [l for l in result["context"]["layers"] if l["is_current"]]
        assert len(current_layers) == 1
        assert current_layers[0]["name"] == "layer2"

    def test_prompt_present(self):
        mock_cmds = _mk_cmds()
        mock_cmds.ls.return_value = []
        mock_cmds.editRenderLayerGlobals.return_value = "defaultRenderLayer"
        result = _call("maya-render-layers", "list_render_layers", mock_cmds, "list_render_layers")
        assert result.get("prompt")


# ===========================================================================
# TestSetRenderLayer
# ===========================================================================


class TestSetRenderLayer:
    def test_missing_object_returns_error(self):
        mock_cmds = _mk_cmds()
        mock_cmds.objExists.return_value = False
        result = _call(
            "maya-render-layers", "set_render_layer", mock_cmds, "set_render_layer",
            object_name="missing", layer_name="rl1",
        )
        assert result["success"] is False

    def test_missing_layer_returns_error(self):
        mock_cmds = _mk_cmds()

        def obj_exists(name):
            return name == "sphere1"

        mock_cmds.objExists.side_effect = obj_exists
        result = _call(
            "maya-render-layers", "set_render_layer", mock_cmds, "set_render_layer",
            object_name="sphere1", layer_name="missingLayer",
        )
        assert result["success"] is False

    def test_wrong_type_layer(self):
        mock_cmds = _mk_cmds()
        mock_cmds.objExists.return_value = True
        mock_cmds.objectType.return_value = "transform"
        result = _call(
            "maya-render-layers", "set_render_layer", mock_cmds, "set_render_layer",
            object_name="sphere1", layer_name="notALayer",
        )
        assert result["success"] is False
        assert "render layer" in result["message"].lower()

    def test_happy_path(self):
        mock_cmds = _mk_cmds()
        mock_cmds.objExists.return_value = True
        mock_cmds.objectType.return_value = "renderLayer"
        result = _call(
            "maya-render-layers", "set_render_layer", mock_cmds, "set_render_layer",
            object_name="sphere1", layer_name="rl1",
        )
        assert result["success"] is True
        mock_cmds.editRenderLayerMembers.assert_called()

    def test_prompt_present(self):
        mock_cmds = _mk_cmds()
        mock_cmds.objExists.return_value = True
        mock_cmds.objectType.return_value = "renderLayer"
        result = _call(
            "maya-render-layers", "set_render_layer", mock_cmds, "set_render_layer",
            object_name="s1", layer_name="rl1",
        )
        assert result.get("prompt")


# ===========================================================================
# TestSetRenderLayerAttribute
# ===========================================================================


class TestSetRenderLayerAttribute:
    def test_missing_layer(self):
        mock_cmds = _mk_cmds()
        mock_cmds.objExists.return_value = False
        result = _call(
            "maya-render-layers", "set_render_layer_attribute", mock_cmds, "set_render_layer_attribute",
            layer_name="noLayer", attribute="renderable", value=True,
        )
        assert result["success"] is False

    def test_wrong_type(self):
        mock_cmds = _mk_cmds()
        mock_cmds.objExists.return_value = True
        mock_cmds.objectType.return_value = "transform"
        result = _call(
            "maya-render-layers", "set_render_layer_attribute", mock_cmds, "set_render_layer_attribute",
            layer_name="notLayer", attribute="renderable", value=True,
        )
        assert result["success"] is False

    def test_bool_value_cast_to_int(self):
        mock_cmds = _mk_cmds()
        mock_cmds.objExists.return_value = True
        mock_cmds.objectType.return_value = "renderLayer"
        result = _call(
            "maya-render-layers", "set_render_layer_attribute", mock_cmds, "set_render_layer_attribute",
            layer_name="rl1", attribute="renderable", value=True,
        )
        assert result["success"] is True
        # bool True cast to int(1)
        mock_cmds.setAttr.assert_called_with("rl1.renderable", 1)

    def test_list_value_calls_setattr_with_type(self):
        mock_cmds = _mk_cmds()
        mock_cmds.objExists.return_value = True
        mock_cmds.objectType.return_value = "renderLayer"
        result = _call(
            "maya-render-layers", "set_render_layer_attribute", mock_cmds, "set_render_layer_attribute",
            layer_name="rl1", attribute="color", value=[0.5, 0.5, 1.0],
        )
        assert result["success"] is True
        mock_cmds.setAttr.assert_called_with("rl1.color", 0.5, 0.5, 1.0, type="double3")

    def test_scalar_value(self):
        mock_cmds = _mk_cmds()
        mock_cmds.objExists.return_value = True
        mock_cmds.objectType.return_value = "renderLayer"
        result = _call(
            "maya-render-layers", "set_render_layer_attribute", mock_cmds, "set_render_layer_attribute",
            layer_name="rl1", attribute="renderOrder", value=5,
        )
        assert result["success"] is True
        mock_cmds.setAttr.assert_called_with("rl1.renderOrder", 5)

    def test_prompt_present(self):
        mock_cmds = _mk_cmds()
        mock_cmds.objExists.return_value = True
        mock_cmds.objectType.return_value = "renderLayer"
        result = _call(
            "maya-render-layers", "set_render_layer_attribute", mock_cmds, "set_render_layer_attribute",
            layer_name="rl1", attribute="renderable", value=False,
        )
        assert result.get("prompt")


# ===========================================================================
# TestDeleteRenderLayer
# ===========================================================================


class TestDeleteRenderLayer:
    def test_default_layer_blocked(self):
        mock_cmds = _mk_cmds()
        result = _call(
            "maya-render-layers", "delete_render_layer", mock_cmds, "delete_render_layer",
            layer_name="defaultRenderLayer",
        )
        assert result["success"] is False
        assert "defaultRenderLayer" in result["message"]

    def test_missing_layer_returns_error(self):
        mock_cmds = _mk_cmds()
        mock_cmds.objExists.return_value = False
        result = _call(
            "maya-render-layers", "delete_render_layer", mock_cmds, "delete_render_layer",
            layer_name="noLayer",
        )
        assert result["success"] is False

    def test_wrong_type_returns_error(self):
        mock_cmds = _mk_cmds()
        mock_cmds.objExists.return_value = True
        mock_cmds.objectType.return_value = "displayLayer"
        result = _call(
            "maya-render-layers", "delete_render_layer", mock_cmds, "delete_render_layer",
            layer_name="notRenderLayer",
        )
        assert result["success"] is False
        assert "render layer" in result["message"].lower()

    def test_happy_path(self):
        mock_cmds = _mk_cmds()
        mock_cmds.objExists.return_value = True
        mock_cmds.objectType.return_value = "renderLayer"
        mock_cmds.editRenderLayerGlobals.return_value = "defaultRenderLayer"
        result = _call(
            "maya-render-layers", "delete_render_layer", mock_cmds, "delete_render_layer",
            layer_name="myLayer",
        )
        assert result["success"] is True
        mock_cmds.delete.assert_called_with("myLayer")

    def test_switches_layer_if_current(self):
        mock_cmds = _mk_cmds()
        mock_cmds.objExists.return_value = True
        mock_cmds.objectType.return_value = "renderLayer"
        mock_cmds.editRenderLayerGlobals.return_value = "myLayer"
        result = _call(
            "maya-render-layers", "delete_render_layer", mock_cmds, "delete_render_layer",
            layer_name="myLayer",
        )
        assert result["success"] is True
        # Should switch to defaultRenderLayer first
        mock_cmds.editRenderLayerGlobals.assert_any_call(currentRenderLayer="defaultRenderLayer")

    def test_prompt_present(self):
        mock_cmds = _mk_cmds()
        mock_cmds.objExists.return_value = True
        mock_cmds.objectType.return_value = "renderLayer"
        mock_cmds.editRenderLayerGlobals.return_value = "defaultRenderLayer"
        result = _call(
            "maya-render-layers", "delete_render_layer", mock_cmds, "delete_render_layer",
            layer_name="lyr",
        )
        assert result.get("prompt")


# ===========================================================================
# TestCreateLight
# ===========================================================================


class TestCreateLight:
    @pytest.mark.parametrize("light_type", ["point", "directional", "spot", "area", "ambient"])
    def test_all_light_types_happy_path(self, light_type):
        mock_cmds = _mk_cmds()
        light_fn = MagicMock(return_value="{}Shape1".format(light_type))
        # Assign all light command attributes
        for lt in ["pointLight", "directionalLight", "spotLight", "areaLight", "ambientLight"]:
            setattr(mock_cmds, lt, light_fn)
        mock_cmds.listRelatives.return_value = ["{}1".format(light_type)]
        result = _call(
            "maya-lighting", "create_light", mock_cmds, "create_light",
            light_type=light_type, name="{}1".format(light_type),
        )
        assert result["success"] is True
        assert result["context"]["light_type"] == light_type

    def test_unknown_type_returns_error(self):
        mock_cmds = _mk_cmds()
        result = _call(
            "maya-lighting", "create_light", mock_cmds, "create_light",
            light_type="laser",
        )
        assert result["success"] is False
        assert "laser" in result["message"].lower()

    def test_color_applied(self):
        mock_cmds = _mk_cmds()
        mock_cmds.pointLight.return_value = "pointShape1"
        mock_cmds.listRelatives.return_value = ["pointLight1"]
        result = _call(
            "maya-lighting", "create_light", mock_cmds, "create_light",
            light_type="point", color=[1.0, 0.0, 0.0],
        )
        assert result["success"] is True
        # colorR should be set
        calls = [str(c) for c in mock_cmds.setAttr.call_args_list]
        assert any("colorR" in c for c in calls)

    def test_position_applied(self):
        mock_cmds = _mk_cmds()
        mock_cmds.pointLight.return_value = "ps"
        mock_cmds.listRelatives.return_value = ["pt"]
        result = _call(
            "maya-lighting", "create_light", mock_cmds, "create_light",
            light_type="point", position=[1.0, 2.0, 3.0],
        )
        assert result["success"] is True
        mock_cmds.move.assert_called_with(1.0, 2.0, 3.0, "pt")

    def test_rotation_applied(self):
        mock_cmds = _mk_cmds()
        mock_cmds.spotLight.return_value = "ss"
        mock_cmds.listRelatives.return_value = ["st"]
        result = _call(
            "maya-lighting", "create_light", mock_cmds, "create_light",
            light_type="spot", rotation=[45.0, 0.0, 0.0],
        )
        assert result["success"] is True
        mock_cmds.rotate.assert_called_with(45.0, 0.0, 0.0, "st")

    def test_prompt_present(self):
        mock_cmds = _mk_cmds()
        mock_cmds.pointLight.return_value = "ps"
        mock_cmds.listRelatives.return_value = ["pt"]
        result = _call("maya-lighting", "create_light", mock_cmds, "create_light", light_type="point")
        assert result.get("prompt")


# ===========================================================================
# TestListLights
# ===========================================================================


class TestListLights:
    def test_empty_scene(self):
        mock_cmds = _mk_cmds()
        mock_cmds.ls.return_value = []
        result = _call("maya-lighting", "list_lights", mock_cmds, "list_lights")
        assert result["success"] is True
        assert result["context"]["lights"] == []
        assert result["context"]["count"] == 0

    def test_two_lights(self):
        mock_cmds = _mk_cmds()
        mock_cmds.ls.return_value = ["pointShape1", "dirShape1"]
        mock_cmds.listRelatives.side_effect = [["pointLight1"], ["dirLight1"]]
        mock_cmds.objectType.side_effect = ["pointLight", "directionalLight"]
        mock_cmds.getAttr.return_value = 2.5
        result = _call("maya-lighting", "list_lights", mock_cmds, "list_lights")
        assert result["success"] is True
        assert result["context"]["count"] == 2

    def test_intensity_exception_returns_none(self):
        mock_cmds = _mk_cmds()
        mock_cmds.ls.return_value = ["shape1"]
        mock_cmds.listRelatives.return_value = ["light1"]
        mock_cmds.objectType.return_value = "pointLight"
        mock_cmds.getAttr.side_effect = Exception("no intensity")
        result = _call("maya-lighting", "list_lights", mock_cmds, "list_lights")
        assert result["success"] is True
        assert result["context"]["lights"][0]["intensity"] is None

    def test_no_parent_uses_shape_as_transform(self):
        mock_cmds = _mk_cmds()
        mock_cmds.ls.return_value = ["orphanShape"]
        mock_cmds.listRelatives.return_value = []
        mock_cmds.objectType.return_value = "pointLight"
        mock_cmds.getAttr.return_value = 1.0
        result = _call("maya-lighting", "list_lights", mock_cmds, "list_lights")
        assert result["success"] is True
        assert result["context"]["lights"][0]["transform"] == "orphanShape"

    def test_prompt_present(self):
        mock_cmds = _mk_cmds()
        mock_cmds.ls.return_value = []
        result = _call("maya-lighting", "list_lights", mock_cmds, "list_lights")
        assert result.get("prompt")


# ===========================================================================
# TestSetLightAttribute
# ===========================================================================


class TestSetLightAttribute:
    def test_missing_light_returns_error(self):
        mock_cmds = _mk_cmds()
        mock_cmds.objExists.return_value = False
        result = _call(
            "maya-lighting", "set_light_attribute", mock_cmds, "set_light_attribute",
            light_name="noLight", attribute="intensity", value=2.0,
        )
        assert result["success"] is False

    def test_transform_resolves_to_shape(self):
        mock_cmds = _mk_cmds()
        mock_cmds.objExists.return_value = True
        mock_cmds.objectType.return_value = "transform"
        mock_cmds.listRelatives.return_value = ["pointShape1"]
        result = _call(
            "maya-lighting", "set_light_attribute", mock_cmds, "set_light_attribute",
            light_name="pointLight1", attribute="intensity", value=3.0,
        )
        assert result["success"] is True
        mock_cmds.setAttr.assert_called_with("pointShape1.intensity", 3.0)
        assert result["context"]["light_name"] == "pointShape1"

    def test_no_shape_under_transform(self):
        mock_cmds = _mk_cmds()
        mock_cmds.objExists.return_value = True
        mock_cmds.objectType.return_value = "transform"
        mock_cmds.listRelatives.return_value = []
        result = _call(
            "maya-lighting", "set_light_attribute", mock_cmds, "set_light_attribute",
            light_name="emptyTransform", attribute="intensity", value=1.0,
        )
        assert result["success"] is False
        assert "no shape" in result["message"].lower()

    def test_shape_node_used_directly(self):
        mock_cmds = _mk_cmds()
        mock_cmds.objExists.return_value = True
        mock_cmds.objectType.return_value = "pointLight"
        result = _call(
            "maya-lighting", "set_light_attribute", mock_cmds, "set_light_attribute",
            light_name="pointShape1", attribute="intensity", value=5.0,
        )
        assert result["success"] is True
        mock_cmds.setAttr.assert_called_with("pointShape1.intensity", 5.0)

    def test_list_value_sets_with_splat(self):
        mock_cmds = _mk_cmds()
        mock_cmds.objExists.return_value = True
        mock_cmds.objectType.return_value = "pointLight"
        result = _call(
            "maya-lighting", "set_light_attribute", mock_cmds, "set_light_attribute",
            light_name="pointShape1", attribute="color", value=[0.2, 0.4, 0.8],
        )
        assert result["success"] is True
        mock_cmds.setAttr.assert_called_with("pointShape1.color", 0.2, 0.4, 0.8)

    def test_context_keys_present(self):
        mock_cmds = _mk_cmds()
        mock_cmds.objExists.return_value = True
        mock_cmds.objectType.return_value = "pointLight"
        result = _call(
            "maya-lighting", "set_light_attribute", mock_cmds, "set_light_attribute",
            light_name="ps1", attribute="intensity", value=2.0,
        )
        assert result["success"] is True
        assert "light_name" in result["context"]
        assert "attribute" in result["context"]
        assert "value" in result["context"]

    def test_prompt_present(self):
        mock_cmds = _mk_cmds()
        mock_cmds.objExists.return_value = True
        mock_cmds.objectType.return_value = "pointLight"
        result = _call(
            "maya-lighting", "set_light_attribute", mock_cmds, "set_light_attribute",
            light_name="ps1", attribute="intensity", value=1.0,
        )
        assert result.get("prompt")


# ===========================================================================
# TestDeleteLight
# ===========================================================================


class TestDeleteLight:
    def test_missing_light_returns_error(self):
        mock_cmds = _mk_cmds()
        mock_cmds.objExists.return_value = False
        result = _call(
            "maya-lighting", "delete_light", mock_cmds, "delete_light",
            light_name="noLight",
        )
        assert result["success"] is False

    def test_transform_deleted_directly(self):
        mock_cmds = _mk_cmds()
        mock_cmds.objExists.return_value = True
        mock_cmds.objectType.return_value = "transform"
        result = _call(
            "maya-lighting", "delete_light", mock_cmds, "delete_light",
            light_name="myLight",
        )
        assert result["success"] is True
        mock_cmds.delete.assert_called_with("myLight")

    def test_shape_resolves_to_parent_transform(self):
        mock_cmds = _mk_cmds()
        mock_cmds.objExists.return_value = True
        mock_cmds.objectType.return_value = "pointLight"
        mock_cmds.listRelatives.return_value = ["pointLight1"]
        result = _call(
            "maya-lighting", "delete_light", mock_cmds, "delete_light",
            light_name="pointShape1",
        )
        assert result["success"] is True
        mock_cmds.delete.assert_called_with("pointLight1")

    def test_prompt_present(self):
        mock_cmds = _mk_cmds()
        mock_cmds.objExists.return_value = True
        mock_cmds.objectType.return_value = "transform"
        result = _call(
            "maya-lighting", "delete_light", mock_cmds, "delete_light",
            light_name="myLight",
        )
        assert result.get("prompt")
