"""Unit tests for the maya-dev skill.

These tests run without a live Maya session.  They pin the development
workflow pieces that are pure Python: project attachment, module purge,
entrypoint/script execution, debugpy bootstrap, and graceful UI-capture
degradation when Qt/Maya is absent.
"""

from __future__ import annotations

import importlib
import sys
import types
from pathlib import Path
from unittest.mock import patch

import yaml

from tests.conftest import load_skill_script


def _write_demo_package(root: Path) -> None:
    pkg = root / "demo_tool"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "runner.py").write_text(
        "VALUE = 1\n"
        "\n"
        "def main(x=0):\n"
        "    print('runner-main', x)\n"
        "    return {'value': VALUE, 'x': x}\n"
        "\n"
        "def boom():\n"
        "    print('before-boom')\n"
        "    raise RuntimeError('dev-boom')\n",
        encoding="utf-8",
    )


def _cleanup_demo_modules() -> None:
    for name in list(sys.modules):
        if name == "demo_tool" or name.startswith("demo_tool."):
            sys.modules.pop(name, None)


def test_attach_project_adds_root_and_src_to_sys_path(tmp_path: Path, monkeypatch) -> None:
    from dcc_mcp_maya import _dev_session

    _dev_session.reset_for_tests()
    old_sys_path = sys.path[:]
    root = tmp_path / "project"
    src = root / "src"
    src.mkdir(parents=True)

    try:
        out = _dev_session.attach_project(str(root), package_prefixes=["demo_tool"])
        assert out["success"] is True
        ctx = out["context"]
        assert ctx["project"]["root"] == str(root)
        assert ctx["project"]["package_prefixes"] == ["demo_tool"]
        assert str(root) in sys.path
        assert str(src) in sys.path
    finally:
        sys.path[:] = old_sys_path
        _dev_session.reset_for_tests()


def test_attach_project_respects_allowed_roots(tmp_path: Path, monkeypatch) -> None:
    from dcc_mcp_maya import _dev_session

    _dev_session.reset_for_tests()
    allowed = tmp_path / "allowed"
    denied = tmp_path / "denied"
    allowed.mkdir()
    denied.mkdir()

    with patch.dict("os.environ", {"DCC_MCP_MAYA_DEV_ROOTS": str(allowed)}):
        out = _dev_session.attach_project(str(denied))

    assert out["success"] is False
    assert "outside allowed" in out["message"].lower()
    assert out["context"]["allowed_root_count"] == 1


def test_reload_modules_purges_attached_project_modules(tmp_path: Path) -> None:
    from dcc_mcp_maya import _dev_session

    _dev_session.reset_for_tests()
    old_sys_path = sys.path[:]
    _cleanup_demo_modules()
    _write_demo_package(tmp_path)

    try:
        assert _dev_session.attach_project(str(tmp_path), package_prefixes=["demo_tool"])["success"] is True
        importlib.import_module("demo_tool.runner")

        assert "demo_tool.runner" in sys.modules
        out = _dev_session.reload_modules()
        assert out["success"] is True
        assert "demo_tool.runner" in out["context"]["modules"]
        assert "demo_tool.runner" not in sys.modules
    finally:
        sys.path[:] = old_sys_path
        _cleanup_demo_modules()
        _dev_session.reset_for_tests()


def test_run_entrypoint_captures_stdout_and_json_return(tmp_path: Path) -> None:
    from dcc_mcp_maya import _dev_session

    _dev_session.reset_for_tests()
    old_sys_path = sys.path[:]
    _cleanup_demo_modules()
    _write_demo_package(tmp_path)

    try:
        _dev_session.attach_project(str(tmp_path), package_prefixes=["demo_tool"])
        out = _dev_session.run_entrypoint(target="demo_tool.runner:main", kwargs={"x": 7})
        assert out["success"] is True
        ctx = out["context"]
        assert "runner-main 7" in ctx["stdout"]
        assert ctx["return_value"] == {"value": 1, "x": 7}
        assert ctx["target"] == "demo_tool.runner:main"
        assert ctx["reload"]["mode"] == "purge"
    finally:
        sys.path[:] = old_sys_path
        _cleanup_demo_modules()
        _dev_session.reset_for_tests()


def test_run_entrypoint_returns_traceback_on_failure(tmp_path: Path) -> None:
    from dcc_mcp_maya import _dev_session

    _dev_session.reset_for_tests()
    old_sys_path = sys.path[:]
    _cleanup_demo_modules()
    _write_demo_package(tmp_path)

    try:
        _dev_session.attach_project(str(tmp_path), package_prefixes=["demo_tool"])
        out = _dev_session.run_entrypoint(target="demo_tool.runner:boom")
        assert out["success"] is False
        ctx = out["context"]
        assert "before-boom" in ctx["stdout"]
        assert "RuntimeError" in ctx["traceback"]
        assert "dev-boom" in ctx["traceback"]
    finally:
        sys.path[:] = old_sys_path
        _cleanup_demo_modules()
        _dev_session.reset_for_tests()


def test_run_script_executes_project_local_file_and_blocks_escape(tmp_path: Path) -> None:
    from dcc_mcp_maya import _dev_session

    _dev_session.reset_for_tests()
    old_sys_path = sys.path[:]
    script = tmp_path / "scripts" / "check.py"
    script.parent.mkdir()
    script.write_text("import sys\nprint('argv', sys.argv[1:])\nRESULT = 42\n", encoding="utf-8")
    outside = tmp_path.parent / "outside_dev_script.py"
    outside.write_text("print('nope')\n", encoding="utf-8")

    try:
        _dev_session.attach_project(str(tmp_path))
        out = _dev_session.run_script("scripts/check.py", argv=["a", "b"])
        assert out["success"] is True
        assert "argv ['a', 'b']" in out["context"]["stdout"]
        assert "RESULT" in out["context"]["global_names"]

        blocked = _dev_session.run_script(str(outside))
        assert blocked["success"] is False
        assert "outside" in blocked["message"].lower()
    finally:
        try:
            outside.unlink()
        except OSError:
            pass
        sys.path[:] = old_sys_path
        _dev_session.reset_for_tests()


def test_start_debugpy_uses_existing_listener_state(monkeypatch) -> None:
    from dcc_mcp_maya import _dev_session

    _dev_session.reset_for_tests()
    fake = types.ModuleType("debugpy")
    calls = []
    fake.listen = lambda address: calls.append(address)
    fake.wait_for_client = lambda: None
    fake.is_client_connected = lambda: True

    with patch.dict(sys.modules, {"debugpy": fake}):
        first = _dev_session.start_debugpy(port=5679)
        second = _dev_session.start_debugpy(port=9999)

    assert first["success"] is True
    assert first["context"]["port"] == 5679
    assert first["context"]["client_connected"] is True
    assert second["context"]["reused"] is True
    assert calls == [("127.0.0.1", 5679)]


def test_capture_ui_degrades_without_qt() -> None:
    from dcc_mcp_maya import _dev_session

    with patch.object(_dev_session, "_qt_modules", return_value=(None, None, None, None)):
        out = _dev_session.capture_ui()
    assert out["success"] is False
    assert "qt" in out["message"].lower()


def test_maya_dev_scripts_delegate_to_shared_session(tmp_path: Path) -> None:
    from dcc_mcp_maya import _dev_session

    _dev_session.reset_for_tests()
    old_sys_path = sys.path[:]
    _write_demo_package(tmp_path)

    try:
        attach = load_skill_script("maya-dev", "attach_project")
        run = load_skill_script("maya-dev", "run_entrypoint")

        attached = attach.main(project_root=str(tmp_path), package_prefixes=["demo_tool"])
        assert attached["success"] is True
        out = run.main(target="demo_tool.runner:main", kwargs={"x": 3})
        assert out["success"] is True
        assert out["context"]["return_value"]["x"] == 3
    finally:
        sys.path[:] = old_sys_path
        _cleanup_demo_modules()
        _dev_session.reset_for_tests()


def test_maya_dev_tools_yaml_contract() -> None:
    path = Path(__file__).parents[1] / "src" / "dcc_mcp_maya" / "skills" / "maya-dev" / "tools.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    tools = {tool["name"]: tool for tool in data["tools"]}

    expected = {
        "attach_project",
        "reload_modules",
        "run_entrypoint",
        "run_script",
        "start_debugpy",
        "capture_ui",
        "run_check",
    }
    assert set(tools) == expected
    assert tools["capture_ui"]["execution"] == "async"
    assert tools["run_check"]["timeout_hint_secs"] == 300
    assert tools["run_entrypoint"]["affinity"] == "main"
