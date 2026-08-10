"""Unit tests for the maya-attributes skill contract."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import yaml
from conftest import load_and_call


def _value_schema() -> dict:
    tools_path = Path(__file__).parents[1] / "src" / "dcc_mcp_maya" / "skills" / "maya-attributes" / "tools.yaml"
    tools = yaml.safe_load(tools_path.read_text(encoding="utf-8"))["tools"]
    tool = next(item for item in tools if item["name"] == "set_attribute")
    return tool["input_schema"]["properties"]["value"]


def test_set_attribute_schema_accepts_native_json_value_types():
    options = _value_schema()["oneOf"]

    assert {option.get("type") for option in options} == {"array", "boolean", "number", "string"}


def test_set_attribute_passes_boolean_without_string_coercion():
    cmds = MagicMock()
    cmds.objExists.return_value = True

    result = load_and_call(
        "maya-attributes/scripts/set_attribute.py",
        cmds,
        "main",
        node_name="defaultArnoldRenderOptions",
        attribute="log_to_file",
        value=True,
    )

    assert result["success"] is True, result
    cmds.setAttr.assert_called_once_with("defaultArnoldRenderOptions.log_to_file", True)
