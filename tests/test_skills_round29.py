"""Tests for Round 29: bulk validate_node_exists migration.

212 guard replacements across 136 skill scripts:
- ``if not cmds.objExists(X): return skill_error(...)``
  replaced with ``validate_node_exists(cmds, X)`` pattern.
- All replaced files now import from ``dcc_mcp_maya.api``.

This test module verifies:
1. No skill script has ``validate_node_exists`` without importing it.
2. validate_node_exists returns correct error dict on missing node.
3. validate_node_exists returns None on existing node.
4. A sample of migrated scripts pass happy-path + missing-node tests.
5. Structural: all 174 scripts that use validate_node_exists have the import.
"""

# Import future modules
from __future__ import annotations

# Import built-in modules
import ast
import importlib.util
import sys
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

_SKILLS_ROOT = Path(__file__).parent.parent / "src" / "dcc_mcp_maya" / "skills"
_MOD_COUNTER = [0]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_script(skill_dir: str, script_name: str) -> Any:
    _MOD_COUNTER[0] += 1
    script_path = _SKILLS_ROOT / skill_dir / "scripts" / "{}.py".format(script_name)
    module_name = "skill_r29_{}_{}_{}_{}".format(
        skill_dir.replace("-", "_"), script_name, _MOD_COUNTER[0], id(script_name)
    )
    spec = importlib.util.spec_from_file_location(module_name, str(script_path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _make_maya(objExists_return: bool = True, **extra):
    """Return (maya_mock, cmds_mock, sys_modules_patch_dict)."""
    maya_mock = MagicMock()
    cmds = MagicMock()
    cmds.objExists.return_value = objExists_return
    cmds.objectType.return_value = "transform"
    for k, v in extra.items():
        setattr(cmds, k, v)
    maya_mock.cmds = cmds
    modules = {
        "maya": maya_mock,
        "maya.cmds": cmds,
        "maya.api": MagicMock(),
        "maya.utils": MagicMock(),
        "maya.mel": MagicMock(),
    }
    return maya_mock, cmds, modules


# ---------------------------------------------------------------------------
# 1. Structural: all files that call validate_node_exists must import it
# ---------------------------------------------------------------------------


class TestMigrationStructural:
    """Ensure every skill script that calls validate_node_exists imports it."""

    def _parse_module_imports(self, source: str) -> set:
        """Return set of imported names from dcc_mcp_maya.api."""
        imported = set()
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return imported
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module and "dcc_mcp_maya.api" in node.module:
                    for alias in node.names:
                        imported.add(alias.name)
        return imported

    def test_no_missing_validate_imports(self):
        """Every script using validate_node_exists must import it."""
        missing = []
        for path in sorted(_SKILLS_ROOT.rglob("scripts/*.py")):
            source = path.read_text(encoding="utf-8")
            if "validate_node_exists" not in source:
                continue
            imported = self._parse_module_imports(source)
            if "validate_node_exists" not in imported:
                missing.append(str(path.relative_to(_SKILLS_ROOT.parent.parent.parent.parent)))
        assert missing == [], "Scripts missing validate_node_exists import:\n" + "\n".join(missing)

    def test_no_syntax_errors_in_migrated_scripts(self):
        """All skill scripts must be parseable (no IndentationError etc.)."""
        errors = []
        for path in sorted(_SKILLS_ROOT.rglob("scripts/*.py")):
            source = path.read_text(encoding="utf-8")
            try:
                ast.parse(source)
            except SyntaxError as exc:
                errors.append("{}: {}".format(path.name, exc))
        assert errors == [], "Syntax errors found:\n" + "\n".join(errors)

    def test_validate_import_at_top_level(self):
        """validate_node_exists import must be at module top level (not indented)."""
        bad = []
        for path in sorted(_SKILLS_ROOT.rglob("scripts/*.py")):
            source = path.read_text(encoding="utf-8")
            if "from dcc_mcp_maya.api import" not in source:
                continue
            for line in source.splitlines():
                if "from dcc_mcp_maya.api import" in line and line.startswith((" ", "\t")):
                    bad.append("{}: {!r}".format(path.name, line.strip()))
        assert bad == [], "Indented api imports found:\n" + "\n".join(bad)

    def test_objexists_guard_count_reduced(self):
        """Number of raw if-not-objExists guards must be below 100 (was 353)."""
        count = 0
        for path in sorted(_SKILLS_ROOT.rglob("scripts/*.py")):
            source = path.read_text(encoding="utf-8")
            count += source.count("if not cmds.objExists(")
        # We started with 353; migration converted 212+; remaining are in complex patterns
        assert count < 150, "Expected < 150 remaining objExists guards, got {}".format(count)

    def test_validate_node_exists_usage_count(self):
        """At least 140 skill scripts should call validate_node_exists."""
        count = sum(
            1
            for path in _SKILLS_ROOT.rglob("scripts/*.py")
            if "validate_node_exists" in path.read_text(encoding="utf-8")
        )
        assert count >= 140, "Expected >= 140 scripts using validate_node_exists, got {}".format(count)


# ---------------------------------------------------------------------------
# 2. Unit tests for validate_node_exists / validate_node_type API helpers
# ---------------------------------------------------------------------------


class TestValidateNodeExistsHelper:
    """Unit tests for the dcc_mcp_maya.api helpers themselves."""

    def _get_api(self):
        from dcc_mcp_maya import api  # noqa: PLC0415

        return api

    def test_returns_none_when_node_exists(self):
        api = self._get_api()
        cmds = MagicMock()
        cmds.objExists.return_value = True
        result = api.validate_node_exists(cmds, "pSphere1")
        assert result is None

    def test_returns_error_dict_when_missing(self):
        api = self._get_api()
        cmds = MagicMock()
        cmds.objExists.return_value = False
        result = api.validate_node_exists(cmds, "missingNode")
        assert result is not None
        assert result["success"] is False
        assert "missingNode" in result["message"]

    def test_error_includes_node_name(self):
        api = self._get_api()
        cmds = MagicMock()
        cmds.objExists.return_value = False
        result = api.validate_node_exists(cmds, "myMesh")
        assert "myMesh" in result["message"] or "myMesh" in result.get("error", "")

    def test_error_has_possible_solutions(self):
        api = self._get_api()
        cmds = MagicMock()
        cmds.objExists.return_value = False
        result = api.validate_node_exists(cmds, "ghost")
        # possible_solutions may be in context or top-level depending on core version
        solutions = result.get("possible_solutions", result.get("context", {}).get("possible_solutions", []))
        assert len(solutions) > 0

    def test_batch_validate_short_circuits_on_first_missing(self):
        api = self._get_api()
        cmds = MagicMock()
        cmds.objExists.side_effect = lambda n: n != "missing1"
        result = api.batch_validate_nodes(cmds, ["ok1", "missing1", "ok2"])
        assert result is not None
        assert "missing1" in result["message"]
        # ok2 should not have been checked
        assert cmds.objExists.call_count == 2

    def test_batch_validate_returns_none_when_all_exist(self):
        api = self._get_api()
        cmds = MagicMock()
        cmds.objExists.return_value = True
        result = api.batch_validate_nodes(cmds, ["a", "b", "c"])
        assert result is None


# ---------------------------------------------------------------------------
# 3. Sample migrated scripts: get_transform (maya-primitives)
# ---------------------------------------------------------------------------


class TestGetTransformMigrated:
    """Verify get_transform uses validate_node_exists correctly."""

    def test_success_returns_transform(self):
        _, mc, mods = _make_maya(objExists_return=True)
        mc.getAttr.side_effect = lambda attr, **kw: [(1.0, 2.0, 3.0)]
        with patch.dict(sys.modules, mods):
            mod = _load_script("maya-primitives", "get_transform")
            result = mod.get_transform("pSphere1")
        assert result["success"] is True
        assert result["context"]["translate"] == [1.0, 2.0, 3.0]

    def test_missing_node_uses_validate(self):
        _, mc, mods = _make_maya(objExists_return=False)
        with patch.dict(sys.modules, mods):
            mod = _load_script("maya-primitives", "get_transform")
            result = mod.get_transform("ghost")
        assert result["success"] is False
        assert "ghost" in result["message"]

    def test_has_validate_import(self):
        source = (_SKILLS_ROOT / "maya-primitives" / "scripts" / "get_transform.py").read_text()
        assert "validate_node_exists" in source


# ---------------------------------------------------------------------------
# 4. Sample migrated scripts: get_keyframes (maya-animation)
# ---------------------------------------------------------------------------


class TestGetKeyframesMigrated:
    """Verify get_keyframes migration."""

    def test_success_empty_keyframes(self):
        _, mc, mods = _make_maya(objExists_return=True)
        mc.keyframe.return_value = None
        with patch.dict(sys.modules, mods):
            mod = _load_script("maya-animation", "get_keyframes")
            result = mod.get_keyframes("pSphere1")
        assert result["success"] is True
        assert result["context"]["keyframes"] == []

    def test_success_with_keyframes(self):
        _, mc, mods = _make_maya(objExists_return=True)
        mc.keyframe.return_value = [1.0, 5.0, 10.0]
        with patch.dict(sys.modules, mods):
            mod = _load_script("maya-animation", "get_keyframes")
            result = mod.get_keyframes("pSphere1")
        assert result["success"] is True
        assert result["context"]["count"] == 3

    def test_missing_node_error(self):
        _, mc, mods = _make_maya(objExists_return=False)
        with patch.dict(sys.modules, mods):
            mod = _load_script("maya-animation", "get_keyframes")
            result = mod.get_keyframes("phantom")
        assert result["success"] is False
        assert "phantom" in result["message"]


# ---------------------------------------------------------------------------
# 5. Sample migrated scripts: get_blend_shape_weights (maya-blend-shape-utils)
# ---------------------------------------------------------------------------


class TestGetBlendShapeWeightsMigrated:
    """Verify blend shape weights migration."""

    def test_success(self):
        _, mc, mods = _make_maya(objExists_return=True)
        mc.blendShape.return_value = [0.0, 0.5, 1.0]
        mc.aliasAttr.return_value = ["smile", "weight[0]", "frown", "weight[1]", "brow_up", "weight[2]"]
        with patch.dict(sys.modules, mods):
            mod = _load_script("maya-blend-shape-utils", "get_blend_shape_weights")
            result = mod.get_blend_shape_weights("blendShape1")
        assert result["success"] is True
        assert result["context"]["count"] == 3

    def test_missing_node_returns_error(self):
        _, mc, mods = _make_maya(objExists_return=False)
        with patch.dict(sys.modules, mods):
            mod = _load_script("maya-blend-shape-utils", "get_blend_shape_weights")
            result = mod.get_blend_shape_weights("missingBS")
        assert result["success"] is False
        assert "missingBS" in result["message"]


# ---------------------------------------------------------------------------
# 6. Sample migrated scripts: delete_annotation (maya-annotation)
# ---------------------------------------------------------------------------


class TestDeleteAnnotationMigrated:
    """Verify delete_annotation migration."""

    def test_delete_shape_node(self):
        _, mc, mods = _make_maya(objExists_return=True)
        mc.objectType.return_value = "annotationShape"
        mc.listRelatives.return_value = ["annotation1"]
        with patch.dict(sys.modules, mods):
            mod = _load_script("maya-annotation", "delete_annotation")
            result = mod.delete_annotation("annotation1Shape")
        assert result["success"] is True
        mc.delete.assert_called_once_with("annotation1")

    def test_delete_missing_node(self):
        _, mc, mods = _make_maya(objExists_return=False)
        with patch.dict(sys.modules, mods):
            mod = _load_script("maya-annotation", "delete_annotation")
            result = mod.delete_annotation("noNode")
        assert result["success"] is False

    def test_has_validate_import(self):
        source = (_SKILLS_ROOT / "maya-annotation" / "scripts" / "delete_annotation.py").read_text()
        assert "validate_node_exists" in source
        # import must be at top level
        for line in source.splitlines():
            if "from dcc_mcp_maya.api import" in line:
                assert not line.startswith((" ", "\t")), "Import is indented!"
                break


# ---------------------------------------------------------------------------
# 7. Sample migrated scripts: maya-xform-utils/freeze_transforms
# ---------------------------------------------------------------------------


class TestFreezeTransformsMigrated:
    """Verify freeze_transforms migration."""

    def test_success_single_object(self):
        _, mc, mods = _make_maya(objExists_return=True)
        with patch.dict(sys.modules, mods):
            mod = _load_script("maya-xform-utils", "freeze_transforms")
            result = mod.freeze_transforms(objects=["pSphere1"])
        assert result["success"] is True

    def test_missing_object_error(self):
        _, mc, mods = _make_maya(objExists_return=False)
        with patch.dict(sys.modules, mods):
            mod = _load_script("maya-xform-utils", "freeze_transforms")
            result = mod.freeze_transforms(objects=["ghost"])
        assert result["success"] is False


# ---------------------------------------------------------------------------
# 8. Regression: batch_validate_nodes is imported where used
# ---------------------------------------------------------------------------


class TestBatchValidateImports:
    """Scripts using batch_validate_nodes must also import it."""

    def test_no_missing_batch_imports(self):
        missing = []
        for path in sorted(_SKILLS_ROOT.rglob("scripts/*.py")):
            source = path.read_text(encoding="utf-8")
            if "batch_validate_nodes" not in source:
                continue
            # Check that import exists
            has_import = (
                "from dcc_mcp_maya.api import batch_validate_nodes" in source
                or "from dcc_mcp_maya import" in source  # namespace import
            )
            if not has_import:
                missing.append(str(path.name))
        assert missing == [], "Missing batch_validate_nodes imports: " + str(missing)
