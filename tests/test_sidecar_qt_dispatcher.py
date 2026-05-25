"""Regression tests for the vendored in-Maya Qt dispatcher."""

from __future__ import annotations

from dcc_mcp_maya.sidecar import _qt_dispatcher


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


def test_stop_qt_server_preserves_singleton_key_for_restart(monkeypatch):
    """Menu restart calls start -> stop -> start; singleton state must survive."""

    monkeypatch.setattr(_qt_dispatcher, "_singleton", {"server": None})
    monkeypatch.setattr(
        _qt_dispatcher,
        "_import_qt",
        lambda: (_FakeQtCore, _FakeQtNetwork, "fake-qt"),
    )

    first = _qt_dispatcher.start_qt_server(port=0)
    assert first["port"] == 55123
    assert first["reused"] is False

    stopped = _qt_dispatcher.stop_qt_server()
    assert stopped == {"stopped": True}
    assert _qt_dispatcher._singleton["server"] is None

    second = _qt_dispatcher.start_qt_server(port=0)
    try:
        assert second["port"] == 55123
        assert second["reused"] is False
    finally:
        _qt_dispatcher.stop_qt_server()
