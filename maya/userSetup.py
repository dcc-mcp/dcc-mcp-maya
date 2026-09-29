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

#: Maximum number of watchdog-driven load retries after the deferred call.
WATCHDOG_MAX_ATTEMPTS = 3
#: Seconds the watchdog waits between two load attempts.
WATCHDOG_GRACE_SECS = 10.0


def _bootstrap_error_dir() -> Path:
    """Directory that receives user-visible auto-load failure records."""
    override = os.environ.get(BOOTSTRAP_ERROR_DIR_ENV)
    if override:
        return Path(override)
    return Path.home() / ".dcc-mcp" / "receipts" / "bootstrap-errors"


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
    try:
        log_dir = _bootstrap_error_dir()
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / "userSetup-{}.jsonl".format(datetime.now(timezone.utc).strftime("%Y%m%d"))
        record = {
            "schema_version": 1,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "pid": os.getpid(),
            "stage": stage,
            "status": "failed",
            "error_type": error_type,
            "error": str(exc),
            "traceback": traceback.format_exc(),
        }
        with log_path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    except Exception:
        pass
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
    """
    try:
        _apply_default_env()
        _setup_module_paths()
    except Exception as exc:
        _report_failure("environment", exc)
        return

    try:
        from dcc_mcp_maya.install import bootstrap_user_setup
    except Exception as exc:
        _report_failure("import", exc)
        return

    try:
        _load_via_bootstrap(bootstrap_user_setup)
    except Exception as exc:
        _report_failure("plugin_load", exc)
        return

    # A load that returns cleanly without registering the plug-in is the
    # failure mode that started this investigation: every channel reported
    # success while no MCP server existed. Verify instead of assuming.
    try:
        cmds = _maya_cmds()
        if cmds is not None and not cmds.pluginInfo("dcc_mcp_maya_plugin", query=True, loaded=True):
            _report_failure(
                "plugin_verify",
                RuntimeError(
                    "bootstrap_user_setup() returned but dcc_mcp_maya_plugin is not loaded; "
                    "check the Plug-in Manager and the bootstrap-error log"
                ),
            )
    except Exception as exc:
        _report_failure("plugin_verify", exc)


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
        return
    eval_deferred = getattr(cmds, "evalDeferred", None)
    if eval_deferred is None:
        _report_failure(
            "schedule",
            RuntimeError("maya.cmds.evalDeferred is unavailable; the Maya deferred queue is not ready"),
        )
        return
    try:
        eval_deferred(callback, lowestPriority=True)
    except Exception as exc:
        _report_failure("schedule", exc)


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
        _report_failure("watchdog_schedule", exc)


_schedule(_load_dcc_mcp_maya)
_arm_autoload_watchdog()
