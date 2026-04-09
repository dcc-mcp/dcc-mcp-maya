"""Unit tests for Round 3 skill scripts: expressions, namespaces, scripting,
utility, vertex-color, deformers, and texture-bake.

All tests mock maya.cmds / maya.mel to avoid requiring a real Maya environment.
Scripts are loaded via importlib to handle hyphenated skill directory names.
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
    """Load a skill script from its file path with a unique module name."""
    _MOD_COUNTER[0] += 1
    script_path = _SKILLS_ROOT / skill_dir / "scripts" / "{}.py".format(script_name)
    module_name = "skill_r3_{}_{}_{}".format(
        skill_dir.replace("-", "_"), script_name, _MOD_COUNTER[0]
    )
    spec = importlib.util.spec_from_file_location(module_name, str(script_path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _make_maya_env(**cmds_overrides):
    """Return (maya_mock, cmds_mock, mel_mock, modules_dict)."""
    maya_mock = MagicMock()
    cmds_mock = MagicMock()
    mel_mock = MagicMock()
    cmds_mock.objExists.return_value = True
    cmds_mock.ls.return_value = []
    for k, v in cmds_overrides.items():
        setattr(cmds_mock, k, v)
    maya_mock.cmds = cmds_mock
    maya_mock.mel = mel_mock
    modules = {
        "maya": maya_mock,
        "maya.cmds": cmds_mock,
        "maya.mel": mel_mock,
        "maya.api": MagicMock(),
        "maya.utils": MagicMock(),
    }
    return maya_mock, cmds_mock, mel_mock, modules


# ---------------------------------------------------------------------------
# maya-expressions
# ---------------------------------------------------------------------------


class TestCreateExpression:
    def test_create_basic(self):
        _, cmds_mock, _, modules = _make_maya_env()
        cmds_mock.expression.return_value = "expression1"
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-expressions", "create_expression")
            result = mod.create_expression("pSphere1.tx = sin(time);")
        assert result["success"] is True
        assert result["context"]["expression_name"] == "expression1"

    def test_create_with_name(self):
        _, cmds_mock, _, modules = _make_maya_env()
        cmds_mock.expression.return_value = "myExpr"
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-expressions", "create_expression")
            result = mod.create_expression("pSphere1.tx = 1;", name="myExpr")
        assert result["success"] is True
        assert result["context"]["expression_name"] == "myExpr"

    def test_create_with_object_and_attribute(self):
        _, cmds_mock, _, modules = _make_maya_env()
        cmds_mock.expression.return_value = "expression2"
        cmds_mock.objExists.return_value = True
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-expressions", "create_expression")
            result = mod.create_expression(
                "tx = sin(time);",
                object_name="pSphere1",
                attribute="translateX",
            )
        assert result["success"] is True
        assert result["context"]["object_name"] == "pSphere1"

    def test_empty_expression_fails(self):
        _, cmds_mock, _, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-expressions", "create_expression")
            result = mod.create_expression("   ")
        assert result["success"] is False

    def test_invalid_unit_conversion_fails(self):
        _, cmds_mock, _, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-expressions", "create_expression")
            result = mod.create_expression("tx = 1;", unit_conversion=99)
        assert result["success"] is False

    def test_object_not_found(self):
        _, cmds_mock, _, modules = _make_maya_env()
        cmds_mock.objExists.return_value = False
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-expressions", "create_expression")
            result = mod.create_expression("tx = 1;", object_name="ghost")
        assert result["success"] is False

    def test_maya_exception(self):
        _, cmds_mock, _, modules = _make_maya_env()
        cmds_mock.expression.side_effect = RuntimeError("syntax error in MEL")
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-expressions", "create_expression")
            result = mod.create_expression("pSphere1.tx = !!!;")
        assert result["success"] is False


class TestListExpressions:
    def test_list_all(self):
        _, cmds_mock, _, modules = _make_maya_env()
        cmds_mock.ls.return_value = ["expression1", "expression2"]
        cmds_mock.expression.return_value = "pSphere1.tx = sin(time);"
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-expressions", "list_expressions")
            result = mod.list_expressions()
        assert result["success"] is True
        assert result["context"]["count"] == 2

    def test_list_empty(self):
        _, cmds_mock, _, modules = _make_maya_env()
        cmds_mock.ls.return_value = []
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-expressions", "list_expressions")
            result = mod.list_expressions()
        assert result["success"] is True
        assert result["context"]["count"] == 0

    def test_list_filtered_by_object(self):
        _, cmds_mock, _, modules = _make_maya_env()

        def ls_side(type=None):
            return ["expression1", "expression2"]

        cmds_mock.ls.side_effect = ls_side

        call_count = [0]

        def expr_side(name, **kwargs):
            call_count[0] += 1
            # expression1 references pSphere1, expression2 doesn't
            if name == "expression1":
                return "pSphere1.tx = sin(time);"
            return "pCube1.ty = 5;"

        cmds_mock.expression.side_effect = expr_side
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-expressions", "list_expressions")
            result = mod.list_expressions(object_name="pSphere1")
        assert result["success"] is True
        assert result["context"]["count"] == 1
        assert result["context"]["expressions"][0]["name"] == "expression1"

    def test_object_not_found(self):
        _, cmds_mock, _, modules = _make_maya_env()
        cmds_mock.objExists.return_value = False
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-expressions", "list_expressions")
            result = mod.list_expressions(object_name="ghost")
        assert result["success"] is False


class TestDeleteExpression:
    def test_delete_existing(self):
        _, cmds_mock, _, modules = _make_maya_env()
        cmds_mock.objExists.return_value = True
        cmds_mock.objectType.return_value = "expression"
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-expressions", "delete_expression")
            result = mod.delete_expression("expression1")
        assert result["success"] is True
        assert result["context"]["expression_name"] == "expression1"
        cmds_mock.delete.assert_called_once_with("expression1")

    def test_not_found(self):
        _, cmds_mock, _, modules = _make_maya_env()
        cmds_mock.objExists.return_value = False
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-expressions", "delete_expression")
            result = mod.delete_expression("ghost")
        assert result["success"] is False

    def test_wrong_type(self):
        _, cmds_mock, _, modules = _make_maya_env()
        cmds_mock.objExists.return_value = True
        cmds_mock.objectType.return_value = "transform"
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-expressions", "delete_expression")
            result = mod.delete_expression("pSphere1")
        assert result["success"] is False

    def test_delete_exception(self):
        _, cmds_mock, _, modules = _make_maya_env()
        cmds_mock.objExists.return_value = True
        cmds_mock.objectType.return_value = "expression"
        cmds_mock.delete.side_effect = RuntimeError("locked")
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-expressions", "delete_expression")
            result = mod.delete_expression("expression1")
        assert result["success"] is False


# ---------------------------------------------------------------------------
# maya-namespaces
# ---------------------------------------------------------------------------


class TestSetNamespace:
    def test_move_to_namespace(self):
        _, cmds_mock, _, modules = _make_maya_env()
        cmds_mock.namespace.return_value = True  # exists
        cmds_mock.rename.return_value = "char:pSphere1"
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-namespaces", "set_namespace")
            result = mod.set_namespace("pSphere1", "char")
        assert result["success"] is True
        assert result["context"]["namespace"] == "char"
        assert result["context"]["new_name"] == "char:pSphere1"

    def test_create_namespace_if_missing(self):
        _, cmds_mock, _, modules = _make_maya_env()
        # namespace does not exist
        cmds_mock.namespace.side_effect = lambda **kw: (
            False if kw.get("exists") else None
        )
        cmds_mock.rename.return_value = "newns:pSphere1"
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-namespaces", "set_namespace")
            result = mod.set_namespace("pSphere1", "newns", create_if_missing=True)
        assert result["success"] is True

    def test_namespace_missing_no_create(self):
        _, cmds_mock, _, modules = _make_maya_env()
        cmds_mock.namespace.return_value = False
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-namespaces", "set_namespace")
            result = mod.set_namespace("pSphere1", "missing", create_if_missing=False)
        assert result["success"] is False

    def test_move_to_root(self):
        _, cmds_mock, _, modules = _make_maya_env()
        cmds_mock.rename.return_value = "pSphere1"
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-namespaces", "set_namespace")
            result = mod.set_namespace("char:pSphere1", "")
        assert result["success"] is True
        assert result["context"]["namespace"] == ":"

    def test_object_not_found(self):
        _, cmds_mock, _, modules = _make_maya_env()
        cmds_mock.objExists.return_value = False
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-namespaces", "set_namespace")
            result = mod.set_namespace("ghost", "char")
        assert result["success"] is False


class TestRenameNamespace:
    def test_rename_success(self):
        _, cmds_mock, _, modules = _make_maya_env()

        def ns_side(**kw):
            if kw.get("exists") == ":old":
                return True
            if kw.get("exists") == ":new":
                return False
            return None

        cmds_mock.namespace.side_effect = ns_side
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-namespaces", "rename_namespace")
            result = mod.rename_namespace("old", "new")
        assert result["success"] is True
        assert result["context"]["old_name"] == "old"
        assert result["context"]["new_name"] == "new"

    def test_rename_empty_old(self):
        _, cmds_mock, _, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-namespaces", "rename_namespace")
            result = mod.rename_namespace("", "new")
        assert result["success"] is False

    def test_rename_protected_ns(self):
        _, cmds_mock, _, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-namespaces", "rename_namespace")
            result = mod.rename_namespace("UI", "myUI")
        assert result["success"] is False

    def test_rename_old_not_found(self):
        _, cmds_mock, _, modules = _make_maya_env()
        cmds_mock.namespace.return_value = False
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-namespaces", "rename_namespace")
            result = mod.rename_namespace("nonexistent", "new")
        assert result["success"] is False

    def test_rename_new_already_exists(self):
        _, cmds_mock, _, modules = _make_maya_env()
        # both old and new exist
        cmds_mock.namespace.return_value = True
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-namespaces", "rename_namespace")
            result = mod.rename_namespace("old", "alreadyExists")
        assert result["success"] is False


class TestDeleteNamespace:
    def test_delete_with_merge(self):
        _, cmds_mock, _, modules = _make_maya_env()
        cmds_mock.namespace.return_value = True
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-namespaces", "delete_namespace")
            result = mod.delete_namespace("char")
        assert result["success"] is True
        assert result["context"]["namespace"] == "char"
        assert result["context"]["merged_with_root"] is True

    def test_delete_without_merge(self):
        _, cmds_mock, _, modules = _make_maya_env()
        cmds_mock.namespace.return_value = True
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-namespaces", "delete_namespace")
            result = mod.delete_namespace("char", merge_with_root=False)
        assert result["success"] is True
        assert result["context"]["merged_with_root"] is False

    def test_delete_empty_ns(self):
        _, cmds_mock, _, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-namespaces", "delete_namespace")
            result = mod.delete_namespace("")
        assert result["success"] is False

    def test_delete_protected_ns(self):
        _, cmds_mock, _, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-namespaces", "delete_namespace")
            result = mod.delete_namespace("shared")
        assert result["success"] is False

    def test_namespace_not_found(self):
        _, cmds_mock, _, modules = _make_maya_env()
        cmds_mock.namespace.return_value = False
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-namespaces", "delete_namespace")
            result = mod.delete_namespace("ghost")
        assert result["success"] is False


# ---------------------------------------------------------------------------
# maya-scripting
# ---------------------------------------------------------------------------


class TestExecuteMel:
    def test_execute_success(self):
        _, cmds_mock, mel_mock, modules = _make_maya_env()
        mel_mock.eval.return_value = "sphere1"
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-scripting", "execute_mel")
            result = mod.execute_mel("sphere;")
        assert result["success"] is True
        assert result["context"]["output"] == "sphere1"
        assert result["context"]["script"] == "sphere;"

    def test_execute_none_result(self):
        _, cmds_mock, mel_mock, modules = _make_maya_env()
        mel_mock.eval.return_value = None
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-scripting", "execute_mel")
            result = mod.execute_mel("select -all;")
        assert result["success"] is True
        assert result["context"]["output"] == ""

    def test_execute_mel_exception(self):
        _, cmds_mock, mel_mock, modules = _make_maya_env()
        mel_mock.eval.side_effect = RuntimeError("MEL syntax error")
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-scripting", "execute_mel")
            result = mod.execute_mel("!!!invalid mel")
        assert result["success"] is False

    def test_execute_returns_int(self):
        _, cmds_mock, mel_mock, modules = _make_maya_env()
        mel_mock.eval.return_value = 42
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-scripting", "execute_mel")
            result = mod.execute_mel("getAttr pSphere1.tx;")
        assert result["success"] is True
        assert result["context"]["output"] == "42"


class TestExecutePython:
    def test_execute_with_result(self):
        _, cmds_mock, _, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-scripting", "execute_python")
            result = mod.execute_python("result = 'hello'")
        assert result["success"] is True
        assert result["context"]["output"] == "hello"

    def test_execute_no_result(self):
        _, cmds_mock, _, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-scripting", "execute_python")
            result = mod.execute_python("x = 1 + 1")
        assert result["success"] is True
        assert result["context"]["output"] == ""

    def test_syntax_error(self):
        _, cmds_mock, _, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-scripting", "execute_python")
            result = mod.execute_python("def )(:")
        assert result["success"] is False

    def test_runtime_error(self):
        _, cmds_mock, _, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-scripting", "execute_python")
            result = mod.execute_python("raise ValueError('oops')")
        assert result["success"] is False

    def test_execute_cmds_available(self):
        """cmds should be pre-imported and accessible inside the executed code."""
        _, cmds_mock, _, modules = _make_maya_env()
        cmds_mock.ls.return_value = ["pSphere1"]
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-scripting", "execute_python")
            result = mod.execute_python("result = str(cmds.ls())")
        assert result["success"] is True
        assert "pSphere1" in result["context"]["output"]


# ---------------------------------------------------------------------------
# maya-utility
# ---------------------------------------------------------------------------


class TestCreateUtilityNode:
    def test_create_multiply_divide(self):
        _, cmds_mock, _, modules = _make_maya_env()
        cmds_mock.shadingNode.return_value = "multiplyDivide1"
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-utility", "create_utility_node")
            result = mod.create_utility_node("multiplyDivide")
        assert result["success"] is True
        assert result["context"]["node_name"] == "multiplyDivide1"
        assert result["context"]["node_type"] == "multiplyDivide"

    def test_create_with_name(self):
        _, cmds_mock, _, modules = _make_maya_env()
        cmds_mock.shadingNode.return_value = "reverse1"
        cmds_mock.rename.return_value = "myReverse"
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-utility", "create_utility_node")
            result = mod.create_utility_node("reverse", name="myReverse")
        assert result["success"] is True
        assert result["context"]["node_name"] == "myReverse"

    def test_empty_type_fails(self):
        _, cmds_mock, _, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-utility", "create_utility_node")
            result = mod.create_utility_node("")
        assert result["success"] is False

    def test_create_exception(self):
        _, cmds_mock, _, modules = _make_maya_env()
        cmds_mock.shadingNode.side_effect = RuntimeError("unknown type")
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-utility", "create_utility_node")
            result = mod.create_utility_node("bogusNodeType")
        assert result["success"] is False


class TestGetSceneStatistics:
    def test_get_stats(self):
        _, cmds_mock, _, modules = _make_maya_env()

        _type_map = {
            "transform": ["pSphere1", "camera1"],
            "mesh": ["pSphereShape1"],
            "file": [],
            "camera": ["cameraShape1"],
            "pointLight": [],
            "directionalLight": [],
            "spotLight": [],
            "areaLight": [],
            "ambientLight": [],
            "aiAreaLight": [],
            "aiSkyDomeLight": [],
        }

        def ls_side(*args, **kw):
            t = kw.get("type")
            if t is not None:
                return _type_map.get(t, [])
            return ["pSphere1", "pSphereShape1", "camera1", "cameraShape1"]

        cmds_mock.ls.side_effect = ls_side
        cmds_mock.polyEvaluate.return_value = 382
        cmds_mock.file.return_value = "/scene/test.ma"
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-utility", "get_scene_statistics")
            result = mod.get_scene_statistics()
        assert result["success"] is True
        assert "total_nodes" in result["context"]
        assert "mesh_count" in result["context"]
        assert "poly_vertex_count" in result["context"]

    def test_get_stats_empty_scene(self):
        _, cmds_mock, _, modules = _make_maya_env()
        cmds_mock.ls.return_value = []
        cmds_mock.polyEvaluate.return_value = 0
        cmds_mock.file.return_value = ""
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-utility", "get_scene_statistics")
            result = mod.get_scene_statistics()
        assert result["success"] is True
        assert result["context"]["total_nodes"] == 0
        assert result["context"]["scene_file"] == ""

    def test_exception(self):
        _, cmds_mock, _, modules = _make_maya_env()
        cmds_mock.ls.side_effect = RuntimeError("DG error")
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-utility", "get_scene_statistics")
            result = mod.get_scene_statistics()
        assert result["success"] is False


# ---------------------------------------------------------------------------
# maya-vertex-color
# ---------------------------------------------------------------------------


class TestCreateColorSet:
    def test_create_rgba(self):
        _, cmds_mock, _, modules = _make_maya_env()
        cmds_mock.polyColorSet.return_value = []
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-vertex-color", "create_color_set")
            result = mod.create_color_set("pSphere1", "myColorSet")
        assert result["success"] is True
        assert result["context"]["color_set_name"] == "myColorSet"
        assert result["context"]["representation"] == "RGBA"

    def test_create_rgb_representation(self):
        _, cmds_mock, _, modules = _make_maya_env()
        cmds_mock.polyColorSet.return_value = []
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-vertex-color", "create_color_set")
            result = mod.create_color_set("pSphere1", "rgbSet", representation="RGB")
        assert result["success"] is True
        assert result["context"]["representation"] == "RGB"

    def test_invalid_representation(self):
        _, cmds_mock, _, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-vertex-color", "create_color_set")
            result = mod.create_color_set("pSphere1", "mySet", representation="XYZ")
        assert result["success"] is False

    def test_object_not_found(self):
        _, cmds_mock, _, modules = _make_maya_env()
        cmds_mock.objExists.return_value = False
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-vertex-color", "create_color_set")
            result = mod.create_color_set("ghost", "mySet")
        assert result["success"] is False

    def test_color_set_already_exists(self):
        _, cmds_mock, _, modules = _make_maya_env()
        cmds_mock.polyColorSet.return_value = ["existingSet"]
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-vertex-color", "create_color_set")
            result = mod.create_color_set("pSphere1", "existingSet")
        assert result["success"] is False


class TestSetVertexColor:
    def test_set_all_vertices(self):
        _, cmds_mock, _, modules = _make_maya_env()
        cmds_mock.polyEvaluate.return_value = 382
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-vertex-color", "set_vertex_color")
            result = mod.set_vertex_color("pSphere1", (1.0, 0.0, 0.0))
        assert result["success"] is True
        assert result["context"]["colored_count"] == 382
        assert result["context"]["color"] == [1.0, 0.0, 0.0]

    def test_set_specific_vertices(self):
        _, cmds_mock, _, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-vertex-color", "set_vertex_color")
            result = mod.set_vertex_color("pSphere1", (0.0, 1.0, 0.0), vertices=[0, 1, 2])
        assert result["success"] is True
        assert result["context"]["colored_count"] == 3

    def test_set_with_alpha(self):
        _, cmds_mock, _, modules = _make_maya_env()
        cmds_mock.polyEvaluate.return_value = 8
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-vertex-color", "set_vertex_color")
            result = mod.set_vertex_color("pCube1", (0.5, 0.5, 0.5), alpha=0.5)
        assert result["success"] is True
        assert result["context"]["alpha"] == 0.5

    def test_object_not_found(self):
        _, cmds_mock, _, modules = _make_maya_env()
        cmds_mock.objExists.return_value = False
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-vertex-color", "set_vertex_color")
            result = mod.set_vertex_color("ghost", (1.0, 0.0, 0.0))
        assert result["success"] is False

    def test_exception(self):
        _, cmds_mock, _, modules = _make_maya_env()
        cmds_mock.polyColorPerVertex.side_effect = RuntimeError("no color set")
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-vertex-color", "set_vertex_color")
            result = mod.set_vertex_color("pSphere1", (1.0, 0.0, 0.0))
        assert result["success"] is False


class TestGetVertexColor:
    def test_get_summary(self):
        _, cmds_mock, _, modules = _make_maya_env()
        cmds_mock.polyColorSet.side_effect = lambda obj, **kw: (
            ["colorSet1"] if kw.get("allColorSets") else ["colorSet1"]
        )
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-vertex-color", "get_vertex_color")
            result = mod.get_vertex_color("pSphere1")
        assert result["success"] is True
        assert "color_sets" in result["context"]

    def test_get_specific_vertex(self):
        _, cmds_mock, _, modules = _make_maya_env()
        cmds_mock.polyColorSet.return_value = ["colorSet1"]
        cmds_mock.objExists.return_value = True
        cmds_mock.polyColorPerVertex.return_value = [0.8, 0.2, 0.1, 1.0]
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-vertex-color", "get_vertex_color")
            result = mod.get_vertex_color("pSphere1", vertex_index=0)
        assert result["success"] is True
        assert result["context"]["vertex_index"] == 0
        assert len(result["context"]["color"]) == 3

    def test_vertex_not_found(self):
        _, cmds_mock, _, modules = _make_maya_env()
        cmds_mock.polyColorSet.return_value = []
        # first call (object) returns True, second call (vertex component) returns False
        call_count = [0]

        def exists_side(name):
            call_count[0] += 1
            if call_count[0] == 1:
                return True  # object exists
            return False  # vertex component does not

        cmds_mock.objExists.side_effect = exists_side
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-vertex-color", "get_vertex_color")
            result = mod.get_vertex_color("pSphere1", vertex_index=9999)
        assert result["success"] is False

    def test_object_not_found(self):
        _, cmds_mock, _, modules = _make_maya_env()
        cmds_mock.objExists.return_value = False
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-vertex-color", "get_vertex_color")
            result = mod.get_vertex_color("ghost")
        assert result["success"] is False


# ---------------------------------------------------------------------------
# maya-deformers
# ---------------------------------------------------------------------------


class TestCreateCluster:
    def test_create_basic(self):
        _, cmds_mock, _, modules = _make_maya_env()
        cmds_mock.cluster.return_value = ["cluster1", "cluster1Handle"]
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-deformers", "create_cluster")
            result = mod.create_cluster(["pSphere1"])
        assert result["success"] is True
        assert result["context"]["cluster_node"] == "cluster1"
        assert result["context"]["cluster_handle"] == "cluster1Handle"

    def test_create_with_name(self):
        _, cmds_mock, _, modules = _make_maya_env()
        cmds_mock.cluster.return_value = ["myCluster", "myClusterHandle"]
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-deformers", "create_cluster")
            result = mod.create_cluster(["pSphere1"], name="myCluster")
        assert result["success"] is True
        assert result["context"]["cluster_node"] == "myCluster"

    def test_no_objects_fails(self):
        _, cmds_mock, _, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-deformers", "create_cluster")
            result = mod.create_cluster([])
        assert result["success"] is False

    def test_object_not_found(self):
        _, cmds_mock, _, modules = _make_maya_env()
        cmds_mock.objExists.return_value = False
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-deformers", "create_cluster")
            result = mod.create_cluster(["ghost"])
        assert result["success"] is False

    def test_relative_mode(self):
        _, cmds_mock, _, modules = _make_maya_env()
        cmds_mock.cluster.return_value = ["cluster1", "cluster1Handle"]
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-deformers", "create_cluster")
            result = mod.create_cluster(["pSphere1"], relative=True)
        assert result["success"] is True
        call_kwargs = cmds_mock.cluster.call_args
        assert call_kwargs[1].get("relative") is True

    def test_exception(self):
        _, cmds_mock, _, modules = _make_maya_env()
        cmds_mock.cluster.side_effect = RuntimeError("deformer error")
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-deformers", "create_cluster")
            result = mod.create_cluster(["pSphere1"])
        assert result["success"] is False


class TestCreateLattice:
    def test_create_basic(self):
        _, cmds_mock, _, modules = _make_maya_env()
        cmds_mock.lattice.return_value = ["ffd1", "ffd1Lattice", "ffd1Base"]
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-deformers", "create_lattice")
            result = mod.create_lattice(["pSphere1"])
        assert result["success"] is True
        assert result["context"]["ffd_node"] == "ffd1"
        assert result["context"]["lattice_node"] == "ffd1Lattice"
        assert result["context"]["base_node"] == "ffd1Base"

    def test_create_with_custom_divisions(self):
        _, cmds_mock, _, modules = _make_maya_env()
        cmds_mock.lattice.return_value = ["ffd1", "ffd1Lattice", "ffd1Base"]
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-deformers", "create_lattice")
            result = mod.create_lattice(["pSphere1"], divisions=[3, 5, 3])
        assert result["success"] is True
        assert result["context"]["divisions"] == [3, 5, 3]

    def test_create_with_local_scale(self):
        _, cmds_mock, _, modules = _make_maya_env()
        cmds_mock.lattice.return_value = ["ffd1", "ffd1Lattice", "ffd1Base"]
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-deformers", "create_lattice")
            result = mod.create_lattice(["pSphere1"], local_scale=[2.0, 3.0, 2.0])
        assert result["success"] is True
        # setAttr should be called 3 times for sx, sy, sz
        assert cmds_mock.setAttr.call_count == 3

    def test_no_objects_fails(self):
        _, cmds_mock, _, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-deformers", "create_lattice")
            result = mod.create_lattice([])
        assert result["success"] is False

    def test_object_not_found(self):
        _, cmds_mock, _, modules = _make_maya_env()
        cmds_mock.objExists.return_value = False
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-deformers", "create_lattice")
            result = mod.create_lattice(["ghost"])
        assert result["success"] is False

    def test_default_divisions_on_invalid_input(self):
        """divisions with wrong length should fall back to [2, 5, 2]."""
        _, cmds_mock, _, modules = _make_maya_env()
        cmds_mock.lattice.return_value = ["ffd1", "ffd1Lattice", "ffd1Base"]
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-deformers", "create_lattice")
            result = mod.create_lattice(["pSphere1"], divisions=[2, 2])  # invalid length
        assert result["success"] is True
        assert result["context"]["divisions"] == [2, 5, 2]

    def test_exception(self):
        _, cmds_mock, _, modules = _make_maya_env()
        cmds_mock.lattice.side_effect = RuntimeError("not a polygon")
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-deformers", "create_lattice")
            result = mod.create_lattice(["pSphere1"])
        assert result["success"] is False


class TestWireDeformer:
    def test_create_basic(self):
        _, cmds_mock, _, modules = _make_maya_env()
        cmds_mock.wire.return_value = ["wire1"]
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-deformers", "wire_deformer")
            result = mod.wire_deformer(["curve1"], ["pSphere1"])
        assert result["success"] is True
        assert result["context"]["wire_node"] == "wire1"
        assert result["context"]["curves"] == ["curve1"]
        assert result["context"]["objects"] == ["pSphere1"]

    def test_no_curves_fails(self):
        _, cmds_mock, _, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-deformers", "wire_deformer")
            result = mod.wire_deformer([], ["pSphere1"])
        assert result["success"] is False

    def test_no_objects_fails(self):
        _, cmds_mock, _, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-deformers", "wire_deformer")
            result = mod.wire_deformer(["curve1"], [])
        assert result["success"] is False

    def test_curve_not_found(self):
        _, cmds_mock, _, modules = _make_maya_env()
        cmds_mock.objExists.side_effect = lambda x: x != "ghostCurve"
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-deformers", "wire_deformer")
            result = mod.wire_deformer(["ghostCurve"], ["pSphere1"])
        assert result["success"] is False

    def test_object_not_found(self):
        _, cmds_mock, _, modules = _make_maya_env()
        cmds_mock.objExists.side_effect = lambda x: x != "ghostMesh"
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-deformers", "wire_deformer")
            result = mod.wire_deformer(["curve1"], ["ghostMesh"])
        assert result["success"] is False

    def test_exception(self):
        _, cmds_mock, _, modules = _make_maya_env()
        cmds_mock.wire.side_effect = RuntimeError("wire failed")
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-deformers", "wire_deformer")
            result = mod.wire_deformer(["curve1"], ["pSphere1"])
        assert result["success"] is False


# ---------------------------------------------------------------------------
# maya-texture-bake
# ---------------------------------------------------------------------------


class TestBakeTextures:
    def test_bake_basic(self):
        _, cmds_mock, _, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-texture-bake", "bake_textures")
            result = mod.bake_textures(["pSphere1"], "/tmp/bake")
        assert result["success"] is True
        assert result["context"]["bake_type"] == "diffuse"
        assert result["context"]["resolution"] == 512

    def test_bake_arnold(self):
        _, cmds_mock, _, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-texture-bake", "bake_textures")
            result = mod.bake_textures(["pSphere1"], "/tmp/bake", renderer="arnold", bake_type="normals")
        assert result["success"] is True
        assert result["context"]["renderer"] == "arnold"

    def test_invalid_bake_type(self):
        _, cmds_mock, _, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-texture-bake", "bake_textures")
            result = mod.bake_textures(["pSphere1"], "/tmp/bake", bake_type="invalid")
        assert result["success"] is False

    def test_invalid_renderer(self):
        _, cmds_mock, _, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-texture-bake", "bake_textures")
            result = mod.bake_textures(["pSphere1"], "/tmp/bake", renderer="vray")
        assert result["success"] is False

    def test_no_objects(self):
        _, cmds_mock, _, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-texture-bake", "bake_textures")
            result = mod.bake_textures([], "/tmp/bake")
        assert result["success"] is False

    def test_invalid_resolution(self):
        _, cmds_mock, _, modules = _make_maya_env()
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-texture-bake", "bake_textures")
            result = mod.bake_textures(["pSphere1"], "/tmp/bake", resolution=0)
        assert result["success"] is False

    def test_object_not_found(self):
        _, cmds_mock, _, modules = _make_maya_env()
        cmds_mock.objExists.return_value = False
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-texture-bake", "bake_textures")
            result = mod.bake_textures(["ghost"], "/tmp/bake")
        assert result["success"] is False


class TestSetColorManagement:
    def test_enable_cm(self):
        _, cmds_mock, _, modules = _make_maya_env()
        cmds_mock.colorManagementPrefs.return_value = True
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-texture-bake", "set_color_management")
            result = mod.set_color_management(enabled=True)
        assert result["success"] is True

    def test_disable_cm(self):
        _, cmds_mock, _, modules = _make_maya_env()
        cmds_mock.colorManagementPrefs.return_value = False
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-texture-bake", "set_color_management")
            result = mod.set_color_management(enabled=False)
        assert result["success"] is True

    def test_set_with_spaces(self):
        _, cmds_mock, _, modules = _make_maya_env()
        cmds_mock.colorManagementPrefs.return_value = "sRGB"
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-texture-bake", "set_color_management")
            result = mod.set_color_management(
                input_color_space="sRGB",
                rendering_space="ACEScg",
                output_transform="sRGB gamma",
            )
        assert result["success"] is True

    def test_exception(self):
        _, cmds_mock, _, modules = _make_maya_env()
        cmds_mock.colorManagementPrefs.side_effect = RuntimeError("OCIO error")
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-texture-bake", "set_color_management")
            result = mod.set_color_management()
        assert result["success"] is False


class TestListColorSpaces:
    def test_list_spaces(self):
        _, cmds_mock, _, modules = _make_maya_env()
        cmds_mock.colorManagementPrefs.return_value = ["sRGB", "ACEScg", "linear"]
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-texture-bake", "list_color_spaces")
            result = mod.list_color_spaces()
        assert result["success"] is True
        assert "input_color_spaces" in result["context"]
        assert "rendering_spaces" in result["context"]

    def test_list_empty(self):
        _, cmds_mock, _, modules = _make_maya_env()
        cmds_mock.colorManagementPrefs.return_value = []
        with patch.dict(sys.modules, modules):
            mod = _load_script("maya-texture-bake", "list_color_spaces")
            result = mod.list_color_spaces()
        assert result["success"] is True
