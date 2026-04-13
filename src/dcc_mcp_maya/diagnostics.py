"""Diagnostic IPC action handlers for dcc-mcp-maya.

Registers three action handlers on the McpHttpServer so that the
``dcc-diagnostics`` and ``workflow`` example skills can retrieve live
runtime data by calling back into the Maya MCP server via IPC.

Handlers
--------
``get_audit_log``
    Returns entries from the server-level :class:`SandboxContext` audit log.
    Supports ``filter`` (all/success/denied/error) and ``action_name`` filters.

``get_action_metrics``
    Returns per-action performance counters from the shared
    :class:`ActionRecorder`.  Optionally filtered to a single action name.

``dispatch_action``
    Relays a ``{"action": "...", "params": {...}}`` request through the
    server's internal dispatcher.  Used by ``workflow__run_chain`` to execute
    multi-step chains via IPC without spawning extra sub-processes.

Usage
-----
Called automatically by :meth:`MayaMcpServer.register_builtin_actions`::

    server = MayaMcpServer()
    server.register_builtin_actions()   # registers handlers + sets env var
    handle = server.start()

The ``DCC_MCP_IPC_ADDRESS`` environment variable is set to the server's IPC
address so skill subprocesses can discover it automatically.
"""

from __future__ import annotations

import json
import logging
import os
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# ── module-level shared state ──────────────────────────────────────────────
# Populated by register_diagnostic_handlers() below.
_sandbox_context: Any = None  # SandboxContext | None
_action_recorder: Any = None  # ActionRecorder | None
_dispatcher_ref: Any = None  # ActionDispatcher | None


def _get_sandbox_context():
    """Return the shared SandboxContext, creating one lazily if needed."""
    global _sandbox_context  # noqa: PLW0603
    if _sandbox_context is None:
        try:
            from dcc_mcp_core import SandboxContext, SandboxPolicy  # noqa: PLC0415

            policy = SandboxPolicy()
            _sandbox_context = SandboxContext(policy)
        except Exception as exc:
            logger.debug("Failed to create SandboxContext: %s", exc)
    return _sandbox_context


def _get_action_recorder():
    """Return the shared ActionRecorder, creating one lazily if needed."""
    global _action_recorder  # noqa: PLW0603
    if _action_recorder is None:
        try:
            from dcc_mcp_core import ActionRecorder  # noqa: PLC0415

            _action_recorder = ActionRecorder("dcc-mcp-maya")
        except Exception as exc:
            logger.debug("Failed to create ActionRecorder: %s", exc)
    return _action_recorder


# ── handler implementations ────────────────────────────────────────────────


def _handle_get_audit_log(params_json: str) -> str:
    """Return audit log entries as a JSON string."""
    try:
        params = json.loads(params_json) if params_json else {}
    except json.JSONDecodeError:
        params = {}

    filter_ = params.get("filter", "all")
    action_name = params.get("action_name")
    limit = int(params.get("limit", 50))

    ctx = _get_sandbox_context()
    if ctx is None:
        return json.dumps({"success": False, "message": "SandboxContext not available."})

    try:
        audit = ctx.audit_log
        if action_name:
            entries = audit.entries_for_action(action_name)
        elif filter_ == "success":
            entries = audit.successes()
        elif filter_ == "denied":
            entries = audit.denials()
        else:
            entries = audit.entries()

        total = len(entries)
        serialized = []
        for entry in entries[:limit]:
            try:
                serialized.append({
                    "action": entry.action,
                    "outcome": entry.outcome,
                    "timestamp_ms": getattr(entry, "timestamp_ms", None),
                    "details": getattr(entry, "details", None),
                })
            except Exception:
                serialized.append(str(entry))

        return json.dumps({
            "success": True,
            "total_entries": total,
            "entries": serialized,
            "source": "maya-ipc",
        })
    except Exception as exc:
        logger.warning("get_audit_log handler error: %s", exc)
        return json.dumps({"success": False, "message": str(exc)})


def _handle_get_action_metrics(params_json: str) -> str:
    """Return ActionRecorder metrics as a JSON string."""
    try:
        params = json.loads(params_json) if params_json else {}
    except json.JSONDecodeError:
        params = {}

    action_name = params.get("action_name")

    recorder = _get_action_recorder()
    if recorder is None:
        return json.dumps({"success": False, "message": "ActionRecorder not available."})

    try:
        if action_name:
            metric = recorder.metrics(action_name)
            metrics_list = [_metric_to_dict(metric)] if metric else []
        else:
            metrics_list = [_metric_to_dict(m) for m in recorder.all_metrics()]

        return json.dumps({
            "success": True,
            "metrics": metrics_list,
            "source": "maya-ipc",
        })
    except Exception as exc:
        logger.warning("get_action_metrics handler error: %s", exc)
        return json.dumps({"success": False, "message": str(exc)})


def _handle_dispatch_action(params_json: str) -> str:
    """Relay a dispatch request through the server's ActionDispatcher."""
    try:
        params = json.loads(params_json) if params_json else {}
    except json.JSONDecodeError:
        return json.dumps({"success": False, "message": "Invalid JSON params."})

    action = params.get("action", "")
    action_params = params.get("params", {})

    if not action:
        return json.dumps({"success": False, "message": "Missing 'action' field."})

    dispatcher = _dispatcher_ref
    if dispatcher is None:
        return json.dumps({"success": False, "message": "Dispatcher not available."})

    try:
        result = dispatcher.dispatch(action, json.dumps(action_params))
        # result keys: "action", "output", "validation_skipped"
        output = result.get("output", "{}")
        if isinstance(output, str):
            try:
                return output  # already JSON
            except Exception:
                return json.dumps({"success": True, "message": output})
        return json.dumps(output)
    except Exception as exc:
        logger.warning("dispatch_action handler error for '%s': %s", action, exc)
        return json.dumps({"success": False, "message": str(exc)})


# ── registration helper ────────────────────────────────────────────────────


def register_diagnostic_handlers(server: Any, dispatcher: Any = None) -> None:
    """Register the three diagnostic action handlers on *server*.

    Also sets ``DCC_MCP_IPC_ADDRESS`` in the process environment so that
    skill subprocesses launched by the server can find the IPC endpoint.

    Args:
        server: A :class:`dcc_mcp_core.McpHttpServer` instance (the object
            returned by ``create_skill_manager``).
        dispatcher: Optional :class:`dcc_mcp_core.ActionDispatcher` reference
            for the ``dispatch_action`` relay handler.  When ``None``, relayed
            dispatch calls will return an error until set later.

    Example::

        from dcc_mcp_maya.diagnostics import register_diagnostic_handlers
        register_diagnostic_handlers(self._server, dispatcher=my_dispatcher)
    """
    global _dispatcher_ref  # noqa: PLW0603
    if dispatcher is not None:
        _dispatcher_ref = dispatcher

    try:
        server.register_handler("get_audit_log", _handle_get_audit_log)
        server.register_handler("get_action_metrics", _handle_get_action_metrics)
        server.register_handler("dispatch_action", _handle_dispatch_action)
        logger.debug("Registered diagnostic IPC handlers: get_audit_log, get_action_metrics, dispatch_action")
    except Exception as exc:
        logger.warning("Failed to register diagnostic handlers: %s", exc)
        return

    # Derive IPC address from the server handle if already started,
    # otherwise use the default pipe name for the current PID.
    # The env var is set before start() so skill subprocesses inherit it.
    _set_ipc_address_env()


def _set_ipc_address_env() -> None:
    """Derive and export DCC_MCP_IPC_ADDRESS for skill subprocesses."""
    if os.environ.get("DCC_MCP_IPC_ADDRESS"):
        return  # already set externally — respect the override

    try:
        from dcc_mcp_core import TransportAddress  # noqa: PLC0415

        addr = TransportAddress.default_local("maya", os.getpid())
        addr_str = str(addr)
        os.environ["DCC_MCP_IPC_ADDRESS"] = addr_str
        logger.debug("Set DCC_MCP_IPC_ADDRESS=%s", addr_str)
    except Exception as exc:
        logger.debug("Could not derive IPC address: %s", exc)


# ── helpers ────────────────────────────────────────────────────────────────


def _metric_to_dict(metric: Any) -> dict:
    return {
        "action_name": metric.action_name,
        "invocation_count": metric.invocation_count,
        "success_count": metric.success_count,
        "failure_count": metric.failure_count,
        "success_rate": round(metric.success_rate(), 4),
        "avg_duration_ms": round(metric.avg_duration_ms, 2),
        "p95_duration_ms": round(metric.p95_duration_ms, 2),
        "p99_duration_ms": round(metric.p99_duration_ms, 2),
    }
