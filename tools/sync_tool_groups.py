#!/usr/bin/env python3
"""Sync per-tool ``group:`` field in ``tools.yaml`` from ``groups.yaml``.

Background
----------
dcc-mcp-core's skill loader reads each tool's group membership from the
``group:`` attribute on the :class:`ToolDeclaration` itself, not by
cross-referencing the skill's ``groups:`` list.  The "sibling-file"
migration (#356) split tool and group declarations into separate files
but did not duplicate the per-tool ``group:`` field, which broke
progressive exposure (minimal mode no longer deactivates the
``extended`` / ``scene-management`` groups because every tool's
``group`` ends up empty).

This script walks every skill directory under ``src/dcc_mcp_maya/skills``,
reads its ``groups.yaml`` (or the ``groups:`` key embedded in
``tools.yaml``) and writes the matching ``group:`` value back onto each
entry in ``tools.yaml``.  The file is rewritten in-place with the same
ordering of tools and groups.

Usage
-----
    python tools/sync_tool_groups.py                 # update every skill
    python tools/sync_tool_groups.py --check         # exit 1 if any skill is stale
    python tools/sync_tool_groups.py --skill maya-scene
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Dict, List, Optional

import yaml


def _load_yaml(path: Path) -> dict:
    with path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    return data if isinstance(data, dict) else {}


def _dump_yaml(data: dict, path: Path) -> None:
    text = yaml.safe_dump(
        data,
        default_flow_style=False,
        sort_keys=False,
        allow_unicode=True,
        width=80,
    )
    path.write_text(text, encoding="utf-8")


def _build_tool_group_map(groups: List[dict]) -> Dict[str, str]:
    """Return a ``{tool_name: group_name}`` map derived from the groups list."""
    out: Dict[str, str] = {}
    for group in groups:
        if not isinstance(group, dict):
            continue
        gname = group.get("name")
        if not gname:
            continue
        for tool in group.get("tools", []) or []:
            if isinstance(tool, str):
                out[tool] = str(gname)
    return out


def _sync_skill(skill_dir: Path, check_only: bool) -> Optional[bool]:
    """Sync a single skill. Returns ``True`` if changes were needed."""
    tools_path = skill_dir / "tools.yaml"
    if not tools_path.exists():
        return None

    tools_doc = _load_yaml(tools_path)
    tools = tools_doc.get("tools")
    if not isinstance(tools, list):
        return None

    groups: List[dict] = []
    groups_path = skill_dir / "groups.yaml"
    if groups_path.exists():
        groups_doc = _load_yaml(groups_path)
        grp = groups_doc.get("groups")
        if isinstance(grp, list):
            groups = grp

    if not groups:
        inline = tools_doc.get("groups")
        if isinstance(inline, list):
            groups = inline

    if not groups:
        return None

    group_map = _build_tool_group_map(groups)
    if not group_map:
        return None

    changed = False
    new_tools: List[dict] = []
    for entry in tools:
        if isinstance(entry, str):
            entry = {"name": entry}
        if not isinstance(entry, dict):
            new_tools.append(entry)
            continue
        name = entry.get("name")
        if not name:
            new_tools.append(entry)
            continue
        want_group = group_map.get(name)
        have_group = entry.get("group")
        if want_group and have_group != want_group:
            entry = {**entry, "group": want_group}
            changed = True
        new_tools.append(entry)

    if not changed:
        return False

    if check_only:
        return True

    tools_doc["tools"] = new_tools
    _dump_yaml(tools_doc, tools_path)
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--skills-root",
        default="src/dcc_mcp_maya/skills",
        help="Path to skills directory (default: src/dcc_mcp_maya/skills)",
    )
    parser.add_argument(
        "--skill",
        default=None,
        help="Limit to a single skill by name (e.g. 'maya-scene').",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit 1 if any skill's tools.yaml is out of sync with groups.yaml.",
    )
    args = parser.parse_args()

    skills_root = Path(args.skills_root)
    if not skills_root.is_dir():
        print(f"ERROR: skills root {skills_root!r} does not exist", file=sys.stderr)
        sys.exit(2)

    if args.skill:
        targets = [skills_root / args.skill]
    else:
        targets = sorted(d for d in skills_root.iterdir() if d.is_dir())

    any_changed = False
    for skill_dir in targets:
        result = _sync_skill(skill_dir, check_only=args.check)
        if result is None:
            continue
        if result:
            any_changed = True
            if args.check:
                print(f"STALE   {skill_dir.name}")
            else:
                print(f"UPDATED {skill_dir.name}")
        else:
            print(f"OK      {skill_dir.name}")

    if args.check and any_changed:
        sys.exit(1)


if __name__ == "__main__":
    main()
