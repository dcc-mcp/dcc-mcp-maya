"""Unit tests for the maya-asset-source skill (Pipeline stage)."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from unittest.mock import MagicMock

# Import local modules
from conftest import load_and_call

# ---------------------------------------------------------------------------
# search_assets
# ---------------------------------------------------------------------------

def test_search_assets_finds_fbx_in_flat_dir(tmp_path):
    (tmp_path / "hero.fbx").write_bytes(b"FBX")
    (tmp_path / "rig.fbx").write_bytes(b"FBX")
    (tmp_path / "readme.txt").write_text("ignore me")

    result = load_and_call(
        "maya-asset-source/scripts/search_assets.py",
        MagicMock(),
        "main",
        root_dir=str(tmp_path),
    )

    assert result["success"] is True
    assets = result["context"]["assets"]
    names = {a["name"] for a in assets}
    assert "hero" in names
    assert "rig" in names
    # .txt must be excluded
    assert all(a["format"] in ("fbx", "obj", "usd", "usda", "usdc", "ma", "mb") for a in assets)


def test_search_assets_query_filters_by_stem(tmp_path):
    (tmp_path / "hero_v001.fbx").write_bytes(b"FBX")
    (tmp_path / "prop_box.fbx").write_bytes(b"FBX")
    (tmp_path / "env_ground.obj").write_bytes(b"OBJ")

    result = load_and_call(
        "maya-asset-source/scripts/search_assets.py",
        MagicMock(),
        "main",
        root_dir=str(tmp_path),
        query="hero",
    )

    assert result["success"] is True
    assets = result["context"]["assets"]
    assert len(assets) == 1
    assert assets[0]["name"] == "hero_v001"


def test_search_assets_formats_filter(tmp_path):
    (tmp_path / "mesh.fbx").write_bytes(b"FBX")
    (tmp_path / "cache.obj").write_bytes(b"OBJ")
    (tmp_path / "scene.ma").write_text("// maya ascii")

    result = load_and_call(
        "maya-asset-source/scripts/search_assets.py",
        MagicMock(),
        "main",
        root_dir=str(tmp_path),
        formats=["fbx"],
    )

    assert result["success"] is True
    assets = result["context"]["assets"]
    assert len(assets) == 1
    assert assets[0]["format"] == "fbx"


def test_search_assets_recursive_finds_nested(tmp_path):
    sub = tmp_path / "characters" / "hero"
    sub.mkdir(parents=True)
    (sub / "hero.fbx").write_bytes(b"FBX")

    result = load_and_call(
        "maya-asset-source/scripts/search_assets.py",
        MagicMock(),
        "main",
        root_dir=str(tmp_path),
        recursive=True,
    )

    assert result["success"] is True
    assert result["context"]["count"] == 1
    assert result["context"]["assets"][0]["name"] == "hero"


def test_search_assets_non_recursive_skips_subdirs(tmp_path):
    sub = tmp_path / "sub"
    sub.mkdir()
    (tmp_path / "root.fbx").write_bytes(b"FBX")
    (sub / "nested.fbx").write_bytes(b"FBX")

    result = load_and_call(
        "maya-asset-source/scripts/search_assets.py",
        MagicMock(),
        "main",
        root_dir=str(tmp_path),
        recursive=False,
    )

    assert result["success"] is True
    assert result["context"]["count"] == 1
    assert result["context"]["assets"][0]["name"] == "root"


def test_search_assets_max_results_cap(tmp_path):
    for i in range(10):
        (tmp_path / "mesh_{:02d}.fbx".format(i)).write_bytes(b"FBX")

    result = load_and_call(
        "maya-asset-source/scripts/search_assets.py",
        MagicMock(),
        "main",
        root_dir=str(tmp_path),
        max_results=3,
    )

    assert result["success"] is True
    assert result["context"]["count"] == 3
    assert len(result["context"]["assets"]) == 3


def test_search_assets_returns_error_for_missing_dir(tmp_path):
    missing = str(tmp_path / "does_not_exist")

    result = load_and_call(
        "maya-asset-source/scripts/search_assets.py",
        MagicMock(),
        "main",
        root_dir=missing,
    )

    assert result["success"] is False
    assert "not a directory" in result["message"].lower() or "not found" in result["message"].lower()


def test_search_assets_descriptor_has_required_fields(tmp_path):
    (tmp_path / "prop.fbx").write_bytes(b"FBX" * 100)

    result = load_and_call(
        "maya-asset-source/scripts/search_assets.py",
        MagicMock(),
        "main",
        root_dir=str(tmp_path),
    )

    assert result["success"] is True
    descriptor = result["context"]["assets"][0]
    assert "id" in descriptor
    assert "name" in descriptor
    assert "path" in descriptor
    assert "format" in descriptor
    assert "size_bytes" in descriptor
    assert descriptor["size_bytes"] > 0
    # Path must use forward slashes
    assert "\\" not in descriptor["path"]


def test_search_assets_usd_formats_detected(tmp_path):
    (tmp_path / "scene.usd").write_bytes(b"PXR-USDC")
    (tmp_path / "scene_text.usda").write_bytes(b"#usda")
    (tmp_path / "scene_bin.usdc").write_bytes(b"PXR-USDC")

    result = load_and_call(
        "maya-asset-source/scripts/search_assets.py",
        MagicMock(),
        "main",
        root_dir=str(tmp_path),
    )

    assert result["success"] is True
    formats = {a["format"] for a in result["context"]["assets"]}
    assert "usd" in formats
    assert "usda" in formats
    assert "usdc" in formats


# ---------------------------------------------------------------------------
# resolve_asset
# ---------------------------------------------------------------------------

def test_resolve_asset_returns_descriptor_for_fbx(tmp_path):
    path = tmp_path / "hero.fbx"
    path.write_bytes(b"FBX" * 50)

    result = load_and_call(
        "maya-asset-source/scripts/resolve_asset.py",
        MagicMock(),
        "main",
        path=str(path),
    )

    assert result["success"] is True
    descriptor = result["context"]["asset"]
    assert descriptor["name"] == "hero"
    assert descriptor["format"] == "fbx"
    assert descriptor["size_bytes"] == len(b"FBX" * 50)
    assert "\\" not in descriptor["path"]


def test_resolve_asset_returns_error_for_missing_file(tmp_path):
    missing = str(tmp_path / "ghost.fbx")

    result = load_and_call(
        "maya-asset-source/scripts/resolve_asset.py",
        MagicMock(),
        "main",
        path=missing,
    )

    assert result["success"] is False
    assert "not found" in result["message"].lower() or "does not exist" in result["message"].lower()


def test_resolve_asset_returns_error_for_unsupported_extension(tmp_path):
    path = tmp_path / "data.xyz"
    path.write_bytes(b"data")

    result = load_and_call(
        "maya-asset-source/scripts/resolve_asset.py",
        MagicMock(),
        "main",
        path=str(path),
    )

    assert result["success"] is False
    assert "unsupported" in result["message"].lower() or "not supported" in result["message"].lower()


def test_resolve_asset_returns_error_for_empty_path():
    result = load_and_call(
        "maya-asset-source/scripts/resolve_asset.py",
        MagicMock(),
        "main",
        path="",
    )

    assert result["success"] is False


def test_resolve_asset_id_is_stable_for_same_path(tmp_path):
    path = tmp_path / "prop.obj"
    path.write_bytes(b"OBJ")

    r1 = load_and_call("maya-asset-source/scripts/resolve_asset.py", MagicMock(), "main", path=str(path))
    r2 = load_and_call("maya-asset-source/scripts/resolve_asset.py", MagicMock(), "main", path=str(path))

    assert r1["success"] is True
    assert r2["success"] is True
    assert r1["context"]["asset"]["id"] == r2["context"]["asset"]["id"]


def test_resolve_asset_obj_format(tmp_path):
    path = tmp_path / "mesh.obj"
    path.write_bytes(b"OBJ")

    result = load_and_call("maya-asset-source/scripts/resolve_asset.py", MagicMock(), "main", path=str(path))

    assert result["success"] is True
    assert result["context"]["asset"]["format"] == "obj"


def test_resolve_asset_usd_format(tmp_path):
    path = tmp_path / "level.usd"
    path.write_bytes(b"PXR")

    result = load_and_call("maya-asset-source/scripts/resolve_asset.py", MagicMock(), "main", path=str(path))

    assert result["success"] is True
    assert result["context"]["asset"]["format"] == "usd"
