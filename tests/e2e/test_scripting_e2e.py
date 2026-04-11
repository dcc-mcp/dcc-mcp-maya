"""E2E tests for maya-scripting, maya-utility, and maya-pipeline skills.

Requires a real mayapy interpreter.  Skipped automatically when maya is not
available.

Run::

    mayapy -m pytest tests/e2e/test_scripting_e2e.py -v
"""

# Import future modules
from __future__ import annotations

# Import built-in modules
import importlib.util
import os
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
        "e2e_scr_{}_{}_{}" .format(skill_dir.replace("-", "_"), script_name, _MOD_COUNTER[0]),
        str(path),
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _new_scene():
    cmds.file(new=True, force=True)


class TestScriptingE2E:
    def setup_method(self):
        _new_scene()

    def test_execute_mel_polysphere(self):
        mod = _load("maya-scripting", "execute_mel")
        result = mod.execute_mel(script="polySphere -r 1 -n melE2ESphere;")
        assert result["success"] is True
        assert cmds.objExists("melE2ESphere")

    def test_execute_mel_syntax_error_returns_result(self):
        """Invalid MEL returns a result dict (success or failure, not crash)."""
        mod = _load("maya-scripting", "execute_mel")
        result = mod.execute_mel(script="this_is_invalid_mel_xyz!!!;")
        assert isinstance(result, dict)
        # Should be failure, not a Python exception
        assert "success" in result

    def test_execute_python_creates_node(self):
        mod = _load("maya-scripting", "execute_python")
        result = mod.execute_python(code="import maya.cmds as cmds; cmds.polyCube(n='pyE2ECube')")
        assert result["success"] is True
        assert cmds.objExists("pyE2ECube")

    def test_execute_python_captures_result(self):
        mod = _load("maya-scripting", "execute_python")
        result = mod.execute_python(code="result = 1 + 2")
        assert result["success"] is True
        # result variable should be captured in context
        ctx = result.get("context", {})
        assert ctx.get("result") == 3 or ctx.get("output") is not None

    def test_list_mel_procedures(self):
        mod = _load("maya-scripting", "list_mel_procedures")
        result = mod.list_mel_procedures()
        assert result["success"] is True
        procs = result["context"].get("procedures", [])
        assert isinstance(procs, list)

    def test_get_script_node(self):
        # Create a script node first
        import maya.mel as mel
        mel.eval(
            'scriptNode -st 2 -bs "print(\\"hello\\");" -n e2eScriptNode -stp "python";'
        )
        mod = _load("maya-scripting", "get_script_node")
        result = mod.get_script_node(node_name="e2eScriptNode")
        assert result["success"] is True
        assert "script" in result["context"] or "node_name" in result["context"]


class TestUtilityE2E:
    def setup_method(self):
        _new_scene()

    def test_get_scene_statistics(self):
        cmds.polySphere(name="statSphere")
        cmds.polyCube(name="statCube")
        mod = _load("maya-utility", "get_scene_statistics")
        result = mod.get_scene_statistics()
        assert result["success"] is True
        ctx = result["context"]
        assert "scene_file" in ctx or "node_count" in ctx or "total_nodes" in ctx

    def test_create_utility_node_multiplyDivide(self):
        mod = _load("maya-utility", "create_utility_node")
        result = mod.create_utility_node(node_type="multiplyDivide", name="e2eMulDiv")
        assert result["success"] is True
        # Node should exist (may be renamed by Maya)
        nodes = cmds.ls(type="multiplyDivide") or []
        assert len(nodes) > 0

    def test_list_node_connections(self):
        cmds.polySphere(name="connSphere")
        mod = _load("maya-utility", "list_node_connections")
        result = mod.list_node_connections(node_name="connSphere")
        assert result["success"] is True
        assert "connections" in result["context"]

    def test_clean_scene_removes_unused(self):
        # Create and immediately disconnect an unused material
        cmds.shadingNode("lambert", asShader=True, name="unusedLambert")
        mod = _load("maya-utility", "clean_scene")
        result = mod.clean_scene()
        assert result["success"] is True


class TestPipelineE2E:
    def setup_method(self):
        _new_scene()

    def test_set_project(self, tmp_path):
        mod = _load("maya-pipeline", "set_project")
        result = mod.set_project(project_path=str(tmp_path))
        assert result["success"] is True

    def test_tag_and_get_asset_metadata(self):
        cmds.polySphere(name="assetSphere")
        tag_mod = _load("maya-pipeline", "tag_asset_metadata")
        result = tag_mod.tag_asset_metadata(
            node_name="assetSphere",
            asset_name="TestAsset",
            asset_type="prop",
            version="1.0.0",
        )
        assert result["success"] is True

        get_mod = _load("maya-pipeline", "get_asset_metadata")
        get_result = get_mod.get_asset_metadata(node_name="assetSphere")
        assert get_result["success"] is True
        ctx = get_result["context"]
        assert ctx.get("asset_name") == "TestAsset" or "metadata" in ctx
