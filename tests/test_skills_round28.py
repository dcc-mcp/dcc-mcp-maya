"""Tests for Round 28: maya-mash, maya-selection, maya-xgen skill script migration.

All 15 scripts migrated from ``def run(params)`` to typed ``def func(**kwargs) + @skill_entry``.
"""

# Import future modules
from __future__ import annotations

# Import built-in modules
import importlib.util
import sys
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

_SKILLS_ROOT = Path(__file__).parent.parent / "src" / "dcc_mcp_maya" / "skills"
_MOD_COUNTER = [0]


# ---------------------------------------------------------------------------
# Loaders / helpers
# ---------------------------------------------------------------------------


def _load_script(skill_dir: str, script_name: str) -> Any:
    """Load a skill script from its file path."""
    _MOD_COUNTER[0] += 1
    script_path = _SKILLS_ROOT / skill_dir / "scripts" / "{}.py".format(script_name)
    module_name = "skill_r28_{}_{}_{}_{}".format(
        skill_dir.replace("-", "_"), script_name, _MOD_COUNTER[0], id(script_name)
    )
    spec = importlib.util.spec_from_file_location(module_name, str(script_path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _make_maya_env(**cmds_overrides: Any):
    """Return (maya_mock, cmds_mock, modules_dict)."""
    maya_mock = MagicMock()
    cmds_mock = MagicMock()
    cmds_mock.objExists.return_value = True
    cmds_mock.ls.return_value = []
    cmds_mock.listConnections.return_value = []
    cmds_mock.setAttr.return_value = None
    cmds_mock.objectType.return_value = "transform"
    for k, v in cmds_overrides.items():
        setattr(cmds_mock, k, v)
    maya_mock.cmds = cmds_mock
    modules = {
        "maya": maya_mock,
        "maya.cmds": cmds_mock,
        "maya.api": MagicMock(),
        "maya.utils": MagicMock(),
        "maya.mel": MagicMock(),
    }
    return maya_mock, cmds_mock, modules


def _run(skill_dir: str, func_name: str, modules: dict, **kwargs):
    """Load script and call its named function with patched sys.modules."""
    mod = _load_script(skill_dir, func_name)
    fn = getattr(mod, func_name)
    original = {k: sys.modules.get(k) for k in modules}
    sys.modules.update(modules)
    try:
        return fn(**kwargs)
    finally:
        for k, v in original.items():
            if v is None:
                sys.modules.pop(k, None)
            else:
                sys.modules[k] = v


def _success(result):
    assert result["success"] is True, "Expected success but got: {}".format(result)
    return result


def _fail(result):
    assert result["success"] is False, "Expected failure but got: {}".format(result)
    return result


# ===========================================================================
# maya-mash
# ===========================================================================


def _make_mash_mods(network_mock=None, side_effect=None):
    """Build sys.modules entries for MASH."""
    mapi = MagicMock()
    if side_effect is not None:
        mapi.Network.side_effect = side_effect
    elif network_mock is not None:
        mapi.Network.return_value = network_mock
    mash_pkg = MagicMock()
    mash_pkg.api = mapi
    return {"MASH": mash_pkg, "MASH.api": mapi}


def _make_network(mesh_name="MASH1_Instancer", instancer="MASH1_Instancer", waiter="MASH1_Waiter"):
    network = MagicMock()
    network.meshName = mesh_name
    network.instancer = instancer
    network.waiter = waiter
    return network


class TestMashCreateNetwork:
    """maya-mash/scripts/create_network.py."""

    SKILL = "maya-mash"
    SCRIPT = "create_network"

    def _call(self, mods, **kwargs):
        return _run(self.SKILL, self.SCRIPT, mods, **kwargs)

    def test_happy_path(self):
        _, cmds, mods = _make_maya_env()
        mods.update(_make_mash_mods(network_mock=_make_network()))
        result = _success(self._call(mods, object_name="pSphere1"))
        assert result["context"]["waiter"] == "MASH1_Waiter"

    def test_missing_object(self):
        _, cmds, mods = _make_maya_env()
        cmds.objExists.return_value = False
        mods.update(_make_mash_mods())
        result = _fail(self._call(mods, object_name="nonexistent"))
        assert "nonexistent" in str(result)

    def test_custom_geometry_type(self):
        _, cmds, mods = _make_maya_env()
        mods.update(_make_mash_mods(network_mock=_make_network()))
        result = _success(self._call(mods, object_name="pCube1", geometry_type="Repro"))
        assert result["context"]["waiter"] == "MASH1_Waiter"

    def test_mash_exception(self):
        _, cmds, mods = _make_maya_env()
        mods.update(_make_mash_mods(side_effect=RuntimeError("MASH plugin not loaded")))
        result = _fail(self._call(mods, object_name="pSphere1"))
        assert not result["success"]


class TestMashAddNode:
    """maya-mash/scripts/add_node.py."""

    SKILL = "maya-mash"
    SCRIPT = "add_node"

    def _call(self, mods, **kwargs):
        return _run(self.SKILL, self.SCRIPT, mods, **kwargs)

    def test_happy_path(self):
        _, cmds, mods = _make_maya_env()
        network = MagicMock()
        network.addNode.return_value = "MASH1_Random"
        mods.update(_make_mash_mods(network_mock=network))
        result = _success(self._call(mods, waiter="MASH1_Waiter", node_type="MASH_Random"))
        assert result["context"]["node_name"] == "MASH1_Random"

    def test_waiter_not_found(self):
        _, cmds, mods = _make_maya_env()
        cmds.objExists.return_value = False
        mods.update(_make_mash_mods())
        result = _fail(self._call(mods, waiter="bad_waiter", node_type="MASH_Random"))
        assert "bad_waiter" in str(result)

    def test_add_node_exception(self):
        _, cmds, mods = _make_maya_env()
        mods.update(_make_mash_mods(side_effect=RuntimeError("MASH error")))
        result = _fail(self._call(mods, waiter="MASH1_Waiter", node_type="MASH_Random"))
        assert not result["success"]


class TestMashDeleteNetwork:
    """maya-mash/scripts/delete_network.py."""

    SKILL = "maya-mash"
    SCRIPT = "delete_network"

    def _call(self, mods, **kwargs):
        return _run(self.SKILL, self.SCRIPT, mods, **kwargs)

    def test_happy_path(self):
        _, cmds, mods = _make_maya_env()
        mods.update(_make_mash_mods(network_mock=MagicMock()))
        result = _success(self._call(mods, waiter="MASH1_Waiter"))
        assert result["context"]["waiter"] == "MASH1_Waiter"

    def test_waiter_not_found(self):
        _, cmds, mods = _make_maya_env()
        cmds.objExists.return_value = False
        mods.update(_make_mash_mods())
        result = _fail(self._call(mods, waiter="ghost_waiter"))
        assert not result["success"]

    def test_delete_exception(self):
        _, cmds, mods = _make_maya_env()
        mods.update(_make_mash_mods(side_effect=RuntimeError("locked")))
        result = _fail(self._call(mods, waiter="MASH1_Waiter"))
        assert not result["success"]


class TestMashListNetworks:
    """maya-mash/scripts/list_networks.py."""

    SKILL = "maya-mash"
    SCRIPT = "list_networks"

    def _call(self, mods, **kwargs):
        return _run(self.SKILL, self.SCRIPT, mods, **kwargs)

    def test_empty_scene(self):
        _, cmds, mods = _make_maya_env()
        cmds.ls.return_value = []
        result = _success(self._call(mods))
        assert result["context"]["count"] == 0

    def test_with_two_networks(self):
        _, cmds, mods = _make_maya_env()
        cmds.ls.return_value = ["MASH1_Waiter", "MASH2_Waiter"]
        cmds.listConnections.return_value = ["MASH1_Instancer"]
        result = _success(self._call(mods))
        assert result["context"]["count"] == 2
        assert len(result["context"]["networks"]) == 2

    def test_exception(self):
        _, cmds, mods = _make_maya_env()
        cmds.ls.side_effect = RuntimeError("scene error")
        result = _fail(self._call(mods))
        assert not result["success"]


class TestMashSetAttribute:
    """maya-mash/scripts/set_mash_attribute.py."""

    SKILL = "maya-mash"
    SCRIPT = "set_mash_attribute"

    def _call(self, mods, **kwargs):
        return _run(self.SKILL, self.SCRIPT, mods, **kwargs)

    def test_happy_path(self):
        _, cmds, mods = _make_maya_env()
        result = _success(self._call(mods, node="MASH1_Random", attribute="amplitudeX", value=2.5))
        assert result["context"]["attribute"] == "amplitudeX"
        assert result["context"]["value"] == 2.5

    def test_node_not_found(self):
        _, cmds, mods = _make_maya_env()
        cmds.objExists.return_value = False
        result = _fail(self._call(mods, node="ghost_node", attribute="amplitudeX", value=1.0))
        assert not result["success"]

    def test_setattr_exception(self):
        _, cmds, mods = _make_maya_env()
        cmds.setAttr.side_effect = RuntimeError("locked attribute")
        result = _fail(self._call(mods, node="MASH1_Random", attribute="amplitudeX", value=1.0))
        assert not result["success"]


# ===========================================================================
# maya-selection
# ===========================================================================


class TestGrowSelection:
    """maya-selection/scripts/grow_selection.py."""

    SKILL = "maya-selection"
    SCRIPT = "grow_selection"

    def _call(self, mods, **kwargs):
        return _run(self.SKILL, self.SCRIPT, mods, **kwargs)

    def test_grows_selection(self):
        _, cmds, mods = _make_maya_env()
        cmds.ls.side_effect = [
            ["pSphere1.vtx[0]"],  # before
            ["pSphere1.vtx[0]", "pSphere1.vtx[1]", "pSphere1.vtx[2]"],  # after
        ]
        result = _success(self._call(mods))
        assert result["context"]["added"] == 2

    def test_empty_selection_no_error(self):
        _, cmds, mods = _make_maya_env()
        cmds.ls.return_value = []
        result = _success(self._call(mods))
        assert result["context"]["before_count"] == 0

    def test_exception(self):
        _, cmds, mods = _make_maya_env()
        cmds.ls.side_effect = RuntimeError("no mesh")
        result = _fail(self._call(mods))
        assert not result["success"]


class TestShrinkSelection:
    """maya-selection/scripts/shrink_selection.py."""

    SKILL = "maya-selection"
    SCRIPT = "shrink_selection"

    def _call(self, mods, **kwargs):
        return _run(self.SKILL, self.SCRIPT, mods, **kwargs)

    def test_shrinks_selection(self):
        _, cmds, mods = _make_maya_env()
        cmds.ls.side_effect = [
            ["pSphere1.vtx[0]", "pSphere1.vtx[1]", "pSphere1.vtx[2]"],
            ["pSphere1.vtx[1]"],
        ]
        result = _success(self._call(mods))
        assert result["context"]["removed"] == 2

    def test_exception(self):
        _, cmds, mods = _make_maya_env()
        cmds.ls.side_effect = RuntimeError("no mesh")
        result = _fail(self._call(mods))
        assert not result["success"]


class TestInvertSelection:
    """maya-selection/scripts/invert_selection.py."""

    SKILL = "maya-selection"
    SCRIPT = "invert_selection"

    def _call(self, mods, **kwargs):
        return _run(self.SKILL, self.SCRIPT, mods, **kwargs)

    def test_inverts(self):
        _, cmds, mods = _make_maya_env()
        cmds.ls.side_effect = [
            ["pSphere1"],
            ["pCube1", "pCylinder1"],
        ]
        result = _success(self._call(mods))
        assert result["context"]["after_count"] == 2

    def test_exception(self):
        _, cmds, mods = _make_maya_env()
        cmds.ls.side_effect = RuntimeError("selection error")
        result = _fail(self._call(mods))
        assert not result["success"]


class TestConvertSelection:
    """maya-selection/scripts/convert_selection.py."""

    SKILL = "maya-selection"
    SCRIPT = "convert_selection"

    def _call(self, mods, **kwargs):
        return _run(self.SKILL, self.SCRIPT, mods, **kwargs)

    def test_convert_to_vertex(self):
        _, cmds, mods = _make_maya_env()
        cmds.ls.side_effect = [
            ["pSphere1.f[0]"],  # current selection
            ["pSphere1.vtx[0]", "pSphere1.vtx[1]"],  # after flatten
        ]
        cmds.polyListComponentConversion.return_value = ["pSphere1.vtx[0]", "pSphere1.vtx[1]"]
        result = _success(self._call(mods, target="vertex"))
        assert result["context"]["target"] == "vertex"

    def test_invalid_target(self):
        _, cmds, mods = _make_maya_env()
        result = _fail(self._call(mods, target="invalid_type"))
        assert "invalid" in result["message"].lower()

    def test_nothing_selected(self):
        _, cmds, mods = _make_maya_env()
        cmds.ls.return_value = []
        result = _fail(self._call(mods, target="edge"))
        assert not result["success"]

    def test_convert_to_object(self):
        _, cmds, mods = _make_maya_env()
        cmds.ls.side_effect = [
            ["pSphere1.f[0]"],  # current
            ["pSphere1"],  # after objectsOnly
            ["pSphere1"],  # final flatten
        ]
        result = _success(self._call(mods, target="object"))
        assert result["context"]["target"] == "object"


class TestSelectSimilar:
    """maya-selection/scripts/select_similar.py."""

    SKILL = "maya-selection"
    SCRIPT = "select_similar"

    def _call(self, mods, **kwargs):
        return _run(self.SKILL, self.SCRIPT, mods, **kwargs)

    def test_invalid_criteria(self):
        _, cmds, mods = _make_maya_env()
        result = _fail(self._call(mods, criteria="color"))
        assert "invalid" in result["message"].lower()

    def test_nothing_selected(self):
        _, cmds, mods = _make_maya_env()
        cmds.ls.return_value = []
        result = _fail(self._call(mods, criteria="type"))
        assert not result["success"]

    def test_by_name_prefix(self):
        _, cmds, mods = _make_maya_env()
        cmds.ls.side_effect = [
            ["pSphere1"],  # current selection
            ["pSphere1", "pSphere2", "pSphere3", "pCube1"],  # all objects
        ]
        result = _success(self._call(mods, criteria="name_prefix", prefix="pSphere"))
        assert result["context"]["count"] == 3

    def test_by_type_returns_success(self):
        _, cmds, mods = _make_maya_env()
        cmds.ls.side_effect = [
            ["pSphere1"],  # current
            ["pSphere1", "pCube1"],  # all objects
        ]
        cmds.objectType.return_value = "transform"
        result = _success(self._call(mods, criteria="type"))
        assert result["context"]["criteria"] == "type"


# ===========================================================================
# maya-xgen
# ===========================================================================


def _make_xgenm_mock():
    xg = MagicMock()
    xg.palettes.return_value = ["myCollection"]
    xg.descriptions.return_value = ["desc1"]
    xg.boundGeometry.return_value = ["pSphere1"]
    xg.createPalette.return_value = "myCollection"
    xg.createDescription.return_value = "desc1"
    xg.getAttr.return_value = "5.0"
    return xg


class TestXGenCreateDescription:
    """maya-xgen/scripts/create_description.py."""

    SKILL = "maya-xgen"
    SCRIPT = "create_description"

    def _call(self, mods, **kwargs):
        return _run(self.SKILL, self.SCRIPT, mods, **kwargs)

    def test_happy_path(self):
        _, cmds, mods = _make_maya_env()
        mods["xgenm"] = _make_xgenm_mock()
        result = _success(self._call(mods, mesh="pSphere1"))
        assert result["context"]["collection"] == "myCollection"
        assert result["context"]["description"] == "desc1"

    def test_mesh_not_found(self):
        _, cmds, mods = _make_maya_env()
        cmds.objExists.return_value = False
        mods["xgenm"] = _make_xgenm_mock()
        result = _fail(self._call(mods, mesh="ghost_mesh"))
        assert not result["success"]

    def test_custom_primitive(self):
        _, cmds, mods = _make_maya_env()
        xg = _make_xgenm_mock()
        xg.createDescription.return_value = "cardDesc"
        mods["xgenm"] = xg
        result = _success(self._call(mods, mesh="pSphere1", primitive="CardPrimitive"))
        assert result["context"]["primitive"] == "CardPrimitive"

    def test_xgenm_exception(self):
        _, cmds, mods = _make_maya_env()
        xg = _make_xgenm_mock()
        xg.createPalette.side_effect = RuntimeError("xgen not loaded")
        mods["xgenm"] = xg
        result = _fail(self._call(mods, mesh="pSphere1"))
        assert not result["success"]


class TestXGenDeleteDescription:
    """maya-xgen/scripts/delete_description.py."""

    SKILL = "maya-xgen"
    SCRIPT = "delete_description"

    def _call(self, mods, **kwargs):
        return _run(self.SKILL, self.SCRIPT, mods, **kwargs)

    def test_happy_path(self):
        _, cmds, mods = _make_maya_env()
        mods["xgenm"] = _make_xgenm_mock()
        result = _success(self._call(mods, collection="myCollection", description="desc1"))
        assert result["context"]["description"] == "desc1"

    def test_description_not_found(self):
        _, cmds, mods = _make_maya_env()
        xg = _make_xgenm_mock()
        xg.descriptions.return_value = ["other"]
        mods["xgenm"] = xg
        result = _fail(self._call(mods, collection="myCollection", description="missing"))
        assert "not found" in result["message"].lower()

    def test_delete_exception(self):
        _, cmds, mods = _make_maya_env()
        xg = _make_xgenm_mock()
        xg.deleteDescription.side_effect = RuntimeError("delete failed")
        mods["xgenm"] = xg
        result = _fail(self._call(mods, collection="myCollection", description="desc1"))
        assert not result["success"]


class TestXGenListDescriptions:
    """maya-xgen/scripts/list_descriptions.py."""

    SKILL = "maya-xgen"
    SCRIPT = "list_descriptions"

    def _call(self, mods, **kwargs):
        return _run(self.SKILL, self.SCRIPT, mods, **kwargs)

    def test_list_all(self):
        _, cmds, mods = _make_maya_env()
        mods["xgenm"] = _make_xgenm_mock()
        result = _success(self._call(mods))
        assert result["context"]["count"] == 1
        assert result["context"]["descriptions"][0]["collection"] == "myCollection"

    def test_filter_by_collection(self):
        _, cmds, mods = _make_maya_env()
        mods["xgenm"] = _make_xgenm_mock()
        result = _success(self._call(mods, collection="myCollection"))
        assert result["context"]["count"] == 1

    def test_filter_no_match(self):
        _, cmds, mods = _make_maya_env()
        mods["xgenm"] = _make_xgenm_mock()
        result = _success(self._call(mods, collection="otherCollection"))
        assert result["context"]["count"] == 0

    def test_empty_scene(self):
        _, cmds, mods = _make_maya_env()
        xg = _make_xgenm_mock()
        xg.palettes.return_value = []
        mods["xgenm"] = xg
        result = _success(self._call(mods))
        assert result["context"]["count"] == 0


class TestXGenGetAttribute:
    """maya-xgen/scripts/get_xgen_attribute.py."""

    SKILL = "maya-xgen"
    SCRIPT = "get_xgen_attribute"

    def _call(self, mods, **kwargs):
        return _run(self.SKILL, self.SCRIPT, mods, **kwargs)

    def test_happy_path(self):
        _, cmds, mods = _make_maya_env()
        mods["xgenm"] = _make_xgenm_mock()
        result = _success(self._call(mods, collection="myCollection", description="desc1", attribute="density"))
        assert result["context"]["value"] == "5.0"
        assert result["context"]["attribute"] == "density"

    def test_with_object_context(self):
        _, cmds, mods = _make_maya_env()
        xg = _make_xgenm_mock()
        mods["xgenm"] = xg
        self._call(
            mods,
            collection="myCollection",
            description="desc1",
            attribute="length",
            object_name="pSphere1",
        )
        xg.getAttr.assert_called_once_with("length", "myCollection", "desc1", "pSphere1")

    def test_xgen_exception(self):
        _, cmds, mods = _make_maya_env()
        xg = _make_xgenm_mock()
        xg.getAttr.side_effect = RuntimeError("attribute not found")
        mods["xgenm"] = xg
        result = _fail(self._call(mods, collection="myCollection", description="desc1", attribute="bad_attr"))
        assert not result["success"]


class TestXGenSetAttribute:
    """maya-xgen/scripts/set_xgen_attribute.py."""

    SKILL = "maya-xgen"
    SCRIPT = "set_xgen_attribute"

    def _call(self, mods, **kwargs):
        return _run(self.SKILL, self.SCRIPT, mods, **kwargs)

    def test_happy_path(self):
        _, cmds, mods = _make_maya_env()
        xg = _make_xgenm_mock()
        mods["xgenm"] = xg
        result = _success(
            self._call(
                mods,
                collection="myCollection",
                description="desc1",
                attribute="density",
                value="10.0",
            )
        )
        assert result["context"]["value"] == "10.0"
        xg.setAttr.assert_called_once()

    def test_numeric_value_coerced_to_str(self):
        _, cmds, mods = _make_maya_env()
        xg = _make_xgenm_mock()
        mods["xgenm"] = xg
        result = _success(
            self._call(
                mods,
                collection="myCollection",
                description="desc1",
                attribute="length",
                value=5,
            )
        )
        assert result["context"]["value"] == "5"

    def test_xgen_exception(self):
        _, cmds, mods = _make_maya_env()
        xg = _make_xgenm_mock()
        xg.setAttr.side_effect = RuntimeError("read-only attr")
        mods["xgenm"] = xg
        result = _fail(
            self._call(
                mods,
                collection="myCollection",
                description="desc1",
                attribute="ro_attr",
                value="1.0",
            )
        )
        assert not result["success"]


# ===========================================================================
# Structural: no more def run(params) in any skill script
# ===========================================================================


class TestNoLegacyRunSignature:
    """Ensure no skill scripts still use the old run(params) signature."""

    def test_no_run_params_in_skill_scripts(self):
        """All 369 skill scripts must use the new skill_entry style."""
        import ast

        skills_root = Path(__file__).parent.parent / "src" / "dcc_mcp_maya" / "skills"
        violations = []
        for py_file in skills_root.rglob("*.py"):
            try:
                tree = ast.parse(py_file.read_text(encoding="utf-8"))
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name == "run":
                    args = [a.arg for a in node.args.args]
                    if args == ["params"]:
                        violations.append(str(py_file.relative_to(skills_root)))
        assert violations == [], "Legacy run(params) found in: {}".format(violations)
