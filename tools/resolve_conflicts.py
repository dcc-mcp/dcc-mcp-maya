"""Batch resolve merge conflicts by taking the 'theirs' (origin/main) side."""

import re
import sys
from pathlib import Path

CONFLICT_PATTERN = re.compile(
    r"<<<<<<< HEAD\n(.*?)=======\n(.*?)>>>>>>> origin/main\n",
    re.DOTALL,
)


def resolve_file(path: Path) -> int:
    """Resolve all conflicts in *path* by keeping the 'theirs' side.

    Returns number of conflicts resolved.
    """
    text = path.read_text(encoding="utf-8")
    count = len(CONFLICT_PATTERN.findall(text))
    if count == 0:
        return 0
    resolved = CONFLICT_PATTERN.sub(r"\2", text)
    path.write_text(resolved, encoding="utf-8")
    return count


def main():
    roots = [Path("src"), Path("tests")]
    total_files = 0
    total_conflicts = 0
    for root in roots:
        for py_file in root.rglob("*.py"):
            n = resolve_file(py_file)
            if n:
                print(f"  {py_file}: {n} conflict(s) resolved")
                total_files += 1
                total_conflicts += n
        for md_file in root.rglob("*.md"):
            n = resolve_file(md_file)
            if n:
                print(f"  {md_file}: {n} conflict(s) resolved")
                total_files += 1
                total_conflicts += n
    print(f"\nTotal: {total_files} files, {total_conflicts} conflicts resolved.")


if __name__ == "__main__":
    main()
