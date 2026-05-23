"""Unit + HTTP round-trip coverage for ``dcc_mcp_maya._project_tools``.

These tests exercise three concentric rings:

1. **Unit ring** — pure logic of :class:`ProjectToolsIntegration`,
   :class:`MayaSceneResolver`, env-var resolution, defensive paths.
2. **MCP ring** — start a real :class:`MayaMcpServer`, hit it over HTTP,
   prove ``project_save`` / ``project_load`` / ``project_resume`` /
   ``project_status`` round-trip correctly.
3. **REST ring** — when core mounts ``/v1/tools/call`` (issue #165),
   the same four tools must be reachable via the gateway-friendly
   REST channel as well.

Token-budget guard: ``tools/list`` must report each ``project_*`` tool
in **<= 800 B** of serialised JSON.  The point of these tools is that
they are cheap to expose; if the upstream description ever grows
silently we want CI to catch it before agents start paying for the
extra tokens on every discovery turn.
"""

from __future__ import annotations

import json
import os
import re
import socket
import tempfile
import unittest
import urllib.error
import urllib.request
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import pytest

import dcc_mcp_maya
from dcc_mcp_maya import (
    MayaMcpServer,
    MayaSceneResolver,
    ProjectToolsIntegration,
    attach_project_tools,
)
from dcc_mcp_maya._project_tools import ENV_PROJECT_TOOLS, resolve_enabled

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

_MCP_HEADERS = {
    "Accept": "application/json, text/event-stream",
    "Content-Type": "application/json",
}
_CLAUDE_TOOL_NAME_RE = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")
_PROJECT_TOOL_NAMES = {"project_save", "project_load", "project_resume", "project_status"}


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _post_json(url: str, payload: Dict[str, Any], timeout: float = 10.0) -> Tuple[int, Dict[str, Any]]:
    """POST JSON to *url* and return ``(status, parsed_body)``.

    Handles MCP's ``text/event-stream`` framing: when the response is
    SSE we extract the last ``data:`` line and parse its body as JSON,
    matching the behaviour of the existing ``test_e2e_maya_standalone``
    helper.
    """
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=_MCP_HEADERS, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            status = resp.status
            raw = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        status = exc.code
        raw = exc.read().decode("utf-8", errors="replace") if hasattr(exc, "read") else ""
    if not raw:
        return status, {}
    if "data:" in raw:
        # SSE — take the last data block.
        chunk = raw.split("data:")[-1].strip()
        return status, json.loads(chunk)
    return status, json.loads(raw)


def _list_all_mcp_tools(url: str, *, request_id: int = 100) -> list:
    """Walk core 0.15.9+ ``tools/list`` cursor pages and return every tool."""
    tools = []
    cursor = None
    pages = 0
    while True:
        payload: Dict[str, Any] = {"jsonrpc": "2.0", "id": request_id, "method": "tools/list"}
        if cursor:
            payload["params"] = {"cursor": cursor}
        status, body = _post_json(url, payload)
        assert status == 200, body
        result = body.get("result", {})
        tools.extend(result.get("tools", []))
        cursor = result.get("nextCursor")
        if not cursor:
            return tools
        pages += 1
        if pages > 50:
            raise RuntimeError("tools/list pagination exceeded 50 pages")


@contextmanager
def _running_server(*, scene_resolver: Optional[MayaSceneResolver] = None):
    """Start a real ``MayaMcpServer`` on a free port and yield it.

    The server runs entirely in-process; we explicitly disable the
    multi-instance gateway (``gateway_port=0``) so this fixture works
    in the per-PR CI matrix without leaving stale FileRegistry
    entries between tests.
    """
    port = _free_port()
    server = MayaMcpServer(port=port, gateway_port=0, job_storage_path="")
    # Re-bind a custom resolver before registration if the test asked
    # for one (e.g. to fake a "current Maya scene" without touching
    # ``maya.cmds``).  We patch by overwriting the integration object
    # on the server in-line; this matches how ``register_builtin_actions``
    # behaves — it just calls ``attach_to_server(self)``.
    server.register_builtin_actions()
    if scene_resolver is not None:
        # Replace the auto-bound integration with one that knows about
        # the fake scene.  Re-binding twice is safe: core's registry
        # is idempotent for ``register(name=...)``.
        integration = ProjectToolsIntegration(dcc_name="maya", scene_resolver=scene_resolver)
        integration.bind(server)
        server._project_tools = integration
    handle = server.start()
    try:
        yield server, handle
    finally:
        try:
            server.stop()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Ring 1 — unit tests
# ---------------------------------------------------------------------------


class TestEnvResolution(unittest.TestCase):
    """``DCC_MCP_MAYA_PROJECT_TOOLS`` precedence — explicit > env > default."""

    def setUp(self) -> None:
        self._saved = os.environ.pop(ENV_PROJECT_TOOLS, None)

    def tearDown(self) -> None:
        os.environ.pop(ENV_PROJECT_TOOLS, None)
        if self._saved is not None:
            os.environ[ENV_PROJECT_TOOLS] = self._saved

    def test_default_is_enabled(self) -> None:
        self.assertTrue(resolve_enabled(None))

    def test_env_zero_disables(self) -> None:
        os.environ[ENV_PROJECT_TOOLS] = "0"
        self.assertFalse(resolve_enabled(None))

    def test_env_one_enables(self) -> None:
        os.environ[ENV_PROJECT_TOOLS] = "1"
        self.assertTrue(resolve_enabled(None))

    def test_env_arbitrary_truthy_enables(self) -> None:
        os.environ[ENV_PROJECT_TOOLS] = "yes"
        self.assertTrue(resolve_enabled(None))

    def test_explicit_true_overrides_env_zero(self) -> None:
        os.environ[ENV_PROJECT_TOOLS] = "0"
        self.assertTrue(resolve_enabled(True))

    def test_explicit_false_overrides_env_one(self) -> None:
        os.environ[ENV_PROJECT_TOOLS] = "1"
        self.assertFalse(resolve_enabled(False))


class _StaticSceneResolver(MayaSceneResolver):
    """Test double — returns whatever ``scene`` was injected at construction."""

    def __init__(self, scene: Optional[str]) -> None:
        self._scene = scene
        self.calls = 0

    def current_scene(self) -> Optional[str]:
        self.calls += 1
        return self._scene


class _RaisingSceneResolver(MayaSceneResolver):
    """Test double — simulates ``cmds.file()`` blowing up in odd Maya state."""

    def current_scene(self) -> Optional[str]:
        raise RuntimeError("cmds.file blew up")


class TestMayaSceneResolverDefault(unittest.TestCase):
    """Default resolver must never raise — only return ``None`` outside Maya."""

    def test_returns_none_outside_maya(self) -> None:
        # We are not running inside maya.app.* so the import-guard branch
        # short-circuits and returns ``None``.  This is the contract the
        # integration relies on.
        resolver = MayaSceneResolver()
        self.assertIsNone(resolver.current_scene())


class TestProjectToolsIntegrationUnit(unittest.TestCase):
    """Bind/inner-server selection logic does not need a running server."""

    def test_inner_server_picked_when_both_attrs_present(self) -> None:
        # ``register_handler`` + ``registry`` → inner is acceptable.
        class _Inner:
            registry = object()

            def register_handler(self, name: str, fn: Any) -> None:
                pass

        class _Outer:
            _server = _Inner()
            registry = _Inner.registry  # proxied attr (matches MayaMcpServer)

        outer = _Outer()
        self.assertIs(
            ProjectToolsIntegration._inner_server(outer),
            outer._server,
        )

    def test_inner_server_returns_none_when_register_handler_missing(self) -> None:
        # If the wrapper proxies ``registry`` but inner has no
        # ``register_handler`` we must refuse to bind — registering
        # tools whose handlers won't actually fire would silently
        # 404 every agent call.
        class _BadInner:
            registry = object()

        class _Outer:
            _server = _BadInner()

        self.assertIsNone(ProjectToolsIntegration._inner_server(_Outer()))

    def test_inner_server_returns_none_when_no_inner(self) -> None:
        class _Outer:
            pass

        self.assertIsNone(ProjectToolsIntegration._inner_server(_Outer()))

    def test_safe_resolve_scene_swallows_resolver_errors(self) -> None:
        integration = ProjectToolsIntegration(scene_resolver=_RaisingSceneResolver())
        # Must NOT raise — server startup must always succeed.
        self.assertIsNone(integration._safe_resolve_scene())

    def test_safe_resolve_scene_normalises_path(self) -> None:
        # Forward-slash input on Windows should be normalised to the
        # platform separator so DccProject.open writes to a predictable
        # location.
        with tempfile.TemporaryDirectory() as td:
            scene = os.path.join(td, "shot.ma")
            integration = ProjectToolsIntegration(scene_resolver=_StaticSceneResolver(scene))
            resolved = integration._safe_resolve_scene()
            self.assertEqual(Path(resolved), Path(scene))

    def test_bind_returns_false_when_inner_server_missing(self) -> None:
        integration = ProjectToolsIntegration(scene_resolver=_StaticSceneResolver(None))

        class _NoInner:
            pass

        # ``register_project_tools`` must not be called when the server
        # cannot accept handlers — silent partial registration would be
        # worse than no registration at all.
        self.assertFalse(integration.bind(_NoInner()))
        self.assertFalse(integration.registered)

    def test_attach_to_server_skipped_when_disabled(self) -> None:
        # Explicit ``enabled=False`` must short-circuit before any
        # core call so a tightly-controlled embedding host can opt out.
        result = attach_project_tools(object(), enabled=False)
        self.assertIsNone(result)


# ---------------------------------------------------------------------------
# Ring 2 — MCP HTTP round-trip
# ---------------------------------------------------------------------------


class TestProjectToolsListedAndCallableOverMcp:
    """``project_*`` tools must round-trip via the live MCP server."""

    @pytest.fixture
    def scene(self, tmp_path: Path) -> Path:
        path = tmp_path / "shot_010.ma"
        path.write_text("//Maya ASCII 2024\n", encoding="utf-8")
        return path

    @pytest.fixture
    def server_with_default_project(self, scene: Path):
        with _running_server(scene_resolver=_StaticSceneResolver(str(scene))) as pair:
            yield pair

    def test_tools_list_includes_all_four_project_tools(self, server_with_default_project) -> None:
        _, handle = server_with_default_project
        names = {t["name"] for t in _list_all_mcp_tools(handle.mcp_url(), request_id=1)}
        assert _PROJECT_TOOL_NAMES <= names
        assert not any(name.startswith("project.") for name in names)
        assert all(_CLAUDE_TOOL_NAME_RE.fullmatch(name) for name in names)

    def test_token_budget_per_project_tool_is_under_800_bytes(self, server_with_default_project) -> None:
        """Guard against silent description bloat in the upstream tools.

        Each ``project_*`` entry in ``tools/list`` should fit comfortably
        under 800 B serialised — that is the whole point of registering
        them as a thin filesystem surface instead of bundling them as
        a full skill.  If this assertion fires, an upstream
        ``register_project_tools`` change has expanded the description
        or schema; verify the new size is intentional before bumping.
        """
        _, handle = server_with_default_project
        project_tools = [
            t for t in _list_all_mcp_tools(handle.mcp_url(), request_id=2) if t["name"].startswith("project_")
        ]
        assert len(project_tools) == 4
        for tool in project_tools:
            wire = json.dumps(tool, separators=(",", ":")).encode("utf-8")
            assert len(wire) <= 800, f"{tool['name']} has grown to {len(wire)}B — exceeds 800B token budget"

    def test_save_then_status_round_trip(self, server_with_default_project, scene: Path) -> None:
        _, handle = server_with_default_project
        save_status, save_body = _post_json(
            handle.mcp_url(),
            {
                "jsonrpc": "2.0",
                "id": 10,
                "method": "tools/call",
                "params": {
                    "name": "project_save",
                    "arguments": {"scene_path": str(scene)},
                },
            },
        )
        assert save_status == 200
        save_text = save_body["result"]["content"][0]["text"]
        save_payload = json.loads(save_text)
        assert save_payload["success"] is True
        # The state file must actually exist on disk.
        state_path = Path(save_payload["context"]["state_path"])
        assert state_path.is_file(), state_path
        assert state_path.parent.name == ".dcc-mcp"

        # ``project_status`` should report the same state file.
        _, status_body = _post_json(
            handle.mcp_url(),
            {
                "jsonrpc": "2.0",
                "id": 11,
                "method": "tools/call",
                "params": {
                    "name": "project_status",
                    "arguments": {"scene_path": str(scene)},
                },
            },
        )
        status_payload = json.loads(status_body["result"]["content"][0]["text"])
        assert status_payload["success"] is True
        assert status_payload["context"]["state_path"] == str(state_path)

    def test_load_returns_failure_for_missing_project(self, server_with_default_project, tmp_path: Path) -> None:
        # Pointing ``project_load`` at a directory that has never had a
        # project saved must return a structured failure — not an
        # internal 5xx — so agents can recover gracefully.
        unrelated = tmp_path / "elsewhere" / "fresh.ma"
        unrelated.parent.mkdir(parents=True)
        unrelated.write_text("//Maya ASCII\n", encoding="utf-8")
        _, handle = server_with_default_project
        _, body = _post_json(
            handle.mcp_url(),
            {
                "jsonrpc": "2.0",
                "id": 20,
                "method": "tools/call",
                "params": {
                    "name": "project_load",
                    "arguments": {"scene_path": str(unrelated)},
                },
            },
        )
        payload = json.loads(body["result"]["content"][0]["text"])
        assert payload["success"] is False
        assert "No project.json" in payload["message"]

    def test_resume_emits_full_session_payload(self, server_with_default_project, scene: Path) -> None:
        _, handle = server_with_default_project
        # Save first so resume has something to return.
        _post_json(
            handle.mcp_url(),
            {
                "jsonrpc": "2.0",
                "id": 30,
                "method": "tools/call",
                "params": {
                    "name": "project_save",
                    "arguments": {"scene_path": str(scene)},
                },
            },
        )
        _, body = _post_json(
            handle.mcp_url(),
            {
                "jsonrpc": "2.0",
                "id": 31,
                "method": "tools/call",
                "params": {
                    "name": "project_resume",
                    "arguments": {"scene_path": str(scene)},
                },
            },
        )
        payload = json.loads(body["result"]["content"][0]["text"])
        assert payload["success"] is True
        ctx = payload["context"]
        # The resume contract: full surface needed to rebuild a session.
        for required in (
            "scene_path",
            "loaded_assets",
            "active_skills",
            "active_tool_groups",
            "checkpoint_ids",
            "metadata",
            "session_id",
            "created_at",
            "updated_at",
            "project_dir",
            "state_path",
        ):
            assert required in ctx, f"missing {required!r} in resume payload"

    def test_default_project_binding_records_current_scene_on_server(
        self, server_with_default_project, scene: Path
    ) -> None:
        """The integration must remember the bound scene on the server.

        Upstream MCP schema validation requires ``scene_path`` for
        every ``project_*`` call (good — agents must be explicit
        about which scene they target), so the bound default project
        is not a "skip the argument" shortcut at the MCP layer.  Its
        real purpose is to give in-process Python callers (and future
        REST endpoints that resolve the active scene server-side) a
        stable handle to the live Maya scene's project state.

        We therefore assert two things:

        1. The :class:`ProjectToolsIntegration` recorded the scene
           the resolver returned.
        2. ``project_save`` with the explicit ``scene_path`` writes
           ``project.json`` next to that same scene — proving the
           server-side handler and the bound project agree on the
           filesystem location.
        """
        server, handle = server_with_default_project
        integration = server._project_tools
        assert integration is not None
        assert integration.bound_scene == str(scene)
        assert integration.bound_project is not None

        _, body = _post_json(
            handle.mcp_url(),
            {
                "jsonrpc": "2.0",
                "id": 40,
                "method": "tools/call",
                "params": {
                    "name": "project_save",
                    "arguments": {"scene_path": str(scene)},
                },
            },
        )
        payload = json.loads(body["result"]["content"][0]["text"])
        assert payload["success"] is True, payload
        assert payload["context"]["state"]["scene_path"] == str(scene)
        assert Path(payload["context"]["project_dir"]).parent == scene.parent


class TestProjectToolsWithoutDefaultProject:
    """When no Maya scene is open, callers MUST pass ``scene_path``."""

    @pytest.fixture
    def server(self):
        # Resolver returns ``None`` → no default project → argument-less
        # calls return a structured failure (not a crash).
        with _running_server(scene_resolver=_StaticSceneResolver(None)) as pair:
            yield pair

    def test_save_without_args_returns_friendly_error(self, server) -> None:
        """Calls missing ``scene_path`` MUST surface a structured error.

        Upstream MCP runs JSON-Schema validation before the handler
        executes, so the error envelope returned to the agent is the
        validator's ``EXECUTION_FAILED`` payload (with ``isError=True``)
        — not the handler's own ``success: False`` body.  Either path
        is acceptable for this test as long as:

        * the call did not crash with a 5xx, and
        * the agent receives a discoverable hint about ``scene_path``.

        That keeps the test resilient to upstream changes (e.g. core
        could later relax the schema and let the handler-level error
        surface) without losing the contract — agents always learn
        what they got wrong.
        """
        _, handle = server
        status, body = _post_json(
            handle.mcp_url(),
            {
                "jsonrpc": "2.0",
                "id": 50,
                "method": "tools/call",
                "params": {"name": "project_save", "arguments": {}},
            },
        )
        assert status == 200
        result = body["result"]
        text = result["content"][0]["text"]
        # Either ``isError`` or ``success: False`` must mark the failure.
        if result.get("isError"):
            assert "scene_path" in text
        else:
            payload = json.loads(text)
            assert payload["success"] is False
            assert "scene_path" in payload["message"]


# ---------------------------------------------------------------------------
# Ring 3 — REST channel (issue #165)
# ---------------------------------------------------------------------------


class TestProjectToolsViaRestChannel:
    """The four tools must also be reachable via the REST surface.

    Core 0.14.21 mounts ``/v1/tools/list`` and ``/v1/tools/call`` on the
    per-DCC server when the Rust REST layer is active.  In some build
    configurations the mount is conditional — we accept 404 as a valid
    "endpoint not present" answer (mirrors :mod:`test_rest_skill_api`)
    but reject any 5xx, malformed JSON, or — when present — any
    response that omits the four ``project_*`` tools.
    """

    @pytest.fixture
    def rest_server(self, tmp_path: Path):
        scene = tmp_path / "rest_shot.ma"
        scene.write_text("//Maya ASCII\n", encoding="utf-8")
        with _running_server(scene_resolver=_StaticSceneResolver(str(scene))) as pair:
            yield pair, scene

    @staticmethod
    def _rest_base(handle: Any) -> str:
        return handle.mcp_url().rsplit("/", 1)[0]

    @staticmethod
    def _safe_get(url: str) -> Tuple[int, bytes]:
        try:
            with urllib.request.urlopen(url, timeout=5) as resp:
                return resp.status, resp.read()
        except urllib.error.HTTPError as exc:
            return exc.code, exc.read() if hasattr(exc, "read") else b""

    @staticmethod
    def _safe_post(url: str, body: Dict[str, Any]) -> Tuple[int, bytes]:
        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return resp.status, resp.read()
        except urllib.error.HTTPError as exc:
            return exc.code, exc.read() if hasattr(exc, "read") else b""

    def test_rest_tools_list_includes_project_when_present(self, rest_server) -> None:
        (server, handle), _scene = rest_server
        base = self._rest_base(handle)

        # ``GET /v1/tools`` is the canonical REST mirror; some core
        # builds also serve ``/v1/skills`` for skill metadata only.
        status, body = self._safe_get(base + "/v1/tools")
        if status == 404:
            pytest.skip("Core build did not mount /v1/tools — REST surface optional")
        assert status < 500, body[:200]
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            pytest.fail(f"Non-JSON 200 from /v1/tools: {body[:200]!r}")
        names = {t["name"] for t in payload.get("tools", [])}
        assert _PROJECT_TOOL_NAMES <= names
        assert not any(name.startswith("project.") for name in names)

    def test_rest_tools_call_save_round_trips(self, rest_server) -> None:
        (server, handle), scene = rest_server
        base = self._rest_base(handle)
        status, body = self._safe_post(
            base + "/v1/call",
            {"tool_slug": "maya.core.project_save", "params": {"scene_path": str(scene)}},
        )
        assert status == 200, body[:200]
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            pytest.fail(f"Non-JSON {status} from /v1/call: {body[:200]!r}")
        # REST contract mirrors MCP: the envelope returned by the
        # handler is wrapped in a ``content``-style structure.  We do
        # not over-specify the wrapper here so this test stays resilient
        # to core's REST shape decisions; the only invariant we own is
        # that the call succeeds and references the scene's project dir.
        wire = json.dumps(payload)
        assert "project.json" in wire or "state_path" in wire, payload


# ---------------------------------------------------------------------------
# Ring 4 — opt-out path
# ---------------------------------------------------------------------------


class TestProjectToolsOptOut:
    """``DCC_MCP_MAYA_PROJECT_TOOLS=0`` skips registration end-to-end."""

    def test_disabled_via_env_means_no_project_tools_in_tools_list(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv(ENV_PROJECT_TOOLS, "0")
        with _running_server() as (server, handle):
            assert server._project_tools is None
            names = {t["name"] for t in _list_all_mcp_tools(handle.mcp_url(), request_id=60)}
            assert not any(n.startswith("project_") for n in names)


# ---------------------------------------------------------------------------
# Ring 5 — public re-exports
# ---------------------------------------------------------------------------


class TestPublicSurface(unittest.TestCase):
    """The package must surface the new symbols for downstream agents."""

    def test_top_level_exports(self) -> None:
        for name in (
            "ENV_PROJECT_TOOLS",
            "MayaSceneResolver",
            "ProjectToolsIntegration",
            "attach_project_tools",
        ):
            self.assertTrue(
                hasattr(dcc_mcp_maya, name),
                f"dcc_mcp_maya.{name} should be importable",
            )
            self.assertIn(name, dcc_mcp_maya.__all__, f"{name} missing from __all__")
