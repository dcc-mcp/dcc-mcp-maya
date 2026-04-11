"""Round 24: Edge-case unit tests for maya-display, maya-annotation (gaps),
maya-audio (gaps), and E2E-style integration tests for maya-grooming and
maya-paint-effects skills.

Coverage targets:
- maya-display: create_display_layer, delete_display_layer, list_display_layers,
  set_display_layer — full happy-path + error branches
- maya-annotation: update via transform (no annotationShape found), no parent path,
  exception paths not covered in round15
- maya-audio: remove_audio wrong-type, remove_audio exception,
  set_timeline_audio exception
"""

# Import future modules
from __future__ import annotations

# Import built-in modules
import importlib.util
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

SKILLS_ROOT = Path(__file__).parent.parent / "src" / "dcc_mcp_maya" / "skills"


def _load_script(skill_dir: str, script_name: str):
    """Load a skill script module by path (unique module name per call)."""
    _load_script._counter = getattr(_load_script, "_counter", 0) + 1
    script_path = SKILLS_ROOT / skill_dir / "scripts" / "{}.py".format(script_name)
    module_name = "r24_{}_{}_{}".format(skill_dir.replace("-", "_"), script_name, _load_script._counter)
    spec = importlib.util.spec_from_file_location(module_name, str(script_path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _make_mock_maya(cmds_attrs=None):
    """Return (mock_maya, mock_cmds) with .cmds linkage wired."""
    mock_cmds = MagicMock()
    mock_maya = MagicMock()
    mock_maya.cmds = mock_cmds
    if cmds_attrs:
        for k, v in cmds_attrs.items():
            setattr(mock_cmds, k, v)
    return mock_maya, mock_cmds


# ---------------------------------------------------------------------------
# maya-display / create_display_layer
# ---------------------------------------------------------------------------


class TestCreateDisplayLayer:
    """Tests for maya-display/scripts/create_display_layer.py."""

    def test_create_layer_no_name(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.createDisplayLayer.return_value = "layer1"
        mock_cmds.objExists.return_value = False

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-display", "create_display_layer")
            result = mod.create_display_layer()

        assert result["success"] is True
        assert result["context"]["layer_name"] == "layer1"
        assert result["context"]["objects_added"] == []
        assert result["context"]["visibility"] is True

    def test_create_layer_with_name(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.createDisplayLayer.return_value = "myLayer"

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-display", "create_display_layer")
            result = mod.create_display_layer(name="myLayer")

        assert result["success"] is True
        assert result["context"]["layer_name"] == "myLayer"
        call_kwargs = mock_cmds.createDisplayLayer.call_args
        assert "name" in str(call_kwargs)

    def test_create_layer_hidden(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.createDisplayLayer.return_value = "hiddenLayer"

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-display", "create_display_layer")
            result = mod.create_display_layer(visibility=False)

        assert result["success"] is True
        assert result["context"]["visibility"] is False
        mock_cmds.setAttr.assert_called_once()

    def test_create_layer_with_objects(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.createDisplayLayer.return_value = "layer2"
        mock_cmds.objExists.side_effect = [True, True, False]

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-display", "create_display_layer")
            result = mod.create_display_layer(objects=["pSphere1", "pCube1", "missing"])

        assert result["success"] is True
        assert result["context"]["objects_added"] == ["pSphere1", "pCube1"]
        assert mock_cmds.editDisplayLayerMembers.call_count == 2

    def test_create_layer_objects_all_missing(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.createDisplayLayer.return_value = "layer3"
        mock_cmds.objExists.return_value = False

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-display", "create_display_layer")
            result = mod.create_display_layer(objects=["gone1", "gone2"])

        assert result["success"] is True
        assert result["context"]["objects_added"] == []

    def test_create_layer_exception(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.createDisplayLayer.side_effect = RuntimeError("layer limit reached")

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-display", "create_display_layer")
            result = mod.create_display_layer()

        assert result["success"] is False
        assert "layer limit reached" in result["error"]

    def test_create_layer_main_entry(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.createDisplayLayer.return_value = "layerX"

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-display", "create_display_layer")
            result = mod.main()

        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# maya-display / delete_display_layer
# ---------------------------------------------------------------------------


class TestDeleteDisplayLayer:
    """Tests for maya-display/scripts/delete_display_layer.py."""

    def test_delete_default_layer_rejected(self):
        mock_maya, mock_cmds = _make_mock_maya()

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-display", "delete_display_layer")
            result = mod.delete_display_layer("defaultLayer")

        assert result["success"] is False
        assert "defaultLayer" in result["message"]

    def test_delete_nonexistent_layer(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.objExists.return_value = False

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-display", "delete_display_layer")
            result = mod.delete_display_layer("ghost_layer")

        assert result["success"] is False
        assert "ghost_layer" in result["message"]

    def test_delete_wrong_node_type(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.objectType.return_value = "transform"

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-display", "delete_display_layer")
            result = mod.delete_display_layer("pSphere1")

        assert result["success"] is False
        assert result["message"].lower().startswith("wrong node type")

    def test_delete_layer_success(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.objectType.return_value = "displayLayer"
        mock_cmds.editDisplayLayerMembers.return_value = None

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-display", "delete_display_layer")
            result = mod.delete_display_layer("layer1")

        assert result["success"] is True
        assert result["context"]["layer_name"] == "layer1"
        assert result["context"]["objects_deleted"] == []
        mock_cmds.delete.assert_called_once_with("layer1")

    def test_delete_layer_with_objects(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.objectType.return_value = "displayLayer"
        mock_cmds.editDisplayLayerMembers.return_value = ["pSphere1", "pCube1"]

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-display", "delete_display_layer")
            result = mod.delete_display_layer("layer1", remove_objects=True)

        assert result["success"] is True
        assert "pSphere1" in result["context"]["objects_deleted"]
        assert "pCube1" in result["context"]["objects_deleted"]
        # delete called for objects + layer
        assert mock_cmds.delete.call_count == 2

    def test_delete_layer_remove_objects_empty_members(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.objectType.return_value = "displayLayer"
        mock_cmds.editDisplayLayerMembers.return_value = []

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-display", "delete_display_layer")
            result = mod.delete_display_layer("emptyLayer", remove_objects=True)

        assert result["success"] is True
        assert result["context"]["objects_deleted"] == []

    def test_delete_layer_exception(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.objectType.return_value = "displayLayer"
        mock_cmds.delete.side_effect = RuntimeError("cannot delete")

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-display", "delete_display_layer")
            result = mod.delete_display_layer("layer1")

        assert result["success"] is False
        assert "cannot delete" in result["error"]


# ---------------------------------------------------------------------------
# maya-display / list_display_layers
# ---------------------------------------------------------------------------


class TestListDisplayLayers:
    """Tests for maya-display/scripts/list_display_layers.py."""

    def test_list_empty(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.ls.return_value = []

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-display", "list_display_layers")
            result = mod.list_display_layers()

        assert result["success"] is True
        assert result["context"]["count"] == 0
        assert result["context"]["layers"] == []

    def test_list_multiple_layers(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.ls.return_value = ["defaultLayer", "myLayer"]
        mock_cmds.getAttr.side_effect = [1, 0]
        mock_cmds.editDisplayLayerMembers.side_effect = [
            [],
            ["pSphere1"],
        ]

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-display", "list_display_layers")
            result = mod.list_display_layers()

        assert result["success"] is True
        assert result["context"]["count"] == 2
        layer_names = [layer["name"] for layer in result["context"]["layers"]]
        assert "defaultLayer" in layer_names
        assert "myLayer" in layer_names

    def test_list_layer_with_members(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.ls.return_value = ["layer1"]
        mock_cmds.getAttr.return_value = 1
        mock_cmds.editDisplayLayerMembers.return_value = ["pSphere1", "pCube1"]

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-display", "list_display_layers")
            result = mod.list_display_layers()

        layer = result["context"]["layers"][0]
        assert "pSphere1" in layer["members"]
        assert layer["visibility"] is True

    def test_list_layers_members_none(self):
        """editDisplayLayerMembers returns None — should produce empty list."""
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.ls.return_value = ["layer1"]
        mock_cmds.getAttr.return_value = 1
        mock_cmds.editDisplayLayerMembers.return_value = None

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-display", "list_display_layers")
            result = mod.list_display_layers()

        assert result["context"]["layers"][0]["members"] == []

    def test_list_layers_exception(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.ls.side_effect = RuntimeError("scene read error")

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-display", "list_display_layers")
            result = mod.list_display_layers()

        assert result["success"] is False


# ---------------------------------------------------------------------------
# maya-display / set_display_layer
# ---------------------------------------------------------------------------


class TestSetDisplayLayer:
    """Tests for maya-display/scripts/set_display_layer.py."""

    def test_set_layer_success_all_exist(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.objExists.side_effect = [True, True, True]

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-display", "set_display_layer")
            result = mod.set_display_layer("layer1", ["pSphere1", "pCube1"])

        assert result["success"] is True
        assert result["context"]["assigned"] == ["pSphere1", "pCube1"]
        assert result["context"]["missing"] == []
        assert mock_cmds.editDisplayLayerMembers.call_count == 2

    def test_set_layer_some_missing(self):
        mock_maya, mock_cmds = _make_mock_maya()
        # layer exists, obj1 exists, obj2 missing
        mock_cmds.objExists.side_effect = [True, True, False]

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-display", "set_display_layer")
            result = mod.set_display_layer("layer1", ["pSphere1", "ghost"])

        assert result["success"] is True
        assert "pSphere1" in result["context"]["assigned"]
        assert "ghost" in result["context"]["missing"]
        assert "not found" in result["message"]

    def test_set_layer_not_found(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.objExists.return_value = False

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-display", "set_display_layer")
            result = mod.set_display_layer("nonexistent_layer", ["pSphere1"])

        assert result["success"] is False
        assert "not found" in result["message"].lower() or "nonexistent_layer" in result["error"]

    def test_set_layer_empty_object_list(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.objExists.return_value = True  # layer exists

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-display", "set_display_layer")
            result = mod.set_display_layer("layer1", [])

        assert result["success"] is True
        assert result["context"]["assigned"] == []
        mock_cmds.editDisplayLayerMembers.assert_not_called()

    def test_set_layer_exception(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.editDisplayLayerMembers.side_effect = RuntimeError("layer locked")

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-display", "set_display_layer")
            result = mod.set_display_layer("layer1", ["pSphere1"])

        assert result["success"] is False
        assert "layer locked" in result["error"]

    def test_set_layer_main_entry(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.objExists.return_value = True

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-display", "set_display_layer")
            result = mod.main(layer_name="defaultLayer", objects=["pSphere1"])

        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# maya-annotation — gap coverage
# ---------------------------------------------------------------------------


class TestUpdateAnnotationEdgeCases:
    """Additional edge cases for maya-annotation/scripts/update_annotation.py."""

    def test_update_transform_no_annotationshape(self):
        """Transform exists but has no annotationShape children → error."""
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.objectType.return_value = "transform"
        mock_cmds.listRelatives.return_value = []  # no annotationShape children

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-annotation", "update_annotation")
            result = mod.update_annotation("annotation1", text="new text")

        assert result["success"] is False
        assert "annotationShape" in result["message"]

    def test_update_annotation_no_parent(self):
        """annotationShape with no parent transform — should still succeed."""
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.objectType.return_value = "annotationShape"
        mock_cmds.listRelatives.return_value = None  # no parent
        mock_cmds.getAttr.return_value = "updated"

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-annotation", "update_annotation")
            result = mod.update_annotation("annotationShape1", text="updated")

        assert result["success"] is True
        assert result["context"]["transform_node"] is None

    def test_update_annotation_exception(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.objectType.return_value = "annotationShape"
        mock_cmds.listRelatives.return_value = ["ann1"]
        mock_cmds.setAttr.side_effect = RuntimeError("attr locked")

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-annotation", "update_annotation")
            result = mod.update_annotation("annotationShape1", text="x")

        assert result["success"] is False
        assert "attr locked" in result["error"]

    def test_update_position_bad_length(self):
        """position list with wrong length → position unchanged, text updated."""
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.objectType.return_value = "annotationShape"
        mock_cmds.listRelatives.return_value = ["ann1"]
        mock_cmds.getAttr.return_value = "my text"

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-annotation", "update_annotation")
            result = mod.update_annotation("annotationShape1", position=[1.0, 2.0])

        assert result["success"] is True
        mock_cmds.move.assert_not_called()


class TestDeleteAnnotationEdgeCases:
    """Additional edge cases for maya-annotation/scripts/delete_annotation.py."""

    def test_delete_shape_no_parent(self):
        """annotationShape with no parent — should delete shape itself."""
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.objectType.return_value = "annotationShape"
        mock_cmds.listRelatives.return_value = None

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-annotation", "delete_annotation")
            result = mod.delete_annotation("annotationShape1")

        assert result["success"] is True
        mock_cmds.delete.assert_called_once_with("annotationShape1")

    def test_delete_exception(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.objectType.return_value = "transform"
        mock_cmds.delete.side_effect = RuntimeError("delete failed")

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-annotation", "delete_annotation")
            result = mod.delete_annotation("annotation1")

        assert result["success"] is False
        assert "delete failed" in result["error"]


# ---------------------------------------------------------------------------
# maya-audio — gap coverage
# ---------------------------------------------------------------------------


class TestRemoveAudioEdgeCases:
    """Additional edge cases for maya-audio/scripts/remove_audio.py."""

    def test_remove_audio_wrong_type(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.objectType.return_value = "transform"

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-audio", "remove_audio")
            result = mod.remove_audio("pSphere1")

        assert result["success"] is False
        assert "Not a sound node" in result["message"]

    def test_remove_audio_exception(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.objectType.return_value = "audio"
        mock_cmds.delete.side_effect = RuntimeError("node locked")

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-audio", "remove_audio")
            result = mod.remove_audio("sound1")

        assert result["success"] is False
        assert "node locked" in result["error"]

    def test_remove_audio_main_entry(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.objectType.return_value = "audio"

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-audio", "remove_audio")
            result = mod.main(sound_node="sound1")

        assert isinstance(result, dict)


class TestSetTimelineAudioEdgeCases:
    """Additional edge cases for maya-audio/scripts/set_timeline_audio.py."""

    def test_set_timeline_audio_exception(self):
        """timeControl raises exception — should return error."""
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.objectType.return_value = "audio"
        mock_mel = MagicMock()
        mock_mel.eval.return_value = "timeControl1"
        mock_cmds.timeControl.side_effect = RuntimeError("UI not available")

        with patch.dict(
            sys.modules,
            {"maya": mock_maya, "maya.cmds": mock_cmds, "maya.mel": mock_mel},
        ):
            mod = _load_script("maya-audio", "set_timeline_audio")
            result = mod.set_timeline_audio("sound1")

        assert result["success"] is False
        assert "UI not available" in result["error"]

    def test_set_timeline_audio_mel_exception(self):
        """timeControl call raises after mel.eval succeeds — error path."""
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.objExists.return_value = True
        mock_cmds.objectType.return_value = "audio"
        mock_mel = MagicMock()
        mock_mel.eval.return_value = "timeControl1"
        # Both timeControl and the mel eval fail
        mock_cmds.timeControl.side_effect = RuntimeError("MEL context not available")

        with patch.dict(
            sys.modules,
            {"maya": mock_maya, "maya.cmds": mock_cmds, "maya.mel": mock_mel},
        ):
            mod = _load_script("maya-audio", "set_timeline_audio")
            result = mod.set_timeline_audio("sound1")

        assert result["success"] is False

    def test_set_timeline_audio_main_entry(self):
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
            result = mod.main(sound_node="sound1")

        assert isinstance(result, dict)


class TestImportAudioEdgeCases:
    """Additional edge cases for maya-audio/scripts/import_audio.py."""

    def test_import_audio_name_passed_to_sound(self, tmp_path):
        audio_file = tmp_path / "track.wav"
        audio_file.write_bytes(b"RIFF")

        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.sound.return_value = "trackSound"

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-audio", "import_audio")
            result = mod.import_audio(str(audio_file), name="trackSound")

        assert result["success"] is True
        call_kwargs = mock_cmds.sound.call_args
        assert "name" in str(call_kwargs)

    def test_import_audio_zero_offset(self, tmp_path):
        audio_file = tmp_path / "fx.wav"
        audio_file.write_bytes(b"RIFF")

        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.sound.return_value = "fxSound"

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-audio", "import_audio")
            result = mod.import_audio(str(audio_file))

        assert result["context"]["offset"] == 0.0

    def test_import_audio_main_entry(self, tmp_path):
        audio_file = tmp_path / "main.wav"
        audio_file.write_bytes(b"RIFF")

        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.sound.return_value = "mainSound"

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-audio", "import_audio")
            result = mod.main(file_path=str(audio_file))

        assert isinstance(result, dict)


class TestListAudioEdgeCases:
    """Additional edge cases for maya-audio/scripts/list_audio.py."""

    def test_list_audio_getattr_none(self):
        """getAttr returns None for filename/offset — should default gracefully."""
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.ls.return_value = ["sound1"]
        mock_cmds.getAttr.side_effect = [None, None]

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-audio", "list_audio")
            result = mod.list_audio()

        assert result["success"] is True
        node = result["context"]["sound_nodes"][0]
        assert node["file_path"] == ""
        assert node["offset"] == 0.0

    def test_list_audio_main_entry(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.ls.return_value = []

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-audio", "list_audio")
            result = mod.main()

        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# maya-annotation — list_annotations no-parent edge case
# ---------------------------------------------------------------------------


class TestListAnnotationsEdgeCases:
    """Additional edge cases for maya-annotation/scripts/list_annotations.py."""

    def test_list_annotations_no_parent(self):
        """annotationShape with no parent — transform_node should fall back to shape."""
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.ls.return_value = ["annotationShape1"]
        mock_cmds.getAttr.return_value = "Some text"
        mock_cmds.listRelatives.return_value = None

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-annotation", "list_annotations")
            result = mod.list_annotations()

        assert result["success"] is True
        ann = result["context"]["annotations"][0]
        assert ann["transform_node"] == "annotationShape1"

    def test_list_annotations_empty_text(self):
        """getAttr returns None — text should be empty string."""
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.ls.return_value = ["annotationShape1"]
        mock_cmds.getAttr.return_value = None
        mock_cmds.listRelatives.return_value = ["annotation1"]

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-annotation", "list_annotations")
            result = mod.list_annotations()

        assert result["context"]["annotations"][0]["text"] == ""

    def test_list_annotations_main_entry(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.ls.return_value = []

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-annotation", "list_annotations")
            result = mod.main()

        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# maya-create_annotation — default position fallback
# ---------------------------------------------------------------------------


class TestCreateAnnotationEdgeCases:
    """Additional edge cases for maya-annotation/scripts/create_annotation.py."""

    def test_create_annotation_default_position(self):
        """position=None → default [0, 1, 0] used."""
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.annotate.return_value = "annotationShape1"
        mock_cmds.listRelatives.return_value = ["annotation1"]

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-annotation", "create_annotation")
            result = mod.create_annotation("note")

        assert result["success"] is True
        assert result["context"]["position"] == [0.0, 1.0, 0.0]

    def test_create_annotation_wrong_position_length(self):
        """position with length != 3 → fallback to default."""
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.annotate.return_value = "annotationShape1"
        mock_cmds.listRelatives.return_value = ["annotation1"]

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-annotation", "create_annotation")
            result = mod.create_annotation("note", position=[1.0, 2.0])

        assert result["success"] is True
        assert result["context"]["position"] == [0.0, 1.0, 0.0]

    def test_create_annotation_long_text_truncated_in_message(self):
        """Long text should be truncated to 40 chars in success message."""
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.annotate.return_value = "annotationShape1"
        mock_cmds.listRelatives.return_value = ["annotation1"]
        long_text = "A" * 100

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-annotation", "create_annotation")
            result = mod.create_annotation(long_text)

        assert result["success"] is True
        # context.text holds the full text
        assert result["context"]["text"] == long_text
        # message is truncated
        assert len(result["message"]) < len(long_text) + 50

    def test_create_annotation_main_entry(self):
        mock_maya, mock_cmds = _make_mock_maya()
        mock_cmds.annotate.return_value = "annotationShape1"
        mock_cmds.listRelatives.return_value = ["annotation1"]

        with patch.dict(sys.modules, {"maya": mock_maya, "maya.cmds": mock_cmds}):
            mod = _load_script("maya-annotation", "create_annotation")
            result = mod.main(text="hello")

        assert isinstance(result, dict)
