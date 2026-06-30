"""Maya integration for ``dcc_mcp_core.register_project_tools`` (issue #576).

Wires the four project-persistence MCP/REST tools from ``dcc-mcp-core``:

* ``project_save``   — persist current Maya project state to ``.dcc-mcp/project.json``
* ``project_load``   — read an existing ``project.json`` back
* ``project_resume`` — return the rehydration payload an agent needs to
  restore scene, assets, active skills, tool groups and checkpoint IDs
* ``project_status`` — pure-read snapshot of the current state

Design notes (SOLID)
--------------------
* **Single Responsibility** — only orchestration: resolve the *current*
  Maya scene (so agents can call ``project_save`` with no arguments
  while inside Maya) and forward to ``register_project_tools``.
* **Open/Closed** — the scene resolver is injectable
  (:class:`MayaSceneResolver`).  Tests subclass it to fake a scene path
  without touching ``maya.cmds``.
* **Liskov** — the resolver returns ``str | None`` and never raises;
  callers always treat ``None`` as "no default project bound".
* **Interface Segregation** — :class:`ProjectToolsIntegration.bind`
  takes only the symbols it needs (``server`` for the registry, the
  resolver, an optional explicit ``DccProject``).
* **Dependency Inversion** — scene resolution is isolated behind
  :class:`MayaSceneResolver`, while core project persistence is used via
  its public ``register_project_tools`` contract.

Opt-out
-------
Set ``DCC_MCP_MAYA_PROJECT_TOOLS=0`` to skip registration.  Default is
**enabled** because the four tools are pure filesystem operations: they
never touch Maya state, never spawn subprocesses, and add ~640 B per
tool to ``tools/list`` (well under the budget guarded by
:func:`tests.test_affinity_http_roundtrip`).
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Callable, Optional

from dcc_mcp_core import DccProject, register_project_tools

logger = logging.getLogger(__name__)

#: Env var that disables project-tools registration.  ``"0"`` → disabled,
#: anything else (including unset) → enabled.
ENV_PROJECT_TOOLS = "DCC_MCP_MAYA_PROJECT_TOOLS"


# ---------------------------------------------------------------------------
# Scene resolution strategy
# ---------------------------------------------------------------------------


class MayaSceneResolver:
    """Resolve the *current* Maya scene path, if one is open.

    Returning ``None`` is a first-class signal — :func:`bind` then
    skips binding a default project so the four MCP tools require an
    explicit ``scene_path`` / ``project_dir`` argument from the caller.

    The default implementation calls ``cmds.file(query=True, sceneName=True)``
    inside a guarded import block so this module remains usable
    outside Maya (e.g. during unit tests, in ``mayapy`` batch mode
    where no scene is loaded yet, or during gateway-only deployments).
    """

    def current_scene(self) -> Optional[str]:
        """Return the absolute scene path, or ``None`` when unavailable."""
        try:
            import maya.cmds as cmds  # noqa: PLC0415
        except Exception:  # noqa: BLE001 — Maya unavailable
            return None
        try:
            scene = cmds.file(query=True, sceneName=True)
        except Exception as exc:  # noqa: BLE001 — Maya in odd state
            logger.debug("MayaSceneResolver: cmds.file() failed: %s", exc)
            return None
        scene = (scene or "").strip()
        return scene or None


def resolve_enabled(flag: Optional[bool] = None) -> bool:
    """Resolve whether project tools should be wired in.

    Priority: explicit ``flag`` argument > ``DCC_MCP_MAYA_PROJECT_TOOLS``
    env var (``"0"`` disables) > ``True``.
    """
    if flag is not None:
        return bool(flag)
    raw = os.environ.get(ENV_PROJECT_TOOLS)
    if raw is None:
        return True
    return raw.strip() != "0"


# ---------------------------------------------------------------------------
# Integration object
# ---------------------------------------------------------------------------


class ProjectToolsIntegration:
    """Bind ``register_project_tools`` against a :class:`MayaMcpServer`.

    The integration is a small object so callers can inspect what was
    bound (handy for tests and debug logging) without re-running the
    registration.

    Parameters
    ----------
    dcc_name:
        Tag passed to ``register_project_tools``; defaults to ``"maya"``.
    scene_resolver:
        Strategy used to discover the *current* Maya scene path.  When
        the resolver returns a string, a :class:`DccProject` rooted at
        that scene is bound as the default — argument-less calls then
        target the live Maya scene.  Pass a custom resolver in tests
        so we never have to import ``maya.cmds``.
    """

    def __init__(
        self,
        *,
        dcc_name: str = "maya",
        scene_resolver: Optional[MayaSceneResolver] = None,
    ) -> None:
        self.dcc_name = dcc_name
        self.scene_resolver = scene_resolver or MayaSceneResolver()
        # Populated by :meth:`bind` so tests can assert what we wired.
        self.bound_scene: Optional[str] = None
        self.bound_project: Any = None
        self.registered: bool = False

    # ── Public API ──────────────────────────────────────────────────────

    def bind(
        self,
        server: Any,
        *,
        project_factory: Optional[Callable[[str], Any]] = None,
        explicit_project: Any = None,
    ) -> bool:
        """Register the four project tools on *server*.

        Parameters
        ----------
        server:
            The :class:`MayaMcpServer`.  We forward ``server._server``
            (the inner Rust ``McpHttpServer``) because that is the
            object that exposes both ``registry`` and
            ``register_handler``.
        project_factory:
            Override the default :class:`DccProject` factory.  Tests
            inject a fake here to avoid touching the filesystem.
        explicit_project:
            Bind this :class:`DccProject` regardless of what the scene
            resolver returns.  Useful for callers that already manage
            their own project state.

        Returns
        -------
        bool
            ``True`` when the four tools were registered, ``False``
            when the inner server is unavailable or registration fails.
        """
        inner = self._inner_server(server)
        if inner is None:
            return False

        project = explicit_project
        if project is None:
            scene = self._safe_resolve_scene()
            if scene:
                factory = project_factory or DccProject.open
                try:
                    project = factory(scene)
                except Exception as exc:  # noqa: BLE001 — unwriteable dir, etc.
                    logger.debug(
                        "ProjectToolsIntegration.bind: DccProject.open(%s) failed: %s",
                        scene,
                        exc,
                    )
                    project = None

        try:
            register_project_tools(inner, dcc_name=self.dcc_name, project=project)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "ProjectToolsIntegration.bind: register_project_tools raised: %s",
                exc,
            )
            return False

        self.bound_scene = getattr(project, "state", None) and project.state.scene_path
        self.bound_project = project
        self.registered = True
        logger.info(
            "[%s] project tools registered (default scene=%s)",
            self.dcc_name,
            self.bound_scene or "<none>",
        )
        return True

    # ── Internals ───────────────────────────────────────────────────────

    @staticmethod
    def _inner_server(server: Any) -> Any:
        """Return the inner Rust ``McpHttpServer`` (or ``None``).

        ``register_project_tools`` calls ``server.registry`` *and*
        ``server.register_handler``.  On :class:`MayaMcpServer` only the
        inner ``_server`` exposes both — the wrapper proxies ``registry``
        but not ``register_handler``.  We never duck-type because
        accidentally targeting the wrong layer registers tools but
        leaves their handlers unwired (silent 404 at call time).
        """
        inner = getattr(server, "_server", None)
        if inner is None:
            return None
        if not hasattr(inner, "register_handler") or not hasattr(inner, "registry"):
            return None
        return inner

    def _safe_resolve_scene(self) -> Optional[str]:
        """Run the scene resolver, swallowing any unexpected error.

        We never let a misbehaving Maya scene break server startup;
        worst case is "no default project bound" and the agent must
        pass ``scene_path`` explicitly.
        """
        try:
            scene = self.scene_resolver.current_scene()
        except Exception as exc:  # noqa: BLE001
            logger.debug("ProjectToolsIntegration: scene resolver raised: %s", exc)
            return None
        if not scene:
            return None
        try:
            scene = str(Path(scene))
        except Exception:  # noqa: BLE001
            scene = str(scene)
        return scene


# ---------------------------------------------------------------------------
# Module-level convenience
# ---------------------------------------------------------------------------


def attach_to_server(
    server: Any,
    *,
    enabled: Optional[bool] = None,
    dcc_name: str = "maya",
    scene_resolver: Optional[MayaSceneResolver] = None,
    project_factory: Optional[Callable[[str], Any]] = None,
    explicit_project: Any = None,
) -> Optional[ProjectToolsIntegration]:
    """One-shot helper used by :class:`MayaMcpServer.register_builtin_actions`.

    Returns the :class:`ProjectToolsIntegration` instance when
    registration succeeded (``server`` now exposes the four tools), or
    ``None`` when env var disabled the surface or registration failed.
    """
    if not resolve_enabled(enabled):
        return None
    integration = ProjectToolsIntegration(
        dcc_name=dcc_name,
        scene_resolver=scene_resolver,
    )
    if integration.bind(
        server,
        project_factory=project_factory,
        explicit_project=explicit_project,
    ):
        return integration
    return None
