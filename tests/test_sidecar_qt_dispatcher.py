"""Regression tests for Maya's direct use of the core Qt dispatcher."""

from __future__ import annotations

import dcc_mcp_core.qt_dispatcher as core_qt_dispatcher


class _Signal:
    def connect(self, _handler):
        return None


class _FakeTcpServer:
    def __init__(self):
        self.newConnection = _Signal()
        self._port = 0
        self.closed = False

    def listen(self, _addr, port):
        self._port = 55123 if int(port) == 0 else int(port)
        return True

    def serverPort(self):
        return self._port

    def errorString(self):
        return "fake listen error"

    def hasPendingConnections(self):
        return False

    def close(self):
        self.closed = True


class _FakeTimer:
    def __init__(self):
        self.timeout = _Signal()
        self.running = False

    def start(self, _interval):
        self.running = True

    def stop(self):
        self.running = False


class _FakeQtCore:
    QTimer = _FakeTimer


class _FakeQtNetwork:
    QTcpServer = _FakeTcpServer
    QHostAddress = str


def test_core_qt_server_ping_dispatch_and_restart(monkeypatch):
    """Menu restart still works through the core singleton."""

    monkeypatch.setattr(core_qt_dispatcher, "_singleton", {"server": None})
    monkeypatch.setattr(
        core_qt_dispatcher,
        "_import_qt",
        lambda: (_FakeQtCore, _FakeQtNetwork, "fake-qt"),
    )

    first = core_qt_dispatcher.start_qt_server(
        port=0,
        dispatch_handler=lambda params: {"ok": True, "params": params},
    )
    assert first["port"] == 55123
    assert first["url"] == "qtserver://127.0.0.1:55123"
    assert first["reused"] is False

    assert first.server.registry.dispatch("ping", {}) == {
        "result": {"pong": True, "version": core_qt_dispatcher.DISPATCHER_VERSION},
    }
    assert first.server.registry.dispatch("dispatch", {"x": 1}) == {
        "result": {"ok": True, "params": {"x": 1}},
    }

    stopped = core_qt_dispatcher.stop_qt_server()
    assert stopped == {"stopped": True}
    assert core_qt_dispatcher._singleton["server"] is None

    second = core_qt_dispatcher.start_qt_server(port=0)
    try:
        assert second["port"] == 55123
        assert second["reused"] is False
    finally:
        core_qt_dispatcher.stop_qt_server()
