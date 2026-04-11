"""Fix missing validate_node_exists imports in migrated skill scripts.

For every script that calls validate_node_exists but does NOT have the import,
insert the import after the last dcc_mcp_core import line.
"""

# Import built-in modules
from pathlib import Path

ROOT = Path(__file__).parent.parent
SKILLS_DIR = ROOT / "src" / "dcc_mcp_maya" / "skills"
IMPORT_LINE = "from dcc_mcp_maya.api import validate_node_exists\n"
BATCH_IMPORT_LINE = "from dcc_mcp_maya.api import batch_validate_nodes, validate_node_exists\n"


def fix_file(path: Path) -> bool:
    source = path.read_text(encoding="utf-8")

    uses_validate = "validate_node_exists" in source
    uses_batch = "batch_validate_nodes" in source
    has_validate_import = "from dcc_mcp_maya.api import" in source and "validate_node_exists" in source

    if not uses_validate:
        return False
    if has_validate_import:
        return False  # already correct

    # Determine which import to add
    if uses_batch and "from dcc_mcp_maya.api import" not in source:
        import_to_add = BATCH_IMPORT_LINE
    else:
        import_to_add = IMPORT_LINE

    lines = source.splitlines(keepends=True)

    # Find insertion point: after the last 'from dcc_mcp_' import line
    last_dcc_idx = -1
    for i, line in enumerate(lines):
        stripped = line.lstrip()
        if stripped.startswith("from dcc_mcp_") or stripped.startswith("import dcc_mcp_"):
            last_dcc_idx = i

    if last_dcc_idx >= 0:
        lines.insert(last_dcc_idx + 1, import_to_add)
    else:
        # Fallback: after first import block
        for i, line in enumerate(lines):
            stripped = line.lstrip()
            if stripped.startswith("from ") or stripped.startswith("import "):
                lines.insert(i + 1, import_to_add)
                break

    new_source = "".join(lines)
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
