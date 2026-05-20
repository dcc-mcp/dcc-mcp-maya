"""Unit tests for the maya-dev skill.

These tests run without a live Maya session.  They pin the development
workflow pieces that are pure Python: project attachment, module purge,
entrypoint/script execution, debugpy bootstrap, and graceful UI-capture
degradation when Qt/Maya is absent.
"""

from __future__ import annotations

import builtins
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


class _Rect:
    def __init__(self, x: int = 0, y: int = 0, width: int = 100, height: int = 24) -> None:
        self._x = x
        self._y = y
        self._width = width
        self._height = height

    def x(self) -> int:
        return self._x

    def y(self) -> int:
        return self._y

    def width(self) -> int:
        return self._width

    def height(self) -> int:
        return self._height


class _FakeWidget:
    def __init__(
        self,
        object_name: str = "",
        text: str = "",
        title: str = "",
        tooltip: str = "",
        children: list["_FakeWidget"] | None = None,
    ) -> None:
        self._object_name = object_name
        self._text = text
        self._title = title
        self._tooltip = tooltip
        self._children = children or []
        self._visible = True
        self._enabled = True
        self._focused = False

    def objectName(self) -> str:
        return self._object_name

    def text(self) -> str:
        return self._text

    def windowTitle(self) -> str:
        return self._title

    def toolTip(self) -> str:
        return self._tooltip

    def isVisible(self) -> bool:
        return self._visible

    def isEnabled(self) -> bool:
        return self._enabled

    def isWindow(self) -> bool:
        return bool(self._title)

    def geometry(self) -> _Rect:
        return _Rect()

    def children(self) -> list["_FakeWidget"]:
        return list(self._children)

    def findChildren(self, _widget_type):
        found = []
        stack = list(self._children)
        while stack:
            child = stack.pop(0)
            found.append(child)
            stack.extend(child.children())
        return found

    def findChild(self, _widget_type, object_name: str):
        for child in self.findChildren(_widget_type):
            if child.objectName() == object_name:
                return child
        return None

    def setFocus(self) -> None:
        self._focused = True


class _FakeButton(_FakeWidget):
    def __init__(self, object_name: str, text: str) -> None:
        super().__init__(object_name=object_name, text=text)
        self.clicked = 0

    def click(self) -> None:
        self.clicked += 1


class _FakeLineEdit(_FakeWidget):
    def setText(self, value: str) -> None:
        self._text = value


class _FakeComboBox(_FakeWidget):
    def __init__(self, object_name: str, options: list[str], current_index: int = 0) -> None:
        super().__init__(object_name=object_name, text=options[current_index] if options else "")
        self._options = options
        self._current_index = current_index

    def findText(self, value: str) -> int:
        try:
            return self._options.index(value)
        except ValueError:
            return -1

    def setCurrentIndex(self, index: int) -> None:
        if 0 <= index < len(self._options):
            self._current_index = index
            self._text = self._options[index]

    def setCurrentText(self, value: str) -> None:
        index = self.findText(value)
        if index >= 0:
            self.setCurrentIndex(index)

    def currentText(self) -> str:
        if 0 <= self._current_index < len(self._options):
            return self._options[self._current_index]
        return ""


def _fake_ui_tree():
    save = _FakeButton("saveButton", "Save")
    name = _FakeLineEdit("nameEdit", "Old")
    root = _FakeWidget("mainWindow", title="Maya", children=[save, name])
    return root, save, name


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


def test_start_debugpy_reports_optional_missing_debugpy(monkeypatch) -> None:
    from dcc_mcp_maya import _dev_session

    _dev_session.reset_for_tests()
    real_import = builtins.__import__

    def _import(name, *args, **kwargs):
        if name == "debugpy":
            raise ImportError("debugpy intentionally unavailable")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _import)
    out = _dev_session.start_debugpy(port=5682)

    assert out["success"] is False
    assert out["context"]["error_code"] == "debugpy_missing"
    assert "optional" in out["context"]["debug_session"]["setup_instructions"]
    assert "stronger breakpoint debugging" in out["error"]


def test_start_debugpy_returns_core_metadata_and_logging(tmp_path: Path) -> None:
    from dcc_mcp_maya import _dev_session

    _dev_session.reset_for_tests()
    fake = types.ModuleType("debugpy")
    calls = {"listen": [], "configure": [], "log_to": []}
    fake.listen = lambda address: calls["listen"].append(address)
    fake.wait_for_client = lambda: None
    fake.is_client_connected = lambda: False
    fake.configure = lambda **kwargs: calls["configure"].append(kwargs)
    fake.log_to = lambda path: calls["log_to"].append(path)

    log_dir = tmp_path / "debugpy-logs"
    with patch.dict(sys.modules, {"debugpy": fake}):
        out = _dev_session.start_debugpy(
            port=5680,
            python_executable=str(tmp_path / "mayapy.exe"),
            log_dir=str(log_dir),
            path_mappings=[{"local_root": str(tmp_path), "remote_root": str(tmp_path)}],
        )

    assert out["success"] is True
    ctx = out["context"]
    assert ctx["listening"] is True
    assert ctx["debug_session"]["debugger_kind"] == "debugpy"
    assert ctx["debug_session"]["status"] == "listening"
    assert ctx["debug_session"]["path_mappings"][0]["local_root"] == str(tmp_path)
    assert calls["listen"] == [("127.0.0.1", 5680)]
    assert calls["configure"] == [{"python": str(tmp_path / "mayapy.exe")}]
    assert calls["log_to"] == [str(log_dir)]


def test_start_debugpy_classifies_port_in_use() -> None:
    from dcc_mcp_maya import _dev_session

    _dev_session.reset_for_tests()
    fake = types.ModuleType("debugpy")

    def _listen(_address):
        raise RuntimeError("Address already in use")

    fake.listen = _listen
    fake.configure = lambda **_kwargs: None
    fake.is_client_connected = lambda: False

    with patch.dict(sys.modules, {"debugpy": fake}):
        out = _dev_session.start_debugpy(port=5681)

    assert out["success"] is False
    assert out["context"]["error_code"] == "port_in_use"


def test_capture_ui_degrades_without_qt() -> None:
    from dcc_mcp_maya import _dev_session

    with patch.object(_dev_session, "_qt_modules", return_value=(None, None, None, None)):
        out = _dev_session.capture_ui()
    assert out["success"] is False
    assert "qt" in out["message"].lower()


def test_ui_snapshot_find_and_action_with_fake_qt() -> None:
    from dcc_mcp_maya import _dev_session

    _dev_session.reset_for_tests()
    root, save, name = _fake_ui_tree()
    with patch.object(_dev_session, "_maya_main_window", return_value=(root, _FakeWidget, None)):
        snapshot = _dev_session.ui_snapshot(max_depth=3)
        found = _dev_session.ui_find(label="save")
        control_id = found["context"]["matches"][0]["id"]
        clicked = _dev_session.ui_action(action="click", control_id=control_id)
        edited = _dev_session.ui_action(action="set_text", object_name="nameEdit", text="New")

    assert snapshot["success"] is True
    assert snapshot["context"]["snapshot"]["node_count"] == 3
    assert found["success"] is True
    assert found["context"]["match_count"] == 1
    assert clicked["success"] is True
    assert save.clicked == 1
    assert edited["success"] is True
    assert name.text() == "New"
    assert edited["context"]["control"]["object_name"] == "nameEdit"


def test_ui_action_select_option_validates_missing_options() -> None:
    from dcc_mcp_maya import _dev_session

    _dev_session.reset_for_tests()
    combo = _FakeComboBox("modeCombo", ["Draft", "Final"])
    root = _FakeWidget("mainWindow", title="Maya", children=[combo])
    with patch.object(_dev_session, "_maya_main_window", return_value=(root, _FakeWidget, None)):
        selected = _dev_session.ui_action(action="select_option", object_name="modeCombo", option="Final")
        missing = _dev_session.ui_action(action="select_option", object_name="modeCombo", option="Missing")

    assert selected["success"] is True
    assert combo.currentText() == "Final"
    assert missing["success"] is False
    assert missing["context"]["error_code"] == "unsupported_action"
    assert "not found" in missing["error"].lower()
    assert combo.currentText() == "Final"


def test_ui_action_requires_unique_locator() -> None:
    from dcc_mcp_maya import _dev_session

    _dev_session.reset_for_tests()
    root = _FakeWidget(
        "mainWindow",
        title="Maya",
        children=[_FakeButton("saveOne", "Save"), _FakeButton("saveTwo", "Save")],
    )
    with patch.object(_dev_session, "_maya_main_window", return_value=(root, _FakeWidget, None)):
        out = _dev_session.ui_action(action="click", label="Save")

    assert out["success"] is False
    assert out["context"]["error_code"] == "ambiguous_control"


def test_run_check_writes_artifact_refs_for_large_output(tmp_path: Path) -> None:
    from dcc_mcp_maya import _dev_session

    _dev_session.reset_for_tests()
    old_sys_path = sys.path[:]
    _cleanup_demo_modules()
    _write_demo_package(tmp_path)
    (tmp_path / "demo_tool" / "runner.py").write_text(
        "def main():\n    print('x' * 20)\n    return 'ok'\n",
        encoding="utf-8",
    )

    try:
        with patch.dict("os.environ", {"DCC_MCP_MAYA_DEV_ARTIFACT_DIR": str(tmp_path / "artifacts")}):
            _dev_session.attach_project(str(tmp_path), package_prefixes=["demo_tool"])
            out = _dev_session.run_check(target="demo_tool.runner:main", artifact_threshold=4)
    finally:
        sys.path[:] = old_sys_path
        _cleanup_demo_modules()
        _dev_session.reset_for_tests()

    assert out["success"] is True
    artifacts = out["context"]["artifacts"]
    assert artifacts
    assert artifacts[0]["kind"] == "stdout"
    assert Path(artifacts[0]["path"]).exists()
    assert out["context"]["run_summary"]["artifact_count"] == 1


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
        "ui_snapshot",
        "ui_find",
        "ui_action",
        "make_node_ref",
        "resolve_node_ref",
        "run_check",
    }
    assert set(tools) == expected
    assert tools["capture_ui"]["execution"] == "async"
    assert tools["ui_snapshot"]["annotations"]["read_only_hint"] is True
    assert tools["ui_action"]["affinity"] == "main"
    assert tools["make_node_ref"]["annotations"]["read_only_hint"] is True
    assert tools["run_check"]["timeout_hint_secs"] == 300
    assert tools["run_entrypoint"]["affinity"] == "main"
