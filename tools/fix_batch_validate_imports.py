"""Add 'from dcc_mcp_maya.api import batch_validate_nodes' import to files that use it.

Strategy: Insert after 'import maya.cmds as cmds' inside the try block,
since these skill scripts use late (inside-try) imports for Maya modules.
"""

# Import built-in modules
import os
import re
import sys


IMPORT_STMT = "        from dcc_mcp_maya.api import batch_validate_nodes  # noqa: PLC0415\n"


def fix_file(fpath):
    with open(fpath, encoding="utf-8") as f:
        content = f.read()

    # Skip if already has the import
    if "from dcc_mcp_maya.api import batch_validate_nodes" in content:
        return 0

    # Skip if no batch_validate_nodes usage
    if "batch_validate_nodes" not in content:
        return 0

    # Insert after the line: "        import maya.cmds as cmds  # noqa: PLC0415"
    pattern = r"(        import maya\.cmds as cmds.*\n)"
    replacement = r"\1" + IMPORT_STMT
    new_content, count = re.subn(pattern, replacement, content, count=1)

    if count == 0:
        # Try 8-space variant without noqa
        pattern2 = r"(        import maya\.cmds as cmds\n)"
        new_content, count = re.subn(pattern2, replacement, content, count=1)

    if count == 0:
        print("  [SKIP] Could not find maya.cmds import in {}".format(os.path.basename(fpath)))
        return 0

    with open(fpath, "w", encoding="utf-8", newline="\n") as f:
        f.write(new_content)

    print("  [OK] Fixed imports in {}".format(os.path.basename(fpath)))
    return 1


def main(src_root):
    total = 0
    for root, dirs, files in os.walk(src_root):
        dirs[:] = [d for d in dirs if d not in ("__pycache__", ".git")]
        for fname in sorted(files):
            if not fname.endswith(".py"):
                continue
            fpath = os.path.join(root, fname)
            content = open(fpath, encoding="utf-8").read()
            if "batch_validate_nodes(cmds," in content:
                total += fix_file(fpath)
    print("\nTotal files fixed: {}".format(total))


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "..", "src")
    main(os.path.abspath(src))
