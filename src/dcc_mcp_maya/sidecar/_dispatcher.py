"""Maya adapter hooks for core-owned sidecar action dispatch.

``dcc-mcp-core`` owns the DCC-neutral sidecar contract: payload validation,
error envelopes, script-source resolution flow, and result normalization.
Maya keeps only the host-specific hooks:

* locate the currently running :class:`MayaMcpServer`;
* read Maya's action registry shape;
* execute via :func:`dcc_mcp_maya._executor.execute_in_process` so
  ``tools.yaml`` affinity semantics remain unchanged.

Built-in sidecar actions (``load_skill``, ``get_skill_info``) are server
methods, not script-backed actions. They are handled directly in this
module before delegating to ``SidecarActionDispatcher``.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Callable, Mapping, Optional

from dcc_mcp_core.sidecar import SidecarActionDispatcher, SidecarDispatchRequest

logger = logging.getLogger(__name__)

__all__ = ["dispatch_payload"]

# Built-in sidecar actions that are not backed by skill scripts.
# These are handled by calling server methods directly.
_BUILTIN_SIDECAR_ACTIONS = frozenset({"load_skill", "get_skill_info"})


def dispatch_payload(
    payload: Mapping[str, Any] | str,
    *,
    server_lookup: Optional[Callable[[], Any]] = None,
) -> dict[str, Any]:
    """Dispatch a sidecar payload through the shared core helper.

    Built-in actions (``load_skill``, ``get_skill_info``) are handled
    directly since they are server methods, not script-backed actions.
    All other actions delegate to the core ``SidecarActionDispatcher``.

    ``server_lookup`` remains injectable for tests and for the lightweight
    ``qtserver://`` stubs used by transport coverage.
    """
    coerced = _coerce_payload(payload)

    if isinstance(coerced, Mapping):
        action = coerced.get("action")
        if isinstance(action, str) and action in _BUILTIN_SIDECAR_ACTIONS:
            server = (server_lookup or _default_server_lookup)()
            if server is None:
                return _not_running_envelope(action, coerced.get("request_id"))
            return _dispatch_builtin_action(
                action=action,
                args=coerced.get("args", {}) or {},
                server=server,
                request_id=coerced.get("request_id"),
            )

    dispatcher = SidecarActionDispatcher(
        "maya",
        server_provider=server_lookup or _default_server_lookup,
        action_resolver=_resolve_action_source,
        executor=_execute_maya_request,
    )
    return dispatcher.dispatch_payload(coerced)


def _not_running_envelope(action: str, request_id: Any) -> dict[str, Any]:
    """Return a structured ``server-not-running`` envelope for built-in actions."""
    return _error_envelope(
        code="server-not-running",
        message=f"Cannot dispatch built-in sidecar action '{action}': server is not running",
        action=action,
        request_id=request_id,
    )


def _error_envelope(code: str, message: str, **context: Any) -> dict[str, Any]:
    """Build a standard error envelope matching the core sidecar convention."""
    clean = {k: v for k, v in context.items() if v not in (None, "", {})}
    result: dict[str, Any] = {"success": False, "message": message, "error": code}
    if clean:
        result["context"] = clean
    return result


def _dispatch_builtin_action(
    action: str,
    args: Mapping[str, Any],
    server: Any,
    request_id: Any,
) -> dict[str, Any]:
    """Dispatch a built-in sidecar action by calling the server method directly."""
    try:
        if action == "load_skill":
            return _handle_load_skill(args, server, request_id)
        if action == "get_skill_info":
            return _handle_get_skill_info(args, server, request_id)
    except Exception as exc:  # noqa: BLE001
        logger.warning("builtin sidecar action %r failed: %s", action, exc)
        return _error_envelope(
            code="dispatch-failed",
            message=f"Built-in sidecar action '{action}' failed",
            action=action,
            request_id=request_id,
            error_type=type(exc).__name__,
        )
    return _error_envelope(
        code="unknown-action",
        message=f"Unknown built-in sidecar action: {action}",
        action=action,
        request_id=request_id,
    )


def _handle_load_skill(
    args: Mapping[str, Any],
    server: Any,
    request_id: Any,
) -> dict[str, Any]:
    """Handle ``load_skill`` by calling ``server.load_skill()``."""
    skill_name = args.get("skill_name") if isinstance(args, Mapping) else None
    if not isinstance(skill_name, str) or not skill_name.strip():
        return _error_envelope(
            code="payload-malformed",
            message="load_skill requires a non-empty skill_name",
            action="load_skill",
            request_id=request_id,
            reason="missing-skill-name",
        )

    loaded = server.load_skill(skill_name)
    if loaded:
        return {
            "success": True,
            "loaded": True,
            "skill_name": skill_name,
            "message": f"Skill '{skill_name}' loaded successfully",
            "request_id": request_id or "",
            "action": "load_skill",
        }
    return {
        "success": False,
        "loaded": False,
        "skill_name": skill_name,
        "message": f"Failed to load skill '{skill_name}'",
        "error": "load-skill-failed",
        "request_id": request_id or "",
        "action": "load_skill",
    }


def _handle_get_skill_info(
    args: Mapping[str, Any],
    server: Any,
    request_id: Any,
) -> dict[str, Any]:
    """Handle ``get_skill_info`` by calling ``server.get_skill_info()``."""
    skill_name = args.get("skill_name") if isinstance(args, Mapping) else None
    if not isinstance(skill_name, str) or not skill_name.strip():
        return _error_envelope(
            code="payload-malformed",
            message="get_skill_info requires a non-empty skill_name",
            action="get_skill_info",
            request_id=request_id,
            reason="missing-skill-name",
        )

    info = server.get_skill_info(skill_name)
    return {
        "success": True,
        "skill_name": skill_name,
        "skill_info": str(info) if info is not None else None,
        "message": f"Skill info for '{skill_name}'",
        "request_id": request_id or "",
        "action": "get_skill_info",
    }


def _coerce_payload(payload: Mapping[str, Any] | str) -> Any:
    if isinstance(payload, str):
        try:
            return json.loads(payload)
        except json.JSONDecodeError:
            return payload
    return payload


def _resolve_action_source(action_name: str, *, server: Any, **_: Any) -> Optional[Mapping[str, Any]]:
    try:
        actions = server.list_actions()
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "sidecar dispatch: server.list_actions() raised; treating %r as unknown: %s",
            action_name,
            exc,
        )
        return None

    for action in actions or ():
        if _attr_or_item(action, "name") != action_name:
            continue
        return {
            "source_file": _attr_or_item(action, "source_file"),
            "skill_name": _attr_or_item(action, "skill_name") or _attr_or_item(action, "skill") or "",
            "thread_affinity": _attr_or_item(action, "thread_affinity") or _attr_or_item(action, "affinity") or "",
            "execution": _attr_or_item(action, "execution") or "",
            "timeout_hint_secs": _attr_or_item(action, "timeout_hint_secs"),
        }
    return None


def _execute_maya_request(request: SidecarDispatchRequest) -> Any:
    from dcc_mcp_maya._executor import execute_in_process  # noqa: PLC0415

    result = execute_in_process(
        request.server,
        request.script_path,
        dict(request.args),
        request.action,
    )
    if isinstance(result, Mapping):
        enriched = dict(result)
    else:
        enriched = {"success": True, "data": result}
    enriched.setdefault("request_id", request.request_id or "")
    enriched.setdefault("action", request.action)
    return enriched


def _attr_or_item(obj: Any, key: str) -> Any:
    if hasattr(obj, key):
        return getattr(obj, key)
    if isinstance(obj, Mapping):
        return obj.get(key)
    return None


def _default_server_lookup() -> Any:
    try:
        from dcc_mcp_maya import server as _server_mod  # noqa: PLC0415
    except ImportError:
        return None
    return getattr(_server_mod, "_server_instance", None)
