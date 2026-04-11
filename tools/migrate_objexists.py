"""Migrate cmds.objExists guard patterns to validate_node_exists / batch_validate_nodes.

This tool performs text-based (regex) replacement rather than full AST rewriting,
which is safer given the highly uniform skill script structure.

Patterns transformed:
  1. Single-node guard:
       if not cmds.objExists(X):
           return skill_error(...)
     → becomes:
       err = validate_node_exists(cmds, X)
       if err:
           return err

  2. Already using validate_node_exists (skip).

Adds the import line if not already present:
    from dcc_mcp_maya.api import validate_node_exists

Usage:
    python tools/migrate_objexists.py [--dry-run] [path/to/skill.py ...]
"""

# Import built-in modules
import argparse
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------

# Match: if not cmds.objExists(EXPR):\n    return skill_error(MSG, DETAIL)
# Captures: EXPR (group 1), full original block (group 0)
# We handle the common 2-line and 3-line error return forms.

_SINGLE_GUARD_RE = re.compile(
    r"(?m)"
    r"^(?P<indent>[ \t]*)if not cmds\.objExists\((?P<expr>[^)]+)\):\n"
    r"(?P=indent)    return skill_error\([^)]*\)\n",
)

# Multiline skill_error call (with trailing comma / multiple lines)
_SINGLE_GUARD_MULTI_RE = re.compile(
    r"(?m)"
    r"^(?P<indent>[ \t]*)if not cmds\.objExists\((?P<expr>[^)]+)\):\n"
    r"(?P=indent)    return skill_error\(\n"
    r"(?:(?P=indent)        [^\n]+\n)+"
    r"(?P=indent)    \)\n",
)

_IMPORT_LINE = "from dcc_mcp_maya.api import validate_node_exists"
_BATCH_IMPORT_LINE = "from dcc_mcp_maya.api import batch_validate_nodes, validate_node_exists"
_VALIDATE_IMPORT_LINE = "from dcc_mcp_maya.api import validate_node_exists"


def _already_imported(source: str, symbol: str) -> bool:
    return symbol in source


def _add_import(source: str, import_line: str) -> str:
    """Insert import after the last 'from dcc_mcp_core' or 'from dcc_mcp_maya' import."""
    if import_line in source:
        return source  # already present

    # Find insertion point: after last dcc_mcp import block
    lines = source.splitlines(keepends=True)
    last_dcc_idx = -1
    for i, line in enumerate(lines):
        if line.startswith("from dcc_mcp_") or line.startswith("import dcc_mcp_"):
            last_dcc_idx = i

    if last_dcc_idx >= 0:
        lines.insert(last_dcc_idx + 1, import_line + "\n")
    else:
        # Fallback: insert after first import block
        for i, line in enumerate(lines):
            if line.startswith("from ") or line.startswith("import "):
                lines.insert(i + 1, import_line + "\n")
                break
    return "".join(lines)


def _replace_single_guards(source: str) -> tuple:
    """Replace single cmds.objExists guards. Returns (new_source, count)."""
    count = 0

    def replace_one_line(m: re.Match) -> str:
        nonlocal count
        indent = m.group("indent")
        expr = m.group("expr").strip()
        count += 1
        return (
            "{indent}err = validate_node_exists(cmds, {expr})\n"
            "{indent}if err:\n"
            "{indent}    return err\n"
        ).format(indent=indent, expr=expr)

    def replace_multi_line(m: re.Match) -> str:
        nonlocal count
        indent = m.group("indent")
        expr = m.group("expr").strip()
        count += 1
        return (
            "{indent}err = validate_node_exists(cmds, {expr})\n"
            "{indent}if err:\n"
            "{indent}    return err\n"
        ).format(indent=indent, expr=expr)

    # Try multi-line first (more specific), then single-line
    new_source = _SINGLE_GUARD_MULTI_RE.sub(replace_multi_line, source)
    new_source = _SINGLE_GUARD_RE.sub(replace_one_line, new_source)
    return new_source, count


def migrate_file(path: Path, dry_run: bool = False) -> tuple:
    """Migrate a single skill script. Returns (changed: bool, replacements: int)."""
    original = path.read_text(encoding="utf-8")
    source = original

    # Skip files that don't use objExists
    if "cmds.objExists" not in source:
        return False, 0

    # Skip if already fully migrated
    if "cmds.objExists" not in source:
        return False, 0

    new_source, count = _replace_single_guards(source)

    if count == 0:
        return False, 0

    # Add import if needed
    if "validate_node_exists" not in new_source:
        new_source = _add_import(new_source, _VALIDATE_IMPORT_LINE)
    elif "batch_validate_nodes" in new_source and "batch_validate_nodes" not in source:
        # batch was newly added; ensure both are imported
        if "from dcc_mcp_maya.api import validate_node_exists" in new_source:
            new_source = new_source.replace(
                "from dcc_mcp_maya.api import validate_node_exists",
                _BATCH_IMPORT_LINE,
            )

    if new_source == original:
        return False, 0

    if not dry_run:
        path.write_text(new_source, encoding="utf-8")
    return True, count


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Show what would be changed without writing")
    parser.add_argument("paths", nargs="*", help="Files or directories to process (default: src/)")
    args = parser.parse_args()

    root = Path(__file__).parent.parent
    if args.paths:
        candidates = []
        for p in args.paths:
            pp = Path(p)
            if pp.is_dir():
                candidates.extend(pp.rglob("*.py"))
            else:
                candidates.append(pp)
    else:
        candidates = list((root / "src" / "dcc_mcp_maya" / "skills").rglob("scripts/*.py"))

    total_files = 0
    total_replacements = 0
    for path in sorted(candidates):
        changed, count = migrate_file(path, dry_run=args.dry_run)
        if changed or (args.dry_run and count > 0):
            prefix = "[DRY-RUN] " if args.dry_run else ""
            print("{}  {} ({} replacement{})".format(prefix, path.relative_to(root), count, "s" if count != 1 else ""))
            total_files += 1
            total_replacements += count

    print("\n{} file{} modified, {} replacement{} total{}".format(
        total_files,
        "s" if total_files != 1 else "",
        total_replacements,
        "s" if total_replacements != 1 else "",
        " (dry-run)" if args.dry_run else "",
    ))


if __name__ == "__main__":
    main()
