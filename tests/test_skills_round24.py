"""Round 24 tests: maya-xform-utils, maya-export-preset, maya-annotation."""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

SKILLS_ROOT = Path(__file__).parent.parent / "src" / "dcc_mcp_maya" / "skills"


def load_script(skill_dir: str, script_name: str):
    """Dynamically load a skill script, injecting a mock Maya environment."""
    mock_cmds = MagicMock()
    mock_mel = MagicMock()
    mock_maya = MagicMock()
    mock_maya.cmds = mock_cmds

    sys.modules["maya"] = mock_maya
    sys.modules["maya.cmds"] = mock_cmds
    sys.modules["maya.api"] = MagicMock()
    sys.modules["maya.utils"] = MagicMock()
    sys.modules["maya.mel"] = mock_mel

    script_path = SKILLS_ROOT / skill_dir / "scripts" / script_name
    spec = importlib.util.spec_from_file_location(script_name[:-3], str(script_path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    for key in list(sys.modules.keys()):
        if key in ("maya", "maya.cmds", "maya.api", "maya.utils", "maya.mel"):
            sys.modules.pop(key, None)

    return mod, mock_cmds, mock_mel


# ===========================================================================
# maya-xform-utils
# ===========================================================================


class TestGetWorldMatrix:
    def test_missing_name(self):
        mod, cmds, _ = load_script("maya-xform-utils", "get_world_matrix.py")
        r = mod.run({})
        assert not r.success
        assert "'name' is required" in r.error

    def test_object_not_found(self):
        mod, cmds, _ = load_script("maya-xform-utils", "get_world_matrix.py")
        cmds.objExists.return_value = False
        r = mod.run({"name": "pSphere1"})
        assert not r.success
        assert "not found" in r.message.lower() or "not exist" in r.error.lower()

    def test_returns_flat_matrix_by_default(self):
        mod, cmds, _ = load_script("maya-xform-utils", "get_world_matrix.py")
        cmds.objExists.return_value = True
        flat = list(range(16))
        cmds.getAttr.return_value = flat
        r = mod.run({"name": "pSphere1"})
        assert r.success
        assert r.context["matrix"] == flat

    def test_returns_nested_matrix_when_as_list_false(self):
        mod, cmds, _ = load_script("maya-xform-utils", "get_world_matrix.py")
        cmds.objExists.return_value = True
        flat = list(range(16))
        cmds.getAttr.return_value = flat
        r = mod.run({"name": "pSphere1", "as_list": False})
        assert r.success
        mat = r.context["matrix"]
        assert len(mat) == 4
        assert len(mat[0]) == 4

    def test_exception_handled(self):
        mod, cmds, _ = load_script("maya-xform-utils", "get_world_matrix.py")
        cmds.objExists.side_effect = RuntimeError("maya error")
        r = mod.run({"name": "pSphere1"})
        assert not r.success


class TestDecomposeMatrix:
    def test_missing_name(self):
        mod, cmds, _ = load_script("maya-xform-utils", "decompose_matrix.py")
        r = mod.run({})
        assert not r.success
        assert "'name' is required" in r.error

    def test_object_not_found(self):
        mod, cmds, _ = load_script("maya-xform-utils", "decompose_matrix.py")
        cmds.objExists.return_value = False
        r = mod.run({"name": "pCube1"})
        assert not r.success

    def test_world_space_decompose(self):
        mod, cmds, _ = load_script("maya-xform-utils", "decompose_matrix.py")
        cmds.objExists.return_value = True
        cmds.getAttr.return_value = [(1.0, 2.0, 3.0)]
        cmds.xform.side_effect = [
            [1.0, 2.0, 3.0],   # world translate
            [0.0, 45.0, 0.0],  # world rotate
            [1.0, 1.0, 1.0],   # world scale
        ]
        r = mod.run({"name": "pCube1", "space": "world"})
        assert r.success
        assert r.context["space"] == "world"
        assert "translate" in r.context

    def test_local_space_decompose(self):
        mod, cmds, _ = load_script("maya-xform-utils", "decompose_matrix.py")
        cmds.objExists.return_value = True
        cmds.getAttr.return_value = [(0.0, 1.0, 0.0)]
        r = mod.run({"name": "pCube1", "space": "local"})
        assert r.success
        assert r.context["space"] == "local"

    def test_exception_handled(self):
        mod, cmds, _ = load_script("maya-xform-utils", "decompose_matrix.py")
        cmds.objExists.side_effect = RuntimeError("boom")
        r = mod.run({"name": "x"})
        assert not r.success


class TestSnapToObject:
    def test_missing_source(self):
        mod, cmds, _ = load_script("maya-xform-utils", "snap_to_object.py")
        r = mod.run({"target": "pCube1"})
        assert not r.success
        assert "'source' is required" in r.error

    def test_missing_target(self):
        mod, cmds, _ = load_script("maya-xform-utils", "snap_to_object.py")
        r = mod.run({"source": "pSphere1"})
        assert not r.success
        assert "'target' is required" in r.error

    def test_source_not_found(self):
        mod, cmds, _ = load_script("maya-xform-utils", "snap_to_object.py")
        cmds.objExists.side_effect = [False, True]
        r = mod.run({"source": "missing", "target": "pCube1"})
        assert not r.success

    def test_target_not_found(self):
        mod, cmds, _ = load_script("maya-xform-utils", "snap_to_object.py")
        cmds.objExists.side_effect = [True, False]
        r = mod.run({"source": "pSphere1", "target": "missing"})
        assert not r.success

    def test_snap_success(self):
        mod, cmds, _ = load_script("maya-xform-utils", "snap_to_object.py")
        cmds.objExists.return_value = True
        # xform calls in order: get target t, set source t (None), get target r,
        # set source r (None), query final t, query final r
        cmds.xform.side_effect = [
            [1.0, 2.0, 3.0],   # get target translate
            None,               # set source translate
            [0.0, 90.0, 0.0],  # get target rotate
            None,               # set source rotate
            [1.0, 2.0, 3.0],   # query final translate
            [0.0, 90.0, 0.0],  # query final rotate
        ]
        r = mod.run({"source": "pSphere1", "target": "pCube1"})
        assert r.success
        assert "Snapped" in r.message

    def test_exception_handled(self):
        mod, cmds, _ = load_script("maya-xform-utils", "snap_to_object.py")
        cmds.objExists.side_effect = RuntimeError("crash")
        r = mod.run({"source": "a", "target": "b"})
        assert not r.success


class TestBakeWorldTransforms:
    def test_missing_objects(self):
        mod, cmds, _ = load_script("maya-xform-utils", "bake_world_transforms.py")
        r = mod.run({})
        assert not r.success
        assert "'objects' must be a non-empty list" in r.error

    def test_objects_not_found(self):
        mod, cmds, _ = load_script("maya-xform-utils", "bake_world_transforms.py")
        cmds.objExists.return_value = False
        cmds.playbackOptions.return_value = 1
        r = mod.run({"objects": ["missing1", "missing2"]})
        assert not r.success
        assert "not found" in r.message.lower() or "do not exist" in r.error.lower()

    def test_bake_success(self):
        mod, cmds, _ = load_script("maya-xform-utils", "bake_world_transforms.py")
        cmds.objExists.return_value = True
        cmds.playbackOptions.return_value = 1
        r = mod.run({"objects": ["pSphere1", "pCube1"], "start_frame": 1, "end_frame": 24})
        assert r.success
        assert r.context["count"] == 2

    def test_uses_timeline_defaults(self):
        mod, cmds, _ = load_script("maya-xform-utils", "bake_world_transforms.py")
        cmds.objExists.return_value = True
        cmds.playbackOptions.return_value = 10
        r = mod.run({"objects": ["pSphere1"]})
        assert r.success

    def test_exception_handled(self):
        mod, cmds, _ = load_script("maya-xform-utils", "bake_world_transforms.py")
        cmds.playbackOptions.side_effect = RuntimeError("no maya")
        r = mod.run({"objects": ["x"]})
        assert not r.success


class TestMatchTransforms:
    def test_missing_objects(self):
        mod, cmds, _ = load_script("maya-xform-utils", "match_transforms.py")
        r = mod.run({"reference": "pCube1"})
        assert not r.success

    def test_missing_reference(self):
        mod, cmds, _ = load_script("maya-xform-utils", "match_transforms.py")
        r = mod.run({"objects": ["pSphere1"]})
        assert not r.success
        assert "'reference' is required" in r.error

    def test_reference_not_found(self):
        mod, cmds, _ = load_script("maya-xform-utils", "match_transforms.py")
        cmds.objExists.side_effect = [False]
        r = mod.run({"objects": ["pSphere1"], "reference": "missing"})
        assert not r.success

    def test_objects_not_found(self):
        mod, cmds, _ = load_script("maya-xform-utils", "match_transforms.py")
        cmds.objExists.side_effect = [True, False]
        r = mod.run({"objects": ["missing_obj"], "reference": "pCube1"})
        assert not r.success

    def test_match_success(self):
        mod, cmds, _ = load_script("maya-xform-utils", "match_transforms.py")
        cmds.objExists.return_value = True
        cmds.xform.return_value = [0.0, 0.0, 0.0]
        r = mod.run({"objects": ["pSphere1", "pCylinder1"], "reference": "pCube1"})
        assert r.success
        assert r.context["count"] == 2

    def test_match_with_scale(self):
        mod, cmds, _ = load_script("maya-xform-utils", "match_transforms.py")
        cmds.objExists.return_value = True
        cmds.xform.return_value = [1.0, 1.0, 1.0]
        r = mod.run({
            "objects": ["pSphere1"],
            "reference": "pCube1",
            "match_scale": True,
        })
        assert r.success

    def test_exception_handled(self):
        mod, cmds, _ = load_script("maya-xform-utils", "match_transforms.py")
        cmds.objExists.side_effect = RuntimeError("fail")
        r = mod.run({"objects": ["x"], "reference": "y"})
        assert not r.success


# ===========================================================================
# maya-export-preset
# ===========================================================================


class TestSaveExportPreset:
    def test_missing_name(self):
        mod, cmds, _ = load_script("maya-export-preset", "save_export_preset.py")
        r = mod.run({})
        assert not r.success
        assert "'name' is required" in r.error

    def test_save_success(self):
        mod, cmds, _ = load_script("maya-export-preset", "save_export_preset.py")
        with tempfile.TemporaryDirectory() as tmpdir:
            r = mod.run({
                "name": "my_fbx_preset",
                "format": "fbx",
                "settings": {"animation": True},
                "preset_dir": tmpdir,
            })
        assert r.success
        assert "my_fbx_preset" in r.message

    def test_default_format_is_fbx(self):
        mod, cmds, _ = load_script("maya-export-preset", "save_export_preset.py")
        with tempfile.TemporaryDirectory() as tmpdir:
            r = mod.run({"name": "test_preset", "preset_dir": tmpdir})
        assert r.success
        assert r.context["format"] == "fbx"

    def test_saved_file_contains_correct_data(self):
        mod, cmds, _ = load_script("maya-export-preset", "save_export_preset.py")
        with tempfile.TemporaryDirectory() as tmpdir:
            r = mod.run({
                "name": "abc_preset",
                "format": "alembic",
                "settings": {"frame_range": [1, 100]},
                "preset_dir": tmpdir,
            })
            assert r.success
            saved_path = r.context["path"]
            with open(saved_path) as fh:
                data = json.load(fh)
            assert data["format"] == "alembic"
            assert data["settings"]["frame_range"] == [1, 100]

    def test_exception_handled(self):
        mod, cmds, _ = load_script("maya-export-preset", "save_export_preset.py")
        with patch("os.makedirs", side_effect=OSError("permission denied")):
            r = mod.run({"name": "bad_preset", "preset_dir": "/some/dir"})
        assert not r.success


class TestLoadExportPreset:
    def test_missing_name(self):
        mod, cmds, _ = load_script("maya-export-preset", "load_export_preset.py")
        r = mod.run({})
        assert not r.success

    def test_preset_not_found(self):
        mod, cmds, _ = load_script("maya-export-preset", "load_export_preset.py")
        with tempfile.TemporaryDirectory() as tmpdir:
            r = mod.run({"name": "nonexistent", "preset_dir": tmpdir})
        assert not r.success
        assert "not found" in r.message.lower() or "not found" in r.error.lower()

    def test_load_success(self):
        mod, cmds, _ = load_script("maya-export-preset", "load_export_preset.py")
        with tempfile.TemporaryDirectory() as tmpdir:
            preset_path = os.path.join(tmpdir, "my_preset.json")
            with open(preset_path, "w") as fh:
                json.dump({"name": "my_preset", "format": "fbx", "settings": {}}, fh)
            r = mod.run({"name": "my_preset", "preset_dir": tmpdir})
        assert r.success
        assert r.context["preset"]["format"] == "fbx"

    def test_exception_handled(self):
        mod, cmds, _ = load_script("maya-export-preset", "load_export_preset.py")
        with tempfile.TemporaryDirectory() as tmpdir:
            preset_path = os.path.join(tmpdir, "p.json")
            with open(preset_path, "w", encoding="utf-8") as fh:
                fh.write("not valid json{{{")
            r = mod.run({"name": "p", "preset_dir": tmpdir})
        assert not r.success


class TestListExportPresets:
    def test_empty_dir_returns_empty_list(self):
        mod, cmds, _ = load_script("maya-export-preset", "list_export_presets.py")
        with tempfile.TemporaryDirectory() as tmpdir:
            r = mod.run({"preset_dir": tmpdir})
        assert r.success
        assert r.context["count"] == 0

    def test_nonexistent_dir_returns_empty(self):
        mod, cmds, _ = load_script("maya-export-preset", "list_export_presets.py")
        r = mod.run({"preset_dir": "/does/not/exist/__xyz__"})
        assert r.success
        assert r.context["count"] == 0

    def test_lists_all_presets(self):
        mod, cmds, _ = load_script("maya-export-preset", "list_export_presets.py")
        with tempfile.TemporaryDirectory() as tmpdir:
            for name, fmt in [("a", "fbx"), ("b", "alembic"), ("c", "obj")]:
                with open(os.path.join(tmpdir, "{}.json".format(name)), "w") as fh:
                    json.dump({"name": name, "format": fmt, "settings": {}}, fh)
            r = mod.run({"preset_dir": tmpdir})
        assert r.success
        assert r.context["count"] == 3

    def test_format_filter(self):
        mod, cmds, _ = load_script("maya-export-preset", "list_export_presets.py")
        with tempfile.TemporaryDirectory() as tmpdir:
            for name, fmt in [("a", "fbx"), ("b", "alembic")]:
                with open(os.path.join(tmpdir, "{}.json".format(name)), "w") as fh:
                    json.dump({"name": name, "format": fmt, "settings": {}}, fh)
            r = mod.run({"preset_dir": tmpdir, "format_filter": "fbx"})
        assert r.success
        assert r.context["count"] == 1

    def test_exception_handled(self):
        mod, cmds, _ = load_script("maya-export-preset", "list_export_presets.py")
        with patch("os.listdir", side_effect=OSError("boom")):
            with tempfile.TemporaryDirectory() as tmpdir:
                r = mod.run({"preset_dir": tmpdir})
        assert not r.success


class TestDeleteExportPreset:
    def test_missing_name(self):
        mod, cmds, _ = load_script("maya-export-preset", "delete_export_preset.py")
        r = mod.run({})
        assert not r.success

    def test_preset_not_found(self):
        mod, cmds, _ = load_script("maya-export-preset", "delete_export_preset.py")
        with tempfile.TemporaryDirectory() as tmpdir:
            r = mod.run({"name": "ghost", "preset_dir": tmpdir})
        assert not r.success

    def test_delete_success(self):
        mod, cmds, _ = load_script("maya-export-preset", "delete_export_preset.py")
        with tempfile.TemporaryDirectory() as tmpdir:
            preset_path = os.path.join(tmpdir, "to_delete.json")
            with open(preset_path, "w") as fh:
                json.dump({"name": "to_delete", "format": "fbx", "settings": {}}, fh)
            r = mod.run({"name": "to_delete", "preset_dir": tmpdir})
            assert r.success
            assert not os.path.exists(preset_path)

    def test_prompt_present(self):
        mod, cmds, _ = load_script("maya-export-preset", "delete_export_preset.py")
        with tempfile.TemporaryDirectory() as tmpdir:
            preset_path = os.path.join(tmpdir, "p.json")
            with open(preset_path, "w") as fh:
                json.dump({"name": "p", "format": "obj", "settings": {}}, fh)
            r = mod.run({"name": "p", "preset_dir": tmpdir})
        assert r.success
        assert r.prompt  # should have a follow-up prompt

    def test_exception_handled(self):
        mod, cmds, _ = load_script("maya-export-preset", "delete_export_preset.py")
        with patch("os.remove", side_effect=OSError("perm")):
            with tempfile.TemporaryDirectory() as tmpdir:
                preset_path = os.path.join(tmpdir, "q.json")
                open(preset_path, "w").close()
                r = mod.run({"name": "q", "preset_dir": tmpdir})
        assert not r.success


class TestApplyExportPreset:
    def test_missing_name(self):
        mod, cmds, _ = load_script("maya-export-preset", "apply_export_preset.py")
        r = mod.run({})
        assert not r.success

    def test_preset_not_found(self):
        mod, cmds, _ = load_script("maya-export-preset", "apply_export_preset.py")
        with tempfile.TemporaryDirectory() as tmpdir:
            r = mod.run({"name": "ghost", "preset_dir": tmpdir})
        assert not r.success

    def test_missing_output_path(self):
        mod, cmds, _ = load_script("maya-export-preset", "apply_export_preset.py")
        with tempfile.TemporaryDirectory() as tmpdir:
            preset_path = os.path.join(tmpdir, "p.json")
            with open(preset_path, "w") as fh:
                json.dump({"name": "p", "format": "fbx", "settings": {}}, fh)
            r = mod.run({"name": "p", "preset_dir": tmpdir})
        assert not r.success
        assert "output path" in r.error.lower() or "output path" in r.message.lower()

    def test_apply_fbx_preset(self):
        mod, cmds, mock_mel = load_script("maya-export-preset", "apply_export_preset.py")
        with tempfile.TemporaryDirectory() as tmpdir:
            preset_path = os.path.join(tmpdir, "fbx_p.json")
            with open(preset_path, "w") as fh:
                json.dump({
                    "name": "fbx_p", "format": "fbx",
                    "settings": {"animation": True, "output_path": "/tmp/out.fbx"},
                }, fh)
            r = mod.run({"name": "fbx_p", "preset_dir": tmpdir})
        assert r.success
        assert r.context["format"] == "fbx"

    def test_apply_obj_preset(self):
        mod, cmds, _ = load_script("maya-export-preset", "apply_export_preset.py")
        with tempfile.TemporaryDirectory() as tmpdir:
            preset_path = os.path.join(tmpdir, "obj_p.json")
            with open(preset_path, "w") as fh:
                json.dump({
                    "name": "obj_p", "format": "obj",
                    "settings": {"output_path": "/tmp/out.obj"},
                }, fh)
            r = mod.run({"name": "obj_p", "preset_dir": tmpdir})
        assert r.success
        assert r.context["format"] == "obj"

    def test_unsupported_format(self):
        mod, cmds, _ = load_script("maya-export-preset", "apply_export_preset.py")
        with tempfile.TemporaryDirectory() as tmpdir:
            preset_path = os.path.join(tmpdir, "bad_p.json")
            with open(preset_path, "w") as fh:
                json.dump({
                    "name": "bad_p", "format": "dae",
                    "settings": {"output_path": "/tmp/out.dae"},
                }, fh)
            r = mod.run({"name": "bad_p", "preset_dir": tmpdir})
        assert not r.success
        assert "not supported" in r.error.lower()

    def test_output_path_override(self):
        mod, cmds, _ = load_script("maya-export-preset", "apply_export_preset.py")
        with tempfile.TemporaryDirectory() as tmpdir:
            preset_path = os.path.join(tmpdir, "ov_p.json")
            with open(preset_path, "w") as fh:
                json.dump({
                    "name": "ov_p", "format": "obj",
                    "settings": {},
                }, fh)
            r = mod.run({
                "name": "ov_p",
                "output_path": "/custom/path/out.obj",
                "preset_dir": tmpdir,
            })
        assert r.success
        assert r.context["output_path"] == "/custom/path/out.obj"


# ===========================================================================
# maya-annotation
# ===========================================================================


class TestCreateAnnotation:
    def test_missing_text(self):
        mod, cmds, _ = load_script("maya-annotation", "create_annotation.py")
        r = mod.run({})
        assert not r.success
        assert "'text' is required" in r.error

    def test_create_with_target(self):
        mod, cmds, _ = load_script("maya-annotation", "create_annotation.py")
        cmds.objExists.return_value = True
        cmds.annotate.return_value = "annotationShape1"
        cmds.listRelatives.return_value = ["annotation1"]
        r = mod.run({"text": "My note", "target": "pSphere1"})
        assert r.success
        assert "annotation_transform" in r.context

    def test_create_without_target(self):
        mod, cmds, _ = load_script("maya-annotation", "create_annotation.py")
        cmds.objExists.return_value = False
        cmds.spaceLocator.return_value = ["locator1"]
        cmds.annotate.return_value = "annotationShape1"
        cmds.listRelatives.return_value = ["annotation1"]
        r = mod.run({"text": "Free note", "position": [1.0, 2.0, 3.0]})
        assert r.success

    def test_rename_annotation(self):
        mod, cmds, _ = load_script("maya-annotation", "create_annotation.py")
        cmds.objExists.return_value = True
        cmds.annotate.return_value = "annotationShape1"
        cmds.listRelatives.return_value = ["annotation1"]
        cmds.rename.return_value = "myNote"
        r = mod.run({"text": "Named note", "target": "pSphere1", "name": "myNote"})
        assert r.success

    def test_short_position_padded(self):
        mod, cmds, _ = load_script("maya-annotation", "create_annotation.py")
        cmds.objExists.return_value = False
        cmds.spaceLocator.return_value = ["loc1"]
        cmds.annotate.return_value = "shape1"
        cmds.listRelatives.return_value = ["ann1"]
        r = mod.run({"text": "Test", "position": [5.0]})
        assert r.success
        assert len(r.context["position"]) == 3

    def test_exception_handled(self):
        mod, cmds, _ = load_script("maya-annotation", "create_annotation.py")
        cmds.objExists.return_value = False
        cmds.spaceLocator.return_value = ["loc1"]
        cmds.annotate.side_effect = RuntimeError("crash")
        r = mod.run({"text": "boom"})
        assert not r.success


class TestSetAnnotationText:
    def test_missing_name(self):
        mod, cmds, _ = load_script("maya-annotation", "set_annotation_text.py")
        r = mod.run({"text": "hello"})
        assert not r.success

    def test_missing_text(self):
        mod, cmds, _ = load_script("maya-annotation", "set_annotation_text.py")
        r = mod.run({"name": "ann1"})
        assert not r.success

    def test_node_not_found(self):
        mod, cmds, _ = load_script("maya-annotation", "set_annotation_text.py")
        cmds.objExists.return_value = False
        r = mod.run({"name": "ghost", "text": "hello"})
        assert not r.success

    def test_set_on_shape_node(self):
        mod, cmds, _ = load_script("maya-annotation", "set_annotation_text.py")
        cmds.objExists.return_value = True
        cmds.objectType.return_value = "annotationShape"
        r = mod.run({"name": "annShape1", "text": "Updated text"})
        assert r.success

    def test_set_on_transform_node(self):
        mod, cmds, _ = load_script("maya-annotation", "set_annotation_text.py")
        cmds.objExists.return_value = True
        cmds.objectType.return_value = "transform"
        cmds.listRelatives.return_value = ["annShape1"]
        # Make objectType return 'annotationShape' for the shape lookup
        cmds.objectType.side_effect = ["transform", "annotationShape"]
        r = mod.run({"name": "annTransform1", "text": "Transform updated"})
        assert r.success

    def test_transform_no_annotation_child(self):
        mod, cmds, _ = load_script("maya-annotation", "set_annotation_text.py")
        cmds.objExists.return_value = True
        cmds.objectType.return_value = "transform"
        cmds.listRelatives.return_value = []
        r = mod.run({"name": "emptyTransform", "text": "hello"})
        assert not r.success

    def test_invalid_node_type(self):
        mod, cmds, _ = load_script("maya-annotation", "set_annotation_text.py")
        cmds.objExists.return_value = True
        cmds.objectType.return_value = "mesh"
        r = mod.run({"name": "pSphereShape1", "text": "nope"})
        assert not r.success


class TestListAnnotations:
    def test_empty_scene(self):
        mod, cmds, _ = load_script("maya-annotation", "list_annotations.py")
        cmds.ls.return_value = []
        r = mod.run({})
        assert r.success
        assert r.context["count"] == 0

    def test_lists_all_shapes(self):
        mod, cmds, _ = load_script("maya-annotation", "list_annotations.py")
        cmds.ls.return_value = ["annShape1", "annShape2"]
        cmds.listRelatives.side_effect = [["ann1"], ["ann2"]]
        cmds.getAttr.side_effect = ["Note 1", "Note 2"]
        r = mod.run({})
        assert r.success
        assert r.context["count"] == 2

    def test_include_text_false(self):
        mod, cmds, _ = load_script("maya-annotation", "list_annotations.py")
        cmds.ls.return_value = ["annShape1"]
        cmds.listRelatives.return_value = ["ann1"]
        r = mod.run({"include_text": False})
        assert r.success
        assert "text" not in r.context["annotations"][0]

    def test_exception_handled(self):
        mod, cmds, _ = load_script("maya-annotation", "list_annotations.py")
        cmds.ls.side_effect = RuntimeError("ls failed")
        r = mod.run({})
        assert not r.success


class TestDeleteAnnotation:
    def test_missing_name(self):
        mod, cmds, _ = load_script("maya-annotation", "delete_annotation.py")
        r = mod.run({})
        assert not r.success

    def test_node_not_found(self):
        mod, cmds, _ = load_script("maya-annotation", "delete_annotation.py")
        cmds.objExists.return_value = False
        r = mod.run({"name": "ghost"})
        assert not r.success

    def test_invalid_node_type(self):
        mod, cmds, _ = load_script("maya-annotation", "delete_annotation.py")
        cmds.objExists.return_value = True
        cmds.objectType.return_value = "mesh"
        r = mod.run({"name": "pSphereShape1"})
        assert not r.success
        assert "Invalid node type" in r.message

    def test_delete_from_shape(self):
        mod, cmds, _ = load_script("maya-annotation", "delete_annotation.py")
        cmds.objExists.return_value = True
        cmds.objectType.return_value = "annotationShape"
        cmds.listRelatives.return_value = ["annTransform1"]
        r = mod.run({"name": "annShape1"})
        assert r.success
        cmds.delete.assert_called_once()

    def test_delete_from_transform(self):
        mod, cmds, _ = load_script("maya-annotation", "delete_annotation.py")
        cmds.objExists.return_value = True
        cmds.objectType.return_value = "transform"
        r = mod.run({"name": "annTransform1"})
        assert r.success
        cmds.delete.assert_called_once_with("annTransform1")

    def test_exception_handled(self):
        mod, cmds, _ = load_script("maya-annotation", "delete_annotation.py")
        cmds.objExists.side_effect = RuntimeError("oops")
        r = mod.run({"name": "x"})
        assert not r.success


class TestCreateStickyNote:
    def test_missing_node(self):
        mod, cmds, _ = load_script("maya-annotation", "create_sticky_note.py")
        r = mod.run({"text": "hello"})
        assert not r.success

    def test_missing_text(self):
        mod, cmds, _ = load_script("maya-annotation", "create_sticky_note.py")
        r = mod.run({"node": "pSphere1"})
        assert not r.success

    def test_node_not_found(self):
        mod, cmds, _ = load_script("maya-annotation", "create_sticky_note.py")
        cmds.objExists.return_value = False
        r = mod.run({"node": "ghost", "text": "hello"})
        assert not r.success

    def test_create_notes_attr_if_missing(self):
        mod, cmds, _ = load_script("maya-annotation", "create_sticky_note.py")
        cmds.objExists.return_value = True
        cmds.attributeQuery.return_value = False
        r = mod.run({"node": "pSphere1", "text": "My note"})
        assert r.success
        cmds.addAttr.assert_called_once()

    def test_reuse_existing_notes_attr(self):
        mod, cmds, _ = load_script("maya-annotation", "create_sticky_note.py")
        cmds.objExists.return_value = True
        cmds.attributeQuery.return_value = True
        r = mod.run({"node": "pSphere1", "text": "Updated note"})
        assert r.success
        cmds.addAttr.assert_not_called()

    def test_exception_handled(self):
        mod, cmds, _ = load_script("maya-annotation", "create_sticky_note.py")
        cmds.objExists.side_effect = RuntimeError("boom")
        r = mod.run({"node": "x", "text": "y"})
        assert not r.success
