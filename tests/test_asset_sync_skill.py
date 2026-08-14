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
