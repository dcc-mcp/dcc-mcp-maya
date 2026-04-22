"""One-shot migration script: move dcc-mcp-core v0.14-era SKILL.md to the
v0.15+ sibling-file pattern (agentskills.io 1.0 compliant).

Idempotent: safe to re-run; already-migrated skills are skipped.

Rules:
  - SKILL.md frontmatter keeps ONLY: name, description, license,
    compatibility, metadata, allowed-tools
  - dcc/version/tags/search-hint/depends/external_deps/products/
    allow_implicit_invocation → metadata.dcc-mcp.*
  - tools:    → sibling tools.yaml, frontmatter references via
    metadata.dcc-mcp.tools: tools.yaml
  - groups:   → sibling groups.yaml, referenced via
    metadata.dcc-mcp.groups: groups.yaml
  - allowed-tools list[str] → space-separated string
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import yaml

SPEC_TOP_LEVEL = {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}
DCC_MCP_EXTENSIONS = {
    "dcc",
    "version",
    "tags",
    "search-hint",
    "depends",
    "external_deps",
    "products",
    "allow_implicit_invocation",
}


def split_frontmatter(text: str) -> tuple[dict[str, Any] | None, str]:
    if not text.startswith("---\n"):
        return None, text
    end = text.find("\n---\n", 4)
    if end == -1:
        return None, text
    fm = yaml.safe_load(text[4:end])
    body = text[end + 5 :]
    return fm, body


def migrate_skill(skill_dir: Path, *, dry_run: bool = False) -> dict[str, Any]:
    """Return a small report dict."""
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        return {"skipped": str(skill_dir), "reason": "no SKILL.md"}

    fm, body = split_frontmatter(skill_md.read_text(encoding="utf-8"))
    if fm is None:
        return {"skipped": str(skill_dir), "reason": "no frontmatter"}

    # Skip if already migrated (has metadata.dcc-mcp and no top-level tools/groups/dcc)
    already = (
        isinstance(fm.get("metadata"), dict)
        and isinstance(fm["metadata"].get("dcc-mcp"), dict)
        and "tools" not in fm
        and "groups" not in fm
        and "dcc" not in fm
    )
    if already:
        return {"skipped": str(skill_dir), "reason": "already migrated"}

    new_fm: dict[str, Any] = {}
    metadata = dict(fm.get("metadata") or {})
    dcc_mcp = dict(metadata.get("dcc-mcp") or {})

    for key in ("name", "description", "license", "compatibility"):
        if key in fm:
            new_fm[key] = fm[key]

    # allowed-tools: list[str] -> space-separated string
    if "allowed-tools" in fm:
        at = fm["allowed-tools"]
        new_fm["allowed-tools"] = " ".join(at) if isinstance(at, list) else str(at)

    # Move dcc-mcp-core extension fields into metadata.dcc-mcp
    for key in DCC_MCP_EXTENSIONS:
        if key in fm:
            dcc_mcp[key] = fm[key]

    # Preserve arbitrary user metadata passthrough
    for k, v in metadata.items():
        if k != "dcc-mcp":
            # agentskills.io requires metadata values be strings; coerce lists/dicts to JSON-ish
            new_fm.setdefault("metadata", {})[k] = v

    # Tools -> tools.yaml
    if "tools" in fm:
        tools_list = fm["tools"]
        if isinstance(tools_list, list) and tools_list:
            tools_doc = {"tools": []}
            for t in tools_list:
                if not isinstance(t, dict) or "name" not in t:
                    continue
                tool_entry: dict[str, Any] = {"name": t["name"]}
                if "description" in t:
                    tool_entry["description"] = t["description"]
                # Shorthand annotation hints go into a nested annotations map
                ann: dict[str, Any] = {}
                for hint in (
                    "read_only_hint",
                    "destructive_hint",
                    "idempotent_hint",
                    "open_world_hint",
                    "deferred_hint",
                ):
                    if hint in t:
                        ann[hint] = t[hint]
                if ann:
                    tool_entry["annotations"] = ann
                # next-tools (rare in current fixtures, but preserve if present)
                if "next-tools" in t:
                    tool_entry["next-tools"] = t["next-tools"]
                # required_capabilities per-tool (new in #354)
                if "required_capabilities" in t:
                    tool_entry["required_capabilities"] = t["required_capabilities"]
                tools_doc["tools"].append(tool_entry)
            if not dry_run:
                (skill_dir / "tools.yaml").write_text(
                    yaml.safe_dump(tools_doc, sort_keys=False, default_flow_style=False),
                    encoding="utf-8",
                )
            dcc_mcp["tools"] = "tools.yaml"

    # Groups -> groups.yaml
    if "groups" in fm:
        groups_doc = {"groups": fm["groups"]}
        if not dry_run:
            (skill_dir / "groups.yaml").write_text(
                yaml.safe_dump(groups_doc, sort_keys=False, default_flow_style=False),
                encoding="utf-8",
            )
        dcc_mcp["groups"] = "groups.yaml"

    if dcc_mcp:
        new_fm.setdefault("metadata", {})["dcc-mcp"] = dcc_mcp

    # Write back SKILL.md
    new_fm_yaml = yaml.safe_dump(new_fm, sort_keys=False, default_flow_style=False, allow_unicode=True)
    new_text = f"---\n{new_fm_yaml}---\n{body.lstrip()}" if body else f"---\n{new_fm_yaml}---\n"
    if not dry_run:
        skill_md.write_text(new_text, encoding="utf-8")

    return {
        "migrated": str(skill_dir),
        "tools_count": len(fm.get("tools", []) or []),
        "groups_count": len(fm.get("groups", []) or []),
        "moved_to_dcc_mcp": sorted(k for k in DCC_MCP_EXTENSIONS if k in fm),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("skills_root", type=Path, help="Directory containing skill subdirectories")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not args.skills_root.is_dir():
        print(f"not a directory: {args.skills_root}", file=sys.stderr)
        return 2

    migrated = 0
    skipped = 0
    for skill_dir in sorted(p for p in args.skills_root.iterdir() if p.is_dir()):
        report = migrate_skill(skill_dir, dry_run=args.dry_run)
        if "migrated" in report:
            migrated += 1
            print(
                f"migrated {skill_dir.name}  tools={report['tools_count']}  groups={report['groups_count']}  "
                f"moved={','.join(report['moved_to_dcc_mcp']) or '-'}"
            )
        else:
            skipped += 1
            print(f"skipped  {skill_dir.name}  ({report.get('reason', '?')})")

    print(f"\nTotal: migrated={migrated} skipped={skipped} dry_run={args.dry_run}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
