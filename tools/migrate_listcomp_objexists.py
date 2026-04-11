"""Migrate list-comprehension cmds.objExists patterns to batch_validate_nodes.

Target pattern (2+ lines):
    missing = [... for ... if not cmds.objExists(...)]
    if missing:
        return skill_error(...)

Replaces with:
    err = batch_validate_nodes(cmds, list(<iterable>))
    if err:
        return err

Skips positive-filter patterns (existing = [... if cmds.objExists(...)]).
Skips clean_mocap_keys.py (intentional positive filter).
"""

# Import built-in modules
import os
import re
import sys

# Files to skip (intentional positive-filter logic)
SKIP_FILES = {
    "clean_mocap_keys.py",
}

# Pattern: missing = [VAR for VAR in ITERABLE if not cmds.objExists(VAR)]
# Group 1: var, Group 2: iterable
LIST_COMP_PATTERN = re.compile(
    r"^(\s*)"  # indentation
    r"missing\s*=\s*\["
    r"\w+\s+for\s+(\w+)\s+in\s+([\w_]+)\s+"
    r"if\s+not\s+cmds\.objExists\(\2\)"
    r"\]",
    re.MULTILINE,
)

# Pattern for the subsequent if missing: block (2 lines):
#   if missing:
#       return skill_error(...)
IF_MISSING_PATTERN = re.compile(
    r"\n(\s*)if\s+missing\s*:\s*\n"
    r"(\s+)return\s+skill_error\([^)]+\)",
    re.DOTALL,
)

IMPORT_LINE = "from dcc_mcp_maya.api import batch_validate_nodes\n"


def has_import(content):
    return "batch_validate_nodes" in content


def insert_import(content):
    """Insert batch_validate_nodes import after the last dcc_mcp_maya.api or dcc_mcp_core import."""
    # Try to insert after existing dcc_mcp_maya.api import
    match = re.search(r"^from dcc_mcp_maya\.api import .*\n", content, re.MULTILINE)
    if match:
        pos = match.end()
        # Check if already imported on same line
        if "batch_validate_nodes" not in match.group():
            existing = match.group().rstrip("\n")
            new_line = existing.rstrip() + "\n" + IMPORT_LINE
            return content[: match.start()] + new_line + content[pos:]
    # Otherwise insert after last dcc_mcp_core.skill import
    match = re.search(r"^from dcc_mcp_core\.skill import .*\n", content, re.MULTILINE)
    if match:
        pos = match.end()
        return content[:pos] + IMPORT_LINE + content[pos:]
    # Fallback: insert after last import block
    last_import = None
    for m in re.finditer(r"^(?:import|from)\s+.*\n", content, re.MULTILINE):
        last_import = m
    if last_import:
        pos = last_import.end()
        return content[:pos] + IMPORT_LINE + content[pos:]
    return IMPORT_LINE + content


def migrate_file(fpath):
    with open(fpath, encoding="utf-8") as f:
        original = f.read()

    content = original
    changes = 0

    # Find all list-comp patterns and replace
    # We do a line-by-line scan for robustness
    lines = content.splitlines(keepends=True)
    new_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        # Check for: missing = [VAR for VAR in ITERABLE if not cmds.objExists(VAR)]
        m = re.match(
            r"^(\s*)missing\s*=\s*\[\s*(\w+)\s+for\s+(\w+)\s+in\s+([\w_]+)\s+if\s+not\s+cmds\.objExists\(\3\)\s*\]",
            line,
        )
        if m:
            indent = m.group(1)
            iterable = m.group(4)

            # Look for the next 2 lines: "if missing:" + "return skill_error(...)"
            # Could span multiple lines if skill_error has line continuation
            j = i + 1
            # Skip blank lines
            while j < len(lines) and lines[j].strip() == "":
                j += 1

            if_line = lines[j] if j < len(lines) else ""
            if re.match(r"\s*if\s+missing\s*:", if_line):
                # Find the return skill_error block (might be multiline)
                k = j + 1
                # Collect lines until we see 'return skill_error' closed
                skill_error_lines = []
                paren_depth = 0
                while k < len(lines):
                    sl = lines[k]
                    skill_error_lines.append(sl)
                    paren_depth += sl.count("(") - sl.count(")")
                    if "return skill_error" in sl or skill_error_lines:
                        if paren_depth <= 0 and skill_error_lines:
                            break
                    k += 1

                # Replace the entire block
                # line i → err = batch_validate_nodes(cmds, list(iterable))
                # lines i+1 to k → if err:\n    return err
                replacement = (
                    "{}err = batch_validate_nodes(cmds, list({}))\n"
                    "{}if err:\n"
                    "{}    return err\n"
                ).format(indent, iterable, indent, indent)
                new_lines.append(replacement)
                changes += 1
                i = k + 1
                continue

        # Also handle: missing_X = [VAR for VAR in ITERABLE if not cmds.objExists(VAR)]
        m2 = re.match(
            r"^(\s*)(missing\w*)\s*=\s*\[\s*(\w+)\s+for\s+(\w+)\s+in\s+([\w_]+)\s+if\s+not\s+cmds\.objExists\(\4\)\s*\]",
            line,
        )
        if m2:
            indent = m2.group(1)
            var_name = m2.group(2)
            iterable = m2.group(5)

            j = i + 1
            while j < len(lines) and lines[j].strip() == "":
                j += 1

            if_line = lines[j] if j < len(lines) else ""
            if re.match(r"\s*if\s+" + re.escape(var_name) + r"\s*:", if_line):
                k = j + 1
                skill_error_lines = []
                paren_depth = 0
                while k < len(lines):
                    sl = lines[k]
                    skill_error_lines.append(sl)
                    paren_depth += sl.count("(") - sl.count(")")
                    if "return skill_error" in sl or skill_error_lines:
                        if paren_depth <= 0 and skill_error_lines:
                            break
                    k += 1

                replacement = (
                    "{}err = batch_validate_nodes(cmds, list({}))\n"
                    "{}if err:\n"
                    "{}    return err\n"
                ).format(indent, iterable, indent, indent)
                new_lines.append(replacement)
                changes += 1
                i = k + 1
                continue

        new_lines.append(line)
        i += 1

    if changes == 0:
        return 0

    content = "".join(new_lines)

    # Add import if needed
    if not has_import(content):
        content = insert_import(content)

    with open(fpath, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)

    print("  [{}] {} replacement(s) in {}".format("OK", changes, os.path.basename(fpath)))
    return changes


def main(src_root):
    total = 0
    for root, dirs, files in os.walk(src_root):
        # Skip tools and test dirs
        dirs[:] = [d for d in dirs if d not in ("__pycache__", ".git")]
        for fname in sorted(files):
            if not fname.endswith(".py"):
                continue
            if fname in SKIP_FILES:
                continue
            fpath = os.path.join(root, fname)
            total += migrate_file(fpath)
    print("\nTotal replacements: {}".format(total))


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "..", "src")
    main(os.path.abspath(src))
