"""Maya-side dispatcher for the sidecar wire frame (RFC #998 Phase 2).

The sidecar Rust binary (``dcc-mcp-server sidecar`` shipped from
``dcc-mcp-core``) connects to Maya's ``commandPort`` and sends a
single-line Python expression per ``tools/call``::

    __import__('dcc_mcp_maya._sidecar', fromlist=['dispatch']).dispatch(
        {"action": "<backend_tool>", "args": {...}, "request_id": "..."}
    )

Maya's ``commandPort`` (opened with ``sourceType='python'``) evaluates
that expression on the **main thread**, so this dispatcher inherits
the same thread-affinity guarantees the in-process MCP HTTP server
provides today. No cross-thread marshalling, no `executeDeferred`
games — `cmds.*` is safe to call directly from the body of the skill
script invoked by :func:`dispatch`.

Returns
-------

The function returns a single-line **JSON string** that Maya's
commandPort sends straight back to the sidecar. The Rust client parses
it as a :class:`serde_json::Value`. Newlines and tabs are explicitly
escaped (``ensure_ascii=False``) so a multi-line traceback does not
break the line-oriented wire protocol.

Error envelope
--------------

Any failure between "we received the wire frame" and "we have a real
return value" is wrapped in a structured envelope (still single line)
with ``success: false`` and an ``error`` discriminator the gateway can
surface verbatim to MCP clients:

* ``server-not-running`` — :class:`MayaMcpServer` was never started in
  this Maya session, or has already been torn down. Operator should
  load the dcc-mcp-maya plug-in.
* ``payload-malformed`` — the wire frame failed shape validation
  (missing ``action`` key, wrong types, etc.).
* ``unknown-action`` — the action name is not in the running server's
  action registry. May happen when the gateway has cached a tool from
  a skill that was subsequently unloaded.
* ``no-source-file`` — the action exists but its :class:`ToolMeta`
  carries no ``source_file``. Usually means it is a Rust-implemented
  built-in (e.g. ``search_tools``) that does not go through the
  Python skill runner.
* ``dispatch-failed`` — anything else (skill script raised, import
  failed, etc.). Carries the formatted traceback in ``traceback``.

The error envelope mirrors :func:`dcc_mcp_maya.api.maya_error` so
gateway-side ranking heuristics (which already know that shape) keep
working.
"""

from __future__ import annotations

import json
import logging
import traceback
from typing import Any, Callable, Mapping, Optional

logger = logging.getLogger(__name__)

__all__ = ["dispatch", "dispatch_payload"]


def dispatch(payload: Mapping[str, Any] | str) -> str:
    """Entry point invoked by the sidecar binary's wire expression.

    Always returns a single-line JSON string — never raises, never
    returns ``None`` — so the line-oriented commandPort protocol stays
    intact. Exceptions become structured envelopes carrying the
    traceback for postmortem audit.

    Args:
        payload: The decoded wire frame from the sidecar. Accepts the
            already-parsed mapping the wire expression hands us. A
            JSON string is also tolerated to make manual smoke tests
            from Maya's script editor easier (``dispatch('{"action":
            "..."}')``).

    Returns:
        Single-line JSON string. Either the action's own return value
        (re-serialised with ``ensure_ascii=False``) or one of the
        structured error envelopes documented in the module docstring.
    """
    try:
        return _dispatch_inner(payload, server_lookup=_default_server_lookup)
    except Exception as exc:  # noqa: BLE001 — last-resort safety net
        logger.exception("dcc-mcp-maya sidecar dispatch raised unexpectedly")
        return _envelope(
            success=False,
            error="dispatch-failed",
            message=f"unexpected dispatcher error: {exc}",
            traceback=traceback.format_exc(),
            request_id=_safe_request_id(payload),
        )


def dispatch_payload(
    payload: Mapping[str, Any] | str,
    *,
    server_lookup: Optional[Callable[[], Any]] = None,
) -> str:
    """Like :func:`dispatch` but with an injectable server-lookup hook.

    Exposed for unit tests that need to stub the running
    :class:`MayaMcpServer` (which itself depends on ``maya.cmds``).
    Production code always calls :func:`dispatch`.
    """
    lookup = server_lookup or _default_server_lookup
    try:
        return _dispatch_inner(payload, server_lookup=lookup)
    except Exception as exc:  # noqa: BLE001
        logger.exception("dcc-mcp-maya sidecar dispatch_payload raised unexpectedly")
        return _envelope(
            success=False,
            error="dispatch-failed",
            message=f"unexpected dispatcher error: {exc}",
            traceback=traceback.format_exc(),
            request_id=_safe_request_id(payload),
        )


# ── internals ──────────────────────────────────────────────────────


def _dispatch_inner(
    payload: Mapping[str, Any] | str,
    *,
    server_lookup: Callable[[], Any],
) -> str:
    parsed = _coerce_payload(payload)
    if parsed is None:
        return _envelope(
            success=False,
            error="payload-malformed",
            message="payload must be a JSON object or dict with `action` key",
            request_id="",
        )
    action_name = parsed.get("action")
    if not isinstance(action_name, str) or not action_name.strip():
        return _envelope(
            success=False,
            error="payload-malformed",
            message="payload.action must be a non-empty string",
            request_id=str(parsed.get("request_id") or ""),
        )
    args = parsed.get("args") or {}
    if not isinstance(args, Mapping):
        return _envelope(
            success=False,
            error="payload-malformed",
            message=f"payload.args must be a JSON object (got {type(args).__name__})",
            request_id=str(parsed.get("request_id") or ""),
            action=action_name,
        )
    request_id = str(parsed.get("request_id") or "")

    server = server_lookup()
    if server is None:
        return _envelope(
            success=False,
            error="server-not-running",
            message=(
                "MayaMcpServer is not initialised; load the dcc-mcp-maya "
                "plug-in or call dcc_mcp_maya.start_server() before "
                "dispatching"
            ),
            request_id=request_id,
            action=action_name,
        )

    script_path = _resolve_script_path(server, action_name)
    if script_path is None:
        return _envelope(
            success=False,
            error="unknown-action",
            message=f"action {action_name!r} is not registered with this Maya MCP server",
            request_id=request_id,
            action=action_name,
        )
    if not script_path:
        return _envelope(
            success=False,
            error="no-source-file",
            message=(
                f"action {action_name!r} carries no source_file (likely "
                "a Rust-implemented built-in); the sidecar cannot dispatch it"
            ),
            request_id=request_id,
            action=action_name,
        )

    # ── execute via :func:`execute_in_process` so ``tools.yaml``
    #   ``affinity`` is respected ────────────────────────────────
    #
    # The old code called :func:`run_skill_script` directly, which
    # always runs on the calling thread (the Qt main thread for
    # qtserver:// transport).  That defeats ``affinity: any`` —
    # those actions are safe to run off the main thread but were
    # still blocking the UI.
    #
    # :func:`execute_in_process` reads ``tools.yaml``, then:
    #
    # * ``affinity == "any"`` → run inline on the *current* thread.
    #   For qtserver:// the current thread IS the Qt main thread,
    #   so we additionally dispatch through the main-thread queue
    #   only when we are NOT already on the main thread (HTTP worker
    #   path).  For the qtserver:// path we intentionally stay
    #   synchronous — the Qt event loop pumps between requests.
    # * ``affinity == "main"`` (default) → use the dispatcher or
    #   main-thread queue so the call always lands on the Maya UI
    #   thread.
    #
    # We lazy-import to keep the module importable without Maya.
    from dcc_mcp_maya._executor import execute_in_process  # noqa: PLC0415

    result = execute_in_process(server, script_path, dict(args), action_name)
    if not isinstance(result, Mapping):
        # Defensive: ``run_skill_script`` always returns a dict today,
        # but if a future refactor relaxes that contract we still want
        # a valid envelope on the wire.
        result = {"success": True, "data": result}

    # Enrich with correlation IDs from the wire frame so the gateway
    # can match an async response to its request.  ``setdefault`` keeps
    # any value the skill already produced (rare, but happens with
    # the ``request_id`` echo pattern some pipeline skills use).
    enriched = dict(result)
    enriched.setdefault("request_id", request_id)
    enriched.setdefault("action", action_name)
    return _to_single_line_json(enriched)


def _coerce_payload(payload: Mapping[str, Any] | str) -> Optional[Mapping[str, Any]]:
    """Accept either an already-parsed dict or a JSON string."""
    if isinstance(payload, Mapping):
        return payload
    if isinstance(payload, str):
        try:
            obj = json.loads(payload)
        except json.JSONDecodeError:
            return None
        return obj if isinstance(obj, Mapping) else None
    return None


def _resolve_script_path(server: Any, action_name: str) -> Optional[str]:
    """Return the script file backing the named action, or ``None``.

    ``None`` distinguishes "action unknown" from "action exists but
    has no source_file" — the latter returns an empty string so the
    caller can surface ``no-source-file`` rather than ``unknown-action``.
    """
    try:
        actions = server.list_actions()
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "sidecar dispatch: server.list_actions() raised — treating action %r as unknown. cause: %s",
            action_name,
            exc,
        )
        return None
    for action in actions or ():
        name = _attr_or_item(action, "name")
        if name != action_name:
            continue
        source = _attr_or_item(action, "source_file")
        if source is None:
            return ""
        return str(source)
    return None


def _attr_or_item(obj: Any, key: str) -> Any:
    """Read ``obj.<key>`` if it exists, else ``obj[key]`` if mapping-like.

    ``server.list_actions()`` returns Rust-backed objects with attribute
    access; test stubs return dicts.  Supporting both keeps the test
    surface unencumbered.
    """
    if hasattr(obj, key):
        return getattr(obj, key)
    if isinstance(obj, Mapping):
        return obj.get(key)
    return None


def _default_server_lookup() -> Any:
    """Return the currently-running :class:`MayaMcpServer`, if any.

    The lookup is deferred so the dispatcher module can be imported in
    test contexts that have never instantiated a MayaMcpServer (and
    that therefore cannot tolerate the `maya.cmds` import the server
    module's globals would otherwise trigger).
    """
    try:
        from dcc_mcp_maya import server as _server_mod  # noqa: PLC0415
    except ImportError:
        return None
    return getattr(_server_mod, "_server_instance", None)


def _envelope(
    *,
    success: bool,
    request_id: str,
    error: str | None = None,
    message: str | None = None,
    traceback: str | None = None,
    action: str | None = None,
) -> str:
    """Build a single-line JSON error / minimal-success envelope."""
    body: dict[str, Any] = {"success": success, "request_id": request_id}
    if action:
        body["action"] = action
    if error:
        body["error"] = error
    if message:
        body["message"] = message
    if traceback:
        body["traceback"] = traceback
    return _to_single_line_json(body)


def _to_single_line_json(obj: Mapping[str, Any]) -> str:
    """Serialise ``obj`` to JSON guaranteed to fit on one line.

    Maya's ``commandPort`` is line-oriented: every ``\\n`` in the
    response would be interpreted as "end of reply" by the sidecar's
    ``read_line`` loop and any subsequent bytes would corrupt the
    next request/response pair. We serialise with explicit separators
    plus ``str.replace`` for the (rare) embedded newline / tab inside
    string values.
    """
    encoded = json.dumps(obj, separators=(",", ":"), ensure_ascii=False)
    return encoded.replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t")


def _safe_request_id(payload: Mapping[str, Any] | str) -> str:
    if isinstance(payload, Mapping):
        rid = payload.get("request_id")
        if isinstance(rid, str):
            return rid
    return ""
