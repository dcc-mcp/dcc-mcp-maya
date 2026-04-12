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


def check_dcc_field(skill_dir: Path, skill_name: str, fm: dict) -> List[LintIssue]:
    issues: List[LintIssue] = []
    file_path = str(skill_dir / "SKILL.md")
    dcc = fm.get("dcc", "python")

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
    version = fm.get("version", "1.0.0")
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


def check_tools_source_files(skill_dir: Path, skill_name: str, fm: dict) -> List[LintIssue]:
    """Warn if tools[].source_file paths don't exist in scripts/ dir."""
    issues: List[LintIssue] = []
    tools = fm.get("tools", [])
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
    depends = fm.get("depends", [])
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
