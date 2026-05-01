"""In-process skill executor (issue #127).

Extracted from the previous monolithic ``server.py``.  Provides three
entry points consumed by :class:`MayaMcpServer`:

* :func:`run_skill_script` — load a skill ``main()`` and execute it on
  the calling thread.  No Maya / dispatcher dependencies.
* :func:`wire_in_process_executor` — register Python in-process handlers
  for every action currently in the registry (called once after
  startup-time skill loading).
* :func:`register_inprocess_handlers` — register handlers for an explicit
  action-name list (called by :meth:`MayaMcpServer.load_skill` for
  dynamic loads).

The dispatcher routing logic also lives here in
:func:`execute_in_process` so the composition root can stay small.

See: https://github.com/loonghao/dcc-mcp-maya/issues/127
"""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import Any, Callable, Dict, List

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
        try:
            from dcc_mcp_core.skill import skill_exception  # noqa: PLC0415

            return skill_exception(exc, message="Error loading skill script: {}".format(script_path))
        except ImportError:
            return {"success": False, "message": "Error loading {}: {}".format(script_path, exc)}

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
        try:
            from dcc_mcp_core.skill import skill_exception  # noqa: PLC0415

            return skill_exception(exc)
        except ImportError:
            return {"success": False, "message": str(exc)}


def execute_in_process(
    server_obj: Any,
    script_path: str,
    params: Dict[str, Any],
    action_name: str,
) -> Dict[str, Any]:
    """Execute a skill script via the attached Maya UI dispatcher.

    Routes through ``server_obj._maya_dispatcher.submit_callable`` when a
    dispatcher is attached so the script runs on Maya's UI thread.
    Falls back to executing inline on the calling thread otherwise
    (standalone / ``mayapy`` mode).

    The ``server_obj`` argument is the :class:`MayaMcpServer` instance
    (a ``DccServerBase``); we only access ``_maya_dispatcher`` so a
    duck-typed object suffices for testing.
    """
    dispatcher = getattr(server_obj, "_maya_dispatcher", None)
    if dispatcher is not None and hasattr(dispatcher, "submit_callable"):
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
            try:
                from dcc_mcp_core.skill import skill_exception  # noqa: PLC0415

                return skill_exception(
                    exc,
                    message="Dispatcher failed to execute {}".format(action_name),
                )
            except ImportError:
                return {"success": False, "message": "{}: {}".format(action_name, exc)}

        # Issue #153 — pass a DeferredToolResult straight through so the
        # core poll loop owns the lifecycle.  Detection is duck-typed on
        # ``check_is_finished`` to avoid hard-importing core internals.
        if hasattr(result, "check_is_finished"):
            return result  # type: ignore[return-value]

        if isinstance(result, dict):
            output = result.get("output")
            if hasattr(output, "check_is_finished"):
                return output  # type: ignore[return-value]
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


def register_inprocess_handlers(server_obj: Any, action_names: List[str]) -> int:
    """Register in-process Python handlers for ``action_names``.

    For each action that has a ``source_file`` and no handler registered
    yet, wraps :func:`execute_in_process` as an
    :meth:`McpHttpServer.register_handler` callable so ``tools/call``
    dispatches to the live Maya interpreter instead of spawning a
    ``mayapy`` subprocess.

    Returns the number of handlers newly registered.
    """
    inner = server_obj._server
    registered = 0
    for action_name in action_names:
        if inner.has_handler(action_name):
            continue

        try:
            action = inner.registry.get_action(action_name)
        except Exception:  # noqa: BLE001
            continue

        if not action:
            continue

        script_path = action.get("source_file") if isinstance(action, dict) else None
        if not script_path:
            continue

        def _make_handler(spath: str, aname: str) -> Callable[[Dict[str, Any]], Dict[str, Any]]:
            def handler(params: Dict[str, Any]) -> Dict[str, Any]:
                return execute_in_process(server_obj, spath, params, aname)

            return handler

        try:
            inner.register_handler(action_name, _make_handler(script_path, action_name))
            registered += 1
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to register in-process handler for %r: %s", action_name, exc)

    return registered


def wire_in_process_executor(server_obj: Any) -> None:
    """Register in-process handlers for every loaded action.

    Called once after :meth:`MayaMcpServer.register_builtin_actions`
    (and once after any dynamic :meth:`load_skill` call) so all loaded
    actions route through :func:`run_skill_script` instead of the
    subprocess executor.
    """
    inner = server_obj._server
    try:
        actions = inner.registry.list_actions_enabled()
    except AttributeError:
        logger.debug("server.registry not available — skipping in-process executor wiring")
        return

    action_names = [a["name"] for a in actions if isinstance(a, dict) and a.get("name")]
    registered = register_inprocess_handlers(server_obj, action_names)
    if registered > 0:
        logger.info(
            "Maya in-process executor: registered %d handler(s) via register_handler",
            registered,
        )
    else:
        logger.debug("Maya in-process executor: no new handlers registered (no loaded actions found)")
