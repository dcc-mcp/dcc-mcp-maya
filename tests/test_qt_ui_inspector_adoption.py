"""Issue #307 — Maya adopts the shared core qt-ui-inspector skill.

Verifies the adapter registers the five read-only ``qt_ui_inspector__*``
tools on the inner MCP server, wraps each handler in Maya main-thread
routing, and surfaces a clear capability envelope when no QApplication is
running (the pytest case) instead of crashing or encouraging ad-hoc scripts.

No live Maya / QApplication needed — a fake inner server captures the
registrations.
"""

from __future__ import annotations

import threading
from typing import Any, Callable, Dict, List

import pytest

from dcc_mcp_maya import _qt_inspector

_HAS_INSPECTOR = True
try:  # pragma: no cover - import guard
    from dcc_mcp_core.skills.qt_ui_inspector import register_qt_ui_inspector  # noqa: F401
except Exception:  # noqa: BLE001
    _HAS_INSPECTOR = False

pytestmark = pytest.mark.skipif(not _HAS_INSPECTOR, reason="installed dcc-mcp-core lacks qt-ui-inspector")

_EXPECTED_TOOLS = {
    "qt_ui_inspector__list_windows",
    "qt_ui_inspector__find_widgets",
    "qt_ui_inspector__describe_widget",
    "qt_ui_inspector__snapshot_tree",
    "qt_ui_inspector__wait_for_widget",
}


class _FakeRegistry:
    def __init__(self) -> None:
        self.registered: List[str] = []

    def register(self, *, name: str, **_kwargs: Any) -> None:
        self.registered.append(name)


class _FakeServer:
    def __init__(self) -> None:
        self.registry = _FakeRegistry()
        self.handlers: Dict[str, Callable[[Any], Any]] = {}

    def register_handler(self, name: str, handler: Callable[[Any], Any]) -> None:
        self.handlers[name] = handler


class TestRegistration:
    def test_registers_all_five_tools(self):
        server = _FakeServer()
        assert _qt_inspector.register_maya_qt_ui_inspector(server, dcc_name="maya") is True
        assert _EXPECTED_TOOLS <= set(server.registry.registered)
        assert _EXPECTED_TOOLS <= set(server.handlers)

    def test_env_opt_out_skips_registration(self, monkeypatch):
        monkeypatch.setenv(_qt_inspector.ENV_QT_UI_INSPECTOR, "0")
        server = _FakeServer()
        assert _qt_inspector.register_maya_qt_ui_inspector(server, dcc_name="maya") is False
        assert server.registry.registered == []

    def test_handlers_return_structured_result_never_raise(self):
        """The inspector must always return a structured dict — a clear
        capability envelope when Qt/QApplication is missing, a normal result
        otherwise — never raise into the host."""
        server = _FakeServer()
        _qt_inspector.register_maya_qt_ui_inspector(server, dcc_name="maya")
        out = server.handlers["qt_ui_inspector__list_windows"]({})
        assert isinstance(out, dict)
        assert "success" in out


class TestMainThreadRouting:
    def test_handler_runs_through_marshal(self, monkeypatch):
        """The registered handler must funnel through ``_marshal_to_main``."""
        server = _FakeServer()
        _qt_inspector.register_maya_qt_ui_inspector(server, dcc_name="maya")

        seen: List[bool] = []
        real = _qt_inspector._marshal_to_main

        def _spy(fn):
            seen.append(True)
            return real(fn)

        monkeypatch.setattr(_qt_inspector, "_marshal_to_main", _spy)
        server.handlers["qt_ui_inspector__find_widgets"]({"object_name": "x"})
        assert seen == [True]

    def test_marshal_runs_inline_on_main_thread(self):
        assert threading.current_thread() is threading.main_thread()
        assert _qt_inspector._marshal_to_main(lambda: 41 + 1) == 42

    def test_marshal_runs_inline_without_maya_bridge(self, monkeypatch):
        """Off the main thread but no Maya UI bridge → run inline (mayapy/pytest)."""
        from dcc_mcp_maya import _main_thread_queue

        monkeypatch.setattr(_main_thread_queue, "_import_maya_utils", lambda: None)
        result: List[Any] = []

        def _worker():
            result.append(_qt_inspector._marshal_to_main(lambda: "ran"))

        t = threading.Thread(target=_worker)
        t.start()
        t.join(timeout=5.0)
        assert result == ["ran"]
