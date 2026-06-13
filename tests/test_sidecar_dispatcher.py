"""Unit tests for Maya's core-backed sidecar dispatch adapter."""

from __future__ import annotations

import textwrap
from pathlib import Path
from typing import Any, Callable, Optional

import pytest
from dcc_mcp_core.sidecar import (
    ERROR_DISPATCH_FAILED,
    ERROR_NO_SOURCE_FILE,
    ERROR_PAYLOAD_MALFORMED,
    ERROR_SERVER_NOT_RUNNING,
    ERROR_UNKNOWN_ACTION,
)

from dcc_mcp_maya.sidecar._dispatcher import dispatch_payload


class _StubAction:
    def __init__(
        self,
        name: str,
        source_file: Optional[str],
        *,
        skill_name: str = "maya-test-skill",
        affinity: str = "main",
        execution: str = "sync",
        timeout_hint_secs: int = 30,
    ) -> None:
        self.name = name
        self.source_file = source_file
        self.skill_name = skill_name
        self.affinity = affinity
        self.execution = execution
        self.timeout_hint_secs = timeout_hint_secs


class _StubServer:
    def __init__(
        self,
        actions: list[_StubAction] | None = None,
        *,
        raise_on_list: Exception | None = None,
    ) -> None:
        self._actions = actions or []
        self._raise_on_list = raise_on_list
        self.list_actions_call_count = 0
        self._skills: dict[str, bool] = {}

    def list_actions(self) -> list[_StubAction]:
        self.list_actions_call_count += 1
        if self._raise_on_list is not None:
            raise self._raise_on_list
        return list(self._actions)

    def load_skill(self, skill_name: str) -> bool:
        if skill_name in ("maya-primitives", "maya-animation"):
            self._skills[skill_name] = True
            return True
        return False

    def get_skill_info(self, skill_name: str) -> dict[str, Any] | None:
        if skill_name == "maya-primitives":
            return {"name": "maya-primitives", "tools": ["create_sphere", "create_cube"], "loaded": True}
        if skill_name == "maya-scene":
            return {"name": "maya-scene", "tools": ["save_scene"], "loaded": False}
        return None


def _server_lookup_returning(server: Any) -> Callable[[], Any]:
    return lambda: server


@pytest.fixture
def skill_script_dir(tmp_path: Path) -> Path:
    return tmp_path


def _write_skill(script_dir: Path, name: str, body: str) -> Path:
    src = textwrap.dedent(
        f"""
        def main(**params):
{textwrap.indent(textwrap.dedent(body), "            ")}
        """
    )
    script_path = script_dir / f"{name}.py"
    script_path.write_text(src, encoding="utf-8")
    return script_path


class TestPayloadValidation:
    def test_non_dict_payload_returns_payload_malformed(self):
        envelope = dispatch_payload(42, server_lookup=lambda: None)
        assert envelope["success"] is False
        assert envelope["error"] == ERROR_PAYLOAD_MALFORMED
        assert "object" in envelope["message"]

    def test_missing_action_key_returns_payload_malformed(self):
        envelope = dispatch_payload({"args": {}}, server_lookup=lambda: None)
        assert envelope["success"] is False
        assert envelope["error"] == ERROR_PAYLOAD_MALFORMED
        assert envelope["context"]["reason"] == "missing-action"

    def test_empty_action_string_returns_payload_malformed(self):
        envelope = dispatch_payload(
            {"action": "   ", "args": {}, "request_id": "r"},
            server_lookup=lambda: None,
        )
        assert envelope["error"] == ERROR_PAYLOAD_MALFORMED
        assert envelope["context"]["reason"] == "missing-action"

    def test_non_object_args_returns_payload_malformed(self):
        envelope = dispatch_payload(
            {"action": "ok", "args": [1, 2], "request_id": "r"},
            server_lookup=lambda: None,
        )
        assert envelope["error"] == ERROR_PAYLOAD_MALFORMED
        assert envelope["context"]["action"] == "ok"
        assert envelope["context"]["reason"] == "invalid-args"

    def test_string_payload_is_parsed_as_json(self):
        envelope = dispatch_payload('{"action": "ok"}', server_lookup=lambda: None)
        assert envelope["error"] == ERROR_SERVER_NOT_RUNNING

    def test_invalid_json_string_returns_payload_malformed(self):
        envelope = dispatch_payload("{ not even close to json", server_lookup=lambda: None)
        assert envelope["error"] == ERROR_PAYLOAD_MALFORMED


class TestServerLookup:
    def test_server_not_running_when_lookup_returns_none(self):
        envelope = dispatch_payload(
            {"action": "x", "args": {}, "request_id": "r1"},
            server_lookup=lambda: None,
        )
        assert envelope["success"] is False
        assert envelope["error"] == ERROR_SERVER_NOT_RUNNING
        assert envelope["context"]["request_id"] == "r1"
        assert envelope["context"]["action"] == "x"

    def test_unknown_action_returns_structured_envelope(self):
        server = _StubServer(actions=[_StubAction("known", "/tmp/known.py")])
        envelope = dispatch_payload(
            {"action": "mystery", "args": {}, "request_id": "r2"},
            server_lookup=_server_lookup_returning(server),
        )
        assert envelope["error"] == ERROR_UNKNOWN_ACTION
        assert envelope["context"]["action"] == "mystery"
        assert envelope["context"]["request_id"] == "r2"
        assert server.list_actions_call_count == 1

    def test_action_without_source_file_returns_no_source_file(self):
        server = _StubServer(actions=[_StubAction("rust_builtin", None)])
        envelope = dispatch_payload(
            {"action": "rust_builtin", "args": {}, "request_id": "r3"},
            server_lookup=_server_lookup_returning(server),
        )
        assert envelope["error"] == ERROR_NO_SOURCE_FILE
        assert envelope["context"]["action"] == "rust_builtin"

    def test_list_actions_raising_collapses_to_unknown_action(self):
        server = _StubServer(raise_on_list=RuntimeError("registry on fire"))
        envelope = dispatch_payload(
            {"action": "x", "args": {}, "request_id": "r4"},
            server_lookup=_server_lookup_returning(server),
        )
        assert envelope["error"] == ERROR_UNKNOWN_ACTION


class TestDispatchExecution:
    def test_happy_path_forwards_skill_return(self, skill_script_dir: Path):
        script = _write_skill(
            skill_script_dir,
            "echo",
            'return {"success": True, "echoed": params}',
        )
        server = _StubServer(actions=[_StubAction("echo_action", str(script))])

        envelope = dispatch_payload(
            {
                "action": "echo_action",
                "args": {"x": 1, "y": "hello"},
                "request_id": "r-happy",
            },
            server_lookup=_server_lookup_returning(server),
        )

        assert envelope["success"] is True
        assert envelope["echoed"] == {"x": 1, "y": "hello"}
        assert envelope["request_id"] == "r-happy"
        assert envelope["action"] == "echo_action"

    def test_skill_exception_forwards_executor_envelope(self, skill_script_dir: Path):
        script = _write_skill(
            skill_script_dir,
            "exploder",
            "raise RuntimeError('boom')",
        )
        server = _StubServer(actions=[_StubAction("exploder", str(script))])

        envelope = dispatch_payload(
            {"action": "exploder", "args": {}, "request_id": "r-fail"},
            server_lookup=_server_lookup_returning(server),
        )

        assert envelope["success"] is False
        assert "RuntimeError" in envelope["error"]
        assert "boom" in envelope["error"]
        assert envelope["request_id"] == "r-fail"
        assert envelope["action"] == "exploder"

    def test_executor_failure_returns_core_dispatch_failed(self, monkeypatch, skill_script_dir: Path):
        script = _write_skill(skill_script_dir, "noop", 'return {"success": True}')
        server = _StubServer(actions=[_StubAction("noop", str(script))])

        def fail(*_args, **_kwargs):
            raise RuntimeError("host executor stopped")

        monkeypatch.setattr("dcc_mcp_maya._executor.execute_in_process", fail)

        envelope = dispatch_payload(
            {"action": "noop", "args": {}, "request_id": "r-crash"},
            server_lookup=_server_lookup_returning(server),
        )

        assert envelope["success"] is False
        assert envelope["error"] == ERROR_DISPATCH_FAILED
        assert envelope["context"]["error_type"] == "RuntimeError"
        assert envelope["context"]["error_message"] == "host executor stopped"


class TestQtDispatchHandler:
    def test_dispatch_payload_returns_dict_for_core_qtserver_handler(self, skill_script_dir: Path):
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
        assert isinstance(response, dict)
        assert response["log"] == "line1\nline2\nline3"

    def test_dispatch_payload_returns_dict_for_qtserver_handler(self, skill_script_dir: Path):
        script = _write_skill(
            skill_script_dir,
            "i18n",
            'return {"success": True, "message": "已完成 (done)"}',
        )
        server = _StubServer(actions=[_StubAction("i18n", str(script))])

        envelope = dispatch_payload(
            {"action": "i18n", "args": {}, "request_id": "r-i18n"},
            server_lookup=_server_lookup_returning(server),
        )

        assert isinstance(envelope, dict)
        assert envelope["message"] == "已完成 (done)"


class TestBuiltinActionsLoadSkill:
    """Tests for the built-in ``load_skill`` sidecar action."""

    def test_load_skill_happy_path(self):
        server = _StubServer()
        envelope = dispatch_payload(
            {"action": "load_skill", "args": {"skill_name": "maya-primitives"}, "request_id": "r-load-1"},
            server_lookup=_server_lookup_returning(server),
        )
        assert envelope["success"] is True
        assert envelope["loaded"] is True
        assert envelope["skill_name"] == "maya-primitives"
        assert envelope["action"] == "load_skill"
        assert envelope["request_id"] == "r-load-1"
        assert "loaded successfully" in envelope["message"]

    def test_load_skill_failure(self):
        server = _StubServer()
        envelope = dispatch_payload(
            {"action": "load_skill", "args": {"skill_name": "nonexistent-skill"}, "request_id": "r-load-2"},
            server_lookup=_server_lookup_returning(server),
        )
        assert envelope["success"] is False
        assert envelope["loaded"] is False
        assert envelope["skill_name"] == "nonexistent-skill"
        assert envelope["error"] == "load-skill-failed"
        assert envelope["action"] == "load_skill"

    def test_load_skill_missing_skill_name(self):
        envelope = dispatch_payload(
            {"action": "load_skill", "args": {}, "request_id": "r-load-3"},
            server_lookup=_server_lookup_returning(_StubServer()),
        )
        assert envelope["success"] is False
        assert envelope["error"] == "payload-malformed"
        assert envelope["context"]["reason"] == "missing-skill-name"

    def test_load_skill_extra_args_passthrough(self):
        server = _StubServer()
        envelope = dispatch_payload(
            {"action": "load_skill", "args": {"skill_name": "maya-animation", "activate_groups": True}},
            server_lookup=_server_lookup_returning(server),
        )
        assert envelope["success"] is True
        assert envelope["loaded"] is True
        assert envelope["skill_name"] == "maya-animation"

    def test_load_skill_server_not_running(self):
        envelope = dispatch_payload(
            {"action": "load_skill", "args": {"skill_name": "maya-primitives"}, "request_id": "r-load-5"},
            server_lookup=lambda: None,
        )
        assert envelope["success"] is False
        assert envelope["error"] == "server-not-running"
        assert "server is not running" in envelope["message"]

    def test_load_skill_unknown_action_from_resolver_preserved(self):
        """A non-builtin action with name 'load_skill_fake' should still go through the resolver."""
        server = _StubServer()
        envelope = dispatch_payload(
            {"action": "load_skill_fake", "args": {}, "request_id": "r-load-6"},
            server_lookup=_server_lookup_returning(server),
        )
        assert envelope["error"] == ERROR_UNKNOWN_ACTION


class TestBuiltinActionsGetSkillInfo:
    """Tests for the built-in ``get_skill_info`` sidecar action."""

    def test_get_skill_info_happy_path(self):
        server = _StubServer()
        envelope = dispatch_payload(
            {"action": "get_skill_info", "args": {"skill_name": "maya-primitives"}, "request_id": "r-info-1"},
            server_lookup=_server_lookup_returning(server),
        )
        assert envelope["success"] is True
        assert envelope["skill_name"] == "maya-primitives"
        assert envelope["skill_info"] is not None
        assert "create_sphere" in envelope["skill_info"]
        assert envelope["action"] == "get_skill_info"

    def test_get_skill_info_not_found(self):
        server = _StubServer()
        envelope = dispatch_payload(
            {"action": "get_skill_info", "args": {"skill_name": "nonexistent"}, "request_id": "r-info-2"},
            server_lookup=_server_lookup_returning(server),
        )
        assert envelope["success"] is True
        assert envelope["skill_name"] == "nonexistent"
        assert envelope["skill_info"] is None

    def test_get_skill_info_missing_skill_name(self):
        envelope = dispatch_payload(
            {"action": "get_skill_info", "args": {}, "request_id": "r-info-3"},
            server_lookup=_server_lookup_returning(_StubServer()),
        )
        assert envelope["success"] is False
        assert envelope["error"] == "payload-malformed"
        assert envelope["context"]["reason"] == "missing-skill-name"

    def test_get_skill_info_server_not_running(self):
        envelope = dispatch_payload(
            {"action": "get_skill_info", "args": {"skill_name": "maya-primitives"}, "request_id": "r-info-4"},
            server_lookup=lambda: None,
        )
        assert envelope["success"] is False
        assert envelope["error"] == "server-not-running"

    def test_regular_actions_still_routed_through_resolver(self):
        """Non-builtin actions should not be intercepted; resolver is called."""
        server = _StubServer(actions=[_StubAction("regular_tool", "/tmp/some_tool.py")])
        dispatch_payload(
            {"action": "regular_tool", "args": {}},
            server_lookup=_server_lookup_returning(server),
        )
        # list_actions() was called, proving the resolver path was used
        assert server.list_actions_call_count == 1
