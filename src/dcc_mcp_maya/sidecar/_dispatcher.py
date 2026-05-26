"""Maya adapter hooks for core-owned sidecar action dispatch.

``dcc-mcp-core`` owns the DCC-neutral sidecar contract: payload validation,
error envelopes, script-source resolution flow, and result normalization.
Maya keeps only the host-specific hooks:

* locate the currently running :class:`MayaMcpServer`;
* read Maya's action registry shape;
* execute via :func:`dcc_mcp_maya._executor.execute_in_process` so
  ``tools.yaml`` affinity semantics remain unchanged.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Callable, Mapping, Optional

from dcc_mcp_core.sidecar import SidecarActionDispatcher, SidecarDispatchRequest

logger = logging.getLogger(__name__)

__all__ = ["dispatch_payload"]


def dispatch_payload(
    payload: Mapping[str, Any] | str,
    *,
    server_lookup: Optional[Callable[[], Any]] = None,
) -> dict[str, Any]:
    """Dispatch a sidecar payload through the shared core helper.

    ``server_lookup`` remains injectable for tests and for the lightweight
    ``qtserver://`` stubs used by transport coverage.
    """

    dispatcher = SidecarActionDispatcher(
        "maya",
        server_provider=server_lookup or _default_server_lookup,
        action_resolver=_resolve_action_source,
        executor=_execute_maya_request,
    )
    return dispatcher.dispatch_payload(_coerce_payload(payload))


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
