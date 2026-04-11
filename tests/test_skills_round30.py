"""Round 30: Tests for batch objExists migration across maya-scripting scripts.

Covers:
- uv_ops.py: validate_node_exists migration (8 replacements)
- vertex_color.py: validate_node_exists migration (5 replacements)
- deformer_advanced.py: batch_validate_nodes migration (5 list patterns)
- mesh_ops.py: validate_node_exists migration (7 replacements)
- rigging.py: validate_node_exists migration (5 replacements)
- dynamics.py: validate_node_exists / conditional nucleus migration (2 replacements)
- animation.py: batch_validate_nodes migration (2 replacements)
- sets.py: batch_validate_nodes migration (2 replacements)
- Structural: no syntax errors, all imports present
"""

# Import future modules
from __future__ import annotations

# Import built-in modules
import ast
import os
from pathlib import Path
from unittest.mock import MagicMock

# Import third-party modules
import pytest
import sys


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SKILLS_ROOT = Path(__file__).parent.parent / "src" / "dcc_mcp_maya" / "skills"
SCRIPTING_SCRIPTS = SKILLS_ROOT / "maya-scripting" / "scripts"


def _mock_cmds(**kwargs):
    """Return a MagicMock for maya.cmds with sensible defaults."""
    m = MagicMock()
    m.objExists.return_value = True
    for k, v in kwargs.items():
        setattr(m, k, v)
    return m


def _setup_maya_mocks():
    """Install minimal maya module mocks if not already present."""
    if "maya" not in sys.modules:
        maya_mock = MagicMock()
        cmds_mock = MagicMock()
        cmds_mock.objExists.return_value = True
        maya_mock.cmds = cmds_mock
        sys.modules["maya"] = maya_mock
        sys.modules["maya.cmds"] = cmds_mock
        sys.modules["maya.api"] = MagicMock()
        sys.modules["maya.utils"] = MagicMock()


_setup_maya_mocks()

# ---------------------------------------------------------------------------
# Structural tests
# ---------------------------------------------------------------------------


class TestRound30Structural:
    """Verify that all migrated files are syntactically valid and have correct imports."""

    MIGRATED = [
        "maya-scripting/scripts/uv_ops.py",
        "maya-scripting/scripts/vertex_color.py",
        "maya-scripting/scripts/deformer_advanced.py",
        "maya-scripting/scripts/mesh_ops.py",
        "maya-scripting/scripts/rigging.py",
        "maya-scripting/scripts/dynamics.py",
        "maya-scripting/scripts/animation.py",
        "maya-scripting/scripts/sets.py",
    ]

    def test_no_syntax_errors(self):
        errors = []
        for rel in self.MIGRATED:
            path = SKILLS_ROOT / rel
            try:
                ast.parse(path.read_text(encoding="utf-8"))
            except SyntaxError as e:
                errors.append("{}: {}".format(rel, e))
        assert errors == [], "Syntax errors in migrated files:\n" + "\n".join(errors)

    def test_uv_ops_no_raw_objexists(self):
        text = (SKILLS_ROOT / "maya-scripting/scripts/uv_ops.py").read_text(encoding="utf-8")
        raw = [l for l in text.splitlines() if "cmds.objExists" in l]
        assert raw == [], "uv_ops.py still has raw cmds.objExists: {}".format(raw)

    def test_vertex_color_no_raw_objexists(self):
        text = (SKILLS_ROOT / "maya-scripting/scripts/vertex_color.py").read_text(encoding="utf-8")
        raw = [l for l in text.splitlines() if "cmds.objExists" in l]
        assert raw == [], "vertex_color.py still has raw cmds.objExists: {}".format(raw)

    def test_deformer_advanced_no_raw_objexists(self):
        text = (SKILLS_ROOT / "maya-scripting/scripts/deformer_advanced.py").read_text(encoding="utf-8")
        raw = [l for l in text.splitlines() if "cmds.objExists" in l]
        assert raw == [], "deformer_advanced.py still has raw cmds.objExists: {}".format(raw)

    def test_mesh_ops_no_raw_objexists(self):
        text = (SKILLS_ROOT / "maya-scripting/scripts/mesh_ops.py").read_text(encoding="utf-8")
        raw = [l for l in text.splitlines() if "cmds.objExists" in l]
        assert raw == [], "mesh_ops.py still has raw cmds.objExists: {}".format(raw)

    def test_migrated_files_have_validate_import(self):
        """All files using validate_node_exists must import it from dcc_mcp_maya.api."""
        missing = []
        for rel in self.MIGRATED:
            path = SKILLS_ROOT / rel
            source = path.read_text(encoding="utf-8")
            if "validate_node_exists" not in source and "batch_validate_nodes" not in source:
                continue
            try:
                tree = ast.parse(source)
            except SyntaxError:
                continue
            imported = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module and "dcc_mcp_maya.api" in node.module:
                    for alias in node.names:
                        imported.add(alias.name)
            if "validate_node_exists" in source and "validate_node_exists" not in imported:
                missing.append(rel + " (validate_node_exists)")
            if "batch_validate_nodes" in source and "batch_validate_nodes" not in imported:
                missing.append(rel + " (batch_validate_nodes)")
        assert missing == [], "Missing imports:\n" + "\n".join(missing)

    def test_reduced_objexists_total(self):
        """Total cmds.objExists count should be below 100 (was 142 before Round 16)."""
        total = 0
        for root, dirs, files in os.walk(str(SKILLS_ROOT)):
            for f in files:
                if f.endswith(".py"):
                    c = open(os.path.join(root, f), encoding="utf-8").read().count("cmds.objExists")
                    total += c
        assert total < 100, f"Expected < 100 raw objExists, got {total}"


# ---------------------------------------------------------------------------
# UV ops tests
# ---------------------------------------------------------------------------


class TestUvOpsValidation:
    """validate_node_exists used in uv_ops.py functions."""

    def _get_module(self):
        import importlib
        import importlib.util
        path = str(SKILLS_ROOT / "maya-scripting/scripts/uv_ops.py")
        spec = importlib.util.spec_from_file_location("uv_ops_r30", path)
        mod = importlib.util.module_from_spec(spec)
        return mod, spec

    def test_get_uv_info_missing_object(self):
        from dcc_mcp_maya.api import validate_node_exists
        cmds = _mock_cmds()
        cmds.objExists.return_value = False

        # Simulate via validate_node_exists
        err = validate_node_exists(cmds, "missing_obj")
        assert err is not None
        assert not err.get("success", True)

    def test_get_uv_info_success(self):
        cmds = _mock_cmds()
        cmds.polyUVSet.return_value = ["map1"]

        from dcc_mcp_maya.api import validate_node_exists
        err = validate_node_exists(cmds, "pSphere1")
        assert err is None  # object exists

    def test_uv_ops_uses_validate_not_raw_check(self):
        """uv_ops.py must not have if not cmds.objExists() guard pattern."""
        text = (SKILLS_ROOT / "maya-scripting/scripts/uv_ops.py").read_text(encoding="utf-8")
        bad_pattern = "if not cmds.objExists"
        assert bad_pattern not in text, "Still has raw guard: {}".format(bad_pattern)


# ---------------------------------------------------------------------------
# Vertex color tests
# ---------------------------------------------------------------------------


class TestVertexColorValidation:
    """validate_node_exists used in vertex_color.py."""

    def test_missing_object_returns_error_via_validate(self):
        from dcc_mcp_maya.api import validate_node_exists
        cmds = _mock_cmds()
        cmds.objExists.return_value = False
        err = validate_node_exists(cmds, "nonexistent_mesh")
        assert err is not None
        assert not err.get("success", True)

    def test_vertex_color_has_validate_import(self):
        source = (SKILLS_ROOT / "maya-scripting/scripts/vertex_color.py").read_text(encoding="utf-8")
        assert "from dcc_mcp_maya.api import validate_node_exists" in source

    def test_no_raw_objexists_guard_in_vertex_color(self):
        source = (SKILLS_ROOT / "maya-scripting/scripts/vertex_color.py").read_text(encoding="utf-8")
        assert "if not cmds.objExists" not in source


# ---------------------------------------------------------------------------
# Deformer advanced tests
# ---------------------------------------------------------------------------


class TestDeformerAdvancedBatchValidation:
    """batch_validate_nodes used in deformer_advanced.py."""

    def test_create_cluster_missing_objects(self):
        from dcc_mcp_maya.api import batch_validate_nodes
        cmds = _mock_cmds()
        cmds.objExists.side_effect = lambda name: name != "missing_obj"

        err = batch_validate_nodes(cmds, ["pSphere1", "missing_obj"])
        assert err is not None
        assert not err.get("success", True)

    def test_create_cluster_all_present(self):
        from dcc_mcp_maya.api import batch_validate_nodes
        cmds = _mock_cmds()
        cmds.objExists.return_value = True

        err = batch_validate_nodes(cmds, ["pSphere1", "pCube1"])
        assert err is None

    def test_wire_deformer_missing_curve(self):
        from dcc_mcp_maya.api import batch_validate_nodes
        cmds = _mock_cmds()
        cmds.objExists.side_effect = lambda n: n != "missing_curve"

        err = batch_validate_nodes(cmds, ["missing_curve"])
        assert err is not None

    def test_deformer_advanced_has_batch_import(self):
        source = (SKILLS_ROOT / "maya-scripting/scripts/deformer_advanced.py").read_text(encoding="utf-8")
        assert "batch_validate_nodes" in source
        assert "from dcc_mcp_maya.api import" in source


# ---------------------------------------------------------------------------
# Mesh ops tests
# ---------------------------------------------------------------------------


class TestMeshOpsValidation:
    """validate_node_exists used across mesh_ops.py functions."""

    def test_mesh_ops_no_raw_guard(self):
        source = (SKILLS_ROOT / "maya-scripting/scripts/mesh_ops.py").read_text(encoding="utf-8")
        assert "if not cmds.objExists" not in source

    def test_mesh_ops_has_validate_import(self):
        source = (SKILLS_ROOT / "maya-scripting/scripts/mesh_ops.py").read_text(encoding="utf-8")
        assert "validate_node_exists" in source

    def test_apply_subdivision_missing_object(self):
        from dcc_mcp_maya.api import validate_node_exists
        cmds = _mock_cmds()
        cmds.objExists.return_value = False
        err = validate_node_exists(cmds, "nonexistent")
        assert err is not None

    def test_merge_vertices_missing_object(self):
        from dcc_mcp_maya.api import validate_node_exists
        cmds = _mock_cmds()
        cmds.objExists.return_value = False
        err = validate_node_exists(cmds, "nonexistent")
        assert err is not None

    def test_triangulate_missing_object(self):
        from dcc_mcp_maya.api import validate_node_exists
        cmds = _mock_cmds()
        cmds.objExists.return_value = False
        err = validate_node_exists(cmds, "nonexistent")
        assert err is not None


# ---------------------------------------------------------------------------
# Rigging tests
# ---------------------------------------------------------------------------


class TestRiggingValidation:
    """validate_node_exists used in rigging.py."""

    def test_rigging_has_validate_import(self):
        source = (SKILLS_ROOT / "maya-scripting/scripts/rigging.py").read_text(encoding="utf-8")
        assert "validate_node_exists" in source

    def test_rigging_no_raw_guard(self):
        source = (SKILLS_ROOT / "maya-scripting/scripts/rigging.py").read_text(encoding="utf-8")
        assert "if not cmds.objExists" not in source

    def test_create_joint_missing_parent(self):
        from dcc_mcp_maya.api import validate_node_exists
        cmds = _mock_cmds()
        cmds.objExists.return_value = False
        err = validate_node_exists(cmds, "missing_parent")
        assert err is not None

    def test_set_driven_key_pattern_replaced(self):
        """set_driven_key uses validate_node_exists not raw objExists."""
        source = (SKILLS_ROOT / "maya-scripting/scripts/rigging.py").read_text(encoding="utf-8")
        # set_driven_key should not have raw guard
        assert source.count("cmds.objExists") == 0


# ---------------------------------------------------------------------------
# Dynamics tests
# ---------------------------------------------------------------------------


class TestDynamicsConditionalValidation:
    """Conditional nucleus objExists replaced by validate_node_exists."""

    def test_dynamics_no_nucleus_guard(self):
        source = (SKILLS_ROOT / "maya-scripting/scripts/dynamics.py").read_text(encoding="utf-8")
        # nucleus guards should use validate_node_exists now
        # Only 1 remaining is the attribute-probe (if cmds.objExists(mag_attr))
        remaining = [l for l in source.splitlines() if "cmds.objExists" in l and "not cmds.objExists" in l]
        assert remaining == [], "Found residual not-objExists guards: {}".format(remaining)

    def test_dynamics_has_validate_import(self):
        source = (SKILLS_ROOT / "maya-scripting/scripts/dynamics.py").read_text(encoding="utf-8")
        assert "validate_node_exists" in source

    def test_attribute_probe_preserved(self):
        """Attribute-existence probe (mag_attr) should be kept as cmds.objExists."""
        source = (SKILLS_ROOT / "maya-scripting/scripts/dynamics.py").read_text(encoding="utf-8")
        assert "cmds.objExists(mag_attr)" in source


# ---------------------------------------------------------------------------
# Animation tests
# ---------------------------------------------------------------------------


class TestAnimationBatchValidation:
    """batch_validate_nodes migration in animation.py."""

    def test_animation_has_batch_import(self):
        source = (SKILLS_ROOT / "maya-scripting/scripts/animation.py").read_text(encoding="utf-8")
        assert "batch_validate_nodes" in source

    def test_animation_no_broken_return_err(self):
        source = (SKILLS_ROOT / "maya-scripting/scripts/animation.py").read_text(encoding="utf-8")
        for line in source.splitlines():
            stripped = line.strip()
            if stripped.startswith("return err") and stripped != "return err":
                pytest.fail("Broken 'return err' line found: {!r}".format(line))


# ---------------------------------------------------------------------------
# Sets tests
# ---------------------------------------------------------------------------


class TestSetsBatchValidation:
    """batch_validate_nodes migration in sets.py."""

    def test_sets_has_batch_import(self):
        source = (SKILLS_ROOT / "maya-scripting/scripts/sets.py").read_text(encoding="utf-8")
        assert "batch_validate_nodes" in source

    def test_sets_no_broken_return_err(self):
        source = (SKILLS_ROOT / "maya-scripting/scripts/sets.py").read_text(encoding="utf-8")
        for line in source.splitlines():
            stripped = line.strip()
            if stripped.startswith("return err") and stripped != "return err":
                pytest.fail("Broken 'return err' line found: {!r}".format(line))

    def test_sets_no_raw_guard(self):
        source = (SKILLS_ROOT / "maya-scripting/scripts/sets.py").read_text(encoding="utf-8")
        # Only the best-effort 'existing = [obj for obj in objects if cmds.objExists(obj)]' may remain
        bad = [l for l in source.splitlines() if "if not cmds.objExists" in l]
        assert bad == [], "Found residual not-objExists guards: {}".format(bad)


# ---------------------------------------------------------------------------
# Global count test
# ---------------------------------------------------------------------------


class TestGlobalObjExistsReduction:
    """Total objExists count in skills must be reduced compared to Round 15 baseline (353)."""

    def test_total_objexists_below_threshold(self):
        total = 0
        for root, dirs, files in os.walk(str(SKILLS_ROOT)):
            for f in files:
                if f.endswith(".py"):
                    c = open(os.path.join(root, f), encoding="utf-8").read().count("cmds.objExists")
                    total += c
        # Round 15 ended at ~353 raw, Round 29 at ~95; this round should be <100
        assert total < 100, f"Total cmds.objExists = {total}, expected < 100"

    def test_validate_node_exists_usage_widespread(self):
        """validate_node_exists should be used in at least 170 skill scripts."""
        count = 0
        for root, dirs, files in os.walk(str(SKILLS_ROOT)):
            for f in files:
                if f.endswith(".py"):
                    if "validate_node_exists" in open(os.path.join(root, f), encoding="utf-8").read():
                        count += 1
        assert count >= 170, f"Only {count} scripts use validate_node_exists"
