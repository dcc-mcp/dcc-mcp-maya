#!/usr/bin/env python3
"""Annotate all bundled ``tools.yaml`` files with ``execution``/``affinity``.

Addresses issue #84 (core #317 / #332): every tool declared by a bundled
skill must tell the gateway how it should be dispatched so the async
path (core #318), chunked-execution path (core #332) and ``deferredHint``
in ``tools/list`` can make correct decisions.

Classification strategy
-----------------------
1. A per-skill default ``(execution, affinity, timeout_hint_secs)`` tuple
   is chosen from :data:`SKILL_DEFAULTS` below.  The table follows the
   categorisation given in the issue description.
2. Tool-name heuristics (:data:`TOOL_OVERRIDES`) override the default for
   specific verbs.  Read-only verbs (``get_*``, ``list_*``, ``query_*``)
   collapse to ``execution: sync`` regardless of the skill default.
3. Maya cmds-touching tools always get ``affinity: main`` — it is never
   safe to assume ``any`` unless we know the script is pure filesystem.

The script is idempotent: running it twice produces the same output.
It is intentionally kept as a one-shot maintenance helper, not a runtime
dependency, so it lives under ``tools/`` rather than ``src/``.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    import yaml
except ImportError:  # pragma: no cover
    print("ERROR: PyYAML is required (pip install pyyaml)", file=sys.stderr)
    sys.exit(2)


ExecAffinity = Tuple[str, str, Optional[int]]  # (execution, affinity, timeout_hint_secs)


# Per-skill defaults (execution, affinity, timeout_hint_secs).
# The ``timeout_hint_secs`` field is only meaningful when execution == "async".
SKILL_DEFAULTS: Dict[str, ExecAffinity] = {
    # Long-running / main-thread-affine families
    "maya-render": ("async", "main", 600),
    "maya-render-farm": ("async", "main", 900),
    "maya-render-layers": ("sync", "main", None),
    "maya-render-passes": ("sync", "main", None),
    "maya-texture-bake": ("async", "main", 600),
    "maya-cache": ("async", "main", 300),
    "maya-cloth-sim": ("async", "main", 600),
    "maya-fluid": ("async", "main", 600),
    "maya-dynamics": ("async", "main", 600),
    "maya-muscle": ("async", "main", 300),
    "maya-grooming": ("async", "main", 300),
    "maya-xgen": ("async", "main", 300),
    "maya-bifrost": ("async", "main", 600),
    "maya-ocean": ("async", "main", 300),
    "maya-mocap": ("async", "main", 300),
    "maya-nparticles": ("async", "main", 600),
    # Scene I/O: export/save are async, meta reads are sync (overrides handle them)
    "maya-scene": ("sync", "main", None),
    "maya-scene-assembly": ("sync", "main", None),
    "maya-scene-utils": ("sync", "main", None),
    "maya-export-preset": ("sync", "main", None),
    "maya-shot-export": ("async", "main", 300),
    # Scripting: arbitrary user code — sync + main by default; caller chooses
    # async if they know the script is long-running.
    "maya-scripting": ("sync", "main", None),
    # Pure filesystem readers: worker-thread safe
    "maya-pipeline": ("sync", "main", None),
    "maya-material-library": ("sync", "main", None),
    # Everything else: sync + main (touches maya.cmds)
    "maya-animation": ("sync", "main", None),
    "maya-annotation": ("sync", "main", None),
    "maya-arnold-aov": ("sync", "main", None),
    "maya-attributes": ("sync", "main", None),
    "maya-audio": ("sync", "main", None),
    "maya-blend-shape-utils": ("sync", "main", None),
    "maya-camera-sequence": ("sync", "main", None),
    "maya-cameras": ("sync", "main", None),
    "maya-color-grading": ("sync", "main", None),
    "maya-constraints": ("sync", "main", None),
    "maya-constraints-advanced": ("sync", "main", None),
    "maya-deformers": ("sync", "main", None),
    "maya-display": ("sync", "main", None),
    "maya-expressions": ("sync", "main", None),
    "maya-gpu-cache": ("sync", "main", None),
    "maya-hdri": ("sync", "main", None),
    "maya-instancer": ("sync", "main", None),
    "maya-light-rig": ("sync", "main", None),
    "maya-lighting": ("sync", "main", None),
    "maya-mash": ("sync", "main", None),
    "maya-materials": ("sync", "main", None),
    "maya-mesh-ops": ("sync", "main", None),
    "maya-namespaces": ("sync", "main", None),
    "maya-node-graph": ("sync", "main", None),
    "maya-paint-effects": ("sync", "main", None),
    "maya-pose-library": ("sync", "main", None),
    "maya-primitives": ("sync", "main", None),
    "maya-proxy-mesh": ("sync", "main", None),
    "maya-references": ("sync", "main", None),
    "maya-rig-utils": ("sync", "main", None),
    "maya-rigging": ("sync", "main", None),
    "maya-selection": ("sync", "main", None),
    "maya-sets": ("sync", "main", None),
    "maya-skinning-utils": ("sync", "main", None),
    "maya-spline-ik": ("sync", "main", None),
    "maya-toon": ("sync", "main", None),
    "maya-utility": ("sync", "main", None),
    "maya-uv-ops": ("sync", "main", None),
    "maya-vertex-color": ("sync", "main", None),
    "maya-xform-utils": ("sync", "main", None),
}


# Per-tool overrides (skill, tool) -> (execution, affinity, timeout_hint_secs).
# Used when the skill default is not right for a specific verb.
TOOL_OVERRIDES: Dict[Tuple[str, str], ExecAffinity] = {
    # maya-scene long-running I/O
    ("maya-scene", "export_scene"): ("async", "main", 300),
    ("maya-scene", "save_scene"): ("async", "main", 120),
    ("maya-scene", "open_scene"): ("async", "main", 300),
    ("maya-scene", "new_scene"): ("async", "main", 60),
    # maya-scene-assembly definition is fast; create/add can be slow
    ("maya-scene-assembly", "create_assembly_definition"): ("async", "main", 120),
    ("maya-scene-assembly", "create_assembly_reference"): ("async", "main", 120),
    # maya-render long-running overrides (playblast/capture hit render engine)
    ("maya-render", "get_render_settings"): ("sync", "main", None),
    ("maya-render", "set_render_settings"): ("sync", "main", None),
    ("maya-render", "set_render_quality"): ("sync", "main", None),
    ("maya-render", "get_scene_render_stats"): ("sync", "main", None),
    ("maya-render", "export_selection"): ("async", "main", 300),
    ("maya-render", "import_file"): ("async", "main", 300),
    # maya-render-farm — all async
    ("maya-render-farm", "get_render_job_status"): ("sync", "any", None),
    # maya-scripting execute_* stays sync; long scripts submitted separately
    # maya-cache
    ("maya-cache", "list_geometry_caches"): ("sync", "main", None),
    ("maya-cache", "delete_geometry_cache"): ("sync", "main", None),
    # maya-mocap
    ("maya-mocap", "create_hik_definition"): ("sync", "main", None),
    ("maya-mocap", "clean_mocap_keys"): ("sync", "main", None),
    # maya-xgen fast meta ops
    ("maya-xgen", "list_descriptions"): ("sync", "main", None),
    ("maya-xgen", "get_xgen_attribute"): ("sync", "main", None),
    ("maya-xgen", "set_xgen_attribute"): ("sync", "main", None),
    # maya-bifrost fast meta ops
    ("maya-bifrost", "list_bifrost_graphs"): ("sync", "main", None),
    ("maya-bifrost", "connect_bifrost_ports"): ("sync", "main", None),
    ("maya-bifrost", "set_bifrost_property"): ("sync", "main", None),
    ("maya-bifrost", "add_bifrost_node"): ("sync", "main", None),
    # maya-grooming fast meta ops
    ("maya-grooming", "list_hair_systems"): ("sync", "main", None),
    ("maya-grooming", "set_nhair_attribute"): ("sync", "main", None),
    # maya-ocean fast meta ops
    ("maya-ocean", "list_ocean_surfaces"): ("sync", "main", None),
    ("maya-ocean", "set_ocean_attribute"): ("sync", "main", None),
    ("maya-ocean", "add_ocean_wake"): ("sync", "main", None),
    # maya-fluid fast meta ops
    ("maya-fluid", "list_fluid_containers"): ("sync", "main", None),
    ("maya-fluid", "delete_fluid_container"): ("sync", "main", None),
    ("maya-fluid", "set_fluid_attribute"): ("sync", "main", None),
    # maya-cloth-sim fast meta ops
    ("maya-cloth-sim", "list_ncloth_objects"): ("sync", "main", None),
    ("maya-cloth-sim", "set_ncloth_attribute"): ("sync", "main", None),
    ("maya-cloth-sim", "create_ncloth"): ("sync", "main", None),
    # maya-dynamics fast meta ops
    ("maya-dynamics", "list_ncloth_nodes"): ("sync", "main", None),
    ("maya-dynamics", "list_nrigid_nodes"): ("sync", "main", None),
    ("maya-dynamics", "set_ncloth_attribute"): ("sync", "main", None),
    ("maya-dynamics", "set_nrigid_attribute"): ("sync", "main", None),
    ("maya-dynamics", "set_nucleus_attribute"): ("sync", "main", None),
    ("maya-dynamics", "create_nucleus"): ("sync", "main", None),
    ("maya-dynamics", "create_ncloth"): ("sync", "main", None),
    ("maya-dynamics", "create_nrigid"): ("sync", "main", None),
    ("maya-dynamics", "connect_field_to_objects"): ("sync", "main", None),
    ("maya-dynamics", "create_dynamic_field"): ("sync", "main", None),
    # maya-muscle fast meta ops
    ("maya-muscle", "list_muscles"): ("sync", "main", None),
    ("maya-muscle", "set_muscle_attribute"): ("sync", "main", None),
    ("maya-muscle", "create_muscle_capsule"): ("sync", "main", None),
    # maya-nparticles fast meta ops
    ("maya-nparticles", "list_nparticle_systems"): ("sync", "main", None),
    ("maya-nparticles", "set_nparticle_attribute"): ("sync", "main", None),
    ("maya-nparticles", "add_field_to_nparticles"): ("sync", "main", None),
    ("maya-nparticles", "create_nparticle_emitter"): ("sync", "main", None),
    # maya-texture-bake fast meta ops
    ("maya-texture-bake", "list_bake_sets"): ("sync", "main", None),
    ("maya-texture-bake", "list_color_spaces"): ("sync", "main", None),
    ("maya-texture-bake", "set_color_management"): ("sync", "main", None),
    # maya-shot-export meta
    ("maya-shot-export", "get_shot_info"): ("sync", "main", None),
    # maya-scripting introspect tools: list/signature/search are worker-safe (no DAG access)
    ("maya-scripting", "introspect_list_module"): ("sync", "any", None),
    ("maya-scripting", "introspect_signature"): ("sync", "any", None),
    ("maya-scripting", "introspect_search"): ("sync", "any", None),
    # introspect_eval touches DAG via expression, must stay main-thread
    ("maya-scripting", "introspect_eval"): ("sync", "main", None),
}


READ_ONLY_PREFIXES = ("get_", "list_", "query_", "describe_", "read_")


def classify(skill: str, tool_name: str) -> ExecAffinity:
    """Return ``(execution, affinity, timeout_hint_secs)`` for a tool."""
    override = TOOL_OVERRIDES.get((skill, tool_name))
    if override is not None:
        return override

    default = SKILL_DEFAULTS.get(skill)
    if default is None:
        # Unknown skill — conservative: sync + main (Maya cmds assumed).
        return ("sync", "main", None)

    execution, affinity, timeout = default

    # Read-only verbs are always sync regardless of skill default.
    if tool_name.startswith(READ_ONLY_PREFIXES):
        return ("sync", affinity, None)

    return (execution, affinity, timeout)


def annotate_tool(tool: dict, skill: str) -> bool:
    """Populate ``execution``/``affinity``/``timeout_hint_secs``.

    Returns ``True`` if anything was changed.
    """
    if not isinstance(tool, dict):
        return False

    name = tool.get("name")
    if not isinstance(name, str):
        return False

    execution, affinity, timeout = classify(skill, name)
    changed = False

    if tool.get("execution") != execution:
        tool["execution"] = execution
        changed = True

    if tool.get("affinity") != affinity:
        tool["affinity"] = affinity
        changed = True

    if execution == "async":
        if tool.get("timeout_hint_secs") != timeout:
            tool["timeout_hint_secs"] = timeout
            changed = True
    else:
        # Drop any stale hint on sync tools.
        if "timeout_hint_secs" in tool:
            del tool["timeout_hint_secs"]
            changed = True

    return changed


def dump_tool(tool: dict) -> str:
    """Dump a single tool as a YAML list entry with stable key ordering."""
    # Preferred key order for readability.
    order = [
        "name",
        "description",
        "execution",
        "affinity",
        "timeout_hint_secs",
        "source_file",
        "annotations",
    ]
    ordered: Dict[str, object] = {}
    for key in order:
        if key in tool:
            ordered[key] = tool[key]
    for key, value in tool.items():
        if key not in ordered:
            ordered[key] = value

    # yaml.dump with the single-entry dict, then prefix the first line with "- ".
    rendered = yaml.safe_dump(ordered, sort_keys=False, default_flow_style=False).rstrip("\n")
    lines = rendered.splitlines()
    out_lines: List[str] = []
    for i, line in enumerate(lines):
        if i == 0:
            out_lines.append(f"- {line}")
        else:
            out_lines.append(f"  {line}")
    return "\n".join(out_lines)


def annotate_file(path: Path) -> bool:
    """Annotate a single ``tools.yaml`` file in place.  Returns ``True`` on change."""
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    tools = data.get("tools")
    if not isinstance(tools, list):
        return False

    skill = path.parent.name
    changed_any = False
    for tool in tools:
        if annotate_tool(tool, skill):
            changed_any = True

    if not changed_any:
        return False

    header = "tools:\n"
    body = "\n".join(dump_tool(t) for t in tools) + "\n"
    path.write_text(header + body, encoding="utf-8")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--skills-root",
        default="src/dcc_mcp_maya/skills",
        help="Path to skills directory (default: src/dcc_mcp_maya/skills)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Do not modify files; exit non-zero if any file would be changed.",
    )
    args = parser.parse_args()

    root = Path(args.skills_root)
    if not root.is_dir():
        print(f"ERROR: {root} is not a directory", file=sys.stderr)
        return 2

    files = sorted(root.glob("*/tools.yaml"))
    changed: List[Path] = []
    for file in files:
        if args.check:
            original = file.read_text(encoding="utf-8")
            data = yaml.safe_load(original) or {}
            tools = data.get("tools") or []
            dirty = False
            for tool in tools:
                snapshot = dict(tool) if isinstance(tool, dict) else None
                if annotate_tool(tool, file.parent.name):
                    dirty = True
                if snapshot is not None and isinstance(tool, dict):
                    tool.clear()
                    tool.update(snapshot)
            if dirty:
                changed.append(file)
        else:
            if annotate_file(file):
                changed.append(file)

    if args.check:
        if changed:
            print("The following tools.yaml files are missing affinity annotations:")
            for path in changed:
                print(f"  {path}")
            return 1
        print(f"All {len(files)} tools.yaml files are annotated.")
        return 0

    print(f"Annotated {len(changed)} of {len(files)} tools.yaml files.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
