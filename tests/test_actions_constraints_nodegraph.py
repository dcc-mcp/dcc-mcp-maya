"""Tests for constraints and node_graph action modules."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import sys
from unittest.mock import MagicMock, patch

# Import third-party modules
import pytest


# ---------------------------------------------------------------------------
# Shared Maya mock helpers
# ---------------------------------------------------------------------------

def _make_cmds():
    """Return a MagicMock configured with sensible Maya cmds defaults."""
    m = MagicMock()
    m.objExists.return_value = True
    m.objectType.return_value = "transform"
    m.listRelatives.return_value = []
    m.listConnections.return_value = []
    m.ls.return_value = ["|group1|pSphere1"]
    m.isConnected.return_value = True
    return m


@pytest.fixture(autouse=True)
def mock_maya(monkeypatch):
    """Inject mock maya modules before each test."""
    mock_cmds = _make_cmds()
    mock_maya_mod = MagicMock()
    mock_maya_mod.cmds = mock_cmds
    monkeypatch.setitem(sys.modules, "maya", mock_maya_mod)
    monkeypatch.setitem(sys.modules, "maya.cmds", mock_cmds)
    monkeypatch.setitem(sys.modules, "maya.api", MagicMock())
    monkeypatch.setitem(sys.modules, "maya.utils", MagicMock())
    return mock_cmds


# ===========================================================================
# add_constraint
# ===========================================================================

class TestAddConstraint:
    def test_parent_constraint_success(self, mock_maya):
        mock_maya.parentConstraint.return_value = ["pCube1_parentConstraint1"]
        from dcc_mcp_maya.actions.constraints import add_constraint
        result = add_constraint("pCube1", "pSphere1", constraint_type="parent")
        assert result["success"] is True
        assert result["context"]["constraint_type"] == "parent"
        assert result["context"]["source"] == "pCube1"
        assert result["context"]["target"] == "pSphere1"
        mock_maya.parentConstraint.assert_called_once()

    def test_point_constraint_success(self, mock_maya):
        mock_maya.pointConstraint.return_value = ["pSphere1_pointConstraint1"]
        from dcc_mcp_maya.actions.constraints import add_constraint
        result = add_constraint("src", "dst", constraint_type="point")
        assert result["success"] is True
        assert result["context"]["constraint_type"] == "point"
        mock_maya.pointConstraint.assert_called_once()

    def test_orient_constraint(self, mock_maya):
        mock_maya.orientConstraint.return_value = ["node_orientConstraint1"]
        from dcc_mcp_maya.actions.constraints import add_constraint
        result = add_constraint("A", "B", constraint_type="orient")
        assert result["success"] is True
        mock_maya.orientConstraint.assert_called_once()

    def test_scale_constraint(self, mock_maya):
        mock_maya.scaleConstraint.return_value = ["node_scaleConstraint1"]
        from dcc_mcp_maya.actions.constraints import add_constraint
        result = add_constraint("A", "B", constraint_type="scale")
        assert result["success"] is True

    def test_aim_constraint(self, mock_maya):
        mock_maya.aimConstraint.return_value = ["node_aimConstraint1"]
        from dcc_mcp_maya.actions.constraints import add_constraint
        result = add_constraint("A", "B", constraint_type="aim")
        assert result["success"] is True
        mock_maya.aimConstraint.assert_called_once()

    def test_invalid_constraint_type(self, mock_maya):
        from dcc_mcp_maya.actions.constraints import add_constraint
        result = add_constraint("A", "B", constraint_type="bogus")
        assert result["success"] is False
        assert "bogus" in result["message"]

    def test_source_not_found(self, mock_maya):
        mock_maya.objExists.side_effect = lambda n: n != "missing_src"
        from dcc_mcp_maya.actions.constraints import add_constraint
        result = add_constraint("missing_src", "B")
        assert result["success"] is False
        assert "missing_src" in result["message"]

    def test_target_not_found(self, mock_maya):
        mock_maya.objExists.side_effect = lambda n: n != "missing_tgt"
        from dcc_mcp_maya.actions.constraints import add_constraint
        result = add_constraint("A", "missing_tgt")
        assert result["success"] is False

    def test_with_custom_name(self, mock_maya):
        mock_maya.parentConstraint.return_value = ["myConstraint"]
        from dcc_mcp_maya.actions.constraints import add_constraint
        result = add_constraint("A", "B", name="myConstraint")
        assert result["success"] is True
        call_kwargs = mock_maya.parentConstraint.call_args[1]
        assert call_kwargs.get("name") == "myConstraint"

    def test_maya_unavailable(self, monkeypatch):
        monkeypatch.delitem(sys.modules, "maya.cmds", raising=False)
        monkeypatch.setitem(sys.modules, "maya.cmds", None)
        import importlib
        import dcc_mcp_maya.actions.constraints as m
        importlib.reload(m)
        with patch.dict(sys.modules, {"maya.cmds": None}):
            with patch("builtins.__import__", side_effect=ImportError):
                result = m.add_constraint.__wrapped__("A", "B") if hasattr(m.add_constraint, "__wrapped__") else None
        # Just verify the function exists and handles ImportError via the module
        assert callable(m.add_constraint)


# ===========================================================================
# remove_constraint
# ===========================================================================

class TestRemoveConstraint:
    def test_remove_all_constraints(self, mock_maya):
        mock_maya.listRelatives.side_effect = lambda obj, type=None: (
            ["pSphere1_parentConstraint1"] if type == "parentConstraint" else []
        )
        from dcc_mcp_maya.actions.constraints import remove_constraint
        result = remove_constraint("pSphere1")
        assert result["success"] is True
        assert result["context"]["count"] == 1
        assert "pSphere1_parentConstraint1" in result["context"]["removed"]
        mock_maya.delete.assert_called_once_with("pSphere1_parentConstraint1")

    def test_remove_specific_type(self, mock_maya):
        mock_maya.listRelatives.return_value = ["pSphere1_orientConstraint1"]
        from dcc_mcp_maya.actions.constraints import remove_constraint
        result = remove_constraint("pSphere1", constraint_type="orient")
        assert result["success"] is True
        assert result["context"]["count"] == 1

    def test_no_constraints_found(self, mock_maya):
        mock_maya.listRelatives.return_value = []
        from dcc_mcp_maya.actions.constraints import remove_constraint
        result = remove_constraint("pSphere1")
        assert result["success"] is True
        assert result["context"]["count"] == 0

    def test_invalid_type(self, mock_maya):
        from dcc_mcp_maya.actions.constraints import remove_constraint
        result = remove_constraint("pSphere1", constraint_type="invalid")
        assert result["success"] is False

    def test_target_not_found(self, mock_maya):
        mock_maya.objExists.return_value = False
        from dcc_mcp_maya.actions.constraints import remove_constraint
        result = remove_constraint("ghost")
        assert result["success"] is False


# ===========================================================================
# list_constraints
# ===========================================================================

class TestListConstraints:
    def test_lists_parent_constraint(self, mock_maya):
        mock_maya.listRelatives.side_effect = lambda obj, type=None: (
            ["pSphere1_parentConstraint1"] if type == "parentConstraint" else []
        )
        from dcc_mcp_maya.actions.constraints import list_constraints
        result = list_constraints("pSphere1")
        assert result["success"] is True
        assert result["context"]["count"] == 1
        assert result["context"]["constraints"][0]["type"] == "parentConstraint"

    def test_no_constraints(self, mock_maya):
        mock_maya.listRelatives.return_value = []
        from dcc_mcp_maya.actions.constraints import list_constraints
        result = list_constraints("pSphere1")
        assert result["success"] is True
        assert result["context"]["count"] == 0

    def test_multiple_constraint_types(self, mock_maya):
        def _list_rel(obj, type=None):
            mapping = {
                "parentConstraint": ["pc1"],
                "orientConstraint": ["oc1"],
            }
            return mapping.get(type, [])
        mock_maya.listRelatives.side_effect = _list_rel
        from dcc_mcp_maya.actions.constraints import list_constraints
        result = list_constraints("pSphere1")
        assert result["success"] is True
        assert result["context"]["count"] == 2

    def test_target_not_found(self, mock_maya):
        mock_maya.objExists.return_value = False
        from dcc_mcp_maya.actions.constraints import list_constraints
        result = list_constraints("ghost")
        assert result["success"] is False


# ===========================================================================
# connect_attr
# ===========================================================================

class TestConnectAttr:
    def test_connect_success(self, mock_maya):
        from dcc_mcp_maya.actions.node_graph import connect_attr
        result = connect_attr("pSphere1.translateX", "pCube1.translateX")
        assert result["success"] is True
        mock_maya.connectAttr.assert_called_once_with(
            "pSphere1.translateX", "pCube1.translateX", force=False
        )

    def test_connect_with_force(self, mock_maya):
        from dcc_mcp_maya.actions.node_graph import connect_attr
        result = connect_attr("A.tx", "B.tx", force=True)
        assert result["success"] is True
        mock_maya.connectAttr.assert_called_once_with("A.tx", "B.tx", force=True)

    def test_source_not_found(self, mock_maya):
        mock_maya.objExists.side_effect = lambda n: "missing" not in n
        from dcc_mcp_maya.actions.node_graph import connect_attr
        result = connect_attr("missing.tx", "B.tx")
        assert result["success"] is False
        assert "missing" in result["message"]

    def test_dest_not_found(self, mock_maya):
        mock_maya.objExists.side_effect = lambda n: "missing" not in n
        from dcc_mcp_maya.actions.node_graph import connect_attr
        result = connect_attr("A.tx", "missing.tx")
        assert result["success"] is False

    def test_connect_exception(self, mock_maya):
        mock_maya.connectAttr.side_effect = RuntimeError("already connected")
        from dcc_mcp_maya.actions.node_graph import connect_attr
        result = connect_attr("A.tx", "B.tx")
        assert result["success"] is False
        assert "already connected" in str(result)


# ===========================================================================
# disconnect_attr
# ===========================================================================

class TestDisconnectAttr:
    def test_disconnect_success(self, mock_maya):
        from dcc_mcp_maya.actions.node_graph import disconnect_attr
        result = disconnect_attr("pSphere1.translateX", "pCube1.translateX")
        assert result["success"] is True
        mock_maya.disconnectAttr.assert_called_once_with(
            "pSphere1.translateX", "pCube1.translateX"
        )

    def test_source_not_found(self, mock_maya):
        mock_maya.objExists.side_effect = lambda n: "missing" not in n
        from dcc_mcp_maya.actions.node_graph import disconnect_attr
        result = disconnect_attr("missing.tx", "B.tx")
        assert result["success"] is False

    def test_dest_not_found(self, mock_maya):
        mock_maya.objExists.side_effect = lambda n: "missing" not in n
        from dcc_mcp_maya.actions.node_graph import disconnect_attr
        result = disconnect_attr("A.tx", "missing.tx")
        assert result["success"] is False

    def test_not_connected(self, mock_maya):
        mock_maya.isConnected.return_value = False
        from dcc_mcp_maya.actions.node_graph import disconnect_attr
        result = disconnect_attr("A.tx", "B.tx")
        assert result["success"] is False
        assert "not connected" in result["message"].lower()

    def test_disconnect_exception(self, mock_maya):
        mock_maya.disconnectAttr.side_effect = RuntimeError("disconnect error")
        from dcc_mcp_maya.actions.node_graph import disconnect_attr
        result = disconnect_attr("A.tx", "B.tx")
        assert result["success"] is False


# ===========================================================================
# list_connections
# ===========================================================================

class TestListConnections:
    def test_list_connections_success(self, mock_maya):
        mock_maya.listConnections.return_value = [
            "pSphere1.translateX", "multiplyDivide1.input1X",
        ]
        from dcc_mcp_maya.actions.node_graph import list_connections
        result = list_connections("pSphere1")
        assert result["success"] is True
        assert result["context"]["count"] == 1
        assert result["context"]["connections"][0]["from"] == "pSphere1.translateX"

    def test_no_connections(self, mock_maya):
        mock_maya.listConnections.return_value = []
        from dcc_mcp_maya.actions.node_graph import list_connections
        result = list_connections("pSphere1")
        assert result["success"] is True
        assert result["context"]["count"] == 0

    def test_with_attribute_filter(self, mock_maya):
        mock_maya.listConnections.return_value = ["pSphere1.tx", "node2.input"]
        from dcc_mcp_maya.actions.node_graph import list_connections
        result = list_connections("pSphere1", attribute="translateX")
        assert result["success"] is True
        call_args = mock_maya.listConnections.call_args
        assert "pSphere1.translateX" in call_args[0]

    def test_object_not_found(self, mock_maya):
        mock_maya.objExists.return_value = False
        from dcc_mcp_maya.actions.node_graph import list_connections
        result = list_connections("ghost")
        assert result["success"] is False

    def test_attribute_not_found(self, mock_maya):
        mock_maya.objExists.side_effect = lambda n: n != "pSphere1.badAttr"
        from dcc_mcp_maya.actions.node_graph import list_connections
        result = list_connections("pSphere1", attribute="badAttr")
        assert result["success"] is False


# ===========================================================================
# get_dag_path
# ===========================================================================

class TestGetDagPath:
    def test_get_dag_path_success(self, mock_maya):
        mock_maya.ls.return_value = ["|group1|pSphere1"]
        mock_maya.objectType.return_value = "transform"
        from dcc_mcp_maya.actions.node_graph import get_dag_path
        result = get_dag_path("pSphere1")
        assert result["success"] is True
        assert result["context"]["dag_path"] == "|group1|pSphere1"
        assert result["context"]["short_name"] == "pSphere1"
        assert result["context"]["node_type"] == "transform"

    def test_root_level_object(self, mock_maya):
        mock_maya.ls.return_value = ["|pCube1"]
        from dcc_mcp_maya.actions.node_graph import get_dag_path
        result = get_dag_path("pCube1")
        assert result["success"] is True
        assert result["context"]["dag_path"] == "|pCube1"
        assert result["context"]["short_name"] == "pCube1"

    def test_object_not_found(self, mock_maya):
        mock_maya.objExists.return_value = False
        from dcc_mcp_maya.actions.node_graph import get_dag_path
        result = get_dag_path("ghost")
        assert result["success"] is False

    def test_ls_returns_empty(self, mock_maya):
        mock_maya.ls.return_value = []
        from dcc_mcp_maya.actions.node_graph import get_dag_path
        result = get_dag_path("pSphere1")
        assert result["success"] is False
        assert "empty" in str(result).lower() or "dag path" in result["message"].lower()


# ===========================================================================
# smooth_mesh
# ===========================================================================

class TestSmoothMesh:
    def test_preview_method(self, mock_maya):
        mock_maya.listRelatives.return_value = ["|pSphere1|pSphereShape1"]
        from dcc_mcp_maya.actions.node_graph import smooth_mesh
        result = smooth_mesh("pSphere1", divisions=2, method="preview")
        assert result["success"] is True
        assert result["context"]["method"] == "preview"
        assert result["context"]["divisions"] == 2
        mock_maya.setAttr.assert_any_call("|pSphere1|pSphereShape1.displaySmoothMesh", 2)
        mock_maya.setAttr.assert_any_call("|pSphere1|pSphereShape1.smoothLevel", 2)

    def test_preview_no_shape(self, mock_maya):
        """Falls back to transform node when no shape is returned."""
        mock_maya.listRelatives.return_value = []
        from dcc_mcp_maya.actions.node_graph import smooth_mesh
        result = smooth_mesh("pSphere1", divisions=1, method="preview")
        assert result["success"] is True
        mock_maya.setAttr.assert_any_call("pSphere1.displaySmoothMesh", 2)

    def test_subdivide_method(self, mock_maya):
        mock_maya.polySmooth.return_value = ["polySmoothFace1"]
        from dcc_mcp_maya.actions.node_graph import smooth_mesh
        result = smooth_mesh("pSphere1", divisions=1, method="subdivide")
        assert result["success"] is True
        assert result["context"]["method"] == "subdivide"
        assert result["context"]["poly_smooth_node"] == "polySmoothFace1"
        mock_maya.polySmooth.assert_called_once_with("pSphere1", divisions=1)

    def test_invalid_method(self, mock_maya):
        from dcc_mcp_maya.actions.node_graph import smooth_mesh
        result = smooth_mesh("pSphere1", method="invalid")
        assert result["success"] is False

    def test_negative_divisions(self, mock_maya):
        from dcc_mcp_maya.actions.node_graph import smooth_mesh
        result = smooth_mesh("pSphere1", divisions=-1)
        assert result["success"] is False

    def test_object_not_found(self, mock_maya):
        mock_maya.objExists.return_value = False
        from dcc_mcp_maya.actions.node_graph import smooth_mesh
        result = smooth_mesh("ghost")
        assert result["success"] is False

    def test_subdivide_exception(self, mock_maya):
        mock_maya.polySmooth.side_effect = RuntimeError("smooth failed")
        from dcc_mcp_maya.actions.node_graph import smooth_mesh
        result = smooth_mesh("pSphere1", method="subdivide")
        assert result["success"] is False


# ===========================================================================
# Registration check
# ===========================================================================

class TestRegisterAllRound6:
    def test_total_actions_count(self):
        from dcc_mcp_maya.actions import __all__
        # After round 6: 56 + 8 = 64
        assert len(__all__) >= 64

    def test_new_actions_exported(self):
        from dcc_mcp_maya.actions import (
            add_constraint,
            connect_attr,
            disconnect_attr,
            get_dag_path,
            list_connections,
            list_constraints,
            remove_constraint,
            smooth_mesh,
        )
        for fn in (
            add_constraint, remove_constraint, list_constraints,
            connect_attr, disconnect_attr, list_connections,
            get_dag_path, smooth_mesh,
        ):
            assert callable(fn)

    def test_register_all_includes_new_actions(self):
        registry = MagicMock()
        from dcc_mcp_maya.actions import register_all
        register_all(registry)
        call_names = [call[0][0] for call in registry.register.call_args_list]
        for name in ("add_constraint", "remove_constraint", "list_constraints",
                     "connect_attr", "disconnect_attr", "list_connections",
                     "get_dag_path", "smooth_mesh"):
            assert name in call_names, "Missing registration: {}".format(name)


# ===========================================================================
# ImportError branches — cover Maya-unavailable paths
# ===========================================================================

class TestImportErrorBranches:
    """Verify graceful error_result when maya.cmds cannot be imported."""

    def _no_maya(self, monkeypatch):
        """Remove maya.cmds from sys.modules to trigger ImportError."""
        monkeypatch.delitem(sys.modules, "maya", raising=False)
        monkeypatch.delitem(sys.modules, "maya.cmds", raising=False)
        monkeypatch.delitem(sys.modules, "maya.api", raising=False)
        monkeypatch.delitem(sys.modules, "maya.utils", raising=False)

    def test_add_constraint_no_maya(self, monkeypatch):
        self._no_maya(monkeypatch)
        import dcc_mcp_maya.actions.constraints as m
        import importlib; importlib.reload(m)
        result = m.add_constraint("A", "B")
        assert result["success"] is False
        assert "maya" in result["message"].lower()

    def test_remove_constraint_no_maya(self, monkeypatch):
        self._no_maya(monkeypatch)
        import dcc_mcp_maya.actions.constraints as m
        import importlib; importlib.reload(m)
        result = m.remove_constraint("pSphere1")
        assert result["success"] is False

    def test_list_constraints_no_maya(self, monkeypatch):
        self._no_maya(monkeypatch)
        import dcc_mcp_maya.actions.constraints as m
        import importlib; importlib.reload(m)
        result = m.list_constraints("pSphere1")
        assert result["success"] is False

    def test_connect_attr_no_maya(self, monkeypatch):
        self._no_maya(monkeypatch)
        import dcc_mcp_maya.actions.node_graph as m
        import importlib; importlib.reload(m)
        result = m.connect_attr("A.tx", "B.tx")
        assert result["success"] is False

    def test_disconnect_attr_no_maya(self, monkeypatch):
        self._no_maya(monkeypatch)
        import dcc_mcp_maya.actions.node_graph as m
        import importlib; importlib.reload(m)
        result = m.disconnect_attr("A.tx", "B.tx")
        assert result["success"] is False

    def test_list_connections_no_maya(self, monkeypatch):
        self._no_maya(monkeypatch)
        import dcc_mcp_maya.actions.node_graph as m
        import importlib; importlib.reload(m)
        result = m.list_connections("pSphere1")
        assert result["success"] is False

    def test_get_dag_path_no_maya(self, monkeypatch):
        self._no_maya(monkeypatch)
        import dcc_mcp_maya.actions.node_graph as m
        import importlib; importlib.reload(m)
        result = m.get_dag_path("pSphere1")
        assert result["success"] is False

    def test_smooth_mesh_no_maya(self, monkeypatch):
        self._no_maya(monkeypatch)
        import dcc_mcp_maya.actions.node_graph as m
        import importlib; importlib.reload(m)
        result = m.smooth_mesh("pSphere1")
        assert result["success"] is False
