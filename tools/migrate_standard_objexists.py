"""Migrate standard single-node if not cmds.objExists patterns to validate_node_exists."""
import re
import os


# Pattern: blank line + if not cmds.objExists(VAR):\n+indent return skill_error("... {}", .format(VAR))
PATTERN = re.compile(
    r'( +)if not cmds\.objExists\((\w+)\):\n'
    r'\1    return skill_error\("([^"]+): \{\}"\.format\(\2\)\)',
    re.MULTILINE,
)


def replacement(m):
    indent = m.group(1)
    var = m.group(2)
    return (
        f"{indent}err = validate_node_exists(cmds, {var})\n"
        f"{indent}if err:\n"
        f"{indent}    return err"
    )


def ensure_import(text):
    if "batch_validate_nodes" in text and "validate_node_exists" in text:
        # already has both
        return text
    if "from dcc_mcp_maya.api import validate_node_exists" in text:
        return text
    if "from dcc_mcp_maya.api import batch_validate_nodes, validate_node_exists" in text:
        return text
    if "from dcc_mcp_maya.api import" in text:
        # just ensure validate_node_exists is in there
        text = re.sub(
            r'from dcc_mcp_maya\.api import ([^\n]+)',
            lambda m: m.group(0) if 'validate_node_exists' in m.group(1) 
                      else m.group(0).rstrip() + ', validate_node_exists',
            text,
        )
        return text
    # add new import after dcc_mcp_core skill import
    return text.replace(
        "from dcc_mcp_core.skill import skill_error, skill_exception, skill_success\n",
        "from dcc_mcp_core.skill import skill_error, skill_exception, skill_success\n"
        "\nfrom dcc_mcp_maya.api import validate_node_exists\n",
    )


def migrate_file(path):
    text = open(path, encoding="utf-8").read()
    new_text, n = PATTERN.subn(replacement, text)
    if n:
        new_text = ensure_import(new_text)
        open(path, "w", encoding="utf-8").write(new_text)
    return n


TARGETS = [
    "src/dcc_mcp_maya/skills/maya-scripting/scripts/mesh_ops.py",
    "src/dcc_mcp_maya/skills/maya-scripting/scripts/rigging.py",
    "src/dcc_mcp_maya/skills/maya-scripting/scripts/lighting.py",
    "src/dcc_mcp_maya/skills/maya-scripting/scripts/cameras.py",
    "src/dcc_mcp_maya/skills/maya-scripting/scripts/node_attrs.py",
]

total = 0
for t in TARGETS:
    if not os.path.exists(t):
        print(f"  SKIP: {t}")
        continue
    n = migrate_file(t)
    c_after = open(t, encoding="utf-8").read().count("cmds.objExists")
    print(f"  {t}: {n} replaced, {c_after} remaining")
    total += n

print(f"Total: {total}")
