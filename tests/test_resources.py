"""Unit tests for the Maya resource publisher (issue #187).

Covers:

* Pure producer functions (``maya-cmds://help`` / ``maya-cmds://flags`` /
  ``maya-api://signatures`` / ``maya-project://current``) — verified
  in headless mode where ``maya.cmds`` is intentionally absent so the
  graceful-degradation envelopes are exercised.
* :class:`MayaResourceBinder.bind` — confirms producers are registered
  on the inner Rust :class:`ResourceHandle` exactly once and the
  initial scene snapshot is published.
* Trailing-edge throttling — a burst of scene events collapses to two
  ``set_scene`` calls (lead-edge + trail-edge), proving the
  ``DagObjectCreated`` storm protection works without a live event
  loop.
* End-to-end integration with a real :class:`MayaMcpServer` — the
  scene URI flips from the ``no_scene_published`` placeholder to the
  Maya snapshot, and the three producers appear in ``resources/list``.
"""

from __future__ import annotations

import json
import sys
import time
from typing import Any, Callable, Dict, List
from unittest.mock import MagicMock

import pytest

from dcc_mcp_maya import (
    DEFAULT_SCENE_EVENTS,
    DEFAULT_SCENE_THROTTLE_SECS,
    ENV_RESOURCES,
    SCHEME_MAYA_API,
    SCHEME_MAYA_CMDS,
    SCHEME_MAYA_PROJECT,
    MayaResourceBinder,
    install_resources,
)
from dcc_mcp_maya._resources import (
    _maya_api_signatures_producer,
    _maya_cmds_help_producer,
    _maya_project_current_producer,
    _parse_path_uri,
    resolve_enabled,
)

# ---------------------------------------------------------------------------
# resolve_enabled
# ---------------------------------------------------------------------------


class TestResolveEnabled:
    def test_default_is_enabled(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv(ENV_RESOURCES, raising=False)
        assert resolve_enabled() is True

    def test_zero_disables(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv(ENV_RESOURCES, "0")
        assert resolve_enabled() is False

    def test_explicit_argument_wins(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv(ENV_RESOURCES, "0")
        assert resolve_enabled(True) is True
        monkeypatch.delenv(ENV_RESOURCES)
        assert resolve_enabled(False) is False

    def test_empty_string_acts_like_unset(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv(ENV_RESOURCES, "")
        # Empty string is not exactly "0", so we treat it as "set but
        # leave default" → stays enabled.
        assert resolve_enabled() is True


# ---------------------------------------------------------------------------
# _parse_path_uri
# ---------------------------------------------------------------------------


class TestParsePathUri:
    def test_strips_scheme_and_splits(self) -> None:
        assert _parse_path_uri("maya-cmds://help/ls", scheme=SCHEME_MAYA_CMDS) == ["help", "ls"]

    def test_returns_none_when_scheme_mismatches(self) -> None:
        assert _parse_path_uri("scene://current", scheme=SCHEME_MAYA_CMDS) is None

    def test_collapses_trailing_slashes(self) -> None:
        assert _parse_path_uri("maya-cmds://help/", scheme=SCHEME_MAYA_CMDS) == ["help"]
        assert _parse_path_uri("maya-cmds://", scheme=SCHEME_MAYA_CMDS) == []


# ---------------------------------------------------------------------------
# Producers — graceful degradation when maya.cmds is unavailable
# ---------------------------------------------------------------------------


class TestProducersWithoutMaya:
    """Outside Maya every producer must return a JSON envelope, never raise."""

    @pytest.fixture(autouse=True)
    def _hide_maya_modules(self, monkeypatch: Any) -> None:
        # These tests assert the non-Maya degradation path.  In mayapy CI,
        # the real Maya modules are importable, so block just the producer
        # imports explicitly instead of depending on the ambient interpreter.
        monkeypatch.setitem(sys.modules, "maya.cmds", None)
        monkeypatch.setitem(sys.modules, "maya.api.OpenMaya", None)

    def test_cmds_help_returns_unavailable_envelope(self) -> None:
        out = _maya_cmds_help_producer("maya-cmds://help/ls")
        assert out["mimeType"] == "application/json"
        body = json.loads(out["text"])
        assert body["status"] == "maya_unavailable"
        assert body["uri"] == "maya-cmds://help/ls"

    def test_cmds_flags_returns_unavailable_envelope(self) -> None:
        out = _maya_cmds_help_producer("maya-cmds://flags/polySphere")
        body = json.loads(out["text"])
        assert body["status"] == "maya_unavailable"
        assert body["command"] == "polySphere"

    def test_cmds_help_invalid_uri(self) -> None:
        out = _maya_cmds_help_producer("maya-cmds://")
        body = json.loads(out["text"])
        # Empty path → invalid_uri
        assert body["status"] == "invalid_uri"

    def test_cmds_help_missing_command(self) -> None:
        # ``maya-cmds://help`` with no command — degrade with a hint.
        # Note: outside Maya this hits maya_unavailable first, but with
        # mocked maya.cmds we'd hit missing_command.  Verify the hint
        # path by injecting a minimal stub.
        from unittest.mock import MagicMock

        cmds_mock = MagicMock()
        # If called, would explode the test — but missing_command is
        # checked before any cmds invocation.
        cmds_mock.help = MagicMock(side_effect=AssertionError("should not be called"))

        with _patched_maya_cmds(cmds_mock):
            out = _maya_cmds_help_producer("maya-cmds://help")
        body = json.loads(out["text"])
        assert body["status"] == "missing_command"

    def test_api_signatures_returns_unavailable_envelope(self) -> None:
        out = _maya_api_signatures_producer("maya-api://signatures/MFnMesh")
        body = json.loads(out["text"])
        # No maya.api package outside Maya — class_not_found is the
        # documented end state.
        assert body["status"] in {"class_not_found", "maya_unavailable", "error"}

    def test_api_signatures_invalid_uri(self) -> None:
        out = _maya_api_signatures_producer("maya-api://wrong/path")
        body = json.loads(out["text"])
        assert body["status"] == "invalid_uri"

    def test_project_current_returns_unavailable_envelope(self) -> None:
        out = _maya_project_current_producer("maya-project://current")
        body = json.loads(out["text"])
        assert body["status"] == "maya_unavailable"


# ---------------------------------------------------------------------------
# Producers — happy path with mocked maya.cmds
# ---------------------------------------------------------------------------


class _PatchedMayaCmds:
    """Context manager that injects a mock ``maya.cmds`` into ``sys.modules``."""

    def __init__(self, mock: Any) -> None:
        self.mock = mock
        self._saved_maya: Any = None
        self._saved_cmds: Any = None

    def __enter__(self):
        import sys

        self._saved_maya = sys.modules.get("maya")
        self._saved_cmds = sys.modules.get("maya.cmds")
        sys.modules["maya"] = MagicMock(cmds=self.mock)
        sys.modules["maya.cmds"] = self.mock
        return self.mock

    def __exit__(self, exc_type, exc, tb):
        import sys

        if self._saved_maya is None:
            sys.modules.pop("maya", None)
        else:
            sys.modules["maya"] = self._saved_maya
        if self._saved_cmds is None:
            sys.modules.pop("maya.cmds", None)
        else:
            sys.modules["maya.cmds"] = self._saved_cmds


def _patched_maya_cmds(mock: Any) -> _PatchedMayaCmds:
    return _PatchedMayaCmds(mock)


class TestProducersWithMockedMaya:
    """When ``maya.cmds`` is mocked we should hit the real code path."""

    def test_cmds_help_returns_help_text(self) -> None:
        cmds_mock = MagicMock()
        cmds_mock.help.return_value = "polySphere flags: -r/-radius float ..."

        with _patched_maya_cmds(cmds_mock):
            out = _maya_cmds_help_producer("maya-cmds://help/polySphere")

        assert out["mimeType"] == "text/plain"
        assert "polySphere flags" in out["text"]
        cmds_mock.help.assert_called_once_with("polySphere", language="python")

    def test_cmds_flags_returns_flag_dict(self) -> None:
        cmds_mock = MagicMock()
        cmds_mock.help.return_value = ["-r/-radius", "-h/-help"]

        with _patched_maya_cmds(cmds_mock):
            out = _maya_cmds_help_producer("maya-cmds://flags/polySphere")

        body = json.loads(out["text"])
        assert body["command"] == "polySphere"
        assert body["flags"] == ["-r/-radius", "-h/-help"]
        cmds_mock.help.assert_called_once_with("polySphere", flags=True)

    def test_cmds_help_command_not_found(self) -> None:
        cmds_mock = MagicMock()
        cmds_mock.help.side_effect = RuntimeError("Unknown command")

        with _patched_maya_cmds(cmds_mock):
            out = _maya_cmds_help_producer("maya-cmds://help/totallyMadeUpCmd")

        body = json.loads(out["text"])
        assert body["status"] == "command_not_found"
        assert body["command"] == "totallyMadeUpCmd"

    def test_project_current_returns_workspace_and_rules(self) -> None:
        cmds_mock = MagicMock()

        def _workspace_dispatch(*_args: Any, **kwargs: Any) -> Any:
            if kwargs.get("rootDirectory"):
                return "/projects/foo"
            if kwargs.get("fileRule"):
                return ["scene", "scenes", "image", "images"]
            return None

        cmds_mock.workspace.side_effect = _workspace_dispatch

        with _patched_maya_cmds(cmds_mock):
            out = _maya_project_current_producer("maya-project://current")

        body = json.loads(out["text"])
        assert body["workspace"] == "/projects/foo"
        assert body["file_rules"] == [
            {"rule": "scene", "path": "scenes"},
            {"rule": "image", "path": "images"},
        ]


# ---------------------------------------------------------------------------
# MayaResourceBinder — bind / unbind / throttling
# ---------------------------------------------------------------------------


class _RecordingResourceHandle:
    """Minimal stand-in for the Rust ``ResourceHandle``."""

    def __init__(self) -> None:
        self.scenes: List[Any] = []
        self.producers: Dict[str, Callable[[str], Dict[str, Any]]] = {}
        self.notifications: List[str] = []

    def set_scene(self, value: Any) -> None:
        self.scenes.append(value)

    def register_producer(self, scheme_or_uri: str, callable_: Callable[[str], Dict[str, Any]]) -> None:
        self.producers[scheme_or_uri] = callable_

    def notify_updated(self, uri: str) -> None:
        self.notifications.append(uri)


class _FakeServer:
    """Stand-in for :class:`MayaMcpServer` exposing only ``_server.resources()``."""

    def __init__(self) -> None:
        self.resource_handle = _RecordingResourceHandle()
        inner = MagicMock()
        inner.resources.return_value = self.resource_handle
        self._server = inner


class TestMayaResourceBinderBind:
    def test_bind_publishes_initial_snapshot_and_registers_producers(self) -> None:
        server = _FakeServer()
        snapshots: List[Dict[str, Any]] = []

        def provider() -> Dict[str, Any]:
            snap = {"dcc": "maya", "scene": f"snap-{len(snapshots)}"}
            snapshots.append(snap)
            return snap

        binder = MayaResourceBinder(snapshot_provider=provider)
        assert binder.bind(server) is True
        assert binder.handle is server.resource_handle
        assert binder.scene_publish_count == 1
        assert server.resource_handle.scenes == [{"dcc": "maya", "scene": "snap-0"}]
        assert sorted(binder.registered_producers) == sorted(
            [
                SCHEME_MAYA_CMDS,
                SCHEME_MAYA_API,
                SCHEME_MAYA_PROJECT,
            ]
        )
        assert sorted(server.resource_handle.producers.keys()) == sorted(
            [
                SCHEME_MAYA_CMDS,
                SCHEME_MAYA_API,
                SCHEME_MAYA_PROJECT,
            ]
        )

    def test_bind_without_snapshot_provider_skips_initial_publish(self) -> None:
        server = _FakeServer()
        binder = MayaResourceBinder()
        assert binder.bind(server) is True
        assert binder.scene_publish_count == 0
        assert server.resource_handle.scenes == []

    def test_bind_is_idempotent(self) -> None:
        server = _FakeServer()
        binder = MayaResourceBinder(snapshot_provider=lambda: {"k": "v"})
        binder.bind(server)
        binder.bind(server)  # second call must be a no-op
        # Producers registered exactly once each.
        assert len(server.resource_handle.producers) == 3
        # Scene published exactly once.
        assert binder.scene_publish_count == 1

    def test_bind_returns_false_when_resources_unavailable(self) -> None:
        server = MagicMock()
        server._server.resources.side_effect = RuntimeError("not enabled")
        binder = MayaResourceBinder()
        assert binder.bind(server) is False
        assert binder.handle is None

    def test_install_scene_events_uses_injected_installer(self) -> None:
        server = _FakeServer()
        installed_events: List[str] = []

        def installer(callback: Callable[[], None], events: tuple) -> List[int]:
            installed_events.extend(events)
            return [101, 102, 103]

        binder = MayaResourceBinder(event_installer=installer)
        binder.bind(server)
        ids = binder.install_scene_events()
        assert ids == [101, 102, 103]
        assert binder.scene_event_ids == [101, 102, 103]
        # All default events offered to the installer.
        for ev in DEFAULT_SCENE_EVENTS:
            assert ev in installed_events

    def test_unbind_is_idempotent_and_clears_state(self) -> None:
        server = _FakeServer()
        binder = MayaResourceBinder(event_installer=lambda cb, evs: [1, 2])
        binder.bind(server)
        binder.install_scene_events()
        binder.unbind()
        binder.unbind()  # idempotent
        assert binder.scene_event_ids == []


# ---------------------------------------------------------------------------
# Throttling — burst protection for DagObjectCreated
# ---------------------------------------------------------------------------


class TestThrottling:
    """A burst of scene events collapses to two publishes (lead + trail)."""

    def test_event_after_throttle_window_publishes_immediately(self) -> None:
        """Lead-edge: an event arriving outside the throttle window publishes synchronously."""
        server = _FakeServer()
        binder = MayaResourceBinder(
            snapshot_provider=lambda: {"event": "tick"},
            throttle_secs=0.05,
        )
        binder.bind(server)
        baseline = binder.scene_publish_count

        # Wait past the throttle window so the next event takes the
        # lead-edge path.
        time.sleep(0.1)
        binder._on_scene_event()  # type: ignore[attr-defined]
        assert binder.scene_publish_count == baseline + 1

    def test_burst_collapses_to_one_trailing_publish(self) -> None:
        """A burst within the throttle window collapses to a single trail-edge publish."""
        server = _FakeServer()
        binder = MayaResourceBinder(
            snapshot_provider=lambda: {"event": "tick"},
            throttle_secs=0.05,
        )
        binder.bind(server)
        baseline = binder.scene_publish_count  # bind() already published

        # Fire 50 events tightly — all land within the throttle window
        # opened by the bind() publish, so they go to trail-edge.
        for _ in range(50):
            binder._on_scene_event()  # type: ignore[attr-defined]

        # No synchronous publish — the throttle window is still open.
        assert binder.scene_publish_count == baseline
        # Wait for the trail-edge timer to fire.
        time.sleep(0.2)
        # Exactly one trailing publish, regardless of burst size.
        assert binder.scene_publish_count == baseline + 1

        binder.unbind()

    def test_lead_then_burst_then_trail(self) -> None:
        """Full lead+trail dance: first event past window leads, burst trails."""
        server = _FakeServer()
        binder = MayaResourceBinder(
            snapshot_provider=lambda: {"event": "tick"},
            throttle_secs=0.05,
        )
        binder.bind(server)
        time.sleep(0.1)  # clear throttle window from bind()
        baseline = binder.scene_publish_count

        # Lead-edge fires immediately.
        binder._on_scene_event()  # type: ignore[attr-defined]
        assert binder.scene_publish_count == baseline + 1

        # Subsequent burst within the window goes to trail-edge.
        for _ in range(20):
            binder._on_scene_event()  # type: ignore[attr-defined]
        assert binder.scene_publish_count == baseline + 1
        time.sleep(0.2)
        assert binder.scene_publish_count == baseline + 2

        binder.unbind()

    def test_publish_scene_explicit_payload_bypasses_provider(self) -> None:
        server = _FakeServer()
        provider_calls: List[int] = []

        def provider() -> Dict[str, Any]:
            provider_calls.append(1)
            return {"called": True}

        binder = MayaResourceBinder(snapshot_provider=provider)
        binder.bind(server)
        provider_calls.clear()  # bind() consumed the initial snapshot

        binder.publish_scene({"explicit": True})
        assert provider_calls == []
        assert server.resource_handle.scenes[-1] == {"explicit": True}

    def test_unbind_cancels_pending_throttle_timer(self) -> None:
        server = _FakeServer()
        binder = MayaResourceBinder(
            snapshot_provider=lambda: {"event": "tick"},
            throttle_secs=0.5,
        )
        binder.bind(server)
        baseline = binder.scene_publish_count

        # First event within bind's window → trail-edge timer scheduled.
        binder._on_scene_event()  # type: ignore[attr-defined]
        assert binder._pending_publish is True  # type: ignore[attr-defined]
        assert binder.scene_publish_count == baseline  # not yet published

        # Unbind before the trail-edge fires.
        binder.unbind()
        time.sleep(0.7)  # past the throttle window
        # Timer must have been cancelled, so no extra publish.
        assert binder.scene_publish_count == baseline

    def test_scene_events_drop_while_executor_busy(self) -> None:
        server = _FakeServer()
        busy = {"value": True}
        binder = MayaResourceBinder(
            snapshot_provider=lambda: {"event": "tick"},
            busy_checker=lambda: busy["value"],
            throttle_secs=0.0,
        )
        binder.bind(server)
        baseline = binder.scene_publish_count

        binder._on_scene_event()  # type: ignore[attr-defined]
        assert binder.scene_publish_count == baseline

        busy["value"] = False
        binder._on_scene_event()  # type: ignore[attr-defined]
        assert binder.scene_publish_count == baseline + 1


# ---------------------------------------------------------------------------
# install_resources — module-level convenience
# ---------------------------------------------------------------------------


class TestInstallResources:
    def test_returns_none_when_disabled_via_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv(ENV_RESOURCES, "0")
        server = _FakeServer()
        assert install_resources(server) is None

    def test_returns_binder_with_producers_wired(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv(ENV_RESOURCES, raising=False)
        server = _FakeServer()
        binder = install_resources(
            server,
            snapshot_provider=lambda: {"dcc": "maya"},
            install_scene_events=False,  # avoid scriptJob path in tests
        )
        assert binder is not None
        assert binder.handle is server.resource_handle
        assert binder.scene_publish_count == 1


# ---------------------------------------------------------------------------
# End-to-end with a real MayaMcpServer
# ---------------------------------------------------------------------------


class TestMayaMcpServerResourcesIntegration:
    """Full server lifecycle — confirm the binder is wired and producers route."""

    def test_register_builtin_actions_creates_binder(self) -> None:
        from dcc_mcp_maya import MayaMcpServer

        server = MayaMcpServer(port=0, enable_gateway_failover=False, gateway_port=0)
        try:
            server.register_builtin_actions(minimal=True)
            assert server._resources is not None
            assert server._resources.handle is not None
            assert sorted(server._resources.registered_producers) == sorted(
                [
                    SCHEME_MAYA_CMDS,
                    SCHEME_MAYA_API,
                    SCHEME_MAYA_PROJECT,
                ]
            )
            assert server._resources.scene_publish_count == 1
        finally:
            try:
                server.stop()
            except Exception:  # noqa: BLE001
                pass

    def test_env_var_disables_binder(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from dcc_mcp_maya import MayaMcpServer

        monkeypatch.setenv(ENV_RESOURCES, "0")
        server = MayaMcpServer(port=0, enable_gateway_failover=False, gateway_port=0)
        try:
            server.register_builtin_actions(minimal=True)
            assert server._resources is None
        finally:
            try:
                server.stop()
            except Exception:  # noqa: BLE001
                pass

    def test_stop_unbinds_resources(self) -> None:
        from dcc_mcp_maya import MayaMcpServer

        server = MayaMcpServer(port=0, enable_gateway_failover=False, gateway_port=0)
        server.register_builtin_actions(minimal=True)
        binder = server._resources
        assert binder is not None
        # Sanity: scene events were not installed (no maya.cmds), so
        # scene_event_ids is empty — but unbind should still clear
        # internal state.
        server.stop()
        # After stop, _unbound is set; further publishes should be no-ops.
        baseline = binder.scene_publish_count
        binder._on_scene_event()  # type: ignore[attr-defined]
        assert binder.scene_publish_count == baseline


# ---------------------------------------------------------------------------
# Default constants exposed for other modules / docs
# ---------------------------------------------------------------------------


class TestModuleExports:
    def test_default_throttle_is_positive(self) -> None:
        assert DEFAULT_SCENE_THROTTLE_SECS > 0

    def test_default_events_includes_core_scene_events(self) -> None:
        assert "SceneOpened" in DEFAULT_SCENE_EVENTS
        assert "SceneSaved" in DEFAULT_SCENE_EVENTS
        assert "DagObjectCreated" in DEFAULT_SCENE_EVENTS
