"""E2E tests for maya-deformers and maya-xform-utils skills.

Requires a real mayapy interpreter.  Skipped automatically when maya is not
available so the file is safe to collect in normal (non-mayapy) test runs.

Run::

    mayapy -m pytest tests/e2e/test_deformers_xform_e2e.py -v
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
        "e2e_{}_{}_{}".format(skill_dir.replace("-", "_"), script_name, _MOD_COUNTER[0]),
        str(path),
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _new_scene():
    cmds.file(new=True, force=True)


# ---------------------------------------------------------------------------
# maya-deformers
# ---------------------------------------------------------------------------


class TestDeformersE2E:
    def setup_method(self):
        _new_scene()

    def test_create_cluster_exists(self):
        cmds.polySphere(name="clusterSphere")
        mod = _load("maya-deformers", "create_cluster")
        result = mod.create_cluster(mesh="clusterSphere")
        assert result["success"] is True
        assert "cluster_handle" in result["context"]
        handle = result["context"]["cluster_handle"]
        assert cmds.objExists(handle)

    def test_create_lattice_exists(self):
        cmds.polyCube(name="latticeCube")
        mod = _load("maya-deformers", "create_lattice")
        result = mod.create_lattice(objects=["latticeCube"], s_divisions=3, t_divisions=3, u_divisions=3)
        assert result["success"] is True
        assert "ffd_node" in result["context"]

    def test_create_cluster_missing_mesh(self):
        mod = _load("maya-deformers", "create_cluster")
        result = mod.create_cluster(mesh="nonExistentMesh_xyz")
        assert result["success"] is False

    def test_apply_subdivision_exists(self):
        cmds.polyCube(name="subdivCube")
        mod = _load("maya-deformers", "apply_subdivision")
        result = mod.apply_subdivision(mesh="subdivCube", iterations=1)
        assert result["success"] is True

    def test_apply_subdivision_missing_mesh(self):
        mod = _load("maya-deformers", "apply_subdivision")
        result = mod.apply_subdivision(mesh="noSuchMesh_xyz")
        assert result["success"] is False

    def test_cleanup_mesh(self):
        cmds.polyCube(name="cleanupCube")
        mod = _load("maya-deformers", "cleanup_mesh")
        result = mod.cleanup_mesh(mesh="cleanupCube")
        assert result["success"] is True


# ---------------------------------------------------------------------------
# maya-xform-utils
# ---------------------------------------------------------------------------


class TestXFormUtilsE2E:
    def setup_method(self):
        _new_scene()

    def test_freeze_transforms(self):
        cmds.polySphere(name="freezeSphere")
        cmds.setAttr("freezeSphere.translateX", 5.0)
        mod = _load("maya-xform-utils", "freeze_transforms")
        result = mod.freeze_transforms(objects=["freezeSphere"])
        assert result["success"] is True
        tx = cmds.getAttr("freezeSphere.translateX")
        assert abs(tx) < 1e-5, "translateX should be 0 after freeze"

    def test_freeze_transforms_missing_object(self):
        mod = _load("maya-xform-utils", "freeze_transforms")
        result = mod.freeze_transforms(objects=["noSuchObject_xyz"])
        assert result["success"] is False

    def test_reset_pivot_bbox_center(self):
        cmds.polyCube(name="pivotCube")
        cmds.setAttr("pivotCube.translateX", 3.0)
        mod = _load("maya-xform-utils", "reset_pivot")
        result = mod.reset_pivot(object_name="pivotCube", mode="bbox_center")
        assert result["success"] is True

    def test_match_transforms(self):
        cmds.polySphere(name="srcSphere")
        cmds.setAttr("srcSphere.translateY", 5.0)
        cmds.polyCube(name="tgtCube")
        mod = _load("maya-xform-utils", "match_transforms")
        result = mod.match_transforms(source="tgtCube", target="srcSphere")
        assert result["success"] is True
        ty = cmds.getAttr("tgtCube.translateY")
        assert abs(ty - 5.0) < 1e-4, "tgtCube.ty should match srcSphere.ty"

    def test_match_transforms_missing_source(self):
        cmds.polySphere(name="existingSphere")
        mod = _load("maya-xform-utils", "match_transforms")
        result = mod.match_transforms(source="missingSource_xyz", target="existingSphere")
        assert result["success"] is False
