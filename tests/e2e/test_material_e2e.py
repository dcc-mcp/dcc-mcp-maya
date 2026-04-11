"""E2E tests for maya-materials and maya-uv-ops skills.

Requires a real mayapy interpreter.  Skipped automatically when maya is not
available.

Run::

    mayapy -m pytest tests/e2e/test_material_e2e.py -v
"""

# Import future modules
from __future__ import annotations

# Import built-in modules
import importlib.util
from pathlib import Path

# Import third-party modules
import pytest

maya_standalone = pytest.importorskip(
    "maya.standalone",
    reason="maya.standalone not available — run under mayapy",
)

try:
    maya_standalone.initialize(name="python")
except Exception:
    pass

from maya import cmds  # noqa: E402

pytestmark = pytest.mark.e2e

_SKILLS_ROOT = Path(__file__).parent.parent.parent / "src" / "dcc_mcp_maya" / "skills"

_MOD_COUNTER = [0]


def _load(skill_dir: str, script_name: str):
    _MOD_COUNTER[0] += 1
    path = _SKILLS_ROOT / skill_dir / "scripts" / "{}.py".format(script_name)
    spec = importlib.util.spec_from_file_location(
        "e2e_mat_{}_{}_{}".format(skill_dir.replace("-", "_"), script_name, _MOD_COUNTER[0]),
        str(path),
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _new_scene():
    cmds.file(new=True, force=True)


class TestMaterialsE2E:
    def setup_method(self):
        _new_scene()

    def test_create_lambert(self):
        mod = _load("maya-materials", "create_material")
        result = mod.create_material(material_type="lambert", name="e2eLambert")
        assert result["success"] is True
        assert cmds.objExists("e2eLambert")
        assert cmds.objectType("e2eLambert") == "lambert"

    def test_create_blinn(self):
        mod = _load("maya-materials", "create_material")
        result = mod.create_material(material_type="blinn", name="e2eBlinn")
        assert result["success"] is True
        assert cmds.objectType("e2eBlinn") == "blinn"

    def test_assign_material_to_sphere(self):
        cmds.polySphere(name="matSphere")
        create_mod = _load("maya-materials", "create_material")
        create_mod.create_material(material_type="lambert", name="sphrLambert")
        assign_mod = _load("maya-materials", "assign_material")
        result = assign_mod.assign_material(material_name="sphrLambert", objects=["matSphere"])
        assert result["success"] is True

    def test_list_materials_includes_defaults(self):
        mod = _load("maya-materials", "list_materials")
        result = mod.list_materials()
        assert result["success"] is True
        mat_names = [m.get("name", "") for m in result["context"].get("materials", [])]
        # Lambert1 is always present in a new Maya scene
        assert any("lambert" in n.lower() for n in mat_names)

    def test_set_material_attribute_color(self):
        create_mod = _load("maya-materials", "create_material")
        create_mod.create_material(material_type="lambert", name="colorLambert")
        set_mod = _load("maya-materials", "set_material_attribute")
        result = set_mod.set_material_attribute(
            material_name="colorLambert",
            attribute="color",
            value=[1.0, 0.0, 0.0],
        )
        assert result["success"] is True
        r = cmds.getAttr("colorLambert.colorR")
        assert abs(r - 1.0) < 0.01

    def test_get_shader_assignment(self):
        cmds.polyCube(name="shaderCube")
        create_mod = _load("maya-materials", "create_material")
        create_mod.create_material(material_type="lambert", name="shaderLambert")
        assign_mod = _load("maya-materials", "assign_material")
        assign_mod.assign_material(material_name="shaderLambert", objects=["shaderCube"])
        mod = _load("maya-materials", "get_shader_assignment")
        result = mod.get_shader_assignment(object_name="shaderCube")
        assert result["success"] is True


class TestUvOpsE2E:
    def setup_method(self):
        _new_scene()

    def test_project_uvs_planar(self):
        cmds.polySphere(name="uvSphere")
        mod = _load("maya-uv-ops", "project_uvs")
        result = mod.project_uvs(object_name="uvSphere", projection_type="planar", axis="y")
        assert result["success"] is True

    def test_get_uv_info(self):
        cmds.polySphere(name="uvInfoSphere")
        mod = _load("maya-uv-ops", "get_uv_info")
        result = mod.get_uv_info(object_name="uvInfoSphere")
        assert result["success"] is True
        assert "uv_count" in result["context"] or "uv_sets" in result["context"]

    def test_create_uv_set(self):
        cmds.polySphere(name="uvSetSphere")
        mod = _load("maya-uv-ops", "create_uv_set")
        result = mod.create_uv_set(object_name="uvSetSphere", uv_set_name="myCustomUVSet")
        assert result["success"] is True
        uv_sets = cmds.polyUVSet("uvSetSphere", query=True, allUVSets=True) or []
        assert "myCustomUVSet" in uv_sets
