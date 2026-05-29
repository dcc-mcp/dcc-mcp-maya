"""Tests for the maya-procedural-rig workflow skill (issue #306).

These tests are dependency-free: they do not require a running Maya. They
verify the package wiring (SKILL.md frontmatter, tools.yaml ↔ scripts ↔
groups.yaml consistency) and that every workflow script degrades to a
structured ``maya_error`` envelope — never an unhandled exception — when
``maya.cmds`` is unavailable.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Dict

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILL_DIR = REPO_ROOT / "src" / "dcc_mcp_maya" / "skills" / "maya-procedural-rig"
SCRIPTS_DIR = SKILL_DIR / "scripts"

EXPECTED_TOOLS = {
    "create_sphere_layout",
    "assign_palette_materials",
    "create_rig_joints",
    "bind_objects_to_joints",
    "keyframe_orbit_animation",
    "create_playblast",
    "export_scene_artifact",
}


def _load_yaml(name: str) -> Dict:
    return yaml.safe_load((SKILL_DIR / name).read_text(encoding="utf-8")) or {}


def _load_script_module(stem: str):
    """Import a workflow script by file path without installing the package."""
    spec = importlib.util.spec_from_file_location("procedural_rig_" + stem, SCRIPTS_DIR / (stem + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_skill_md_declares_pipeline_stage() -> None:
    import dcc_mcp_core

    meta = dcc_mcp_core.parse_skill_md(str(SKILL_DIR))
    assert meta is not None
    assert getattr(meta, "stage", None) == "pipeline"


def test_tools_match_scripts_and_groups() -> None:
    tools = {t["name"] for t in _load_yaml("tools.yaml")["tools"]}
    assert tools == EXPECTED_TOOLS

    scripts = {p.stem for p in SCRIPTS_DIR.glob("*.py")}
    assert EXPECTED_TOOLS <= scripts

    group_tools = set()
    for group in _load_yaml("groups.yaml")["groups"]:
        group_tools.update(group["tools"])
    assert group_tools == EXPECTED_TOOLS


def test_async_tools_declare_timeout_hint() -> None:
    for tool in _load_yaml("tools.yaml")["tools"]:
        if tool.get("execution") == "async":
            assert tool.get("timeout_hint_secs"), tool["name"]


@pytest.mark.parametrize(
    ("stem", "kwargs"),
    [
        ("create_sphere_layout", {"count": 3}),
        ("assign_palette_materials", {"objects": ["a", "b"]}),
        ("create_rig_joints", {"objects": ["a"]}),
        ("bind_objects_to_joints", {"objects": ["a"], "joints": ["j"]}),
        ("keyframe_orbit_animation", {"nodes": ["a"]}),
        ("create_playblast", {"output_path": "/tmp/out"}),
        ("export_scene_artifact", {"output_path": "/tmp/out"}),
    ],
)
def test_scripts_degrade_gracefully_without_maya(stem: str, kwargs: Dict) -> None:
    """Without ``maya.cmds`` every script returns a structured envelope."""
    module = _load_script_module(stem)
    func = getattr(module, stem)
    result = func(**kwargs)
    assert isinstance(result, dict)
    assert "success" in result


@pytest.mark.parametrize(
    ("stem", "kwargs"),
    [
        ("create_sphere_layout", {"layout": "bogus"}),
        ("assign_palette_materials", {"objects": ["a"], "palette": "bogus"}),
        ("bind_objects_to_joints", {"objects": ["a"], "joints": ["x", "y"]}),
        ("keyframe_orbit_animation", {"nodes": ["a"], "mode": "bogus"}),
    ],
)
def test_input_validation_rejects_bad_args(stem: str, kwargs: Dict) -> None:
    """Validation errors are caught before any maya.cmds import is attempted."""
    module = _load_script_module(stem)
    func = getattr(module, stem)
    result = func(**kwargs)
    assert result.get("success") is False
