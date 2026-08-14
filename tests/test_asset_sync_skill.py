"""Contract tests for native-editable and fidelity-first Maya Asset Sync."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
import yaml

_ROOT = Path(__file__).parents[1]
_SKILL = _ROOT / "src" / "dcc_mcp_maya" / "skills" / "maya-asset-sync"


def _module():
    spec = importlib.util.spec_from_file_location("maya_asset_sync_test", _SKILL / "scripts" / "asset_sync.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_source_name_is_confined_to_operator_root(tmp_path: Path) -> None:
    module = _module()
    assert module._safe_relative(tmp_path, "exports/bee.usdc") == tmp_path / "exports" / "bee.usdc"
    with pytest.raises(ValueError, match="safe relative"):
        module._safe_relative(tmp_path, "../secret.usdc")
    with pytest.raises(ValueError, match="safe relative"):
        module._safe_relative(tmp_path, str(tmp_path / "absolute.usdc"))


def test_sync_schema_exposes_deliberate_editability_modes() -> None:
    tools = yaml.safe_load((_SKILL / "tools.yaml").read_text(encoding="utf-8"))["tools"]
    by_name = {tool["name"]: tool for tool in tools}
    assert set(by_name) == {"publish_usd_revision", "read_asset_head", "sync_usd_revision"}
    sync_schema = by_name["sync_usd_revision"]["input_schema"]
    assert sync_schema["additionalProperties"] is False
    assert sync_schema["properties"]["editability_mode"]["enum"] == ["native", "usd_proxy"]
    assert sync_schema["properties"]["rig_expectation"]["enum"] == ["auto", "ignore", "skeleton", "skinned"]
    publish_properties = by_name["publish_usd_revision"]["input_schema"]["properties"]
    assert "source_name" in publish_properties
    assert "source_path" not in publish_properties
    assert "store_root" not in publish_properties


def test_native_sync_reports_arnold_pbr_evidence() -> None:
    source = (_SKILL / "scripts" / "asset_sync.py").read_text(encoding="utf-8")
    assert '"preferredMaterial": "standardSurface"' in source
    assert '"arnold_standard_surface_materials"' in source
    assert '"pbr_materials"' in source
    assert '"specular_ior"' in source
    assert '"connected_inputs"' in source
    assert '"image_textures"' in source
    assert '"image_texture_evidence_truncated"' in source


def test_image_texture_evidence_reports_paths_color_spaces_and_material_inputs(tmp_path: Path) -> None:
    module = _module()
    source_image = tmp_path / "sourceimages" / "bee" / "albedo.png"
    source_image.parent.mkdir(parents=True)
    source_image.write_bytes(b"texture")
    normal_image = tmp_path / "normal.exr"
    normal_image.write_bytes(b"texture")

    class FakeCmds:
        types = {
            "BeeAlbedo": "file",
            "BeeColorCorrect": "aiColorCorrect",
            "BeeNormal": "aiImage",
            "BeeNormalMap": "aiNormalMap",
            "BeeMat": "standardSurface",
        }
        attrs = {
            "BeeAlbedo.fileTextureName": "bee/albedo.png",
            "BeeAlbedo.colorSpace": "sRGB",
            "BeeNormal.filename": str(normal_image),
            "BeeNormal.colorSpace": "Raw",
        }
        downstream = {
            "BeeAlbedo": ["BeeAlbedo.outColor", "BeeColorCorrect.input"],
            "BeeColorCorrect": ["BeeColorCorrect.outColor", "BeeMat.baseColor"],
            "BeeNormal": ["BeeNormal.outColor", "BeeNormalMap.input"],
            "BeeNormalMap": ["BeeNormalMap.outValue", "BeeMat.normalCamera"],
        }

        @classmethod
        def ls(cls, materials=False, **_kwargs):
            return ["BeeMat"] if materials else []

        @classmethod
        def nodeType(cls, node):
            return cls.types[node]

        @classmethod
        def getAttr(cls, plug):
            if plug not in cls.attrs:
                raise RuntimeError(plug)
            return cls.attrs[plug]

        @classmethod
        def workspace(cls, query=False, rootDirectory=False, fileRuleEntry=None):
            if query and rootDirectory:
                return str(tmp_path)
            if fileRuleEntry == "sourceImages":
                return "sourceimages"
            raise AssertionError((query, rootDirectory, fileRuleEntry))

        @classmethod
        def listConnections(cls, node, **kwargs):
            assert kwargs == {
                "source": False,
                "destination": True,
                "plugs": True,
                "connections": True,
            }
            return cls.downstream.get(node, [])

        @classmethod
        def objectType(cls, _node, isAType=None):
            assert isAType == "dagNode"
            return False

    imported = {"BeeAlbedo", "BeeColorCorrect", "BeeNormal", "BeeNormalMap", "BeeMat"}
    result = module._image_texture_evidence(FakeCmds, ["BeeNormal", "BeeAlbedo"], imported)

    assert result == {
        "records": [
            {
                "node": "BeeAlbedo",
                "type": "file",
                "path": "bee/albedo.png",
                "path_attr": "fileTextureName",
                "exists": True,
                "color_space": "sRGB",
                "is_absolute": False,
                "workspace_relative_path": "sourceimages/bee/albedo.png",
                "under_workspace": True,
                "imported": True,
                "connected_material_inputs": [
                    {
                        "material": "BeeMat",
                        "input": "baseColor",
                        "plug": "BeeMat.baseColor",
                        "direct": False,
                        "via": ["BeeColorCorrect"],
                        "material_imported": True,
                    }
                ],
                "connections_truncated": False,
            },
            {
                "node": "BeeNormal",
                "type": "aiImage",
                "path": str(normal_image),
                "path_attr": "filename",
                "exists": True,
                "color_space": "Raw",
                "is_absolute": True,
                "workspace_relative_path": "normal.exr",
                "under_workspace": True,
                "imported": True,
                "connected_material_inputs": [
                    {
                        "material": "BeeMat",
                        "input": "normalCamera",
                        "plug": "BeeMat.normalCamera",
                        "direct": False,
                        "via": ["BeeNormalMap"],
                        "material_imported": True,
                    }
                ],
                "connections_truncated": False,
            },
        ],
        "total": 2,
        "limit": module._IMAGE_TEXTURE_EVIDENCE_LIMIT,
        "truncated": False,
    }


def test_image_texture_evidence_is_bounded_and_prioritizes_imported_nodes(monkeypatch) -> None:
    module = _module()
    monkeypatch.setattr(module, "_IMAGE_TEXTURE_EVIDENCE_LIMIT", 2)

    class FakeCmds:
        @staticmethod
        def ls(materials=False, **_kwargs):
            return []

        @staticmethod
        def nodeType(_node):
            return "file"

        @staticmethod
        def getAttr(plug):
            if plug.endswith(".fileTextureName"):
                return ""
            if plug.endswith(".colorSpace"):
                return "Raw"
            raise RuntimeError(plug)

        @staticmethod
        def workspace(**_kwargs):
            raise RuntimeError("workspace unavailable")

        @staticmethod
        def listConnections(_node, **_kwargs):
            return []

    result = module._image_texture_evidence(FakeCmds, ["OldB", "New", "OldA"], {"New"})

    assert [record["node"] for record in result["records"]] == ["New", "OldA"]
    assert result["total"] == 3
    assert result["limit"] == 2
    assert result["truncated"] is True


def test_image_texture_evidence_marks_external_absolute_path_outside_workspace(tmp_path: Path) -> None:
    module = _module()
    external_root = tmp_path.parent / f"{tmp_path.name}_external"
    external_root.mkdir()
    external_texture = external_root / "normal.exr"
    external_texture.write_bytes(b"texture")

    class FakeCmds:
        @staticmethod
        def ls(materials=False, **_kwargs):
            return []

        @staticmethod
        def nodeType(_node):
            return "aiImage"

        @staticmethod
        def getAttr(plug):
            if plug.endswith(".filename"):
                return str(external_texture)
            if plug.endswith(".colorSpace"):
                return "Raw"
            raise RuntimeError(plug)

        @staticmethod
        def workspace(query=False, rootDirectory=False, fileRuleEntry=None):
            if query and rootDirectory:
                return str(tmp_path)
            if fileRuleEntry == "sourceImages":
                return "sourceimages"
            raise AssertionError((query, rootDirectory, fileRuleEntry))

        @staticmethod
        def listConnections(_node, **_kwargs):
            return []

    result = module._image_texture_evidence(FakeCmds, ["ExternalNormal"], {"ExternalNormal"})
    record = result["records"][0]

    assert record["exists"] is True
    assert record["is_absolute"] is True
    assert record["workspace_relative_path"] is None
    assert record["under_workspace"] is False


def test_texture_existence_accepts_common_udim_tokens(tmp_path: Path) -> None:
    module = _module()
    (tmp_path / "bee_albedo.1001.exr").write_bytes(b"texture")

    assert module._path_or_sequence_exists(tmp_path / "bee_albedo.<UDIM>.exr") is True
    assert module._path_or_sequence_exists(tmp_path / "missing.<UDIM>.exr") is False


def test_native_sync_audits_standard_rig_preservation() -> None:
    source = (_SKILL / "scripts" / "asset_sync.py").read_text(encoding="utf-8")
    tools = (_SKILL / "tools.yaml").read_text(encoding="utf-8")
    assert "def _usd_rig_evidence" in source
    assert '"skin_clusters": count_type("skinCluster")' in source
    assert 'rig_expectation: str = "auto"' in source
    assert 'evidence["joints"] == 0' in source
    assert 'evidence["skin_clusters"] == 0' in source
    assert "rig_expectation:" in tools
    assert "- skinned" in tools


def test_maya_namespace_uses_host_context_and_restores_it() -> None:
    module = _module()

    class FakeCmds:
        current = ":"
        namespaces = set()
        calls = []

        @classmethod
        def namespaceInfo(cls, currentNamespace=False):
            assert currentNamespace
            return cls.current

        @classmethod
        def namespace(cls, **kwargs):
            if "exists" in kwargs:
                return kwargs["exists"] in cls.namespaces
            if "add" in kwargs:
                cls.namespaces.add(kwargs["add"])
                cls.calls.append(("add", kwargs["add"]))
                return kwargs["add"]
            if "set" in kwargs:
                cls.current = kwargs["set"]
                cls.calls.append(("set", kwargs["set"]))
                return kwargs["set"]
            raise AssertionError(kwargs)

    with module._maya_namespace(FakeCmds, "HB18"):
        assert FakeCmds.current == "HB18"
    assert FakeCmds.current == ":"
    assert FakeCmds.calls == [("add", "HB18"), ("set", "HB18"), ("set", ":")]


def test_maya_namespace_restores_after_import_failure() -> None:
    module = _module()

    class FakeCmds:
        current = ":root"

        @classmethod
        def namespaceInfo(cls, currentNamespace=False):
            return cls.current

        @classmethod
        def namespace(cls, **kwargs):
            if "exists" in kwargs:
                return True
            if "set" in kwargs:
                cls.current = kwargs["set"]
                return cls.current
            raise AssertionError(kwargs)

    with pytest.raises(RuntimeError, match="import failed"):
        with module._maya_namespace(FakeCmds, "bee"):
            raise RuntimeError("import failed")
    assert FakeCmds.current == ":root"
