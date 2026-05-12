"""Maya availability + version detection (issue #127).

Two pure helpers extracted from the previous monolithic ``server.py``:

* :func:`maya_available` returns ``True`` when ``maya.cmds`` can be
  imported in the current Python environment.
* :func:`get_maya_version_string` returns the result of
  ``maya.cmds.about(version=True)`` or the literal ``"unknown"`` when
  Maya is not running / not importable.

Both helpers are safe to call from any thread and never raise: failures
collapse to ``"unknown"`` / ``False`` so the server can still report a
sensible value during the very first start-up tick.
"""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

from dcc_mcp_maya.api import require_main_thread

logger = logging.getLogger(__name__)

#: Sentinel returned when Maya is not available or its version cannot be probed.
UNKNOWN_VERSION = "unknown"


def maya_available() -> bool:
    """Return ``True`` if ``maya.cmds`` is importable in this Python env.

    Used by skill-discovery code paths that must run *outside* a live
    Maya session (CI, ``mayapy``-less unit tests).  The check is cheap —
    a single :keyword:`import` attempt — and the result is **not** cached
    so callers that mock ``sys.modules`` mid-test see the updated value.
    """
    try:
        import maya.cmds  # noqa: F401, PLC0415

        return True
    except ImportError:
        return False


@require_main_thread
def get_maya_version_string() -> str:
    """Return Maya's version string via ``cmds.about(version=True)``.

    Returns :data:`UNKNOWN_VERSION` when Maya is not running or the
    ``about`` call raises (mocked Maya, partially-initialised module,
    etc.).  Never raises.
    """
    if not maya_available():
        return UNKNOWN_VERSION
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        return str(cmds.about(version=True))
    except Exception as exc:  # noqa: BLE001
        logger.debug("Failed to read Maya version: %s", exc)
        return UNKNOWN_VERSION
