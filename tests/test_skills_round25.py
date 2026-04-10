"""Round 25: Tests for maya-blend-shape-utils, maya-material-library, maya-render-farm."""
from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

SKILLS_ROOT = Path(__file__).parent.parent / "src" / "dcc_mcp_maya" / "skills"


def _load_script(skill_dir: str, script_name: str):
    """Load a Skill script module from a hyphenated directory."""
    script_path = SKILLS_ROOT / skill_dir / "scripts" / script_name
    spec = importlib.util.spec_from_file_location(
        "{}_{}".format(skill_dir.replace("-", "_"), script_name[:-3]),
        str(script_path),
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(autouse=True)
def mock_maya_env():
    """Mock Maya modules for all tests."""
    mock_cmds = MagicMock()
    mock_maya = MagicMock()
    mock_maya.cmds = mock_cmds
    sys.modules["maya"] = mock_maya
    sys.modules["maya.cmds"] = mock_cmds
    sys.modules["maya.api"] = MagicMock()
    sys.modules["maya.utils"] = MagicMock()
    yield mock_cmds
    for mod in ["maya", "maya.cmds", "maya.api", "maya.utils"]:
        sys.modules.pop(mod, None)


# ---------------------------------------------------------------------------
# maya-blend-shape-utils
# ---------------------------------------------------------------------------

class TestGetBlendShapeWeights:
    def test_missing_mesh(self, mock_maya_env):
        mod = _load_script("maya-blend-shape-utils", "get_blend_shape_weights.py")
        r = mod.run({})
        assert r.success is False
        assert "mesh" in r.error.lower()

    def test_mesh_with_blend_shape(self, mock_maya_env):
        mock_cmds = mock_maya_env
        mock_cmds.objectType.side_effect = lambda n: "transform" if n == "mesh1" else "blendShape"
        mock_cmds.listHistory.return_value = ["blendShape1"]
        mock_cmds.aliasAttr.return_value = ["Smile", "weight[0]", "Frown", "weight[1]"]
        mock_cmds.getAttr.side_effect = lambda attr: 0.5 if "Smile" in attr else 0.0
        mod = _load_script("maya-blend-shape-utils", "get_blend_shape_weights.py")
        r = mod.run({"mesh": "mesh1"})
        assert r.success is True
        assert r.context["count"] == 2
        assert r.context["blend_shape_node"] == "blendShape1"

    def test_blend_shape_node_direct(self, mock_maya_env):
        mock_cmds = mock_maya_env
        mock_cmds.objectType.return_value = "blendShape"
        mock_cmds.aliasAttr.return_value = ["Happy", "weight[0]"]
        mock_cmds.getAttr.return_value = 1.0
        mod = _load_script("maya-blend-shape-utils", "get_blend_shape_weights.py")
        r = mod.run({"mesh": "blendShape1"})
        assert r.success is True
        assert r.context["count"] == 1

    def test_no_blend_shape_on_mesh(self, mock_maya_env):
        mock_cmds = mock_maya_env
        mock_cmds.objectType.return_value = "transform"
        mock_cmds.listHistory.return_value = ["skinCluster1"]
        mod = _load_script("maya-blend-shape-utils", "get_blend_shape_weights.py")
        r = mod.run({"mesh": "mesh1"})
        assert r.success is False
        assert "no blendshape" in r.error.lower()

    def test_exception(self, mock_maya_env):
        mock_cmds = mock_maya_env
        mock_cmds.objectType.side_effect = RuntimeError("cmds error")
        mod = _load_script("maya-blend-shape-utils", "get_blend_shape_weights.py")
        r = mod.run({"mesh": "mesh1"})
        assert r.success is False


class TestSetBlendShapeWeight:
    def test_missing_blend_shape(self, mock_maya_env):
        mod = _load_script("maya-blend-shape-utils", "set_blend_shape_weight.py")
        r = mod.run({"target": "Smile", "weight": 0.5})
        assert r.success is False
        assert "blend_shape" in r.error.lower()

    def test_missing_weight(self, mock_maya_env):
        mod = _load_script("maya-blend-shape-utils", "set_blend_shape_weight.py")
        r = mod.run({"blend_shape": "bs1", "target": "Smile"})
        assert r.success is False
        assert "weight" in r.error.lower()

    def test_missing_target_and_index(self, mock_maya_env):
        mod = _load_script("maya-blend-shape-utils", "set_blend_shape_weight.py")
        r = mod.run({"blend_shape": "bs1", "weight": 0.5})
        assert r.success is False

    def test_node_not_found(self, mock_maya_env):
        mock_maya_env.objExists.return_value = False
        mod = _load_script("maya-blend-shape-utils", "set_blend_shape_weight.py")
        r = mod.run({"blend_shape": "bs1", "target": "Smile", "weight": 0.5})
        assert r.success is False
        assert "not exist" in r.error.lower()

    def test_set_by_target_name(self, mock_maya_env):
        mock_maya_env.objExists.return_value = True
        mod = _load_script("maya-blend-shape-utils", "set_blend_shape_weight.py")
        r = mod.run({"blend_shape": "bs1", "target": "Smile", "weight": 0.8})
        assert r.success is True
        assert r.context["weight"] == pytest.approx(0.8)

    def test_set_by_index(self, mock_maya_env):
        mock_maya_env.objExists.return_value = True
        mod = _load_script("maya-blend-shape-utils", "set_blend_shape_weight.py")
        r = mod.run({"blend_shape": "bs1", "index": 0, "weight": 1.0})
        assert r.success is True
        assert r.context["target"] == "index_0"

    def test_exception(self, mock_maya_env):
        mock_maya_env.objExists.side_effect = RuntimeError("err")
        mod = _load_script("maya-blend-shape-utils", "set_blend_shape_weight.py")
        r = mod.run({"blend_shape": "bs1", "target": "Smile", "weight": 0.5})
        assert r.success is False


class TestListBlendShapes:
    def test_list_all(self, mock_maya_env):
        mock_maya_env.ls.return_value = ["blendShape1", "blendShape2"]
        mock_maya_env.blendShape.return_value = ["pSphere1"]
        mock_maya_env.aliasAttr.return_value = ["Smile", "weight[0]"]
        mock_maya_env.objectType.return_value = "blendShape"
        mod = _load_script("maya-blend-shape-utils", "list_blend_shapes.py")
        r = mod.run({})
        assert r.success is True
        assert r.context["count"] == 2

    def test_filter_by_mesh(self, mock_maya_env):
        mock_maya_env.listHistory.return_value = ["blendShape1"]
        mock_maya_env.objectType.return_value = "blendShape"
        mock_maya_env.blendShape.return_value = ["pSphere1"]
        mock_maya_env.aliasAttr.return_value = []
        mod = _load_script("maya-blend-shape-utils", "list_blend_shapes.py")
        r = mod.run({"mesh": "pSphere1"})
        assert r.success is True
        assert r.context["count"] == 1

    def test_no_blend_shapes(self, mock_maya_env):
        mock_maya_env.ls.return_value = []
        mod = _load_script("maya-blend-shape-utils", "list_blend_shapes.py")
        r = mod.run({})
        assert r.success is True
        assert r.context["count"] == 0

    def test_exception(self, mock_maya_env):
        mock_maya_env.ls.side_effect = RuntimeError("err")
        mod = _load_script("maya-blend-shape-utils", "list_blend_shapes.py")
        r = mod.run({})
        assert r.success is False


class TestZeroBlendShapeWeights:
    def test_missing_blend_shape(self, mock_maya_env):
        mod = _load_script("maya-blend-shape-utils", "zero_blend_shape_weights.py")
        r = mod.run({})
        assert r.success is False

    def test_node_not_found(self, mock_maya_env):
        mock_maya_env.objExists.return_value = False
        mod = _load_script("maya-blend-shape-utils", "zero_blend_shape_weights.py")
        r = mod.run({"blend_shape": "bs1"})
        assert r.success is False
        assert "not exist" in r.error.lower()

    def test_zero_weights(self, mock_maya_env):
        mock_maya_env.objExists.return_value = True
        mock_maya_env.aliasAttr.return_value = ["Smile", "weight[0]", "Frown", "weight[1]"]
        mod = _load_script("maya-blend-shape-utils", "zero_blend_shape_weights.py")
        r = mod.run({"blend_shape": "bs1"})
        assert r.success is True
        assert r.context["zeroed_count"] == 2

    def test_no_targets(self, mock_maya_env):
        mock_maya_env.objExists.return_value = True
        mock_maya_env.aliasAttr.return_value = []
        mod = _load_script("maya-blend-shape-utils", "zero_blend_shape_weights.py")
        r = mod.run({"blend_shape": "bs1"})
        assert r.success is True
        assert r.context["zeroed_count"] == 0

    def test_exception(self, mock_maya_env):
        mock_maya_env.objExists.side_effect = RuntimeError("err")
        mod = _load_script("maya-blend-shape-utils", "zero_blend_shape_weights.py")
        r = mod.run({"blend_shape": "bs1"})
        assert r.success is False


class TestAddBlendShapeTarget:
    def test_missing_blend_shape(self, mock_maya_env):
        mod = _load_script("maya-blend-shape-utils", "add_blend_shape_target.py")
        r = mod.run({"target": "mesh2"})
        assert r.success is False

    def test_missing_target(self, mock_maya_env):
        mod = _load_script("maya-blend-shape-utils", "add_blend_shape_target.py")
        r = mod.run({"blend_shape": "bs1"})
        assert r.success is False

    def test_blend_shape_not_found(self, mock_maya_env):
        mock_maya_env.objExists.side_effect = lambda n: n != "bs1"
        mod = _load_script("maya-blend-shape-utils", "add_blend_shape_target.py")
        r = mod.run({"blend_shape": "bs1", "target": "mesh2"})
        assert r.success is False

    def test_target_not_found(self, mock_maya_env):
        mock_maya_env.objExists.side_effect = lambda n: n == "bs1"
        mod = _load_script("maya-blend-shape-utils", "add_blend_shape_target.py")
        r = mod.run({"blend_shape": "bs1", "target": "mesh2"})
        assert r.success is False

    def test_add_target_auto_index(self, mock_maya_env):
        mock_maya_env.objExists.return_value = True
        mock_maya_env.aliasAttr.return_value = ["Smile", "weight[0]"]
        mock_maya_env.blendShape.return_value = ["pSphere1"]
        mod = _load_script("maya-blend-shape-utils", "add_blend_shape_target.py")
        r = mod.run({"blend_shape": "bs1", "target": "mesh2"})
        assert r.success is True
        assert r.context["index"] == 1  # auto-assigned (len/2 = 1)

    def test_add_target_explicit_index(self, mock_maya_env):
        mock_maya_env.objExists.return_value = True
        mock_maya_env.aliasAttr.return_value = []
        mock_maya_env.blendShape.return_value = ["pSphere1"]
        mod = _load_script("maya-blend-shape-utils", "add_blend_shape_target.py")
        r = mod.run({"blend_shape": "bs1", "target": "mesh2", "index": 5})
        assert r.success is True
        assert r.context["index"] == 5

    def test_exception(self, mock_maya_env):
        mock_maya_env.objExists.side_effect = RuntimeError("err")
        mod = _load_script("maya-blend-shape-utils", "add_blend_shape_target.py")
        r = mod.run({"blend_shape": "bs1", "target": "mesh2"})
        assert r.success is False


# ---------------------------------------------------------------------------
# maya-material-library
# ---------------------------------------------------------------------------

class TestSaveMaterialPreset:
    def test_missing_material(self, mock_maya_env, tmp_path):
        mod = _load_script("maya-material-library", "save_material_preset.py")
        r = mod.run({"preset_name": "test", "preset_dir": str(tmp_path)})
        assert r.success is False
        assert "material" in r.error.lower()

    def test_missing_preset_name(self, mock_maya_env, tmp_path):
        mod = _load_script("maya-material-library", "save_material_preset.py")
        r = mod.run({"material": "mat1", "preset_dir": str(tmp_path)})
        assert r.success is False

    def test_material_not_found(self, mock_maya_env, tmp_path):
        mock_maya_env.objExists.return_value = False
        mod = _load_script("maya-material-library", "save_material_preset.py")
        r = mod.run({"material": "mat1", "preset_name": "test", "preset_dir": str(tmp_path)})
        assert r.success is False

    def test_save_lambert(self, mock_maya_env, tmp_path):
        mock_maya_env.objExists.side_effect = lambda n: True
        mock_maya_env.objectType.return_value = "lambert"
        mock_maya_env.getAttr.side_effect = lambda attr: [(0.8, 0.2, 0.1)] if "color" in attr.lower() else 0.8
        mod = _load_script("maya-material-library", "save_material_preset.py")
        r = mod.run({"material": "mat1", "preset_name": "myLambert", "preset_dir": str(tmp_path)})
        assert r.success is True
        assert r.context["shader_type"] == "lambert"
        assert os.path.isfile(r.context["preset_path"])

    def test_saved_json_valid(self, mock_maya_env, tmp_path):
        mock_maya_env.objExists.side_effect = lambda n: True
        mock_maya_env.objectType.return_value = "lambert"
        mock_maya_env.getAttr.return_value = 0.5
        mod = _load_script("maya-material-library", "save_material_preset.py")
        r = mod.run({"material": "mat1", "preset_name": "valid", "preset_dir": str(tmp_path)})
        with open(r.context["preset_path"]) as fh:
            data = json.load(fh)
        assert "shader_type" in data
        assert "attributes" in data

    def test_exception(self, mock_maya_env, tmp_path):
        mock_maya_env.objExists.side_effect = RuntimeError("err")
        mod = _load_script("maya-material-library", "save_material_preset.py")
        r = mod.run({"material": "mat1", "preset_name": "test", "preset_dir": str(tmp_path)})
        assert r.success is False


class TestApplyMaterialPreset:
    def _make_preset(self, tmp_path, name="testPreset"):
        data = {"shader_type": "lambert", "attributes": {"diffuse": 0.8, "color": [0.5, 0.5, 0.5]}}
        p = tmp_path / "{}.json".format(name)
        p.write_text(json.dumps(data))
        return str(tmp_path)

    def test_missing_material(self, mock_maya_env, tmp_path):
        mod = _load_script("maya-material-library", "apply_material_preset.py")
        r = mod.run({"preset_name": "test", "preset_dir": str(tmp_path)})
        assert r.success is False

    def test_missing_preset_name(self, mock_maya_env, tmp_path):
        mod = _load_script("maya-material-library", "apply_material_preset.py")
        r = mod.run({"material": "mat1", "preset_dir": str(tmp_path)})
        assert r.success is False

    def test_material_not_found(self, mock_maya_env, tmp_path):
        mock_maya_env.objExists.return_value = False
        mod = _load_script("maya-material-library", "apply_material_preset.py")
        r = mod.run({"material": "mat1", "preset_name": "test", "preset_dir": str(tmp_path)})
        assert r.success is False

    def test_preset_not_found(self, mock_maya_env, tmp_path):
        mock_maya_env.objExists.return_value = True
        mod = _load_script("maya-material-library", "apply_material_preset.py")
        r = mod.run({"material": "mat1", "preset_name": "nonexistent", "preset_dir": str(tmp_path)})
        assert r.success is False
        assert "preset" in r.message.lower() or "preset" in r.error.lower()

    def test_apply_preset(self, mock_maya_env, tmp_path):
        preset_dir = self._make_preset(tmp_path)
        mock_maya_env.objExists.return_value = True
        mod = _load_script("maya-material-library", "apply_material_preset.py")
        r = mod.run({"material": "mat1", "preset_name": "testPreset", "preset_dir": preset_dir})
        assert r.success is True
        assert r.context["applied_count"] >= 1

    def test_exception(self, mock_maya_env, tmp_path):
        mock_maya_env.objExists.side_effect = RuntimeError("err")
        mod = _load_script("maya-material-library", "apply_material_preset.py")
        r = mod.run({"material": "mat1", "preset_name": "test", "preset_dir": str(tmp_path)})
        assert r.success is False


class TestListMaterialPresets:
    def test_no_directory(self, mock_maya_env, tmp_path):
        mod = _load_script("maya-material-library", "list_material_presets.py")
        r = mod.run({"preset_dir": str(tmp_path / "nonexistent")})
        assert r.success is True
        assert r.context["count"] == 0

    def test_list_presets(self, mock_maya_env, tmp_path):
        for name in ["mat_a", "mat_b"]:
            p = tmp_path / "{}.json".format(name)
            p.write_text(json.dumps({"shader_type": "lambert", "attributes": {}}))
        mod = _load_script("maya-material-library", "list_material_presets.py")
        r = mod.run({"preset_dir": str(tmp_path)})
        assert r.success is True
        assert r.context["count"] == 2

    def test_filter_by_shader_type(self, mock_maya_env, tmp_path):
        (tmp_path / "a.json").write_text(json.dumps({"shader_type": "lambert", "attributes": {}}))
        (tmp_path / "b.json").write_text(json.dumps({"shader_type": "blinn", "attributes": {}}))
        mod = _load_script("maya-material-library", "list_material_presets.py")
        r = mod.run({"preset_dir": str(tmp_path), "shader_type": "lambert"})
        assert r.success is True
        assert r.context["count"] == 1

    def test_skip_invalid_json(self, mock_maya_env, tmp_path):
        (tmp_path / "bad.json").write_text("NOT JSON")
        (tmp_path / "good.json").write_text(json.dumps({"shader_type": "lambert", "attributes": {}}))
        mod = _load_script("maya-material-library", "list_material_presets.py")
        r = mod.run({"preset_dir": str(tmp_path)})
        assert r.success is True
        assert r.context["count"] == 1

    def test_exception(self, mock_maya_env):
        mod = _load_script("maya-material-library", "list_material_presets.py")
        with patch("os.path.isdir", side_effect=RuntimeError("err")):
            r = mod.run({"preset_dir": "/some/path"})
        assert r.success is False


class TestDeleteMaterialPreset:
    def test_missing_preset_name(self, mock_maya_env, tmp_path):
        mod = _load_script("maya-material-library", "delete_material_preset.py")
        r = mod.run({"preset_dir": str(tmp_path)})
        assert r.success is False

    def test_preset_not_found(self, mock_maya_env, tmp_path):
        mod = _load_script("maya-material-library", "delete_material_preset.py")
        r = mod.run({"preset_name": "nonexistent", "preset_dir": str(tmp_path)})
        assert r.success is False

    def test_delete_success(self, mock_maya_env, tmp_path):
        p = tmp_path / "myMat.json"
        p.write_text("{}")
        mod = _load_script("maya-material-library", "delete_material_preset.py")
        r = mod.run({"preset_name": "myMat", "preset_dir": str(tmp_path)})
        assert r.success is True
        assert not p.exists()

    def test_exception(self, mock_maya_env, tmp_path):
        p = tmp_path / "mat.json"
        p.write_text("{}")
        mod = _load_script("maya-material-library", "delete_material_preset.py")
        with patch("os.remove", side_effect=OSError("permission denied")):
            r = mod.run({"preset_name": "mat", "preset_dir": str(tmp_path)})
        assert r.success is False


class TestCreateMaterialFromPreset:
    def _make_preset(self, tmp_path, name="testMat"):
        data = {"shader_type": "lambert", "attributes": {"diffuse": 0.8}}
        p = tmp_path / "{}.json".format(name)
        p.write_text(json.dumps(data))
        return str(tmp_path)

    def test_missing_preset_name(self, mock_maya_env, tmp_path):
        mod = _load_script("maya-material-library", "create_material_from_preset.py")
        r = mod.run({"preset_dir": str(tmp_path)})
        assert r.success is False

    def test_preset_not_found(self, mock_maya_env, tmp_path):
        mod = _load_script("maya-material-library", "create_material_from_preset.py")
        r = mod.run({"preset_name": "none", "preset_dir": str(tmp_path)})
        assert r.success is False

    def test_create_material(self, mock_maya_env, tmp_path):
        preset_dir = self._make_preset(tmp_path)
        mock_maya_env.shadingNode.return_value = "testMat_mat1"
        mock_maya_env.sets.return_value = "testMat_mat1_SG"
        mock_maya_env.objExists.return_value = True
        mod = _load_script("maya-material-library", "create_material_from_preset.py")
        r = mod.run({"preset_name": "testMat", "preset_dir": preset_dir})
        assert r.success is True
        assert r.context["shader_type"] == "lambert"

    def test_assign_to_objects(self, mock_maya_env, tmp_path):
        preset_dir = self._make_preset(tmp_path)
        mock_maya_env.shadingNode.return_value = "newMat"
        mock_maya_env.sets.return_value = "newMat_SG"
        mock_maya_env.objExists.return_value = True
        mod = _load_script("maya-material-library", "create_material_from_preset.py")
        r = mod.run({
            "preset_name": "testMat",
            "preset_dir": preset_dir,
            "assign_to": ["pSphere1", "pCube1"],
        })
        assert r.success is True
        assert len(r.context["assigned_objects"]) == 2

    def test_exception(self, mock_maya_env, tmp_path):
        preset_dir = self._make_preset(tmp_path)
        mock_maya_env.shadingNode.side_effect = RuntimeError("err")
        mod = _load_script("maya-material-library", "create_material_from_preset.py")
        r = mod.run({"preset_name": "testMat", "preset_dir": preset_dir})
        assert r.success is False


# ---------------------------------------------------------------------------
# maya-render-farm
# ---------------------------------------------------------------------------

class TestSubmitDeadlineJob:
    def test_no_scene_open(self, mock_maya_env):
        mock_maya_env.file.return_value = ""
        mod = _load_script("maya-render-farm", "submit_deadline_job.py")
        r = mod.run({})
        assert r.success is False
        assert "scene" in r.error.lower()

    def test_submit_success(self, mock_maya_env):
        mock_maya_env.file.return_value = "/path/to/scene.ma"
        mock_maya_env.workspace.return_value = "/project/"
        mock_maya_env.about.return_value = "2024"
        proc = MagicMock()
        proc.returncode = 0
        proc.stdout = "JobID: abc123"
        with patch("subprocess.run", return_value=proc):
            mod = _load_script("maya-render-farm", "submit_deadline_job.py")
            r = mod.run({"job_name": "TestRender", "frames": "1-10"})
        assert r.success is True
        assert r.context["frames"] == "1-10"

    def test_deadline_failure(self, mock_maya_env):
        mock_maya_env.file.return_value = "/path/to/scene.ma"
        mock_maya_env.workspace.return_value = "/project/"
        mock_maya_env.about.return_value = "2024"
        proc = MagicMock()
        proc.returncode = 1
        proc.stderr = "Connection refused"
        with patch("subprocess.run", return_value=proc):
            mod = _load_script("maya-render-farm", "submit_deadline_job.py")
            r = mod.run({})
        assert r.success is False

    def test_exception(self, mock_maya_env):
        mock_maya_env.file.return_value = "/path/to/scene.ma"
        mock_maya_env.workspace.return_value = "/project/"
        mock_maya_env.about.return_value = "2024"
        with patch("subprocess.run", side_effect=OSError("not found")):
            mod = _load_script("maya-render-farm", "submit_deadline_job.py")
            r = mod.run({})
        assert r.success is False


class TestListRenderFarmJobs:
    def test_list_jobs_success(self, mock_maya_env):
        proc = MagicMock()
        proc.returncode = 0
        proc.stdout = json.dumps([
            {"JobId": "j1", "Name": "Job1", "Status": "Active", "Frames": "1-10", "Priority": "50"},
            {"JobId": "j2", "Name": "Job2", "Status": "Completed", "Frames": "1-5", "Priority": "50"},
        ])
        with patch("subprocess.run", return_value=proc):
            mod = _load_script("maya-render-farm", "list_render_farm_jobs.py")
            r = mod.run({})
        assert r.success is True
        assert r.context["count"] == 2

    def test_filter_by_status(self, mock_maya_env):
        proc = MagicMock()
        proc.returncode = 0
        proc.stdout = json.dumps([
            {"JobId": "j1", "Name": "Job1", "Status": "active"},
            {"JobId": "j2", "Name": "Job2", "Status": "completed"},
        ])
        with patch("subprocess.run", return_value=proc):
            mod = _load_script("maya-render-farm", "list_render_farm_jobs.py")
            r = mod.run({"status": "active"})
        assert r.success is True
        assert r.context["count"] == 1

    def test_deadline_failure(self, mock_maya_env):
        proc = MagicMock()
        proc.returncode = 1
        proc.stderr = "No connection"
        with patch("subprocess.run", return_value=proc):
            mod = _load_script("maya-render-farm", "list_render_farm_jobs.py")
            r = mod.run({})
        assert r.success is False

    def test_exception(self, mock_maya_env):
        with patch("subprocess.run", side_effect=OSError("err")):
            mod = _load_script("maya-render-farm", "list_render_farm_jobs.py")
            r = mod.run({})
        assert r.success is False


class TestCancelRenderFarmJob:
    def test_missing_job_id(self, mock_maya_env):
        mod = _load_script("maya-render-farm", "cancel_render_farm_job.py")
        r = mod.run({})
        assert r.success is False

    def test_cancel_success(self, mock_maya_env):
        proc = MagicMock()
        proc.returncode = 0
        proc.stdout = "Job failed successfully"
        with patch("subprocess.run", return_value=proc):
            mod = _load_script("maya-render-farm", "cancel_render_farm_job.py")
            r = mod.run({"job_id": "abc123"})
        assert r.success is True
        assert r.context["job_id"] == "abc123"

    def test_cancel_failure(self, mock_maya_env):
        proc = MagicMock()
        proc.returncode = 1
        proc.stderr = "Job not found"
        with patch("subprocess.run", return_value=proc):
            mod = _load_script("maya-render-farm", "cancel_render_farm_job.py")
            r = mod.run({"job_id": "badid"})
        assert r.success is False

    def test_exception(self, mock_maya_env):
        with patch("subprocess.run", side_effect=OSError("err")):
            mod = _load_script("maya-render-farm", "cancel_render_farm_job.py")
            r = mod.run({"job_id": "abc"})
        assert r.success is False


class TestGenerateSubmissionManifest:
    def test_missing_output_path(self, mock_maya_env):
        mod = _load_script("maya-render-farm", "generate_submission_manifest.py")
        r = mod.run({})
        assert r.success is False

    def test_generate_manifest(self, mock_maya_env, tmp_path):
        mock_maya_env.file.return_value = "/project/scene.ma"
        mock_maya_env.playbackOptions.side_effect = lambda **kw: 1 if kw.get("minTime") else 100
        mock_maya_env.ls.return_value = ["defaultRenderGlobals"]
        mock_maya_env.getAttr.side_effect = lambda attr: "arnold" if "Renderer" in attr else 1920 if "width" in attr else 1080
        mock_maya_env.about.return_value = "2024"
        mock_maya_env.listCameras.return_value = ["camera1"]
        out_path = str(tmp_path / "manifest.json")
        mod = _load_script("maya-render-farm", "generate_submission_manifest.py")
        r = mod.run({"output_path": out_path})
        assert r.success is True
        assert os.path.isfile(out_path)

    def test_manifest_content(self, mock_maya_env, tmp_path):
        mock_maya_env.file.return_value = "/project/scene.ma"
        mock_maya_env.playbackOptions.side_effect = lambda **kw: 1 if kw.get("minTime") else 50
        mock_maya_env.ls.return_value = []
        mock_maya_env.getAttr.side_effect = lambda attr: 1280 if "width" in attr else 720
        mock_maya_env.about.return_value = "2025"
        mock_maya_env.listCameras.return_value = []
        out_path = str(tmp_path / "m.json")
        mod = _load_script("maya-render-farm", "generate_submission_manifest.py")
        mod.run({"output_path": out_path, "renderer": "vray", "chunk_size": 5})
        with open(out_path) as fh:
            data = json.load(fh)
        assert data["renderer"] == "vray"
        assert data["chunk_size"] == 5

    def test_exception(self, mock_maya_env, tmp_path):
        mock_maya_env.file.side_effect = RuntimeError("err")
        mod = _load_script("maya-render-farm", "generate_submission_manifest.py")
        r = mod.run({"output_path": str(tmp_path / "m.json")})
        assert r.success is False


class TestGetJobOutput:
    def test_missing_job_id(self, mock_maya_env):
        mod = _load_script("maya-render-farm", "get_job_output.py")
        r = mod.run({})
        assert r.success is False

    def test_get_output_success(self, mock_maya_env):
        proc = MagicMock()
        proc.returncode = 0
        proc.stdout = "/renders/job1\n/renders/job1_extra\n"
        with patch("subprocess.run", return_value=proc):
            mod = _load_script("maya-render-farm", "get_job_output.py")
            r = mod.run({"job_id": "j1"})
        assert r.success is True
        assert r.context["directory_count"] == 2

    def test_get_output_with_check_exists(self, mock_maya_env, tmp_path):
        proc = MagicMock()
        proc.returncode = 0
        proc.stdout = str(tmp_path) + "\n"
        # Create some fake render files
        (tmp_path / "frame.0001.exr").write_bytes(b"")
        (tmp_path / "frame.0002.exr").write_bytes(b"")
        with patch("subprocess.run", return_value=proc):
            mod = _load_script("maya-render-farm", "get_job_output.py")
            r = mod.run({"job_id": "j1", "check_exists": True})
        assert r.success is True
        dirs = r.context["output_directories"]
        assert dirs[0]["file_count"] == 2

    def test_deadline_failure(self, mock_maya_env):
        proc = MagicMock()
        proc.returncode = 1
        proc.stderr = "Job not found"
        with patch("subprocess.run", return_value=proc):
            mod = _load_script("maya-render-farm", "get_job_output.py")
            r = mod.run({"job_id": "bad"})
        assert r.success is False

    def test_exception(self, mock_maya_env):
        with patch("subprocess.run", side_effect=OSError("err")):
            mod = _load_script("maya-render-farm", "get_job_output.py")
            r = mod.run({"job_id": "j1"})
        assert r.success is False
