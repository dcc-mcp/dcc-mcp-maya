"""Controlled option-flow tests; no Maya, HTTP server, Host, or CUA task starts.

Published Core versions without the new options use a frozen API fixture only
for the opt-in boundary. The default path still exercises their real options.
"""

from __future__ import annotations

import builtins
import threading
from dataclasses import FrozenInstanceError, dataclass, replace
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from dcc_mcp_maya import server


@dataclass(frozen=True)
class ControlledRuntimeOptions:
    binary: str
    sha256: str
    runtime_version: str
    allowed_actions: tuple = ()
    window_operations: tuple = ("restore_activate",)
    ttl_minutes: int = 5
    recording: object = None


@pytest.fixture
def runtime_options(monkeypatch, tmp_path):
    import dcc_mcp_core.server as core_server

    options_type = getattr(core_server, "UiControlRuntimeOptions", ControlledRuntimeOptions)
    monkeypatch.setattr(core_server, "UiControlRuntimeOptions", options_type, raising=False)
    return options_type(
        binary=str(tmp_path / "dcc-cua.exe"),
        sha256="a" * 64,
        runtime_version="candidate-test-only",
        allowed_actions=(),
        window_operations=("restore_activate",),
        ttl_minutes=5,
    )


@pytest.fixture(autouse=True)
def isolated_singleton(monkeypatch):
    monkeypatch.setattr(server, "_instance_holder", [None])
    monkeypatch.setattr(server, "_server_instance", None)
    monkeypatch.setattr(server, "_bootstrap_ui_control", None)
    monkeypatch.setattr(server, "_startup_attempted", False)
    monkeypatch.setattr(server, "_auto_correct_pyexec", lambda: None)


@pytest.fixture
def controlled_start(monkeypatch):
    calls = []

    class ControlledServer:
        def __init__(self, **kwargs):
            calls.append(kwargs)
            self.is_running = False
            self._handle = object()

        def register_builtin_actions(self, **_kwargs):
            pass

        def start(self):
            self.is_running = True
            return self._handle

        def stop(self):
            self.is_running = False

    def controlled_factory(*, instance_holder, lock, server_class, **kwargs):
        with lock:
            if instance_holder[0] is None:
                instance_holder[0] = server_class(**kwargs)
            return instance_holder[0].start()

    monkeypatch.setattr(server, "MayaMcpServer", ControlledServer)
    monkeypatch.setattr(server, "create_dcc_server", controlled_factory)
    return calls


def test_default_options_do_not_import_or_forward_new_core_surface(monkeypatch):
    original_import = builtins.__import__
    original_from_env = server.DccServerOptions.from_env
    captured = {}

    def guarded_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "dcc_mcp_core.server" and "UiControlRuntimeOptions" in fromlist:
            raise AssertionError("default path imported the opt-in Core surface")
        return original_import(name, globals, locals, fromlist, level)

    def from_env(**kwargs):
        captured.update(kwargs)
        return original_from_env(**kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded_import)
    monkeypatch.setattr(server.DccServerOptions, "from_env", from_env)
    options = server.MayaServerOptions(port=0, gateway_port=0).to_core_options()

    assert options.dcc_name == "maya"
    assert "ui_control" not in captured


def test_adapter_options_forward_original_frozen_scope(monkeypatch, runtime_options):
    captured = {}

    def from_env(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(**kwargs)

    monkeypatch.setattr(server.DccServerOptions, "from_env", from_env)
    result = server.MayaServerOptions(ui_control=runtime_options).to_core_options()

    assert result.ui_control is runtime_options
    assert captured["ui_control"] is runtime_options
    assert runtime_options.allowed_actions == ()
    assert runtime_options.window_operations == ("restore_activate",)
    assert runtime_options.ttl_minutes == 5
    assert runtime_options.recording is None
    with pytest.raises(FrozenInstanceError):
        runtime_options.ttl_minutes = 60


def test_constructor_forwards_options_before_any_core_resource_creation(monkeypatch, runtime_options):
    captured = {}

    class OptionsCaptured(Exception):
        pass

    def from_env(**kwargs):
        return SimpleNamespace(**kwargs)

    def capture_core_init(_self, *, options):
        captured["options"] = options
        raise OptionsCaptured

    monkeypatch.setattr(server.DccServerOptions, "from_env", from_env)
    monkeypatch.setattr(server.DccServerBase, "__init__", capture_core_init)
    with pytest.raises(OptionsCaptured):
        server.MayaMcpServer(ui_control=runtime_options)
    assert captured["options"].ui_control is runtime_options


def test_rejects_untyped_runtime_before_core_options(monkeypatch):
    from_env = MagicMock()
    monkeypatch.setattr(server.DccServerOptions, "from_env", from_env)
    with pytest.raises((TypeError, server.BootstrapConfigurationError)):
        server.MayaServerOptions(ui_control={"approved": True}).to_core_options()
    from_env.assert_not_called()


def test_configuration_is_idempotent_before_start_but_rejects_conflict(runtime_options):
    server.configure_bootstrap(ui_control=runtime_options)
    server.configure_bootstrap(ui_control=replace(runtime_options))
    assert server._bootstrap_ui_control is runtime_options
    with pytest.raises(server.BootstrapConfigurationError, match="different"):
        server.configure_bootstrap(ui_control=replace(runtime_options, runtime_version="other"))


@pytest.mark.parametrize("register_builtins", [True, False])
def test_plugin_start_consumes_original_selection_once(runtime_options, controlled_start, register_builtins):
    server.configure_bootstrap(ui_control=runtime_options)
    first = server.start_server(register_builtins=register_builtins)
    second = server.start_server(register_builtins=register_builtins, ui_control=runtime_options)

    assert first is second
    assert len(controlled_start) == 1
    assert controlled_start[0]["ui_control"] is runtime_options
    with pytest.raises(server.BootstrapConfigurationError, match="before"):
        server.configure_bootstrap(ui_control=runtime_options)
    with pytest.raises(server.BootstrapConfigurationError, match="cannot change"):
        server.start_server(ui_control=replace(runtime_options, ttl_minutes=6))
    assert len(controlled_start) == 1


def test_direct_start_and_adapter_options_use_one_selection(runtime_options, controlled_start):
    supplied = server.MayaServerOptions(ui_control=runtime_options)
    server.start_server(options=supplied)
    assert controlled_start[0]["options"] is supplied
    assert "ui_control" not in controlled_start[0]


def test_configured_start_preserves_caller_options(runtime_options, controlled_start):
    supplied = server.MayaServerOptions(port=12345)
    server.configure_bootstrap(ui_control=runtime_options)
    server.start_server(options=supplied)
    forwarded = controlled_start[0]["options"]
    assert forwarded is not supplied
    assert forwarded.port == 12345
    assert forwarded.ui_control is runtime_options
    assert supplied.ui_control is None


def test_conflicting_direct_and_adapter_options_fail_before_construction(runtime_options, controlled_start):
    supplied = server.MayaServerOptions(ui_control=runtime_options)
    with pytest.raises(server.BootstrapConfigurationError, match="conflicts"):
        server.start_server(options=supplied, ui_control=replace(runtime_options, ttl_minutes=6))
    assert controlled_start == []


def test_default_start_then_stop_cannot_enable_new_runtime(runtime_options, controlled_start):
    server.start_server()
    assert "ui_control" not in controlled_start[0]
    server.stop_server()
    with pytest.raises(server.BootstrapConfigurationError):
        server.configure_bootstrap(ui_control=runtime_options)
    with pytest.raises(server.BootstrapConfigurationError):
        server.start_server(ui_control=runtime_options)
    assert len(controlled_start) == 1


def test_failed_constructor_latches_selection(monkeypatch, runtime_options):
    def fail(**_kwargs):
        raise RuntimeError("controlled constructor failure")

    monkeypatch.setattr(server, "MayaMcpServer", fail)
    with pytest.raises(RuntimeError, match="controlled constructor"):
        server.start_server(ui_control=runtime_options)
    with pytest.raises(server.BootstrapConfigurationError, match="before"):
        server.configure_bootstrap(ui_control=runtime_options)
    with pytest.raises(server.BootstrapConfigurationError, match="cannot change"):
        server.start_server(ui_control=replace(runtime_options, ttl_minutes=6))


def test_concurrent_configuration_has_one_immutable_winner(runtime_options):
    barrier = threading.Barrier(2)
    accepted = []
    rejected = []

    def configure(options):
        barrier.wait(timeout=5)
        try:
            server.configure_bootstrap(ui_control=options)
            accepted.append(options)
        except server.BootstrapConfigurationError as exc:
            rejected.append(exc)

    threads = [
        threading.Thread(target=configure, args=(runtime_options,)),
        threading.Thread(target=configure, args=(replace(runtime_options, ttl_minutes=6),)),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)
        assert not thread.is_alive()
    assert len(accepted) == len(rejected) == 1
    assert server._bootstrap_ui_control is accepted[0]


def test_configuration_racing_start_cannot_replace_attempted_selection(monkeypatch, runtime_options):
    constructing = threading.Event()
    release = threading.Event()
    failed = []

    def fail_constructor(**_kwargs):
        constructing.set()
        assert release.wait(timeout=5)
        raise RuntimeError("controlled constructor failure")

    def start():
        try:
            server.start_server(ui_control=runtime_options)
        except RuntimeError as exc:
            failed.append(exc)

    monkeypatch.setattr(server, "MayaMcpServer", fail_constructor)
    starter = threading.Thread(target=start)
    starter.start()
    assert constructing.wait(timeout=5)
    release.set()
    with pytest.raises(server.BootstrapConfigurationError, match="before"):
        server.configure_bootstrap(ui_control=replace(runtime_options, ttl_minutes=6))
    starter.join(timeout=5)
    assert not starter.is_alive()
    assert len(failed) == 1
    assert server._bootstrap_ui_control is runtime_options
