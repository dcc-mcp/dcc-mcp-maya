"""Migrate remaining cmds.objExists node-guard patterns to validate_node_exists.

Only targets patterns of the form:
    if not cmds.objExists(VAR):
        return skill_error(...)
OR
    if not cmds.objExists(VAR):
        return <helper>(...)

Skips:
- Attribute probes: cmds.objExists("node.attr") or cmds.objExists(var + ".attr") patterns
- Positive checks: if cmds.objExists(...)
- Inline conditional expressions
"""

from __future__ import annotations

import os
import re
import sys

# Pattern: if not cmds.objExists(<expr>):
# where <expr> does NOT contain a "." (attribute probe)
# Single-line: matches "if not cmds.objExists(EXPR):\n    return skill_error(...)"
GUARD_PATTERN = re.compile(
    r'^(?P<indent>[ \t]+)if not cmds\.objExists\((?P<expr>[^)]+)\):\n'
    r'(?P=indent)    return (?P<ret_call>[^\n]+)',
    re.MULTILINE,
)

# Detect attribute probe: if expr contains "." or is a string literal with "."
ATTR_PROBE_RE = re.compile(r'\.')


def is_attribute_probe(expr: str) -> bool:
    """Return True if the expression looks like an attribute probe (node.attr)."""
    stripped = expr.strip().strip('"\'')
    # String literals with dots (e.g. "node.attr") or variable with "."
    if '.' in stripped:
        return True
    # Format strings like "{}.{}".format(...)
    if '.format(' in expr or '".' in expr or "'." in expr:
        return True
    return False


def has_validate_import(content: str) -> bool:
    return 'from dcc_mcp_maya.api import' in content and 'validate_node_exists' in content


def ensure_import(content: str) -> str:
    """Ensure validate_node_exists is imported from dcc_mcp_maya.api."""
    if has_validate_import(content):
        # Already imported, check if validate_node_exists is in import line
        import_re = re.compile(
            r'(from dcc_mcp_maya\.api import )([^\n]+)',
        )
        m = import_re.search(content)
        if m and 'validate_node_exists' not in m.group(2):
            new_imports = m.group(2).rstrip() + ', validate_node_exists'
            content = content[:m.start()] + m.group(1) + new_imports + content[m.end():]
        return content

    # Add import after last dcc_mcp_core import line
    core_import_re = re.compile(r'^from dcc_mcp_core[^\n]*\n', re.MULTILINE)
    matches = list(core_import_re.finditer(content))
    if matches:
        last = matches[-1]
        insert_pos = last.end()
        content = (
            content[:insert_pos]
            + 'from dcc_mcp_maya.api import validate_node_exists\n'
            + content[insert_pos:]
        )
        return content

    # Fallback: add after last import block
    import_re2 = re.compile(r'^(?:import |from )[^\n]+\n', re.MULTILINE)
    matches2 = list(import_re2.finditer(content))
    if matches2:
        last2 = matches2[-1]
        insert_pos = last2.end()
        content = (
            content[:insert_pos]
            + 'from dcc_mcp_maya.api import validate_node_exists\n'
            + content[insert_pos:]
        )
    return content


def migrate_file(path: str, dry_run: bool = False) -> int:
    """Migrate one file. Returns number of replacements made."""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            original = f.read()
    except Exception as e:
        print('  SKIP (read error): {}'.format(e))
        return 0

    content = original
    replacements = 0

    for m in list(GUARD_PATTERN.finditer(content)):
        expr = m.group('expr').strip()
        indent = m.group('indent')
        ret_call = m.group('ret_call')

        if is_attribute_probe(expr):
            continue

        # Build replacement
        new_block = (
            '{indent}err = validate_node_exists(cmds, {expr})\n'
            '{indent}if err:\n'
            '{indent}    return err'
        ).format(indent=indent, expr=expr)

        content = content.replace(m.group(0), new_block, 1)
        replacements += 1

    if replacements == 0:
        return 0

    # Ensure import is present
    content = ensure_import(content)

    if not dry_run:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)

    return replacements


def main() -> None:
    dry_run = '--dry-run' in sys.argv
    src_root = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'src')

    total_files = 0
    total_replacements = 0

    for root, dirs, files in os.walk(src_root):
        for fname in files:
            if not fname.endswith('.py'):
                continue
            path = os.path.join(root, fname)
            # Skip api.py — it IS the implementation of validate_node_exists
            if os.path.basename(root) == 'dcc_mcp_maya' and fname == 'api.py':
                continue
            try:
                with open(path, encoding='utf-8') as f:
                    content = f.read()
            except Exception:
                continue

            if 'cmds.objExists' not in content:
                continue

            count = migrate_file(path, dry_run=dry_run)
            if count > 0:
                rel = os.path.relpath(path, src_root)
                print('  {:3d}  {}'.format(count, rel))
                total_files += 1
                total_replacements += count

    mode = 'DRY RUN' if dry_run else 'APPLIED'
    print('\n[{}] {} replacements across {} files'.format(mode, total_replacements, total_files))


if __name__ == '__main__':
    main()
