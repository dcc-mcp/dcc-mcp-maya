"""Tests for Round 7 actions: history, symmetry, joint limits, expressions."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import sys
from unittest.mock import MagicMock

# Import third-party modules
import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_cmds():
    """Return a MagicMock configured with sensible Maya cmds defaults."""
    m = MagicMock()
    m.objExists.return_value = True
    m.objectType.return_value = "transform"
    m.listHistory.return_value = []
    m.ls.return_value = []
    m.expression.return_value = "expression1"
    return m


@pytest.fixture(autouse=True)
def mock_maya(monkeypatch):
    """Inject mock maya modules before each test via monkeypatch."""
    mc = _make_cmds()
    mock_maya_mod = MagicMock()
    mock_maya_mod.cmds = mc
    monkeypatch.setitem(sys.modules, "maya", mock_maya_mod)
    monkeypatch.setitem(sys.modules, "maya.cmds", mc)
    monkeypatch.setitem(sys.modules, "maya.api", MagicMock())
    monkeypatch.setitem(sys.modules, "maya.utils", MagicMock())
    return mc


# ===========================================================================
# list_history
# ===========================================================================

class TestListHistory:
    def test_happy_path(self, mock_maya):
        mock_maya.objExists.return_value = True
        mock_maya.listHistory.return_value = ["polySphere1", "pSphere1"]
        mock_maya.objectType.side_effect = lambda n: "polySphere" if "poly" in n else "transform"

        from dcc_mcp_maya.actions.node_graph import list_history
        result = list_history("pSphere1")
        assert result["success"] is True
        context = result["context"]
        # pSphere1 is excluded (same as object_name), polySphere1 remains
        assert context["count"] == 1
        assert context["history"][0]["name"] == "polySphere1"

    def test_future_flag(self, mock_maya):
        mock_maya.objExists.return_value = True
        mock_maya.listHistory.return_value = []

        from dcc_mcp_maya.actions.node_graph import list_history
        result = list_history("pSphere1", future=True)
        assert result["success"] is True
        call_kwargs = mock_maya.listHistory.call_args[1]
        assert call_kwargs["future"] is True

    def test_levels_param(self, mock_maya):
        mock_maya.objExists.return_value = True
        mock_maya.listHistory.return_value = []

        from dcc_mcp_maya.actions.node_graph import list_history
        result = list_history("pSphere1", levels=3)
        assert result["success"] is True
        call_kwargs = mock_maya.listHistory.call_args[1]
        assert call_kwargs["levels"] == 3

    def test_object_not_found(self, mock_maya):
        mock_maya.objExists.return_value = False

        from dcc_mcp_maya.actions.node_graph import list_history
        result = list_history("nonexistent")
        assert result["success"] is False
        assert "not found" in result["message"].lower()

    def test_empty_history(self, mock_maya):
        mock_maya.objExists.return_value = True
        mock_maya.listHistory.return_value = []

        from dcc_mcp_maya.actions.node_graph import list_history
        result = list_history("pSphere1")
        assert result["success"] is True
        assert result["context"]["count"] == 0

    def test_none_return_from_listhistory(self, mock_maya):
        """listHistory may return None; should be treated as empty."""
        mock_maya.objExists.return_value = True
        mock_maya.listHistory.return_value = None

        from dcc_mcp_maya.actions.node_graph import list_history
        result = list_history("pSphere1")
        assert result["success"] is True
        assert result["context"]["count"] == 0

    def test_import_error(self, monkeypatch):
        monkeypatch.delitem(sys.modules, "maya.cmds", raising=False)
        monkeypatch.setitem(sys.modules, "maya.cmds", None)

        from dcc_mcp_maya.actions.node_graph import list_history
        result = list_history("pSphere1")
        assert result["success"] is False

    def test_exception_path(self, mock_maya):
        mock_maya.objExists.return_value = True
        mock_maya.listHistory.side_effect = RuntimeError("history error")

        from dcc_mcp_maya.actions.node_graph import list_history
        result = list_history("pSphere1")
        assert result["success"] is False


# ===========================================================================
# delete_history
# ===========================================================================

class TestDeleteHistory:
    def test_happy_path(self, mock_maya):
        mock_maya.objExists.return_value = True

        from dcc_mcp_maya.actions.node_graph import delete_history
        result = delete_history("pSphere1")
        assert result["success"] is True
        mock_maya.delete.assert_called_once_with("pSphere1", constructionHistory=True)

    def test_result_context(self, mock_maya):
        mock_maya.objExists.return_value = True

        from dcc_mcp_maya.actions.node_graph import delete_history
        result = delete_history("pCube1")
        assert result["context"]["object_name"] == "pCube1"

    def test_object_not_found(self, mock_maya):
        mock_maya.objExists.return_value = False

        from dcc_mcp_maya.actions.node_graph import delete_history
        result = delete_history("ghost")
        assert result["success"] is False
        assert "not found" in result["message"].lower()

    def test_import_error(self, monkeypatch):
        monkeypatch.setitem(sys.modules, "maya.cmds", None)

        from dcc_mcp_maya.actions.node_graph import delete_history
        result = delete_history("pSphere1")
        assert result["success"] is False

    def test_exception_path(self, mock_maya):
        mock_maya.objExists.return_value = True
        mock_maya.delete.side_effect = RuntimeError("delete error")

        from dcc_mcp_maya.actions.node_graph import delete_history
        result = delete_history("pSphere1")
        assert result["success"] is False


# ===========================================================================
# apply_symmetry
# ===========================================================================

class TestApplySymmetry:
    def test_happy_path_x(self, mock_maya):
        mock_maya.objExists.return_value = True

        from dcc_mcp_maya.actions.node_graph import apply_symmetry
        result = apply_symmetry("pSphere1", axis="x")
        assert result["success"] is True
        assert result["context"]["axis"] == "x"
        mock_maya.symmetricModelling.assert_called()

    def test_happy_path_y(self, mock_maya):
        mock_maya.objExists.return_value = True

        from dcc_mcp_maya.actions.node_graph import apply_symmetry
        result = apply_symmetry("pSphere1", axis="y")
        assert result["success"] is True
        assert result["context"]["axis"] == "y"

    def test_happy_path_z(self, mock_maya):
        mock_maya.objExists.return_value = True

        from dcc_mcp_maya.actions.node_graph import apply_symmetry
        result = apply_symmetry("pSphere1", axis="z")
        assert result["success"] is True

    def test_disable_symmetry(self, mock_maya):
        mock_maya.objExists.return_value = True

        from dcc_mcp_maya.actions.node_graph import apply_symmetry
        result = apply_symmetry("pSphere1", axis="none")
        assert result["success"] is True
        mock_maya.symmetricModelling.assert_called_with(symmetry=False)

    def test_invalid_axis(self, mock_maya):
        mock_maya.objExists.return_value = True

        from dcc_mcp_maya.actions.node_graph import apply_symmetry
        result = apply_symmetry("pSphere1", axis="w")
        assert result["success"] is False
        assert "axis" in result["message"].lower()

    def test_object_not_found(self, mock_maya):
        mock_maya.objExists.return_value = False

        from dcc_mcp_maya.actions.node_graph import apply_symmetry
        result = apply_symmetry("ghost", axis="x")
        assert result["success"] is False

    def test_object_space(self, mock_maya):
        mock_maya.objExists.return_value = True

        from dcc_mcp_maya.actions.node_graph import apply_symmetry
        result = apply_symmetry("pSphere1", axis="y", world_space=False)
        assert result["success"] is True
        call_kwargs = mock_maya.symmetricModelling.call_args[1]
        assert call_kwargs["about"] == "object"

    def test_world_space_default(self, mock_maya):
        mock_maya.objExists.return_value = True

        from dcc_mcp_maya.actions.node_graph import apply_symmetry
        result = apply_symmetry("pSphere1", axis="x")
        assert result["context"]["world_space"] is True

    def test_import_error(self, monkeypatch):
        monkeypatch.setitem(sys.modules, "maya.cmds", None)

        from dcc_mcp_maya.actions.node_graph import apply_symmetry
        result = apply_symmetry("pSphere1")
        assert result["success"] is False

    def test_exception_path(self, mock_maya):
        mock_maya.objExists.return_value = True
        mock_maya.symmetricModelling.side_effect = RuntimeError("sym error")

        from dcc_mcp_maya.actions.node_graph import apply_symmetry
        result = apply_symmetry("pSphere1", axis="x")
        assert result["success"] is False


# ===========================================================================
# set_joint_limit
# ===========================================================================

class TestSetJointLimit:
    def test_happy_path(self, mock_maya):
        mock_maya.objExists.return_value = True
        mock_maya.objectType.return_value = "joint"
        mock_maya.getAttr.side_effect = [-45.0, 45.0]

        from dcc_mcp_maya.actions.rigging import set_joint_limit
        result = set_joint_limit("joint1", axis="x", min_angle=-45.0, max_angle=45.0)
        assert result["success"] is True
        ctx = result["context"]
        assert ctx["axis"] == "x"
        assert ctx["min_angle"] == -45.0
        assert ctx["max_angle"] == 45.0
        assert ctx["enable"] is True

    def test_disable_limit(self, mock_maya):
        mock_maya.objExists.return_value = True
        mock_maya.objectType.return_value = "joint"
        mock_maya.getAttr.side_effect = [0.0, 0.0]

        from dcc_mcp_maya.actions.rigging import set_joint_limit
        result = set_joint_limit("joint1", axis="y", enable=False)
        assert result["success"] is True
        assert result["context"]["enable"] is False

    def test_axis_z(self, mock_maya):
        mock_maya.objExists.return_value = True
        mock_maya.objectType.return_value = "joint"
        mock_maya.getAttr.side_effect = [-90.0, 90.0]

        from dcc_mcp_maya.actions.rigging import set_joint_limit
        result = set_joint_limit("joint1", axis="z", min_angle=-90.0, max_angle=90.0)
        assert result["success"] is True
        assert result["context"]["axis"] == "z"

    def test_invalid_axis(self, mock_maya):
        mock_maya.objExists.return_value = True
        mock_maya.objectType.return_value = "joint"

        from dcc_mcp_maya.actions.rigging import set_joint_limit
        result = set_joint_limit("joint1", axis="w")
        assert result["success"] is False
        assert "axis" in result["message"].lower()

    def test_not_a_joint(self, mock_maya):
        mock_maya.objExists.return_value = True
        mock_maya.objectType.return_value = "transform"

        from dcc_mcp_maya.actions.rigging import set_joint_limit
        result = set_joint_limit("pSphere1", axis="x")
        assert result["success"] is False
        assert "joint" in result["message"].lower()

    def test_joint_not_found(self, mock_maya):
        mock_maya.objExists.return_value = False

        from dcc_mcp_maya.actions.rigging import set_joint_limit
        result = set_joint_limit("ghost", axis="x")
        assert result["success"] is False
        assert "not found" in result["message"].lower()

    def test_no_angles_specified(self, mock_maya):
        """Calling with no min/max should still succeed (enable/disable only)."""
        mock_maya.objExists.return_value = True
        mock_maya.objectType.return_value = "joint"
        mock_maya.getAttr.side_effect = [-180.0, 180.0]

        from dcc_mcp_maya.actions.rigging import set_joint_limit
        result = set_joint_limit("joint1", axis="z")
        assert result["success"] is True

    def test_setattr_called_for_enable(self, mock_maya):
        mock_maya.objExists.return_value = True
        mock_maya.objectType.return_value = "joint"
        mock_maya.getAttr.side_effect = [-45.0, 45.0]

        from dcc_mcp_maya.actions.rigging import set_joint_limit
        set_joint_limit("joint1", axis="x", min_angle=-45.0, max_angle=45.0)
        # setAttr should be called at least 4 times: enable_min, enable_max, min, max
        assert mock_maya.setAttr.call_count >= 4

    def test_import_error(self, monkeypatch):
        monkeypatch.setitem(sys.modules, "maya.cmds", None)

        from dcc_mcp_maya.actions.rigging import set_joint_limit
        result = set_joint_limit("joint1", axis="x")
        assert result["success"] is False

    def test_exception_path(self, mock_maya):
        mock_maya.objExists.return_value = True
        mock_maya.objectType.return_value = "joint"
        mock_maya.setAttr.side_effect = RuntimeError("locked attr")

        from dcc_mcp_maya.actions.rigging import set_joint_limit
        result = set_joint_limit("joint1", axis="x")
        assert result["success"] is False


# ===========================================================================
# create_expression
# ===========================================================================

class TestCreateExpression:
    def test_happy_path(self, mock_maya):
        mock_maya.expression.return_value = "expression1"

        from dcc_mcp_maya.actions.expressions import create_expression
        result = create_expression("pSphere1.tx = sin(time);")
        assert result["success"] is True
        assert result["context"]["expression_name"] == "expression1"

    def test_with_name(self, mock_maya):
        mock_maya.expression.return_value = "myExpr"

        from dcc_mcp_maya.actions.expressions import create_expression
        result = create_expression("pSphere1.tx = time;", name="myExpr")
        assert result["success"] is True
        call_kwargs = mock_maya.expression.call_args[1]
        assert call_kwargs["name"] == "myExpr"

    def test_with_object_and_attribute(self, mock_maya):
        mock_maya.objExists.return_value = True
        mock_maya.expression.return_value = "expression1"

        from dcc_mcp_maya.actions.expressions import create_expression
        result = create_expression("tx = sin(time);", object_name="pSphere1", attribute="translateX")
        assert result["success"] is True
        call_kwargs = mock_maya.expression.call_args[1]
        assert call_kwargs["object"] == "pSphere1"
        assert call_kwargs["attribute"] == "translateX"

    def test_object_not_found(self, mock_maya):
        mock_maya.objExists.return_value = False

        from dcc_mcp_maya.actions.expressions import create_expression
        result = create_expression("tx = 0;", object_name="ghost")
        assert result["success"] is False

    def test_empty_expression(self, mock_maya):
        from dcc_mcp_maya.actions.expressions import create_expression
        result = create_expression("")
        assert result["success"] is False
        assert "empty" in result["message"].lower()

    def test_whitespace_only_expression(self, mock_maya):
        from dcc_mcp_maya.actions.expressions import create_expression
        result = create_expression("   ")
        assert result["success"] is False

    def test_invalid_unit_conversion(self, mock_maya):
        from dcc_mcp_maya.actions.expressions import create_expression
        result = create_expression("tx = 0;", unit_conversion=99)
        assert result["success"] is False

    def test_unit_conversion_valid_values(self, mock_maya):
        mock_maya.expression.return_value = "expression1"

        from dcc_mcp_maya.actions.expressions import create_expression
        for uc in (0, 1, 2):
            result = create_expression("tx = 0;", unit_conversion=uc)
            assert result["success"] is True, "unit_conversion={} should succeed".format(uc)

    def test_import_error(self, monkeypatch):
        monkeypatch.setitem(sys.modules, "maya.cmds", None)

        from dcc_mcp_maya.actions.expressions import create_expression
        result = create_expression("tx = 0;")
        assert result["success"] is False

    def test_exception_path(self, mock_maya):
        mock_maya.expression.side_effect = RuntimeError("expr error")

        from dcc_mcp_maya.actions.expressions import create_expression
        result = create_expression("pSphere1.tx = sin(time);")
        assert result["success"] is False


# ===========================================================================
# list_expressions
# ===========================================================================

class TestListExpressions:
    def test_happy_path_all(self, mock_maya):
        mock_maya.ls.return_value = ["expression1", "expression2"]

        def expr_string(name, **kw):
            return "body_{};".format(name)

        mock_maya.expression.side_effect = expr_string

        from dcc_mcp_maya.actions.expressions import list_expressions
        result = list_expressions()
        assert result["success"] is True
        assert result["context"]["count"] == 2

    def test_filter_by_object(self, mock_maya):
        mock_maya.objExists.return_value = True
        mock_maya.ls.return_value = ["expression1", "expression2"]

        def expr_string(name, **kw):
            if name == "expression1":
                return "pSphere1.tx = sin(time);"
            return "pCube1.ty = time;"

        mock_maya.expression.side_effect = expr_string

        from dcc_mcp_maya.actions.expressions import list_expressions
        result = list_expressions(object_name="pSphere1")
        assert result["success"] is True
        assert result["context"]["count"] == 1
        assert result["context"]["expressions"][0]["name"] == "expression1"

    def test_object_not_found(self, mock_maya):
        mock_maya.objExists.return_value = False

        from dcc_mcp_maya.actions.expressions import list_expressions
        result = list_expressions(object_name="ghost")
        assert result["success"] is False

    def test_empty_scene(self, mock_maya):
        mock_maya.ls.return_value = []

        from dcc_mcp_maya.actions.expressions import list_expressions
        result = list_expressions()
        assert result["success"] is True
        assert result["context"]["count"] == 0

    def test_returns_expression_strings(self, mock_maya):
        mock_maya.ls.return_value = ["expression1"]
        mock_maya.expression.return_value = "tx = time;"

        from dcc_mcp_maya.actions.expressions import list_expressions
        result = list_expressions()
        assert result["context"]["expressions"][0]["string"] == "tx = time;"

    def test_import_error(self, monkeypatch):
        monkeypatch.setitem(sys.modules, "maya.cmds", None)

        from dcc_mcp_maya.actions.expressions import list_expressions
        result = list_expressions()
        assert result["success"] is False

    def test_exception_path(self, mock_maya):
        mock_maya.ls.side_effect = RuntimeError("ls error")

        from dcc_mcp_maya.actions.expressions import list_expressions
        result = list_expressions()
        assert result["success"] is False


# ===========================================================================
# delete_expression
# ===========================================================================

class TestDeleteExpression:
    def test_happy_path(self, mock_maya):
        mock_maya.objExists.return_value = True
        mock_maya.objectType.return_value = "expression"

        from dcc_mcp_maya.actions.expressions import delete_expression
        result = delete_expression("expression1")
        assert result["success"] is True
        mock_maya.delete.assert_called_once_with("expression1")

    def test_result_context(self, mock_maya):
        mock_maya.objExists.return_value = True
        mock_maya.objectType.return_value = "expression"

        from dcc_mcp_maya.actions.expressions import delete_expression
        result = delete_expression("myExpr")
        assert result["context"]["expression_name"] == "myExpr"

    def test_not_found(self, mock_maya):
        mock_maya.objExists.return_value = False

        from dcc_mcp_maya.actions.expressions import delete_expression
        result = delete_expression("ghost")
        assert result["success"] is False
        assert "not found" in result["message"].lower()

    def test_wrong_node_type(self, mock_maya):
        mock_maya.objExists.return_value = True
        mock_maya.objectType.return_value = "transform"

        from dcc_mcp_maya.actions.expressions import delete_expression
        result = delete_expression("pSphere1")
        assert result["success"] is False
        assert "expression" in result["message"].lower()

    def test_import_error(self, monkeypatch):
        monkeypatch.setitem(sys.modules, "maya.cmds", None)

        from dcc_mcp_maya.actions.expressions import delete_expression
        result = delete_expression("expression1")
        assert result["success"] is False

    def test_exception_path(self, mock_maya):
        mock_maya.objExists.return_value = True
        mock_maya.objectType.return_value = "expression"
        mock_maya.delete.side_effect = RuntimeError("locked")

        from dcc_mcp_maya.actions.expressions import delete_expression
        result = delete_expression("expression1")
        assert result["success"] is False


# ===========================================================================
# register_all includes new Round 7 actions
# ===========================================================================

class TestRegisterAllRound7:
    def test_register_count_at_least_70(self, mock_maya):
        from dcc_mcp_maya.actions import register_all
        registry = MagicMock()
        register_all(registry)
        assert registry.register.call_count >= 70

    def test_new_actions_registered(self, mock_maya):
        from dcc_mcp_maya.actions import register_all
        registry = MagicMock()
        register_all(registry)
        names = {call[0][0] for call in registry.register.call_args_list}
        for action in ("list_history", "delete_history", "apply_symmetry",
                       "set_joint_limit", "create_expression", "list_expressions",
                       "delete_expression"):
            assert action in names, "{} not registered".format(action)
