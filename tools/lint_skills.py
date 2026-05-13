#!/usr/bin/env python3
"""Lint SKILL.md files in the dcc-mcp-maya skills directory.

Usage:
    python tools/lint_skills.py                    # lint all skills
    python tools/lint_skills.py --fix              # auto-fix conflict markers
    python tools/lint_skills.py --error-only       # only report ERRORs
    python tools/lint_skills.py --skills-root path # custom skills root
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SUPPORTED_SCRIPT_EXTENSIONS: Set[str] = {
    ".py",
    ".mel",
    ".ms",
    ".bat",
    ".cmd",
    ".sh",
    ".bash",
    ".ps1",
    ".vbs",
    ".jsx",
    ".js",
}

VALID_DCC_VALUES: Set[str] = {
    "maya",
    "blender",
    "houdini",
    "3dsmax",
    "unreal",
    "unity",
    "python",
}

# For this project all skills must target maya
PROJECT_DCC = "maya"

CONFLICT_MARKER_RE = re.compile(r"^(<{7}|={7}|>{7})", re.MULTILINE)
CONFLICT_FULL_RE = re.compile(
    r"<<<<<<< HEAD\n(.*?)=======\n(.*?)>>>>>>> origin/main\n",
    re.DOTALL,
)
SEMVER_RE = re.compile(r"^\d+\.\d+(\.\d+)?(-[\w.]+)?(\+[\w.]+)?$")
NAME_VALID_RE = re.compile(r"^[a-z0-9-]+$")

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class LintIssue:
    skill: str  # skill directory name
    file: str  # relative path from project root
    severity: str  # "ERROR" | "WARNING"
    rule: str  # rule code
    message: str


@dataclass
class SkillInfo:
    name: str
    skill_dir: Path
    scripts: List[Path] = field(default_factory=list)


# ---------------------------------------------------------------------------
# YAML frontmatter parsing (PyYAML with stdlib fallback)
# ---------------------------------------------------------------------------


def _parse_yaml_minimal(yaml_text: str) -> Optional[dict]:
    """Minimal YAML key:value parser (no nesting, no lists) as stdlib fallback."""
    result: dict = {}
    for line in yaml_text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line:
            key, _, val = line.partition(":")
            val = val.strip().strip('"').strip("'")
            result[key.strip()] = val
    return result


def extract_frontmatter(content: str) -> Optional[dict]:
    """Extract and parse YAML frontmatter bounded by --- delimiters."""
    if not content.startswith("---"):
        return None
    # Find the closing ---
    end = content.find("\n---", 3)
    if end == -1:
        return None
    yaml_text = content[4:end]
    try:
        import yaml  # type: ignore[import]

        data = yaml.safe_load(yaml_text)
        return data if isinstance(data, dict) else None
    except Exception:
        # Try minimal fallback
        return _parse_yaml_minimal(yaml_text)


# ---------------------------------------------------------------------------
# Individual rule checks
# ---------------------------------------------------------------------------


def check_conflict_markers(skill_dir: Path, skill_name: str, content: str) -> List[LintIssue]:
    issues: List[LintIssue] = []
    if CONFLICT_MARKER_RE.search(content):
        issues.append(
            LintIssue(
                skill=skill_name,
                file=str(skill_dir / "SKILL.md"),
                severity="ERROR",
                rule="CONFLICT_MARKER",
                message="Unresolved git merge conflict markers found in SKILL.md",
            )
        )
    return issues


def check_frontmatter_parseable(
    skill_dir: Path, skill_name: str, content: str
) -> Tuple[List[LintIssue], Optional[dict]]:
    """Returns (issues, frontmatter_dict_or_None)."""
    issues: List[LintIssue] = []

    if not content.startswith("---"):
        issues.append(
            LintIssue(
                skill=skill_name,
                file=str(skill_dir / "SKILL.md"),
                severity="ERROR",
                rule="NO_FRONTMATTER",
                message="SKILL.md does not start with --- (missing YAML frontmatter)",
            )
        )
        return issues, None

    if content.find("\n---", 3) == -1:
        issues.append(
            LintIssue(
                skill=skill_name,
                file=str(skill_dir / "SKILL.md"),
                severity="ERROR",
                rule="NO_FRONTMATTER",
                message="SKILL.md frontmatter closing --- not found",
            )
        )
        return issues, None

    fm = extract_frontmatter(content)
    if fm is None:
        issues.append(
            LintIssue(
                skill=skill_name,
                file=str(skill_dir / "SKILL.md"),
                severity="ERROR",
                rule="NO_FRONTMATTER",
                message="SKILL.md YAML frontmatter could not be parsed",
            )
        )
    return issues, fm


def check_name_field(skill_dir: Path, skill_name: str, fm: dict) -> List[LintIssue]:
    issues: List[LintIssue] = []
    file_path = str(skill_dir / "SKILL.md")
    name = fm.get("name")

    if not name:
        issues.append(
            LintIssue(
                skill=skill_name,
                file=file_path,
                severity="ERROR",
                rule="NO_NAME",
                message="frontmatter missing required 'name' field",
            )
        )
        return issues

    name = str(name)

    if name != skill_name:
        issues.append(
            LintIssue(
                skill=skill_name,
                file=file_path,
                severity="ERROR",
                rule="NAME_MISMATCH",
                message=f"name '{name}' does not match directory name '{skill_name}'",
            )
        )

    if len(name) > 64:
        issues.append(
            LintIssue(
                skill=skill_name,
                file=file_path,
                severity="WARNING",
                rule="NAME_FORMAT",
                message=f"name '{name}' exceeds 64 chars (agentskills.io limit)",
            )
        )

    if name.startswith("-") or name.endswith("-"):
        issues.append(
            LintIssue(
                skill=skill_name,
                file=file_path,
                severity="WARNING",
                rule="NAME_FORMAT",
                message=f"name '{name}' must not start or end with a hyphen",
            )
        )

    if "--" in name:
        issues.append(
            LintIssue(
                skill=skill_name,
                file=file_path,
                severity="WARNING",
                rule="NAME_FORMAT",
                message=f"name '{name}' must not contain consecutive hyphens",
            )
        )

    if not NAME_VALID_RE.match(name):
        issues.append(
            LintIssue(
                skill=skill_name,
                file=file_path,
                severity="WARNING",
                rule="NAME_FORMAT",
                message=f"name '{name}' should be lowercase letters, digits, and hyphens only",
            )
        )

    return issues


def _extract_dcc_mcp_field(fm: dict, key: str, default=None):
    """Read a ``metadata.dcc-mcp.*`` field from either the nested or flat form.

    Supports three SKILL.md layouts:

    1. Top-level shorthand (pre-0.15 dcc-mcp-core):  ``dcc: maya``
    2. Flat metadata form:  ``metadata: {"dcc-mcp.dcc": "maya"}``
    3. Nested agentskills.io-compliant form (issue #356):
       ``metadata: {dcc-mcp: {dcc: maya}}``
    """
    if key in fm:
        return fm[key]
    metadata = fm.get("metadata") or {}
    if not isinstance(metadata, dict):
        return default
    flat = metadata.get(f"dcc-mcp.{key}")
    if flat is not None:
        return flat
    nested = metadata.get("dcc-mcp")
    if isinstance(nested, dict) and key in nested:
        return nested[key]
    return default


def check_dcc_field(skill_dir: Path, skill_name: str, fm: dict) -> List[LintIssue]:
    issues: List[LintIssue] = []
    file_path = str(skill_dir / "SKILL.md")
    dcc = _extract_dcc_mcp_field(fm, "dcc", default="python")

    if dcc not in VALID_DCC_VALUES:
        issues.append(
            LintIssue(
                skill=skill_name,
                file=file_path,
                severity="WARNING",
                rule="UNKNOWN_DCC",
                message=f"dcc '{dcc}' is not a known value (expected one of: {', '.join(sorted(VALID_DCC_VALUES))})",
            )
        )

    if dcc != PROJECT_DCC:
        issues.append(
            LintIssue(
                skill=skill_name,
                file=file_path,
                severity="ERROR",
                rule="WRONG_DCC",
                message=f"dcc '{dcc}' should be '{PROJECT_DCC}' for this project",
            )
        )

    return issues


def check_version_field(skill_dir: Path, skill_name: str, fm: dict) -> List[LintIssue]:
    issues: List[LintIssue] = []
    version = _extract_dcc_mcp_field(fm, "version", default="1.0.0")
    if version and not SEMVER_RE.match(str(version)):
        issues.append(
            LintIssue(
                skill=skill_name,
                file=str(skill_dir / "SKILL.md"),
                severity="WARNING",
                rule="BAD_VERSION",
                message=f"version '{version}' does not follow semver (e.g. '1.0.0')",
            )
        )
    return issues


def check_description_field(skill_dir: Path, skill_name: str, fm: dict) -> List[LintIssue]:
    issues: List[LintIssue] = []
    file_path = str(skill_dir / "SKILL.md")
    desc = fm.get("description", "")

    if not desc:
        issues.append(
            LintIssue(
                skill=skill_name,
                file=file_path,
                severity="WARNING",
                rule="MISSING_DESC",
                message="'description' field is empty or missing",
            )
        )
    elif len(str(desc)) > 1024:
        issues.append(
            LintIssue(
                skill=skill_name,
                file=file_path,
                severity="WARNING",
                rule="DESC_TOO_LONG",
                message=f"description length {len(str(desc))} exceeds 1024 chars (agentskills.io limit)",
            )
        )

    return issues


def check_scripts_section(skill_dir: Path, skill_name: str, content: str) -> List[LintIssue]:
    """Warn if scripts/ contains files but SKILL.md body has no ## Scripts section."""
    issues: List[LintIssue] = []
    scripts_dir = skill_dir / "scripts"
    if not scripts_dir.is_dir():
        return issues

    script_files = [f for f in scripts_dir.iterdir() if f.is_file() and f.suffix.lower() in SUPPORTED_SCRIPT_EXTENSIONS]
    if not script_files:
        return issues

    # Check body (after closing frontmatter ---)
    end = content.find("\n---", 3)
    body = content[end + 4 :] if end != -1 else content

    if "## Scripts" not in body and "##Scripts" not in body:
        issues.append(
            LintIssue(
                skill=skill_name,
                file=str(skill_dir / "SKILL.md"),
                severity="WARNING",
                rule="MISSING_SCRIPTS_SECTION",
                message=f"{len(script_files)} script(s) found in scripts/ but no '## Scripts' section in SKILL.md body",
            )
        )
    return issues


def _resolve_tools_list(skill_dir: Path, fm: dict) -> list:
    """Return the skill's tool list, resolving sibling ``tools.yaml`` references.

    Supports three shapes:

    * Inline list (legacy):  ``tools: [{name: ...}, ...]``
    * Sibling filename:       ``tools: tools.yaml``
    * Nested + sibling:       ``metadata.dcc-mcp.tools: tools.yaml``
    """
    raw = _extract_dcc_mcp_field(fm, "tools", default=None)
    if raw is None:
        return []
    if isinstance(raw, list):
        return raw
    if isinstance(raw, str):
        candidate = skill_dir / raw
        if not candidate.exists():
            return []
        try:
            import yaml  # type: ignore[import]

            data = yaml.safe_load(candidate.read_text(encoding="utf-8")) or {}
            tools = data.get("tools") if isinstance(data, dict) else None
            return tools if isinstance(tools, list) else []
        except Exception:
            return []
    return []


def _resolve_groups_list(skill_dir: Path, fm: dict) -> list:
    """Return the skill's group list, resolving sibling ``groups.yaml`` references.

    Falls back to the ``groups:`` key in the sibling ``tools.yaml`` when the
    dedicated groups file is not declared.
    """
    raw_groups = _extract_dcc_mcp_field(fm, "groups", default=None)
    if isinstance(raw_groups, list):
        return raw_groups
    if isinstance(raw_groups, str):
        candidate = skill_dir / raw_groups
        if candidate.exists():
            try:
                import yaml  # type: ignore[import]

                data = yaml.safe_load(candidate.read_text(encoding="utf-8")) or {}
                groups = data.get("groups") if isinstance(data, dict) else None
                if isinstance(groups, list):
                    return groups
            except Exception:
                pass
    # Fallback: groups defined inside tools.yaml alongside the tools list.
    raw_tools = _extract_dcc_mcp_field(fm, "tools", default=None)
    if isinstance(raw_tools, str):
        candidate = skill_dir / raw_tools
        if candidate.exists():
            try:
                import yaml  # type: ignore[import]

                data = yaml.safe_load(candidate.read_text(encoding="utf-8")) or {}
                groups = data.get("groups") if isinstance(data, dict) else None
                if isinstance(groups, list):
                    return groups
            except Exception:
                pass
    return []


def check_tools_source_files(skill_dir: Path, skill_name: str, fm: dict) -> List[LintIssue]:
    """Warn if tools[].source_file paths don't exist in scripts/ dir."""
    issues: List[LintIssue] = []
    tools = _resolve_tools_list(skill_dir, fm)
    if not tools or not isinstance(tools, list):
        return issues

    for tool_entry in tools:
        if not isinstance(tool_entry, dict):
            continue
        source_file = tool_entry.get("source_file", "")
        if not source_file:
            continue
        # source_file is relative to skill_dir
        full_path = skill_dir / source_file
        if not full_path.exists():
            issues.append(
                LintIssue(
                    skill=skill_name,
                    file=str(skill_dir / "SKILL.md"),
                    severity="WARNING",
                    rule="TOOL_SOURCE_MISSING",
                    message=f"tools entry source_file '{source_file}' not found at {full_path}",
                )
            )
    return issues


def check_depends_exist(
    skill_dir: Path,
    skill_name: str,
    fm: dict,
    all_skill_names: Set[str],
) -> List[LintIssue]:
    """Warn if depends[] references skill names that don't exist."""
    issues: List[LintIssue] = []
    depends = _extract_dcc_mcp_field(fm, "depends", default=[])
    if not depends or not isinstance(depends, list):
        return issues

    for dep in depends:
        dep_str = str(dep).strip()
        if dep_str and dep_str not in all_skill_names:
            issues.append(
                LintIssue(
                    skill=skill_name,
                    file=str(skill_dir / "SKILL.md"),
                    severity="WARNING",
                    rule="MISSING_DEPENDS",
                    message=f"depends references '{dep_str}' which is not a known skill",
                )
            )
    return issues


def _references_metadata_ok(fm: dict) -> bool:
    """True when references/ content is wired for agent read tools (recipes, introspection, or skill-reference-docs)."""
    srd = _extract_dcc_mcp_field(fm, "skill-reference-docs")
    if srd:
        return True
    recipes = _extract_dcc_mcp_field(fm, "recipes")
    if isinstance(recipes, str) and recipes.strip().startswith("references"):
        return True
    if isinstance(recipes, list) and any(isinstance(x, str) and x.strip().startswith("references") for x in recipes):
        return True
    intro = _extract_dcc_mcp_field(fm, "introspection")
    if isinstance(intro, str) and intro.strip().startswith("references"):
        return True
    return False


def check_references_dir_wiring(skill_dir: Path, skill_name: str, fm: dict) -> List[LintIssue]:
    """Warn when a references/ directory exists but SKILL metadata does not wire it."""
    ref_dir = skill_dir / "references"
    if not ref_dir.is_dir():
        return []
    if _references_metadata_ok(fm):
        return []
    return [
        LintIssue(
            skill=skill_name,
            file=str(skill_dir / "SKILL.md"),
            severity="WARNING",
            rule="REF_DIR_UNWIRED",
            message=(
                "references/ exists — add metadata.dcc-mcp.skill-reference-docs (glob list), "
                "or point recipes/introspection under references/ "
                "(see docs/guide/skill-maintenance.md in dcc-mcp-core)"
            ),
        )
    ]


def check_io_tool_descriptions(skill_dir: Path, skill_name: str, fm: dict) -> List[LintIssue]:
    """Warn when interchange-style tools have very short descriptions (agents rely on tools/list text)."""
    issues: List[LintIssue] = []
    tools = _resolve_tools_list(skill_dir, fm)
    if not tools:
        return issues
    tools_yaml = _extract_dcc_mcp_field(fm, "tools", default=None)
    yaml_label = str(tools_yaml) if tools_yaml else "tools.yaml"

    for tool_entry in tools:
        if not isinstance(tool_entry, dict):
            continue
        name = str(tool_entry.get("name") or "")
        if not (name.startswith("export_") or name.startswith("import_")):
            continue
        desc = str(tool_entry.get("description") or "").replace("\n", " ").strip()
        if len(desc) >= 100:
            continue
        issues.append(
            LintIssue(
                skill=skill_name,
                file=str(skill_dir / yaml_label),
                severity="WARNING",
                rule="IO_TOOL_DESC_SHORT",
                message=(
                    f"tool '{name}': description is short ({len(desc)} chars) — expand with "
                    "absolute paths, plugins, prerequisites, and common failures "
                    "(see docs/guide/skill-maintenance.md in dcc-mcp-core)"
                ),
            )
        )
    return issues


# ---------------------------------------------------------------------------
# Cross-skill checks
# ---------------------------------------------------------------------------


def check_duplicate_action_names(
    all_skills_info: List[SkillInfo],
) -> List[LintIssue]:
    """Warn when two skills share the same script stem (action name collision)."""
    issues: List[LintIssue] = []
    # stem -> list of (skill_name, script_path)
    stem_map: Dict[str, List[Tuple[str, Path]]] = {}

    for info in all_skills_info:
        for script in info.scripts:
            stem = script.stem
            stem_map.setdefault(stem, []).append((info.name, script))

    for stem, occurrences in stem_map.items():
        if len(occurrences) > 1:
            skill_list = ", ".join(f"{s} ({p.name})" for s, p in occurrences)
            for skill_name, script_path in occurrences:
                issues.append(
                    LintIssue(
                        skill=skill_name,
                        file=str(script_path),
                        severity="WARNING",
                        rule="DUPLICATE_SCRIPT_STEM",
                        message=f"script stem '{stem}' appears in multiple skills: {skill_list}",
                    )
                )
    return issues


# ---------------------------------------------------------------------------
# Single-skill linter
# ---------------------------------------------------------------------------


def collect_scripts(skill_dir: Path) -> List[Path]:
    """Return all script files in skill_dir/scripts/."""
    scripts_dir = skill_dir / "scripts"
    if not scripts_dir.is_dir():
        return []
    return sorted(f for f in scripts_dir.iterdir() if f.is_file() and f.suffix.lower() in SUPPORTED_SCRIPT_EXTENSIONS)


def lint_skill(
    skill_dir: Path,
    all_skill_names: Set[str],
) -> Tuple[List[LintIssue], SkillInfo]:
    """Run all per-skill checks. Returns issues and SkillInfo for cross-skill checks."""
    skill_name = skill_dir.name
    skill_md = skill_dir / "SKILL.md"

    info = SkillInfo(name=skill_name, skill_dir=skill_dir, scripts=collect_scripts(skill_dir))

    if not skill_md.exists():
        return [
            LintIssue(
                skill=skill_name,
                file=str(skill_md),
                severity="ERROR",
                rule="NO_FRONTMATTER",
                message="SKILL.md does not exist",
            )
        ], info

    content = skill_md.read_text(encoding="utf-8")
    issues: List[LintIssue] = []

    # Check for conflict markers first — if present, YAML won't parse cleanly
    issues += check_conflict_markers(skill_dir, skill_name, content)
    if any(i.rule == "CONFLICT_MARKER" for i in issues):
        # Skip remaining checks that require parseable frontmatter
        return issues, info

    fm_issues, fm = check_frontmatter_parseable(skill_dir, skill_name, content)
    issues += fm_issues
    if fm is None:
        return issues, info

    issues += check_name_field(skill_dir, skill_name, fm)
    issues += check_dcc_field(skill_dir, skill_name, fm)
    issues += check_version_field(skill_dir, skill_name, fm)
    issues += check_description_field(skill_dir, skill_name, fm)
    issues += check_scripts_section(skill_dir, skill_name, content)
    issues += check_tools_source_files(skill_dir, skill_name, fm)
    issues += check_depends_exist(skill_dir, skill_name, fm, all_skill_names)
    issues += check_references_dir_wiring(skill_dir, skill_name, fm)
    issues += check_io_tool_descriptions(skill_dir, skill_name, fm)

    return issues, info


# ---------------------------------------------------------------------------
# Auto-fix
# ---------------------------------------------------------------------------


def fix_conflict_markers(skill_dir: Path) -> int:
    """Resolve conflict markers in SKILL.md by keeping origin/main side. Returns count."""
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        return 0
    content = skill_md.read_text(encoding="utf-8")
    count = len(CONFLICT_FULL_RE.findall(content))
    if count == 0:
        return 0
    resolved = CONFLICT_FULL_RE.sub(r"\2", content)
    skill_md.write_text(resolved, encoding="utf-8")
    return count


# ---------------------------------------------------------------------------
# Main linter runner
# ---------------------------------------------------------------------------


def lint_all(
    skills_root: Path,
    fix: bool = False,
    error_only: bool = False,
) -> List[LintIssue]:
    """Lint all skills under skills_root. If fix=True, auto-fix conflict markers first."""
    skill_dirs = sorted(d for d in skills_root.iterdir() if d.is_dir())
    all_skill_names: Set[str] = {d.name for d in skill_dirs}

    if fix:
        fixed_total = 0
        for skill_dir in skill_dirs:
            n = fix_conflict_markers(skill_dir)
            if n:
                print(f"  [FIX] {skill_dir.name}/SKILL.md: {n} conflict(s) resolved")
                fixed_total += n
        if fixed_total:
            print(f"  Fixed {fixed_total} conflict(s) total.\n")

    all_issues: List[LintIssue] = []
    all_info: List[SkillInfo] = []

    for skill_dir in skill_dirs:
        issues, info = lint_skill(skill_dir, all_skill_names)
        all_issues += issues
        all_info.append(info)

    # Cross-skill checks
    all_issues += check_duplicate_action_names(all_info)

    if error_only:
        all_issues = [i for i in all_issues if i.severity == "ERROR"]

    return all_issues


# ---------------------------------------------------------------------------
# Output formatting
# ---------------------------------------------------------------------------


def print_report(issues: List[LintIssue], skills_root: Path) -> None:
    """Print a human-readable lint report."""
    if not issues:
        print("All SKILL.md files passed lint checks.")
        return

    # Group by skill
    by_skill: Dict[str, List[LintIssue]] = {}
    for issue in issues:
        by_skill.setdefault(issue.skill, []).append(issue)

    error_count = sum(1 for i in issues if i.severity == "ERROR")
    warning_count = sum(1 for i in issues if i.severity == "WARNING")

    for skill_name, skill_issues in sorted(by_skill.items()):
        print(f"\n{skill_name}:")
        for issue in skill_issues:
            prefix = "  ERROR  " if issue.severity == "ERROR" else "  WARN   "
            # Make file path relative to CWD for readability
            try:
                rel_file = Path(issue.file).relative_to(Path.cwd())
            except ValueError:
                rel_file = Path(issue.file)
            print(f"{prefix}[{issue.rule}] {rel_file}: {issue.message}")

    print(f"\n--- Summary: {error_count} error(s), {warning_count} warning(s) across {len(by_skill)} skill(s) ---")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Lint SKILL.md files in the dcc-mcp-maya skills directory.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Auto-fix unresolved git merge conflict markers (keeps origin/main side)",
    )
    parser.add_argument(
        "--skills-root",
        default="src/dcc_mcp_maya/skills",
        help="Path to skills directory (default: src/dcc_mcp_maya/skills)",
    )
    parser.add_argument(
        "--error-only",
        action="store_true",
        help="Only report ERRORs, suppress WARNINGs",
    )
    args = parser.parse_args()

    skills_root = Path(args.skills_root)
    if not skills_root.is_dir():
        print(f"ERROR: skills root '{skills_root}' does not exist or is not a directory", file=sys.stderr)
        sys.exit(2)

    issues = lint_all(skills_root, fix=args.fix, error_only=args.error_only)
    print_report(issues, skills_root)

    error_count = sum(1 for i in issues if i.severity == "ERROR")
    sys.exit(0 if error_count == 0 else 1)


if __name__ == "__main__":
    main()
