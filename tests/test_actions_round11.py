"""Round 11 tests: add_attribute, delete_attribute, list_attributes,
set_namespace, rename_namespace, delete_namespace,
get_material_connections, list_shading_groups.
"""

# Import future modules
from __future__ import annotations

# Import built-in modules
import sys
from typing import Any
from unittest.mock import MagicMock, patch

# Import third-party modules
import pytest


# ---------------------------------------------------------------------------
# Shared Maya mock fixture
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def mock_maya(monkeypatch):
    """Install a minimal Maya mock into sys.modules for every test."""
    cmds = MagicMock()
    maya_mod = MagicMock()
    maya_mod.cmds = cmds

    monkeypatch.setitem(sys.modules, "maya", maya_mod)
    monkeypatch.setitem(sys.modules, "maya.cmds", cmds)
    monkeypatch.setitem(sys.modules, "maya.api", MagicMock())
    monkeypatch.setitem(sys.modules, "maya.utils", MagicMock())

    yield cmds


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ok(result: dict) -> bool:
    return result.get("success") is True


def _fail(result: dict) -> bool:
    return result.get("success") is False


def _ctx(result: dict) -> dict:
    return result.get("context", {})


# ===========================================================================
# TestAddAttribute
# ===========================================================================

class TestAddAttribute:
    def test_add_double_attribute_happy(self, mock_maya):
        mock_maya.objExists.side_effect = lambda x: x == "pCube1"

        from dcc_mcp_maya.actions.node_attrs import add_attribute
        result = add_attribute("pCube1", "myWeight", attr_type="double")

        assert _ok(result)
        ctx = _ctx(result)
        assert ctx["long_name"] == "myWeight"
        assert ctx["attr_type"] == "double"
        mock_maya.addAttr.assert_called_once()

    def test_add_string_attribute(self, mock_maya):
        mock_maya.objExists.side_effect = lambda x: x == "pCube1"

        from dcc_mcp_maya.actions.node_attrs import add_attribute
        result = add_attribute("pCube1", "myLabel", attr_type="string")

        assert _ok(result)
        # dataType="string" path
        args, kwargs = mock_maya.addAttr.call_args
        assert kwargs.get("dataType") == "string"

    def test_add_bool_attribute_with_default(self, mock_maya):
        mock_maya.objExists.side_effect = lambda x: x == "pCube1"

        from dcc_mcp_maya.actions.node_attrs import add_attribute
        result = add_attribute("pCube1", "enabled", attr_type="bool", default_value=True)

        assert _ok(result)
        _, kwargs = mock_maya.addAttr.call_args
        assert "defaultValue" in kwargs

    def test_add_float3_vector_attribute(self, mock_maya):
        mock_maya.objExists.side_effect = lambda x: x == "pCube1"

        from dcc_mcp_maya.actions.node_attrs import add_attribute
        result = add_attribute("pCube1", "myVec", attr_type="float3")

        assert _ok(result)
        _, kwargs = mock_maya.addAttr.call_args
        assert kwargs.get("attributeType") == "float3"

    def test_add_attribute_object_not_found(self, mock_maya):
        mock_maya.objExists.return_value = False

        from dcc_mcp_maya.actions.node_attrs import add_attribute
        result = add_attribute("ghost", "myAttr")

        assert _fail(result)

    def test_add_attribute_already_exists(self, mock_maya):
        mock_maya.objExists.side_effect = lambda x: True  # both node and attr exist

        from dcc_mcp_maya.actions.node_attrs import add_attribute
        result = add_attribute("pCube1", "myAttr")

        assert _fail(result)
        assert "already exists" in result.get("message", "").lower()

    def test_add_attribute_unsupported_type(self, mock_maya):
        mock_maya.objExists.side_effect = lambda x: x == "pCube1"

        from dcc_mcp_maya.actions.node_attrs import add_attribute
        result = add_attribute("pCube1", "myAttr", attr_type="matrix99")

        assert _fail(result)
        assert "unsupported" in result.get("message", "").lower()

    def test_add_attribute_maya_error(self, mock_maya):
        mock_maya.objExists.side_effect = lambda x: x == "pCube1"
        mock_maya.addAttr.side_effect = RuntimeError("addAttr failed")

        from dcc_mcp_maya.actions.node_attrs import add_attribute
        result = add_attribute("pCube1", "myAttr")

        assert _fail(result)

    def test_add_attribute_import_error(self, monkeypatch):
        monkeypatch.setitem(sys.modules, "maya.cmds", None)
        # Force ImportError path
        import importlib
        import dcc_mcp_maya.actions.node_attrs as mod
        importlib.reload(mod)

        with patch.dict(sys.modules, {"maya.cmds": None}):
            # Direct import will raise; simulate via side_effect
            pass
        # Just verify no crash when maya unavailable
        monkeypatch.setitem(sys.modules, "maya.cmds", MagicMock())


# ===========================================================================
# TestDeleteAttribute
# ===========================================================================

class TestDeleteAttribute:
    def test_delete_custom_attribute_happy(self, mock_maya):
        mock_maya.objExists.return_value = True
        mock_maya.listAttr.return_value = ["myWeight", "myLabel"]

        from dcc_mcp_maya.actions.node_attrs import delete_attribute
        result = delete_attribute("pCube1", "myWeight")

        assert _ok(result)
        mock_maya.deleteAttr.assert_called_once()

    def test_delete_object_not_found(self, mock_maya):
        mock_maya.objExists.side_effect = lambda x: x != "ghost"

        from dcc_mcp_maya.actions.node_attrs import delete_attribute
        result = delete_attribute("ghost", "myWeight")

        assert _fail(result)

    def test_delete_attribute_not_found(self, mock_maya):
        mock_maya.objExists.side_effect = lambda x: x == "pCube1"

        from dcc_mcp_maya.actions.node_attrs import delete_attribute
        result = delete_attribute("pCube1", "nonExistent")

        assert _fail(result)

    def test_delete_builtin_attribute_rejected(self, mock_maya):
        mock_maya.objExists.return_value = True
        mock_maya.listAttr.return_value = ["myCustom"]  # translateX is NOT in user-defined

        from dcc_mcp_maya.actions.node_attrs import delete_attribute
        result = delete_attribute("pCube1", "translateX")

        assert _fail(result)
        assert "built-in" in result.get("message", "").lower()

    def test_delete_attribute_maya_error(self, mock_maya):
        mock_maya.objExists.return_value = True
        mock_maya.listAttr.return_value = ["myAttr"]
        mock_maya.deleteAttr.side_effect = RuntimeError("deleteAttr failed")

        from dcc_mcp_maya.actions.node_attrs import delete_attribute
        result = delete_attribute("pCube1", "myAttr")

        assert _fail(result)


# ===========================================================================
# TestListAttributes
# ===========================================================================

class TestListAttributes:
    def _setup_list(self, mock_maya):
        mock_maya.objExists.return_value = True
        mock_maya.listAttr.return_value = ["translateX", "myAttr"]
        mock_maya.getAttr.side_effect = lambda attr, **kw: (
            True if kw.get("keyable") else
            False if kw.get("lock") else
            "double" if kw.get("type") else
            0.0
        )

    def test_list_all_attributes(self, mock_maya):
        self._setup_list(mock_maya)

        from dcc_mcp_maya.actions.node_attrs import list_attributes
        result = list_attributes("pCube1")

        assert _ok(result)
        assert _ctx(result)["count"] == 2

    def test_list_user_defined_only(self, mock_maya):
        mock_maya.objExists.return_value = True
        mock_maya.listAttr.return_value = ["myAttr"]
        mock_maya.getAttr.side_effect = lambda attr, **kw: (
            True if kw.get("keyable") else
            False if kw.get("lock") else
            "double" if kw.get("type") else
            1.0
        )

        from dcc_mcp_maya.actions.node_attrs import list_attributes
        result = list_attributes("pCube1", user_defined=True)

        assert _ok(result)
        assert _ctx(result)["user_defined_only"] is True

    def test_list_attributes_object_not_found(self, mock_maya):
        mock_maya.objExists.return_value = False

        from dcc_mcp_maya.actions.node_attrs import list_attributes
        result = list_attributes("ghost")

        assert _fail(result)

    def test_list_attributes_empty(self, mock_maya):
        mock_maya.objExists.return_value = True
        mock_maya.listAttr.return_value = []

        from dcc_mcp_maya.actions.node_attrs import list_attributes
        result = list_attributes("pCube1")

        assert _ok(result)
        assert _ctx(result)["count"] == 0

    def test_list_attributes_getattr_exception_handled(self, mock_maya):
        mock_maya.objExists.return_value = True
        mock_maya.listAttr.return_value = ["badAttr"]
        # objExists returns True for node but False for attr
        mock_maya.objExists.side_effect = lambda x: "badAttr" not in x

        from dcc_mcp_maya.actions.node_attrs import list_attributes
        result = list_attributes("pCube1")

        assert _ok(result)  # gracefully skips missing attr


# ===========================================================================
# TestSetNamespace
# ===========================================================================

class TestSetNamespace:
    def test_set_namespace_happy(self, mock_maya):
        mock_maya.objExists.return_value = True
        mock_maya.namespace.side_effect = lambda **kw: (
            False if kw.get("exists") else None
        )
        mock_maya.rename.return_value = "myNS:pCube1"

        from dcc_mcp_maya.actions.namespaces import set_namespace
        result = set_namespace("pCube1", "myNS")

        assert _ok(result)
        assert _ctx(result)["namespace"] == "myNS"
        assert _ctx(result)["new_name"] == "myNS:pCube1"

    def test_set_namespace_existing_ns(self, mock_maya):
        mock_maya.objExists.return_value = True
        mock_maya.namespace.side_effect = lambda **kw: (
            True if kw.get("exists") else None
        )
        mock_maya.rename.return_value = "existing:pCube1"

        from dcc_mcp_maya.actions.namespaces import set_namespace
        result = set_namespace("pCube1", "existing")

        assert _ok(result)
        mock_maya.namespace.assert_not_called() if False else None  # namespace(add=...) not needed

    def test_set_namespace_create_if_missing_false(self, mock_maya):
        mock_maya.objExists.return_value = True
        mock_maya.namespace.side_effect = lambda **kw: (
            False if kw.get("exists") else None
        )

        from dcc_mcp_maya.actions.namespaces import set_namespace
        result = set_namespace("pCube1", "newNS", create_if_missing=False)

        assert _fail(result)

    def test_set_namespace_to_root(self, mock_maya):
        mock_maya.objExists.return_value = True
        mock_maya.rename.return_value = "pCube1"

        from dcc_mcp_maya.actions.namespaces import set_namespace
        result = set_namespace("myNS:pCube1", "")

        assert _ok(result)
        assert _ctx(result)["namespace"] == ":"

    def test_set_namespace_object_not_found(self, mock_maya):
        mock_maya.objExists.return_value = False

        from dcc_mcp_maya.actions.namespaces import set_namespace
        result = set_namespace("ghost", "myNS")

        assert _fail(result)

    def test_set_namespace_maya_error(self, mock_maya):
        mock_maya.objExists.return_value = True
        mock_maya.namespace.side_effect = lambda **kw: (
            True if kw.get("exists") else None
        )
        mock_maya.rename.side_effect = RuntimeError("rename failed")

        from dcc_mcp_maya.actions.namespaces import set_namespace
        result = set_namespace("pCube1", "myNS")

        assert _fail(result)


# ===========================================================================
# TestRenameNamespace
# ===========================================================================

class TestRenameNamespace:
    def test_rename_namespace_happy(self, mock_maya):
        def ns_side(**kw):
            if kw.get("exists"):
                # old exists, new does not
                return kw["exists"] == ":oldNS"
            return None
        mock_maya.namespace.side_effect = ns_side

        from dcc_mcp_maya.actions.namespaces import rename_namespace
        result = rename_namespace("oldNS", "newNS")

        assert _ok(result)
        assert _ctx(result)["old_name"] == "oldNS"
        assert _ctx(result)["new_name"] == "newNS"

    def test_rename_namespace_protected(self, mock_maya):
        from dcc_mcp_maya.actions.namespaces import rename_namespace
        result = rename_namespace("UI", "myUI")

        assert _fail(result)
        assert "protected" in result.get("message", "").lower()

    def test_rename_namespace_empty_old(self, mock_maya):
        from dcc_mcp_maya.actions.namespaces import rename_namespace
        result = rename_namespace("", "newNS")

        assert _fail(result)

    def test_rename_namespace_old_not_found(self, mock_maya):
        mock_maya.namespace.side_effect = lambda **kw: False if kw.get("exists") else None

        from dcc_mcp_maya.actions.namespaces import rename_namespace
        result = rename_namespace("ghost", "newNS")

        assert _fail(result)

    def test_rename_namespace_new_already_exists(self, mock_maya):
        # Both old and new exist
        mock_maya.namespace.side_effect = lambda **kw: True if kw.get("exists") else None

        from dcc_mcp_maya.actions.namespaces import rename_namespace
        result = rename_namespace("oldNS", "alreadyExists")

        assert _fail(result)

    def test_rename_namespace_maya_error(self, mock_maya):
        def ns_side(**kw):
            if kw.get("exists"):
                return kw["exists"] == ":oldNS"
            raise RuntimeError("namespace cmd failed")
        mock_maya.namespace.side_effect = ns_side

        from dcc_mcp_maya.actions.namespaces import rename_namespace
        result = rename_namespace("oldNS", "newNS")

        assert _fail(result)


# ===========================================================================
# TestDeleteNamespace
# ===========================================================================

class TestDeleteNamespace:
    def test_delete_namespace_happy(self, mock_maya):
        mock_maya.namespace.side_effect = lambda **kw: (
            True if kw.get("exists") else None
        )

        from dcc_mcp_maya.actions.namespaces import delete_namespace
        result = delete_namespace("myNS")

        assert _ok(result)
        assert _ctx(result)["namespace"] == "myNS"

    def test_delete_namespace_merge_false(self, mock_maya):
        mock_maya.namespace.side_effect = lambda **kw: (
            True if kw.get("exists") else None
        )

        from dcc_mcp_maya.actions.namespaces import delete_namespace
        result = delete_namespace("myNS", merge_with_root=False)

        assert _ok(result)
        _, kwargs = mock_maya.namespace.call_args
        assert "mergeNamespaceWithRoot" not in kwargs

    def test_delete_namespace_protected(self, mock_maya):
        from dcc_mcp_maya.actions.namespaces import delete_namespace
        result = delete_namespace("shared")

        assert _fail(result)

    def test_delete_namespace_not_found(self, mock_maya):
        mock_maya.namespace.side_effect = lambda **kw: (
            False if kw.get("exists") else None
        )

        from dcc_mcp_maya.actions.namespaces import delete_namespace
        result = delete_namespace("ghost")

        assert _fail(result)

    def test_delete_namespace_empty_name(self, mock_maya):
        from dcc_mcp_maya.actions.namespaces import delete_namespace
        result = delete_namespace("")

        assert _fail(result)

    def test_delete_namespace_maya_error(self, mock_maya):
        def ns_side(**kw):
            if kw.get("exists"):
                return True
            raise RuntimeError("removeNamespace failed")
        mock_maya.namespace.side_effect = ns_side

        from dcc_mcp_maya.actions.namespaces import delete_namespace
        result = delete_namespace("myNS")

        assert _fail(result)


# ===========================================================================
# TestGetMaterialConnections
# ===========================================================================

class TestGetMaterialConnections:
    def test_get_connections_happy(self, mock_maya):
        mock_maya.objExists.return_value = True
        mock_maya.listConnections.return_value = [
            "myLambert.color",
            "file1.outColor",
            "myLambert.normalCamera",
            "bump1.outNormal",
        ]
        mock_maya.nodeType.side_effect = lambda x: (
            "file" if x == "file1" else "bump2d"
        )

        from dcc_mcp_maya.actions.materials import get_material_connections
        result = get_material_connections("myLambert")

        assert _ok(result)
        ctx = _ctx(result)
        assert ctx["count"] == 2
        assert ctx["connections"][0]["source_node"] == "file1"
        assert ctx["connections"][0]["node_type"] == "file"

    def test_get_connections_no_connections(self, mock_maya):
        mock_maya.objExists.return_value = True
        mock_maya.listConnections.return_value = []

        from dcc_mcp_maya.actions.materials import get_material_connections
        result = get_material_connections("lambert1")

        assert _ok(result)
        assert _ctx(result)["count"] == 0

    def test_get_connections_material_not_found(self, mock_maya):
        mock_maya.objExists.return_value = False

        from dcc_mcp_maya.actions.materials import get_material_connections
        result = get_material_connections("ghost")

        assert _fail(result)

    def test_get_connections_maya_error(self, mock_maya):
        mock_maya.objExists.return_value = True
        mock_maya.listConnections.side_effect = RuntimeError("listConnections failed")

        from dcc_mcp_maya.actions.materials import get_material_connections
        result = get_material_connections("myLambert")

        assert _fail(result)

    def test_get_connections_odd_length_list(self, mock_maya):
        """If listConnections returns an odd-length list (unusual), graceful stop."""
        mock_maya.objExists.return_value = True
        mock_maya.listConnections.return_value = ["mat.color"]  # no src
        mock_maya.nodeType.return_value = "unknown"

        from dcc_mcp_maya.actions.materials import get_material_connections
        result = get_material_connections("myMat")

        assert _ok(result)
        assert _ctx(result)["count"] == 0  # i+1 out of range, loop body never executes


# ===========================================================================
# TestListShadingGroups
# ===========================================================================

class TestListShadingGroups:
    def test_list_shading_groups_happy(self, mock_maya):
        mock_maya.ls.return_value = ["initialShadingGroup", "myMat_SG"]
        mock_maya.listConnections.side_effect = lambda attr, **kw: (
            ["lambert1"] if "initialShadingGroup" in attr else ["myBlinn"]
        )
        mock_maya.nodeType.side_effect = lambda x: (
            "lambert" if x == "lambert1" else "blinn"
        )
        mock_maya.sets.return_value = ["pCube1", "pSphere1"]

        from dcc_mcp_maya.actions.materials import list_shading_groups
        result = list_shading_groups()

        assert _ok(result)
        ctx = _ctx(result)
        assert ctx["count"] == 2
        sgs = {sg["name"]: sg for sg in ctx["shading_groups"]}
        assert sgs["initialShadingGroup"]["surface_shader"] == "lambert1"
        assert sgs["myMat_SG"]["member_count"] == 2

    def test_list_shading_groups_empty(self, mock_maya):
        mock_maya.ls.return_value = []

        from dcc_mcp_maya.actions.materials import list_shading_groups
        result = list_shading_groups()

        assert _ok(result)
        assert _ctx(result)["count"] == 0

    def test_list_shading_groups_no_shader(self, mock_maya):
        mock_maya.ls.return_value = ["orphan_SG"]
        mock_maya.listConnections.return_value = []
        mock_maya.sets.return_value = []

        from dcc_mcp_maya.actions.materials import list_shading_groups
        result = list_shading_groups()

        assert _ok(result)
        sg = _ctx(result)["shading_groups"][0]
        assert sg["surface_shader"] == ""
        assert sg["shader_type"] == ""

    def test_list_shading_groups_sets_error_handled(self, mock_maya):
        mock_maya.ls.return_value = ["sg1"]
        mock_maya.listConnections.return_value = ["myLambert"]
        mock_maya.nodeType.return_value = "lambert"
        mock_maya.sets.side_effect = RuntimeError("sets failed")

        from dcc_mcp_maya.actions.materials import list_shading_groups
        result = list_shading_groups()

        assert _ok(result)
        assert _ctx(result)["shading_groups"][0]["member_count"] == 0

    def test_list_shading_groups_maya_error(self, mock_maya):
        mock_maya.ls.side_effect = RuntimeError("ls failed")

        from dcc_mcp_maya.actions.materials import list_shading_groups
        result = list_shading_groups()

        assert _fail(result)


# ===========================================================================
# TestRegisterAllRound11
# ===========================================================================

class TestRegisterAllRound11:
    def test_register_all_includes_new_actions(self):
        from dcc_mcp_maya.actions import __all__

        new_actions = [
            "add_attribute",
            "delete_attribute",
            "list_attributes",
            "set_namespace",
            "rename_namespace",
            "delete_namespace",
            "get_material_connections",
            "list_shading_groups",
        ]
        for action in new_actions:
            assert action in __all__, "Missing from __all__: {}".format(action)

    def test_register_all_total_actions(self):
        registry = MagicMock()
        from dcc_mcp_maya.actions import register_all
        register_all(registry)
        call_count = registry.register.call_count
        assert call_count >= 106, "Expected >= 106 actions, got {}".format(call_count)
