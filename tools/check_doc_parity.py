#!/usr/bin/env python3
"""CI lint that keeps the EN docs and the ZH translation section-parallel.

Scope (issue #88)
-----------------
Every ``docs/<path>.md`` (excluding ``docs/zh/**`` and ``docs/node_modules/**``)
must have a mirror file at ``docs/zh/<path>.md``, and the two must share
the same ordered sequence of ATX headings (``#`` … ``######``) at the
same depth.

What we check
-------------
* **Mirror existence** — a ZH file must exist for every non-index EN
  file under ``docs/guide/`` and ``docs/api/``. Missing mirrors fail
  loudly so translations cannot silently drift out of sync.
* **Heading parity** — we parse ATX headings and compare the list of
  ``(depth, order)`` tuples between EN and ZH.  Heading *text* is not
  compared because translations rightly change the wording; only the
  *structure* must stay identical so section links keep working and
  reviewers can trust that both versions cover the same material.
* **Fenced code block parity** — the number of fenced blocks (triple
  backticks or triple tildes) must match, because a dropped fence in
  either side usually means the translator accidentally ate a code
  sample.

The check is intentionally structural, not semantic.  It exists to catch
the most common translation drift (new EN section not yet translated,
ZH file still on an older heading outline) without demanding the
translator match headings word-for-word.

Usage
-----
    python tools/check_doc_parity.py
    python tools/check_doc_parity.py --docs-root docs
    python tools/check_doc_parity.py --allowlist tools/doc_parity_allowlist.txt

Allowlist
---------
Existing drift is grandfathered via ``tools/doc_parity_allowlist.txt`` —
each line is a POSIX-style doc path (relative to ``docs/``) whose ZH
mirror is exempt from the structural check.  New docs are not exempt,
so drift can only shrink over time.  Remove a path from the allowlist
once the ZH translation has been brought back in sync.

Exit codes
----------
    0  all EN docs have a section-parallel ZH mirror
    1  one or more mismatches found
    2  internal / argument error
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

# ATX headings only (``#``-prefixed).  Setext headings (``===`` / ``---``
# underlines) are intentionally ignored: VitePress-authored docs in this
# repo do not use them, and an incidental ``---`` underline inside a code
# block would otherwise trip the lint.
_HEADING_RE = re.compile(r"^(#{1,6})\s+\S")
_FENCE_RE = re.compile(r"^(```|~~~)")

# Paths under ``docs/`` that we never mirror (vendored tooling output /
# landing pages owned separately by VitePress).
_SKIP_DIRS = ("node_modules", "zh")
_INDEX_FILES = {"index.md"}


@dataclass(frozen=True)
class DocMetrics:
    headings: Tuple[Tuple[int, int], ...]  # (depth, running_index) pairs
    fences: int


def _iter_en_docs(docs_root: Path) -> Iterable[Path]:
    """Yield every EN Markdown file under ``docs_root`` that should have a ZH mirror."""
    for path in sorted(docs_root.rglob("*.md")):
        rel = path.relative_to(docs_root)
        # Filter out vendored + translated trees.
        if any(part in _SKIP_DIRS for part in rel.parts):
            continue
        # ``docs/index.md`` is the landing page — the ZH index lives at
        # ``docs/zh/index.md`` and is authored independently; skip it.
        if rel.name in _INDEX_FILES and len(rel.parts) == 1:
            continue
        yield path


def _parse_metrics(path: Path) -> DocMetrics:
    """Extract the ``(depth, order)`` heading tuple list and fence count.

    Headings inside fenced code blocks are ignored — otherwise a commented
    ``# sample`` line inside a shell snippet would pollute the comparison.
    """
    headings: List[Tuple[int, int]] = []
    in_fence = False
    fences = 0
    order = 0
    text = path.read_text(encoding="utf-8", errors="replace")
    for line in text.splitlines():
        stripped = line.strip()
        if _FENCE_RE.match(stripped):
            in_fence = not in_fence
            fences += 1
            continue
        if in_fence:
            continue
        m = _HEADING_RE.match(stripped)
        if not m:
            continue
        depth = len(m.group(1))
        headings.append((depth, order))
        order += 1
    return DocMetrics(headings=tuple(headings), fences=fences)


def _format_headings_diff(en: DocMetrics, zh: DocMetrics) -> str:
    """Render a small textual diff of the two heading outlines."""
    en_depths = [d for d, _ in en.headings]
    zh_depths = [d for d, _ in zh.headings]
    return "    EN outline ({n_en} headings): {en}\n    ZH outline ({n_zh} headings): {zh}".format(
        n_en=len(en.headings),
        n_zh=len(zh.headings),
        en=" ".join("H{}".format(d) for d in en_depths) or "(none)",
        zh=" ".join("H{}".format(d) for d in zh_depths) or "(none)",
    )


def _load_allowlist(path: Optional[Path]) -> set:
    """Load the allowlist file — returns an empty set when no path given."""
    if path is None or not path.exists():
        return set()
    out = set()
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        out.add(line)
    return out


def check_parity(docs_root: Path, allowlist: Optional[set] = None) -> List[str]:
    """Return a list of human-readable error strings; empty means OK."""
    errors: List[str] = []
    allowlist = allowlist or set()
    zh_root = docs_root / "zh"
    for en_path in _iter_en_docs(docs_root):
        rel = en_path.relative_to(docs_root)
        rel_posix = rel.as_posix()
        zh_path = zh_root / rel
        if not zh_path.exists():
            # Missing mirrors are always reported — allowlist exempts
            # structural drift only, never an entirely untranslated file,
            # because a silently missing translation is the worst failure
            # mode this lint is meant to prevent.
            errors.append("MISSING ZH: {en} has no mirror at docs/zh/{rel}".format(en=rel_posix, rel=rel_posix))
            continue

        if rel_posix in allowlist:
            continue

        en_metrics = _parse_metrics(en_path)
        zh_metrics = _parse_metrics(zh_path)

        # Heading parity — compare depth-only, not text, so translations
        # are free to reword as long as the outline matches.
        en_depths = [d for d, _ in en_metrics.headings]
        zh_depths = [d for d, _ in zh_metrics.headings]
        if en_depths != zh_depths:
            errors.append(
                "HEADING MISMATCH: docs/{rel} vs docs/zh/{rel}\n{diff}".format(
                    rel=rel_posix,
                    diff=_format_headings_diff(en_metrics, zh_metrics),
                )
            )

        if en_metrics.fences != zh_metrics.fences:
            errors.append(
                "FENCE MISMATCH: docs/{rel} has {n_en} code fences but "
                "docs/zh/{rel} has {n_zh} — check for dropped fences".format(
                    rel=rel_posix,
                    n_en=en_metrics.fences,
                    n_zh=zh_metrics.fences,
                )
            )
    return errors


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--docs-root",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "docs",
        help="Root of the docs tree (default: repo ``docs/``).",
    )
    parser.add_argument(
        "--allowlist",
        type=Path,
        default=Path(__file__).resolve().parent / "doc_parity_allowlist.txt",
        help=(
            "Path to an allowlist of known-drifted docs, one POSIX path "
            "per line, relative to ``docs/``. Default: "
            "``tools/doc_parity_allowlist.txt`` (no-op if the file is absent)."
        ),
    )
    args = parser.parse_args(argv)

    docs_root = args.docs_root
    if not docs_root.is_dir():
        print("ERROR: docs root not found: {}".format(docs_root), file=sys.stderr)
        return 2

    allowlist = _load_allowlist(args.allowlist)
    errors = check_parity(docs_root, allowlist=allowlist)
    if errors:
        print(
            "Documentation parity check failed ({n} issue{s}):".format(
                n=len(errors), s="" if len(errors) == 1 else "s"
            ),
            file=sys.stderr,
        )
        for err in errors:
            print("  - {}".format(err), file=sys.stderr)
        return 1

    print("OK: EN and ZH documentation trees are section-parallel.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
