"""Integration tests: custom skill discovery, in-process execution, side effects.

These tests exercise the full path that an MCP host triggers when calling a
tool registered against the Maya MCP server, without going over HTTP:

1. A custom skill (``SKILL.md`` + ``tools.yaml`` + ``scripts/*.py``) is written
   to a temporary directory.
2. ``MayaMcpServer.register_builtin_actions(extra_skill_paths=[tmp])`` discovers
   the skill, then ``load_skill`` activates it and wires the in-process Python executor.
3. The registered handler is invoked via :meth:`_execute_in_process` (the same
   call path used by ``tools/call``) and the on-disk side effects produced by
   the script are asserted directly.

Coverage targets:

* Custom skill end-to-end: file write / read / append from inside a script.
* Bundled ``maya-scripting`` scripts (``execute_python`` / ``execute_mel``)
  invoked with a mocked ``maya.cmds`` / ``maya.mel`` so the dispatch contract
  is validated even outside ``mayapy``.
"""

# Import future modules
from __future__ import annotations

# Import built-in modules
import sys
import textwrap
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock

import pytest

# ---------------------------------------------------------------------------
# Skill scaffolding helpers
# ---------------------------------------------------------------------------


_SKILL_MD_TEMPLATE = textwrap.dedent("""\
    ---
    name: {name}
    description: "Integration-test skill that touches files on disk."
    license: MIT
    metadata:
      dcc-mcp:
        dcc: maya
        layer: domain
        version: 1.0.0
        tags: [maya, test]
        depends: []
        tools: tools.yaml
        groups: groups.yaml
    ---

    # {name}

    Integration-test skill.
""")


def _write_skill(skill_root: Path, skill_name: str, scripts: dict[str, str]) -> Path:
    """Create a skill package on disk and return its directory."""
    pkg = skill_root / skill_name
    (pkg / "scripts").mkdir(parents=True)
    (pkg / "SKILL.md").write_text(_SKILL_MD_TEMPLATE.format(name=skill_name), encoding="utf-8")

    tool_lines = ["tools:"]
    for stem in scripts:
        tool_lines.extend([f"- name: {stem}", "  execution: sync", "  affinity: any", "  group: core"])
    (pkg / "tools.yaml").write_text("\n".join(tool_lines) + "\n", encoding="utf-8")

    group_lines = [
        "groups:",
        "- name: core",
        '  description: "Integration-test core group."',
        "  default_active: true",
        "  tools:",
    ]
    group_lines.extend(f"  - {stem}" for stem in scripts)
    (pkg / "groups.yaml").write_text("\n".join(group_lines) + "\n", encoding="utf-8")

    for stem, body in scripts.items():
        (pkg / "scripts" / f"{stem}.py").write_text(textwrap.dedent(body), encoding="utf-8")

    return pkg


def _make_server():
    """Build a real ``MayaMcpServer`` without starting the HTTP listener."""
    from dcc_mcp_maya.server import MayaMcpServer

    return MayaMcpServer(port=0, server_name="maya-integration-test")


def _action_name(skill_name: str, script_stem: str) -> str:
    """Mirror the AGENTS.md convention: ``{skill}__{script}`` with dashes->underscores."""
    return f"{skill_name.replace('-', '_')}__{script_stem}"


def _discover_and_load(server, skill: Path) -> None:
    server.register_builtin_actions(extra_skill_paths=[str(skill.parent)], include_bundled=False, minimal=False)
    assert server.load_skill(skill.name)


# ---------------------------------------------------------------------------
# 1. Custom skill end-to-end (discovery + handler wiring + file side effect)
# ---------------------------------------------------------------------------


class TestCustomSkillEndToEnd:
    """Discover a custom skill from a tmp dir, invoke its handler, assert side effects."""

    def test_discover_custom_skill_via_extra_skill_paths(self, tmp_path):
        skill = _write_skill(
            tmp_path,
            "maya-itest-discover",
            {"ping": "def main(**kwargs):\n    return {'success': True, 'message': 'pong'}\n"},
        )
        server = _make_server()
        try:
            _discover_and_load(server, skill)

            actions = server._server.registry.list_actions_enabled()
            names = {a["name"] for a in actions if isinstance(a, dict) and a.get("name")}
            assert _action_name("maya-itest-discover", "ping") in names
        finally:
            server.stop()

    def test_discover_custom_skill_via_single_package_extra_skill_path(self, tmp_path):
        """A direct skill package path is a valid ``extra_skill_paths`` entry."""
        skill = _write_skill(
            tmp_path,
            "maya-itest-direct-root",
            {"ping": "def main(**kwargs):\n    return {'success': True, 'message': 'pong'}\n"},
        )
        server = _make_server()
        try:
            server.register_builtin_actions(extra_skill_paths=[str(skill)], include_bundled=False, minimal=False)
            assert server.load_skill(skill.name)

            actions = server._server.registry.list_actions_enabled()
            names = {a["name"] for a in actions if isinstance(a, dict) and a.get("name")}
            assert _action_name("maya-itest-direct-root", "ping") in names
        finally:
            server.stop()

    def test_handler_registered_for_custom_skill(self, tmp_path):
        skill = _write_skill(
            tmp_path,
            "maya-itest-handler",
            {"noop": "def main(**kwargs):\n    return {'success': True, 'message': 'ok'}\n"},
        )
        server = _make_server()
        try:
            _discover_and_load(server, skill)

            assert server._server.has_handler(_action_name("maya-itest-handler", "noop"))
        finally:
            server.stop()

    def test_invoke_custom_skill_writes_file(self, tmp_path):
        """Handler creates a file on disk; the test reads it back to prove execution happened."""
        artifact = tmp_path / "artifact.txt"
        skill = _write_skill(
            tmp_path,
            "maya-itest-write",
            {
                "write": f"""
                    from pathlib import Path

                    def main(content: str = "default", **kwargs):
                        target = Path(r"{artifact}")
                        target.write_text(content, encoding="utf-8")
                        return {{"success": True, "message": "wrote", "context": {{"path": str(target)}}}}
                """,
            },
        )
        server = _make_server()
        try:
            _discover_and_load(server, skill)
            action_name = _action_name("maya-itest-write", "write")
            script_path = server._server.registry.get_action(action_name)["source_file"]

            result = server._execute_in_process(script_path, {"content": "hello-from-skill"}, action_name)

            assert result["success"] is True
            assert artifact.read_text(encoding="utf-8") == "hello-from-skill"
            assert result["context"]["path"] == str(artifact)
        finally:
            server.stop()

    def test_invoke_custom_skill_modifies_existing_file(self, tmp_path):
        """Handler reads existing content, appends to it, writes back; result reflects both states."""
        artifact = tmp_path / "log.txt"
        artifact.write_text("seed\n", encoding="utf-8")
        skill = _write_skill(
            tmp_path,
            "maya-itest-modify",
            {
                "append": f"""
                    from pathlib import Path

                    def main(line: str = "", **kwargs):
                        target = Path(r"{artifact}")
                        before = target.read_text(encoding="utf-8")
                        target.write_text(before + line + "\\n", encoding="utf-8")
                        return {{
                            "success": True,
                            "message": "appended",
                            "context": {{"before_len": len(before), "after_len": len(before) + len(line) + 1}},
                        }}
                """,
            },
        )
        server = _make_server()
        try:
            _discover_and_load(server, skill)
            action_name = _action_name("maya-itest-modify", "append")
            script_path = server._server.registry.get_action(action_name)["source_file"]

            result = server._execute_in_process(script_path, {"line": "added-by-test"}, action_name)

            assert result["success"] is True
            assert artifact.read_text(encoding="utf-8") == "seed\nadded-by-test\n"
            assert result["context"]["before_len"] == len("seed\n")
            assert result["context"]["after_len"] == len("seed\nadded-by-test\n")
        finally:
            server.stop()

    def test_custom_skill_kwargs_propagate_to_main(self, tmp_path):
        """Arguments passed to the handler reach ``main(**kwargs)`` verbatim."""
        skill = _write_skill(
            tmp_path,
            "maya-itest-args",
            {
                "echo": """
                    def main(**kwargs):
                        return {"success": True, "message": "echo", "context": {"got": kwargs}}
                """,
            },
        )
        server = _make_server()
        try:
            _discover_and_load(server, skill)
            action_name = _action_name("maya-itest-args", "echo")
            script_path = server._server.registry.get_action(action_name)["source_file"]

            result = server._execute_in_process(script_path, {"radius": 2.5, "name": "x"}, action_name)

            assert result["success"] is True
            assert result["context"]["got"] == {"radius": 2.5, "name": "x"}
        finally:
            server.stop()

    def test_custom_skill_exception_returns_failure_dict(self, tmp_path):
        """A raising script must surface as ``{'success': False, ...}`` rather than crash the handler."""
        skill = _write_skill(
            tmp_path,
            "maya-itest-raise",
            {
                "boom": """
                    def main(**kwargs):
                        raise RuntimeError("intentional failure")
                """,
            },
        )
        server = _make_server()
        try:
            _discover_and_load(server, skill)
            action_name = _action_name("maya-itest-raise", "boom")
            script_path = server._server.registry.get_action(action_name)["source_file"]

            result = server._execute_in_process(script_path, {}, action_name)

            assert result["success"] is False
            assert "intentional failure" in str(result)
        finally:
            server.stop()


# ---------------------------------------------------------------------------
# 2. Bundled maya-scripting scripts: execute_python / execute_mel
# ---------------------------------------------------------------------------


@pytest.fixture()
def fake_maya(monkeypatch):
    """Inject a stubbed ``maya`` package so scripts importing ``maya.cmds`` / ``maya.mel`` succeed.

    The real ``maya`` modules are only available inside ``mayapy`` / Maya. The
    bundled ``execute_python`` and ``execute_mel`` scripts ``import maya.cmds``
    and ``import maya.mel`` lazily inside the function body, so a ``MagicMock``
    namespace is enough to drive the success / failure paths and to assert that
    user code did call into the Maya API as expected.
    """
    cmds = MagicMock(name="maya.cmds")
    mel = MagicMock(name="maya.mel")

    maya_pkg = ModuleType("maya")
    maya_cmds_mod = ModuleType("maya.cmds")
    maya_mel_mod = ModuleType("maya.mel")
    # Forward attribute access on the modules to the per-call mock so the test
    # can assert against ``cmds.polyCube.assert_called_once()`` etc.
    for name in ("polyCube", "polySphere", "ls", "objExists", "currentTime"):
        setattr(maya_cmds_mod, name, getattr(cmds, name))
    maya_mel_mod.eval = mel.eval
    maya_pkg.cmds = maya_cmds_mod
    maya_pkg.mel = maya_mel_mod

    monkeypatch.setitem(sys.modules, "maya", maya_pkg)
    monkeypatch.setitem(sys.modules, "maya.cmds", maya_cmds_mod)
    monkeypatch.setitem(sys.modules, "maya.mel", maya_mel_mod)

    return {"cmds": cmds, "mel": mel}


def _bundled_script(stem: str) -> Path:
    return (
        Path(__file__).resolve().parents[1]
        / "src"
        / "dcc_mcp_maya"
        / "skills"
        / "maya-scripting"
        / "scripts"
        / f"{stem}.py"
    )


def _import_bundled(stem: str):
    """Import a bundled ``maya-scripting`` script as a fresh module."""
    import importlib.util  # noqa: PLC0415

    spec = importlib.util.spec_from_file_location(f"_bundled_{stem}", str(_bundled_script(stem)))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


class TestExecutePythonScript:
    """Bundled ``maya-scripting/scripts/execute_python.py`` end-to-end."""

    def test_runs_provided_python_and_invokes_cmds(self, fake_maya):
        mod = _import_bundled("execute_python")

        result = mod.execute_python(code="cmds.polyCube(name='unitTestCube')")

        assert result["success"] is True, "envelope was {0}".format(result)
        fake_maya["cmds"].polyCube.assert_called_once_with(name="unitTestCube")

    def test_captures_result_variable(self, fake_maya):
        """The new bare-exec contract surfaces the trailing expression
        when ``result_type='VALUE'`` (matches PatrickPalmer/maya-mcp-server).

        The legacy ``result = ...`` magic-variable convention is gone —
        users assign and then leave a bare expression on the last line,
        same as a Script Editor session.
        """
        mod = _import_bundled("execute_python")

        result = mod.execute_python(code="result = 7 * 6\nresult", result_type="VALUE")

        assert result["success"] is True, "envelope was {0}".format(result)
        assert result["context"]["output"] == "42"

    def test_captures_stdout_when_requested(self, fake_maya):
        mod = _import_bundled("execute_python")

        result = mod.execute_python(code="print('hello-stdout')", capture_output=True)

        assert result["success"] is True
        assert "hello-stdout" in result["context"]["stdout"]

    def test_empty_code_returns_failure(self, fake_maya):
        mod = _import_bundled("execute_python")

        result = mod.execute_python(code="   ")

        assert result["success"] is False

    def test_syntax_error_returns_failure_dict(self, fake_maya):
        mod = _import_bundled("execute_python")

        result = mod.execute_python(code="this is not python !!!")

        assert result["success"] is False
        # Must surface as a dict, not a raised exception.
        assert isinstance(result, dict)


class TestExecuteMelScript:
    """Bundled ``maya-scripting/scripts/execute_mel.py`` end-to-end."""

    def test_runs_provided_mel_and_invokes_mel_eval(self, fake_maya):
        mod = _import_bundled("execute_mel")
        fake_maya["mel"].eval.return_value = "melOk"

        result = mod.execute_mel(code="polySphere -r 1 -n unitTestSphere;")

        assert result["success"] is True
        fake_maya["mel"].eval.assert_called_once_with("polySphere -r 1 -n unitTestSphere;")
        assert result["context"]["output"] == "melOk"

    def test_empty_script_returns_failure(self, fake_maya):
        mod = _import_bundled("execute_mel")

        result = mod.execute_mel(code="   ")

        assert result["success"] is False

    def test_mel_runtime_error_returns_failure_dict(self, fake_maya):
        mod = _import_bundled("execute_mel")
        fake_maya["mel"].eval.side_effect = RuntimeError("MEL syntax error")

        result = mod.execute_mel(code="this_is_invalid_mel_xyz!!!;")

        assert result["success"] is False
        assert isinstance(result, dict)
