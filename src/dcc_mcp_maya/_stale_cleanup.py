"""Stale-instance detection and best-effort cleanup helpers.

Issue #126: when Maya crashes (or is killed via Task Manager), the
``FileRegistry`` entry for the MCP server instance is not removed.  Over
time this accumulates "stale" instances that show up in gateway logs
(``Gateway: evicted 43 stale instance(s)``).

``dcc-mcp-core`` 0.14.17 added Rust-side auto-eviction
(``FileRegistry::read_alive``); this module adds a Python-side complement
that runs at plugin start-up so users see a single clear warning instead
of a slow accumulation.

The helpers here are intentionally side-effect-free: they only **read**
the on-disk registry and emit log messages.  Removal of stale entries is
left to the Rust core (which handles atomic file locking) so two
host-side helpers cannot race each other.
"""

# Import future modules
from __future__ import annotations

# Import built-in modules
import json
import logging
import os
import sys
import tempfile
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

REGISTRY_SUBDIR = "dcc-mcp-registry"
REGISTRY_FILE = "services.json"
DEFAULT_STALE_THRESHOLD = 10


def registry_path(registry_dir: Optional[str] = None) -> Path:
    """Return the absolute path of the FileRegistry ``services.json``.

    Resolution order matches the Rust core:

    1. Explicit ``registry_dir`` argument (treated as the parent of
       ``dcc-mcp-registry/``).
    2. ``DCC_MCP_REGISTRY_DIR`` environment variable.
    3. The OS temp directory (``tempfile.gettempdir()``).
    """
    base = registry_dir or os.environ.get("DCC_MCP_REGISTRY_DIR") or tempfile.gettempdir()
    return Path(base) / REGISTRY_SUBDIR / REGISTRY_FILE


def _pid_alive(pid: int) -> bool:
    """Cross-platform liveness check for a process id.

    Returns ``True`` when the process is currently running, ``False``
    when it has exited.  Uses :func:`os.kill` with signal ``0`` on POSIX
    and ``OpenProcess`` on Windows; both are non-destructive.
    """
    if pid <= 0:
        return False
    if sys.platform == "win32":
        try:
            import ctypes
            from ctypes import wintypes

            PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
            STILL_ACTIVE = 259
            kernel32 = ctypes.windll.kernel32
            handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
            if not handle:
                return False
            try:
                exit_code = wintypes.DWORD()
                if not kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
                    return False
                return exit_code.value == STILL_ACTIVE
            finally:
                kernel32.CloseHandle(handle)
        except Exception:
            return False
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        # The process exists; we just can't signal it.
        return True
    except OSError:
        return False


def count_stale_entries(registry_dir: Optional[str] = None) -> Tuple[int, int]:
    """Return ``(alive_count, stale_count)`` for the on-disk registry.

    A "stale" entry is one whose ``pid`` no longer corresponds to a
    running process.  When the registry file is missing or unparseable
    the function returns ``(0, 0)`` — callers treat absence as the same
    as "no stale entries".
    """
    path = registry_path(registry_dir)
    if not path.is_file():
        return 0, 0
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return 0, 0
    if not isinstance(data, list):
        return 0, 0

    alive = 0
    stale = 0
    for entry in data:
        if not isinstance(entry, dict):
            continue
        pid = entry.get("pid")
        if not isinstance(pid, int):
            continue
        if _pid_alive(pid):
            alive += 1
        else:
            stale += 1
    return alive, stale


def warn_if_too_many_stale(
    threshold: int = DEFAULT_STALE_THRESHOLD,
    registry_dir: Optional[str] = None,
) -> int:
    """Log a single ``WARNING`` when ``stale_count > threshold``; return ``stale_count``.

    Returns ``0`` and logs nothing when the registry is missing,
    unparseable, or below the threshold.  Always best-effort — never
    raises so it is safe to call from plugin start-up code paths.
    """
    try:
        alive, stale = count_stale_entries(registry_dir)
    except Exception as exc:  # noqa: BLE001 — never block plugin startup
        logger.debug("stale-instance scan skipped: %s", exc)
        return 0
    if stale > threshold:
        logger.warning(
            "FileRegistry contains %d stale Maya instance(s) (alive=%d, threshold=%d). "
            "These will be auto-evicted by dcc-mcp-core 0.14.17+ on the next gateway "
            "scan; if the count keeps growing, check for crashed Maya processes or "
            "remove the registry manually: %s",
            stale,
            alive,
            threshold,
            registry_path(registry_dir),
        )
    return stale
