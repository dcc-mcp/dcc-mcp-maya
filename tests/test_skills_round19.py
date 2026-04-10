"""Round 19: Tests for maya-paint-effects, maya-hdri, maya-camera-sequence,
maya-namespaces, and maya-texture-bake skills.
"""

# Import future modules
from __future__ import annotations

# Import built-in modules
import os
import sys
import tempfile
from unittest.mock import MagicMock, patch

# Import third-party modules
import pytest

from tests.conftest import load_skill_script, make_mock_maya


# ---------------------------------------------------------------------------
# maya-paint-effects
# ---------------------------------------------------------------------------


class TestCreateStroke:
    """Tests for maya-paint-effects create_stroke."""

    def _load(self):
        return load_skill_script("maya-paint-effects", "create_stroke")

    def test_create_stroke_success(self):
        mod = self._load()
        mock_maya, mock_cmds = make_mock_maya()
        mock_mel = MagicMock()
        mock_cmds.curve.return_value = "curve1"
        mock_cmds.ls.return_value = ["pfxToon1"]
        mock_cmds.listRelatives.return_value = ["pfxToonShape1"]
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds, "maya.mel": mock_mel}):
            result = mod.create_stroke(preset="flowers/daisy.mel")
        assert result["success"] is True
        assert "stroke" in result["message"].lower() or result.get("data") is not None

    def test_create_stroke_with_points(self):
        mod = self._load()
        mock_maya, mock_cmds = make_mock_maya()
        mock_mel = MagicMock()
        mock_cmds.curve.return_value = "curve2"
        mock_cmds.ls.return_value = []
        mock_cmds.listRelatives.return_value = []
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds, "maya.mel": mock_mel}):
            result = mod.create_stroke(
                preset="grasses/grass.mel",
                start_point=[0.0, 0.0, 0.0],
                end_point=[5.0, 0.0, 5.0],
                name="myStroke",
            )
        assert result["success"] is True

    def test_create_stroke_no_maya(self):
        mod = self._load()
        # Temporarily remove maya from sys.modules so the import inside the function fails
        saved = {k: sys.modules.pop(k) for k in list(sys.modules.keys()) if k == "maya" or k.startswith("maya.")}
        try:
            result = mod.create_stroke()
        except Exception:
            result = {"success": False}
        finally:
            sys.modules.update(saved)
        assert result["success"] is False

    def test_create_stroke_main_callable(self):
        mod = self._load()
        mock_maya, mock_cmds = make_mock_maya()
        mock_mel = MagicMock()
        mock_cmds.curve.return_value = "curve3"
        mock_cmds.ls.return_value = []
        mock_cmds.listRelatives.return_value = []
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds, "maya.mel": mock_mel}):
            result = mod.main()
        assert isinstance(result, dict)


class TestAttachStrokeToSurface:
    """Tests for maya-paint-effects attach_stroke_to_surface."""

    def _load(self):
        return load_skill_script("maya-paint-effects", "attach_stroke_to_surface")

    def test_surface_not_found(self):
        mod = self._load()
        mock_maya, mock_cmds = make_mock_maya()
        mock_mel = MagicMock()
        mock_cmds.objExists.return_value = False
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds, "maya.mel": mock_mel}):
            result = mod.attach_stroke_to_surface("nonexistent", preset="grasses/grass.mel")
        assert result["success"] is False
        assert "not found" in result["message"].lower()

    def test_attach_success(self):
        mod = self._load()
        mock_maya, mock_cmds = make_mock_maya()
        mock_mel = MagicMock()
        mock_cmds.objExists.return_value = True
        mock_cmds.ls.side_effect = [[], ["stroke1", "stroke2"]]
        mock_cmds.listRelatives.return_value = ["strokeTransform1"]
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds, "maya.mel": mock_mel}):
            result = mod.attach_stroke_to_surface("pSphere1", stroke_count=2)
        assert result["success"] is True

    def test_attach_with_name(self):
        mod = self._load()
        mock_maya, mock_cmds = make_mock_maya()
        mock_mel = MagicMock()
        mock_cmds.objExists.return_value = True
        mock_cmds.ls.side_effect = [[], ["stroke1"]]
        mock_cmds.listRelatives.return_value = ["strokeTransform1"]
        mock_cmds.rename.return_value = "myStroke_0"
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds, "maya.mel": mock_mel}):
            result = mod.attach_stroke_to_surface("pSphere1", stroke_count=1, name="myStroke")
        assert result["success"] is True

    def test_main_callable(self):
        mod = self._load()
        mock_maya, mock_cmds = make_mock_maya()
        mock_mel = MagicMock()
        mock_cmds.objExists.return_value = False
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds, "maya.mel": mock_mel}):
            result = mod.main(surface="mySurface")
        assert isinstance(result, dict)


class TestListStrokes:
    """Tests for maya-paint-effects list_strokes."""

    def _load(self):
        return load_skill_script("maya-paint-effects", "list_strokes")

    def test_list_empty(self):
        mod = self._load()
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.ls.return_value = []
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            result = mod.list_strokes()
        assert result["success"] is True
        assert result["context"]["count"] == 0

    def test_list_with_strokes(self):
        mod = self._load()
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.ls.return_value = ["stroke1", "stroke2"]
        mock_cmds.listRelatives.return_value = ["strokeTransform1"]
        mock_cmds.getAttr.return_value = True
        mock_cmds.listConnections.return_value = ["brushNode1"]
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            result = mod.list_strokes()
        assert result["success"] is True
        assert result["context"]["count"] == 2

    def test_main_callable(self):
        mod = self._load()
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.ls.return_value = []
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            result = mod.main()
        assert isinstance(result, dict)


class TestDeleteStroke:
    """Tests for maya-paint-effects delete_stroke."""

    def _load(self):
        return load_skill_script("maya-paint-effects", "delete_stroke")

    def test_delete_specific_stroke(self):
        mod = self._load()
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.ls.return_value = ["stroke1"]
        mock_cmds.listRelatives.return_value = ["strokeTransform1"]
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            result = mod.delete_stroke(stroke="stroke1")
        assert result["success"] is True
        assert result["context"]["count"] >= 1

    def test_delete_all(self):
        mod = self._load()
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.ls.return_value = ["s1", "s2", "s3"]
        mock_cmds.listRelatives.return_value = ["t1"]
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            result = mod.delete_stroke(delete_all=True)
        assert result["success"] is True
        assert result["context"]["count"] == 3

    def test_delete_no_args(self):
        mod = self._load()
        mock_maya, mock_cmds = make_mock_maya()
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            result = mod.delete_stroke()
        assert result["success"] is False

    def test_delete_nonexistent(self):
        mod = self._load()
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.objExists.return_value = False
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            result = mod.delete_stroke(stroke="ghost")
        assert result["success"] is False


# ---------------------------------------------------------------------------
# maya-hdri
# ---------------------------------------------------------------------------


class TestLoadHdri:
    """Tests for maya-hdri load_hdri."""

    def _load(self):
        return load_skill_script("maya-hdri", "load_hdri")

    def test_file_not_found(self):
        mod = self._load()
        mock_maya, mock_cmds = make_mock_maya()
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            with patch("os.path.isfile", return_value=False):
                result = mod.load_hdri("/nonexistent.hdr")
        assert result["success"] is False
        assert "not found" in result["message"].lower()

    def test_load_with_arnold(self):
        mod = self._load()
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.loadPlugin.return_value = None
        mock_cmds.shadingNode.side_effect = ["hdriDome1", "hdriDome1_tex"]
        mock_cmds.attributeQuery.return_value = True
        mock_cmds.directionalLight.return_value = "domeLight1"
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            with patch("os.path.isfile", return_value=True):
                result = mod.load_hdri("/some/env.hdr", use_arnold=True)
        assert result["success"] is True

    def test_load_native_fallback(self):
        mod = self._load()
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.loadPlugin.side_effect = Exception("no mtoa")
        mock_cmds.shadingNode.side_effect = ["hdriDome1_tex"]
        mock_cmds.directionalLight.return_value = "nativeDome1"
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            with patch("os.path.isfile", return_value=True):
                result = mod.load_hdri("/some/env.hdr", use_arnold=False)
        assert result["success"] is True

    def test_main_callable(self):
        mod = self._load()
        mock_maya, mock_cmds = make_mock_maya()
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            with patch("os.path.isfile", return_value=False):
                result = mod.main(file_path="/fake.hdr")
        assert isinstance(result, dict)


class TestSetHdriExposure:
    """Tests for maya-hdri set_hdri_exposure."""

    def _load(self):
        return load_skill_script("maya-hdri", "set_hdri_exposure")

    def test_node_not_found(self):
        mod = self._load()
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.objExists.return_value = False
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            result = mod.set_hdri_exposure("ghost", 1.0)
        assert result["success"] is False

    def test_arnold_exposure(self):
        mod = self._load()
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.listRelatives.return_value = ["aiSkyDomeLightShape"]
        mock_cmds.objectType.return_value = "aiSkyDomeLight"
        mock_cmds.attributeQuery.return_value = True
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            result = mod.set_hdri_exposure("hdriDome1", 2.0)
        assert result["success"] is True
        assert result["context"]["exposure"] == 2.0

    def test_native_intensity_fallback(self):
        mod = self._load()
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.listRelatives.return_value = ["directionalLightShape"]
        mock_cmds.objectType.return_value = "directionalLight"
        mock_cmds.attributeQuery.side_effect = lambda attr, **kw: attr == "intensity"
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            result = mod.set_hdri_exposure("nativeDome1", -1.0)
        assert result["success"] is True

    def test_main_callable(self):
        mod = self._load()
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.objExists.return_value = False
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            result = mod.main(light_node="x", exposure=0.0)
        assert isinstance(result, dict)


class TestSetHdriRotation:
    """Tests for maya-hdri set_hdri_rotation."""

    def _load(self):
        return load_skill_script("maya-hdri", "set_hdri_rotation")

    def test_node_not_found(self):
        mod = self._load()
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.objExists.return_value = False
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            result = mod.set_hdri_rotation("ghost", 90.0)
        assert result["success"] is False

    def test_rotation_on_transform(self):
        mod = self._load()
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.objectType.return_value = "transform"
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            result = mod.set_hdri_rotation("hdriDome1", 180.0)
        assert result["success"] is True
        assert result["context"]["rotation_y"] == 180.0

    def test_rotation_on_shape_node(self):
        mod = self._load()
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.objectType.return_value = "aiSkyDomeLight"
        mock_cmds.listRelatives.return_value = ["hdriDome1"]
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            result = mod.set_hdri_rotation("aiSkyDomeLightShape", 45.0)
        assert result["success"] is True

    def test_main_callable(self):
        mod = self._load()
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.objExists.return_value = False
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            result = mod.main(light_node="x", rotation_y=0.0)
        assert isinstance(result, dict)


class TestListHdriNodes:
    """Tests for maya-hdri list_hdri_nodes."""

    def _load(self):
        return load_skill_script("maya-hdri", "list_hdri_nodes")

    def test_empty_scene(self):
        mod = self._load()
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.ls.return_value = []
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            result = mod.list_hdri_nodes()
        assert result["success"] is True
        assert result["context"]["count"] == 0

    def test_with_dome_light(self):
        mod = self._load()
        mock_maya, mock_cmds = make_mock_maya()

        def ls_side(type=None, **kw):
            if type == "aiSkyDomeLight":
                return ["aiSkyDomeLightShape1"]
            return []

        mock_cmds.ls.side_effect = ls_side
        mock_cmds.attributeQuery.return_value = True
        mock_cmds.getAttr.return_value = 1.0
        mock_cmds.listRelatives.return_value = ["hdriDome1"]
        mock_cmds.listConnections.return_value = ["fileTex1"]
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            result = mod.list_hdri_nodes()
        assert result["success"] is True
        assert result["context"]["count"] >= 1

    def test_main_callable(self):
        mod = self._load()
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.ls.return_value = []
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            result = mod.main()
        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# maya-camera-sequence
# ---------------------------------------------------------------------------


class TestCreateShot:
    """Tests for maya-camera-sequence create_shot."""

    def _load(self):
        return load_skill_script("maya-camera-sequence", "create_shot")

    def test_camera_not_found(self):
        mod = self._load()
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.objExists.return_value = False
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            result = mod.create_shot("nonexistent_cam", 1, 24)
        assert result["success"] is False
        assert "not found" in result["message"].lower()

    def test_create_shot_success(self):
        mod = self._load()
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.shot.return_value = "shot1"
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            result = mod.create_shot("camera1", start_frame=1, end_frame=48)
        assert result["success"] is True
        assert result["context"]["shot_node"] == "shot1"

    def test_create_named_shot(self):
        mod = self._load()
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.shot.return_value = "myShot"
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            result = mod.create_shot("camera2", start_frame=50, end_frame=100, name="myShot")
        assert result["success"] is True

    def test_create_shot_with_seq_start(self):
        mod = self._load()
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.shot.return_value = "shot2"
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            result = mod.create_shot("camera1", start_frame=1, end_frame=24, sequence_start_frame=100)
        assert result["success"] is True
        assert result["context"]["sequence_start_frame"] == 100

    def test_main_callable(self):
        mod = self._load()
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.objExists.return_value = False
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            result = mod.main(camera="cam1")
        assert isinstance(result, dict)


class TestListShots:
    """Tests for maya-camera-sequence list_shots."""

    def _load(self):
        return load_skill_script("maya-camera-sequence", "list_shots")

    def test_no_shots(self):
        mod = self._load()
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.ls.return_value = []
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            result = mod.list_shots()
        assert result["success"] is True
        assert result["context"]["count"] == 0

    def test_with_shots(self):
        mod = self._load()
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.ls.return_value = ["shot1", "shot2"]
        mock_cmds.shot.side_effect = lambda sn, **kw: (
            "camera1" if kw.get("currentCamera") else
            1.0 if kw.get("startTime") else
            24.0 if kw.get("endTime") else
            1.0 if kw.get("sequenceStartTime") else
            24.0
        )
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            result = mod.list_shots()
        assert result["success"] is True
        assert result["context"]["count"] == 2

    def test_main_callable(self):
        mod = self._load()
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.ls.return_value = []
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            result = mod.main()
        assert isinstance(result, dict)


class TestSetShotRange:
    """Tests for maya-camera-sequence set_shot_range."""

    def _load(self):
        return load_skill_script("maya-camera-sequence", "set_shot_range")

    def test_shot_not_found(self):
        mod = self._load()
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.objExists.return_value = False
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            result = mod.set_shot_range("ghost")
        assert result["success"] is False

    def test_update_start_and_end(self):
        mod = self._load()
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.shot.side_effect = lambda sn, **kw: (
            1.0 if kw.get("startTime") else
            24.0 if kw.get("endTime") else
            1.0 if kw.get("sequenceStartTime") else
            None
        )
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            result = mod.set_shot_range("shot1", start_frame=10, end_frame=60)
        assert result["success"] is True
        assert result["context"]["start_frame"] == 10
        assert result["context"]["end_frame"] == 60

    def test_update_only_end(self):
        mod = self._load()
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.shot.side_effect = lambda sn, **kw: (
            5.0 if kw.get("startTime") else
            30.0 if kw.get("endTime") else
            5.0
        )
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            result = mod.set_shot_range("shot1", end_frame=100)
        assert result["success"] is True

    def test_main_callable(self):
        mod = self._load()
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.objExists.return_value = False
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            result = mod.main(shot_node="x")
        assert isinstance(result, dict)


class TestDeleteShot:
    """Tests for maya-camera-sequence delete_shot."""

    def _load(self):
        return load_skill_script("maya-camera-sequence", "delete_shot")

    def test_delete_success(self):
        mod = self._load()
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.objExists.return_value = True
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            result = mod.delete_shot("shot1")
        assert result["success"] is True
        assert result["context"]["shot_node"] == "shot1"

    def test_delete_not_found(self):
        mod = self._load()
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.objExists.return_value = False
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            result = mod.delete_shot("ghost")
        assert result["success"] is False

    def test_main_callable(self):
        mod = self._load()
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.objExists.return_value = False
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            result = mod.main(shot_node="x")
        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# maya-namespaces
# ---------------------------------------------------------------------------


class TestCreateNamespace:
    """Tests for maya-namespaces create_namespace."""

    def _load(self):
        return load_skill_script("maya-namespaces", "create_namespace")

    def test_empty_name(self):
        mod = self._load()
        mock_maya, mock_cmds = make_mock_maya()
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            result = mod.create_namespace("")
        assert result["success"] is False

    def test_already_exists(self):
        mod = self._load()
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.namespaceInfo.return_value = ":"
        mock_cmds.namespace.side_effect = lambda *a, **kw: True if kw.get("exists") else None
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            result = mod.create_namespace("char_hero")
        assert result["success"] is False
        assert "already exists" in result["message"].lower()

    def test_create_success(self):
        mod = self._load()
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.namespaceInfo.return_value = ":"

        exists_call_count = [0]

        def ns_side(*args, **kwargs):
            if kwargs.get("exists"):
                exists_call_count[0] += 1
                return exists_call_count[0] > 1  # first call False, subsequent True
            return None

        mock_cmds.namespace.side_effect = ns_side
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            result = mod.create_namespace("char_hero")
        assert result["success"] is True
        assert "char_hero" in result["context"]["full_path"]

    def test_main_callable(self):
        mod = self._load()
        mock_maya, mock_cmds = make_mock_maya()
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            result = mod.main(name="")
        assert isinstance(result, dict)


class TestListNamespaces:
    """Tests for maya-namespaces list_namespaces."""

    def _load(self):
        return load_skill_script("maya-namespaces", "list_namespaces")

    def test_empty_scene(self):
        mod = self._load()
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.namespaceInfo.return_value = []
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            result = mod.list_namespaces()
        assert result["success"] is True
        assert result["context"]["count"] == 0

    def test_filters_defaults(self):
        mod = self._load()
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.namespaceInfo.return_value = ["UI", "shared", "char_hero"]
        mock_cmds.ls.return_value = ["char_hero:ctrl1"]
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            result = mod.list_namespaces(include_defaults=False)
        assert result["success"] is True
        names = [n["name"] for n in result["context"]["namespaces"]]
        assert "UI" not in names
        assert "shared" not in names
        assert "char_hero" in names

    def test_include_defaults(self):
        mod = self._load()
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.namespaceInfo.return_value = ["UI", "shared"]
        mock_cmds.ls.return_value = []
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            result = mod.list_namespaces(include_defaults=True)
        assert result["success"] is True
        assert result["context"]["count"] == 2

    def test_main_callable(self):
        mod = self._load()
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.namespaceInfo.return_value = []
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            result = mod.main()
        assert isinstance(result, dict)


class TestRenameNamespace:
    """Tests for maya-namespaces rename_namespace."""

    def _load(self):
        return load_skill_script("maya-namespaces", "rename_namespace")

    def test_old_not_found(self):
        mod = self._load()
        mock_maya, mock_cmds = make_mock_maya()

        def ns_side(*a, **kw):
            if kw.get("exists"):
                return False
            return None

        mock_cmds.namespace.side_effect = ns_side
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            result = mod.rename_namespace("old_ns", "new_ns")
        assert result["success"] is False

    def test_new_already_exists(self):
        mod = self._load()
        mock_maya, mock_cmds = make_mock_maya()
        call_n = [0]

        def ns_side(*a, **kw):
            if kw.get("exists"):
                call_n[0] += 1
                return True  # both old and new exist
            return None

        mock_cmds.namespace.side_effect = ns_side
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            result = mod.rename_namespace("old_ns", "new_ns")
        assert result["success"] is False

    def test_rename_success(self):
        mod = self._load()
        mock_maya, mock_cmds = make_mock_maya()
        call_n = [0]

        def ns_side(*a, **kw):
            if kw.get("exists"):
                call_n[0] += 1
                return call_n[0] == 1  # first call (old) True, second (new) False
            return None

        mock_cmds.namespace.side_effect = ns_side
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            result = mod.rename_namespace("old_ns", "new_ns")
        assert result["success"] is True

    def test_main_callable(self):
        mod = self._load()
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.namespace.side_effect = lambda *a, **kw: False if kw.get("exists") else None
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            result = mod.main(old_name="x", new_name="y")
        assert isinstance(result, dict)


class TestRemoveNamespace:
    """Tests for maya-namespaces remove_namespace."""

    def _load(self):
        return load_skill_script("maya-namespaces", "remove_namespace")

    def test_not_found(self):
        mod = self._load()
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.namespace.side_effect = lambda *a, **kw: False if kw.get("exists") else None
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            result = mod.remove_namespace("ghost")
        assert result["success"] is False

    def test_not_empty_no_force(self):
        mod = self._load()
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.namespace.side_effect = lambda *a, **kw: True if kw.get("exists") else None
        mock_cmds.ls.return_value = ["char_hero:ctrl1", "char_hero:ctrl2"]
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            result = mod.remove_namespace("char_hero", force=False)
        assert result["success"] is False
        assert "not empty" in result["message"].lower()

    def test_remove_with_force(self):
        mod = self._load()
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.namespace.side_effect = lambda *a, **kw: True if kw.get("exists") else None
        mock_cmds.ls.return_value = ["char_hero:ctrl1"]
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            result = mod.remove_namespace("char_hero", force=True)
        assert result["success"] is True
        assert result["context"]["merged_objects"] == 1

    def test_remove_empty_namespace(self):
        mod = self._load()
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.namespace.side_effect = lambda *a, **kw: True if kw.get("exists") else None
        mock_cmds.ls.return_value = []
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            result = mod.remove_namespace("empty_ns")
        assert result["success"] is True
        assert result["context"]["merged_objects"] == 0

    def test_main_callable(self):
        mod = self._load()
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.namespace.side_effect = lambda *a, **kw: False if kw.get("exists") else None
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            result = mod.main(name="x")
        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# maya-texture-bake
# ---------------------------------------------------------------------------


class TestBakeLighting:
    """Tests for maya-texture-bake bake_lighting."""

    def _load(self):
        return load_skill_script("maya-texture-bake", "bake_lighting")

    def test_no_objects(self):
        mod = self._load()
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.ls.return_value = []
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            result = mod.bake_lighting()
        assert result["success"] is False
        assert "no objects" in result["message"].lower()

    def test_bake_success(self):
        mod = self._load()
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.objExists.return_value = True
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            with patch("os.path.isdir", return_value=True):
                result = mod.bake_lighting(objects=["pSphere1"], output_dir="/tmp")
        assert result["success"] is True
        assert len(result["context"]["baked_files"]) == 1

    def test_skip_nonexistent_objects(self):
        mod = self._load()
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.objExists.return_value = False
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            with patch("os.path.isdir", return_value=True):
                result = mod.bake_lighting(objects=["ghost1", "ghost2"], output_dir="/tmp")
        assert result["success"] is True
        assert result["context"]["baked_files"] == []

    def test_main_callable(self):
        mod = self._load()
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.ls.return_value = []
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            result = mod.main()
        assert isinstance(result, dict)


class TestBakeAmbientOcclusion:
    """Tests for maya-texture-bake bake_ambient_occlusion."""

    def _load(self):
        return load_skill_script("maya-texture-bake", "bake_ambient_occlusion")

    def test_no_objects(self):
        mod = self._load()
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.ls.return_value = []
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            result = mod.bake_ambient_occlusion()
        assert result["success"] is False

    def test_bake_ao_success(self):
        mod = self._load()
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.shadingNode.side_effect = ["_tmp_ao_shader", "_tmp_ao_sg"]
        mock_cmds.sets.return_value = "_tmp_ao_sg"
        mock_cmds.listHistory.return_value = ["pSphereShape1"]
        mock_cmds.listConnections.return_value = ["initialShadingGroup"]
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            with patch("os.path.isdir", return_value=True):
                result = mod.bake_ambient_occlusion(objects=["pSphere1"], output_dir="/tmp")
        assert result["success"] is True

    def test_main_callable(self):
        mod = self._load()
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.ls.return_value = []
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            result = mod.main()
        assert isinstance(result, dict)


class TestTransferMaps:
    """Tests for maya-texture-bake transfer_maps."""

    def _load(self):
        return load_skill_script("maya-texture-bake", "transfer_maps")

    def test_source_not_found(self):
        mod = self._load()
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.objExists.side_effect = [False, True]
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            result = mod.transfer_maps("ghost", "lowRes")
        assert result["success"] is False

    def test_invalid_map_type(self):
        mod = self._load()
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.objExists.return_value = True
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            with patch("os.path.isdir", return_value=True):
                result = mod.transfer_maps("high", "low", map_types=["fakeMap"])
        assert result["success"] is False
        assert "invalid map types" in result["message"].lower()

    def test_transfer_normals(self):
        mod = self._load()
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.objExists.return_value = True
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            with patch("os.path.isdir", return_value=True):
                result = mod.transfer_maps("highMesh", "lowMesh", map_types=["normals"])
        assert result["success"] is True
        assert len(result["context"]["baked_files"]) == 1

    def test_transfer_multiple_maps(self):
        mod = self._load()
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.objExists.return_value = True
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            with patch("os.path.isdir", return_value=True):
                result = mod.transfer_maps(
                    "highMesh", "lowMesh",
                    map_types=["normals", "diffuse", "ambientOcclusion"],
                )
        assert result["success"] is True
        assert len(result["context"]["baked_files"]) == 3

    def test_main_callable(self):
        mod = self._load()
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.objExists.return_value = False
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            result = mod.main(source="x", target="y")
        assert isinstance(result, dict)


class TestListBakeSets:
    """Tests for maya-texture-bake list_bake_sets."""

    def _load(self):
        return load_skill_script("maya-texture-bake", "list_bake_sets")

    def test_no_bake_sets(self):
        mod = self._load()
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.ls.return_value = ["defaultObjectSet"]
        mock_cmds.attributeQuery.return_value = False
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            result = mod.list_bake_sets()
        assert result["success"] is True
        assert result["context"]["count"] == 0

    def test_with_bake_sets(self):
        mod = self._load()
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.ls.return_value = ["bakeSet1"]
        mock_cmds.attributeQuery.return_value = True
        mock_cmds.getAttr.side_effect = lambda attr: (
            1024 if "resolution" in attr.lower() else
            "png" if "format" in attr.lower() else
            None
        )
        mock_cmds.sets.return_value = ["pSphere1"]
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            result = mod.list_bake_sets()
        assert result["success"] is True
        assert result["context"]["count"] == 1

    def test_main_callable(self):
        mod = self._load()
        mock_maya, mock_cmds = make_mock_maya()
        mock_cmds.ls.return_value = []
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            result = mod.main()
        assert isinstance(result, dict)
