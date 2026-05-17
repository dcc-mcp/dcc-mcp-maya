"""Unit tests for :mod:`dcc_mcp_maya.sidecar._dispatcher`.

The dispatcher is the Maya-side counterpart to the Rust ``CommandPortClient``
(see dcc-mcp-core PR #1006). It accepts a wire frame from the sidecar
binary, looks up the action in the running ``MayaMcpServer``, runs the
backing skill script on the (commandPort-supplied) main thread, and
returns a single-line JSON envelope.

These tests stub ``server_lookup`` so we never need a real Maya — every
permutation of the dispatcher's contract is covered without importing
``maya.cmds``.
"""

# Import future modules
from __future__ import annotations

# Import built-in modules
import json
import textwrap
from pathlib import Path
from typing import Any, Callable, Optional

# Import third-party modules
import pytest

# Import local modules
from dcc_mcp_maya.sidecar._dispatcher import dispatch_payload

# ── server stubs ─────────────────────────────────────────────────


class _StubAction:
    """ToolMeta-shaped attribute access; mirrors the live registry entry."""

    def __init__(self, name: str, source_file: Optional[str]) -> None:
        self.name = name
        self.source_file = source_file


class _StubServer:
    """Pretends to be the running :class:`MayaMcpServer`.

    Records ``list_actions`` calls so tests can assert the dispatcher
    really delegated. Raises whatever the test prepared so we can pin
    the error-handling branches.
    """

    def __init__(
        self,
        actions: list[_StubAction] | None = None,
        *,
        raise_on_list: Exception | None = None,
    ) -> None:
        self._actions = actions or []
        self._raise_on_list = raise_on_list
        self.list_actions_call_count = 0

    def list_actions(self) -> list[_StubAction]:
        self.list_actions_call_count += 1
        if self._raise_on_list is not None:
            raise self._raise_on_list
        return list(self._actions)


def _server_lookup_returning(server: Any) -> Callable[[], Any]:
    return lambda: server


# ── skill-script fixtures ───────────────────────────────────────


@pytest.fixture
def skill_script_dir(tmp_path: Path) -> Path:
    return tmp_path


def _write_skill(script_dir: Path, name: str, body: str) -> Path:
    """Write a tiny skill script that exposes ``main(**params)`` and
    return its absolute path. ``body`` is the *function body* — it
    gets indented and parameters from the wire frame are available as
    ``params``.
    """
    src = textwrap.dedent(
        f"""
        def main(**params):
{textwrap.indent(textwrap.dedent(body), "            ")}
        """
    )
    script_path = script_dir / f"{name}.py"
    script_path.write_text(src, encoding="utf-8")
    return script_path


# ── tests: payload validation ───────────────────────────────────


class TestPayloadValidation:
    """Pin the structured errors the dispatcher emits for malformed
    wire frames. Each shape collapses to a single-line JSON envelope
    even when the payload itself is nonsense."""

    def test_non_dict_payload_returns_payload_malformed(self):
        envelope = json.loads(dispatch_payload(42, server_lookup=lambda: None))
        assert envelope["success"] is False
        assert envelope["error"] == "payload-malformed"
        assert "JSON object" in envelope["message"]

    def test_missing_action_key_returns_payload_malformed(self):
        envelope = json.loads(dispatch_payload({"args": {}}, server_lookup=lambda: None))
        assert envelope["success"] is False
        assert envelope["error"] == "payload-malformed"

    def test_empty_action_string_returns_payload_malformed(self):
        envelope = json.loads(
            dispatch_payload(
                {"action": "   ", "args": {}, "request_id": "r"},
                server_lookup=lambda: None,
            )
        )
        assert envelope["error"] == "payload-malformed"
        assert envelope["request_id"] == "r"

    def test_non_object_args_returns_payload_malformed(self):
        envelope = json.loads(
            dispatch_payload(
                {"action": "ok", "args": [1, 2], "request_id": "r"},
                server_lookup=lambda: None,
            )
        )
        assert envelope["error"] == "payload-malformed"
        assert "JSON object" in envelope["message"]
        assert envelope["action"] == "ok"

    def test_string_payload_is_parsed_as_json(self):
        envelope = json.loads(dispatch_payload('{"action": "ok"}', server_lookup=lambda: None))
        # The server lookup returns None, so we expect the
        # `server-not-running` envelope — not a parse error.
        assert envelope["error"] == "server-not-running"

    def test_invalid_json_string_returns_payload_malformed(self):
        envelope = json.loads(dispatch_payload("{ not even close to json", server_lookup=lambda: None))
        assert envelope["error"] == "payload-malformed"


# ── tests: server lookup branches ──────────────────────────────


class TestServerLookup:
    def test_server_not_running_when_lookup_returns_none(self):
        envelope = json.loads(
            dispatch_payload(
                {"action": "x", "args": {}, "request_id": "r1"},
                server_lookup=lambda: None,
            )
        )
        assert envelope["success"] is False
        assert envelope["error"] == "server-not-running"
        assert envelope["request_id"] == "r1"
        assert envelope["action"] == "x"

    def test_unknown_action_returns_structured_envelope(self):
        server = _StubServer(actions=[_StubAction("known", "/tmp/known.py")])
        envelope = json.loads(
            dispatch_payload(
                {"action": "mystery", "args": {}, "request_id": "r2"},
                server_lookup=_server_lookup_returning(server),
            )
        )
        assert envelope["error"] == "unknown-action"
        assert envelope["action"] == "mystery"
        assert envelope["request_id"] == "r2"
        # The dispatcher must actually have asked the server for the
        # action list — not just guessed.
        assert server.list_actions_call_count == 1

    def test_action_without_source_file_returns_no_source_file(self):
        server = _StubServer(actions=[_StubAction("rust_builtin", None)])
        envelope = json.loads(
            dispatch_payload(
                {"action": "rust_builtin", "args": {}, "request_id": "r3"},
                server_lookup=_server_lookup_returning(server),
            )
        )
        assert envelope["error"] == "no-source-file"
        assert envelope["action"] == "rust_builtin"

    def test_list_actions_raising_collapses_to_unknown_action(self):
        # If the server's own list_actions blows up, we cannot know
        # whether the action exists — collapse to `unknown-action`
        # rather than masquerading as `dispatch-failed`.  The agent
        # will see `unknown-action` and either retry or load_skill.
        server = _StubServer(raise_on_list=RuntimeError("registry on fire"))
        envelope = json.loads(
            dispatch_payload(
                {"action": "x", "args": {}, "request_id": "r4"},
                server_lookup=_server_lookup_returning(server),
            )
        )
        assert envelope["error"] == "unknown-action"


# ── tests: real skill-script execution ──────────────────────────


class TestDispatchExecution:
    def test_happy_path_forwards_skill_return(self, skill_script_dir: Path):
        script = _write_skill(
            skill_script_dir,
            "echo",
            'return {"success": True, "echoed": params}',
        )
        server = _StubServer(actions=[_StubAction("echo_action", str(script))])

        envelope = json.loads(
            dispatch_payload(
                {
                    "action": "echo_action",
                    "args": {"x": 1, "y": "hello"},
                    "request_id": "r-happy",
                },
                server_lookup=_server_lookup_returning(server),
            )
        )

        assert envelope["success"] is True
        assert envelope["echoed"] == {"x": 1, "y": "hello"}

    def test_skill_exception_returns_skill_exception_envelope(self, skill_script_dir: Path):
        # ``run_skill_script`` catches the RuntimeError and wraps it
        # through ``dcc_mcp_core.skill.skill_exception``, producing a
        # ``success: False`` envelope that includes the formatted
        # exception. The dispatcher forwards it verbatim — same shape
        # as the in-process path — and enriches with correlation IDs.
        script = _write_skill(
            skill_script_dir,
            "exploder",
            "raise RuntimeError('boom')",
        )
        server = _StubServer(actions=[_StubAction("exploder", str(script))])

        envelope = json.loads(
            dispatch_payload(
                {"action": "exploder", "args": {}, "request_id": "r-fail"},
                server_lookup=_server_lookup_returning(server),
            )
        )

        assert envelope["success"] is False
        # `error` carries `repr(exc)` per skill_exception's contract.
        assert "RuntimeError" in envelope["error"]
        assert "boom" in envelope["error"]
        # Correlation IDs are enriched by the dispatcher itself, not
        # by the skill.
        assert envelope["request_id"] == "r-fail"
        assert envelope["action"] == "exploder"

    def test_non_dict_return_wrapped_as_success_message(self, skill_script_dir: Path):
        # ``run_skill_script`` already wraps non-dict returns into
        # ``{"success": True, "message": str(value)}`` — the
        # dispatcher passes that through and adds correlation IDs.
        script = _write_skill(skill_script_dir, "primitive", "return 42")
        server = _StubServer(actions=[_StubAction("primitive", str(script))])

        envelope = json.loads(
            dispatch_payload(
                {"action": "primitive", "args": {}, "request_id": "r-int"},
                server_lookup=_server_lookup_returning(server),
            )
        )
        assert envelope["success"] is True
        assert envelope["message"] == "42"
        assert envelope["request_id"] == "r-int"
        assert envelope["action"] == "primitive"

    def test_skill_system_exit_is_silent_success(self, skill_script_dir: Path):
        # ``run_skill_script`` intercepts ``SystemExit`` and returns
        # the script's ``__mcp_result__`` if present, else a default
        # ``{"success": True, "message": "Script executed"}``.  The
        # dispatcher then enriches with correlation IDs.
        script = _write_skill(
            skill_script_dir,
            "bailer",
            "raise SystemExit(0)",
        )
        server = _StubServer(actions=[_StubAction("bailer", str(script))])

        envelope = json.loads(
            dispatch_payload(
                {"action": "bailer", "args": {}, "request_id": "r-bail"},
                server_lookup=_server_lookup_returning(server),
            )
        )
        assert envelope["success"] is True
        assert envelope["request_id"] == "r-bail"
        assert envelope["action"] == "bailer"


# ── tests: wire-format guarantees ───────────────────────────────


class TestWireFormatGuarantees:
    """The Rust ``CommandPortClient`` reads exactly one line per call.
    Multi-line JSON would corrupt the next request's response.  These
    tests pin that contract."""

    def test_response_is_always_single_line(self, skill_script_dir: Path):
        script = _write_skill(
            skill_script_dir,
            "multiliner",
            'return {"success": True, "log": "line1\\nline2\\nline3"}',
        )
        server = _StubServer(actions=[_StubAction("multiliner", str(script))])

        response = dispatch_payload(
            {"action": "multiliner", "args": {}, "request_id": "r-ml"},
            server_lookup=_server_lookup_returning(server),
        )
        assert "\n" not in response, f"response must not contain literal LF; got: {response!r}"
        # JSON-decoded value still has the escape preserved so the
        # gateway / MCP client sees the original newline.
        envelope = json.loads(response)
        assert envelope["log"] == "line1\nline2\nline3"

    def test_traceback_envelope_is_single_line(self):
        # A failing skill produces a multi-line traceback — the most
        # common newline-corrupting case.  This explicit test guards
        # against regressions where someone forgets to call
        # `_to_single_line_json` on the error path.
        server = _StubServer(actions=[_StubAction("boom", "/does/not/exist.py")])
        response = dispatch_payload(
            {"action": "boom", "args": {}, "request_id": "r-tb"},
            server_lookup=_server_lookup_returning(server),
        )
        assert "\n" not in response
        envelope = json.loads(response)
        assert envelope["success"] is False

    def test_response_is_valid_utf8_json(self, skill_script_dir: Path):
        # Confirm we don't ASCII-mangle multi-byte characters in
        # localised skill names / messages.
        script = _write_skill(
            skill_script_dir,
            "i18n",
            'return {"success": True, "message": "已完成 (done)"}',
        )
        server = _StubServer(actions=[_StubAction("i18n", str(script))])
        response = dispatch_payload(
            {"action": "i18n", "args": {}, "request_id": "r-i18n"},
            server_lookup=_server_lookup_returning(server),
        )
        envelope = json.loads(response)
        assert envelope["message"] == "已完成 (done)"
        # Confirm the raw line is NOT pre-escaped to ASCII (`\u5df2`
        # would mean we lost ensure_ascii=False).  Either form is
        # technically valid JSON, but we choose the smaller wire form.
        assert "已" in response, f"i18n chars should ship as UTF-8 on the wire, got: {response!r}"


# ── tests: top-level _sidecar shim ──────────────────────────────


class TestTopLevelShim:
    """The Rust client's wire frame imports
    ``dcc_mcp_maya._sidecar.dispatch``.  Pin that module exists and
    its ``dispatch`` symbol resolves to the same callable the
    sidecar package exports — a wire-format compat smoke test."""

    def test_underscored_sidecar_module_is_importable(self):
        import dcc_mcp_maya._sidecar as wire_entry
        from dcc_mcp_maya.sidecar import dispatch as canonical_dispatch

        assert wire_entry.dispatch is canonical_dispatch

    def test_dispatch_via_top_level_module(self):
        import dcc_mcp_maya._sidecar as wire_entry

        envelope = json.loads(wire_entry.dispatch({"action": "any", "args": {}, "request_id": "r"}))
        # Without a stub server in place we reach the
        # ``server-not-running`` branch — proves the shim is
        # forwarding to the real dispatcher.
        assert envelope["error"] == "server-not-running"


# ── tests: catch-all safety ─────────────────────────────────────


def test_dispatcher_never_raises_to_caller():
    """The commandPort wire is single-line and synchronous.  Any
    exception escaping the dispatcher would corrupt Maya's reply
    handler, so the outer entry point MUST always return a string."""

    def boom_lookup() -> Any:
        raise RuntimeError("server_lookup itself raised")

    response = dispatch_payload(
        {"action": "x", "args": {}, "request_id": "r-catch"},
        server_lookup=boom_lookup,
    )
    envelope = json.loads(response)
    assert envelope["success"] is False
    assert envelope["error"] == "dispatch-failed"
    assert "server_lookup itself raised" in envelope["message"]
