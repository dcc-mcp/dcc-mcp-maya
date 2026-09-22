"""Regenerate maya-render-setup/tools.yaml from the skill script signatures.

Kept in ``tools/`` so the manifest can be reproduced whenever a script
signature changes, and so the JSON Schema types are derived from the code
rather than hand-maintained.

Uses :func:`typing.get_type_hints` because the scripts carry
``from __future__ import annotations``, which turns annotations into strings.
"""

from __future__ import annotations

import importlib.util
import inspect
import sys
from pathlib import Path
from typing import Any, get_type_hints

import yaml

SKILL_ROOT = Path(__file__).resolve().parent.parent / "src" / "dcc_mcp_maya" / "skills" / "maya-render-setup"

SPEC = {
    "create_render_layer": ("sync", "main", "layers", {}),
    "list_render_layers": ("sync", "main", "layers", {"read_only_hint": True, "idempotent_hint": True}),
    "set_current_render_layer": ("sync", "main", "layers", {"idempotent_hint": True}),
    "create_render_collection": ("sync", "main", "collections", {}),
    "create_render_override": ("sync", "main", "collections", {}),
    "add_aov": ("sync", "main", "aovs", {}),
    "list_aovs": ("sync", "main", "aovs", {"read_only_hint": True, "idempotent_hint": True}),
    "set_aov_enabled": ("sync", "main", "aovs", {"idempotent_hint": True}),
    "remove_aov": ("sync", "main", "aovs", {}),
    "plan_comp_outputs": ("sync", "any", "precomp", {"read_only_hint": True, "idempotent_hint": True}),
}

DESCRIPTION = {
    "create_render_layer": "Create a renderSetup render layer and optionally make it visible.",
    "list_render_layers": "List renderSetup layers, the visible layer, and legacy renderLayer nodes.",
    "set_current_render_layer": "Switch the current render layer (renderSetup or legacy).",
    "create_render_collection": "Create a renderSetup collection, or replace an existing collection's members.",
    "create_render_override": "Override an attribute for everything a renderSetup collection selects.",
    "add_aov": "Create an Arnold AOV and wire it into the render options output list.",
    "list_aovs": "List the AOVs wired into Arnold's render options.",
    "set_aov_enabled": "Enable or disable an existing Arnold AOV without disconnecting it.",
    "remove_aov": "Disconnect and delete an Arnold AOV.",
    "plan_comp_outputs": "Plan per-layer and per-AOV output paths for a compositing hand-off.",
}

ENUMS = {
    "set_current_render_layer": {"layer_system": ["render_setup", "legacy"]},
    "create_render_override": {"override_type": ["absolute", "relative", "connection"]},
    "add_aov": {"aov_type": ["int", "uint", "bool", "float", "rgb", "rgba", "vector", "vector2", "pointer"]},
}

SIMPLE_TYPES = {str: "string", int: "integer", float: "number", bool: "boolean"}


def _union_args(annotation):
    """Return the args of a Union, or None if it is not one.

    ``Optional[X]`` is ``Union[X, None]``, so its ``__origin__`` is
    ``typing.Union`` - comparing against ``Optional`` never matches.
    """
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
        inner = base.__args__[0]
        return {"type": "array", "items": {"type": SIMPLE_TYPES.get(inner, "string")}, "minItems": 1}
    if base is Any:
        return {}
    return {"type": SIMPLE_TYPES.get(base, "string")}


def _schema(tool):
    path = SKILL_ROOT / "scripts" / "{}.py".format(tool)
    spec = importlib.util.spec_from_file_location("gen_{}".format(tool), path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["gen_{}".format(tool)] = module
    spec.loader.exec_module(module)
    fn = getattr(module, tool)

    # Resolve the postponed annotations so `bool` does not arrive as "bool".
    hints = get_type_hints(fn)
    signature = inspect.signature(fn)

    properties, required = {}, []
    for name, param in signature.parameters.items():
        base, nullable = _unwrap(hints.get(name, str))
        prop = dict(_json_type(base))
        if nullable:
            # Typed clients send null for omitted optional values.
            prop["type"] = [prop["type"], "null"] if prop.get("type") else prop.get("type")
            if not prop.get("type"):
                prop = {}
        if param.default is inspect.Parameter.empty and not nullable:
            required.append(name)
        if name in ENUMS.get(tool, {}):
            prop["enum"] = ENUMS[tool][name]
        if param.default is not inspect.Parameter.empty:
            prop["default"] = param.default
        properties[name] = prop
    return {"type": "object", "properties": properties, "required": required}


def main():
    tools = []
    for tool, (execution, affinity, group, tool_annotations) in SPEC.items():
        tools.append(
            {
                "name": tool,
                "description": DESCRIPTION[tool],
                "execution": execution,
                "affinity": affinity,
                "annotations": tool_annotations or {"idempotent_hint": False},
                "group": group,
                "input_schema": _schema(tool),
            }
        )
    target = SKILL_ROOT / "tools.yaml"
    target.write_text(
        yaml.safe_dump({"tools": tools}, sort_keys=False, width=100, default_flow_style=False),
        encoding="utf-8",
    )
    print("wrote {} ({} tools)".format(target, len(tools)))
    for tool in tools:
        props = tool["input_schema"]["properties"]
        print("  {:26s} {}".format(tool["name"], {k: v.get("type") for k, v in props.items()}))


if __name__ == "__main__":
    main()
