"""Contract tests for the Maya texture baking skill."""

from __future__ import annotations

import inspect
from pathlib import Path

import yaml
from conftest import load_and_call


def test_bake_textures_defaults_to_arnold() -> None:
    source = (
        Path(__file__).parents[1]
        / "src"
        / "dcc_mcp_maya"
        / "skills"
        / "maya-texture-bake"
        / "scripts"
        / "bake_textures.py"
    )
    namespace = {}
    exec(compile(source.read_text(encoding="utf-8"), str(source), "exec"), namespace)
    assert inspect.signature(namespace["bake_textures"]).parameters["renderer"].default == "arnold"


def test_bake_textures_rejects_removed_mentalray() -> None:
    result = load_and_call(
        "maya-texture-bake/scripts/bake_textures.py",
        object(),
        "main",
        objects=["mesh"],
        file_path="/tmp/bake",
        renderer="mentalRay",
    )
    assert result["success"] is False
    assert "Invalid renderer" in result["message"]


def test_bake_textures_schema_only_advertises_arnold() -> None:
    tools_path = Path(__file__).parents[1] / "src" / "dcc_mcp_maya" / "skills" / "maya-texture-bake" / "tools.yaml"
    tools = yaml.safe_load(tools_path.read_text(encoding="utf-8"))["tools"]
    tool = next(item for item in tools if item["name"] == "bake_textures")
    assert tool["input_schema"]["properties"]["renderer"]["enum"] == ["arnold"]
    assert tool["input_schema"]["properties"]["renderer"]["default"] == "arnold"
