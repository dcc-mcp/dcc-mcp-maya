#!/usr/bin/env python3
"""CI lint for input_schema completeness in bundled tools.yaml files.

Fails (exit 1) when any bundled tool is missing ``input_schema`` or has
a null/empty schema that should carry properties.  Designed to catch
schema/signature drift when script entry points are updated without a
corresponding tools.yaml update.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Tuple

try:
    import yaml
except ImportError:  # pragma: no cover
    print("ERROR: PyYAML is required (pip install pyyaml)", file=sys.stderr)
    sys.exit(2)


SKILLS_ROOT = Path(__file__).resolve().parent.parent / "src" / "dcc_mcp_maya" / "skills"


def lint_file(path: Path) -> List[Tuple[str, str]]:
    """Return a list of ``(rule, message)`` for every problem in *path*."""
    problems: List[Tuple[str, str]] = []
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        return [("YAML_PARSE_ERROR", f"{path}: {exc}")]

    tools = data.get("tools")
    if not isinstance(tools, list):
        return problems

    skill_name = path.parent.name

    for tool in tools:
        if not isinstance(tool, dict):
            continue

        name = tool.get("name", "<unnamed>")

        # Every bundled tool MUST have input_schema (the MCP protocol requirement).
        schema = tool.get("input_schema")
        if schema is None:
            problems.append(
                ("MISSING_INPUT_SCHEMA", f"{skill_name}/{name}: no input_schema")
            )
            continue

        if not isinstance(schema, dict):
            problems.append(
                ("BAD_INPUT_SCHEMA_TYPE", f"{skill_name}/{name}: input_schema is not a dict")
            )
            continue

        if schema.get("type") != "object":
            problems.append(
                ("BAD_INPUT_SCHEMA_ROOT_TYPE", f"{skill_name}/{name}: input_schema.type must be 'object'")
            )
            continue

        # Check properties have valid types when present.
        for prop_name, prop_schema in (schema.get("properties") or {}).items():
            raw_type = prop_schema.get("type")
            valid_types = {"string", "number", "integer", "boolean", "array", "object", "null"}
            # type can be a single string or a list of alternatives (JSON Schema union).
            prop_types = raw_type if isinstance(raw_type, list) else [raw_type] if raw_type else []
            for pt in prop_types:
                if pt not in valid_types:
                    # oneOf/anyOf/enum patterns are also valid without a direct "type".
                    if "oneOf" not in prop_schema and "anyOf" not in prop_schema and "enum" not in prop_schema:
                        problems.append(
                            ("UNKNOWN_PROP_TYPE", f"{skill_name}/{name}.{prop_name}: unknown type '{pt}'")
                        )

            # Required fields must appear in properties (non-empty properties only).
            one_of = prop_schema.get("oneOf", [])
            for variant in one_of:
                vt = variant.get("type")
                if vt and vt not in valid_types:
                    problems.append(
                        ("UNKNOWN_ONEOF_TYPE", f"{skill_name}/{name}.{prop_name}: oneOf has unknown type '{vt}'")
                    )

        # Check required fields are declared.
        required = schema.get("required", [])
        properties = schema.get("properties", {})
        for req in required:
            if req not in properties:
                problems.append(
                    ("REQUIRED_NOT_IN_PROPERTIES", f"{skill_name}/{name}: required field '{req}' missing from properties")
                )

    return problems


def main() -> None:
    parser = argparse.ArgumentParser(description="Lint input_schema completeness for all bundled tools.")
    parser.add_argument(
        "--error-only",
        action="store_true",
        help="Only print errors, skip warnings",
    )
    options = parser.parse_args()

    all_problems: List[Tuple[str, str]] = []
    for tools_yaml in sorted(SKILLS_ROOT.glob("*/tools.yaml")):
        all_problems.extend(lint_file(tools_yaml))

    if not all_problems:
        print("All tools have valid input_schema.")
        sys.exit(0)

    errors = [p for p in all_problems if p[0] != "WARNING"]
    warnings = [p for p in all_problems if p[0] == "WARNING"]

    for rule, msg in all_problems:
        severity = "ERROR" if rule != "WARNING" else "WARNING"
        print(f"{severity} [{rule}] {msg}")

    if options.error_only and errors:
        sys.exit(1)
    if errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
