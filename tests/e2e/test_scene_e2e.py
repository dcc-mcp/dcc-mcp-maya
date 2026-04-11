"""E2E tests for maya-scene and maya-primitives skills.

Requires a real mayapy interpreter.  Skipped automatically when maya is not
available so the file is safe to collect in normal (non-mayapy) test runs.

Run::

    mayapy -m pytest tests/e2e/test_scene_e2e.py -v
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
        "e2e_{}_{}_{}" .format(skill_dir.replace("-", "_"), script_name, _MOD_COUNTER[0]),
        str(path),
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _new_scene():
    cmds.file(new=True, force=True)


# ---------------------------------------------------------------------------
# Scene
# ---------------------------------------------------------------------------


class TestSceneSkillsE2E:
    def setup_method(self):
        _new_scene()

    def test_create_locator(self):
        mod = _load("maya-scene", "create_locator")
        result = mod.create_locator(name="e2eLocator")
        assert result["success"] is True
        assert cmds.objExists("e2eLocator")

    def test_list_objects(self):
        cmds.polySphere(name="lsSphere")
        mod = _load("maya-scene", "list_objects")
        result = mod.list_objects()
        assert result["success"] is True
        assert "objects" in result["context"]

    def test_get_session_info_has_maya_version(self):
        mod = _load("maya-scene", "get_session_info")
        result = mod.get_session_info()
        assert result["success"] is True
        assert "maya_version" in result["context"]

    def test_save_scene_mayaascii(self, tmp_path):
        mod = _load("maya-scene", "save_scene")
        out = str(tmp_path / "e2e_save.ma")
        result = mod.save_scene(file_path=out, file_type="mayaAscii")
        assert result["success"] is True
        import os

        assert os.path.exists(out)

    def test_group_objects(self):
        cmds.polySphere(name="grpSphA")
        cmds.polySphere(name="grpSphB")
        mod = _load("maya-scene", "group_objects")
        result = mod.group_objects(objects=["grpSphA", "grpSphB"], group_name="e2eGroup")
        assert result["success"] is True
        assert cmds.objExists("e2eGroup")

    def test_parent_object(self):
        cmds.polySphere(name="parentChild")
        cmds.group(name="parentGrp", empty=True)
        mod = _load("maya-scene", "parent_object")
        result = mod.parent_object(child="parentChild", parent="parentGrp")
        assert result["success"] is True
        parents = cmds.listRelatives("parentChild", parent=True)
        assert parents and parents[0] == "parentGrp"


# ---------------------------------------------------------------------------
# Primitives
# ---------------------------------------------------------------------------


class TestPrimitivesSkillsE2E:
    def setup_method(self):
        _new_scene()

    def test_create_sphere_exists_in_scene(self):
        mod = _load("maya-primitives", "create_sphere")
        result = mod.create_sphere(name="e2eSphere", radius=3.0)
        assert result["success"] is True
        assert cmds.objExists("e2eSphere")

    def test_create_cube_exists_in_scene(self):
        mod = _load("maya-primitives", "create_cube")
        result = mod.create_cube(name="e2eCube")
        assert result["success"] is True
        assert cmds.objExists("e2eCube")

    def test_create_cylinder(self):
        mod = _load("maya-primitives", "create_cylinder")
        result = mod.create_cylinder(name="e2eCyl")
        assert result["success"] is True
        assert cmds.objExists("e2eCyl")

    def test_create_plane(self):
        mod = _load("maya-primitives", "create_plane")
        result = mod.create_plane(name="e2ePlane")
        assert result["success"] is True
        assert cmds.objExists("e2ePlane")

    def test_set_transform_and_verify(self):
        create_mod = _load("maya-primitives", "create_sphere")
        create_mod.create_sphere(name="xfSphere")
        set_mod = _load("maya-primitives", "set_transform")
        result = set_mod.set_transform(object_name="xfSphere", translate=[2.0, 4.0, 6.0])
        assert result["success"] is True
        tx = cmds.getAttr("xfSphere.translateX")
        assert abs(tx - 2.0) < 1e-4

    def test_get_transform(self):
        cmds.polySphere(name="gtSphere")
        cmds.setAttr("gtSphere.translateY", 7.5)
        mod = _load("maya-primitives", "get_transform")
        result = mod.get_transform(object_name="gtSphere")
        assert result["success"] is True
        ty = result["context"]["translate"][1]
        assert abs(ty - 7.5) < 1e-4

    def test_delete_objects(self):
        cmds.polySphere(name="delSphere")
        assert cmds.objExists("delSphere")
        mod = _load("maya-primitives", "delete_objects")
        result = mod.delete_objects(object_names=["delSphere"])
        assert result["success"] is True
        assert not cmds.objExists("delSphere")

    def test_rename_object(self):
        cmds.polyCube(name="oldName")
        mod = _load("maya-primitives", "rename_object")
        result = mod.rename_object(object_name="oldName", new_name="newName")
        assert result["success"] is True
        assert cmds.objExists("newName")
        assert not cmds.objExists("oldName")
