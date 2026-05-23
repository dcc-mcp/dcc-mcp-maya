"""Maya resource publishing wiring (issue #187).

Core 0.15.0 ships ``McpHttpServer.resources()`` → :class:`ResourceHandle`
with ``set_scene`` / ``register_producer`` / ``notify_updated`` /
``register_output_buffer``.  ``scene://current`` is a built-in resource
URI that returns ``status: no_scene_published`` until the embedding
adapter calls ``set_scene(...)``.  This module is that adapter for
Maya.

Public surface:

* :class:`MayaResourceBinder` — composes a Maya scene-snapshot publisher
  (``scene://current``) plus a small fleet of dynamic producers
  (``maya-cmds://help/<cmd>``, ``maya-cmds://flags/<cmd>``,
  ``maya-api://signatures/<class>``, ``maya-project://current``).
* :func:`install_resources(server)` — one-shot helper invoked from
  :meth:`MayaMcpServer.register_builtin_actions`.

SOLID notes
-----------
* **Single Responsibility** — each producer is a pure function from
  URI to ``{"mimeType", "text"}``; the binder only orchestrates
  registration and scene-snapshot lifetime.
* **Open/Closed** — the snapshot source is injectable
  (:attr:`MayaResourceBinder.snapshot_provider`) and the scriptJob
  installer is injectable (:attr:`MayaResourceBinder.event_installer`),
  so tests can drive the throttling state machine without a live Maya.
* **Dependency Inversion** — every Maya-specific call (``maya.cmds``,
  ``maya.api.OpenMaya``) is lazy-imported inside the producer body so
  the module is importable in plain Python.

Memory rule (``feedback_resources_api.md``): every call to
``server._server.resources()`` lives in this file.  Skill scripts and
plugin code go through the binder, never the raw handle.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

#: Disable scene-snapshot publishing entirely with this env var (e.g.
#: when an embedding host wants to drive ``scene://current`` itself).
ENV_RESOURCES = "DCC_MCP_MAYA_RESOURCES"

#: Throttle for ``scene://current`` republishing.  Maya's
#: ``DagObjectCreated`` scriptJob fires per-node, which can flood SSE
#: subscribers during bulk imports.  500 ms is a sweet spot — fast
#: enough that an interactive user feels resources land "live", slow
#: enough that a 1000-node import collapses to ~2 SSE frames.
DEFAULT_SCENE_THROTTLE_SECS: float = 0.5

#: Scene-event names whose firing triggers a republish.  Matches the
#: vanilla Maya scriptJob event vocabulary; unknown names are silently
#: skipped at install time so per-version differences don't kill
#: bootstrap.
DEFAULT_SCENE_EVENTS: tuple = (
    "SceneSaved",
    "SceneOpened",
    "NewSceneOpened",
    "SceneImported",
    "DagObjectCreated",
    "NameChanged",
    "SelectionChanged",
)

#: Maya-specific dynamic resource URIs we register producers for.
#: Each maps to a ``ResourceHandle.register_producer`` call; the
#: producer callable is dispatched on a Tokio worker thread when an MCP
#: client calls ``resources/read``.
SCHEME_MAYA_CMDS = "maya-cmds://"
SCHEME_MAYA_API = "maya-api://"
SCHEME_MAYA_PROJECT = "maya-project://"


# ---------------------------------------------------------------------------
# Env-var resolution
# ---------------------------------------------------------------------------


def resolve_enabled(flag: Optional[bool] = None) -> bool:
    """Resolve whether resource wiring should run.

    Priority: explicit ``flag`` argument > :data:`ENV_RESOURCES` env var
    (``"0"`` disables) > ``True``.  Mirrors :func:`_project_tools.resolve_enabled`.
    """
    if flag is not None:
        return bool(flag)
    raw = os.environ.get(ENV_RESOURCES)
    if raw is None:
        return True
    return raw.strip() != "0"


# ---------------------------------------------------------------------------
# Producer callables — pure functions, lazy maya.cmds import
# ---------------------------------------------------------------------------


def _read_text(text: str, mime: str = "text/plain") -> Dict[str, Any]:
    """Build the ``{"mimeType", "text"}`` reply expected by core."""
    return {"mimeType": mime, "text": text}


def _maya_cmds():
    """Lazy ``maya.cmds`` import; returns ``None`` outside Maya."""
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        return cmds
    except Exception:  # noqa: BLE001
        return None


def _maya_cmds_help_producer(uri: str) -> Dict[str, Any]:
    """Producer for ``maya-cmds://help/<command>`` URIs.

    Returns the ``cmds.help(command)`` text.  When ``maya.cmds`` is
    unavailable (headless without Maya, plain Python), returns a
    ``status: maya_unavailable`` JSON envelope so the agent can degrade
    gracefully.

    URI grammar: ``maya-cmds://help/<command>`` or
    ``maya-cmds://flags/<command>`` (the latter dispatches to
    :func:`_maya_cmds_flags_producer`).
    """
    parsed = _parse_path_uri(uri, scheme=SCHEME_MAYA_CMDS)
    if parsed is None or not parsed:
        return _read_text(
            json.dumps({"status": "invalid_uri", "uri": uri}),
            mime="application/json",
        )

    section = parsed[0]
    target = parsed[1] if len(parsed) > 1 else ""

    if section == "flags":
        return _maya_cmds_flags_producer_inner(target)

    cmds = _maya_cmds()
    if cmds is None:
        return _read_text(
            json.dumps({"status": "maya_unavailable", "uri": uri}),
            mime="application/json",
        )
    if not target:
        return _read_text(
            json.dumps({"status": "missing_command", "hint": "use maya-cmds://help/<command>"}),
            mime="application/json",
        )
    try:
        text = cmds.help(target, language="python")
    except Exception as exc:  # noqa: BLE001
        return _read_text(
            json.dumps({"status": "command_not_found", "command": target, "error": str(exc)}),
            mime="application/json",
        )
    return _read_text(text or "(no help text)")


def _maya_cmds_flags_producer_inner(command: str) -> Dict[str, Any]:
    """Body for the ``maya-cmds://flags/<command>`` slice.

    Returns a JSON map of ``{flag_name: {short, long, types, description}}``
    when available, or a degraded envelope on failure.  The path is
    isolated as a small inner function so the parent producer can route
    on the URI prefix without growing into a maintenance hazard.
    """
    if not command:
        return _read_text(
            json.dumps({"status": "missing_command", "hint": "use maya-cmds://flags/<command>"}),
            mime="application/json",
        )
    cmds = _maya_cmds()
    if cmds is None:
        return _read_text(
            json.dumps({"status": "maya_unavailable", "command": command}),
            mime="application/json",
        )
    try:
        # ``cmds.help(cmd, flags=True)`` is the canonical introspection
        # entry; the result shape varies across Maya versions, so we
        # serialise whatever comes back as JSON-friendly text.
        flags = cmds.help(command, flags=True)
    except Exception as exc:  # noqa: BLE001
        return _read_text(
            json.dumps({"status": "command_not_found", "command": command, "error": str(exc)}),
            mime="application/json",
        )
    return _read_text(
        json.dumps({"command": command, "flags": flags}, default=str),
        mime="application/json",
    )


def _maya_api_signatures_producer(uri: str) -> Dict[str, Any]:
    """Producer for ``maya-api://signatures/<class>`` URIs.

    Returns a JSON description of the OpenMaya class's public methods —
    cheap enough to compute on demand because ``inspect`` is local.
    """
    parsed = _parse_path_uri(uri, scheme=SCHEME_MAYA_API)
    if parsed is None or len(parsed) < 2 or parsed[0] != "signatures":
        return _read_text(
            json.dumps({"status": "invalid_uri", "uri": uri, "hint": "use maya-api://signatures/<class>"}),
            mime="application/json",
        )
    class_name = parsed[1]
    try:
        import importlib  # noqa: PLC0415

        # Honor both API 1.0 and API 2.0 — agents typically ask for
        # API 2.0 names like ``MFnMesh``.
        for module_path in (
            "maya.api.OpenMaya",
            "maya.api.OpenMayaAnim",
            "maya.api.OpenMayaUI",
            "maya.OpenMaya",
        ):
            try:
                mod = importlib.import_module(module_path)
            except Exception:  # noqa: BLE001
                continue
            cls = getattr(mod, class_name, None)
            if cls is None:
                continue
            return _read_text(
                json.dumps(
                    {
                        "class": class_name,
                        "module": module_path,
                        "methods": _public_methods(cls),
                    },
                    default=str,
                ),
                mime="application/json",
            )
    except Exception as exc:  # noqa: BLE001
        return _read_text(
            json.dumps({"status": "error", "class": class_name, "error": str(exc)}),
            mime="application/json",
        )
    return _read_text(
        json.dumps({"status": "class_not_found", "class": class_name}),
        mime="application/json",
    )


def _maya_project_current_producer(uri: str) -> Dict[str, Any]:  # noqa: ARG001 — single URI scheme
    """Producer for ``maya-project://current``.

    Returns ``{"workspace": <root>, "file_rules": [...]}`` describing
    the active Maya workspace.  Always JSON; unavailable outside Maya.
    """
    cmds = _maya_cmds()
    if cmds is None:
        return _read_text(
            json.dumps({"status": "maya_unavailable"}),
            mime="application/json",
        )
    try:
        root = cmds.workspace(q=True, rootDirectory=True)
    except Exception as exc:  # noqa: BLE001
        return _read_text(
            json.dumps({"status": "workspace_query_failed", "error": str(exc)}),
            mime="application/json",
        )
    try:
        rules = cmds.workspace(q=True, fileRule=True) or []
    except Exception:  # noqa: BLE001
        rules = []
    # Maya returns flat alternating ``[name, path, name, path, ...]``;
    # collapse to a list of pairs for agent ergonomics.
    pairs: List[Dict[str, str]] = []
    for i in range(0, len(rules) - 1, 2):
        pairs.append({"rule": str(rules[i]), "path": str(rules[i + 1])})
    return _read_text(
        json.dumps({"workspace": str(root or ""), "file_rules": pairs}),
        mime="application/json",
    )


def _public_methods(cls: Any) -> List[Dict[str, Any]]:
    """Return ``[{"name": ..., "doc_first_line": ...}]`` for a class.

    Best-effort: ``inspect.signature`` often raises on PyO3 / SWIG
    bindings, so we fall back to ``__doc__`` parsing when needed.
    """
    out: List[Dict[str, Any]] = []
    for name in sorted(dir(cls)):
        if name.startswith("_"):
            continue
        attr = getattr(cls, name, None)
        if not callable(attr):
            continue
        doc = (getattr(attr, "__doc__", "") or "").strip()
        first_line = doc.splitlines()[0] if doc else ""
        out.append({"name": name, "doc": first_line[:160]})
    return out


def _parse_path_uri(uri: str, *, scheme: str) -> Optional[List[str]]:
    """Strip *scheme* prefix and split the rest on ``/``.

    Returns ``None`` when the URI doesn't carry the expected scheme,
    otherwise the path components (empty parts skipped).
    """
    if not uri.startswith(scheme):
        return None
    tail = uri[len(scheme) :]
    return [p for p in tail.split("/") if p]


# ---------------------------------------------------------------------------
# Throttled scene-snapshot publisher
# ---------------------------------------------------------------------------


SnapshotProvider = Callable[[], Dict[str, Any]]
EventInstaller = Callable[[Callable[[], None], tuple], List[int]]
BusyChecker = Callable[[], bool]


def _default_event_installer(callback: Callable[[], None], events: tuple) -> List[int]:
    """Install a Maya scriptJob for each name in *events*.

    Returns the list of scriptJob ids (for cleanup).  Best-effort:
    unknown event names are silently skipped (older Maya versions),
    and a missing ``maya.cmds`` produces an empty list (headless mode).
    """
    cmds = _maya_cmds()
    if cmds is None:
        return []
    job_ids: List[int] = []
    for name in events:
        try:
            jid = cmds.scriptJob(event=[name, callback], protected=True)
        except Exception as exc:  # noqa: BLE001
            logger.debug("resources: scriptJob(%s) refused: %s", name, exc)
            continue
        try:
            job_ids.append(int(jid))
        except (TypeError, ValueError):
            continue
    return job_ids


def _default_event_remover(job_ids: List[int]) -> None:
    """Tear down the scriptJobs installed by :func:`_default_event_installer`."""
    cmds = _maya_cmds()
    if cmds is None:
        return
    for jid in job_ids:
        try:
            cmds.scriptJob(kill=jid, force=True)
        except Exception as exc:  # noqa: BLE001
            logger.debug("resources: scriptJob kill(%s) failed: %s", jid, exc)


# ---------------------------------------------------------------------------
# Maya-side binder
# ---------------------------------------------------------------------------


class MayaResourceBinder:
    """Compose every ``server._server.resources()`` call for Maya.

    Lifecycle::

        binder = MayaResourceBinder()
        binder.bind(server)             # registers producers + scene snapshot
        binder.install_scene_events()   # opt-in scriptJob hooks
        # ... server runs ...
        binder.unbind()                 # detach scriptJobs

    The binder defers every ``maya.cmds`` access to producer callbacks
    so importing this module from a plain Python interpreter (tests,
    ``mayapy`` without ``maya.standalone.initialize``) is free.
    """

    def __init__(
        self,
        *,
        snapshot_provider: Optional[SnapshotProvider] = None,
        event_installer: Optional[EventInstaller] = None,
        busy_checker: Optional[BusyChecker] = None,
        throttle_secs: float = DEFAULT_SCENE_THROTTLE_SECS,
        events: tuple = DEFAULT_SCENE_EVENTS,
    ) -> None:
        self.snapshot_provider: Optional[SnapshotProvider] = snapshot_provider
        self.event_installer: EventInstaller = event_installer or _default_event_installer
        self.busy_checker: Optional[BusyChecker] = busy_checker
        self.throttle_secs: float = max(0.0, float(throttle_secs))
        self.events: tuple = events

        # Populated by :meth:`bind` / :meth:`install_scene_events` so
        # tests can assert what we wired.
        self.bound_server: Any = None
        self.handle: Any = None
        self.registered_producers: List[str] = []
        self.session_event_uri: Optional[str] = None
        self.scene_event_ids: List[int] = []
        self.scene_publish_count: int = 0

        self._lock = threading.Lock()
        self._pending_publish: bool = False
        self._last_publish_at: float = 0.0
        self._publish_timer: Optional[threading.Timer] = None
        self._unbound: bool = False

    # ── Public API ──────────────────────────────────────────────────────

    def bind(self, server: Any) -> bool:
        """Bind the binder to *server*.

        Steps:
          1. Resolve ``server._server.resources()`` once and cache the
             handle on :attr:`handle`.
          2. Register the static set of producers (``maya-cmds://``,
             ``maya-api://``, ``maya-project://``).
          3. Publish an initial scene snapshot if a provider is wired.

        Calling :meth:`bind` twice is a no-op when the second call
        targets the same server.  Returns ``True`` when the handle was
        successfully obtained.
        """
        if self.bound_server is server:
            return True
        self.bound_server = server
        self._unbound = False

        try:
            self.handle = server._server.resources()
        except Exception as exc:  # noqa: BLE001
            logger.debug("resources: server.resources() unavailable: %s", exc)
            return False

        # Static producer registration --------------------------------
        self._register_producer(SCHEME_MAYA_CMDS, _maya_cmds_help_producer)
        self._register_producer(SCHEME_MAYA_API, _maya_api_signatures_producer)
        self._register_producer(SCHEME_MAYA_PROJECT, _maya_project_current_producer)
        self._register_session_event_buffer(server)

        # Initial scene snapshot --------------------------------------
        if self.snapshot_provider is not None:
            self._publish_scene_now()
        return True

    def install_scene_events(self) -> List[int]:
        """Hook scriptJob events so scene mutations republish ``scene://current``.

        Returns the list of scriptJob ids registered.  Calling this in
        a non-Maya environment returns ``[]`` and is otherwise a no-op
        — useful for tests that exercise the throttling logic without
        a live Maya.
        """
        if self.bound_server is None:
            return []
        if self.scene_event_ids:
            return list(self.scene_event_ids)
        ids = self.event_installer(self._on_scene_event, self.events)
        self.scene_event_ids = list(ids)
        return list(self.scene_event_ids)

    def unbind(self) -> None:
        """Detach scriptJobs and stop pending publishes.  Idempotent."""
        if self._unbound:
            return
        self._unbound = True

        with self._lock:
            timer = self._publish_timer
            self._publish_timer = None
            self._pending_publish = False
        if timer is not None:
            try:
                timer.cancel()
            except Exception:  # noqa: BLE001
                pass

        if self.scene_event_ids:
            try:
                _default_event_remover(self.scene_event_ids)
            except Exception as exc:  # noqa: BLE001
                logger.debug("resources: event remover raised: %s", exc)
            self.scene_event_ids = []

    # ── Public helpers used by tests / callers that own the snapshot ──

    def publish_scene(self, payload: Optional[Dict[str, Any]] = None) -> None:
        """Publish a scene snapshot now, bypassing throttling.

        When *payload* is ``None`` the bound :attr:`snapshot_provider`
        is invoked to compute one.  Used by tests and by callers that
        want to force a refresh after a scripted edit.
        """
        if self.handle is None:
            return
        if payload is None:
            if self.snapshot_provider is None:
                return
            try:
                payload = self.snapshot_provider()
            except Exception as exc:  # noqa: BLE001
                logger.debug("resources: snapshot provider raised: %s", exc)
                return
        try:
            self.handle.set_scene(payload)
            self.scene_publish_count += 1
            self._last_publish_at = time.monotonic()
        except Exception as exc:  # noqa: BLE001
            logger.debug("resources: set_scene raised: %s", exc)

    # ── Internals ───────────────────────────────────────────────────────

    def _register_producer(self, scheme: str, producer: Callable[[str], Dict[str, Any]]) -> None:
        """Register *producer* on *scheme*; track what we wired."""
        if self.handle is None:
            return
        try:
            self.handle.register_producer(scheme, producer)
        except Exception as exc:  # noqa: BLE001
            logger.debug("resources: register_producer(%s) raised: %s", scheme, exc)
            return
        self.registered_producers.append(scheme)

    def _register_session_event_buffer(self, server: Any) -> None:
        """Register maya-dev's bounded runtime event buffer when core supports it."""
        if self.handle is None:
            return
        try:
            from dcc_mcp_maya import _dev_session  # noqa: PLC0415

            instance_id = getattr(server, "instance_id", None) or "maya-dev"
            status = _dev_session.register_session_event_buffer(self.handle, instance_id=str(instance_id))
        except Exception as exc:  # noqa: BLE001
            logger.debug("resources: register_session_event_buffer raised: %s", exc)
            return
        uri = status.get("resource_uri") if isinstance(status, dict) else None
        if uri:
            self.session_event_uri = str(uri)

    def _is_executor_busy(self) -> bool:
        if self.busy_checker is None:
            return False
        try:
            return bool(self.busy_checker())
        except Exception as exc:  # noqa: BLE001
            logger.debug("resources: busy checker raised: %s", exc)
            return False

    def _on_scene_event(self) -> None:
        """ScriptJob callback: schedule a throttled scene republish.

        Maya fires ``DagObjectCreated`` per node, which can mean
        thousands of calls during a bulk import.  We collapse the
        storm into one publish per :attr:`throttle_secs` window using
        a trailing-edge timer.
        """
        if self._unbound or self._is_executor_busy():
            return
        with self._lock:
            now = time.monotonic()
            since = now - self._last_publish_at
            if since >= self.throttle_secs:
                # Lead-edge: publish immediately.
                schedule_now = True
                self._pending_publish = False
            else:
                # Trail-edge: defer until the throttle window closes.
                schedule_now = False
                if not self._pending_publish:
                    delay = self.throttle_secs - since
                    self._pending_publish = True
                    self._publish_timer = threading.Timer(delay, self._on_throttle_fire)
                    self._publish_timer.daemon = True
                    self._publish_timer.start()
        if schedule_now:
            self._publish_scene_now()

    def _on_throttle_fire(self) -> None:
        """Trailing-edge throttle handler — runs on a Timer thread."""
        if self._unbound or self._is_executor_busy():
            return
        with self._lock:
            self._pending_publish = False
            self._publish_timer = None
        self._publish_scene_now()

    def _publish_scene_now(self) -> None:
        """Resolve the current snapshot and publish via :meth:`publish_scene`."""
        self.publish_scene()
        self._sync_gateway_scene_metadata()

    def _sync_gateway_scene_metadata(self) -> None:
        """Push scene path / version into the gateway FileRegistry (admin SCENE column).

        MCP ``scene://current`` already refreshes on Maya scriptJob events, but
        the gateway registry row only updates when
        :meth:`~dcc_mcp_maya.server.MayaMcpServer.publish_capability_snapshot`
        runs.  Re-use the same throttled path so save / open / rename keep the
        admin UI and ``gateway://instances`` in sync.
        """
        server = self.bound_server
        if server is None:
            return
        publish = getattr(server, "publish_capability_snapshot", None)
        if publish is None:
            return
        try:
            publish(reason="scene_resource")
        except Exception as exc:  # noqa: BLE001
            logger.debug("resources: publish_capability_snapshot failed: %s", exc)


# ---------------------------------------------------------------------------
# Module-level convenience
# ---------------------------------------------------------------------------


def install_resources(
    server: Any,
    *,
    enabled: Optional[bool] = None,
    snapshot_provider: Optional[SnapshotProvider] = None,
    install_scene_events: bool = True,
    busy_checker: Optional[BusyChecker] = None,
    throttle_secs: float = DEFAULT_SCENE_THROTTLE_SECS,
) -> Optional[MayaResourceBinder]:
    """One-shot helper called from :meth:`MayaMcpServer.register_builtin_actions`.

    Returns the :class:`MayaResourceBinder` when installation succeeded,
    or ``None`` when:
      * resources were disabled (``DCC_MCP_MAYA_RESOURCES=0``);
      * the inner Rust ``McpHttpServer.resources()`` raised.

    Mirrors :func:`_project_tools.attach_to_server` so the call site in
    ``server.py`` is a one-liner that lives next to the existing
    project-tools call.
    """
    if not resolve_enabled(enabled):
        logger.debug("resources: disabled via env var")
        return None
    binder = MayaResourceBinder(
        snapshot_provider=snapshot_provider,
        busy_checker=busy_checker,
        throttle_secs=throttle_secs,
    )
    if not binder.bind(server):
        return None
    if install_scene_events:
        binder.install_scene_events()
    return binder
