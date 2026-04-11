"""Fix import lines that were incorrectly inserted inside if __name__ == '__main__' blocks.

The previous fix script mistakenly inserted:
    from dcc_mcp_maya.api import validate_node_exists
inside the indented block, causing IndentationErrors.

This script:
1. Removes the incorrectly placed import from inside the if __name__ block
2. Inserts it correctly after the last top-level import (before def/class/if __name__)
"""

# Import built-in modules
import re
from pathlib import Path

ROOT = Path(__file__).parent.parent
SKILLS_DIR = ROOT / "src" / "dcc_mcp_maya" / "skills"

VALIDATE_IMPORT = "from dcc_mcp_maya.api import validate_node_exists"
BATCH_IMPORT = "from dcc_mcp_maya.api import batch_validate_nodes, validate_node_exists"

# Patterns that indicate the import was placed incorrectly (with leading spaces/tabs)
_BAD_INDENT_RE = re.compile(r"^[ \t]+from dcc_mcp_maya\.api import .*validate_node_exists.*$", re.MULTILINE)


def fix_file(path: Path) -> bool:
    source = path.read_text(encoding="utf-8")

    uses_validate = "validate_node_exists" in source
    uses_batch = "batch_validate_nodes" in source
    if not uses_validate:
        return False

    # Check if there's a mis-indented import
    bad_matches = list(_BAD_INDENT_RE.finditer(source))

    # Also check if the import is inside the if __name__ block (no indentation but wrong position)
    lines = source.splitlines(keepends=True)

    # Find position of 'if __name__ == "__main__":'
    main_block_start = None
    for i, line in enumerate(lines):
        if re.match(r'^if __name__\s*==\s*["\']__main__["\']:', line):
            main_block_start = i
            break

    # Find if validate import exists and where
    validate_import_line = None
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("from dcc_mcp_maya.api import") and "validate_node_exists" in stripped:
            validate_import_line = i
            break

    needs_fix = False

    # Case 1: import has leading indentation (wrongly inside a block)
    if bad_matches:
        needs_fix = True

    # Case 2: import exists but is after the if __name__ block
    if (validate_import_line is not None and main_block_start is not None
            and validate_import_line > main_block_start):
        needs_fix = True

    if not needs_fix:
        return False

    # Step 1: Remove all existing dcc_mcp_maya.api imports (correct and incorrect)
    new_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("from dcc_mcp_maya.api import") and "validate_node_exists" in stripped:
            continue  # remove this line
        new_lines.append(line)

    # Step 2: Choose correct import line
    needs_batch = uses_batch
    import_to_add = BATCH_IMPORT if needs_batch else VALIDATE_IMPORT

    # Step 3: Find correct insertion point (after last top-level dcc_mcp import, before def/class)
    insert_after = -1
    for i, line in enumerate(new_lines):
        stripped = line.strip()
        # Top-level imports only (no leading whitespace)
        if line[0:1] not in (" ", "\t", "\n", "\r", "#", "\"", "'"):
            if stripped.startswith("from dcc_mcp_") or stripped.startswith("import dcc_mcp_"):
                insert_after = i

    if insert_after >= 0:
        new_lines.insert(insert_after + 1, import_to_add + "\n")
    else:
        # Fallback: insert after first top-level import
        for i, line in enumerate(new_lines):
            if line[0:1] not in (" ", "\t") and (line.startswith("from ") or line.startswith("import ")):
                new_lines.insert(i + 1, import_to_add + "\n")
                break

    new_source = "".join(new_lines)
    if new_source != source:
        path.write_text(new_source, encoding="utf-8")
        return True
    return False


def main():
    fixed = 0
    for path in sorted(SKILLS_DIR.rglob("scripts/*.py")):
        if fix_file(path):
            print("Fixed: {}".format(path.relative_to(ROOT)))
            fixed += 1
    print("\n{} file(s) fixed".format(fixed))


if __name__ == "__main__":
    main()
