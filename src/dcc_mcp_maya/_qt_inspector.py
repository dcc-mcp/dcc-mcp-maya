"""Adopt the shared core ``qt-ui-inspector`` skill in Maya (issue #307).

``dcc-mcp-core`` ships a DCC-agnostic, read-only Qt UI inspector
(``register_qt_ui_inspector``) exposing five tools — ``list_windows``,
``find_widgets``, ``describe_widget``, ``snapshot_tree``,
``wait_for_widget``. Maya is the first adapter to adopt it so agents can
locate custom shelves, dialogs, buttons, tree/table views, etc. **by text /
objectName / class / accessibleName** instead of generating ad-hoc PySide
enumeration scripts through ``execute_python``.

Two Maya-specific concerns are handled here:

* **Main-thread affinity.** ``QApplication.allWidgets()`` / ``topLevelWidgets()``
  must be read on Maya's UI thread. MCP tool handlers run on a tokio worker
  thread, so each inspector handler is wrapped to marshal onto Maya's main
  thread via the same single-writer pump ``execute_python`` uses
  (``maya.utils.executeInMainThreadWithResult``). In headless ``mayapy`` /
  pytest the wrapper runs inline.
* **Clear capability message.** The core tools already return structured
  ``qt-binding-unavailable`` / ``qt-no-application`` envelopes when Qt or a
  running ``QApplication`` is missing, so an unavailable inspector reports a
  readiness message instead of silently encouraging ad-hoc scripting.

Operator opt-out: ``DCC_MCP_MAYA_QT_UI_INSPECTOR=0``.
"""

from __future__ import annotations

import logging
import os
import threading
from typing import Any, Callable

logger = logging.getLogger(__name__)

#: Set to a falsey token to skip registering the Qt UI inspector tools.
ENV_QT_UI_INSPECTOR = "DCC_MCP_MAYA_QT_UI_INSPECTOR"

_TRUTHY = ("1", "true", "yes", "on")


def resolve_qt_ui_inspector_enabled(env: Any = None) -> bool:
    """Return ``True`` unless ``DCC_MCP_MAYA_QT_UI_INSPECTOR`` is falsey."""
    environ = env if env is not None else os.environ
    return str(environ.get(ENV_QT_UI_INSPECTOR, "1")).strip().lower() in _TRUTHY


def _marshal_to_main(fn: Callable[[], Any]) -> Any:
    """Run ``fn`` on Maya's main thread when a UI bridge is available.

    Mirrors ``execute_python``'s dispatch: inline when already on the main
    thread or when no Maya UI bridge exists (``mayapy`` / pytest), otherwise
    queued through the process-wide single-writer pump.
    """
    if threading.current_thread() is threading.main_thread():
        return fn()
    try:
        from dcc_mcp_maya import _main_thread_queue  # noqa: PLC0415

        utils = _main_thread_queue._import_maya_utils()  # noqa: SLF001
        if utils is None or not hasattr(utils, "executeInMainThreadWithResult"):
            return fn()
        return _main_thread_queue.get_queue().submit(fn).result()
    except Exception as exc:  # noqa: BLE001 — degrade to inline rather than fail the call
        logger.debug("[maya] qt inspector main-thread marshalling failed, running inline: %s", exc)
        return fn()


def _wrap_main_thread(handler: Callable[[Any], Any]) -> Callable[[Any], Any]:
    def wrapper(params: Any) -> Any:
        return _marshal_to_main(lambda: handler(params))

    return wrapper


class _MainThreadHandlerProxy:
    """Server proxy that wraps every registered handler in main-thread routing.

    ``register_qt_ui_inspector`` uses only ``server.registry`` and
    ``server.register_handler`` — both are forwarded; ``register_handler``
    additionally wraps the handler so the read happens on Maya's UI thread.
    """

    def __init__(self, server: Any) -> None:
        self._server = server

    @property
    def registry(self) -> Any:
        return self._server.registry

    def register_handler(self, name: str, handler: Callable[[Any], Any]) -> Any:
        return self._server.register_handler(name, _wrap_main_thread(handler))

    def __getattr__(self, item: str) -> Any:  # pragma: no cover - passthrough
        return getattr(self._server, item)


def register_maya_qt_ui_inspector(inner_server: Any, *, dcc_name: str = "maya") -> bool:
    """Register the shared ``qt_ui_inspector__*`` tools on the inner MCP server.

    Returns ``True`` when the core inspector was registered, ``False`` when
    disabled by env var or unavailable in the installed core.
    """
    if not resolve_qt_ui_inspector_enabled():
        logger.info("[%s] qt-ui-inspector disabled via %s", dcc_name, ENV_QT_UI_INSPECTOR)
        return False
    try:
        from dcc_mcp_core.skills.qt_ui_inspector import register_qt_ui_inspector  # noqa: PLC0415
    except Exception as exc:  # noqa: BLE001 — older core without the shared skill
        logger.info("[%s] qt-ui-inspector unavailable in installed dcc-mcp-core: %s", dcc_name, exc)
        return False
    try:
        register_qt_ui_inspector(_MainThreadHandlerProxy(inner_server), dcc_name=dcc_name)
    except Exception as exc:  # noqa: BLE001
        logger.warning("[%s] qt-ui-inspector registration failed: %s", dcc_name, exc)
        return False
    logger.info("[%s] qt-ui-inspector tools registered (main-thread routed)", dcc_name)
    return True
