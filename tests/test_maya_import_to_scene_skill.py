"""Unit tests for the maya-import-to-scene skill (Pipeline stage)."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from unittest.mock import MagicMock

# Import local modules
from conftest import load_and_call, load_and_call_with_mel


def _make_asset(path: str, fmt: str = "fbx", name: str = "hero") -> dict:
    return {"id": "abc123", "name": name, "path": path, "format": fmt, "size_bytes": 100, "metadata": {}}


def _setup_cmds(before=None, after=None):
    """Return a mock cmds where ls() returns before first, then after."""
    cmds = MagicMock()
    cmds.pluginInfo.return_value = False
    _before = before or []
    _after = after or ["|pCube1", "|pCube1|pCubeShape1"]
    call_count = [0]

    def ls_side_effect(*args, **kwargs):
        if kwargs.get("long") or kwargs.get("l") or (args and args[0] in {"-long", "-l"}):
            call_count[0] += 1
            if call_count[0] == 1:
                return list(_before)
            return list(_after)
        return []

    cmds.ls.side_effect = ls_side_effect
    cmds.objectType.return_value = "transform"
    cmds.xform.return_value = [0.0, 0.0, 0.0]
    return cmds


# ---------------------------------------------------------------------------
# Basic import tests
# ---------------------------------------------------------------------------


def test_import_to_scene_fbx_loads_plugin(tmp_path):
    path = tmp_path / "hero.fbx"
    path.write_bytes(b"FBX")
    cmds = _setup_cmds()
    mel = MagicMock()

    result = load_and_call_with_mel(
        "maya-import-to-scene/scripts/import_to_scene.py",
        cmds,
        mel,
        "main",
        asset=_make_asset(str(path), "fbx"),
    )

    assert result["success"] is True, result
    cmds.loadPlugin.assert_called_with("fbxmaya")
    mel.eval.assert_any_call("FBXResetImport")


def test_import_to_scene_obj_loads_plugin(tmp_path):
    path = tmp_path / "mesh.obj"
    path.write_bytes(b"OBJ")
    cmds = _setup_cmds()

    result = load_and_call(
        "maya-import-to-scene/scripts/import_to_scene.py",
        cmds,
        "main",
        asset=_make_asset(str(path), "obj"),
    )

    assert result["success"] is True, result
    cmds.loadPlugin.assert_called_with("objExport")


def test_import_to_scene_ma_no_plugin(tmp_path):
    path = tmp_path / "scene.ma"
    path.write_text("// maya ascii")
    cmds = _setup_cmds()

    result = load_and_call(
        "maya-import-to-scene/scripts/import_to_scene.py",
        cmds,
        "main",
        asset=_make_asset(str(path), "ma"),
    )

    assert result["success"] is True, result
    cmds.loadPlugin.assert_not_called()


def test_import_to_scene_usd_loads_plugin(tmp_path):
    path = tmp_path / "stage.usd"
    path.write_bytes(b"PXR")
    cmds = _setup_cmds()

    result = load_and_call(
        "maya-import-to-scene/scripts/import_to_scene.py",
        cmds,
        "main",
        asset=_make_asset(str(path), "usd"),
    )

    assert result["success"] is True, result
    cmds.loadPlugin.assert_called_with("mayaUsdPlugin")


def test_import_to_scene_returns_import_result_fields(tmp_path):
    path = tmp_path / "prop.fbx"
    path.write_bytes(b"FBX" * 100)
    cmds = _setup_cmds(before=[], after=["|prop", "|prop|propShape"])
    mel = MagicMock()

    result = load_and_call_with_mel(
        "maya-import-to-scene/scripts/import_to_scene.py",
        cmds,
        mel,
        "main",
        asset=_make_asset(str(path), "fbx", name="prop"),
    )

    assert result["success"] is True, result
    ctx = result["context"]
    assert ctx["asset_name"] == "prop"
    assert ctx["format"] == "fbx"
    assert "imported_short_names" in ctx
    assert "imported_long_names" in ctx
    assert "top_level_groups" in ctx
    assert ctx["size_bytes"] > 0
    assert ctx["axis_conversion"] == "none"
    assert ctx["material_mode"] == "preserve"
    assert ctx["placement_hint"] == "origin"


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


def test_import_to_scene_error_on_missing_file(tmp_path):
    asset = _make_asset(str(tmp_path / "ghost.fbx"), "fbx")
    cmds = MagicMock()
    cmds.pluginInfo.return_value = True

    result = load_and_call_with_mel(
        "maya-import-to-scene/scripts/import_to_scene.py",
        cmds,
        MagicMock(),
        "main",
        asset=asset,
    )

    assert result["success"] is False
    assert "not found" in result["message"].lower() or "does not exist" in result["message"].lower()


def test_import_to_scene_error_on_unsupported_format(tmp_path):
    path = tmp_path / "data.xyz"
    path.write_bytes(b"data")

    result = load_and_call(
        "maya-import-to-scene/scripts/import_to_scene.py",
        MagicMock(),
        "main",
        asset=_make_asset(str(path), "xyz"),
    )

    assert result["success"] is False
    assert "unsupported" in result["message"].lower() or "not supported" in result["message"].lower()


def test_import_to_scene_error_on_missing_asset():
    result = load_and_call(
        "maya-import-to-scene/scripts/import_to_scene.py",
        MagicMock(),
        "main",
        asset=None,
    )

    assert result["success"] is False


def test_import_to_scene_error_on_empty_path():
    result = load_and_call(
        "maya-import-to-scene/scripts/import_to_scene.py",
        MagicMock(),
        "main",
        asset={"path": "", "format": "fbx"},
    )

    assert result["success"] is False


# ---------------------------------------------------------------------------
# Axis conversion
# ---------------------------------------------------------------------------


def test_import_to_scene_y_to_z_axis_conversion(tmp_path):
    path = tmp_path / "hero.fbx"
    path.write_bytes(b"FBX")
    cmds = _setup_cmds(before=[], after=["|hero"])
    cmds.objectType.return_value = "transform"
    cmds.xform.return_value = [0.0, 0.0, 0.0]
    mel = MagicMock()

    result = load_and_call_with_mel(
        "maya-import-to-scene/scripts/import_to_scene.py",
        cmds,
        mel,
        "main",
        asset=_make_asset(str(path), "fbx"),
        axis_conversion="y_to_z",
    )

    assert result["success"] is True, result
    assert result["context"]["axis_conversion"] == "y_to_z"
    # xform should have been called with rotation (axis conversion)
    xform_calls = [str(c) for c in cmds.xform.call_args_list]
    assert any("rotation" in c for c in xform_calls)


def test_import_to_scene_z_to_y_axis_conversion(tmp_path):
    path = tmp_path / "hero.fbx"
    path.write_bytes(b"FBX")
    cmds = _setup_cmds(before=[], after=["|hero"])
    cmds.objectType.return_value = "transform"
    cmds.xform.return_value = [0.0, 0.0, 0.0]
    mel = MagicMock()

    result = load_and_call_with_mel(
        "maya-import-to-scene/scripts/import_to_scene.py",
        cmds,
        mel,
        "main",
        asset=_make_asset(str(path), "fbx"),
        axis_conversion="z_to_y",
    )

    assert result["success"] is True
    assert result["context"]["axis_conversion"] == "z_to_y"


def test_import_to_scene_none_axis_conversion_skips_xform(tmp_path):
    path = tmp_path / "hero.fbx"
    path.write_bytes(b"FBX")
    cmds = _setup_cmds(before=[], after=["|hero"])
    cmds.objectType.return_value = "transform"
    mel = MagicMock()

    result = load_and_call_with_mel(
        "maya-import-to-scene/scripts/import_to_scene.py",
        cmds,
        mel,
        "main",
        asset=_make_asset(str(path), "fbx"),
        axis_conversion="none",
    )

    assert result["success"] is True
    # No xform calls for rotation when axis_conversion=none
    rotation_calls = [c for c in cmds.xform.call_args_list if "rotation" in str(c)]
    assert len(rotation_calls) == 0


# ---------------------------------------------------------------------------
# Unit scale
# ---------------------------------------------------------------------------


def test_import_to_scene_unit_scale_applies_xform(tmp_path):
    path = tmp_path / "hero.fbx"
    path.write_bytes(b"FBX")
    cmds = _setup_cmds(before=[], after=["|hero"])
    cmds.objectType.return_value = "transform"
    cmds.xform.return_value = [1.0, 1.0, 1.0]
    mel = MagicMock()

    result = load_and_call_with_mel(
        "maya-import-to-scene/scripts/import_to_scene.py",
        cmds,
        mel,
        "main",
        asset=_make_asset(str(path), "fbx"),
        unit_scale=0.01,
    )

    assert result["success"] is True
    assert result["context"]["unit_scale"] == 0.01
    scale_calls = [c for c in cmds.xform.call_args_list if "scale" in str(c)]
    assert len(scale_calls) > 0


def test_import_to_scene_unit_scale_1_skips_xform(tmp_path):
    path = tmp_path / "hero.fbx"
    path.write_bytes(b"FBX")
    cmds = _setup_cmds(before=[], after=["|hero"])
    cmds.objectType.return_value = "transform"
    mel = MagicMock()

    result = load_and_call_with_mel(
        "maya-import-to-scene/scripts/import_to_scene.py",
        cmds,
        mel,
        "main",
        asset=_make_asset(str(path), "fbx"),
        unit_scale=1.0,
    )

    assert result["success"] is True
    scale_calls = [c for c in cmds.xform.call_args_list if "scale" in str(c)]
    assert len(scale_calls) == 0


# ---------------------------------------------------------------------------
# Material mode
# ---------------------------------------------------------------------------


def test_import_to_scene_assign_lambert_creates_shader(tmp_path):
    path = tmp_path / "hero.fbx"
    path.write_bytes(b"FBX")
    cmds = _setup_cmds(before=[], after=["|hero", "|hero|heroShape"])
    cmds.objectType.side_effect = lambda n: "mesh" if "Shape" in n else "transform"
    mel = MagicMock()

    result = load_and_call_with_mel(
        "maya-import-to-scene/scripts/import_to_scene.py",
        cmds,
        mel,
        "main",
        asset=_make_asset(str(path), "fbx"),
        material_mode="assign_lambert",
    )

    assert result["success"] is True
    assert result["context"]["material_mode"] == "assign_lambert"
    cmds.shadingNode.assert_called_once()
    cmds.connectAttr.assert_called_once()


def test_import_to_scene_preserve_material_no_shader_creation(tmp_path):
    path = tmp_path / "hero.fbx"
    path.write_bytes(b"FBX")
    cmds = _setup_cmds(before=[], after=["|hero", "|hero|heroShape"])
    cmds.objectType.side_effect = lambda n: "mesh" if "Shape" in n else "transform"
    mel = MagicMock()

    result = load_and_call_with_mel(
        "maya-import-to-scene/scripts/import_to_scene.py",
        cmds,
        mel,
        "main",
        asset=_make_asset(str(path), "fbx"),
        material_mode="preserve",
    )

    assert result["success"] is True
    cmds.shadingNode.assert_not_called()


def test_import_to_scene_skip_material_uses_initial_sg(tmp_path):
    path = tmp_path / "hero.fbx"
    path.write_bytes(b"FBX")
    cmds = _setup_cmds(before=[], after=["|hero", "|hero|heroShape"])
    cmds.objectType.side_effect = lambda n: "mesh" if "Shape" in n else "transform"
    mel = MagicMock()

    result = load_and_call_with_mel(
        "maya-import-to-scene/scripts/import_to_scene.py",
        cmds,
        mel,
        "main",
        asset=_make_asset(str(path), "fbx"),
        material_mode="skip",
    )

    assert result["success"] is True
    # sets() called to assign to initialShadingGroup
    sets_calls = [str(c) for c in cmds.sets.call_args_list]
    assert any("initialShadingGroup" in c for c in sets_calls)


# ---------------------------------------------------------------------------
# Placement hint
# ---------------------------------------------------------------------------


def test_import_to_scene_custom_placement_applies_translation(tmp_path):
    path = tmp_path / "hero.fbx"
    path.write_bytes(b"FBX")
    cmds = _setup_cmds(before=[], after=["|hero"])
    cmds.objectType.return_value = "transform"
    cmds.xform.return_value = [0.0, 0.0, 0.0]
    mel = MagicMock()

    result = load_and_call_with_mel(
        "maya-import-to-scene/scripts/import_to_scene.py",
        cmds,
        mel,
        "main",
        asset=_make_asset(str(path), "fbx"),
        placement_hint="custom",
        custom_position=[10.0, 20.0, 30.0],
    )

    assert result["success"] is True
    assert result["context"]["placement_hint"] == "custom"
    translation_calls = [c for c in cmds.xform.call_args_list if "translation" in str(c)]
    assert len(translation_calls) > 0


def test_import_to_scene_selection_placement_queries_pivot(tmp_path):
    path = tmp_path / "hero.fbx"
    path.write_bytes(b"FBX")
    cmds = _setup_cmds(before=[], after=["|hero"])
    cmds.objectType.return_value = "transform"
    cmds.ls.side_effect = None  # override the closure
    call_count = [0]

    def ls_side_effect(*args, **kwargs):
        if kwargs.get("long") or kwargs.get("l"):
            call_count[0] += 1
            if call_count[0] == 1:
                return []
            return ["|hero"]
        if kwargs.get("selection"):
            return ["pSphere1"]
        return []

    cmds.ls.side_effect = ls_side_effect
    cmds.xform.return_value = [5.0, 0.0, 0.0]
    mel = MagicMock()

    result = load_and_call_with_mel(
        "maya-import-to-scene/scripts/import_to_scene.py",
        cmds,
        mel,
        "main",
        asset=_make_asset(str(path), "fbx"),
        placement_hint="selection",
    )

    assert result["success"] is True


# ---------------------------------------------------------------------------
# Namespace
# ---------------------------------------------------------------------------


def test_import_to_scene_namespace_passed_to_cmds_file(tmp_path):
    path = tmp_path / "hero.fbx"
    path.write_bytes(b"FBX")
    cmds = _setup_cmds()
    mel = MagicMock()

    result = load_and_call_with_mel(
        "maya-import-to-scene/scripts/import_to_scene.py",
        cmds,
        mel,
        "main",
        asset=_make_asset(str(path), "fbx"),
        namespace="hero_ns",
    )

    assert result["success"] is True
    _args, kwargs = cmds.file.call_args
    assert kwargs.get("namespace") == "hero_ns"


# ---------------------------------------------------------------------------
# group_name
# ---------------------------------------------------------------------------


def test_import_to_scene_group_name_creates_wrapper(tmp_path):
    path = tmp_path / "hero.fbx"
    path.write_bytes(b"FBX")
    cmds = _setup_cmds(before=[], after=["|hero"])
    cmds.objectType.return_value = "transform"
    cmds.group.return_value = "|hero_grp"
    mel = MagicMock()

    result = load_and_call_with_mel(
        "maya-import-to-scene/scripts/import_to_scene.py",
        cmds,
        mel,
        "main",
        asset=_make_asset(str(path), "fbx"),
        group_name="hero_grp",
    )

    assert result["success"] is True
    cmds.group.assert_called_once()
    assert "|hero_grp" in result["context"]["top_level_groups"]


# ---------------------------------------------------------------------------
# target_collection
# ---------------------------------------------------------------------------


def test_import_to_scene_target_collection_objectset_adds_member(tmp_path):
    path = tmp_path / "hero.fbx"
    path.write_bytes(b"FBX")
    cmds = _setup_cmds(before=[], after=["|hero"])
    cmds.objectType.side_effect = lambda n, **_: "objectSet" if n == "asset_set" else "transform"
    cmds.objExists.return_value = True
    mel = MagicMock()

    result = load_and_call_with_mel(
        "maya-import-to-scene/scripts/import_to_scene.py",
        cmds,
        mel,
        "main",
        asset=_make_asset(str(path), "fbx"),
        target_collection="asset_set",
    )

    assert result["success"] is True
    sets_calls = [str(c) for c in cmds.sets.call_args_list]
    assert any("asset_set" in c for c in sets_calls)
