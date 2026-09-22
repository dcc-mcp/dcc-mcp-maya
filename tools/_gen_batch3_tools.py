"""Regenerate tools.yaml for the batch-3 skills from their script signatures.

Derives JSON Schema types from the code (via :func:`typing.get_type_hints`,
because the scripts use postponed annotations) so the manifest cannot drift
from the implementation. Mirrors ``tools/_gen_render_tools.py``.
"""

from __future__ import annotations

import importlib.util
import inspect
import sys
from pathlib import Path
from typing import Any, get_type_hints

import yaml

SKILLS_ROOT = Path(__file__).resolve().parent.parent / "src" / "dcc_mcp_maya" / "skills"

SPEC = {
    "maya-plugins": {
        "list_plugins": ("sync", "main", "inventory", {"read_only_hint": True, "idempotent_hint": True}),
        "load_plugin": ("sync", "main", "lifecycle", {}),
        "unload_plugin": ("sync", "main", "lifecycle", {}),
        "diagnose_plugin": ("sync", "main", "diagnostics", {"read_only_hint": True, "idempotent_hint": True}),
        "get_plugin_path": ("sync", "main", "diagnostics", {"read_only_hint": True, "idempotent_hint": True}),
    },
    "maya-compositing": {
        "create_image_reader": ("sync", "main", "inputs", {}),
        "create_layer_stack": ("sync", "main", "stacks", {}),
        "add_comp_layer": ("sync", "main", "stacks", {}),
        "list_comp_layers": ("sync", "main", "stacks", {"read_only_hint": True, "idempotent_hint": True}),
        "remove_comp_layer": ("sync", "main", "stacks", {}),
        "merge_comp_layers": ("sync", "main", "merge", {}),
        "create_comp_node": ("sync", "main", "utility", {}),
        "connect_comp_nodes": ("sync", "main", "utility", {}),
    },
}

DESCRIPTION = {
    "list_plugins": "List Maya plug-ins with their load state and metadata.",
    "load_plugin": "Load a Maya plug-in, with an actionable error when it cannot be found.",
    "unload_plugin": "Unload a Maya plug-in, refusing when Maya reports it cannot be unloaded.",
    "diagnose_plugin": "Explain why a plug-in is or is not usable: path, load state and problems.",
    "get_plugin_path": "Report the plug-in search path and resolve a plug-in name to a file.",
    "create_image_reader": "Create a file node that reads rendered imagery from disk.",
    "create_layer_stack": "Create an empty layeredTexture stack to composite layers into.",
    "add_comp_layer": "Connect a source into the next free layer of a comp stack.",
    "list_comp_layers": "List the layers currently connected into a comp stack.",
    "remove_comp_layer": "Disconnect one layer from a comp stack, keeping its source node.",
    "merge_comp_layers": "Combine two or more sources into a single comp output.",
    "create_comp_node": "Create a reverse / multiplyDivide / luminance / clamp / setRange node.",
    "connect_comp_nodes": "Wire two comp nodes together.",
}

ENUMS = {
    "create_comp_node": {
        "node_type": ["reverse", "multiplyDivide", "plusMinusAverage", "luminance", "clamp", "setRange"],
        "operation": ["none", "multiply", "divide", "power"],
    },
    "merge_comp_layers": {"operation": ["blend", "over", "add", "multiply", "subtract", "difference"]},
    "add_comp_layer": {
        "blend_mode": [
            "None",
            "Over",
            "In",
            "Out",
            "Add",
            "Subtract",
            "Multiply",
            "Difference",
            "Lighten",
            "Darken",
            "Saturate",
            "Desaturate",
            "Illuminate",
            "CPV Modulate",
        ]
    },
}

SIMPLE_TYPES = {str: "string", int: "integer", float: "number", bool: "boolean"}


def _union_args(annotation):
    if str(getattr(annotation, "__origin__", "")).endswith("Union"):
        return annotation.__args__
    return None


def _unwrap(annotation):
    """Return (base_type, nullable) for a possibly-optional annotation."""
    args = _union_args(annotation)
    if args is not None:
        non_none = [arg for arg in args if arg is not type(None)]
        if len(non_none) == 1:
            return non_none[0], len(args) != len(non_none)
    return annotation, False


def _json_type(base):
    origin = getattr(base, "__origin__", None)
    if origin is list:
        return {"type": "array", "items": {"type": SIMPLE_TYPES.get(base.__args__[0], "string")}, "minItems": 1}
    if base is Any:
        return {}
    return {"type": SIMPLE_TYPES.get(base, "string")}


def _schema(skill, tool):
    path = SKILLS_ROOT / skill / "scripts" / "{}.py".format(tool)
    spec = importlib.util.spec_from_file_location("gen_{}_{}".format(skill, tool), path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["gen_{}_{}".format(skill, tool)] = module
    spec.loader.exec_module(module)

    hints = get_type_hints(getattr(module, tool))
    signature = inspect.signature(getattr(module, tool))

    properties, required = {}, []
    for name, param in signature.parameters.items():
        base, nullable = _unwrap(hints.get(name, str))
        prop = dict(_json_type(base))
        if nullable and prop.get("type"):
            prop["type"] = [prop["type"], "null"]
        if param.default is inspect.Parameter.empty and not nullable:
            required.append(name)
        if name in ENUMS.get(tool, {}):
            prop["enum"] = list(ENUMS[tool][name]) + ([None] if nullable else [])
        if param.default is not inspect.Parameter.empty:
            prop["default"] = param.default
        properties[name] = prop
    return {"type": "object", "properties": properties, "required": required}


def main():
    for skill, tools in SPEC.items():
        entries = []
        for tool, (execution, affinity, group, tool_annotations) in tools.items():
            entries.append(
                {
                    "name": tool,
                    "description": DESCRIPTION[tool],
                    "execution": execution,
                    "affinity": affinity,
                    "annotations": tool_annotations or {"idempotent_hint": False},
                    "group": group,
                    "input_schema": _schema(skill, tool),
                }
            )
        target = SKILLS_ROOT / skill / "tools.yaml"
        target.write_text(
            yaml.safe_dump({"tools": entries}, sort_keys=False, width=100, default_flow_style=False),
            encoding="utf-8",
        )
        print("wrote {} ({} tools)".format(target, len(entries)))
        for entry in entries:
            props = entry["input_schema"]["properties"]
            print("  {:22s} {}".format(entry["name"], {k: v.get("type") for k, v in props.items()}))


if __name__ == "__main__":
    main()
