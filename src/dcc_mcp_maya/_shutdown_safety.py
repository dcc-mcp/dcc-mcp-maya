"""Shutdown safety nets for non-cooperative Maya exits (issue #186).

The stock plugin path (:func:`uninitializePlugin` → :func:`_stop_blocking`)
only fires when Maya politely tears the plugin down.  That leaves several
common exit paths that **do not** call into our code and therefore leak
the ``FileRegistry`` entry (operator-visible symptom:
``list_dcc_instances`` continues to advertise the just-closed Maya as
``available`` for up to 30 s):

* Maya crash / Ctrl-C in the controlling console.
* Task Manager / ``kill -9``.
* Batch / ``mayapy`` scripts that exit via ``os._exit(...)``.
* User closes the shell while Maya is idle.

This module layers four independent safety nets so the **best** path
always wins:

1. ``kMayaExiting`` hook — :class:`maya.api.OpenMaya.MSceneMessage`
   fires earlier than :func:`uninitializePlugin` on a clean ``File →
   Exit Maya`` and — unlike plugin unload — fires on ``⌘Q`` / Alt+F4
   even when Maya does not otherwise tear the plugin down cleanly.

2. ``atexit`` fallback — Python interpreter teardown.  Catches the
   "script terminated without calling :func:`uninitializePlugin`" case
   in ``mayapy`` / batch mode where Maya never gets a chance to run
   plugin cleanup.

3. Crash-resilient registry sentinel — a small marker file opened with
   OS semantics that drop the file **for free** when the process dies
   (``FILE_FLAG_DELETE_ON_CLOSE`` on Windows, ``O_TMPFILE``-style on
   Linux where available, PID-tagged lock file elsewhere).  A sweeper
   on the other side can then consider a FileRegistry row
   "definitively dead" when its sentinel is gone — no matter how
   the owner exited.

4. Defensive ``__del__`` guard (opt-in) — a light wrapper that forces a
   blocking ``stop()`` during Python's garbage-collection pass.  Off by
   default because the core's ``McpServerHandle::shutdown`` comment
   warns about Tokio-inside-Tokio deadlocks during interpreter
   teardown; invaluable for headless / test-fixture code paths.

All four are composed by :class:`ShutdownCoordinator` which the plugin
instantiates once after ``_start()`` and tears down in
``uninitializePlugin``.  Each piece is individually testable and
individually disable-able via env vars, so operators can opt out of
hooks that conflict with their own shutdown orchestration.

SOLID notes
-----------
* **Single Responsibility** — each module-level function owns one
  safety net; :class:`ShutdownCoordinator` only orchestrates their
  lifetimes.
* **Open/Closed** — the callback the coordinator drives is injected,
  so tests can wire a fake ``stop_callback`` without running a live
  server.
* **Dependency Inversion** — ``maya.api.OpenMaya`` / ``atexit`` /
  ``os.open`` are all imported lazily so the module is importable in
  a stock ``python`` interpreter (tests, CI).
"""

from __future__ import annotations

import atexit
import logging
import os
import sys
import tempfile
import threading
from pathlib import Path
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)

# ── Env-var switches ─────────────────────────────────────────────────────────

#: Disable the ``MSceneMessage.kMayaExiting`` hook when set to ``"0"``.
#: Default is enabled.  Use when the embedding host already owns the
#: scene-exit event (e.g. custom Maya distribution that drives shutdown
#: from a different callback).
ENV_KMAYA_EXITING_HOOK = "DCC_MCP_MAYA_KMAYA_EXITING_HOOK"

#: Disable the ``atexit`` fallback when set to ``"0"``.  Default is
#: enabled.  ``mayapy`` batch scripts that exit via ``os._exit(...)`` do
#: not fire atexit anyway, so disabling this hook is cheap even in
#: environments that bypass it.
ENV_ATEXIT_HOOK = "DCC_MCP_MAYA_ATEXIT_HOOK"

#: Disable the crash-resilient process sentinel file when set to
#: ``"0"``.  Default is enabled.  The sentinel costs one file descriptor
#: kept open for the process lifetime.
ENV_PROCESS_SENTINEL = "DCC_MCP_MAYA_PROCESS_SENTINEL"

#: Opt in to the defensive ``__del__`` guard by setting to ``"1"``.  Off
#: by default because the core's ``McpServerHandle::shutdown`` comment
#: warns about Tokio-inside-Tokio deadlocks when ``block_on`` runs
#: during interpreter teardown.  Recommended for ``mayapy`` / test
#: fixtures only.
ENV_DEFENSIVE_DEL = "DCC_MCP_MAYA_DEFENSIVE_DEL"

#: Directory inside the configured registry dir where process sentinels
#: live.  Matches the ``dcc-mcp-registry`` layout already produced by
#: the Rust core so sweepers can discover sentinels next to their
#: ``services.json`` row.
SENTINEL_SUBDIR = "dcc-mcp-registry/sentinels"


def _env_enabled(name: str, default: bool) -> bool:
    """Parse an on/off env var with ``default`` fallback.

    Accepts the usual truthy/falsy tokens.  Malformed values collapse
    to ``default`` and emit a debug log line — startup should never die
    on a typoed opt-out.
    """
    raw = os.environ.get(name)
    if raw is None:
        return default
    normalised = raw.strip().lower()
    if normalised in ("1", "true", "yes", "on"):
        return True
    if normalised in ("0", "false", "no", "off"):
        return False
    logger.debug("Ignoring invalid %s=%r; falling back to default=%s", name, raw, default)
    return default


# ---------------------------------------------------------------------------
# 1. kMayaExiting hook
# ---------------------------------------------------------------------------


def register_kmaya_exiting_hook(
    callback: Callable[[], None],
) -> Optional[int]:
    """Register a :class:`MSceneMessage.kMayaExiting` callback.

    ``kMayaExiting`` fires **before** ``uninitializePlugin`` during a
    clean ``File → Exit Maya`` and, crucially, fires on ``⌘Q`` / Alt+F4
    even when the plugin unload path is skipped.  Wrapping shutdown in
    both hooks means the cheaper, earlier one always wins while the
    plugin-unload path remains a backstop.

    Parameters
    ----------
    callback:
        Zero-argument callable invoked on the Maya main thread when the
        scene-exiting event fires.  Must not raise; exceptions are
        caught and logged to keep Maya's own teardown unblocked.

    Returns
    -------
    Optional[int]
        The callback id (opaque ``OpenMaya.MCallbackId``).  Callers
        must pass this id to :func:`unregister_kmaya_exiting_hook` on
        plugin unload.  Returns ``None`` when ``maya.api.OpenMaya`` is
        unavailable (non-Maya Python) or the registration failed.
    """
    try:
        # Lazy import — this module must be importable in plain Python
        # so unit tests can exercise the other safety nets without a
        # live Maya.
        import maya.api.OpenMaya as om  # noqa: PLC0415
    except Exception as exc:  # noqa: BLE001
        logger.debug("kMayaExiting: maya.api.OpenMaya unavailable: %s", exc)
        return None

    def _guarded(_client_data: Any) -> None:
        try:
            callback()
        except Exception as exc:  # noqa: BLE001
            logger.warning("kMayaExiting callback raised: %s", exc)

    try:
        callback_id = om.MSceneMessage.addCallback(
            om.MSceneMessage.kMayaExiting,
            _guarded,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("kMayaExiting addCallback failed: %s", exc)
        return None

    logger.debug("kMayaExiting hook registered (callback_id=%s)", callback_id)
    return callback_id


def unregister_kmaya_exiting_hook(callback_id: Optional[int]) -> bool:
    """Remove a previously-registered :func:`register_kmaya_exiting_hook` callback.

    Returns ``True`` when the callback was removed, ``False`` when the
    id was ``None`` or removal failed.  Removal is best-effort: a Maya
    that has already torn down the scene event system may silently drop
    the request.
    """
    if callback_id is None:
        return False
    try:
        import maya.api.OpenMaya as om  # noqa: PLC0415
    except Exception:  # noqa: BLE001
        return False
    try:
        om.MSceneMessage.removeCallback(callback_id)
    except Exception as exc:  # noqa: BLE001
        logger.debug("kMayaExiting removeCallback(%s) failed: %s", callback_id, exc)
        return False
    return True


# ---------------------------------------------------------------------------
# 2. atexit fallback
# ---------------------------------------------------------------------------


def register_atexit_hook(callback: Callable[[], None]) -> Callable[[], None]:
    """Register an :mod:`atexit` hook that invokes *callback* once.

    The returned object is the exact callable handed to
    :func:`atexit.register` — callers pass it back to
    :func:`atexit.unregister` on plugin unload so we do not accumulate
    stale hooks across repeated load/unload cycles.

    The hook is idempotent via a module-level flag so a shutdown path
    that already called ``callback`` (plugin unload or kMayaExiting)
    does not try to run it a second time during interpreter teardown.
    """
    already_ran = threading.Event()

    def _guarded() -> None:
        if already_ran.is_set():
            return
        already_ran.set()
        try:
            callback()
        except Exception as exc:  # noqa: BLE001
            # Python's atexit swallows exceptions but logs them — we do
            # the same explicitly so the log line is ours to grep for.
            logger.warning("atexit shutdown callback raised: %s", exc)

    atexit.register(_guarded)
    return _guarded


def unregister_atexit_hook(hook: Optional[Callable[[], None]]) -> bool:
    """Remove a previously-registered :func:`register_atexit_hook` callable.

    Returns ``True`` on success, ``False`` when *hook* is ``None`` or
    :func:`atexit.unregister` rejected it.
    """
    if hook is None:
        return False
    try:
        atexit.unregister(hook)
    except Exception as exc:  # noqa: BLE001
        logger.debug("atexit.unregister failed: %s", exc)
        return False
    return True


# ---------------------------------------------------------------------------
# 3. Crash-resilient process sentinel
# ---------------------------------------------------------------------------


def _sentinel_dir(registry_dir: Optional[str] = None) -> Path:
    """Return the absolute directory where sentinels live.

    Resolution matches :func:`dcc_mcp_maya._stale_cleanup.registry_path`:

    1. Explicit ``registry_dir`` argument.
    2. ``DCC_MCP_REGISTRY_DIR`` env var.
    3. OS temp dir.

    Creates the sub-directory when missing so the first-run case does
    not require a separate bootstrap step.
    """
    base = registry_dir or os.environ.get("DCC_MCP_REGISTRY_DIR") or tempfile.gettempdir()
    path = Path(base) / SENTINEL_SUBDIR
    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        logger.debug("sentinel dir %s could not be created: %s", path, exc)
    return path


def sentinel_path(
    instance_id: str,
    registry_dir: Optional[str] = None,
) -> Path:
    """Return the absolute sentinel-file path for *instance_id*.

    The filename encodes both the PID and the instance ID so a sweeper
    can cross-check a FileRegistry row against the sentinel even when
    the sentinel content is empty / unreadable.
    """
    pid = os.getpid()
    safe_id = "".join(c for c in instance_id if c.isalnum() or c in "-_") or "unknown"
    return _sentinel_dir(registry_dir) / f"{pid}-{safe_id}.sentinel"


class ProcessSentinel:
    """OS-owned marker file that disappears when the process dies.

    On Windows the file is opened with ``FILE_FLAG_DELETE_ON_CLOSE``
    (``os.O_TEMPORARY``), which the kernel deletes automatically when
    the last open handle closes — including the implicit close on
    process death.  On POSIX we open the file, keep the fd alive, and
    ``unlink()`` it at cleanup time; since the kernel drops open fds
    on process exit, this gives the same "gone on crash" semantics
    when combined with a small extra check on startup.

    Keep the :class:`ProcessSentinel` instance alive for the server
    lifetime.  Dropping it early (or calling :meth:`cleanup`) removes
    the marker — sweepers interpret that as "this instance is done".
    """

    def __init__(self, path: Path) -> None:
        self.path: Path = path
        self._fd: Optional[int] = None
        self._lock = threading.Lock()

    # ── Public API ──────────────────────────────────────────────────────

    def open(self) -> bool:
        """Create + hold the sentinel file open.

        Returns ``True`` on success.  ``False`` when the fd could not be
        opened (permissions, disk full, …) — the safety net gracefully
        degrades: the other three hooks still provide coverage.
        """
        with self._lock:
            if self._fd is not None:
                return True
            flags = os.O_RDWR | os.O_CREAT | os.O_TRUNC
            mode = 0o600
            if sys.platform == "win32":
                # ``os.O_TEMPORARY`` maps to FILE_FLAG_DELETE_ON_CLOSE —
                # when the process dies the kernel drops the file for us.
                # ``O_NOINHERIT`` prevents child processes inheriting
                # the handle, which would otherwise delay deletion
                # until every child closes it too.  Both flags are
                # Windows-only and always present on CPython 3.7+ there.
                flags |= os.O_TEMPORARY | os.O_NOINHERIT
            try:
                self._fd = os.open(str(self.path), flags, mode)
            except OSError as exc:
                logger.debug(
                    "ProcessSentinel: could not open %s: %s",
                    self.path,
                    exc,
                )
                self._fd = None
                return False
            # Write the PID so a sweeper that reads the file can
            # double-check ownership.  Best-effort; we do not fsync.
            try:
                os.write(self._fd, f"{os.getpid()}\n".encode())
            except OSError as exc:
                logger.debug("ProcessSentinel: pid write failed: %s", exc)
            return True

    def cleanup(self) -> None:
        """Close the handle and remove the file.

        Idempotent — safe to call multiple times.  Called from both
        :class:`ShutdownCoordinator.uninstall` (cooperative exit) and
        from the atexit/kMayaExiting guards (non-cooperative).  After
        cleanup the object is "spent"; the sentinel will not be
        re-opened by a subsequent :meth:`open` call.
        """
        with self._lock:
            fd = self._fd
            self._fd = None
            if fd is not None:
                try:
                    os.close(fd)
                except OSError as exc:
                    logger.debug("ProcessSentinel: close(%s) failed: %s", fd, exc)
            # On Windows with O_TEMPORARY the kernel already dropped the
            # file.  On POSIX we must unlink manually.
            #
            # ``Path.unlink(missing_ok=...)`` is Python 3.8+; we still
            # support Python 3.7 / Maya 2022, so we catch
            # ``FileNotFoundError`` ourselves instead.
            try:
                self.path.unlink()
            except FileNotFoundError:
                pass
            except OSError as exc:
                logger.debug(
                    "ProcessSentinel: unlink(%s) failed: %s",
                    self.path,
                    exc,
                )

    def is_alive(self) -> bool:
        """Return ``True`` when the file descriptor is still open."""
        return self._fd is not None


def write_process_sentinel(
    instance_id: str,
    registry_dir: Optional[str] = None,
) -> Optional[ProcessSentinel]:
    """Create a :class:`ProcessSentinel` for *instance_id*.

    Returns the object on success; keep a strong reference for the
    server lifetime.  Returns ``None`` when the sentinel could not be
    created — callers should not treat that as a startup failure; the
    other three safety nets continue to provide coverage.
    """
    path = sentinel_path(instance_id, registry_dir=registry_dir)
    sentinel = ProcessSentinel(path)
    if not sentinel.open():
        return None
    logger.debug("ProcessSentinel created at %s", path)
    return sentinel


def orphan_sentinels(registry_dir: Optional[str] = None) -> list[Path]:
    """Return sentinel files whose PIDs are no longer alive.

    Used by sweepers to cross-check FileRegistry rows.  Never raises —
    on filesystem errors returns an empty list.  Import is local to
    avoid a circular dependency between ``_shutdown_safety`` and
    ``_stale_cleanup`` at load time.
    """
    try:
        from dcc_mcp_maya._stale_cleanup import _pid_alive  # noqa: PLC0415
    except Exception:  # noqa: BLE001
        return []

    sentinels: list[Path] = []
    directory = _sentinel_dir(registry_dir)
    if not directory.is_dir():
        return sentinels
    try:
        candidates = list(directory.iterdir())
    except OSError:
        return sentinels
    for entry in candidates:
        if not entry.is_file() or entry.suffix != ".sentinel":
            continue
        # Filename format: "<pid>-<instance_id>.sentinel".
        pid_str = entry.stem.split("-", 1)[0]
        try:
            pid = int(pid_str)
        except ValueError:
            continue
        if not _pid_alive(pid):
            sentinels.append(entry)
    return sentinels


# ---------------------------------------------------------------------------
# 4. Defensive __del__ guard (opt-in)
# ---------------------------------------------------------------------------


class DefensiveShutdownGuard:
    """Python wrapper that calls *stop_callback* during garbage collection.

    Intentionally **off by default** because the core's
    ``McpServerHandle::shutdown`` comment warns that running
    ``runtime.block_on(handle.shutdown())`` during Python's
    interpreter-teardown pass can deadlock (Tokio-inside-Tokio).  When
    enabled via :data:`ENV_DEFENSIVE_DEL` = ``"1"``, this wrapper holds
    a reference to the server handle and its stop callback; when the
    wrapper itself is collected — including the edge case where
    ``mayapy`` / a test fixture exits without explicitly calling
    ``stop_server()`` — the callback runs.

    Only call :meth:`disarm` when the shutdown has already been
    performed cooperatively; that prevents a double-stop.
    """

    def __init__(self, stop_callback: Callable[[], None]) -> None:
        self._stop_callback = stop_callback
        self._armed = True
        self._lock = threading.Lock()

    def disarm(self) -> None:
        """Mark the guard as already-handled; :meth:`__del__` will no-op."""
        with self._lock:
            self._armed = False

    def __del__(self) -> None:  # pragma: no cover — GC-timing dependent
        with self._lock:
            if not self._armed:
                return
            callback = self._stop_callback
            self._armed = False
        try:
            callback()
        except Exception as exc:  # noqa: BLE001
            # ``sys.stderr`` might be torn down mid-GC; log quietly.
            logger.debug("DefensiveShutdownGuard.__del__ raised: %s", exc)


# ---------------------------------------------------------------------------
# Coordinator — composes the four safety nets
# ---------------------------------------------------------------------------


class ShutdownCoordinator:
    """Orchestrate the lifetime of every shutdown safety net.

    Usage::

        coord = ShutdownCoordinator()
        coord.install(stop_callback, instance_id="maya-abc", registry_dir=None)
        # … server runs …
        coord.uninstall()  # inside uninitializePlugin

    :meth:`install` is idempotent — calling it twice silently no-ops
    the second time.  :meth:`uninstall` tears down every net that was
    actually wired (so callers never need to track which nets they
    opted into).

    The coordinator does **not** itself call ``stop_server()``; that
    decision is left to the injected ``stop_callback`` so plugin code
    can decide whether to route through :class:`MayaMcpServer.stop` or
    the module-level :func:`dcc_mcp_maya.stop_server`.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._installed = False
        self._stop_callback: Optional[Callable[[], None]] = None
        self._kmaya_callback_id: Optional[int] = None
        self._atexit_hook: Optional[Callable[[], None]] = None
        self._sentinel: Optional[ProcessSentinel] = None
        self._guard: Optional[DefensiveShutdownGuard] = None
        self._stop_ran = threading.Event()

    # ── Public API ──────────────────────────────────────────────────────

    def install(
        self,
        stop_callback: Callable[[], None],
        *,
        instance_id: Optional[str] = None,
        registry_dir: Optional[str] = None,
    ) -> None:
        """Wire every enabled safety net against *stop_callback*.

        Parameters
        ----------
        stop_callback:
            Invoked by whichever safety net fires first.  Typical
            implementation is ``_stop_blocking`` from the plugin
            module.  **Must be safe to call multiple times** — the
            coordinator guards against concurrent invocations with a
            ``threading.Event`` but the callback may still see two
            calls if (for example) both kMayaExiting and atexit race.
        instance_id:
            Optional Maya instance id used as part of the sentinel
            filename.  When omitted the sentinel is tagged with the
            string ``"unknown"``.
        registry_dir:
            Explicit registry directory for the sentinel file.  When
            omitted follows the same resolution as
            :func:`dcc_mcp_maya._stale_cleanup.registry_path`.
        """
        with self._lock:
            if self._installed:
                return
            self._installed = True
            self._stop_callback = stop_callback

        guarded_stop = self._make_guarded_stop()

        # 1. kMayaExiting
        if _env_enabled(ENV_KMAYA_EXITING_HOOK, default=True):
            self._kmaya_callback_id = register_kmaya_exiting_hook(guarded_stop)

        # 2. atexit
        if _env_enabled(ENV_ATEXIT_HOOK, default=True):
            self._atexit_hook = register_atexit_hook(guarded_stop)

        # 3. process sentinel
        if _env_enabled(ENV_PROCESS_SENTINEL, default=True):
            self._sentinel = write_process_sentinel(
                instance_id or "unknown",
                registry_dir=registry_dir,
            )

        # 4. defensive __del__ guard (opt-in)
        if _env_enabled(ENV_DEFENSIVE_DEL, default=False):
            self._guard = DefensiveShutdownGuard(guarded_stop)

    def uninstall(self) -> None:
        """Tear down every wired safety net.

        Idempotent.  Safe to call when :meth:`install` was never
        invoked (for example when plugin bootstrap failed before the
        coordinator was built).
        """
        with self._lock:
            if not self._installed:
                return
            self._installed = False

        # Reverse order — disarm optional guard first, then fixed nets.
        if self._guard is not None:
            try:
                self._guard.disarm()
            except Exception as exc:  # noqa: BLE001
                logger.debug("DefensiveShutdownGuard.disarm failed: %s", exc)
            self._guard = None

        if self._sentinel is not None:
            try:
                self._sentinel.cleanup()
            except Exception as exc:  # noqa: BLE001
                logger.debug("ProcessSentinel.cleanup failed: %s", exc)
            self._sentinel = None

        if self._atexit_hook is not None:
            unregister_atexit_hook(self._atexit_hook)
            self._atexit_hook = None

        if self._kmaya_callback_id is not None:
            unregister_kmaya_exiting_hook(self._kmaya_callback_id)
            self._kmaya_callback_id = None

        self._stop_callback = None

    @property
    def stop_already_ran(self) -> bool:
        """Return ``True`` once any safety net has invoked the stop callback."""
        return self._stop_ran.is_set()

    # ── Internals ───────────────────────────────────────────────────────

    def _make_guarded_stop(self) -> Callable[[], None]:
        """Wrap the stop callback so it runs at most once across all nets."""

        def _run_once() -> None:
            if self._stop_ran.is_set():
                return
            self._stop_ran.set()
            callback = self._stop_callback
            if callback is None:
                return
            try:
                callback()
            except Exception as exc:  # noqa: BLE001
                logger.warning("ShutdownCoordinator stop callback raised: %s", exc)

        return _run_once
