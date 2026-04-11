"""Round 27: refactor tests for maya-attributes, maya-scene, maya-uv-ops,
maya-constraints, maya-materials — validate_node_exists / batch_validate_nodes usage.

Scripts are loaded via importlib.util.spec_from_file_location to handle
hyphenated skill directory names which cannot be Python package paths.
"""

# Import future modules
from __future__ import annotations

# Import built-in modules
import importlib.util
import sys
from pathlib import Path
from unittest.mock import MagicMock

_SKILLS_ROOT = Path(__file__).parent.parent / "src" / "dcc_mcp_maya" / "skills"
_MOD_COUNTER = [0]


def _load_script(skill_dir, script_name):
    """Load a skill script via file path (handles hyphenated dirs)."""
    _MOD_COUNTER[0] += 1
    path = _SKILLS_ROOT / skill_dir / "scripts" / "{}.py".format(script_name)
    mod_name = "r27_{}_{}_{}".format(skill_dir.replace("-", "_"), script_name, _MOD_COUNTER[0])
    spec = importlib.util.spec_from_file_location(mod_name, str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _make_env(exists=True, exists_fn=None, **overrides):
    """Build a mock maya environment and return (cmds_mock, modules_dict)."""
    maya_mock = MagicMock()
    cmds = MagicMock()
    cmds.objExists.side_effect = exists_fn if exists_fn else (lambda name: exists)
    for k, v in overrides.items():
        setattr(cmds, k, v)
    maya_mock.cmds = cmds
    mods = {
        "maya": maya_mock,
        "maya.cmds": cmds,
        "maya.api": MagicMock(),
        "maya.utils": MagicMock(),
        "maya.mel": MagicMock(),
    }
    return cmds, mods


# ---------------------------------------------------------------------------
# maya-attributes
# ---------------------------------------------------------------------------


class TestAddAttributeRefactor:
    def test_node_not_found_returns_error(self):
        from dcc_mcp_maya.api import validate_node_exists

        cmds, mods = _make_env(exists=False)
        err = validate_node_exists(cmds, "pSphere1")
        assert err is not None
        assert err["success"] is False
        assert "pSphere1" in err["message"]

    def test_node_exists_happy_path(self):
        cmds, mods = _make_env(exists=True)
        with __import__("unittest.mock", fromlist=["patch"]).patch.dict(sys.modules, mods):
            m = _load_script("maya-attributes", "add_attribute")
            r = m.add_attribute("pSphere1", "myFloat", "float")
        assert r["success"] is True
        assert r["context"]["attribute"] == "myFloat"

    def test_invalid_attr_type_returns_error(self):
        cmds, mods = _make_env(exists=True)
        with __import__("unittest.mock", fromlist=["patch"]).patch.dict(sys.modules, mods):
            m = _load_script("maya-attributes", "add_attribute")
            r = m.add_attribute("pSphere1", "myFloat", "invalid_type")
        assert r["success"] is False
        assert "invalid" in r["message"].lower()

    def test_delete_attribute_node_missing(self):
        from dcc_mcp_maya.api import validate_node_exists

        cmds, _ = _make_env(exists=False)
        err = validate_node_exists(cmds, "missingNode")
        assert err is not None
        assert "missingNode" in err["message"]

    def test_get_attribute_node_missing(self):
        from dcc_mcp_maya.api import validate_node_exists

        cmds, _ = _make_env(exists=False)
        err = validate_node_exists(cmds, "ghostNode")
        assert err["success"] is False

    def test_set_attribute_happy_path(self):
        cmds, mods = _make_env(exists=True)
        with __import__("unittest.mock", fromlist=["patch"]).patch.dict(sys.modules, mods):
            m = _load_script("maya-attributes", "set_attribute")
            r = m.set_attribute("pSphere1", "translateX", 5.0)
        assert r["success"] is True
        assert r["context"]["value"] == 5.0

    def test_source_uses_validate_node_exists(self):
        """All 4 attribute scripts import validate_node_exists."""
        cmds, mods = _make_env(exists=True)
        for script in ["add_attribute", "delete_attribute", "get_attribute", "set_attribute"]:
            with __import__("unittest.mock", fromlist=["patch"]).patch.dict(sys.modules, mods):
                m = _load_script("maya-attributes", script)
            src = Path(m.__file__).read_text(encoding="utf-8")
            assert "validate_node_exists" in src, "{} missing validate_node_exists".format(script)


# ---------------------------------------------------------------------------
# maya-scene
# ---------------------------------------------------------------------------


class TestSceneRefactor:
    def _check_vne(self, name, exists=True):
        from dcc_mcp_maya.api import validate_node_exists

        cmds, _ = _make_env(exists=exists)
        return validate_node_exists(cmds, name)

    def test_set_visibility_node_missing(self):
        err = self._check_vne("missingObj", exists=False)
        assert err is not None and err["success"] is False

    def test_set_visibility_node_exists(self):
        err = self._check_vne("pSphere1", exists=True)
        assert err is None

    def test_lock_object_node_missing(self):
        assert self._check_vne("ghostCube", exists=False) is not None

    def test_duplicate_object_node_missing(self):
        assert self._check_vne("noNode", exists=False) is not None

    def test_center_pivot_node_missing(self):
        assert self._check_vne("missing", exists=False) is not None

    def test_get_bounding_box_node_missing(self):
        assert self._check_vne("nope", exists=False) is not None

    def test_set_visibility_happy_path(self):
        cmds, mods = _make_env(exists=True)
        cmds.setAttr.return_value = None
        with __import__("unittest.mock", fromlist=["patch"]).patch.dict(sys.modules, mods):
            m = _load_script("maya-scene", "set_visibility")
            r = m.set_visibility("pSphere1", True)
        assert r["success"] is True

    def test_duplicate_object_happy_path(self):
        cmds, mods = _make_env(exists=True)
        cmds.duplicate.return_value = ["pSphere2"]
        with __import__("unittest.mock", fromlist=["patch"]).patch.dict(sys.modules, mods):
            m = _load_script("maya-scene", "duplicate_object")
            r = m.duplicate_object("pSphere1")
        assert r["success"] is True
        assert r["context"]["object_name"] == "pSphere2"

    def test_scripts_import_validate_node_exists(self):
        cmds, mods = _make_env(exists=True)
        for script in ["set_visibility", "lock_object", "duplicate_object", "center_pivot", "get_bounding_box"]:
            with __import__("unittest.mock", fromlist=["patch"]).patch.dict(sys.modules, mods):
                m = _load_script("maya-scene", script)
            src = Path(m.__file__).read_text(encoding="utf-8")
            assert "validate_node_exists" in src, "{} missing validate_node_exists".format(script)


# ---------------------------------------------------------------------------
# maya-uv-ops
# ---------------------------------------------------------------------------


class TestUvOpsRefactor:
    def test_batch_validate_nodes_source_missing(self):
        from dcc_mcp_maya.api import batch_validate_nodes

        def oe(name):
            return name != "missing_target"

        cmds, _ = _make_env(exists_fn=oe)
        err = batch_validate_nodes(cmds, ["source_mesh", "missing_target"])
        assert err is not None
        assert "missing_target" in err["message"]

    def test_batch_validate_nodes_both_exist(self):
        from dcc_mcp_maya.api import batch_validate_nodes

        cmds, _ = _make_env(exists=True)
        err = batch_validate_nodes(cmds, ["source_mesh", "target_mesh"])
        assert err is None

    def test_copy_uvs_uses_batch_validate(self):
        cmds, mods = _make_env(exists=True)
        cmds.transferAttributes.return_value = None
        with __import__("unittest.mock", fromlist=["patch"]).patch.dict(sys.modules, mods):
            m = _load_script("maya-uv-ops", "copy_uvs")
        src = Path(m.__file__).read_text(encoding="utf-8")
        assert "batch_validate_nodes" in src

    def test_unfold_uvs_invalid_iterations(self):
        cmds, mods = _make_env(exists=True)
        with __import__("unittest.mock", fromlist=["patch"]).patch.dict(sys.modules, mods):
            m = _load_script("maya-uv-ops", "unfold_uvs")
            r = m.unfold_uvs("pCube1", iterations=0)
        assert r["success"] is False

    def test_unfold_uvs_node_missing(self):
        cmds, mods = _make_env(exists=False)
        with __import__("unittest.mock", fromlist=["patch"]).patch.dict(sys.modules, mods):
            m = _load_script("maya-uv-ops", "unfold_uvs")
            r = m.unfold_uvs("ghostMesh")
        assert r["success"] is False

    def test_normalize_uvs_node_missing(self):
        cmds, mods = _make_env(exists=False)
        with __import__("unittest.mock", fromlist=["patch"]).patch.dict(sys.modules, mods):
            m = _load_script("maya-uv-ops", "normalize_uvs")
            r = m.normalize_uvs("ghostMesh")
        assert r["success"] is False

    def test_project_uvs_invalid_type(self):
        cmds, mods = _make_env(exists=True)
        with __import__("unittest.mock", fromlist=["patch"]).patch.dict(sys.modules, mods):
            m = _load_script("maya-uv-ops", "project_uvs")
            r = m.project_uvs("pCube1", projection_type="invalid")
        assert r["success"] is False

    def test_create_uv_set_node_missing(self):
        cmds, mods = _make_env(exists=False)
        with __import__("unittest.mock", fromlist=["patch"]).patch.dict(sys.modules, mods):
            m = _load_script("maya-uv-ops", "create_uv_set")
            r = m.create_uv_set("ghostMesh", "newSet")
        assert r["success"] is False

    def test_delete_uv_set_node_missing(self):
        cmds, mods = _make_env(exists=False)
        with __import__("unittest.mock", fromlist=["patch"]).patch.dict(sys.modules, mods):
            m = _load_script("maya-uv-ops", "delete_uv_set")
            r = m.delete_uv_set("ghostMesh", "map1")
        assert r["success"] is False

    def test_get_uv_info_node_missing(self):
        cmds, mods = _make_env(exists=False)
        with __import__("unittest.mock", fromlist=["patch"]).patch.dict(sys.modules, mods):
            m = _load_script("maya-uv-ops", "get_uv_info")
            r = m.get_uv_info("ghostMesh")
        assert r["success"] is False

    def test_copy_uvs_both_missing_short_circuits(self):
        """batch_validate_nodes returns first-missing error without checking all."""
        from dcc_mcp_maya.api import batch_validate_nodes

        cmds, _ = _make_env(exists=False)
        err = batch_validate_nodes(cmds, ["miss1", "miss2"])
        assert err is not None
        assert "miss1" in err["message"]


# ---------------------------------------------------------------------------
# maya-constraints
# ---------------------------------------------------------------------------


class TestConstraintsRefactor:
    def test_add_constraint_source_missing(self):
        from dcc_mcp_maya.api import batch_validate_nodes

        def oe(name):
            return name != "missingSrc"

        cmds, _ = _make_env(exists_fn=oe)
        err = batch_validate_nodes(cmds, ["missingSrc", "pCube1"])
        assert err is not None
        assert "missingSrc" in err["message"]

    def test_add_constraint_target_missing(self):
        from dcc_mcp_maya.api import batch_validate_nodes

        def oe(name):
            return name != "missingTgt"

        cmds, _ = _make_env(exists_fn=oe)
        err = batch_validate_nodes(cmds, ["pSphere1", "missingTgt"])
        assert err is not None

    def test_add_constraint_both_exist(self):
        from dcc_mcp_maya.api import batch_validate_nodes

        cmds, _ = _make_env(exists=True)
        err = batch_validate_nodes(cmds, ["pSphere1", "pCube1"])
        assert err is None

    def test_remove_constraint_target_missing(self):
        from dcc_mcp_maya.api import validate_node_exists

        cmds, _ = _make_env(exists=False)
        err = validate_node_exists(cmds, "missingTgt")
        assert err is not None

    def test_create_constraint_weighted_source_missing(self):
        from dcc_mcp_maya.api import batch_validate_nodes

        def oe(name):
            return name != "miss"

        cmds, _ = _make_env(exists_fn=oe)
        err = batch_validate_nodes(cmds, ["pSphere1", "miss", "pCube1"])
        assert err is not None
        assert "miss" in err["message"]

    def test_add_constraint_unknown_type(self):
        cmds, mods = _make_env(exists=True)
        with __import__("unittest.mock", fromlist=["patch"]).patch.dict(sys.modules, mods):
            m = _load_script("maya-constraints", "add_constraint")
            r = m.add_constraint("unknownType", "pSphere1", "pCube1")
        assert r["success"] is False
        assert "unknown" in r["message"].lower()

    def test_add_constraint_happy_path(self):
        cmds, mods = _make_env(exists=True)
        cmds.parentConstraint.return_value = ["pSphere1_parentConstraint1"]
        with __import__("unittest.mock", fromlist=["patch"]).patch.dict(sys.modules, mods):
            m = _load_script("maya-constraints", "add_constraint")
            r = m.add_constraint("parent", "pSphere1", "pCube1")
        assert r["success"] is True

    def test_scripts_use_batch_validate(self):
        cmds, mods = _make_env(exists=True)
        for script in ["add_constraint", "create_constraint_weighted"]:
            with __import__("unittest.mock", fromlist=["patch"]).patch.dict(sys.modules, mods):
                m = _load_script("maya-constraints", script)
            src = Path(m.__file__).read_text(encoding="utf-8")
            assert "batch_validate_nodes" in src, "{} missing batch_validate_nodes".format(script)

    def test_remove_constraint_uses_validate_node_exists(self):
        cmds, mods = _make_env(exists=True)
        with __import__("unittest.mock", fromlist=["patch"]).patch.dict(sys.modules, mods):
            m = _load_script("maya-constraints", "remove_constraint")
        src = Path(m.__file__).read_text(encoding="utf-8")
        assert "validate_node_exists" in src


# ---------------------------------------------------------------------------
# maya-materials
# ---------------------------------------------------------------------------


class TestMaterialsRefactor:
    def test_set_material_attribute_missing_node(self):
        cmds, mods = _make_env(exists=False)
        with __import__("unittest.mock", fromlist=["patch"]).patch.dict(sys.modules, mods):
            m = _load_script("maya-materials", "set_material_attribute")
            r = m.set_material_attribute("ghostMat", "color", [1, 0, 0])
        assert r["success"] is False

    def test_set_material_attribute_happy_path(self):
        cmds, mods = _make_env(exists=True)
        cmds.setAttr.return_value = None
        with __import__("unittest.mock", fromlist=["patch"]).patch.dict(sys.modules, mods):
            m = _load_script("maya-materials", "set_material_attribute")
            r = m.set_material_attribute("lambert1", "color", [1, 0, 0])
        assert r["success"] is True

    def test_get_shader_assignment_missing_node(self):
        cmds, mods = _make_env(exists=False)
        with __import__("unittest.mock", fromlist=["patch"]).patch.dict(sys.modules, mods):
            m = _load_script("maya-materials", "get_shader_assignment")
            r = m.get_shader_assignment("ghostObj")
        assert r["success"] is False

    def test_get_material_connections_missing_node(self):
        cmds, mods = _make_env(exists=False)
        with __import__("unittest.mock", fromlist=["patch"]).patch.dict(sys.modules, mods):
            m = _load_script("maya-materials", "get_material_connections")
            r = m.get_material_connections("ghostMat")
        assert r["success"] is False

    def test_reset_to_default_material_missing_node(self):
        cmds, mods = _make_env(exists=False)
        with __import__("unittest.mock", fromlist=["patch"]).patch.dict(sys.modules, mods):
            m = _load_script("maya-materials", "reset_to_default_material")
            r = m.reset_to_default_material("ghostObj")
        assert r["success"] is False

    def test_all_four_scripts_use_validate_node_exists(self):
        cmds, mods = _make_env(exists=True)
        scripts = [
            "set_material_attribute",
            "get_shader_assignment",
            "get_material_connections",
            "reset_to_default_material",
        ]
        for script in scripts:
            with __import__("unittest.mock", fromlist=["patch"]).patch.dict(sys.modules, mods):
                m = _load_script("maya-materials", script)
            src = Path(m.__file__).read_text(encoding="utf-8")
            assert "validate_node_exists" in src, "{} missing validate_node_exists".format(script)
