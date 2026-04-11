"""E2E tests for maya-animation skills.

Requires a real mayapy interpreter.  Skipped automatically when maya is not
available.

Run::

    mayapy -m pytest tests/e2e/test_animation_e2e.py -v
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
        "e2e_anim_{}_{}_{}".format(skill_dir.replace("-", "_"), script_name, _MOD_COUNTER[0]),
        str(path),
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _new_scene():
    cmds.file(new=True, force=True)


class TestAnimationSkillsE2E:
    def setup_method(self):
        _new_scene()

    def test_set_keyframe_creates_anim_curve(self):
        cmds.polyCube(name="kfCube")
        mod = _load("maya-animation", "set_keyframe")
        result = mod.set_keyframe(object_name="kfCube", attribute="translateX", time=1, value=0.0)
        assert result["success"] is True
        result2 = mod.set_keyframe(object_name="kfCube", attribute="translateX", time=24, value=10.0)
        assert result2["success"] is True
        curves = cmds.keyframe("kfCube.translateX", query=True, timeChange=True) or []
        assert 1.0 in curves or 1 in curves

    def test_get_keyframes(self):
        cmds.polyCube(name="gkCube")
        cmds.setKeyframe("gkCube", attribute="translateX", time=5, value=1.0)
        cmds.setKeyframe("gkCube", attribute="translateX", time=10, value=5.0)
        mod = _load("maya-animation", "get_keyframes")
        result = mod.get_keyframes(object_name="gkCube", attribute="translateX")
        assert result["success"] is True
        keys = result["context"].get("keyframes", [])
        assert len(keys) >= 2

    def test_set_timeline(self):
        mod = _load("maya-animation", "set_timeline")
        result = mod.set_timeline(start_frame=5, end_frame=120)
        assert result["success"] is True
        assert cmds.playbackOptions(query=True, min=True) == 5.0
        assert cmds.playbackOptions(query=True, max=True) == 120.0

    def test_get_current_time(self):
        cmds.currentTime(15)
        mod = _load("maya-animation", "get_current_time")
        result = mod.get_current_time()
        assert result["success"] is True
        assert abs(result["context"]["current_time"] - 15.0) < 0.01

    def test_set_current_time(self):
        mod = _load("maya-animation", "set_current_time")
        result = mod.set_current_time(frame=42)
        assert result["success"] is True
        assert abs(cmds.currentTime(query=True) - 42.0) < 0.01

    def test_bake_simulation(self):
        cmds.polyCube(name="bakeCube")
        cmds.setKeyframe("bakeCube", attribute="translateX", time=1, value=0.0)
        cmds.setKeyframe("bakeCube", attribute="translateX", time=24, value=10.0)
        mod = _load("maya-animation", "bake_simulation")
        result = mod.bake_simulation(objects=["bakeCube"], start_frame=1.0, end_frame=24.0, sample_by=2.0)
        assert result["success"] is True

    def test_list_animation_curves(self):
        cmds.polyCube(name="lacCube")
        cmds.setKeyframe("lacCube", attribute="translateY", time=1, value=0.0)
        mod = _load("maya-animation", "list_animation_curves")
        result = mod.list_animation_curves(object_name="lacCube")
        assert result["success"] is True
        assert len(result["context"].get("curves", [])) > 0

    def test_delete_keyframes(self):
        cmds.polyCube(name="dkCube")
        cmds.setKeyframe("dkCube", attribute="translateX", time=1, value=0.0)
        cmds.setKeyframe("dkCube", attribute="translateX", time=10, value=5.0)
        mod = _load("maya-animation", "delete_keyframes")
        result = mod.delete_keyframes(object_name="dkCube", attribute="translateX", start_time=1, end_time=10)
        assert result["success"] is True
        remaining = cmds.keyframe("dkCube.translateX", query=True, timeChange=True) or []
        assert len(remaining) == 0
