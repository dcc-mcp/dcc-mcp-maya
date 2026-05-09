"""In-process skill executor (issue #127).

Extracted from the previous monolithic ``server.py``.  Core owns skill routing
through ``HostExecutionBridge`` and the global in-process executor.

This module keeps the direct script runner used by the bridge, tests, and
internal helpers.

See: https://github.com/loonghao/dcc-mcp-maya/issues/127
"""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import Any, Dict

# Import third-party modules
from dcc_mcp_core.skill import skill_exception

# Import local modules
from dcc_mcp_maya import _affinity

logger = logging.getLogger(__name__)


def run_skill_script(script_path: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Load and execute a skill script in the current Python process.

    Implements the ``main(**params)`` calling convention used by all
    ``dcc-mcp-maya`` skill scripts.  The ``if __name__ == "__main__":
    run_main(main)`` guard is intentionally **not** triggered so
    parameters are forwarded directly without going through subprocess
    stdout.

    Parameters
    ----------
    script_path:
        Path to the skill Python script.
    params:
        Keyword arguments forwarded to ``main(**params)``.

    Returns
    -------
    dict
        The ``{"success": ..., "message": ..., ...}`` result dict
        (or whatever shape the skill's ``main`` produced).
    """
    import importlib.util  # noqa: PLC0415

    spec = importlib.util.spec_from_file_location("_maya_skill_script", script_path)
    if spec is None or spec.loader is None:
        return {"success": False, "message": "Cannot load skill script: {}".format(script_path)}

    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)  # type: ignore[union-attr]
    except SystemExit:
        pass
    except Exception as exc:  # noqa: BLE001
        return skill_exception(exc, message="Error loading skill script: {}".format(script_path))

    if hasattr(mod, "__mcp_result__"):
        return mod.__mcp_result__  # type: ignore[return-value]

    main_fn = getattr(mod, "main", None)
    if main_fn is None:
        return {
            "success": False,
            "message": "Skill script has no main() entry point: {}".format(script_path),
        }

    try:
        result = main_fn(**params)
        return result if isinstance(result, dict) else {"success": True, "message": str(result)}
    except SystemExit:
        return getattr(mod, "__mcp_result__", {"success": True, "message": "Script executed"})
    except Exception as exc:  # noqa: BLE001
        return skill_exception(exc)


def execute_in_process(
    server_obj: Any,
    script_path: str,
    params: Dict[str, Any],
    action_name: str,
) -> Dict[str, Any]:
    """Execute a skill script via the attached Maya UI dispatcher.

    Routes through ``server_obj._maya_dispatcher.submit_callable`` when
    a dispatcher is attached **and** the action declares
    ``affinity: main`` in its ``tools.yaml``.  Actions declared
    ``affinity: any`` (pure filesystem / no ``maya.cmds`` access —
    e.g. the ``introspect_*`` family) execute inline on the calling
    thread so they do not compete with viewport work on Maya's UI
    thread.  Falls back to executing inline when no dispatcher is
    attached (standalone / ``mayapy`` mode).

    The ``server_obj`` argument is the :class:`MayaMcpServer` instance
    (a ``DccServerBase``); we only access ``_maya_dispatcher`` so a
    duck-typed object suffices for testing.
    """
    affinity = _affinity.resolve_affinity(script_path)
    dispatcher = getattr(server_obj, "_maya_dispatcher", None)
    dispatcher_usable = affinity == "main" and dispatcher is not None and hasattr(dispatcher, "submit_callable")
    if dispatcher_usable:
        # Issue #151 — surface dispatcher-side exceptions (cancellation,
        # main-thread crashes, timeouts) as structured envelopes instead
        # of letting them propagate as Internal Errors.
        try:
            result = dispatcher.submit_callable(
                action_name,
                lambda: run_skill_script(script_path, params),
                affinity="main",
            )
        except BaseException as exc:  # noqa: BLE001 — relay everything
            return skill_exception(
                exc,
                message="Dispatcher failed to execute {}".format(action_name),
            )

        if isinstance(result, dict):
            output = result.get("output")
            if isinstance(output, dict):
                return output
            if not result.get("success", True):
                return {
                    "success": False,
                    "message": result.get("error") or "Dispatcher returned failure for {}".format(action_name),
                }
            if output is not None:
                return {"success": True, "message": str(output)}
        return {
            "success": False,
            "message": "Dispatcher returned unexpected result for {}".format(action_name),
        }

    return run_skill_script(script_path, params)
