"""Maya availability + version detection (issue #127).

Two pure helpers extracted from the previous monolithic ``server.py``:

* :func:`maya_available` returns ``True`` when ``maya.cmds`` can be
  imported in the current Python environment.
* :func:`get_maya_version_string` returns ``maya.cmds.about(version=True)``
  on the **interpreter main thread**, or :data:`UNKNOWN_VERSION` when Maya
  is unavailable, ``about`` fails, or the caller is on a worker thread (Maya
  ``cmds`` is main-thread-only in common builds — concurrent
  :func:`dcc_mcp_maya.start_server` must not probe from background threads).

:func:`maya_available` is a cheap import check (not cached).  Neither helper
raises for normal failures; version probe failures collapse to
:data:`UNKNOWN_VERSION`.
"""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
import threading

from dcc_mcp_maya.api import require_main_thread

logger = logging.getLogger(__name__)

#: Sentinel returned when Maya is not available or its version cannot be probed.
UNKNOWN_VERSION = "unknown"

#: Thread-safe cache for the Maya version string.
# Only probe once (on the main thread); subsequent calls return the cached value.
_version_cache: str | None = None
_version_lock = threading.Lock()


def maya_available() -> bool:
    """Return ``True`` if ``maya.cmds`` is importable in this Python env.

    Used by skill-discovery code paths that must run *outside* a live
    Maya session (CI, ``mayapy``-less unit tests).  The check is cheap —
    a single :keyword:`import` attempt — and the result is **not** cached
    so callers that mock ``sys.modules`` mid-test see the updated value.
    """
    try:
        # Maya import itself may enforce main-thread access in mayapy builds.
        import maya.cmds  # noqa: F401, PLC0415

        return True
    except Exception:  # noqa: BLE001
        return False


@require_main_thread
def get_maya_version_string() -> str:
    """Return Maya's version string via ``cmds.about(version=True)``.

    Returns :data:`UNKNOWN_VERSION` when Maya is not running, when this
    thread is not the interpreter main thread (``cmds`` is unsafe there in
    many Maya builds), or when ``about`` raises.  Never raises.

    Thread-safe: probes at most once (on the main thread); subsequent
    calls return the cached value.
    """
    # Fast path — return cached value if available
    global _version_cache
    if _version_cache is not None:
        return _version_cache

    # Only probe on the main thread; off-main threads get UNKNOWN_VERSION
    if threading.current_thread() is not threading.main_thread():
        logger.debug(
            "Skipping Maya version probe off the interpreter main thread (thread=%s)",
            threading.current_thread().name,
        )
        return UNKNOWN_VERSION

    # Probe once under lock to avoid concurrent probes
    with _version_lock:
        # Double-check cache after acquiring lock
        if _version_cache is not None:
            return _version_cache

        if not maya_available():
            _version_cache = UNKNOWN_VERSION
            return _version_cache

        try:
            import maya.cmds as cmds  # noqa: PLC0415

            _version_cache = str(cmds.about(version=True))
            return _version_cache
        except Exception as exc:  # noqa: BLE001
            logger.debug("Failed to read Maya version: %s", exc)
            _version_cache = UNKNOWN_VERSION
            return _version_cache
