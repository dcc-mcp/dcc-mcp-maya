"""Round 15: Unit tests for maya-annotation, maya-audio, maya-cache,
maya-color-grading and maya-constraints-advanced Skill domains.

All tests use importlib.util to load scripts from hyphenated directories and
mock maya.cmds / maya.mel APIs."""

# Import built-in modules
import importlib.util
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

SKILLS_ROOT = Path(__file__).parent.parent / "src" / "dcc_mcp_maya" / "skills"


def _load_script(skill_dir: str, script_name: str):
    """Load a skill script module by path."""
    script_path = SKILLS_ROOT / skill_dir / "scripts" / "{}.py".format(script_name)
    spec = importlib.util.spec_from_file_location(
        "{}.{}".format(skill_dir.replace("-", "_"), script_name),
        script_path,
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _make_mock_maya(cmds_attrs=None):
    """Return (mock_maya, mock_cmds) with the .cmds linkage wired correctly."""
    mock_cmds = MagicMock()
    mock_maya = MagicMock()
    mock_maya.cmds = mock_cmds
    if cmds_attrs:
        for k, v in cmds_attrs.items():
            setattr(mock_cmds, k, v)
    return mock_maya, mock_cmds


# ---------------------------------------------------------------------------
# maya-annotation
# ---------------------------------------------------------------------------


class TestCreateAnnotation:
    """Tests for maya-annotation/scripts/create_annotation.py."""

    def test_create_annotation_at_position(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.annotate.return_value = "annotationShape1"
        mock_cmds.listRelatives.return_value = ["annotation1"]
        mock_cmds.objectType.return_value = "annotationShape"

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-annotation", "create_annotation")
            result = mod.create_annotation("Test note", position=[1.0, 2.0, 3.0])

        assert result["success"] is True
        assert result["context"]["annotation_node"] == "annotationShape1"
        assert result["context"]["transform_node"] == "annotation1"

    def test_create_annotation_with_target(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.annotate.return_value = "annotationShape1"
        mock_cmds.listRelatives.return_value = ["annotation1"]

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-annotation", "create_annotation")
            result = mod.create_annotation("Attached note", target_object="pSphere1")

        assert result["success"] is True
        call_kwargs = mock_cmds.annotate.call_args
        assert "pSphere1" in str(call_kwargs)

    def test_create_annotation_target_not_found(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.objExists.return_value = False

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-annotation", "create_annotation")
            result = mod.create_annotation("Note", target_object="missing_obj")

        assert result["success"] is False
        assert "missing_obj" in result["message"]

    def test_create_annotation_with_name(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.annotate.return_value = "annotationShape1"
        mock_cmds.listRelatives.return_value = ["annotation1"]
        mock_cmds.rename.return_value = "myAnnotation"

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-annotation", "create_annotation")
            result = mod.create_annotation("Note", name="myAnnotation")

        assert result["success"] is True
        mock_cmds.rename.assert_called_once()

    def test_create_annotation_maya_not_available(self):
        with patch.dict(sys.modules, {"maya": None, "maya.cmds": None}):
            mod = _load_script("maya-annotation", "create_annotation")
            with patch.dict(sys.modules, {"maya.cmds": None}):
                result = mod.create_annotation("note")
        # ImportError path — just assert it returns a dict
        assert isinstance(result, dict)

    def test_create_annotation_exception(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.annotate.side_effect = RuntimeError("annotate failed")

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-annotation", "create_annotation")
            result = mod.create_annotation("Note")

        assert result["success"] is False
        assert "annotate failed" in result["error"]


class TestListAnnotations:
    """Tests for maya-annotation/scripts/list_annotations.py."""

    def test_list_annotations_empty(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.ls.return_value = []

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-annotation", "list_annotations")
            result = mod.list_annotations()

        assert result["success"] is True
        assert result["context"]["count"] == 0
        assert result["context"]["annotations"] == []

    def test_list_annotations_with_nodes(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.ls.return_value = ["annotationShape1", "annotationShape2"]
        mock_cmds.getAttr.side_effect = ["Hello", "World"]
        mock_cmds.listRelatives.side_effect = [["annotation1"], ["annotation2"]]

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-annotation", "list_annotations")
            result = mod.list_annotations()

        assert result["success"] is True
        assert result["context"]["count"] == 2
        texts = [a["text"] for a in result["context"]["annotations"]]
        assert "Hello" in texts
        assert "World" in texts

    def test_list_annotations_exception(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.ls.side_effect = RuntimeError("scene locked")
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-annotation", "list_annotations")
            result = mod.list_annotations()

        assert result["success"] is False


class TestUpdateAnnotation:
    """Tests for maya-annotation/scripts/update_annotation.py."""

    def test_update_text(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.objectType.return_value = "annotationShape"
        mock_cmds.listRelatives.return_value = ["annotation1"]
        mock_cmds.getAttr.return_value = "New text"

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-annotation", "update_annotation")
            result = mod.update_annotation("annotationShape1", text="New text")

        assert result["success"] is True
        assert result["context"]["text"] == "New text"
        mock_cmds.setAttr.assert_called_once()

    def test_update_position(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.objectType.return_value = "annotationShape"
        mock_cmds.listRelatives.return_value = ["annotation1"]
        mock_cmds.getAttr.return_value = "Existing text"

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-annotation", "update_annotation")
            result = mod.update_annotation("annotationShape1", position=[5.0, 0.0, 5.0])

        assert result["success"] is True
        mock_cmds.move.assert_called_once()

    def test_update_annotation_not_found(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.objExists.return_value = False

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-annotation", "update_annotation")
            result = mod.update_annotation("missing")

        assert result["success"] is False

    def test_update_annotation_via_transform(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.objectType.return_value = "transform"
        shapes_call = MagicMock(return_value=["annotationShape1"])
        mock_cmds.listRelatives.side_effect = [shapes_call(), ["annotation1"]]
        mock_cmds.getAttr.return_value = "text"

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-annotation", "update_annotation")
            result = mod.update_annotation("annotation1", text="text")
        assert result["success"] is True


class TestDeleteAnnotation:
    """Tests for maya-annotation/scripts/delete_annotation.py."""

    def test_delete_annotation_shape(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.objectType.return_value = "annotationShape"
        mock_cmds.listRelatives.return_value = ["annotation1"]

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-annotation", "delete_annotation")
            result = mod.delete_annotation("annotationShape1")

        assert result["success"] is True
        mock_cmds.delete.assert_called_once_with("annotation1")

    def test_delete_annotation_transform(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.objectType.return_value = "transform"

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-annotation", "delete_annotation")
            result = mod.delete_annotation("annotation1")

        assert result["success"] is True
        mock_cmds.delete.assert_called_once_with("annotation1")

    def test_delete_annotation_not_found(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.objExists.return_value = False

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-annotation", "delete_annotation")
            result = mod.delete_annotation("missing")

        assert result["success"] is False


# ---------------------------------------------------------------------------
# maya-audio
# ---------------------------------------------------------------------------


class TestImportAudio:
    """Tests for maya-audio/scripts/import_audio.py."""

    def test_import_audio_success(self, tmp_path):
        audio_file = tmp_path / "test.wav"
        audio_file.write_bytes(b"RIFF")

        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.sound.return_value = "sound1"

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-audio", "import_audio")
            result = mod.import_audio(str(audio_file))

        assert result["success"] is True
        assert result["context"]["sound_node"] == "sound1"

    def test_import_audio_file_not_found(self):
        mock_maya, mock_cmds = _make_mock_maya()

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-audio", "import_audio")
            result = mod.import_audio("/nonexistent/audio.wav")

        assert result["success"] is False
        assert "not found" in result["message"]

    def test_import_audio_with_name_and_offset(self, tmp_path):
        audio_file = tmp_path / "music.wav"
        audio_file.write_bytes(b"RIFF")

        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.sound.return_value = "mySound"

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-audio", "import_audio")
            result = mod.import_audio(str(audio_file), name="mySound", offset=10.0)

        assert result["success"] is True
        assert result["context"]["offset"] == 10.0

    def test_import_audio_exception(self, tmp_path):
        audio_file = tmp_path / "bad.wav"
        audio_file.write_bytes(b"RIFF")

        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.sound.side_effect = RuntimeError("sound import error")

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-audio", "import_audio")
            result = mod.import_audio(str(audio_file))

        assert result["success"] is False


class TestListAudio:
    """Tests for maya-audio/scripts/list_audio.py."""

    def test_list_audio_empty(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.ls.return_value = []

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-audio", "list_audio")
            result = mod.list_audio()

        assert result["success"] is True
        assert result["context"]["count"] == 0

    def test_list_audio_with_nodes(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.ls.return_value = ["sound1", "sound2"]
        mock_cmds.getAttr.side_effect = ["/audio/a.wav", 0.0, "/audio/b.wav", 5.0]
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-audio", "list_audio")
            result = mod.list_audio()

        assert result["success"] is True
        assert result["context"]["count"] == 2
        nodes = [n["node"] for n in result["context"]["sound_nodes"]]
        assert "sound1" in nodes

    def test_list_audio_exception(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.ls.side_effect = RuntimeError("scene error")
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-audio", "list_audio")
            result = mod.list_audio()

        assert result["success"] is False


class TestSetTimelineAudio:
    """Tests for maya-audio/scripts/set_timeline_audio.py."""

    def test_set_timeline_audio_success(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.objectType.return_value = "audio"
        mock_mel = MagicMock()
        mock_mel.eval.return_value = "timeControl1"

        with patch.dict(
            sys.modules,
            {"maya": mock_maya, "maya.cmds": mock_cmds, "maya.mel": mock_mel},
        ):
            mod = _load_script("maya-audio", "set_timeline_audio")
            result = mod.set_timeline_audio("sound1")

        assert result["success"] is True
        assert result["context"]["sound_node"] == "sound1"

    def test_set_timeline_audio_not_found(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.objExists.return_value = False

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-audio", "set_timeline_audio")
            result = mod.set_timeline_audio("missing_sound")

        assert result["success"] is False

    def test_set_timeline_audio_wrong_type(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.objectType.return_value = "transform"
        mock_mel = MagicMock()

        with patch.dict(
            sys.modules,
            {"maya": mock_maya, "maya.cmds": mock_cmds, "maya.mel": mock_mel},
        ):
            mod = _load_script("maya-audio", "set_timeline_audio")
            result = mod.set_timeline_audio("pSphere1")

        assert result["success"] is False
        assert "Not a sound node" in result["message"]


class TestRemoveAudio:
    """Tests for maya-audio/scripts/remove_audio.py."""

    def test_remove_audio_success(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.objectType.return_value = "audio"

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-audio", "remove_audio")
            result = mod.remove_audio("sound1")

        assert result["success"] is True
        mock_cmds.delete.assert_called_once_with("sound1")

    def test_remove_audio_not_found(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.objExists.return_value = False

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-audio", "remove_audio")
            result = mod.remove_audio("missing")

        assert result["success"] is False

    def test_remove_audio_wrong_type(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.objectType.return_value = "mesh"

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-audio", "remove_audio")
            result = mod.remove_audio("pSphere1")

        assert result["success"] is False


# ---------------------------------------------------------------------------
# maya-cache
# ---------------------------------------------------------------------------


class TestCreateGeometryCache:
    """Tests for maya-cache/scripts/create_geometry_cache.py."""

    def test_create_cache_success(self, tmp_path):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.playbackOptions.side_effect = [1.0, 50.0]
        mock_cmds.ls.return_value = ["cacheFile1"]
        mock_mel = MagicMock()

        with patch.dict(
            sys.modules,
            {"maya": mock_maya, "maya.cmds": mock_cmds, "maya.mel": mock_mel},
        ):
            mod = _load_script("maya-cache", "create_geometry_cache")
            result = mod.create_geometry_cache(["pSphere1"], str(tmp_path), cache_name="test_cache")

        assert result["success"] is True
        assert result["context"]["cache_name"] == "test_cache"
        assert result["context"]["start_frame"] == 1
        assert result["context"]["end_frame"] == 50

    def test_create_cache_object_not_found(self, tmp_path):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.objExists.return_value = False
        mock_mel = MagicMock()

        with patch.dict(
            sys.modules,
            {"maya": mock_maya, "maya.cmds": mock_cmds, "maya.mel": mock_mel},
        ):
            mod = _load_script("maya-cache", "create_geometry_cache")
            result = mod.create_geometry_cache(["missing_obj"], str(tmp_path))

        assert result["success"] is False
        assert "missing_obj" in result["message"]

    def test_create_cache_custom_frame_range(self, tmp_path):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.ls.return_value = []
        mock_mel = MagicMock()

        with patch.dict(
            sys.modules,
            {"maya": mock_maya, "maya.cmds": mock_cmds, "maya.mel": mock_mel},
        ):
            mod = _load_script("maya-cache", "create_geometry_cache")
            result = mod.create_geometry_cache(
                ["pSphere1"],
                str(tmp_path),
                start_frame=10.0,
                end_frame=25.0,
            )

        assert result["success"] is True
        assert result["context"]["start_frame"] == 10
        assert result["context"]["end_frame"] == 25


class TestAttachGeometryCache:
    """Tests for maya-cache/scripts/attach_geometry_cache.py."""

    def test_attach_cache_success(self, tmp_path):
        xml_file = tmp_path / "sphere.xml"
        xml_file.write_text("<cache/>")

        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.ls.return_value = ["cacheFile1"]
        mock_mel = MagicMock()

        with patch.dict(
            sys.modules,
            {"maya": mock_maya, "maya.cmds": mock_cmds, "maya.mel": mock_mel},
        ):
            mod = _load_script("maya-cache", "attach_geometry_cache")
            result = mod.attach_geometry_cache("pSphere1", str(xml_file))

        assert result["success"] is True
        assert result["context"]["mesh"] == "pSphere1"

    def test_attach_cache_mesh_not_found(self, tmp_path):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.objExists.return_value = False

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-cache", "attach_geometry_cache")
            result = mod.attach_geometry_cache("missing", "/tmp/cache.xml")

        assert result["success"] is False

    def test_attach_cache_file_not_found(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_mel = MagicMock()

        with patch.dict(
            sys.modules,
            {"maya": mock_maya, "maya.cmds": mock_cmds, "maya.mel": mock_mel},
        ):
            mod = _load_script("maya-cache", "attach_geometry_cache")
            result = mod.attach_geometry_cache("pSphere1", "/nonexistent/cache.xml")

        assert result["success"] is False
        assert "not found" in result["message"]


class TestListGeometryCaches:
    """Tests for maya-cache/scripts/list_geometry_caches.py."""

    def test_list_caches_all(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.ls.return_value = ["cacheFile1", "cacheFile2"]
        mock_cmds.getAttr.side_effect = [
            "/cache/",
            "sphere_cache",
            1,
            50,
            "/cache/",
            "cube_cache",
            1,
            25,
        ]
        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-cache", "list_geometry_caches")
            result = mod.list_geometry_caches()

        assert result["success"] is True
        assert result["context"]["count"] == 2

    def test_list_caches_empty(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.ls.return_value = []

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-cache", "list_geometry_caches")
            result = mod.list_geometry_caches()
        assert result["success"] is True
        assert result["context"]["count"] == 0

    def test_list_caches_mesh_not_found(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.objExists.return_value = False

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-cache", "list_geometry_caches")
            result = mod.list_geometry_caches(mesh="missing")

        assert result["success"] is False


class TestDeleteGeometryCache:
    """Tests for maya-cache/scripts/delete_geometry_cache.py."""

    def test_delete_cache_success(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.objExists.return_value = True

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-cache", "delete_geometry_cache")
            result = mod.delete_geometry_cache("cacheFile1")

        assert result["success"] is True
        mock_cmds.delete.assert_called_once_with("cacheFile1")

    def test_delete_cache_not_found(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.objExists.return_value = False

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-cache", "delete_geometry_cache")
            result = mod.delete_geometry_cache("missing")

        assert result["success"] is False

    def test_delete_cache_with_files(self, tmp_path):
        xml_file = tmp_path / "sphere_cache.xml"
        mcx_file = tmp_path / "sphere_cache.mcx"
        xml_file.write_text("<cache/>")
        mcx_file.write_bytes(b"\x00\x01")

        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.getAttr.side_effect = [str(tmp_path) + "/", "sphere_cache"]

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-cache", "delete_geometry_cache")
            result = mod.delete_geometry_cache("cacheFile1", delete_files=True)

        assert result["success"] is True
        assert len(result["context"]["files_deleted"]) >= 1


# ---------------------------------------------------------------------------
# maya-color-grading
# ---------------------------------------------------------------------------


class TestGetColorManagementInfo:
    """Tests for maya-color-grading/scripts/get_color_management_info.py."""

    def test_get_color_info_enabled(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.colorManagementPrefs.side_effect = [True, "ACEScg", "ACES 1.0 SDR-video", "sRGB", "/ocio/config.ocio"]

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-color-grading", "get_color_management_info")
            result = mod.get_color_management_info()

        assert result["success"] is True
        assert result["context"]["enabled"] is True
        assert result["context"]["rendering_space"] == "ACEScg"
        assert result["context"]["view_transform"] == "ACES 1.0 SDR-video"

    def test_get_color_info_disabled(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.colorManagementPrefs.side_effect = [False, "", "", "", ""]

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-color-grading", "get_color_management_info")
            result = mod.get_color_management_info()

        assert result["success"] is True
        assert result["context"]["enabled"] is False
        assert "disabled" in result["message"]

    def test_get_color_info_exception(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.colorManagementPrefs.side_effect = RuntimeError("scene locked")

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-color-grading", "get_color_management_info")
            result = mod.get_color_management_info()

        assert result["success"] is False


class TestSetRenderingSpace:
    """Tests for maya-color-grading/scripts/set_rendering_space.py."""

    def test_set_rendering_space_success(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.colorManagementPrefs.side_effect = [True, None, "ACEScg"]

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-color-grading", "set_rendering_space")
            result = mod.set_rendering_space("ACEScg")

        assert result["success"] is True
        assert result["context"]["rendering_space"] == "ACEScg"

    def test_set_rendering_space_enables_cm(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.colorManagementPrefs.side_effect = [False, None, None, "sRGB linear"]

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-color-grading", "set_rendering_space")
            result = mod.set_rendering_space("sRGB linear")

        assert result["success"] is True
        # Should have called edit to enable CM
        assert mock_cmds.colorManagementPrefs.call_count >= 3

    def test_set_rendering_space_exception(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.colorManagementPrefs.side_effect = RuntimeError("locked")

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-color-grading", "set_rendering_space")
            result = mod.set_rendering_space("ACEScg")

        assert result["success"] is False


class TestSetViewTransform:
    """Tests for maya-color-grading/scripts/set_view_transform.py."""

    def test_set_view_transform_success(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.colorManagementPrefs.side_effect = [True, None, "sRGB gamma"]

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-color-grading", "set_view_transform")
            result = mod.set_view_transform("sRGB gamma")

        assert result["success"] is True
        assert result["context"]["view_transform"] == "sRGB gamma"

    def test_set_view_transform_exception(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.colorManagementPrefs.side_effect = RuntimeError("error")

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-color-grading", "set_view_transform")
            result = mod.set_view_transform("ACES 1.0 SDR-video")

        assert result["success"] is False


class TestApplyGammaCorrection:
    """Tests for maya-color-grading/scripts/apply_gamma_correction.py."""

    def test_apply_gamma_success(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.objectType.return_value = "file"
        mock_cmds.createNode.return_value = "gammaCorrect1"

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-color-grading", "apply_gamma_correction")
            result = mod.apply_gamma_correction("file1")

        assert result["success"] is True
        assert result["context"]["gamma_node"] == "gammaCorrect1"
        assert result["context"]["gamma"] == 2.2

    def test_apply_gamma_texture_not_found(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.objExists.return_value = False

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-color-grading", "apply_gamma_correction")
            result = mod.apply_gamma_correction("missing_file")

        assert result["success"] is False

    def test_apply_gamma_wrong_node_type(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.objectType.return_value = "transform"

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-color-grading", "apply_gamma_correction")
            result = mod.apply_gamma_correction("pSphere1")

        assert result["success"] is False
        assert "file" in result["message"].lower()

    def test_apply_gamma_custom_value(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.objectType.return_value = "file"
        mock_cmds.createNode.return_value = "gammaCorrect1"

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-color-grading", "apply_gamma_correction")
            result = mod.apply_gamma_correction("file1", gamma=0.4545)

        assert result["success"] is True
        assert abs(result["context"]["gamma"] - 0.4545) < 1e-4

    def test_apply_gamma_with_name(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.objectType.return_value = "file"
        mock_cmds.createNode.return_value = "myGamma"

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-color-grading", "apply_gamma_correction")
            result = mod.apply_gamma_correction("file1", name="myGamma")

        assert result["success"] is True
        assert result["context"]["gamma_node"] == "myGamma"


# ---------------------------------------------------------------------------
# maya-constraints-advanced
# ---------------------------------------------------------------------------


class TestAddPoleVectorConstraint:
    """Tests for maya-constraints-advanced/scripts/add_pole_vector_constraint.py."""

    def test_add_pole_vector_success(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.objectType.return_value = "ikHandle"
        mock_cmds.poleVectorConstraint.return_value = ["poleVectorConstraint1"]

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-constraints-advanced", "add_pole_vector_constraint")
            result = mod.add_pole_vector_constraint("poleLocator1", "ikHandle1")

        assert result["success"] is True
        assert result["context"]["constraint_node"] == "poleVectorConstraint1"

    def test_add_pole_vector_pole_not_found(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.objExists.side_effect = [False, True]

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-constraints-advanced", "add_pole_vector_constraint")
            result = mod.add_pole_vector_constraint("missing_pole", "ikHandle1")

        assert result["success"] is False

    def test_add_pole_vector_not_ik_handle(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.objectType.return_value = "transform"

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-constraints-advanced", "add_pole_vector_constraint")
            result = mod.add_pole_vector_constraint("poleLocator1", "pSphere1")

        assert result["success"] is False
        assert "IK" in result["message"] or "ikHandle" in result["message"]

    def test_add_pole_vector_exception(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.objectType.return_value = "ikHandle"
        mock_cmds.poleVectorConstraint.side_effect = RuntimeError("constraint error")

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-constraints-advanced", "add_pole_vector_constraint")
            result = mod.add_pole_vector_constraint("poleLocator1", "ikHandle1")

        assert result["success"] is False


class TestBakeConstraint:
    """Tests for maya-constraints-advanced/scripts/bake_constraint.py."""

    def test_bake_success(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.playbackOptions.side_effect = [1.0, 50.0]
        mock_cmds.listRelatives.return_value = []
        mock_cmds.listConnections.return_value = []

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-constraints-advanced", "bake_constraint")
            result = mod.bake_constraint(["pSphere1"])

        assert result["success"] is True
        assert result["context"]["frame_range"] == [1, 50]
        mock_cmds.bakeResults.assert_called_once()

    def test_bake_custom_range(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.listRelatives.return_value = []
        mock_cmds.listConnections.return_value = []

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-constraints-advanced", "bake_constraint")
            result = mod.bake_constraint(["pSphere1"], start_frame=5.0, end_frame=30.0)

        assert result["success"] is True
        assert result["context"]["frame_range"] == [5, 30]

    def test_bake_object_not_found(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.objExists.return_value = False

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-constraints-advanced", "bake_constraint")
            result = mod.bake_constraint(["missing_obj"])

        assert result["success"] is False

    def test_bake_removes_constraints(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.playbackOptions.side_effect = [1.0, 24.0]
        mock_cmds.listRelatives.return_value = ["parentConstraint1"]
        mock_cmds.listConnections.return_value = []

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-constraints-advanced", "bake_constraint")
            result = mod.bake_constraint(["pSphere1"], remove_constraints=True)

        assert result["success"] is True
        assert result["context"]["constraints_removed"] is True

    def test_bake_keeps_constraints(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.playbackOptions.side_effect = [1.0, 24.0]

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-constraints-advanced", "bake_constraint")
            result = mod.bake_constraint(["pSphere1"], remove_constraints=False)

        assert result["success"] is True
        assert result["context"]["constraints_removed"] is False


class TestGetConstraintWeights:
    """Tests for maya-constraints-advanced/scripts/get_constraint_weights.py."""

    def test_get_weights_success(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.objectType.return_value = "parentConstraint"
        mock_cmds.listAttr.return_value = ["pSphere1W0"]
        mock_cmds.listConnections.return_value = ["pSphere1"]
        mock_cmds.getAttr.return_value = 1.0

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-constraints-advanced", "get_constraint_weights")
            result = mod.get_constraint_weights("parentConstraint1")

        assert result["success"] is True
        assert result["context"]["constraint_type"] == "parentConstraint"
        assert len(result["context"]["weights"]) == 1

    def test_get_weights_no_drivers(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.objectType.return_value = "parentConstraint"
        mock_cmds.listAttr.return_value = []
        mock_cmds.listConnections.return_value = []

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-constraints-advanced", "get_constraint_weights")
            result = mod.get_constraint_weights("parentConstraint1")

        assert result["success"] is True
        assert result["context"]["weights"] == []

    def test_get_weights_not_found(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.objExists.return_value = False

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-constraints-advanced", "get_constraint_weights")
            result = mod.get_constraint_weights("missing")

        assert result["success"] is False


class TestSetConstraintWeight:
    """Tests for maya-constraints-advanced/scripts/set_constraint_weight.py."""

    def test_set_weight_success(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.listAttr.return_value = ["pSphere1W0", "pCubeW1"]

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-constraints-advanced", "set_constraint_weight")
            result = mod.set_constraint_weight("parentConstraint1", driver_index=0, weight=0.5)

        assert result["success"] is True
        assert result["context"]["weight"] == 0.5
        assert result["context"]["driver_index"] == 0
        mock_cmds.setAttr.assert_called_once()

    def test_set_weight_index_out_of_range(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.listAttr.return_value = ["pSphere1W0"]

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-constraints-advanced", "set_constraint_weight")
            result = mod.set_constraint_weight("parentConstraint1", driver_index=5, weight=1.0)

        assert result["success"] is False
        assert "No weight attribute" in result["message"]

    def test_set_weight_constraint_not_found(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.objExists.return_value = False

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-constraints-advanced", "set_constraint_weight")
            result = mod.set_constraint_weight("missing", driver_index=0, weight=1.0)

        assert result["success"] is False

    def test_set_weight_exception(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.listAttr.return_value = ["pSphere1W0"]
        mock_cmds.setAttr.side_effect = RuntimeError("read-only attr")

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-constraints-advanced", "set_constraint_weight")
            result = mod.set_constraint_weight("parentConstraint1", driver_index=0, weight=0.0)
        assert result["success"] is False
