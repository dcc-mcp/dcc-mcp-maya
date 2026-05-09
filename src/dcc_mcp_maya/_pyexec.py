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
from typing import Optional

# Import third-party modules
from dcc_mcp_core import correct_python_executable, is_gui_executable

logger = logging.getLogger(__name__)

ENV_VAR = "DCC_MCP_PYTHON_EXECUTABLE"


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
        logger.warning(
            "%s pointed at a GUI executable (%s); auto-corrected to %s. "
            "Set the env var to the headless Python interpreter to silence this warning.",
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
