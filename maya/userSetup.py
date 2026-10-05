"""Maya userSetup.py -- auto-load the receipted dcc-mcp-maya module."""

from __future__ import annotations

import json
import logging
import os
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType
from typing import Optional

logger = logging.getLogger(__name__)

BOOTSTRAP_ERROR_DIR_ENV = "DCC_MCP_MAYA_BOOTSTRAP_ERROR_DIR"

#: DCC identifier stamped onto every record. Keep in sync with
#: ``dcc_mcp_maya.install.DCC_TYPE``: core keys its own host-error log on the
#: same value, so a cross-referencing operator sees one name for one host.
DCC_TYPE = "maya"

#: Local JSONL schema version. Bump when the record shape below changes.
BOOTSTRAP_ERROR_SCHEMA_VERSION = 1
#: Bytes a single day's JSONL may reach before it is rotated. Matches core's
#: ``RotatingFileHandler(maxBytes=..., backupCount=4)`` in
#: ``dcc_mcp_core.host_errors`` so both logs age out at the same rate.
#:
#: The file is shared with ``dcc_mcp_maya._bootstrap_watch``, which appends
#: its ``finished`` / ``hang_detected`` terminal events to the same
#: ``userSetup-<YYYYMMDD>.jsonl``. Rotation therefore only renames and never
#: truncates in place, so a concurrent append lands in a rotated generation
#: rather than being lost.
BOOTSTRAP_ERROR_MAX_BYTES = 5 * 1024 * 1024
#: Number of rotated generations kept alongside the live file (``.1`` .. ``.4``
#: in core's naming), so the directory is bounded at 5 x 5 MB.
BOOTSTRAP_ERROR_BACKUP_COUNT = 4

#: Stages whose failure is *already* on disk in core's schema, so recording it
#: here as well would leave two differently-shaped records for one failure.
#:
#: ``dcc_mcp_maya.install.bootstrap_user_setup`` wraps ``cmds.loadPlugin`` in
#: core's ``capture_bootstrap_errors``, which records and then re-raises. By
#: the time :func:`_report_failure` sees a ``plugin_load`` failure, core owns
#: the record -- it carries ``adapter_version`` / ``core_version`` /
#: ``dcc_type`` and is rotated, none of which this file could add.
#:
#: Silence here is only safe because ``dcc_mcp_maya.install`` imports
#: ``dcc_mcp_core`` at *module* scope: importing ``bootstrap_user_setup``
#: already requires core, so any failure that reaches ``plugin_load`` came out
#: of core's capture. A host without core fails one stage earlier, at
#: ``import``, which is still recorded locally. If that module-level import is
#: ever made lazy, ``plugin_load`` must come off this set with it.
#:
#: ``environment``, ``import``, ``schedule``, ``plugin_verify`` and the
#: watchdog stages are *not* covered by core, so they keep the local record.
CORE_PERSISTED_STAGES = frozenset({"plugin_load"})

#: Maximum number of watchdog-driven load retries after the deferred call.
WATCHDOG_MAX_ATTEMPTS = 3
#: Seconds the watchdog waits between two load attempts.
WATCHDOG_GRACE_SECS = 10.0
#: Longest *legitimate* time from arming the watchdog to its give-up report:
#: one grace period before the first retry, one per retry, and one final tick
#: on which the give-up is reported. A healthy retry chain therefore finishes
#: within this window, so the hang threshold must stay strictly above it or
#: slow-but-working sessions would be misreported as hung.
WATCHDOG_WORST_CASE_SECS = WATCHDOG_GRACE_SECS * (WATCHDOG_MAX_ATTEMPTS + 1)

#: Run-scoped bootstrap hang marker. ``_mark_run_started`` fills it in once,
#: before the first schedule; ``_retire_run_marker`` empties it. Retries must
#: never rewrite it -- a new marker per retry would let attempt N's retirement
#: mask attempt N+1's hang.
_RUN_MARKER = {"marker": None, "watchdog_armed": False}


def _bootstrap_watch() -> Optional[ModuleType]:
    """Return the hang watchdog, or ``None`` when the adapter is unavailable.

    The watchdog is pure standard library and lives in the adapter package so
    it can be unit-tested outside Maya. If the adapter cannot be imported the
    ``import`` stage below already reports that, so a missing watchdog is not
    itself an error worth raising here.
    """
    try:
        from dcc_mcp_maya import _bootstrap_watch
    except Exception:
        return None
    return _bootstrap_watch


def _mark_run_started() -> bool:
    """Write this run's ``started`` marker exactly once, before scheduling.

    A bootstrap that hangs raises nothing, so neither :func:`_report_failure`
    nor the watchdog's give-up ever fires -- the process simply sits there and
    the receipts directory stays empty. The marker is the only externally
    visible proof that a load was attempted and never returned.

    It is written here, once per sourced ``userSetup.py``, rather than inside
    :func:`_load_dcc_mcp_maya`: that function runs again on every watchdog
    retry, and a marker per attempt would let one attempt's exit hide the
    next attempt's hang.

    Returns ``True`` when a marker is armed and therefore needs retiring.
    """
    watch = _bootstrap_watch()
    if watch is None:
        return False
    try:
        _RUN_MARKER["marker"] = watch.record_bootstrap_started()
    except Exception:
        _RUN_MARKER["marker"] = None
    return _RUN_MARKER["marker"] is not None


def _retire_run_marker(finished: bool = False) -> None:
    """Retire this run's marker. Idempotent, and safe when none was written.

    ``finished`` distinguishes the two terminal states an operator cares
    about: the load really completed (write the ``finished`` receipt) versus
    the run stopped trying (drop the marker so a reported failure is never
    later misread as a hang).
    """
    watch = _bootstrap_watch()
    marker = _RUN_MARKER.get("marker")
    if watch is None or marker is None:
        return
    _RUN_MARKER["marker"] = None
    try:
        if finished:
            watch.record_bootstrap_finished(marker)
        else:
            watch.clear_bootstrap_marker(marker)
    except Exception:
        pass


def _retire_if_terminal(finished: bool) -> None:
    """Retire on success, or on failure when no watchdog will retry it.

    While the idle watchdog is armed a failed attempt is not terminal -- it
    will simply be retried, and the give-up path retires the marker. With no
    watchdog armed (hosts without ``cmds.scriptJob``) a failed attempt *is*
    the last word, so it must retire here or the marker would linger and be
    misread as a hang on the next start-up.
    """
    if finished or not _RUN_MARKER.get("watchdog_armed"):
        _retire_run_marker(finished=finished)


def _report_prior_bootstrap_hang() -> None:
    """Announce a bootstrap that started on an earlier launch and never finished.

    A load that hangs raises nothing, so the only moment it can be observed is
    the *next* start-up. Detection runs at import time rather than inside the
    deferred callback precisely because in the hang scenario the deferred
    callback is the thing that never runs.
    """
    watch = _bootstrap_watch()
    if watch is None:
        return
    try:
        watch.report_bootstrap_hang()
    except Exception:
        # A diagnostic must never stop the load it is diagnosing.
        pass


def _bootstrap_error_dir() -> Path:
    """Directory that receives user-visible auto-load failure records."""
    override = os.environ.get(BOOTSTRAP_ERROR_DIR_ENV)
    if override:
        return Path(override)
    return Path.home() / ".dcc-mcp" / "receipts" / "bootstrap-errors"


def _package_version(module_name: str) -> Optional[str]:
    """Best-effort ``__version__`` of an already-imported-or-importable module.

    Provenance only: a bootstrap record that cannot name its versions is still
    worth far more than no record at all, so every failure here is swallowed.
    """
    module = sys.modules.get(module_name)
    if module is None:
        try:
            module = __import__(module_name, fromlist=["__version__"])
        except Exception:
            return None
    version = getattr(module, "__version__", None)
    return str(version) if version else None


def _rotate_bootstrap_log(path: Path) -> None:
    """Rotate ``path`` through ``.1`` .. ``.N``, mirroring core's handler.

    Core uses :class:`logging.handlers.RotatingFileHandler`, which renames
    ``.i`` to ``.i+1`` from the oldest generation down and then moves the live
    file to ``.1``. Reproducing that naming keeps the two logs -- core's
    ``host-errors.log`` and this one -- inspectable with the same habits.
    """
    for generation in range(BOOTSTRAP_ERROR_BACKUP_COUNT - 1, 0, -1):
        source = path.with_name("{}.{}".format(path.name, generation))
        destination = path.with_name("{}.{}".format(path.name, generation + 1))
        if not source.exists():
            continue
        if destination.exists():
            destination.unlink()
        source.replace(destination)
    first = path.with_name("{}.1".format(path.name))
    if first.exists():
        first.unlink()
    if path.exists():
        path.replace(first)


def _echo_to_stderr(line: str) -> None:
    """Last-resort channel when the JSONL itself cannot be written."""
    try:
        sys.stderr.write(line + "\n")
        sys.stderr.flush()
    except Exception:
        pass


def _write_failure_record(stage: str, error_type: str, message: str, formatted: str) -> None:
    """Append one JSONL record, bounded and rotated, or fall back to stderr.

    The file is the only channel that outlives the Script Editor's scrollback,
    so a failure to write it must never be swallowed: the record is echoed to
    stderr instead, which keeps at least one durable trace in a launched-from-
    terminal or redirected Maya session.
    """
    log_dir = _bootstrap_error_dir()
    log_path = log_dir / "userSetup-{}.jsonl".format(datetime.now(timezone.utc).strftime("%Y%m%d"))
    record = {
        "schema_version": BOOTSTRAP_ERROR_SCHEMA_VERSION,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "pid": os.getpid(),
        "dcc_type": DCC_TYPE,
        "adapter_version": _package_version("dcc_mcp_maya"),
        "core_version": _package_version("dcc_mcp_core"),
        "stage": stage,
        "status": "failed",
        "error_type": error_type,
        "error": message,
        "traceback": formatted,
    }
    payload = json.dumps(record, ensure_ascii=False, sort_keys=True)
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
        if log_path.exists() and log_path.stat().st_size >= BOOTSTRAP_ERROR_MAX_BYTES:
            _rotate_bootstrap_log(log_path)
        # ``newline=""``: on Windows the default text mode rewrites the
        # trailing ``\n`` to ``\r\n``, and a CRLF JSONL is not the line format
        # every downstream reader assumes.
        with log_path.open("a", encoding="utf-8", newline="") as stream:
            stream.write(payload + "\n")
    except Exception as write_error:
        _echo_to_stderr("dcc-mcp-maya auto-load: could not write {} to {}: {}".format(stage, log_path, write_error))
        _echo_to_stderr(payload)


def _report_failure(stage: str, exc: BaseException) -> None:
    """Surface an auto-load failure where an operator can actually see it.

    A bare ``logger.warning`` at Maya start-up is invisible: no handler is
    installed that early, so the record never reaches the Script Editor or
    the Output Window. Mirror the failure onto three channels instead --
    Maya's Script Editor, a durable JSONL file, and the logging module -- so
    a silent no-op can never masquerade as a successful load again.
    """
    error_type = type(exc).__name__
    message = "dcc-mcp-maya auto-load failed ({}): {}: {}".format(stage, error_type, exc)
    # Format the exception's *own* traceback rather than the one currently
    # being handled: several callers (notably the watchdog give-up) build the
    # exception outside an ``except`` block, where ``traceback.format_exc()``
    # would only yield "NoneType: None".
    formatted = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)).strip()
    try:
        import maya.cmds as cmds

        cmds.warning(message)
    except Exception:
        pass
    try:
        # MGlobal also writes to Maya's status line, so the failure is visible
        # even when the Script Editor has never been opened.
        import maya.api.OpenMaya as om

        om.MGlobal.displayWarning(message)
    except Exception:
        pass
    # The Script Editor channel always fires -- it is the one an artist sees
    # first. The file is skipped only for stages core already persisted, so
    # one failure never lands twice in the receipts directory.
    if stage not in CORE_PERSISTED_STAGES:
        _write_failure_record(stage, error_type, str(exc), formatted)
    logger.warning("%s", message)


def _setup_module_paths() -> None:
    """Expose the installed module in GUI, standalone, and batch modes."""
    try:
        import dcc_mcp_maya  # noqa: F401

        return
    except ImportError:
        pass

    if sys.platform == "win32":
        module_dirs = [Path(os.environ.get("USERPROFILE", "")) / "Documents" / "maya" / "modules"]
    elif sys.platform == "darwin":
        module_dirs = [Path.home() / "Library" / "Preferences" / "Autodesk" / "maya" / "modules"]
    else:
        module_dirs = [Path.home() / "maya" / "modules"]

    for modules_dir in module_dirs:
        module_root = modules_dir / "dcc-mcp-maya"
        if not module_root.is_dir():
            continue
        plugins_dir = module_root / "plug-ins"
        if plugins_dir.is_dir():
            current = os.environ.get("MAYA_PLUG_IN_PATH", "")
            plugins = str(plugins_dir)
            if plugins not in current.split(os.pathsep):
                os.environ["MAYA_PLUG_IN_PATH"] = plugins + (os.pathsep + current if current else "")
        python_dir = module_root / ("python37" if sys.version_info[:2] == (3, 7) else "python")
        if not python_dir.is_dir():
            python_dir = module_root / "python"
        python_path = str(python_dir)
        if python_dir.is_dir() and python_path not in sys.path:
            sys.path.insert(0, python_path)
        break


def _apply_default_env() -> None:
    os.environ.setdefault("DCC_MCP_MAYA_PORT", "0")
    os.environ.setdefault("DCC_MCP_GATEWAY_PORT", "9765")


def _load_dcc_mcp_maya() -> None:
    """Run the fixed captured bootstrap after Maya's startup queue drains.

    Each phase is reported separately: "the plug-in did not load" is not
    actionable, while "the adapter package is not importable" is.

    A load that neither raises nor returns leaves no receipt at all, so the
    call is bracketed by a ``started`` / ``finished`` marker pair. A marker
    that outlives its threshold is the only externally visible proof that
    ``cmds.loadPlugin`` blocked instead of failing.
    """
    try:
        _apply_default_env()
        _setup_module_paths()
    except Exception as exc:
        _report_failure("environment", exc)
        _retire_if_terminal(finished=False)
        return

    try:
        from dcc_mcp_maya.install import bootstrap_user_setup
    except Exception as exc:
        _report_failure("import", exc)
        _retire_if_terminal(finished=False)
        return

    try:
        _load_via_bootstrap(bootstrap_user_setup)
    except Exception as exc:
        _report_failure("plugin_load", exc)
        # A raised exception is not a hang, but it is only terminal when no
        # watchdog is going to retry it.
        _retire_if_terminal(finished=False)
        return

    # A load that returns cleanly without registering the plug-in is the
    # failure mode that started this investigation: every channel reported
    # success while no MCP server existed. Verify instead of assuming.
    verified = False
    try:
        cmds = _maya_cmds()
        if cmds is None:  # nothing to verify outside a Maya session
            verified = True
        elif cmds.pluginInfo("dcc_mcp_maya_plugin", query=True, loaded=True):
            verified = True
        else:
            _report_failure(
                "plugin_verify",
                RuntimeError(
                    "bootstrap_user_setup() returned but dcc_mcp_maya_plugin is not loaded; "
                    "check the Plug-in Manager and the bootstrap-error log"
                ),
            )
    except Exception as exc:
        _report_failure("plugin_verify", exc)

    _retire_if_terminal(finished=verified)


def _load_via_bootstrap(bootstrap_user_setup) -> None:
    """Run the adapter's captured, bounded bootstrap.

    Kept as a separate seam so the import phase and the load phase stay
    independently reportable (and testable) -- "the adapter package is not
    importable" and "the plug-in did not load" need different fixes.
    """
    # ``defer=False``: *we* are the deferred callback already.
    bootstrap_user_setup(defer=False)


def _maya_cmds() -> Optional[ModuleType]:
    """Return ``maya.cmds`` inside a live Maya session, else ``None``."""
    try:
        import maya.cmds as cmds
    except ImportError:
        return None
    return cmds


def _schedule(callback) -> None:
    """Queue ``callback`` on Maya's deferred command queue.

    ``cmds.evalDeferred`` drains as part of Maya's start-up sequence. The
    older ``maya.utils.executeDeferred`` it replaced ran on the *idle event
    loop*, which only fires once the main thread actually goes idle -- during
    a GUI start-up that can be never, which is why the adapter silently
    never loaded.
    """
    cmds = _maya_cmds()
    if cmds is None:
        return False
    eval_deferred = getattr(cmds, "evalDeferred", None)
    if eval_deferred is None:
        _report_failure(
            "schedule",
            RuntimeError("maya.cmds.evalDeferred is unavailable; the Maya deferred queue is not ready"),
        )
        return False
    try:
        eval_deferred(callback, lowestPriority=True)
    except Exception as exc:
        _report_failure("schedule", exc)
        return False
    return True


def _plugin_loaded() -> bool:
    """Return True when the plug-in is registered in this Maya session."""
    cmds = _maya_cmds()
    if cmds is None:
        return False
    try:
        return bool(cmds.pluginInfo("dcc_mcp_maya_plugin", query=True, loaded=True))
    except Exception:
        return False


def _arm_autoload_watchdog() -> None:
    """Retry the plug-in load from Maya's idle queue, then stop.

    ``cmds.evalDeferred`` is the primary path and normally fires during
    start-up. This watchdog covers the cases where it does not:

    * the deferred item is dropped while Maya is still booting (packaged /
      ``.mod`` installs where ``userSetup.py`` is sourced very early),
    * the first attempt runs before another plug-in or studio bootstrap has
      finished extending ``MAYA_PLUG_IN_PATH``.

    At most :data:`WATCHDOG_MAX_ATTEMPTS` retries are made, spaced by
    :data:`WATCHDOG_GRACE_SECS`; the job then reports the give-up through
    :func:`_report_failure` and removes itself, so a Maya session never
    carries a permanently polling job.
    """
    cmds = _maya_cmds()
    script_job = getattr(cmds, "scriptJob", None) if cmds is not None else None
    if script_job is None:
        return

    # ``next_check`` stays ``None`` until the first idle tick so both tunables
    # are read from module scope at call time.
    state = {"job": None, "attempts": 0, "next_check": None, "armed_at": time.monotonic()}

    # While armed, a failed load attempt is retryable rather than terminal, so
    # the run marker must survive until the give-up below.
    _RUN_MARKER["watchdog_armed"] = True

    def _disarm() -> None:
        job = state.get("job")
        state["job"] = None
        if job is not None:
            try:
                cmds.scriptJob(kill=job, force=True)
            except Exception:
                pass

    def _on_idle() -> None:
        if _plugin_loaded():
            _disarm()
            return
        now = time.monotonic()
        if state["next_check"] is None:
            state["next_check"] = state["armed_at"] + WATCHDOG_GRACE_SECS
        if now < state["next_check"]:
            return
        if state["attempts"] >= WATCHDOG_MAX_ATTEMPTS:
            # Give up exactly once: a host that cannot kill the scriptJob must
            # not turn the give-up into an infinite warning stream.
            if state.get("gave_up"):
                return
            state["gave_up"] = True
            _disarm()
            _RUN_MARKER["watchdog_armed"] = False
            # The run has stopped trying. This is a reported failure, not a
            # hang, so the marker must not survive to be misread as one.
            _retire_run_marker(finished=False)
            _report_failure(
                "watchdog_give_up",
                RuntimeError(
                    "plug-in still not loaded after {} retries; load it manually with "
                    "cmds.loadPlugin('dcc_mcp_maya_plugin')".format(WATCHDOG_MAX_ATTEMPTS)
                ),
            )
            return
        state["attempts"] += 1
        state["next_check"] = now + WATCHDOG_GRACE_SECS
        _load_dcc_mcp_maya()

    try:
        state["job"] = script_job(event=("idle", _on_idle))
    except Exception as exc:
        _RUN_MARKER["watchdog_armed"] = False
        _report_failure("watchdog_schedule", exc)


_report_prior_bootstrap_hang()
if _maya_cmds() is not None:
    # Only arm a marker when a load can actually be attempted: outside a Maya
    # session nothing would ever retire it. Written before the first schedule
    # so that it exists before any attempt -- including the watchdog's retries.
    _mark_run_started()
scheduled = _schedule(_load_dcc_mcp_maya)
_arm_autoload_watchdog()
if not scheduled:
    # Nothing was queued. The watchdog may still own the run (it retries from
    # the idle queue), in which case its give-up path retires the marker;
    # otherwise retire now so a marker for a load that never started cannot be
    # misread as a hang on the next start-up.
    _retire_if_terminal(finished=False)
