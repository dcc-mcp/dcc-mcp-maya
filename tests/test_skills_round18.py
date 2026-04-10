"""Round 18: Tests for maya-shot-export, maya-material-library, maya-toon,
maya-nparticles, and maya-render-farm skills.
"""

# Import future modules
from __future__ import annotations

# Import built-in modules
import json
import os
import sys
import tempfile
from unittest.mock import MagicMock, patch

# Import third-party modules
import pytest

from tests.conftest import load_skill_script, make_mock_maya


# ---------------------------------------------------------------------------
# maya-shot-export
# ---------------------------------------------------------------------------


class TestExportShotFbx:
    """Tests for export_shot_fbx script."""

    def _make_cmds(self):
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.ls.return_value = ["pSphere1"]
        mock_cmds.playbackOptions.side_effect = lambda **kw: 1.0 if kw.get("minTime") else 24.0
        mock_cmds.pluginInfo.return_value = True
        mock_cmds.file.return_value = "/tmp/test.fbx"
        return mock_maya, mock_cmds

    def test_export_with_objects(self):
        mock_maya, mock_cmds = self._make_cmds()
        mock_mel = MagicMock()
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "shot.fbx")
            with patch.dict(
                sys.modules,
                {"maya": mock_maya, "maya.cmds": mock_cmds, "maya.mel": mock_mel},
            ):
                mod = load_skill_script("maya-shot-export", "export_shot_fbx")
                result = mod.export_shot_fbx(out, objects=["pSphere1"])
        assert result["success"] is True
        assert "fbx" in result["message"].lower() or result["context"]["file_path"] == out

    def test_export_no_selection(self):
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.ls.return_value = []
        mock_mel = MagicMock()
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "shot.fbx")
            with patch.dict(
                sys.modules,
                {"maya": mock_maya, "maya.cmds": mock_cmds, "maya.mel": mock_mel},
            ):
                mod = load_skill_script("maya-shot-export", "export_shot_fbx")
                result = mod.export_shot_fbx(out)
        assert result["success"] is False

    def test_export_custom_frame_range(self):
        mock_maya, mock_cmds = self._make_cmds()
        mock_mel = MagicMock()
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "shot_fr.fbx")
            with patch.dict(
                sys.modules,
                {"maya": mock_maya, "maya.cmds": mock_cmds, "maya.mel": mock_mel},
            ):
                mod = load_skill_script("maya-shot-export", "export_shot_fbx")
                result = mod.export_shot_fbx(out, objects=["pSphere1"], start_frame=10, end_frame=50)
        assert result["success"] is True
        assert result["context"]["start_frame"] == 10
        assert result["context"]["end_frame"] == 50

    def test_no_maya(self):
        with patch.dict(sys.modules, {"maya": None, "maya.cmds": None, "maya.mel": None}):
            mod = load_skill_script("maya-shot-export", "export_shot_fbx")
            result = mod.export_shot_fbx("/tmp/x.fbx", objects=["a"])
        assert result["success"] is False

    def test_main_passthrough(self):
        mock_maya, mock_cmds = self._make_cmds()
        mock_mel = MagicMock()
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "main.fbx")
            with patch.dict(
                sys.modules,
                {"maya": mock_maya, "maya.cmds": mock_cmds, "maya.mel": mock_mel},
            ):
                mod = load_skill_script("maya-shot-export", "export_shot_fbx")
                result = mod.main(file_path=out, objects=["pSphere1"])
        assert isinstance(result, dict)


class TestExportShotAlembic:
    """Tests for export_shot_alembic script."""

    def _make_cmds(self):
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.ls.return_value = ["pCube1"]
        mock_cmds.playbackOptions.side_effect = lambda **kw: 1.0 if kw.get("minTime") else 24.0
        mock_cmds.pluginInfo.return_value = True
        mock_cmds.AbcExport.return_value = None
        return mock_maya, mock_cmds

    def test_export_success(self):
        mock_maya, mock_cmds = self._make_cmds()
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "anim.abc")
            with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
                mod = load_skill_script("maya-shot-export", "export_shot_alembic")
                result = mod.export_shot_alembic(out, objects=["pCube1"])
        assert result["success"] is True
        assert result["context"]["objects"] == ["pCube1"]

    def test_no_selection(self):
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.ls.return_value = []
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "empty.abc")
            with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
                mod = load_skill_script("maya-shot-export", "export_shot_alembic")
                result = mod.export_shot_alembic(out)
        assert result["success"] is False

    def test_no_maya(self):
        with patch.dict(sys.modules, {"maya": None, "maya.cmds": None}):
            mod = load_skill_script("maya-shot-export", "export_shot_alembic")
            result = mod.export_shot_alembic("/tmp/x.abc", objects=["a"])
        assert result["success"] is False


class TestExportCamera:
    """Tests for export_camera script."""

    def _make_cmds(self):
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.objectType.return_value = "transform"
        mock_cmds.pluginInfo.return_value = True
        mock_cmds.file.return_value = "/tmp/cam.fbx"
        return mock_maya, mock_cmds

    def test_export_fbx(self):
        mock_maya, mock_cmds = self._make_cmds()
        mock_mel = MagicMock()
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "cam.fbx")
            with patch.dict(
                sys.modules,
                {"maya": mock_maya, "maya.cmds": mock_cmds, "maya.mel": mock_mel},
            ):
                mod = load_skill_script("maya-shot-export", "export_camera")
                result = mod.export_camera("persp", out)
        assert result["success"] is True
        assert result["context"]["camera"] == "persp"

    def test_camera_shape_resolved(self):
        mock_maya, mock_cmds = self._make_cmds()
        mock_cmds.objectType.return_value = "camera"
        mock_cmds.listRelatives.return_value = ["perspShape_parent"]
        mock_mel = MagicMock()
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "cam_shape.fbx")
            with patch.dict(
                sys.modules,
                {"maya": mock_maya, "maya.cmds": mock_cmds, "maya.mel": mock_mel},
            ):
                mod = load_skill_script("maya-shot-export", "export_camera")
                result = mod.export_camera("perspShape", out)
        assert result["success"] is True

    def test_camera_not_found(self):
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.objExists.return_value = False
        mock_mel = MagicMock()
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "missing.fbx")
            with patch.dict(
                sys.modules,
                {"maya": mock_maya, "maya.cmds": mock_cmds, "maya.mel": mock_mel},
            ):
                mod = load_skill_script("maya-shot-export", "export_camera")
                result = mod.export_camera("nonexistent", out)
        assert result["success"] is False

    def test_export_maya_ascii(self):
        mock_maya, mock_cmds = self._make_cmds()
        mock_mel = MagicMock()
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "cam.ma")
            with patch.dict(
                sys.modules,
                {"maya": mock_maya, "maya.cmds": mock_cmds, "maya.mel": mock_mel},
            ):
                mod = load_skill_script("maya-shot-export", "export_camera")
                result = mod.export_camera("persp", out, file_format="ma")
        assert result["success"] is True
        assert result["context"]["file_format"] == "ma"

    def test_no_maya(self):
        with patch.dict(sys.modules, {"maya": None, "maya.cmds": None, "maya.mel": None}):
            mod = load_skill_script("maya-shot-export", "export_camera")
            result = mod.export_camera("persp", "/tmp/cam.fbx")
        assert result["success"] is False


class TestGetShotInfo:
    """Tests for get_shot_info script."""

    def test_shot_info_success(self):
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.file.return_value = "/path/to/shot_001.ma"
        mock_cmds.playbackOptions.side_effect = lambda **kw: (
            1.0 if kw.get("minTime") else 120.0
        )
        mock_cmds.currentTime.return_value = 50.0
        mock_cmds.getPanel.return_value = ["modelPanel1"]
        mock_cmds.modelEditor.return_value = "persp"
        mock_cmds.ls.return_value = ["perspShape", "topShape"]
        mock_cmds.listRelatives.side_effect = lambda s, **kw: [s.replace("Shape", "")]
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-shot-export", "get_shot_info")
            result = mod.get_shot_info()
        assert result["success"] is True
        assert result["context"]["scene_name"] == "shot_001"
        assert result["context"]["start_frame"] == 1.0
        assert result["context"]["end_frame"] == 120.0

    def test_untitled_scene(self):
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.file.return_value = ""
        mock_cmds.playbackOptions.return_value = 1.0
        mock_cmds.currentTime.return_value = 1.0
        mock_cmds.getPanel.return_value = []
        mock_cmds.ls.return_value = []
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-shot-export", "get_shot_info")
            result = mod.get_shot_info()
        assert result["success"] is True
        assert result["context"]["scene_name"] == "untitled"

    def test_no_maya(self):
        with patch.dict(sys.modules, {"maya": None, "maya.cmds": None}):
            mod = load_skill_script("maya-shot-export", "get_shot_info")
            result = mod.get_shot_info()
        assert result["success"] is False


# ---------------------------------------------------------------------------
# maya-material-library
# ---------------------------------------------------------------------------


class TestSaveMaterial:
    """Tests for save_material script."""

    def test_save_success(self):
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.objectType.return_value = "lambert"
        mock_cmds.listAttr.return_value = ["color", "transparency"]
        mock_cmds.getAttr.return_value = [(0.5, 0.5, 0.5)]
        with tempfile.TemporaryDirectory() as lib_dir:
            with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
                mod = load_skill_script("maya-material-library", "save_material")
                result = mod.save_material("lambert1", lib_dir)
        assert result["success"] is True
        assert "lambert1" in result["message"]

    def test_material_not_found(self):
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.objExists.return_value = False
        with tempfile.TemporaryDirectory() as lib_dir:
            with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
                mod = load_skill_script("maya-material-library", "save_material")
                result = mod.save_material("missing_mat", lib_dir)
        assert result["success"] is False

    def test_no_overwrite_existing(self):
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.objectType.return_value = "blinn"
        mock_cmds.listAttr.return_value = []
        with tempfile.TemporaryDirectory() as lib_dir:
            # Pre-create file
            existing = os.path.join(lib_dir, "blinn1.json")
            with open(existing, "w") as fh:
                fh.write("{}")
            with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
                mod = load_skill_script("maya-material-library", "save_material")
                result = mod.save_material("blinn1", lib_dir, overwrite=False)
        assert result["success"] is False
        assert "already exists" in result["message"].lower()

    def test_custom_preset_name(self):
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.objectType.return_value = "phong"
        mock_cmds.listAttr.return_value = ["cosinePower"]
        mock_cmds.getAttr.return_value = 20.0
        with tempfile.TemporaryDirectory() as lib_dir:
            with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
                mod = load_skill_script("maya-material-library", "save_material")
                result = mod.save_material("phong1", lib_dir, preset_name="hero_skin")
        assert result["success"] is True
        assert "hero_skin" in result["context"]["file_path"]

    def test_no_maya(self):
        with patch.dict(sys.modules, {"maya": None, "maya.cmds": None}):
            mod = load_skill_script("maya-material-library", "save_material")
            result = mod.save_material("mat", "/tmp/lib")
        assert result["success"] is False


class TestLoadMaterial:
    """Tests for load_material script."""

    def test_load_success(self):
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.shadingNode.return_value = "lambert2"
        mock_cmds.sets.return_value = "lambert2_SG"
        mock_cmds.connectAttr.return_value = None
        mock_cmds.objExists.return_value = True
        with tempfile.TemporaryDirectory() as lib_dir:
            preset = os.path.join(lib_dir, "lambert2.json")
            with open(preset, "w") as fh:
                json.dump({"node_type": "lambert", "material": "lambert2", "attributes": {"colorR": 0.5}}, fh)
            with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
                mod = load_skill_script("maya-material-library", "load_material")
                result = mod.load_material(preset)
        assert result["success"] is True
        assert result["context"]["material"] == "lambert2"

    def test_file_not_found(self):
        mock_maya, mock_cmds = make_mock_maya()
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-material-library", "load_material")
            result = mod.load_material("/nonexistent/preset.json")
        assert result["success"] is False

    def test_assign_on_load(self):
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.shadingNode.return_value = "phong2"
        mock_cmds.sets.return_value = "phong2_SG"
        mock_cmds.connectAttr.return_value = None
        mock_cmds.objExists.return_value = True
        with tempfile.TemporaryDirectory() as lib_dir:
            preset = os.path.join(lib_dir, "phong2.json")
            with open(preset, "w") as fh:
                json.dump({"node_type": "phong", "material": "phong2", "attributes": {}}, fh)
            with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
                mod = load_skill_script("maya-material-library", "load_material")
                result = mod.load_material(preset, assign_to=["pSphere1"])
        assert result["success"] is True
        assert "pSphere1" in result["context"]["assigned_to"]

    def test_no_maya(self):
        with tempfile.TemporaryDirectory() as lib_dir:
            preset = os.path.join(lib_dir, "dummy.json")
            with open(preset, "w") as fh:
                json.dump({"node_type": "lambert", "material": "m", "attributes": {}}, fh)
            with patch.dict(sys.modules, {"maya": None, "maya.cmds": None}):
                mod = load_skill_script("maya-material-library", "load_material")
                result = mod.load_material(preset)
        assert result["success"] is False


class TestListMaterials:
    """Tests for list_materials script."""

    def test_list_success(self):
        mock_maya, mock_cmds = make_mock_maya()
        with tempfile.TemporaryDirectory() as lib_dir:
            for name in ["mat_a", "mat_b"]:
                with open(os.path.join(lib_dir, "{}.json".format(name)), "w") as fh:
                    json.dump({"node_type": "lambert", "material": name, "attributes": {}}, fh)
            with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
                mod = load_skill_script("maya-material-library", "list_materials")
                result = mod.list_materials(lib_dir)
        assert result["success"] is True
        assert result["context"]["count"] == 2

    def test_missing_dir(self):
        mock_maya, mock_cmds = make_mock_maya()
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-material-library", "list_materials")
            result = mod.list_materials("/nonexistent/lib_dir")
        assert result["success"] is False

    def test_empty_dir(self):
        mock_maya, mock_cmds = make_mock_maya()
        with tempfile.TemporaryDirectory() as lib_dir:
            with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
                mod = load_skill_script("maya-material-library", "list_materials")
                result = mod.list_materials(lib_dir)
        assert result["success"] is True
        assert result["context"]["count"] == 0


class TestDeleteMaterialPreset:
    """Tests for delete_material_preset script."""

    def test_delete_success(self):
        mock_maya, mock_cmds = make_mock_maya()
        with tempfile.TemporaryDirectory() as lib_dir:
            preset = os.path.join(lib_dir, "old_mat.json")
            with open(preset, "w") as fh:
                fh.write("{}")
            with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
                mod = load_skill_script("maya-material-library", "delete_material_preset")
                result = mod.delete_material_preset(preset)
        assert result["success"] is True
        assert not os.path.exists(preset)

    def test_file_not_found(self):
        mock_maya, mock_cmds = make_mock_maya()
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-material-library", "delete_material_preset")
            result = mod.delete_material_preset("/nonexistent/mat.json")
        assert result["success"] is False


# ---------------------------------------------------------------------------
# maya-toon
# ---------------------------------------------------------------------------


class TestAddToonOutline:
    """Tests for add_toon_outline script."""

    def _make_cmds(self):
        mock_maya, mock_cmds = make_mock_maya()
        mock_mel = MagicMock()
        mock_cmds.ls.return_value = ["pSphere1"]
        mock_cmds.objectType.return_value = "mesh"
        mock_cmds.listRelatives.return_value = []
        mock_cmds.rename.return_value = "pfxToon1"
        mock_cmds.attributeQuery.return_value = True
        mock_cmds.setAttr.return_value = None
        return mock_maya, mock_cmds, mock_mel

    def test_add_outline_success(self):
        mock_maya, mock_cmds, mock_mel = self._make_cmds()
        # Simulate pfxToon node existing after MEL call
        mock_cmds.ls.side_effect = [
            ["pSphere1"],       # first ls call for selection
            ["pfxToon_new"],    # second ls(type="pfxToon")
        ]
        with patch.dict(
            sys.modules,
            {"maya": mock_maya, "maya.cmds": mock_cmds, "maya.mel": mock_mel},
        ):
            mod = load_skill_script("maya-toon", "add_toon_outline")
            result = mod.add_toon_outline(objects=["pSphere1"])
        assert result["success"] is True

    def test_no_objects_no_selection(self):
        mock_maya, mock_cmds, mock_mel = self._make_cmds()
        mock_cmds.ls.return_value = []
        with patch.dict(
            sys.modules,
            {"maya": mock_maya, "maya.cmds": mock_cmds, "maya.mel": mock_mel},
        ):
            mod = load_skill_script("maya-toon", "add_toon_outline")
            result = mod.add_toon_outline()
        assert result["success"] is False

    def test_non_mesh_objects(self):
        mock_maya, mock_cmds, mock_mel = self._make_cmds()
        mock_cmds.ls.return_value = ["joint1"]
        mock_cmds.objectType.return_value = "joint"
        mock_cmds.listRelatives.return_value = []  # no mesh shapes
        with patch.dict(
            sys.modules,
            {"maya": mock_maya, "maya.cmds": mock_cmds, "maya.mel": mock_mel},
        ):
            mod = load_skill_script("maya-toon", "add_toon_outline")
            result = mod.add_toon_outline(objects=["joint1"])
        assert result["success"] is False

    def test_no_maya(self):
        with patch.dict(
            sys.modules, {"maya": None, "maya.cmds": None, "maya.mel": None}
        ):
            mod = load_skill_script("maya-toon", "add_toon_outline")
            result = mod.add_toon_outline(objects=["pSphere1"])
        assert result["success"] is False


class TestCreateToonShader:
    """Tests for create_toon_shader script."""

    def test_create_success(self):
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.shadingNode.return_value = "rampShader1"
        mock_cmds.sets.return_value = "rampShader1_SG"
        mock_cmds.connectAttr.return_value = None
        mock_cmds.objExists.return_value = True
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-toon", "create_toon_shader")
            result = mod.create_toon_shader()
        assert result["success"] is True
        assert result["context"]["shader"] == "rampShader1"

    def test_create_with_assignment(self):
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.shadingNode.return_value = "rampShader2"
        mock_cmds.sets.return_value = "rampShader2_SG"
        mock_cmds.connectAttr.return_value = None
        mock_cmds.objExists.return_value = True
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-toon", "create_toon_shader")
            result = mod.create_toon_shader(assign_to=["pCube1"])
        assert result["success"] is True
        assert "pCube1" in result["context"]["assigned_to"]

    def test_no_maya(self):
        with patch.dict(sys.modules, {"maya": None, "maya.cmds": None}):
            mod = load_skill_script("maya-toon", "create_toon_shader")
            result = mod.create_toon_shader()
        assert result["success"] is False


class TestSetOutlineWidth:
    """Tests for set_outline_width script."""

    def test_set_width_success(self):
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.objectType.return_value = "pfxToon"
        mock_cmds.setAttr.return_value = None
        mock_cmds.attributeQuery.return_value = True
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-toon", "set_outline_width")
            result = mod.set_outline_width("pfxToon1", 2.5)
        assert result["success"] is True
        assert result["context"]["line_width"] == 2.5

    def test_node_not_found(self):
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.objExists.return_value = False
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-toon", "set_outline_width")
            result = mod.set_outline_width("missing_toon", 1.0)
        assert result["success"] is False

    def test_wrong_node_type(self):
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.objectType.return_value = "transform"
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-toon", "set_outline_width")
            result = mod.set_outline_width("pSphere1", 1.0)
        assert result["success"] is False

    def test_no_maya(self):
        with patch.dict(sys.modules, {"maya": None, "maya.cmds": None}):
            mod = load_skill_script("maya-toon", "set_outline_width")
            result = mod.set_outline_width("pfxToon1", 1.0)
        assert result["success"] is False


class TestListToonOutlines:
    """Tests for list_toon_outlines script."""

    def test_list_success(self):
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.ls.return_value = ["pfxToon1", "pfxToon2"]
        mock_cmds.getAttr.return_value = 1.5
        mock_cmds.listConnections.return_value = ["pSphereShape1"]
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-toon", "list_toon_outlines")
            result = mod.list_toon_outlines()
        assert result["success"] is True
        assert result["context"]["count"] == 2

    def test_no_outlines(self):
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.ls.return_value = []
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-toon", "list_toon_outlines")
            result = mod.list_toon_outlines()
        assert result["success"] is True
        assert result["context"]["count"] == 0

    def test_no_maya(self):
        with patch.dict(sys.modules, {"maya": None, "maya.cmds": None}):
            mod = load_skill_script("maya-toon", "list_toon_outlines")
            result = mod.list_toon_outlines()
        assert result["success"] is False


# ---------------------------------------------------------------------------
# maya-nparticles
# ---------------------------------------------------------------------------


class TestCreateNParticleEmitter:
    """Tests for create_nparticle_emitter script."""

    def _make_cmds(self):
        mock_maya, mock_cmds = make_mock_maya()
        mock_mel = MagicMock()
        mock_cmds.ls.side_effect = [
            ["nParticleShape1"],    # ls(type="nParticle") — particle created
            ["nucleus1"],           # ls(type="nucleus")
        ]
        mock_cmds.listRelatives.return_value = ["nParticle1"]
        mock_cmds.listConnections.return_value = ["emitter1"]
        mock_cmds.rename.return_value = "myParticles"
        mock_cmds.setAttr.return_value = None
        mock_cmds.move.return_value = None
        return mock_maya, mock_cmds, mock_mel

    def test_create_success(self):
        mock_maya, mock_cmds, mock_mel = self._make_cmds()
        with patch.dict(
            sys.modules,
            {"maya": mock_maya, "maya.cmds": mock_cmds, "maya.mel": mock_mel},
        ):
            mod = load_skill_script("maya-nparticles", "create_nparticle_emitter")
            result = mod.create_nparticle_emitter()
        assert result["success"] is True

    def test_no_particle_created(self):
        mock_maya, mock_cmds = make_mock_maya()
        mock_mel = MagicMock()
        mock_cmds.ls.return_value = []  # no nParticle found
        with patch.dict(
            sys.modules,
            {"maya": mock_maya, "maya.cmds": mock_cmds, "maya.mel": mock_mel},
        ):
            mod = load_skill_script("maya-nparticles", "create_nparticle_emitter")
            result = mod.create_nparticle_emitter()
        assert result["success"] is False

    def test_no_maya(self):
        with patch.dict(
            sys.modules, {"maya": None, "maya.cmds": None, "maya.mel": None}
        ):
            mod = load_skill_script("maya-nparticles", "create_nparticle_emitter")
            result = mod.create_nparticle_emitter()
        assert result["success"] is False


class TestSetNParticleAttribute:
    """Tests for set_nparticle_attribute script."""

    def test_set_success(self):
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.objectType.return_value = "nParticle"
        mock_cmds.attributeQuery.return_value = True
        mock_cmds.setAttr.return_value = None
        mock_cmds.getAttr.return_value = 0.2
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-nparticles", "set_nparticle_attribute")
            result = mod.set_nparticle_attribute("nParticleShape1", "radius", 0.2)
        assert result["success"] is True
        assert result["context"]["attribute"] == "radius"
        assert result["context"]["value"] == 0.2

    def test_node_not_found(self):
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.objExists.return_value = False
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-nparticles", "set_nparticle_attribute")
            result = mod.set_nparticle_attribute("missing", "radius", 1.0)
        assert result["success"] is False

    def test_wrong_node_type(self):
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.objectType.return_value = "transform"
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-nparticles", "set_nparticle_attribute")
            result = mod.set_nparticle_attribute("pSphere1", "radius", 1.0)
        assert result["success"] is False

    def test_attribute_not_found(self):
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.objectType.return_value = "nParticle"
        mock_cmds.attributeQuery.return_value = False
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-nparticles", "set_nparticle_attribute")
            result = mod.set_nparticle_attribute("nParticleShape1", "nonexistent", 1.0)
        assert result["success"] is False

    def test_no_maya(self):
        with patch.dict(sys.modules, {"maya": None, "maya.cmds": None}):
            mod = load_skill_script("maya-nparticles", "set_nparticle_attribute")
            result = mod.set_nparticle_attribute("nps", "radius", 1.0)
        assert result["success"] is False


class TestAddFieldToNParticles:
    """Tests for add_field_to_nparticles script."""

    def _make_cmds(self):
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.ls.return_value = ["nParticleShape1"]
        mock_cmds.gravity.return_value = ["gravityField1"]
        mock_cmds.turbulence.return_value = ["turbulenceField1"]
        mock_cmds.listRelatives.return_value = ["gravityFieldShape1"]
        return mock_maya, mock_cmds

    def test_add_gravity(self):
        mock_maya, mock_cmds = self._make_cmds()
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-nparticles", "add_field_to_nparticles")
            result = mod.add_field_to_nparticles(field_type="gravity")
        assert result["success"] is True
        assert result["context"]["field_type"] == "gravity"

    def test_add_turbulence(self):
        mock_maya, mock_cmds = self._make_cmds()
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-nparticles", "add_field_to_nparticles")
            result = mod.add_field_to_nparticles(field_type="turbulence", magnitude=5.0)
        assert result["success"] is True

    def test_invalid_field_type(self):
        mock_maya, mock_cmds = make_mock_maya()
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-nparticles", "add_field_to_nparticles")
            result = mod.add_field_to_nparticles(field_type="unknown_field")
        assert result["success"] is False

    def test_no_particle_shapes(self):
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.ls.return_value = []
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-nparticles", "add_field_to_nparticles")
            result = mod.add_field_to_nparticles(
                particle_shapes=[], field_type="gravity"
            )
        assert result["success"] is False

    def test_no_maya(self):
        with patch.dict(sys.modules, {"maya": None, "maya.cmds": None}):
            mod = load_skill_script("maya-nparticles", "add_field_to_nparticles")
            result = mod.add_field_to_nparticles()
        assert result["success"] is False


class TestListNParticleSystems:
    """Tests for list_nparticle_systems script."""

    def test_list_success(self):
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.ls.side_effect = [
            ["nParticleShape1"],
            ["nucleus1"],
        ]
        mock_cmds.nParticle.return_value = 150
        mock_cmds.attributeQuery.return_value = True
        mock_cmds.getAttr.return_value = 0.2
        mock_cmds.listConnections.return_value = []
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-nparticles", "list_nparticle_systems")
            result = mod.list_nparticle_systems()
        assert result["success"] is True
        assert result["context"]["system_count"] == 1

    def test_no_particles(self):
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.ls.return_value = []
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-nparticles", "list_nparticle_systems")
            result = mod.list_nparticle_systems()
        assert result["success"] is True
        assert result["context"]["system_count"] == 0

    def test_no_maya(self):
        with patch.dict(sys.modules, {"maya": None, "maya.cmds": None}):
            mod = load_skill_script("maya-nparticles", "list_nparticle_systems")
            result = mod.list_nparticle_systems()
        assert result["success"] is False


# ---------------------------------------------------------------------------
# maya-render-farm
# ---------------------------------------------------------------------------


class TestValidateSceneForFarm:
    """Tests for validate_scene_for_farm script."""

    def test_valid_scene(self):
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.file.return_value = "/path/to/scene.ma"
        mock_cmds.ls.return_value = []  # no file texture nodes
        mock_cmds.referenceQuery.return_value = True
        mock_cmds.getAttr.side_effect = lambda attr: (
            1.0 if "startFrame" in attr else 100.0 if "endFrame" in attr else "arnold"
        )
        mock_cmds.editRenderLayerGlobals.return_value = "defaultRenderLayer"
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-render-farm", "validate_scene_for_farm")
            result = mod.validate_scene_for_farm()
        assert result["success"] is True
        assert result["context"]["valid"] is True

    def test_unsaved_scene(self):
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.file.return_value = ""
        mock_cmds.ls.return_value = []
        mock_cmds.getAttr.side_effect = lambda attr: (
            1.0 if "startFrame" in attr else 100.0 if "endFrame" in attr else "arnold"
        )
        mock_cmds.editRenderLayerGlobals.return_value = "defaultRenderLayer"
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-render-farm", "validate_scene_for_farm")
            result = mod.validate_scene_for_farm()
        assert result["success"] is True
        assert result["context"]["valid"] is False
        assert any("unsaved" in issue.lower() for issue in result["context"]["issues"])

    def test_missing_texture(self):
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.file.return_value = "/path/to/scene.ma"
        mock_cmds.ls.return_value = ["file1"]
        mock_cmds.getAttr.side_effect = lambda attr: (
            "/nonexistent/texture.png" if "fileTextureName" in attr
            else 1.0 if "startFrame" in attr
            else 100.0 if "endFrame" in attr
            else "arnold"
        )
        mock_cmds.editRenderLayerGlobals.return_value = "defaultRenderLayer"
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-render-farm", "validate_scene_for_farm")
            result = mod.validate_scene_for_farm()
        assert result["success"] is True
        assert result["context"]["valid"] is False

    def test_no_maya(self):
        with patch.dict(sys.modules, {"maya": None, "maya.cmds": None}):
            mod = load_skill_script("maya-render-farm", "validate_scene_for_farm")
            result = mod.validate_scene_for_farm()
        assert result["success"] is False


class TestWriteRenderJob:
    """Tests for write_render_job script."""

    def test_write_success(self):
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.file.return_value = "/path/scene_001.ma"
        mock_cmds.getAttr.side_effect = lambda attr: (
            1.0 if "startFrame" in attr
            else 100.0 if "endFrame" in attr
            else "arnold"
        )
        mock_cmds.workspace.return_value = "/project"
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
                mod = load_skill_script("maya-render-farm", "write_render_job")
                result = mod.write_render_job(tmp)
            assert result["success"] is True
            assert os.path.isfile(result["context"]["job_file"])

    def test_frame_count_calculated(self):
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.file.return_value = "/path/scene.ma"
        mock_cmds.getAttr.side_effect = lambda attr: (
            1.0 if "startFrame" in attr
            else 100.0 if "endFrame" in attr
            else "vray"
        )
        mock_cmds.workspace.return_value = "/project"
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
                mod = load_skill_script("maya-render-farm", "write_render_job")
                result = mod.write_render_job(tmp, chunk_size=10)
        assert result["success"] is True
        assert result["context"]["frame_count"] == 100  # frames 1..100

    def test_no_maya(self):
        with patch.dict(sys.modules, {"maya": None, "maya.cmds": None}):
            mod = load_skill_script("maya-render-farm", "write_render_job")
            result = mod.write_render_job("/tmp/jobs")
        assert result["success"] is False


class TestSubmitToDeadline:
    """Tests for submit_to_deadline script."""

    def test_no_scene_saved(self):
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.file.return_value = ""
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = load_skill_script("maya-render-farm", "submit_to_deadline")
            result = mod.submit_to_deadline()
        assert result["success"] is False
        assert "save" in result["message"].lower() or "saved" in result["message"].lower()

    def test_deadline_not_found(self):
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.file.return_value = "/path/scene.ma"
        mock_cmds.getAttr.side_effect = lambda attr: (
            1.0 if "startFrame" in attr else 100.0 if "endFrame" in attr else "arnold"
        )
        mock_cmds.about.return_value = "2024"
        # Simulate no deadlinecommand on PATH
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="not found")
                mod = load_skill_script("maya-render-farm", "submit_to_deadline")
                result = mod.submit_to_deadline()
        assert result["success"] is False

    def test_no_maya(self):
        with patch.dict(sys.modules, {"maya": None, "maya.cmds": None}):
            mod = load_skill_script("maya-render-farm", "submit_to_deadline")
            result = mod.submit_to_deadline()
        assert result["success"] is False


class TestGetRenderJobStatus:
    """Tests for get_render_job_status script."""

    def test_job_status_success(self):
        with patch("subprocess.run") as mock_run:
            # First call: find deadlinecommand
            find_result = MagicMock(returncode=0, stdout="deadlinecommand\n")
            # Second call: get job details
            details_result = MagicMock(
                returncode=0,
                stdout="Status=Active\nCompletedChunks=5\nTaskCount=10\nFailedChunks=0\n",
            )
            mock_run.side_effect = [find_result, details_result]
            with patch.dict(sys.modules, {"maya": MagicMock(), "maya.cmds": MagicMock()}):
                mod = load_skill_script("maya-render-farm", "get_render_job_status")
                result = mod.get_render_job_status("abc-123")
        assert result["success"] is True
        assert result["context"]["status"] == "Active"

    def test_deadline_error(self):
        with patch("subprocess.run") as mock_run:
            find_result = MagicMock(returncode=0, stdout="deadlinecommand\n")
            err_result = MagicMock(returncode=1, stdout="", stderr="Job not found")
            mock_run.side_effect = [find_result, err_result]
            with patch.dict(sys.modules, {"maya": MagicMock(), "maya.cmds": MagicMock()}):
                mod = load_skill_script("maya-render-farm", "get_render_job_status")
                result = mod.get_render_job_status("bad-id")
        assert result["success"] is False

    def test_deadline_not_found(self):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="")
            with patch.dict(sys.modules, {"maya": MagicMock(), "maya.cmds": MagicMock()}):
                mod = load_skill_script("maya-render-farm", "get_render_job_status")
                result = mod.get_render_job_status("abc-123")
        assert result["success"] is False
