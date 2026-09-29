"""Maya userSetup.py -- auto-load the receipted dcc-mcp-maya module."""

from __future__ import annotations

import json
import logging
import os
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType
from typing import Optional

logger = logging.getLogger(__name__)

BOOTSTRAP_ERROR_DIR_ENV = "DCC_MCP_MAYA_BOOTSTRAP_ERROR_DIR"


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
        bootstrap_user_setup(defer=False)
    except Exception as exc:
        _report_failure("plugin_load", exc)


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


_schedule(_load_dcc_mcp_maya)
