"""Round 18 tests: maya-hdri, maya-camera-sequence, maya-skinning-utils."""
from __future__ import annotations

import importlib.util
import os
import sys
from unittest.mock import MagicMock

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SKILLS_ROOT = os.path.join(
    os.path.dirname(__file__),
    "..",
    "src",
    "dcc_mcp_maya",
    "skills",
)


def load_script(skill_dir: str, script_name: str):
    """Dynamically load a skill script from a hyphenated skill directory."""
    path = os.path.join(SKILLS_ROOT, skill_dir, "scripts", script_name)
    spec = importlib.util.spec_from_file_location(script_name[:-3], path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def make_mock_cmds():
    mock_cmds = MagicMock()
    mock_maya = MagicMock()
    mock_maya.cmds = mock_cmds
    sys.modules["maya"] = mock_maya
    sys.modules["maya.cmds"] = mock_cmds
    sys.modules["maya.api"] = MagicMock()
    sys.modules["maya.utils"] = MagicMock()
    return mock_cmds


def cleanup_maya_mocks():
    for key in list(sys.modules.keys()):
        if key == "maya" or key.startswith("maya."):
            sys.modules.pop(key, None)


# ===========================================================================
# maya-hdri
# ===========================================================================

class TestCreateSkyDome:
    """Tests for maya-hdri/scripts/create_sky_dome.py."""

    def setup_method(self):
        self.mock_cmds = make_mock_cmds()
        self.mock_cmds.pluginInfo.return_value = True
        self.mock_cmds.shadingNode.return_value = ("aiSkyDomeLight1", "aiSkyDomeLightTransform1")

    def teardown_method(self):
        cleanup_maya_mocks()

    def test_basic_create(self):
        mod = load_script("maya-hdri", "create_sky_dome.py")
        result = mod.run({"name": "aiSkyDomeLight1", "exposure": 0.0, "intensity": 1.0})
        assert result.success is True
        assert "aiSkyDomeLightTransform1" in result.message or result.context.get("light_transform")

    def test_with_hdri_path(self):
        self.mock_cmds.shadingNode.side_effect = [
            ("aiSkyDomeLight1", "aiSkyDomeLightTransform1"),  # light
            "fileNode1",  # file texture
        ]
        mod = load_script("maya-hdri", "create_sky_dome.py")
        result = mod.run({"hdri_path": "/renders/studio.hdr"})
        assert result.success is True

    def test_plugin_not_loaded_triggers_load(self):
        self.mock_cmds.pluginInfo.return_value = False
        mod = load_script("maya-hdri", "create_sky_dome.py")
        result = mod.run({})
        assert result.success is True
        self.mock_cmds.loadPlugin.assert_called_once_with("mtoa")

    def test_sets_exposure_and_intensity(self):
        mod = load_script("maya-hdri", "create_sky_dome.py")
        result = mod.run({"exposure": 2.0, "intensity": 1.5})
        assert result.success is True

    def test_exception(self):
        self.mock_cmds.shadingNode.side_effect = RuntimeError("plugin error")
        mod = load_script("maya-hdri", "create_sky_dome.py")
        result = mod.run({})
        assert result.success is False
        assert "plugin error" in result.error


class TestSetHdriImage:
    """Tests for maya-hdri/scripts/set_hdri_image.py."""

    def setup_method(self):
        self.mock_cmds = make_mock_cmds()
        self.mock_cmds.objExists.return_value = True
        self.mock_cmds.listConnections.return_value = None
        self.mock_cmds.shadingNode.return_value = "fileNode1"

    def teardown_method(self):
        cleanup_maya_mocks()

    def test_basic_set(self):
        mod = load_script("maya-hdri", "set_hdri_image.py")
        result = mod.run({"light": "aiSkyDomeLight1", "hdri_path": "/hdri/studio.hdr"})
        assert result.success is True

    def test_reuses_existing_file_node(self):
        self.mock_cmds.listConnections.return_value = ["existingFileNode"]
        mod = load_script("maya-hdri", "set_hdri_image.py")
        result = mod.run({"light": "aiSkyDomeLight1", "hdri_path": "/new.hdr"})
        assert result.success is True
        # Should NOT create a new file node
        self.mock_cmds.shadingNode.assert_not_called()

    def test_missing_light_param(self):
        mod = load_script("maya-hdri", "set_hdri_image.py")
        result = mod.run({"hdri_path": "/hdri/studio.hdr"})
        assert result.success is False

    def test_missing_hdri_path_param(self):
        mod = load_script("maya-hdri", "set_hdri_image.py")
        result = mod.run({"light": "aiSkyDomeLight1"})
        assert result.success is False

    def test_light_not_exists(self):
        self.mock_cmds.objExists.return_value = False
        mod = load_script("maya-hdri", "set_hdri_image.py")
        result = mod.run({"light": "missing", "hdri_path": "/x.hdr"})
        assert result.success is False

    def test_exception(self):
        self.mock_cmds.shadingNode.side_effect = RuntimeError("crash")
        mod = load_script("maya-hdri", "set_hdri_image.py")
        result = mod.run({"light": "aiSkyDomeLight1", "hdri_path": "/x.hdr"})
        assert result.success is False


class TestListSkyDomes:
    """Tests for maya-hdri/scripts/list_sky_domes.py."""

    def setup_method(self):
        self.mock_cmds = make_mock_cmds()

    def teardown_method(self):
        cleanup_maya_mocks()

    def test_empty_scene(self):
        self.mock_cmds.ls.return_value = []
        mod = load_script("maya-hdri", "list_sky_domes.py")
        result = mod.run({})
        assert result.success is True
        assert result.context["count"] == 0

    def test_one_dome(self):
        self.mock_cmds.ls.return_value = ["aiSkyDomeLight1"]
        self.mock_cmds.listRelatives.return_value = ["aiSkyDomeLightTransform1"]
        self.mock_cmds.getAttr.side_effect = [0.0, 1.0, "/hdri/studio.hdr"]
        self.mock_cmds.listConnections.return_value = ["fileNode1"]
        mod = load_script("maya-hdri", "list_sky_domes.py")
        result = mod.run({})
        assert result.success is True
        assert result.context["count"] == 1

    def test_no_hdri_connected(self):
        self.mock_cmds.ls.return_value = ["aiSkyDomeLight1"]
        self.mock_cmds.listRelatives.return_value = ["aiSkyDomeLightTransform1"]
        self.mock_cmds.getAttr.side_effect = [0.0, 1.0]
        self.mock_cmds.listConnections.return_value = None
        mod = load_script("maya-hdri", "list_sky_domes.py")
        result = mod.run({})
        assert result.success is True
        assert result.context["sky_domes"][0]["hdri_path"] == ""

    def test_exception(self):
        self.mock_cmds.ls.side_effect = RuntimeError("ls failed")
        mod = load_script("maya-hdri", "list_sky_domes.py")
        result = mod.run({})
        assert result.success is False


class TestSetSkyDomeAttribute:
    """Tests for maya-hdri/scripts/set_sky_dome_attribute.py."""

    def setup_method(self):
        self.mock_cmds = make_mock_cmds()
        self.mock_cmds.objExists.return_value = True

    def teardown_method(self):
        cleanup_maya_mocks()

    def test_set_numeric(self):
        mod = load_script("maya-hdri", "set_sky_dome_attribute.py")
        result = mod.run({"light": "aiSkyDomeLight1", "attribute": "exposure", "value": 1.5})
        assert result.success is True

    def test_set_string(self):
        mod = load_script("maya-hdri", "set_sky_dome_attribute.py")
        result = mod.run({"light": "aiSkyDomeLight1", "attribute": "notes", "value": "studio"})
        assert result.success is True

    def test_missing_light(self):
        mod = load_script("maya-hdri", "set_sky_dome_attribute.py")
        result = mod.run({"attribute": "exposure", "value": 1.0})
        assert result.success is False

    def test_missing_attribute(self):
        mod = load_script("maya-hdri", "set_sky_dome_attribute.py")
        result = mod.run({"light": "aiSkyDomeLight1", "value": 1.0})
        assert result.success is False

    def test_light_not_found(self):
        self.mock_cmds.objExists.return_value = False
        mod = load_script("maya-hdri", "set_sky_dome_attribute.py")
        result = mod.run({"light": "missing", "attribute": "exposure", "value": 0.0})
        assert result.success is False

    def test_exception(self):
        self.mock_cmds.setAttr.side_effect = RuntimeError("bad attr")
        mod = load_script("maya-hdri", "set_sky_dome_attribute.py")
        result = mod.run({"light": "aiSkyDomeLight1", "attribute": "exposure", "value": 1.0})
        assert result.success is False


class TestDeleteSkyDome:
    """Tests for maya-hdri/scripts/delete_sky_dome.py."""

    def setup_method(self):
        self.mock_cmds = make_mock_cmds()
        self.mock_cmds.objExists.return_value = True
        self.mock_cmds.nodeType.return_value = "aiSkyDomeLight"
        self.mock_cmds.listRelatives.return_value = ["aiSkyDomeLightTransform1"]

    def teardown_method(self):
        cleanup_maya_mocks()

    def test_delete_by_shape(self):
        mod = load_script("maya-hdri", "delete_sky_dome.py")
        result = mod.run({"light": "aiSkyDomeLight1"})
        assert result.success is True

    def test_delete_by_transform(self):
        self.mock_cmds.nodeType.return_value = "transform"
        self.mock_cmds.listRelatives.return_value = ["aiSkyDomeLight1"]
        mod = load_script("maya-hdri", "delete_sky_dome.py")
        result = mod.run({"light": "aiSkyDomeLightTransform1"})
        assert result.success is True

    def test_delete_with_file_nodes(self):
        self.mock_cmds.listConnections.return_value = ["fileNode1"]
        mod = load_script("maya-hdri", "delete_sky_dome.py")
        result = mod.run({"light": "aiSkyDomeLight1", "delete_file_nodes": True})
        assert result.success is True
        assert "fileNode1" in result.context.get("deleted_file_nodes", [])

    def test_missing_param(self):
        mod = load_script("maya-hdri", "delete_sky_dome.py")
        result = mod.run({})
        assert result.success is False

    def test_light_not_found(self):
        self.mock_cmds.objExists.return_value = False
        mod = load_script("maya-hdri", "delete_sky_dome.py")
        result = mod.run({"light": "ghost"})
        assert result.success is False

    def test_wrong_node_type(self):
        self.mock_cmds.nodeType.return_value = "mesh"
        mod = load_script("maya-hdri", "delete_sky_dome.py")
        result = mod.run({"light": "pSphere1"})
        assert result.success is False

    def test_exception(self):
        self.mock_cmds.delete.side_effect = RuntimeError("delete failed")
        mod = load_script("maya-hdri", "delete_sky_dome.py")
        result = mod.run({"light": "aiSkyDomeLight1"})
        assert result.success is False


# ===========================================================================
# maya-camera-sequence
# ===========================================================================

class TestCreateShot:
    """Tests for maya-camera-sequence/scripts/create_shot.py."""

    def setup_method(self):
        self.mock_cmds = make_mock_cmds()
        self.mock_cmds.objExists.return_value = True
        self.mock_cmds.shot.return_value = "shot1"

    def teardown_method(self):
        cleanup_maya_mocks()

    def test_basic_create(self):
        mod = load_script("maya-camera-sequence", "create_shot.py")
        result = mod.run({"name": "shot1", "camera": "persp", "start_frame": 1, "end_frame": 24})
        assert result.success is True
        assert result.context.get("shot") == "shot1"

    def test_default_params(self):
        mod = load_script("maya-camera-sequence", "create_shot.py")
        result = mod.run({})
        assert result.success is True

    def test_camera_not_found(self):
        self.mock_cmds.objExists.return_value = False
        mod = load_script("maya-camera-sequence", "create_shot.py")
        result = mod.run({"camera": "nonexistent_camera"})
        assert result.success is False

    def test_custom_sequence_start(self):
        mod = load_script("maya-camera-sequence", "create_shot.py")
        result = mod.run({"start_frame": 10, "end_frame": 50, "sequence_start": 100})
        assert result.success is True
        assert result.context.get("sequence_start") == 100.0

    def test_exception(self):
        self.mock_cmds.shot.side_effect = RuntimeError("sequencer error")
        mod = load_script("maya-camera-sequence", "create_shot.py")
        result = mod.run({"camera": "persp"})
        assert result.success is False


class TestListShots:
    """Tests for maya-camera-sequence/scripts/list_shots.py."""

    def setup_method(self):
        self.mock_cmds = make_mock_cmds()

    def teardown_method(self):
        cleanup_maya_mocks()

    def test_empty(self):
        self.mock_cmds.ls.return_value = []
        mod = load_script("maya-camera-sequence", "list_shots.py")
        result = mod.run({})
        assert result.success is True
        assert result.context["count"] == 0

    def test_one_shot(self):
        self.mock_cmds.ls.return_value = ["shot1"]
        self.mock_cmds.shot.side_effect = [
            "persp",  # camera
            1.0,      # startTime
            24.0,     # endTime
            1.0,      # sequenceStartTime
            24.0,     # sequenceEndTime
        ]
        mod = load_script("maya-camera-sequence", "list_shots.py")
        result = mod.run({})
        assert result.success is True
        assert result.context["count"] == 1
        assert result.context["shots"][0]["camera"] == "persp"

    def test_sorted_by_sequence_start(self):
        self.mock_cmds.ls.return_value = ["shot2", "shot1"]
        # shot2: seq_start=50; shot1: seq_start=1
        self.mock_cmds.shot.side_effect = [
            "persp", 50.0, 74.0, 50.0, 74.0,  # shot2
            "cam1",  1.0,  25.0,  1.0, 25.0,  # shot1
        ]
        mod = load_script("maya-camera-sequence", "list_shots.py")
        result = mod.run({})
        assert result.success is True
        # Should be sorted: shot1(seq_start=1) before shot2(seq_start=50)
        assert result.context["shots"][0]["sequence_start"] == 1.0

    def test_exception(self):
        self.mock_cmds.ls.side_effect = RuntimeError("ls failed")
        mod = load_script("maya-camera-sequence", "list_shots.py")
        result = mod.run({})
        assert result.success is False


class TestSetShotCamera:
    """Tests for maya-camera-sequence/scripts/set_shot_camera.py."""

    def setup_method(self):
        self.mock_cmds = make_mock_cmds()
        self.mock_cmds.objExists.return_value = True
        self.mock_cmds.nodeType.return_value = "shot"

    def teardown_method(self):
        cleanup_maya_mocks()

    def test_success(self):
        mod = load_script("maya-camera-sequence", "set_shot_camera.py")
        result = mod.run({"shot": "shot1", "camera": "cam1"})
        assert result.success is True

    def test_missing_shot(self):
        mod = load_script("maya-camera-sequence", "set_shot_camera.py")
        result = mod.run({"camera": "cam1"})
        assert result.success is False

    def test_missing_camera(self):
        mod = load_script("maya-camera-sequence", "set_shot_camera.py")
        result = mod.run({"shot": "shot1"})
        assert result.success is False

    def test_shot_not_found(self):
        self.mock_cmds.objExists.side_effect = [False, True]
        mod = load_script("maya-camera-sequence", "set_shot_camera.py")
        result = mod.run({"shot": "ghost", "camera": "cam1"})
        assert result.success is False

    def test_wrong_node_type(self):
        self.mock_cmds.nodeType.return_value = "transform"
        mod = load_script("maya-camera-sequence", "set_shot_camera.py")
        result = mod.run({"shot": "pSphere1", "camera": "cam1"})
        assert result.success is False

    def test_camera_not_found(self):
        self.mock_cmds.objExists.side_effect = [True, False]
        mod = load_script("maya-camera-sequence", "set_shot_camera.py")
        result = mod.run({"shot": "shot1", "camera": "missing_cam"})
        assert result.success is False


class TestDeleteShot:
    """Tests for maya-camera-sequence/scripts/delete_shot.py."""

    def setup_method(self):
        self.mock_cmds = make_mock_cmds()
        self.mock_cmds.objExists.return_value = True
        self.mock_cmds.nodeType.return_value = "shot"

    def teardown_method(self):
        cleanup_maya_mocks()

    def test_success(self):
        mod = load_script("maya-camera-sequence", "delete_shot.py")
        result = mod.run({"shot": "shot1"})
        assert result.success is True
        assert result.context.get("deleted") == "shot1"

    def test_missing_param(self):
        mod = load_script("maya-camera-sequence", "delete_shot.py")
        result = mod.run({})
        assert result.success is False

    def test_not_found(self):
        self.mock_cmds.objExists.return_value = False
        mod = load_script("maya-camera-sequence", "delete_shot.py")
        result = mod.run({"shot": "ghost"})
        assert result.success is False

    def test_wrong_type(self):
        self.mock_cmds.nodeType.return_value = "mesh"
        mod = load_script("maya-camera-sequence", "delete_shot.py")
        result = mod.run({"shot": "pSphere1"})
        assert result.success is False

    def test_exception(self):
        self.mock_cmds.delete.side_effect = RuntimeError("delete error")
        mod = load_script("maya-camera-sequence", "delete_shot.py")
        result = mod.run({"shot": "shot1"})
        assert result.success is False


class TestSetShotRange:
    """Tests for maya-camera-sequence/scripts/set_shot_range.py."""

    def setup_method(self):
        self.mock_cmds = make_mock_cmds()
        self.mock_cmds.objExists.return_value = True
        self.mock_cmds.nodeType.return_value = "shot"
        # shot() with edit=True returns None; with query=True returns numeric value
        def shot_side_effect(*args, **kwargs):
            if kwargs.get("edit"):
                return None
            if kwargs.get("query"):
                if "startTime" in kwargs:
                    return 1.0
                if "endTime" in kwargs:
                    return 50.0
                if "sequenceStartTime" in kwargs:
                    return 1.0
            return None
        self.mock_cmds.shot.side_effect = shot_side_effect

    def teardown_method(self):
        cleanup_maya_mocks()

    def test_set_all(self):
        mod = load_script("maya-camera-sequence", "set_shot_range.py")
        result = mod.run({"shot": "shot1", "start_frame": 1, "end_frame": 50, "sequence_start": 1})
        assert result.success is True

    def test_missing_shot(self):
        mod = load_script("maya-camera-sequence", "set_shot_range.py")
        result = mod.run({"start_frame": 1, "end_frame": 50})
        assert result.success is False

    def test_shot_not_found(self):
        self.mock_cmds.objExists.return_value = False
        mod = load_script("maya-camera-sequence", "set_shot_range.py")
        result = mod.run({"shot": "ghost"})
        assert result.success is False

    def test_wrong_node_type(self):
        self.mock_cmds.nodeType.return_value = "transform"
        mod = load_script("maya-camera-sequence", "set_shot_range.py")
        result = mod.run({"shot": "pSphere1", "start_frame": 1})
        assert result.success is False

    def test_partial_update(self):
        """Only updating end_frame should work."""
        mod = load_script("maya-camera-sequence", "set_shot_range.py")
        result = mod.run({"shot": "shot1", "end_frame": 100})
        assert result.success is True

    def test_exception(self):
        self.mock_cmds.shot.side_effect = RuntimeError("shot error")
        mod = load_script("maya-camera-sequence", "set_shot_range.py")
        result = mod.run({"shot": "shot1", "end_frame": 50})
        assert result.success is False


# ===========================================================================
# maya-skinning-utils
# ===========================================================================

class TestCopySkinWeights:
    """Tests for maya-skinning-utils/scripts/copy_skin_weights.py."""

    def setup_method(self):
        self.mock_cmds = make_mock_cmds()
        self.mock_cmds.objExists.return_value = True

    def teardown_method(self):
        cleanup_maya_mocks()

    def test_basic_copy(self):
        mod = load_script("maya-skinning-utils", "copy_skin_weights.py")
        result = mod.run({"source": "pSphere1", "destination": "pSphere2"})
        assert result.success is True

    def test_missing_source(self):
        mod = load_script("maya-skinning-utils", "copy_skin_weights.py")
        result = mod.run({"destination": "pSphere2"})
        assert result.success is False

    def test_missing_destination(self):
        mod = load_script("maya-skinning-utils", "copy_skin_weights.py")
        result = mod.run({"source": "pSphere1"})
        assert result.success is False

    def test_source_not_found(self):
        self.mock_cmds.objExists.side_effect = [False, True]
        mod = load_script("maya-skinning-utils", "copy_skin_weights.py")
        result = mod.run({"source": "ghost", "destination": "pSphere2"})
        assert result.success is False

    def test_dest_not_found(self):
        self.mock_cmds.objExists.side_effect = [True, False]
        mod = load_script("maya-skinning-utils", "copy_skin_weights.py")
        result = mod.run({"source": "pSphere1", "destination": "ghost"})
        assert result.success is False

    def test_custom_association(self):
        mod = load_script("maya-skinning-utils", "copy_skin_weights.py")
        result = mod.run({
            "source": "pSphere1",
            "destination": "pSphere2",
            "surface_association": "rayCast",
            "influence_association": "oneToOne",
        })
        assert result.success is True

    def test_exception(self):
        self.mock_cmds.copySkinWeights.side_effect = RuntimeError("copy failed")
        mod = load_script("maya-skinning-utils", "copy_skin_weights.py")
        result = mod.run({"source": "pSphere1", "destination": "pSphere2"})
        assert result.success is False


class TestNormalizeSkinWeights:
    """Tests for maya-skinning-utils/scripts/normalize_skin_weights.py."""

    def setup_method(self):
        self.mock_cmds = make_mock_cmds()
        self.mock_cmds.objExists.return_value = True
        self.mock_cmds.nodeType.return_value = "mesh"
        self.mock_cmds.ls.return_value = ["skinCluster1"]
        self.mock_cmds.listHistory.return_value = ["skinCluster1", "tweak1"]

    def teardown_method(self):
        cleanup_maya_mocks()

    def test_basic(self):
        mod = load_script("maya-skinning-utils", "normalize_skin_weights.py")
        result = mod.run({"mesh": "pSphere1"})
        assert result.success is True

    def test_missing_mesh(self):
        mod = load_script("maya-skinning-utils", "normalize_skin_weights.py")
        result = mod.run({})
        assert result.success is False

    def test_invalid_mode(self):
        mod = load_script("maya-skinning-utils", "normalize_skin_weights.py")
        result = mod.run({"mesh": "pSphere1", "normalize_mode": "bad_mode"})
        assert result.success is False

    def test_mesh_not_found(self):
        self.mock_cmds.objExists.return_value = False
        mod = load_script("maya-skinning-utils", "normalize_skin_weights.py")
        result = mod.run({"mesh": "ghost"})
        assert result.success is False

    def test_no_skin_cluster(self):
        self.mock_cmds.ls.return_value = []
        mod = load_script("maya-skinning-utils", "normalize_skin_weights.py")
        result = mod.run({"mesh": "pSphere1"})
        assert result.success is False

    def test_direct_skin_cluster_node(self):
        self.mock_cmds.nodeType.return_value = "skinCluster"
        mod = load_script("maya-skinning-utils", "normalize_skin_weights.py")
        result = mod.run({"mesh": "skinCluster1"})
        assert result.success is True


class TestPruneSkinWeights:
    """Tests for maya-skinning-utils/scripts/prune_skin_weights.py."""

    def setup_method(self):
        self.mock_cmds = make_mock_cmds()
        self.mock_cmds.objExists.return_value = True
        self.mock_cmds.nodeType.return_value = "mesh"
        self.mock_cmds.ls.return_value = ["skinCluster1"]
        self.mock_cmds.listHistory.return_value = ["skinCluster1"]

    def teardown_method(self):
        cleanup_maya_mocks()

    def test_basic(self):
        mod = load_script("maya-skinning-utils", "prune_skin_weights.py")
        result = mod.run({"mesh": "pSphere1", "threshold": 0.001})
        assert result.success is True

    def test_default_threshold(self):
        mod = load_script("maya-skinning-utils", "prune_skin_weights.py")
        result = mod.run({"mesh": "pSphere1"})
        assert result.success is True
        assert result.context.get("threshold") == 0.001

    def test_missing_mesh(self):
        mod = load_script("maya-skinning-utils", "prune_skin_weights.py")
        result = mod.run({})
        assert result.success is False

    def test_invalid_threshold_too_high(self):
        mod = load_script("maya-skinning-utils", "prune_skin_weights.py")
        result = mod.run({"mesh": "pSphere1", "threshold": 1.5})
        assert result.success is False

    def test_no_skin_cluster(self):
        self.mock_cmds.ls.return_value = []
        mod = load_script("maya-skinning-utils", "prune_skin_weights.py")
        result = mod.run({"mesh": "pSphere1"})
        assert result.success is False

    def test_exception(self):
        self.mock_cmds.skinPercent.side_effect = RuntimeError("prune error")
        mod = load_script("maya-skinning-utils", "prune_skin_weights.py")
        result = mod.run({"mesh": "pSphere1"})
        assert result.success is False


class TestMirrorSkinWeights:
    """Tests for maya-skinning-utils/scripts/mirror_skin_weights.py."""

    def setup_method(self):
        self.mock_cmds = make_mock_cmds()
        self.mock_cmds.objExists.return_value = True

    def teardown_method(self):
        cleanup_maya_mocks()

    def test_basic_yz(self):
        mod = load_script("maya-skinning-utils", "mirror_skin_weights.py")
        result = mod.run({"mesh": "pSphere1"})
        assert result.success is True

    def test_xz_mode(self):
        mod = load_script("maya-skinning-utils", "mirror_skin_weights.py")
        result = mod.run({"mesh": "pSphere1", "mirror_mode": "XZ"})
        assert result.success is True

    def test_mirror_inverse(self):
        mod = load_script("maya-skinning-utils", "mirror_skin_weights.py")
        result = mod.run({"mesh": "pSphere1", "mirror_inverse": True})
        assert result.success is True

    def test_missing_mesh(self):
        mod = load_script("maya-skinning-utils", "mirror_skin_weights.py")
        result = mod.run({})
        assert result.success is False

    def test_invalid_mode(self):
        mod = load_script("maya-skinning-utils", "mirror_skin_weights.py")
        result = mod.run({"mesh": "pSphere1", "mirror_mode": "invalid"})
        assert result.success is False

    def test_mesh_not_found(self):
        self.mock_cmds.objExists.return_value = False
        mod = load_script("maya-skinning-utils", "mirror_skin_weights.py")
        result = mod.run({"mesh": "ghost"})
        assert result.success is False

    def test_exception(self):
        self.mock_cmds.copySkinWeights.side_effect = RuntimeError("mirror error")
        mod = load_script("maya-skinning-utils", "mirror_skin_weights.py")
        result = mod.run({"mesh": "pSphere1"})
        assert result.success is False


class TestGetSkinInfo:
    """Tests for maya-skinning-utils/scripts/get_skin_info.py."""

    def setup_method(self):
        self.mock_cmds = make_mock_cmds()
        self.mock_cmds.objExists.return_value = True
        self.mock_cmds.listHistory.return_value = ["skinCluster1", "tweak1"]
        self.mock_cmds.ls.return_value = ["skinCluster1"]
        self.mock_cmds.nodeType.return_value = "mesh"
        self.mock_cmds.skinCluster.side_effect = [
            ["joint1", "joint2"],  # influence query
            4,                     # maxInfluences query
        ]
        self.mock_cmds.getAttr.return_value = 1  # normalizeWeights
        self.mock_cmds.polyEvaluate.return_value = 100

    def teardown_method(self):
        cleanup_maya_mocks()

    def test_basic(self):
        mod = load_script("maya-skinning-utils", "get_skin_info.py")
        result = mod.run({"mesh": "pSphere1"})
        assert result.success is True
        assert result.context.get("influence_count") == 2
        assert result.context.get("vertex_count") == 100

    def test_missing_mesh(self):
        mod = load_script("maya-skinning-utils", "get_skin_info.py")
        result = mod.run({})
        assert result.success is False

    def test_mesh_not_found(self):
        self.mock_cmds.objExists.return_value = False
        mod = load_script("maya-skinning-utils", "get_skin_info.py")
        result = mod.run({"mesh": "ghost"})
        assert result.success is False

    def test_no_skin_cluster(self):
        self.mock_cmds.ls.return_value = []
        mod = load_script("maya-skinning-utils", "get_skin_info.py")
        result = mod.run({"mesh": "pSphere1"})
        assert result.success is False

    def test_normalize_mode_post(self):
        self.mock_cmds.getAttr.return_value = 2
        mod = load_script("maya-skinning-utils", "get_skin_info.py")
        result = mod.run({"mesh": "pSphere1"})
        assert result.success is True
        assert result.context.get("normalize_mode") == "post"

    def test_exception(self):
        self.mock_cmds.listHistory.side_effect = RuntimeError("history error")
        mod = load_script("maya-skinning-utils", "get_skin_info.py")
        result = mod.run({"mesh": "pSphere1"})
        assert result.success is False
