"""Unit tests for the maya-import-to-scene skill (Interchange stage).

Tests the contract-shaped import_to_scene entry point using
dcc_mcp_core.asset_import types with a mocked Maya environment.
"""

# Import future modules
from __future__ import annotations

# Import built-in modules
from unittest.mock import MagicMock

# Import local modules
from conftest import load_and_call


def _make_descriptor(
    asset_id: str = "arch/city-bank/desk",
    path: str = "/tmp/desk.fbx",
    fmt: str = "FBX",
    preferred: bool = False,
):
    """Build an AssetDescriptor-compatible dict for skill input."""
    return {
        "asset_id": asset_id,
        "variants": [
            {
                "local_path": path,
                "format": fmt,
                "preferred": preferred,
            }
        ],
        "tags": ["test"],
        "up_axis": "y",
    }


def test_import_to_scene_requires_descriptor():
    """Calling without a descriptor should return an error."""
    cmds = MagicMock()
    result = load_and_call(
        "maya-import-to-scene/scripts/import_to_scene.py",
        cmds,
        "main",
    )
    assert result["success"] is False
    assert "descriptor" in result.get("message", "").lower() or "descriptor" in result.get("error", "").lower()


def test_import_to_scene_fails_when_file_missing(tmp_path):
    """A non-existent file path should return a file-not-found error."""
    cmds = MagicMock()
    cmds.ls.return_value = []  # _check_skip_existing: ls(type="transform")
    missing = str(tmp_path / "nonexistent.fbx")
    descriptor = _make_descriptor(path=missing)

    result = load_and_call(
        "maya-import-to-scene/scripts/import_to_scene.py",
        cmds,
        "main",
        descriptor=descriptor,
        material_mode="as_authored",
    )
    assert result["success"] is False
    assert "file not found" in result.get("message", "").lower()


def test_import_to_scene_fbx_import(tmp_path):
    """FBX import dispatches through cmds.file with correct kwargs."""
    fbx_path = tmp_path / "desk.fbx"
    fbx_path.write_text("fbx")
    cmds = MagicMock()
    cmds.pluginInfo.return_value = False
    # ls calls: _check_skip_existing(type="transform"), before(long=True), after(long=True)
    cmds.ls.side_effect = [[], [], ["|desk"]]
    cmds.objectType.return_value = "transform"

    descriptor = _make_descriptor(path=str(fbx_path), fmt="FBX")

    result = load_and_call(
        "maya-import-to-scene/scripts/import_to_scene.py",
        cmds,
        "main",
        descriptor=descriptor,
        material_mode="as_authored",
    )

    assert result["success"] is True, result
    cmds.pluginInfo.assert_called_with("fbxmaya", query=True, loaded=True)
    cmds.loadPlugin.assert_called_with("fbxmaya")

    # Verify cmds.file was called with import kwargs.
    found_file_call = False
    for _args, kwargs in cmds.file.call_args_list:
        if kwargs.get("i") is True:
            found_file_call = True
            assert kwargs.get("prompt") is False
            assert kwargs.get("type") == "FBX"
            break
    assert found_file_call, "cmds.file(i=True, ...) was not called"

    # Verify _tag_asset_id set the attr (addAttr skipped since
    # attributeQuery returns truthy on the mock; setAttr still runs).
    cmds.setAttr.assert_called()


def test_import_to_scene_obj_import(tmp_path):
    """OBJ import dispatches through the generic cmds.file import path."""
    obj_path = tmp_path / "model.obj"
    obj_path.write_text("obj")
    cmds = MagicMock()
    cmds.pluginInfo.return_value = False
    # ls: skip_existing(type="transform"), before(long=True), after(long=True), importedNodes(long=True)
    cmds.ls.side_effect = [[], [], ["|model1"], []]
    cmds.objectType.return_value = "transform"

    descriptor = _make_descriptor(path=str(obj_path), fmt="OBJ")

    result = load_and_call(
        "maya-import-to-scene/scripts/import_to_scene.py",
        cmds,
        "main",
        descriptor=descriptor,
        material_mode="skip",
    )

    assert result["success"] is True, result

    # Verify at least one cmds.file call with i=True (generic import).
    file_calls = [a for a in cmds.file.call_args_list if a[1].get("i")]
    assert len(file_calls) >= 1


def test_import_to_scene_skip_existing(tmp_path):
    """When skip_existing=True and the asset_id is already tagged, skip the import."""
    cmds = MagicMock()
    cmds.ls.return_value = ["|existing_asset"]
    cmds.attributeQuery.return_value = True
    cmds.getAttr.return_value = "arch/city-bank/desk"
    cmds.objectType.return_value = "transform"

    descriptor = _make_descriptor(asset_id="arch/city-bank/desk")

    result = load_and_call(
        "maya-import-to-scene/scripts/import_to_scene.py",
        cmds,
        "main",
        descriptor=descriptor,
        material_mode="as_authored",
        skip_existing=True,
    )

    assert result["success"] is True, result
    # cmds.file should NOT be called since we skipped.
    file_calls = [a for a in cmds.file.call_args_list if a[1].get("i")]
    assert len(file_calls) == 0, "Expected zero file imports when skipping existing"


def test_import_to_scene_placement_hint(tmp_path):
    """Placement hint translate/rotate/scale should be applied to the root."""
    fbx_path = tmp_path / "placed.fbx"
    fbx_path.write_text("fbx")
    cmds = MagicMock()
    cmds.pluginInfo.return_value = False
    cmds.ls.side_effect = [[], [], ["|root1"]]
    cmds.objectType.return_value = "transform"

    descriptor = _make_descriptor(path=str(fbx_path))
    placement = {"translate": [1.0, 2.0, 3.0], "rotate": [0.0, 45.0, 0.0]}

    result = load_and_call(
        "maya-import-to-scene/scripts/import_to_scene.py",
        cmds,
        "main",
        descriptor=descriptor,
        material_mode="as_authored",
        placement=placement,
    )

    assert result["success"] is True, result

    # Verify setAttr was called for translate.
    translate_calls = [a for a in cmds.setAttr.call_args_list if "translate" in str(a)]
    assert len(translate_calls) >= 1, "Expected setAttr for translate placement"


def test_import_to_scene_material_mode_skip(tmp_path):
    """material_mode='skip' should delete custom materials and shading engines."""
    obj_path = tmp_path / "nomat.obj"
    obj_path.write_text("obj")
    cmds = MagicMock()
    cmds.pluginInfo.return_value = False
    # ls calls: skip_existing(type="transform"), before, after, importedNodes,
    #            shadingEngine query, mat query, displayLayer (collection=no)
    cmds.ls.side_effect = [
        [],                    # skip_existing: ls(type="transform")
        [],                    # before: ls(long=True)
        ["|nomat"],           # after: ls(long=True)
        [],                    # importedNodes fallback
        ["initialShadingGroup", "mySG"],  # ls(type="shadingEngine")
        ["lambert1", "standardSurface1", "myLambert"],  # ls(mat=True)
    ]
    cmds.objectType.return_value = "transform"

    descriptor = _make_descriptor(path=str(obj_path), fmt="OBJ")

    result = load_and_call(
        "maya-import-to-scene/scripts/import_to_scene.py",
        cmds,
        "main",
        descriptor=descriptor,
        material_mode="skip",
    )

    assert result["success"] is True, result
    # Should have deleted 'mySG' (shading engine) and 'myLambert' (material).
    cmds.delete.assert_any_call("mySG")


def test_import_to_scene_material_mode_default_gray(tmp_path):
    """material_mode='default_gray' should assign lambert1 to mesh faces."""
    obj_path = tmp_path / "gray.obj"
    obj_path.write_text("obj")
    cmds = MagicMock()
    cmds.pluginInfo.return_value = False
    # No importedNodes fallback since imported_long is non-empty (set diff).
    cmds.ls.side_effect = [
        [],                    # skip_existing: ls(type="transform")
        [],                    # before: ls(long=True)
        ["|gray"],            # after: ls(long=True) — imported_long non-empty
        ["|pSphereShape1"],   # _apply_material_mode: ls(type="mesh")
    ]
    cmds.objectType.return_value = "transform"

    descriptor = _make_descriptor(path=str(obj_path), fmt="OBJ")

    result = load_and_call(
        "maya-import-to-scene/scripts/import_to_scene.py",
        cmds,
        "main",
        descriptor=descriptor,
        material_mode="default_gray",
    )

    assert result["success"] is True, result
    cmds.hyperShade.assert_called_with(assign="lambert1")


def test_import_to_scene_target_collection(tmp_path):
    """target_collection should create/edit a display layer."""
    fbx_path = tmp_path / "layered.fbx"
    fbx_path.write_text("fbx")
    cmds = MagicMock()
    cmds.pluginInfo.return_value = False
    # No importedNodes fallback since imported_long is non-empty.
    cmds.ls.side_effect = [
        [],                    # skip_existing: ls(type="transform")
        [],                    # before: ls(long=True)
        ["|layered"],         # after: ls(long=True) — non-empty
        [],                    # _assign_to_collection: ls(type="displayLayer")
    ]
    cmds.objectType.return_value = "transform"

    descriptor = _make_descriptor(path=str(fbx_path))

    result = load_and_call(
        "maya-import-to-scene/scripts/import_to_scene.py",
        cmds,
        "main",
        descriptor=descriptor,
        material_mode="as_authored",
        target_collection="IMPORTED",
    )

    assert result["success"] is True, result
    cmds.createDisplayLayer.assert_called_once()


def test_import_to_scene_blend_unsupported(tmp_path):
    """Blender .blend files should return an unsupported-format error."""
    blend_path = tmp_path / "scene.blend"
    blend_path.write_text("blend")
    cmds = MagicMock()
    cmds.ls.return_value = []

    descriptor = _make_descriptor(path=str(blend_path), fmt="UNKNOWN")

    result = load_and_call(
        "maya-import-to-scene/scripts/import_to_scene.py",
        cmds,
        "main",
        descriptor=descriptor,
        material_mode="as_authored",
    )

    assert result["success"] is False
    # The error message should mention blend or unsupported format.
    msg = result.get("message", "").lower()
    assert "blend" in msg or "unsupported" in msg


def test_import_to_scene_preferred_variant_selection(tmp_path):
    """The 'preferred' flag should override format priority."""
    obj_path = tmp_path / "secondary.obj"
    obj_path.write_text("obj")
    fbx_path = tmp_path / "primary.fbx"
    fbx_path.write_text("fbx")

    cmds = MagicMock()
    cmds.pluginInfo.return_value = False
    cmds.ls.side_effect = [[], [], ["|primary"]]
    cmds.objectType.return_value = "transform"

    descriptor = {
        "asset_id": "test/preferred",
        "variants": [
            {"local_path": str(obj_path), "format": "OBJ", "preferred": False},
            {"local_path": str(fbx_path), "format": "FBX", "preferred": True},
        ],
        "tags": [],
        "up_axis": "y",
    }

    result = load_and_call(
        "maya-import-to-scene/scripts/import_to_scene.py",
        cmds,
        "main",
        descriptor=descriptor,
        material_mode="as_authored",
    )

    assert result["success"] is True, result

    # The preferred variant (FBX) should have been imported.
    # Normalize both sides: Path gives backslashes on Windows but
    # _normalize_path replaces them with forward slashes.
    fbx_str = str(fbx_path).replace("\\", "/")
    found_primary = False
    for args, _kwargs in cmds.file.call_args_list:
        if args and fbx_str in str(args[0]).replace("\\", "/"):
            found_primary = True
            break
    assert found_primary, "Expected preferred FBX variant to be imported"
