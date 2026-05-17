"""Python 3.7 syntax pin for every ``src/dcc_mcp_maya/**.py`` file.

Maya 2020 and Maya 2022 both ship Python 3.7. Maya's plug-in loader
imports the ``dcc_mcp_maya`` package eagerly on plug-in load — if any
single module in the package tree contains 3.8+ syntax (walrus ``:=``,
``match/case``, positional-only ``/``, f-string ``=`` debug, …) or
runs a 3.8+ ``import`` statement (e.g. ``from typing import Final``)
at module-import time, the entire plug-in fails to load and the user
sees an ``ImportError`` modal in the Maya script editor before
sidecar mode can even start.

This guard rejects both classes of regression at pytest time:

1. **Syntax-level drift** — ``ast.parse(src, feature_version=(3, 7))``
   raises ``SyntaxError`` for every grammar feature added after 3.7.
   Parametrised over every ``.py`` file under ``src/dcc_mcp_maya/``
   so a new module joining the package automatically inherits the
   guarantee — no opt-in needed.

2. **Import-level drift** — ``from typing import Final`` is the
   canonical example: 3.7 ``typing`` does not export ``Final`` so
   the bare ``from typing import Final`` raises ``ImportError`` at
   plug-in load time even though the file parses cleanly under
   ``feature_version=(3, 7)``. A separate test scans the same set
   of files for the known offenders and fails loudly.

3. **Self-protection** — a negative-path test feeds a known walrus
   operator through the same ``ast.parse`` machinery and asserts
   ``SyntaxError`` is raised. If a future CPython release silently
   weakens ``feature_version`` (or pytest runs on an interpreter old
   enough to lack the kwarg), the negative test fails first so the
   rest of the pinning cannot lose its teeth unnoticed.

Why per-file parametrisation matters
====================================

A single global ``ast.parse(concat(all_sources))`` would catch the
first failure and then stop. Parametrising over individual files
lets pytest report *every* offending file in one run, which is what
you need when a contributor has accidentally regressed five modules
at once (e.g. an IDE-driven rename that added ``from typing import
TypeAlias`` everywhere it touched).
"""

# Import future modules
from __future__ import annotations

# Import built-in modules
import ast
import os
import sys
from pathlib import Path
from typing import List

# Import third-party modules
import pytest

PACKAGE_ROOT = Path(__file__).parent.parent / "src" / "dcc_mcp_maya"

# Module-level imports that exist in ``typing`` only from Python 3.8+
# (or later) and therefore raise ``ImportError`` when the plug-in is
# loaded in Maya 2020 / 2022. The list is intentionally narrow — we
# only blacklist names whose 3.7 absence has actually caused a Maya
# plug-in load failure in the field. Add more entries as new
# offenders surface.
_TYPING_3_8_PLUS_NAMES = (
    "Final",
    "Literal",
    "Protocol",
    "TypedDict",  # technically 3.8+ in ``typing``; in 3.7 only via ``typing_extensions``
    "runtime_checkable",
)
_TYPING_3_9_PLUS_NAMES = (
    "Annotated",  # 3.9 in ``typing``
)
_TYPING_3_10_PLUS_NAMES = (
    "ParamSpec",
    "TypeAlias",
    "Concatenate",
    "TypeGuard",
)
_TYPING_FORBIDDEN_AT_RUNTIME = _TYPING_3_8_PLUS_NAMES + _TYPING_3_9_PLUS_NAMES + _TYPING_3_10_PLUS_NAMES


def _iter_package_sources() -> List[Path]:
    """Return every ``.py`` file in the ``dcc_mcp_maya`` package tree.

    Sorted for deterministic test-id ordering across CI runs. Skipping
    ``__pycache__`` because pytest already filters those out — the
    explicit check makes the intent obvious for readers.
    """
    found: List[Path] = []
    for dirpath, _, filenames in os.walk(PACKAGE_ROOT):
        if "__pycache__" in dirpath:
            continue
        for name in filenames:
            if name.endswith(".py"):
                found.append(Path(dirpath) / name)
    return sorted(found)


_SOURCES = _iter_package_sources()


def _parse_as_python_3_7(src: str, *, filename: str = "<unknown>") -> ast.AST:
    """Parse source with the strongest Python 3.7 grammar check available.

    CPython 3.8/3.9 accept ``feature_version`` as an integer minor
    version, while 3.10+ accept the ``(major, minor)`` tuple form.  On
    Python 3.7 itself the ambient parser is already the target grammar.
    """
    if sys.version_info < (3, 8):
        return ast.parse(src, filename=filename)
    if sys.version_info < (3, 10):
        return ast.parse(src, filename=filename, feature_version=7)
    return ast.parse(src, filename=filename, feature_version=(3, 7))


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(PACKAGE_ROOT.parent.parent))
    except ValueError:
        return str(path)


def test_python_3_7_guard_catches_walrus() -> None:
    """Self-test for the ``feature_version=(3, 7)`` guard.

    If a future CPython release silently weakens ``feature_version``
    (or pytest runs on an interpreter old enough to lack it), the
    guards below would silently pass without doing any work and a
    3.8+ regression could slip through. This negative-path test
    feeds a known walrus operator and asserts ``SyntaxError`` is
    raised — if it ever stops raising, the rest of the 3.7 pinning
    machinery cannot be trusted and this test fails the build.
    """
    walrus_src = "(n := 1)\n"
    with pytest.raises(SyntaxError):
        _parse_as_python_3_7(walrus_src)


def test_package_root_is_non_empty() -> None:
    """Pin that the parametrise machinery actually picked up files.

    If a refactor moves the package directory or breaks ``os.walk``,
    a zero-length parametrize list silently turns the guard into a
    no-op — every test below would skip with "no parameters" and
    CI would still go green. This canary fails first so the
    misconfiguration surfaces clearly.
    """
    assert len(_SOURCES) > 0, (
        f"expected to find at least one .py file under {PACKAGE_ROOT}, check that the package root has not moved"
    )


@pytest.mark.parametrize("path", _SOURCES, ids=_rel)
def test_source_parses_under_python_3_7_feature_version(path: Path) -> None:
    """Every ``src/dcc_mcp_maya/**.py`` must parse under Python 3.7 syntax.

    Maya 2020 and 2022 ship Python 3.7. Maya's plug-in loader imports
    the entire ``dcc_mcp_maya`` package on plug-in load, so any 3.8+
    syntax in any file in the tree breaks the plug-in entirely
    (visible to the user as a Script Editor modal with a ``SyntaxError``
    on the offending line).

    ``ast.parse(feature_version=(3, 7))`` rejects every grammar
    feature added after 3.7, regardless of the actual CPython
    version running pytest. This is the structural enforcement that
    keeps Maya 2020 / 2022 unblocked.
    """
    src = path.read_text(encoding="utf-8")
    try:
        _parse_as_python_3_7(src, filename=str(path))
    except SyntaxError as exc:
        pytest.fail(f"{_rel(path)} contains Python 3.8+ syntax that would break on Maya 2020/2022 (Python 3.7): {exc}")


@pytest.mark.parametrize("path", _SOURCES, ids=_rel)
def test_source_does_not_import_typing_3_8_plus_names(path: Path) -> None:
    """Reject ``from typing import <3.8+ name>`` at module scope.

    ``ast.parse(feature_version=(3, 7))`` only catches **grammar**
    drift; module-level ``import`` statements that succeed on 3.11
    but fail on 3.7 (``Final``, ``Literal``, ``Protocol``, …) parse
    cleanly under any feature version. We need a separate AST walk
    to catch the import drift.

    The bug that motivated this guard was an ``ImportError: cannot
    import name 'Final' from 'typing'`` modal in Maya 2022 (Python
    3.7) on plug-in load — see RFC #998 follow-up. Every entry in
    :data:`_TYPING_FORBIDDEN_AT_RUNTIME` is a name that exists in
    the CI interpreter's ``typing`` but is absent from Maya 2022's
    Python 3.7 stdlib.

    Annotation-only uses of the same names are fine under
    ``from __future__ import annotations`` (PEP 563) because they
    are never evaluated. This test only flags actual ``import``
    statements at module scope.
    """
    src = path.read_text(encoding="utf-8")
    tree = ast.parse(src, filename=str(path))
    offenders: List[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "typing":
            for alias in node.names:
                if alias.name in _TYPING_FORBIDDEN_AT_RUNTIME:
                    offenders.append(f"line {node.lineno}: from typing import {alias.name}")
    if offenders:
        pytest.fail(
            "{0} imports {1}-only name(s) from `typing` that do not exist on "
            "Python 3.7 (Maya 2020 / 2022) — use `typing_extensions` is NOT "
            "the answer (it adds a runtime dependency); drop the annotation "
            "or use the equivalent literal value. Offenders:\n  {2}".format(
                _rel(path),
                "3.8+",
                "\n  ".join(offenders),
            )
        )
