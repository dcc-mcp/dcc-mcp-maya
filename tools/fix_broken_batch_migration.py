"""Fix broken batch_validate_nodes migrations - remove dangling error call residues."""
import re
import os


# Pattern: return err followed by residue from the old skill_error call
# Possible forms:
#   return err),
#       "...",
#   )
# or
#   return err not found: {}".format(", ".join(missing)),
#       "...",
#   )

BROKEN_PATTERN = re.compile(
    r'( +)(return err[^\n]+\n'     # return err + junk
    r'(?:\1 {4}[^\n]+\n)*'         # optional continuation lines
    r'\1    \))',                    # closing paren
    re.MULTILINE,
)

def fix_return_err(m):
    indent = m.group(1)
    return f"{indent}return err"


def fix_file(path):
    text = open(path, encoding="utf-8").read()
    # Replace "return err)," or "return err not found..." patterns
    # Simpler: find lines that match "return err" followed by junk
    lines = text.split("\n")
    new_lines = []
    i = 0
    fixed = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.lstrip()
        # Detect broken line: starts with "return err" but has extra content
        if stripped.startswith("return err") and stripped != "return err" and not stripped.startswith("return err:"):
            # This is a broken replacement — just emit "return err"
            indent = line[: len(line) - len(line.lstrip())]
            new_lines.append(f"{indent}return err")
            fixed += 1
            # Skip continuation lines until the matching closing paren
            i += 1
            while i < len(lines):
                cl = lines[i]
                cs = cl.strip()
                # Stop when we hit a line that is: empty, or starts a new statement
                # (not a string continuation or closing paren)
                if cs == ")" or cs == "),":
                    i += 1  # consume the closing paren too
                    break
                if cs and not cs.startswith('"') and not cs.startswith("'") and cs != ")":
                    break  # don't consume this line
                i += 1
            continue
        new_lines.append(line)
        i += 1
    
    if fixed:
        open(path, "w", encoding="utf-8").write("\n".join(new_lines))
    return fixed


TARGETS = [
    "src/dcc_mcp_maya/skills/maya-scripting/scripts/animation.py",
    "src/dcc_mcp_maya/skills/maya-scripting/scripts/deformer_advanced.py",
    "src/dcc_mcp_maya/skills/maya-scripting/scripts/dynamics.py",
    "src/dcc_mcp_maya/skills/maya-scripting/scripts/rigging.py",
    "src/dcc_mcp_maya/skills/maya-scripting/scripts/sets.py",
]

for t in TARGETS:
    n = fix_file(t)
    print(f"  {t}: fixed {n} broken lines")
