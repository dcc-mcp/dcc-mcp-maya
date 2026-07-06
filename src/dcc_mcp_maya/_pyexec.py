"""Auto-correct ``DCC_MCP_PYTHON_EXECUTABLE`` when it points at a DCC GUI binary.

Issue #125: when a user sets ``DCC_MCP_PYTHON_EXECUTABLE=/path/to/maya.exe``
(a reasonable first guess), the core subprocess executor correctly refuses to
spawn a GUI process — but the failure mode is a hard error rather than a quiet
fix.  ``dcc-mcp-core`` 0.14.17 added :func:`correct_python_executable` and
:func:`is_gui_executable` exactly to support this kind of host-side
auto-correction.

This module wraps both helpers behind a single ``auto_correct()`` entry point
that is safe to call repeatedly (idempotent) and on any platform.
"""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, Tuple

logger = logging.getLogger(__name__)

ENV_VAR = "DCC_MCP_PYTHON_EXECUTABLE"
AUTOCORRECTED_ENV_VAR = "DCC_MCP_PYTHON_EXECUTABLE_AUTOCORRECTED"


@dataclass
class GuiExecutableHint:
    gui_path: Path
    dcc_kind: str
    recommended_replacement: Optional[Path]


_GUI_BINARIES: Tuple[Tuple[str, Tuple[str, ...], Tuple[str, ...]], ...] = (
    ("maya", ("maya", "maya.bin"), ("mayapy",)),
    ("houdini", ("houdini", "houdinifx", "houdinicore"), ("hython",)),
    ("unreal", ("unrealeditor",), ("unrealeditor-cmd",)),
    ("blender", ("blender",), ()),
    ("3dsmax", ("3dsmax",), ()),
    ("nuke", ("nuke", "nukestudio"), ()),
    ("modo", ("modo",), ()),
    ("motionbuilder", ("motionbuilder",), ()),
    ("c4d", ("cinema4d", "c4d"), ()),
    ("katana", ("katana",), ()),
)


def _real_case(parent: Path, candidate: Path) -> Optional[Path]:
    target = candidate.name.lower()
    try:
        for entry in parent.iterdir():
            if entry.name.lower() == target:
                return entry
    except OSError:
        return None
    return None


def _locate_sibling(gui_path: Path, stems: Tuple[str, ...]) -> Optional[Path]:
    if not stems:
        return None
    parent = gui_path.parent
    suffix = gui_path.suffix
    for stem in stems:
        candidate = parent / stem
        if suffix:
            candidate = candidate.with_suffix(suffix)
        if candidate.exists():
            return _real_case(parent, candidate) or candidate
        found = _real_case(parent, candidate)
        if found is not None:
            return found
    return None


def _fallback_is_gui_executable(path: Any) -> Optional[GuiExecutableHint]:
    gui_path = Path(path)
    stem = gui_path.stem.lower()
    for dcc_kind, stems, sibling_python_stems in _GUI_BINARIES:
        if stem in stems:
            return GuiExecutableHint(
                gui_path=gui_path,
                dcc_kind=dcc_kind,
                recommended_replacement=_locate_sibling(gui_path, sibling_python_stems),
            )
    return None


def _fallback_correct_python_executable(path: Any) -> Path:
    hint = _fallback_is_gui_executable(path)
    if hint is not None and hint.recommended_replacement is not None:
        return hint.recommended_replacement
    return Path(path)


def is_gui_executable(path: Any) -> Optional[GuiExecutableHint]:
    """Return a GUI-binary hint, using core when available."""

    try:
        from dcc_mcp_core import is_gui_executable as core_is_gui_executable
    except Exception:
        return _fallback_is_gui_executable(path)
    return core_is_gui_executable(path)


def correct_python_executable(path: Any) -> Path:
    """Return a corrected Python executable, using core when available."""

    try:
        from dcc_mcp_core import correct_python_executable as core_correct_python_executable
    except Exception:
        return _fallback_correct_python_executable(path)
    return core_correct_python_executable(path)


def auto_correct(env_var: str = ENV_VAR) -> Optional[str]:
    """Auto-correct ``env_var`` in :data:`os.environ` and return the new value.

    Behaviour:

    * If ``env_var`` is unset or empty → returns ``None`` (nothing to do).
    * If the value points to a known DCC GUI binary (``maya.exe``, ``houdinifx``,
      ``UnrealEditor`` …) **and** a headless-Python sibling is found on disk
      → the env var is rewritten to that sibling path and the new value is
      returned.
    * If the value already points to a Python interpreter (``mayapy``, ``python``,
      ``hython`` …) → returns the unchanged value.
    Always idempotent: a second call after a successful correction is a no-op.
    """
    raw = os.environ.get(env_var, "").strip()
    if not raw:
        return None

    # Only rewrite when the value is **actually** a known DCC GUI binary; that
    # way arbitrary user-supplied Python paths (with non-canonical slashes,
    # spaces, etc.) are preserved verbatim.
    if not is_gui_executable(raw):
        return raw

    # Core may return a ``pathlib.Path``; coerce to plain ``str`` for the env.
    fixed_raw = correct_python_executable(raw)
    fixed = str(fixed_raw) if fixed_raw is not None else ""
    if fixed and fixed != raw:
        os.environ[env_var] = fixed
        os.environ[AUTOCORRECTED_ENV_VAR] = "1"
        logger.info(
            "%s pointed at a GUI executable (%s); auto-corrected to %s.",
            env_var,
            raw,
            fixed,
        )
        return fixed

    # GUI binary with no headless sibling found — surface a warning so the user
    # understands the upcoming subprocess-executor failure.
    logger.warning(
        "%s=%s is a DCC GUI executable and no headless Python sibling was "
        "found.  The skill subprocess executor will refuse to spawn it; "
        "set %s to the matching headless interpreter (e.g. mayapy.exe).",
        env_var,
        raw,
        env_var,
    )
    return raw
