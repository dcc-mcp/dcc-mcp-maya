"""
Migrate all skill scripts from dcc_mcp_maya.api to dcc_mcp_core.skill.

This script performs a clean, complete migration:
1. Replace maya_success -> skill_success
2. Replace maya_error -> skill_error
3. Replace maya_from_exception(exc, msg) -> skill_exception(exc, message=msg)
4. Add @skill_entry to main() as a safety net
5. Update __name__ == "__main__" to use run_main
6. Update imports to dcc_mcp_core.skill
7. Keep validation helpers (validate_node_exists etc.) in dcc_mcp_maya.api
8. Keep try/except structure intact (for test compatibility)

Usage:
    python tools/migrate_to_core_skill_api.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

VALIDATION_HELPERS = {"validate_node_exists", "validate_node_type", "batch_validate_nodes"}


def migrate_script(path: Path) -> tuple[bool, str]:
    content = path.read_text(encoding="utf-8")
    original = content

    # Only process files that use dcc_mcp_maya.api result functions
    has_old_api = bool(re.search(
        r"\b(maya_success|maya_error|maya_from_exception)\(",
        content,
    ))
    if not has_old_api:
        return False, "no old API calls"

    # ---- Step 1: Replace function call names ----
    content = content.replace("maya_success(", "skill_success(")
    content = content.replace("maya_error(", "skill_error(")
    # maya_from_exception(exc, "msg") -> skill_exception(exc, message="msg")
    # First: handle positional string message after exc
    content = re.sub(
        r"maya_from_exception\((\w+),\s*(f?\")",
        r"skill_exception(\1, message=\2",
        content,
    )
    # Then handle remaining maya_from_exception (no second arg or keyword args)
    content = content.replace("maya_from_exception(", "skill_exception(")

    # ---- Step 2: Update __name__ == "__main__" block ----
    if "run_main" not in content:
        main_block_re = re.compile(
            r'^if __name__ == "__main__":\n'
            r"(?:    import (?:json|json as \w+)\n\n?)?"
            r"(?:[ \t]*\n|    [^\n]*\n)*?"
            r"    print\([^\n]+\)\n?",  # greedy line match to handle nested parens
            re.MULTILINE,
        )
        new_main_block = (
            'if __name__ == "__main__":\n'
            "    from dcc_mcp_core.skill import run_main\n"
            "    run_main(main)\n"
        )
        if main_block_re.search(content):
            content = main_block_re.sub(new_main_block, content)

    # ---- Step 3: Add @skill_entry to main() ----
    if "def main(" in content and "@skill_entry" not in content:
        content = re.sub(
            r"^(def main\()",
            r"@skill_entry\ndef main(",
            content,
            count=1,
            flags=re.MULTILINE,
        )

    # ---- Step 4: Remove old dcc_mcp_maya.api result function imports ----
    # First extract what LOCAL helpers are still needed
    local_needed: set[str] = set()
    for h in VALIDATION_HELPERS:
        if h + "(" in content:
            local_needed.add(h)

    # Remove multi-line import blocks
    content = re.sub(
        r"^from dcc_mcp_maya\.api import \(\s*\n.*?\)\n",
        "",
        content,
        flags=re.MULTILINE | re.DOTALL,
    )
    # Remove single-line imports
    content = re.sub(
        r"^from dcc_mcp_maya\.api import [^\n]+\n",
        "",
        content,
        flags=re.MULTILINE,
    )
    # Remove any existing dcc_mcp_core.skill imports (will rebuild)
    content = re.sub(
        r"^from dcc_mcp_core\.skill import [^\n]+\n",
        "",
        content,
        flags=re.MULTILINE,
    )

    # ---- Step 5: Build new import lines ----
    skill_fns: set[str] = set()
    if "@skill_entry" in content:
        skill_fns.add("skill_entry")
    if "skill_success(" in content:
        skill_fns.add("skill_success")
    if "skill_error(" in content:
        skill_fns.add("skill_error")
    if "skill_exception(" in content:
        skill_fns.add("skill_exception")

    new_imports: list[str] = []
    if skill_fns:
        new_imports.append("from dcc_mcp_core.skill import " + ", ".join(sorted(skill_fns)))
    if local_needed:
        new_imports.append("from dcc_mcp_maya.api import " + ", ".join(sorted(local_needed)))

    import_block = "\n".join(new_imports) + "\n" if new_imports else ""

    # Insert after "# Import local modules" comment
    lc_re = re.compile(r"^(# Import local modules\n)", re.MULTILINE)
    if lc_re.search(content):
        content = lc_re.sub(r"\g<1>" + import_block, content, count=1)
    elif import_block:
        first_def = re.search(r"^(def |class )", content, re.MULTILINE)
        if first_def:
            content = content[: first_def.start()] + import_block + "\n" + content[first_def.start() :]

    # ---- Cleanup: collapse excessive blank lines ----
    content = re.sub(r"\n{4,}", "\n\n\n", content)

    if content != original:
        path.write_text(content, encoding="utf-8")
        return True, "migrated"
    return False, "no change"


def main() -> None:
    verbose = "--verbose" in sys.argv
    skills_dir = Path("src/dcc_mcp_maya/skills")
    all_scripts = sorted(skills_dir.rglob("scripts/*.py"))

    changed = unchanged = 0
    errors: list[tuple[Path, str]] = []

    for script in all_scripts:
        try:
            ok, reason = migrate_script(script)
            if ok:
                changed += 1
                if verbose:
                    print(f"  MIGRATED {script.relative_to('.')}")
            else:
                unchanged += 1
        except Exception as exc:
            errors.append((script, str(exc)))
            print(f"ERROR {script.relative_to('.')}: {exc}")

    print(f"Total  : {len(all_scripts)}")
    print(f"Changed: {changed}")
    print(f"Same   : {unchanged}")
    print(f"Errors : {len(errors)}")
    if errors:
        for f, e in errors:
            print(f"  {f.name}: {e}")


if __name__ == "__main__":
    main()
