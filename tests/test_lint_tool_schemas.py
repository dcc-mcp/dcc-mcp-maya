"""Unit tests for tools/lint_tool_schemas.py."""

from __future__ import annotations

import sys
from pathlib import Path

# Make tools/ importable
sys.path.insert(0, str(Path(__file__).parent.parent / "tools"))
import lint_tool_schemas  # noqa: E402
import yaml  # noqa: E402


def _make_tools_yaml(tmp_path: Path, tools: list[dict]) -> Path:
    """Create a temporary tools.yaml and return its path."""
    path = tmp_path / "skills" / "maya-test"
    path.mkdir(parents=True)
    yaml_path = path / "tools.yaml"
    yaml_path.write_text(yaml.dump({"tools": tools}), encoding="utf-8")
    return yaml_path


class TestLintToolSchemas:
    def test_valid_schema_passes(self, tmp_path):
        tools = [
            {
                "name": "do_stuff",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "count": {"type": "integer", "default": 1},
                    },
                    "required": ["name"],
                },
            }
        ]
        path = _make_tools_yaml(tmp_path, tools)
        issues = lint_tool_schemas.lint_file(path)
        assert issues == []

    def test_valid_empty_params_schema_passes(self, tmp_path):
        tools = [
            {
                "name": "no_params",
                "input_schema": {"type": "object", "additionalProperties": False},
            }
        ]
        path = _make_tools_yaml(tmp_path, tools)
        issues = lint_tool_schemas.lint_file(path)
        assert issues == []

    def test_valid_nullable_union_type_passes(self, tmp_path):
        tools = [
            {
                "name": "find_by_pattern",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "pattern": {"type": "string"},
                        "type": {"type": ["string", "null"], "default": "transform"},
                    },
                    "required": ["pattern"],
                },
            }
        ]
        path = _make_tools_yaml(tmp_path, tools)
        issues = lint_tool_schemas.lint_file(path)
        assert issues == []

    def test_missing_input_schema(self, tmp_path):
        tools = [{"name": "no_schema"}]
        path = _make_tools_yaml(tmp_path, tools)
        issues = lint_tool_schemas.lint_file(path)
        assert any(rule == "MISSING_INPUT_SCHEMA" for rule, _ in issues)

    def test_null_input_schema(self, tmp_path):
        tools = [{"name": "null_schema", "input_schema": None}]
        path = _make_tools_yaml(tmp_path, tools)
        issues = lint_tool_schemas.lint_file(path)
        assert any(rule == "MISSING_INPUT_SCHEMA" for rule, _ in issues)

    def test_non_dict_input_schema(self, tmp_path):
        tools = [{"name": "bad_schema", "input_schema": "not a dict"}]
        path = _make_tools_yaml(tmp_path, tools)
        issues = lint_tool_schemas.lint_file(path)
        assert any(rule == "BAD_INPUT_SCHEMA_TYPE" for rule, _ in issues)

    def test_wrong_root_type(self, tmp_path):
        tools = [
            {
                "name": "wrong_type",
                "input_schema": {
                    "type": "array",
                    "items": {"type": "string"},
                },
            }
        ]
        path = _make_tools_yaml(tmp_path, tools)
        issues = lint_tool_schemas.lint_file(path)
        assert any(rule == "BAD_INPUT_SCHEMA_ROOT_TYPE" for rule, _ in issues)

    def test_required_not_in_properties(self, tmp_path):
        tools = [
            {
                "name": "bad_required",
                "input_schema": {
                    "type": "object",
                    "properties": {"name": {"type": "string"}},
                    "required": ["name", "missing_field"],
                },
            }
        ]
        path = _make_tools_yaml(tmp_path, tools)
        issues = lint_tool_schemas.lint_file(path)
        assert any(rule == "REQUIRED_NOT_IN_PROPERTIES" for rule, _ in issues)

    def test_valid_oneof_property_passes(self, tmp_path):
        tools = [
            {
                "name": "list_param",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "items": {
                            "oneOf": [
                                {"type": "string"},
                                {"type": "array", "items": {"type": "string"}, "minItems": 1},
                            ]
                        }
                    },
                },
            }
        ]
        path = _make_tools_yaml(tmp_path, tools)
        issues = lint_tool_schemas.lint_file(path)
        assert issues == []

    def test_all_bundled_tools_pass(self):
        """Integration test: all bundled skills must pass the schema linter."""
        skills_root = lint_tool_schemas.SKILLS_ROOT
        all_issues = []
        for tools_yaml in sorted(skills_root.glob("*/tools.yaml")):
            all_issues.extend(lint_tool_schemas.lint_file(tools_yaml))
        assert all_issues == [], "Schema lint issues found:\n" + "\n".join(f"  [{r}] {m}" for r, m in all_issues)
