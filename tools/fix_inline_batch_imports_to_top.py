"""Move 'from dcc_mcp_maya.api import batch_validate_nodes' from try-block to top-level.

These imports were inserted inside try blocks by fix_batch_validate_imports.py.
This script moves them to top-level, after the dcc_mcp_core.skill import.
"""

# Import built-in modules
import os
import re
import sys


INLINE_IMPORT = "        from dcc_mcp_maya.api import batch_validate_nodes  # noqa: PLC0415\n"
TOP_LEVEL_IMPORT = "from dcc_mcp_maya.api import batch_validate_nodes\n"


def fix_file(fpath):
    with open(fpath, encoding="utf-8") as f:
        content = f.read()

    # Check for indented import pattern
    if INLINE_IMPORT not in content:
        return 0

    # Already has top-level import? Just remove the inline one
    has_top = bool(re.search(r"^from dcc_mcp_maya\.api import.*batch_validate_nodes", content, re.MULTILINE))

    # Remove inline import
    content = content.replace(INLINE_IMPORT, "")

    if not has_top:
        # Insert at top level after 'from dcc_mcp_core.skill import ...'
        m = re.search(r"^from dcc_mcp_core\.skill import .*\n", content, re.MULTILINE)
        if m:
            content = content[: m.end()] + TOP_LEVEL_IMPORT + content[m.end():]
        else:
            # After last top-level import
            last = None
            for mm in re.finditer(r"^(?:import|from)\s+\S.*\n", content, re.MULTILINE):
                last = mm
            if last:
                content = content[: last.end()] + TOP_LEVEL_IMPORT + content[last.end():]
            else:
                content = TOP_LEVEL_IMPORT + content

    with open(fpath, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)

    print("  [OK] Moved inline import to top-level in {}".format(os.path.basename(fpath)))
    return 1


def main(src_root):
    total = 0
    for root, dirs, files in os.walk(src_root):
        dirs[:] = [d for d in dirs if d not in ("__pycache__", ".git")]
        for fname in sorted(files):
            if not fname.endswith(".py"):
                continue
            fpath = os.path.join(root, fname)
            total += fix_file(fpath)
    print("\nTotal files fixed: {}".format(total))


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "..", "src")
    main(os.path.abspath(src))
