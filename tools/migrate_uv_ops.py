"""Migrate remaining cmds.objExists patterns in uv_ops.py and other files."""
import re
import os


PATTERN = r'        if not cmds\.objExists\((\w+)\):\n            return skill_error\("Object not found: \{\}"\.format\(\1\)\)'
REPLACEMENT = r'        err = validate_node_exists(cmds, \1)\n        if err:\n            return err'


def migrate_file(path):
    text = open(path, encoding="utf-8").read()
    new_text, n = re.subn(PATTERN, REPLACEMENT, text)
    if n:
        open(path, "w", encoding="utf-8").write(new_text)
    return n


TARGETS = [
    "src/dcc_mcp_maya/skills/maya-scripting/scripts/uv_ops.py",
    "src/dcc_mcp_maya/skills/maya-scripting/scripts/vertex_color.py",
]

total = 0
for t in TARGETS:
    n = migrate_file(t)
    print(f"  {t}: {n} replacements")
    total += n

print(f"Total: {total}")
