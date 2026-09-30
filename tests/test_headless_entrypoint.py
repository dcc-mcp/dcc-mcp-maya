"""Foreground serving lifecycle and official Mayapy CLI contracts."""

from __future__ import annotations

import json
import sys
import threading
from types import SimpleNamespace

import pytest

from dcc_mcp_maya import headless
from dcc_mcp_maya.__main__ import main
from dcc_mcp_maya.server import DccServerOptions, MayaServerOptions


@pytest.fixture
def stack(monkeypatch):
    events = []
    owner = threading.get_ident()
    dispatcher = object()

    class Host:
        def __init__(self, value):
            assert value is dispatcher

        def is_background(self):
            return True

        def run_headless(self, stop_event=None):
            assert threading.get_ident() == owner
            events.append(("pump", stop_event))

        def stop(self):
            events.append("host_stop")

    class Server:
        mcp_url = "http://127.0.0.1:18001/mcp"

        def __init__(self, **kwargs):
            assert kwargs["host_dispatcher"] is dispatcher
            events.append(("server", kwargs))

        def register_builtin_actions(self, **kwargs):
            events.append(("skills", kwargs))

        def start(self):
            events.append("start")

        def stop(self):
            events.append("server_stop")

    monkeypatch.setattr(headless, "BlockingDispatcher", lambda: dispatcher)
    monkeypatch.setattr(headless, "MayaHost", Host)
    monkeypatch.setattr(headless, "MayaMcpServer", Server)
    return events, Host, Server


def test_foreground_owns_dispatcher_and_cleans_up_after_pump(stack):
    events, _, _ = stack
    stop = threading.Event()
    headless.serve_headless(
        port=0, gateway_port=0, registry_dir="registry", extra_skill_paths=["skills"], stop_event=stop
    )
    assert events[0][1]["instance_type"] == "standalone"
    assert events[0][1]["registry_dir"] == "registry"
    assert events[1] == ("skills", {"extra_skill_paths": ["skills"]})
    assert events[2:] == ["start", ("pump", stop), "server_stop", "host_stop"]


@pytest.mark.parametrize("failure", ["start", "register_builtin_actions", "on_started"])
def test_startup_failure_stops_owned_server_and_dispatcher(stack, failure):
    events, _, server = stack

    def fail(*args, **kwargs):
        raise RuntimeError("startup failure")

    callback = fail if failure == "on_started" else None
    if callback is None:
        setattr(server, failure, fail)
    with pytest.raises(RuntimeError, match="startup failure"):
        headless.serve_headless(on_started=callback)
    assert events[-2:] == ["server_stop", "host_stop"]


def test_interactive_host_is_rejected_before_server_start(stack):
    events, host, _ = stack
    host.is_background = lambda self: False
    with pytest.raises(RuntimeError, match="batch Maya"):
        headless.serve_headless()
    assert events == ["host_stop"]


def test_host_cleanup_runs_even_if_server_shutdown_fails(stack):
    events, _, server = stack

    def fail(self):
        raise RuntimeError("shutdown failure")

    server.stop = fail
    with pytest.raises(RuntimeError, match="shutdown failure"):
        headless.serve_headless()
    assert events[-1] == "host_stop"


def test_off_main_thread_is_rejected(stack):
    errors = []

    def run():
        try:
            headless.serve_headless()
        except RuntimeError as exc:
            errors.append(str(exc))

    thread = threading.Thread(target=run)
    thread.start()
    thread.join(timeout=2)
    assert errors == ["serve_headless() must run on Mayapy's main thread"]
    assert stack[0] == []


def test_old_core_is_rejected_before_server_start(stack, monkeypatch):
    monkeypatch.setattr(headless, "core_version", "0.19.45")
    with pytest.raises(RuntimeError, match="dcc-mcp-core>=0.19.64"):
        headless.serve_headless()
    assert stack[0] == []


@pytest.mark.parametrize("instance_type", [None, "standalone"])
def test_instance_registration_preserves_older_gui_options(monkeypatch, instance_type):
    captured = {}
    sentinel = object()

    def from_env(**kwargs):
        captured.update(kwargs)
        if instance_type is None:
            assert "instance_type" not in kwargs
        return sentinel

    monkeypatch.setattr(DccServerOptions, "from_env", from_env)
    assert MayaServerOptions(instance_type=instance_type).to_core_options() is sentinel
    if instance_type is not None:
        assert captured["instance_type"] == instance_type


@pytest.mark.parametrize("failure", [None, KeyboardInterrupt, RuntimeError])
def test_cli_initializes_sdk_and_always_uninitializes(monkeypatch, capsys, failure):
    events = []
    standalone = SimpleNamespace(
        initialize=lambda **kwargs: events.append(("initialize", kwargs)),
        uninitialize=lambda: events.append("uninitialize"),
    )
    maya = SimpleNamespace(standalone=standalone)
    monkeypatch.setitem(sys.modules, "maya", maya)
    monkeypatch.setitem(sys.modules, "maya.standalone", standalone)

    def serve(**kwargs):
        events.append(("serve", kwargs))
        kwargs["on_started"](SimpleNamespace(mcp_url="http://127.0.0.1:18001/mcp"))
        if failure:
            raise failure("stopped")

    monkeypatch.setattr(headless, "serve_headless", serve)
    args = ["--port", "0", "--gateway-port", "0", "--skill-path", "first", "--skill-path", "second", "--json"]
    if failure is RuntimeError:
        with pytest.raises(RuntimeError, match="stopped"):
            main(args)
    else:
        assert main(args) == 0
    assert events[0] == ("initialize", {"name": "python"})
    assert events[1][1]["extra_skill_paths"] == ["first", "second"]
    assert events[-1] == "uninitialize"
    record = json.loads(capsys.readouterr().out)
    assert record["instance_type"] == "standalone"
    assert record["host_pid"] > 0
    assert record["mcp_url"] == "http://127.0.0.1:18001/mcp"


@pytest.mark.parametrize("value", ["-1", "65536", "invalid"])
def test_invalid_port_rejected_before_sdk_initialization(value):
    with pytest.raises(SystemExit) as error:
        main(["--port", value])
    assert error.value.code == 2
