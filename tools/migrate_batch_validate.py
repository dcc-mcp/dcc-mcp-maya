"""Migrate multi-object objExists patterns to batch_validate_nodes in specific files.

Handles patterns like:
    missing = [o for o in objects if not cmds.objExists(o)]
    if missing:
        return skill_error("Object(s) not found: ...")
        
->  err = batch_validate_nodes(cmds, objects)
    if err:
        return err
"""
import re
import os


# --- Pattern: missing = [o for o in VAR if not cmds.objExists(o)]\n
#              if missing:\n
#                  return skill_error("...: {}", ..., missing...)
MULTI_PATTERN = re.compile(
    r'( +)missing = \[(\w+) for \2 in (\w+) if not cmds\.objExists\(\2\)\]\n'
    r'\1if missing:\n'
    r'\1    return skill_error\(\n'
    r'\1        "[^"]+: \{\}"\.format\(", "\.join\(missing\)\),\n'
    r'\1        "[^"]+: \{\}"\.format\(", "\.join\(missing\)\),\n'
    r'\1    \)',
    re.MULTILINE,
)

MULTI_PATTERN2 = re.compile(
    r'( +)missing = \[(\w+) for \2 in (\w+) if not cmds\.objExists\(\2\)\]\n'
    r'\1if missing:\n'
    r'\1    return skill_error\(\n'
    r'\1        "([^"]+): \{\}"\.format\(", "\.join\(missing\)\),\n'
    r'\1        "([^"]+): \{\}"\.format\(", "\.join\(missing\)\),\n'
    r'\1    \)',
    re.MULTILINE,
)


def migrate_file(path):
    text = open(path, encoding="utf-8").read()
    orig = text
    
    # Check if already imports batch_validate_nodes
    needs_import = "batch_validate_nodes" not in text and "cmds.objExists" in text

    # Simple single-var: for name in (source, target) loop already handled
    # Handle [x for x in LIST if not cmds.objExists(x)] patterns
    def replace_list_missing(m):
        indent = m.group(1)
        var_name = m.group(2)
        list_name = m.group(3)
        return (
            f"{indent}err = batch_validate_nodes(cmds, list({list_name}))\n"
            f"{indent}if err:\n"
            f"{indent}    return err"
        )
    
    # Pattern A: missing check with 2-line skill_error
    PAT = re.compile(
        r'( +)missing = \[(\w+) for \2 in (\w+) if not cmds\.objExists\(\2\)\]\n'
        r'\1if missing:\n'
        r'\1    return skill_error\(\n'
        r'(?:.*\n){1,3}'  # 1-3 lines of error content
        r'\1    \)',
        re.MULTILINE,
    )
    
    # Simpler: just replace the pattern mechanically
    # missing = [X for X in LIST if not cmds.objExists(X)]
    MISSING_LINE = re.compile(
        r'( +)missing(?:_\w+)? = \[(\w+) for \2 in (\w+) if not cmds\.objExists\(\2\)\]\n'
        r'\1if missing(?:_\w+)?:\n'
        r'(\1    return skill_error\([^\)]+\))',
        re.MULTILINE,
    )
    
    count = 0
    # Replace missing list patterns with batch_validate_nodes
    def replace_missing(m):
        nonlocal count
        indent = m.group(1)
        var_name = m.group(2)
        list_name = m.group(3)
        count += 1
        return (
            f"{indent}err = batch_validate_nodes(cmds, list({list_name}))\n"
            f"{indent}if err:\n"
            f"{indent}    return err"
        )
    
    text = MISSING_LINE.sub(replace_missing, text)
    
    if count and needs_import:
        # Add batch_validate_nodes to import
        text = text.replace(
            "from dcc_mcp_maya.api import validate_node_exists",
            "from dcc_mcp_maya.api import batch_validate_nodes, validate_node_exists",
        )
        if "from dcc_mcp_maya.api import" not in text:
            # Add after dcc_mcp_core import
            text = text.replace(
                "from dcc_mcp_core.skill import",
                "from dcc_mcp_core.skill import",
            )
    elif count and "batch_validate_nodes" not in text:
        if "from dcc_mcp_maya.api import validate_node_exists" in text:
            text = text.replace(
                "from dcc_mcp_maya.api import validate_node_exists",
                "from dcc_mcp_maya.api import batch_validate_nodes, validate_node_exists",
            )
        else:
            # Insert new import
            text = text.replace(
                "from dcc_mcp_core.skill import skill_error, skill_exception, skill_success\n",
                "from dcc_mcp_core.skill import skill_error, skill_exception, skill_success\n\nfrom dcc_mcp_maya.api import batch_validate_nodes, validate_node_exists\n",
            )
    
    if text != orig:
        open(path, "w", encoding="utf-8").write(text)
    return count


TARGETS = [
    "src/dcc_mcp_maya/skills/maya-scripting/scripts/deformer_advanced.py",
    "src/dcc_mcp_maya/skills/maya-scripting/scripts/mesh_ops.py",
    "src/dcc_mcp_maya/skills/maya-scripting/scripts/rigging.py",
    "src/dcc_mcp_maya/skills/maya-scripting/scripts/dynamics.py",
    "src/dcc_mcp_maya/skills/maya-scripting/scripts/lighting.py",
    "src/dcc_mcp_maya/skills/maya-scripting/scripts/cameras.py",
    "src/dcc_mcp_maya/skills/maya-scripting/scripts/animation.py",
    "src/dcc_mcp_maya/skills/maya-scripting/scripts/sets.py",
    "src/dcc_mcp_maya/skills/maya-scripting/scripts/node_attrs.py",
]

total = 0
for t in TARGETS:
    if not os.path.exists(t):
        print(f"  SKIP (not found): {t}")
        continue
    n = migrate_file(t)
    c_after = open(t, encoding="utf-8").read().count("cmds.objExists")
    print(f"  {t}: {n} patterns replaced, {c_after} remaining")
    total += n

print(f"Total: {total}")
