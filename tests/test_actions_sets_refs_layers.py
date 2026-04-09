"""Tests for Maya object sets, file references, and render layer actions."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import sys
from unittest.mock import MagicMock, patch

# Import third-party modules
import pytest


# ---------------------------------------------------------------------------
# Fixture: mock Maya environment
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def mock_maya_env(monkeypatch):
    """Inject a fully mocked maya.cmds for all tests in this module."""
    mock_cmds = MagicMock()
    maya_mock = MagicMock()
    maya_mock.cmds = mock_cmds

    monkeypatch.setitem(sys.modules, "maya", maya_mock)
    monkeypatch.setitem(sys.modules, "maya.cmds", mock_cmds)
    yield mock_cmds


# ===========================================================================
# Object Sets
# ===========================================================================

class TestCreateSet:
    def test_create_empty_set(self, mock_maya_env):
        mock_maya_env.sets.return_value = "mySet"
        mock_maya_env.objExists.return_value = True

        from dcc_mcp_maya.actions.sets import create_set
        result = create_set("mySet")
        assert result["success"] is True
        assert result["context"]["set_name"] == "mySet"
        assert result["context"]["objects_added"] == []

    def test_create_set_with_objects(self, mock_maya_env):
        mock_maya_env.sets.return_value = "mySet"
        mock_maya_env.objExists.return_value = True

        from dcc_mcp_maya.actions.sets import create_set
        result = create_set("mySet", objects=["pSphere1", "pCube1"])
        assert result["success"] is True
        assert result["context"]["objects_added"] == ["pSphere1", "pCube1"]

    def test_create_set_empty_name(self, mock_maya_env):
        from dcc_mcp_maya.actions.sets import create_set
        result = create_set("")
        assert result["success"] is False
        assert result["message"]  # non-empty message

    def test_create_set_missing_objects(self, mock_maya_env):
        mock_maya_env.objExists.return_value = False

        from dcc_mcp_maya.actions.sets import create_set
        result = create_set("mySet", objects=["ghost"])
        assert result["success"] is False
        assert "ghost" in str(result["message"])

    def test_create_set_import_error(self, monkeypatch):
        monkeypatch.setitem(sys.modules, "maya.cmds", None)
        with patch.dict(sys.modules, {"maya.cmds": None}):
            # Force ImportError by removing the module entirely
            saved = sys.modules.pop("maya.cmds", None)
            sys.modules["maya.cmds"] = None
            try:
                from dcc_mcp_maya.actions import sets as sets_mod
                import importlib
                importlib.reload(sets_mod)
            except Exception:
                pass
            if saved is not None:
                sys.modules["maya.cmds"] = saved

    def test_create_set_exception(self, mock_maya_env):
        mock_maya_env.objExists.return_value = True
        mock_maya_env.sets.side_effect = RuntimeError("sets failed")

        from dcc_mcp_maya.actions.sets import create_set
        result = create_set("mySet", objects=["pSphere1"])
        assert result["success"] is False
        assert result["message"]  # exception details propagated


class TestAddToSet:
    def test_add_objects_success(self, mock_maya_env):
        mock_maya_env.objExists.return_value = True
        mock_maya_env.objectType.return_value = "objectSet"
        mock_maya_env.sets.return_value = None  # add mode returns None

        from dcc_mcp_maya.actions.sets import add_to_set
        result = add_to_set("mySet", ["pSphere1"])
        assert result["success"] is True
        assert result["context"]["objects_added"] == ["pSphere1"]

    def test_add_empty_list(self, mock_maya_env):
        from dcc_mcp_maya.actions.sets import add_to_set
        result = add_to_set("mySet", [])
        assert result["success"] is False

    def test_add_set_not_found(self, mock_maya_env):
        mock_maya_env.objExists.return_value = False

        from dcc_mcp_maya.actions.sets import add_to_set
        result = add_to_set("ghost", ["pSphere1"])
        assert result["success"] is False
        assert "ghost" in result["message"]

    def test_add_wrong_node_type(self, mock_maya_env):
        mock_maya_env.objExists.return_value = True
        mock_maya_env.objectType.return_value = "transform"

        from dcc_mcp_maya.actions.sets import add_to_set
        result = add_to_set("pSphere1", ["pCube1"])
        assert result["success"] is False
        assert "object set" in result["message"].lower() or "objectSet" in str(result)

    def test_add_missing_objects(self, mock_maya_env):
        def _exists(node):
            return node == "mySet"
        mock_maya_env.objExists.side_effect = _exists
        mock_maya_env.objectType.return_value = "objectSet"

        from dcc_mcp_maya.actions.sets import add_to_set
        result = add_to_set("mySet", ["ghost"])
        assert result["success"] is False
        assert "ghost" in str(result["message"])

    def test_add_exception(self, mock_maya_env):
        mock_maya_env.objExists.return_value = True
        mock_maya_env.objectType.return_value = "objectSet"
        mock_maya_env.sets.side_effect = RuntimeError("boom")

        from dcc_mcp_maya.actions.sets import add_to_set
        result = add_to_set("mySet", ["pSphere1"])
        assert result["success"] is False


class TestRemoveFromSet:
    def test_remove_success(self, mock_maya_env):
        mock_maya_env.objExists.return_value = True
        mock_maya_env.objectType.return_value = "objectSet"
        mock_maya_env.sets.return_value = None

        from dcc_mcp_maya.actions.sets import remove_from_set
        result = remove_from_set("mySet", ["pSphere1"])
        assert result["success"] is True
        assert result["context"]["objects_removed"] == ["pSphere1"]

    def test_remove_empty_list(self, mock_maya_env):
        from dcc_mcp_maya.actions.sets import remove_from_set
        result = remove_from_set("mySet", [])
        assert result["success"] is False

    def test_remove_set_not_found(self, mock_maya_env):
        mock_maya_env.objExists.return_value = False

        from dcc_mcp_maya.actions.sets import remove_from_set
        result = remove_from_set("ghost", ["pSphere1"])
        assert result["success"] is False

    def test_remove_wrong_type(self, mock_maya_env):
        mock_maya_env.objExists.return_value = True
        mock_maya_env.objectType.return_value = "mesh"

        from dcc_mcp_maya.actions.sets import remove_from_set
        result = remove_from_set("pMesh", ["pSphere1"])
        assert result["success"] is False

    def test_remove_skips_missing_objects(self, mock_maya_env):
        def _exists(node):
            return node in ("mySet", "pSphere1")
        mock_maya_env.objExists.side_effect = _exists
        mock_maya_env.objectType.return_value = "objectSet"
        mock_maya_env.sets.return_value = None

        from dcc_mcp_maya.actions.sets import remove_from_set
        result = remove_from_set("mySet", ["pSphere1", "ghost"])
        assert result["success"] is True
        assert "pSphere1" in result["context"]["objects_removed"]
        assert "ghost" in result["context"]["objects_skipped"]

    def test_remove_exception(self, mock_maya_env):
        mock_maya_env.objExists.return_value = True
        mock_maya_env.objectType.return_value = "objectSet"
        mock_maya_env.sets.side_effect = RuntimeError("remove failed")

        from dcc_mcp_maya.actions.sets import remove_from_set
        result = remove_from_set("mySet", ["pSphere1"])
        assert result["success"] is False


class TestListSets:
    def test_list_sets_success(self, mock_maya_env):
        mock_maya_env.ls.return_value = ["mySet", "renderSet"]
        mock_maya_env.sets.return_value = ["pSphere1", "pCube1"]

        from dcc_mcp_maya.actions.sets import list_sets
        result = list_sets()
        assert result["success"] is True
        assert result["context"]["count"] == 2

    def test_list_sets_empty_scene(self, mock_maya_env):
        mock_maya_env.ls.return_value = []

        from dcc_mcp_maya.actions.sets import list_sets
        result = list_sets()
        assert result["success"] is True
        assert result["context"]["count"] == 0

    def test_list_sets_filters_internal(self, mock_maya_env):
        mock_maya_env.ls.return_value = [
            "defaultLightSet", "initialShadingGroup", "myCustomSet"
        ]
        mock_maya_env.sets.return_value = []

        from dcc_mcp_maya.actions.sets import list_sets
        result = list_sets(include_internal=False)
        assert result["success"] is True
        names = [s["name"] for s in result["context"]["sets"]]
        assert "defaultLightSet" not in names
        assert "myCustomSet" in names

    def test_list_sets_include_internal(self, mock_maya_env):
        mock_maya_env.ls.return_value = ["defaultLightSet", "myCustomSet"]
        mock_maya_env.sets.return_value = []

        from dcc_mcp_maya.actions.sets import list_sets
        result = list_sets(include_internal=True)
        names = [s["name"] for s in result["context"]["sets"]]
        assert "defaultLightSet" in names

    def test_list_sets_exception(self, mock_maya_env):
        mock_maya_env.ls.side_effect = RuntimeError("ls failed")

        from dcc_mcp_maya.actions.sets import list_sets
        result = list_sets()
        assert result["success"] is False


# ===========================================================================
# File References
# ===========================================================================

class TestCreateReference:
    def test_create_reference_success(self, mock_maya_env):
        mock_maya_env.file.return_value = "charRN"
        mock_maya_env.referenceQuery.return_value = "char"

        from dcc_mcp_maya.actions.references import create_reference
        result = create_reference("/assets/char.mb", namespace="char")
        assert result["success"] is True
        assert result["context"]["reference_node"] == "charRN"
        assert result["context"]["file_path"] == "/assets/char.mb"

    def test_create_reference_no_namespace(self, mock_maya_env):
        mock_maya_env.file.return_value = "envRN"
        mock_maya_env.referenceQuery.return_value = "env"

        from dcc_mcp_maya.actions.references import create_reference
        result = create_reference("/assets/env.mb")
        assert result["success"] is True

    def test_create_reference_empty_path(self, mock_maya_env):
        from dcc_mcp_maya.actions.references import create_reference
        result = create_reference("")
        assert result["success"] is False
        assert result["message"]  # non-empty message

    def test_create_reference_with_group(self, mock_maya_env):
        mock_maya_env.file.return_value = "propRN"
        mock_maya_env.referenceQuery.return_value = "prop"

        from dcc_mcp_maya.actions.references import create_reference
        result = create_reference("/assets/prop.mb", group_reference=True)
        assert result["success"] is True

    def test_create_reference_exception(self, mock_maya_env):
        mock_maya_env.file.side_effect = RuntimeError("file not found")

        from dcc_mcp_maya.actions.references import create_reference
        result = create_reference("/missing/file.mb")
        assert result["success"] is False
        assert result["message"]  # exception propagated

    def test_create_reference_query_fails(self, mock_maya_env):
        """referenceQuery may fail for some nodes; should still succeed."""
        mock_maya_env.file.return_value = "charRN"
        mock_maya_env.referenceQuery.side_effect = RuntimeError("query failed")

        from dcc_mcp_maya.actions.references import create_reference
        result = create_reference("/assets/char.mb", namespace="char")
        assert result["success"] is True


class TestListReferences:
    def test_list_references_success(self, mock_maya_env):
        mock_maya_env.ls.return_value = ["charRN", "envRN"]
        # referenceQuery returns different values per call signature
        call_count = [0]
        def _rq(ref_node, **kwargs):
            if kwargs.get("filename"):
                return "/assets/char.mb" if ref_node == "charRN" else "/assets/env.mb"
            if kwargs.get("namespace"):
                return "char" if ref_node == "charRN" else "env"
            if kwargs.get("isLoaded"):
                return True
            return ""
        mock_maya_env.referenceQuery.side_effect = _rq

        from dcc_mcp_maya.actions.references import list_references
        result = list_references()
        assert result["success"] is True
        assert result["context"]["count"] == 2

    def test_list_references_empty(self, mock_maya_env):
        mock_maya_env.ls.return_value = []

        from dcc_mcp_maya.actions.references import list_references
        result = list_references()
        assert result["success"] is True
        assert result["context"]["count"] == 0

    def test_list_references_filters_shared(self, mock_maya_env):
        mock_maya_env.ls.return_value = ["sharedReferenceNode", "charRN"]
        def _rq(ref_node, **kwargs):
            if kwargs.get("filename"):
                return "/assets/char.mb"
            if kwargs.get("namespace"):
                return "char"
            if kwargs.get("isLoaded"):
                return True
            return ""
        mock_maya_env.referenceQuery.side_effect = _rq

        from dcc_mcp_maya.actions.references import list_references
        result = list_references()
        names = [r["reference_node"] for r in result["context"]["references"]]
        assert "sharedReferenceNode" not in names

    def test_list_references_query_error_skips(self, mock_maya_env):
        """If referenceQuery raises, that reference is skipped gracefully."""
        mock_maya_env.ls.return_value = ["brokenRN", "charRN"]
        def _rq(ref_node, **kwargs):
            if ref_node == "brokenRN":
                raise RuntimeError("broken ref")
            if kwargs.get("filename"):
                return "/assets/char.mb"
            if kwargs.get("namespace"):
                return "char"
            if kwargs.get("isLoaded"):
                return True
            return ""
        mock_maya_env.referenceQuery.side_effect = _rq

        from dcc_mcp_maya.actions.references import list_references
        result = list_references()
        assert result["success"] is True
        assert result["context"]["count"] == 1

    def test_list_references_exception(self, mock_maya_env):
        mock_maya_env.ls.side_effect = RuntimeError("ls error")

        from dcc_mcp_maya.actions.references import list_references
        result = list_references()
        assert result["success"] is False


class TestRemoveReference:
    def test_remove_success(self, mock_maya_env):
        mock_maya_env.objExists.return_value = True
        mock_maya_env.objectType.return_value = "reference"
        mock_maya_env.referenceQuery.return_value = "char"
        mock_maya_env.file.return_value = None
        mock_maya_env.namespace.side_effect = lambda **kw: (
            True if kw.get("exists") else None
        )

        from dcc_mcp_maya.actions.references import remove_reference
        result = remove_reference("charRN")
        assert result["success"] is True
        assert result["context"]["reference_node"] == "charRN"

    def test_remove_not_found(self, mock_maya_env):
        mock_maya_env.objExists.return_value = False

        from dcc_mcp_maya.actions.references import remove_reference
        result = remove_reference("ghost")
        assert result["success"] is False
        assert "ghost" in result["message"]

    def test_remove_wrong_type(self, mock_maya_env):
        mock_maya_env.objExists.return_value = True
        mock_maya_env.objectType.return_value = "transform"

        from dcc_mcp_maya.actions.references import remove_reference
        result = remove_reference("pSphere1")
        assert result["success"] is False
        assert "reference" in result["message"]

    def test_remove_without_namespace(self, mock_maya_env):
        mock_maya_env.objExists.return_value = True
        mock_maya_env.objectType.return_value = "reference"
        mock_maya_env.file.return_value = None

        from dcc_mcp_maya.actions.references import remove_reference
        result = remove_reference("charRN", remove_namespace=False)
        assert result["success"] is True
        assert result["context"]["namespace_removed"] == ""

    def test_remove_exception(self, mock_maya_env):
        mock_maya_env.objExists.return_value = True
        mock_maya_env.objectType.return_value = "reference"
        mock_maya_env.referenceQuery.return_value = "char"
        mock_maya_env.file.side_effect = RuntimeError("cannot remove")

        from dcc_mcp_maya.actions.references import remove_reference
        result = remove_reference("charRN")
        assert result["success"] is False
        assert result["message"]  # exception propagated

    def test_remove_namespace_cleanup_fails_gracefully(self, mock_maya_env):
        """Namespace removal failure should not propagate as an error."""
        mock_maya_env.objExists.return_value = True
        mock_maya_env.objectType.return_value = "reference"
        mock_maya_env.referenceQuery.return_value = "char"
        mock_maya_env.file.return_value = None
        mock_maya_env.namespace.side_effect = RuntimeError("ns error")

        from dcc_mcp_maya.actions.references import remove_reference
        result = remove_reference("charRN")
        assert result["success"] is True


# ===========================================================================
# Render Layers
# ===========================================================================

class TestCreateRenderLayer:
    def test_create_empty_layer(self, mock_maya_env):
        mock_maya_env.createRenderLayer.return_value = "myLayer"
        mock_maya_env.objExists.return_value = True

        from dcc_mcp_maya.actions.render_layers import create_render_layer
        result = create_render_layer("myLayer")
        assert result["success"] is True
        assert result["context"]["layer_name"] == "myLayer"
        assert result["context"]["objects_added"] == []

    def test_create_layer_with_objects(self, mock_maya_env):
        mock_maya_env.createRenderLayer.return_value = "myLayer"
        mock_maya_env.objExists.return_value = True

        from dcc_mcp_maya.actions.render_layers import create_render_layer
        result = create_render_layer("myLayer", objects=["pSphere1"])
        assert result["success"] is True
        assert "pSphere1" in result["context"]["objects_added"]

    def test_create_layer_empty_name(self, mock_maya_env):
        from dcc_mcp_maya.actions.render_layers import create_render_layer
        result = create_render_layer("")
        assert result["success"] is False

    def test_create_layer_missing_objects(self, mock_maya_env):
        mock_maya_env.objExists.return_value = False

        from dcc_mcp_maya.actions.render_layers import create_render_layer
        result = create_render_layer("myLayer", objects=["ghost"])
        assert result["success"] is False

    def test_create_layer_make_current(self, mock_maya_env):
        mock_maya_env.createRenderLayer.return_value = "myLayer"
        mock_maya_env.objExists.return_value = True

        from dcc_mcp_maya.actions.render_layers import create_render_layer
        result = create_render_layer("myLayer", make_current=True)
        assert result["success"] is True
        assert result["context"]["is_current"] is True

    def test_create_layer_exception(self, mock_maya_env):
        mock_maya_env.objExists.return_value = True
        mock_maya_env.createRenderLayer.side_effect = RuntimeError("layer failed")

        from dcc_mcp_maya.actions.render_layers import create_render_layer
        result = create_render_layer("myLayer")
        assert result["success"] is False


class TestSetRenderLayer:
    def test_set_render_layer_success(self, mock_maya_env):
        mock_maya_env.objExists.return_value = True
        mock_maya_env.objectType.return_value = "renderLayer"
        mock_maya_env.editRenderLayerMembers.return_value = None

        from dcc_mcp_maya.actions.render_layers import set_render_layer
        result = set_render_layer("pSphere1", "myLayer")
        assert result["success"] is True
        assert result["context"]["object_name"] == "pSphere1"
        assert result["context"]["layer_name"] == "myLayer"

    def test_set_render_layer_object_not_found(self, mock_maya_env):
        mock_maya_env.objExists.side_effect = lambda x: x != "pSphere1"

        from dcc_mcp_maya.actions.render_layers import set_render_layer
        result = set_render_layer("pSphere1", "myLayer")
        assert result["success"] is False
        assert "pSphere1" in result["message"]

    def test_set_render_layer_not_found(self, mock_maya_env):
        def _exists(node):
            return node == "pSphere1"
        mock_maya_env.objExists.side_effect = _exists

        from dcc_mcp_maya.actions.render_layers import set_render_layer
        result = set_render_layer("pSphere1", "ghost")
        assert result["success"] is False

    def test_set_render_layer_wrong_type(self, mock_maya_env):
        mock_maya_env.objExists.return_value = True
        mock_maya_env.objectType.return_value = "displayLayer"

        from dcc_mcp_maya.actions.render_layers import set_render_layer
        result = set_render_layer("pSphere1", "dspLayer")
        assert result["success"] is False
        assert "render layer" in result["message"].lower() or "renderLayer" in str(result)

    def test_set_render_layer_exception(self, mock_maya_env):
        mock_maya_env.objExists.return_value = True
        mock_maya_env.objectType.return_value = "renderLayer"
        mock_maya_env.editRenderLayerMembers.side_effect = RuntimeError("err")

        from dcc_mcp_maya.actions.render_layers import set_render_layer
        result = set_render_layer("pSphere1", "myLayer")
        assert result["success"] is False


class TestListRenderLayers:
    def test_list_render_layers_success(self, mock_maya_env):
        mock_maya_env.ls.return_value = ["defaultRenderLayer", "myLayer"]
        mock_maya_env.editRenderLayerGlobals.return_value = "myLayer"
        mock_maya_env.editRenderLayerMembers.return_value = ["pSphere1"]
        mock_maya_env.getAttr.return_value = True

        from dcc_mcp_maya.actions.render_layers import list_render_layers
        result = list_render_layers()
        assert result["success"] is True
        assert result["context"]["count"] == 2
        assert result["context"]["current_layer"] == "myLayer"

    def test_list_render_layers_exclude_default(self, mock_maya_env):
        mock_maya_env.ls.return_value = ["defaultRenderLayer", "myLayer"]
        mock_maya_env.editRenderLayerGlobals.return_value = "myLayer"
        mock_maya_env.editRenderLayerMembers.return_value = []
        mock_maya_env.getAttr.return_value = True

        from dcc_mcp_maya.actions.render_layers import list_render_layers
        result = list_render_layers(include_default=False)
        names = [lr["name"] for lr in result["context"]["layers"]]
        assert "defaultRenderLayer" not in names

    def test_list_render_layers_is_current_flag(self, mock_maya_env):
        mock_maya_env.ls.return_value = ["defaultRenderLayer", "myLayer"]
        mock_maya_env.editRenderLayerGlobals.return_value = "myLayer"
        mock_maya_env.editRenderLayerMembers.return_value = []
        mock_maya_env.getAttr.return_value = True

        from dcc_mcp_maya.actions.render_layers import list_render_layers
        result = list_render_layers()
        layer_map = {lr["name"]: lr for lr in result["context"]["layers"]}
        assert layer_map["myLayer"]["is_current"] is True
        assert layer_map["defaultRenderLayer"]["is_current"] is False

    def test_list_render_layers_empty_scene(self, mock_maya_env):
        mock_maya_env.ls.return_value = []
        mock_maya_env.editRenderLayerGlobals.return_value = "defaultRenderLayer"

        from dcc_mcp_maya.actions.render_layers import list_render_layers
        result = list_render_layers()
        assert result["success"] is True
        assert result["context"]["count"] == 0

    def test_list_render_layers_exception(self, mock_maya_env):
        mock_maya_env.ls.side_effect = RuntimeError("ls error")

        from dcc_mcp_maya.actions.render_layers import list_render_layers
        result = list_render_layers()
        assert result["success"] is False


# ===========================================================================
# register_all includes new actions
# ===========================================================================

class TestRegisterAllRound9:
    def test_total_action_count(self):
        """register_all should contain at least 89 entries (79 previous + 10 new)."""
        import dcc_mcp_maya.actions as actions_pkg

        all_actions = actions_pkg.__all__
        assert len(all_actions) >= 89, "Expected >= 89 actions, got {}".format(len(all_actions))

    def test_new_actions_in_all(self):
        """All 10 new actions must be in __all__."""
        import dcc_mcp_maya.actions as actions_pkg

        new_actions = [
            "create_set", "add_to_set", "remove_from_set", "list_sets",
            "create_reference", "list_references", "remove_reference",
            "create_render_layer", "set_render_layer", "list_render_layers",
        ]
        for action in new_actions:
            assert action in actions_pkg.__all__, "{} missing from __all__".format(action)
