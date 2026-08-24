"""Behavior regressions for typed Maya texture binding."""

from __future__ import annotations

from pathlib import Path

import yaml
from conftest import load_and_call

SKILL_ROOT = Path(__file__).parents[1] / "src" / "dcc_mcp_maya" / "skills" / "maya-material-library"


class _TextureGraphCmds:
    def __init__(self):
        self.node_types = {"heroMat": "aiStandardSurface"}
        self.attrs = {}
        self.connections = {}
        self.deleted = []
        self.dirty = []

    def objExists(self, name):
        node = name.split(".", 1)[0]
        return node in self.node_types

    def nodeType(self, name):
        return self.node_types[name]

    def shadingNode(self, node_type, **kwargs):
        name = kwargs["name"]
        self.node_types[name] = node_type
        return name

    def createNode(self, node_type, **kwargs):
        name = kwargs["name"]
        self.node_types[name] = node_type
        return name

    def setAttr(self, attr, *values, **_kwargs):
        self.attrs[attr] = values[0] if len(values) == 1 else tuple(values)

    def getAttr(self, attr):
        return self.attrs[attr]

    def connectAttr(self, source, destination, **_kwargs):
        self.connections[destination] = source

    def isConnected(self, source, destination):
        return self.connections.get(destination) == source

    def listConnections(self, plug, **_kwargs):
        source = self.connections.get(plug)
        return [source.split(".", 1)[0]] if source else []

    def delete(self, nodes):
        for node in nodes if isinstance(nodes, list) else [nodes]:
            self.deleted.append(node)
            self.node_types.pop(node, None)

    def dgdirty(self, node):
        self.dirty.append(node)


def test_assign_texture_binds_base_color_with_srgb_and_native_readback(tmp_path):
    texture = tmp_path / "hero_basecolor.png"
    texture.write_bytes(b"png")
    cmds = _TextureGraphCmds()

    result = load_and_call(
        "maya-material-library/scripts/assign_texture.py",
        cmds,
        "main",
        material_name="heroMat",
        texture_path=str(texture),
        slot="base_color",
        color_space="auto",
        udim_mode="off",
    )

    assert result["success"] is True, result
    context = result["context"]
    assert context["material"] == "heroMat"
    assert context["slot"] == "base_color"
    assert context["color_space"] == "sRGB"
    assert context["udim_mode"] == "off"
    assert context["verified"] is True
    assert cmds.connections["heroMat.baseColor"] == "heroMat_base_color_file.outColor"
    assert cmds.attrs["heroMat_base_color_file.fileTextureName"] == str(texture.resolve())
    assert cmds.attrs["heroMat_base_color_file.colorSpace"] == "sRGB"


def test_assign_texture_binds_roughness_as_raw_scalar_data(tmp_path):
    texture = tmp_path / "hero_roughness.png"
    texture.write_bytes(b"png")
    cmds = _TextureGraphCmds()

    result = load_and_call(
        "maya-material-library/scripts/assign_texture.py",
        cmds,
        "main",
        material_name="heroMat",
        texture_path=str(texture),
        slot="roughness",
        color_space="auto",
        udim_mode="off",
    )

    assert result["success"] is True, result
    assert result["context"]["color_space"] == "Raw"
    assert cmds.connections["heroMat.specularRoughness"] == "heroMat_roughness_file.outAlpha"
    assert cmds.attrs["heroMat_roughness_file.alphaIsLuminance"] is True


def test_assign_texture_routes_raw_normal_map_through_arnold_normal_node(tmp_path):
    texture = tmp_path / "hero_normal.png"
    texture.write_bytes(b"png")
    cmds = _TextureGraphCmds()

    result = load_and_call(
        "maya-material-library/scripts/assign_texture.py",
        cmds,
        "main",
        material_name="heroMat",
        texture_path=str(texture),
        slot="normal",
        color_space="auto",
        udim_mode="off",
    )

    assert result["success"] is True, result
    assert result["context"]["color_space"] == "Raw"
    assert result["context"]["utility_node"] == "heroMat_normal_normal"
    assert cmds.node_types["heroMat_normal_normal"] == "aiNormalMap"
    assert cmds.connections["heroMat_normal_normal.input"] == "heroMat_normal_file.outColor"
    assert cmds.connections["heroMat.normalCamera"] == "heroMat_normal_normal.outValue"


def test_assign_texture_binds_udim_pattern_without_resolving_the_tokenized_filename(tmp_path, monkeypatch):
    (tmp_path / "hero_basecolor.1001.exr").write_bytes(b"tile-1001")
    (tmp_path / "hero_basecolor.1002.exr").write_bytes(b"tile-1002")
    pattern = tmp_path / "hero_basecolor.<UDIM>.exr"
    expected_pattern = str(pattern.parent.resolve() / pattern.name)
    cmds = _TextureGraphCmds()
    original_resolve = Path.resolve

    def reject_tokenized_resolve(path, *args, **kwargs):
        if "<UDIM>" in path.name:
            raise OSError("tokenized filenames cannot be resolved on older Windows Python")
        return original_resolve(path, *args, **kwargs)

    monkeypatch.setattr(Path, "resolve", reject_tokenized_resolve)

    result = load_and_call(
        "maya-material-library/scripts/assign_texture.py",
        cmds,
        "main",
        material_name="heroMat",
        texture_path=str(pattern),
        slot="base_color",
        color_space="auto",
        udim_mode="udim",
    )

    assert result["success"] is True, result
    assert result["context"]["udim_mode"] == "udim"
    assert result["context"]["tile_count"] == 2
    assert cmds.attrs["heroMat_base_color_file.uvTilingMode"] == 3
    assert cmds.attrs["heroMat_base_color_file.fileTextureName"] == expected_pattern


def test_assign_texture_fails_before_mutation_when_slot_is_already_connected(tmp_path):
    texture = tmp_path / "hero_basecolor.png"
    texture.write_bytes(b"png")
    cmds = _TextureGraphCmds()
    cmds.node_types["existingFile"] = "file"
    cmds.connections["heroMat.baseColor"] = "existingFile.outColor"

    result = load_and_call(
        "maya-material-library/scripts/assign_texture.py",
        cmds,
        "main",
        material_name="heroMat",
        texture_path=str(texture),
        slot="base_color",
    )

    assert result["success"] is False
    assert result["context"]["existing_sources"] == ["existingFile"]
    assert set(cmds.node_types) == {"heroMat", "existingFile"}
    assert cmds.deleted == []


def test_reload_textures_reissues_native_paths_and_reports_disk_evidence(tmp_path):
    texture = tmp_path / "hero_basecolor.png"
    texture.write_bytes(b"regenerated-png")
    cmds = _TextureGraphCmds()
    cmds.node_types["hero_base_file"] = "file"
    cmds.attrs["hero_base_file.fileTextureName"] = str(texture.resolve())
    cmds.attrs["hero_base_file.uvTilingMode"] = 0

    result = load_and_call(
        "maya-material-library/scripts/reload_textures.py",
        cmds,
        "main",
        texture_nodes=["hero_base_file"],
    )

    assert result["success"] is True, result
    assert result["context"]["reloaded_count"] == 1
    assert result["context"]["verified"] is True
    assert result["context"]["textures"] == [
        {
            "node": "hero_base_file",
            "texture_path": str(texture.resolve()),
            "udim_mode": "off",
            "tile_count": 1,
            "bytes": len(b"regenerated-png"),
            "mtime_ns": texture.stat().st_mtime_ns,
        }
    ]
    assert cmds.dirty == ["hero_base_file"]


def test_reload_textures_reports_aggregate_udim_disk_evidence(tmp_path, monkeypatch):
    tile_1001 = tmp_path / "hero_basecolor.1001.exr"
    tile_1002 = tmp_path / "hero_basecolor.1002.exr"
    tile_1001.write_bytes(b"tile-1001")
    tile_1002.write_bytes(b"tile-1002-more")
    pattern = tmp_path / "hero_basecolor.<UDIM>.exr"
    expected_pattern = str(pattern.parent.resolve() / pattern.name)
    original_resolve = Path.resolve

    def reject_tokenized_resolve(path, *args, **kwargs):
        if "<UDIM>" in path.name:
            raise OSError("tokenized filenames cannot be resolved on older Windows Python")
        return original_resolve(path, *args, **kwargs)

    monkeypatch.setattr(Path, "resolve", reject_tokenized_resolve)
    cmds = _TextureGraphCmds()
    cmds.node_types["hero_udim_file"] = "file"
    cmds.attrs["hero_udim_file.fileTextureName"] = expected_pattern
    cmds.attrs["hero_udim_file.uvTilingMode"] = 3

    result = load_and_call(
        "maya-material-library/scripts/reload_textures.py",
        cmds,
        "main",
        texture_nodes=["hero_udim_file"],
    )

    assert result["success"] is True, result
    texture = result["context"]["textures"][0]
    assert texture["udim_mode"] == "udim"
    assert texture["tile_count"] == 2
    assert texture["bytes"] == tile_1001.stat().st_size + tile_1002.stat().st_size
    assert texture["mtime_ns"] == max(tile_1001.stat().st_mtime_ns, tile_1002.stat().st_mtime_ns)


def test_repath_textures_preserves_relative_paths_and_reads_back_every_write(tmp_path):
    old_root = tmp_path / "old"
    new_root = tmp_path / "new"
    old_texture = old_root / "maps" / "hero_basecolor.png"
    new_texture = new_root / "maps" / "hero_basecolor.png"
    old_texture.parent.mkdir(parents=True)
    new_texture.parent.mkdir(parents=True)
    old_texture.write_bytes(b"old")
    new_texture.write_bytes(b"new")
    cmds = _TextureGraphCmds()
    cmds.node_types["hero_base_file"] = "file"
    cmds.attrs["hero_base_file.fileTextureName"] = str(old_texture.resolve())
    cmds.attrs["hero_base_file.uvTilingMode"] = 0

    result = load_and_call(
        "maya-material-library/scripts/repath_textures.py",
        cmds,
        "main",
        texture_nodes=["hero_base_file"],
        old_root=str(old_root),
        new_root=str(new_root),
    )

    assert result["success"] is True, result
    assert result["context"]["changed_count"] == 1
    assert result["context"]["verified"] is True
    assert result["context"]["changes"] == [
        {
            "node": "hero_base_file",
            "previous_path": str(old_texture.resolve()),
            "texture_path": str(new_texture.resolve()),
            "udim_mode": "off",
            "tile_count": 1,
        }
    ]
    assert cmds.attrs["hero_base_file.fileTextureName"] == str(new_texture.resolve())


def test_repath_textures_rolls_back_all_paths_after_partial_readback_failure(tmp_path):
    old_root = tmp_path / "old"
    new_root = tmp_path / "new"
    old_root.mkdir()
    new_root.mkdir()
    old_paths = [old_root / "base.png", old_root / "rough.png"]
    new_paths = [new_root / "base.png", new_root / "rough.png"]
    for path in old_paths + new_paths:
        path.write_bytes(path.name.encode("ascii"))

    cmds = _TextureGraphCmds()
    for node, path in zip(["base_file", "rough_file"], old_paths):
        cmds.node_types[node] = "file"
        cmds.attrs["{}.fileTextureName".format(node)] = str(path.resolve())
        cmds.attrs["{}.uvTilingMode".format(node)] = 0
    original_set_attr = cmds.setAttr
    failed = {"once": False}

    def _mismatch_second_write(attr, *values, **kwargs):
        if attr == "rough_file.fileTextureName" and values[0] == str(new_paths[1].resolve()) and not failed["once"]:
            failed["once"] = True
            cmds.attrs[attr] = "readback-mismatch"
            return
        original_set_attr(attr, *values, **kwargs)

    cmds.setAttr = _mismatch_second_write
    result = load_and_call(
        "maya-material-library/scripts/repath_textures.py",
        cmds,
        "main",
        texture_nodes=["base_file", "rough_file"],
        old_root=str(old_root),
        new_root=str(new_root),
    )

    assert result["success"] is False
    assert result["context"]["rollback_succeeded"] is True
    assert cmds.attrs["base_file.fileTextureName"] == str(old_paths[0].resolve())
    assert cmds.attrs["rough_file.fileTextureName"] == str(old_paths[1].resolve())
    assert cmds.dirty == ["base_file", "rough_file", "rough_file", "base_file"]


def test_texture_management_tools_are_typed_and_discoverable():
    manifest = yaml.safe_load((SKILL_ROOT / "tools.yaml").read_text(encoding="utf-8"))
    tools = {tool["name"]: tool for tool in manifest["tools"]}

    assert tools["assign_texture"]["source_file"] == "scripts/assign_texture.py"
    assert tools["assign_texture"]["input_schema"]["properties"]["slot"]["enum"] == [
        "base_color",
        "roughness",
        "normal",
    ]
    assert tools["assign_texture"]["output_schema"]["required"] == [
        "material",
        "material_type",
        "slot",
        "destination_attr",
        "texture_node",
        "place2d_node",
        "utility_node",
        "texture_path",
        "color_space",
        "udim_mode",
        "tile_count",
        "verified",
    ]
    assert tools["reload_textures"]["input_schema"]["properties"]["texture_nodes"]["maxItems"] == 64
    assert tools["reload_textures"]["output_schema"]["properties"]["verified"]["const"] is True
    assert tools["repath_textures"]["input_schema"]["additionalProperties"] is False
    assert tools["repath_textures"]["output_schema"]["properties"]["changed_count"]["maximum"] == 64
    assert all(
        tools[name]["affinity"] == "main"
        for name in tools
        if name
        in {
            "assign_texture",
            "reload_textures",
            "repath_textures",
        }
    )

    groups = yaml.safe_load((SKILL_ROOT / "groups.yaml").read_text(encoding="utf-8"))
    assert groups["groups"][0]["tools"] == [
        "assign_texture",
        "delete_material_preset",
        "list_material_presets",
        "load_material",
        "reload_textures",
        "repath_textures",
        "save_material",
    ]
