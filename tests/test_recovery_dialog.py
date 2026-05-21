"""Tests for Qt-level Maya recovery dialog detection (issue #241)."""

from __future__ import annotations

# Import local modules
from dcc_mcp_maya import _recovery_dialog


class _FakeButton:
    def __init__(self, text: str) -> None:
        self._text = text
        self.clicked = 0

    def text(self) -> str:
        return self._text

    def click(self) -> None:
        self.clicked += 1


class _FakeWidget:
    def __init__(self, title: str, visible: bool = True, buttons=None) -> None:
        self._title = title
        self._visible = visible
        self._buttons = list(buttons or [])
        self.accepted = False
        self.closed = False

    def windowTitle(self) -> str:
        return self._title

    def isVisible(self) -> bool:
        return self._visible

    def findChildren(self, _cls=object):
        return list(self._buttons)

    def accept(self) -> None:
        self.accepted = True

    def close(self) -> None:
        self.closed = True


def setup_function() -> None:
    _recovery_dialog.reset_for_tests()


def teardown_function() -> None:
    _recovery_dialog.reset_for_tests()


def test_scan_detects_visible_english_recovery_dialog() -> None:
    widget = _FakeWidget("Maya has stopped working - recovering your file")

    event = _recovery_dialog.scan_recovery_dialog(qt_widgets=[widget], auto_dismiss=False)

    assert event["detected"] is True
    assert event["active"] is True
    assert event["status"] == "recovery_dialog_detected"
    status = _recovery_dialog.current_recovery_status()
    assert status["maya_recovered"] is True
    assert status["maya_status"] == "recovery_dialog_detected"
    assert status["maya_recovery_dialog"]["title"] == "Maya has stopped working - recovering your file"


def test_scan_detects_visible_chinese_recovery_dialog() -> None:
    widget = _FakeWidget("Maya 已停止工作 - 正在恢复文件")

    event = _recovery_dialog.scan_recovery_dialog(qt_widgets=[widget], auto_dismiss=False)

    assert event["detected"] is True
    assert event["title"] == "Maya 已停止工作 - 正在恢复文件"


def test_scan_ignores_hidden_or_unrelated_windows() -> None:
    hidden = _FakeWidget("Maya has stopped working", visible=False)
    unrelated = _FakeWidget("Maya Preferences")

    event = _recovery_dialog.scan_recovery_dialog(qt_widgets=[hidden, unrelated], auto_dismiss=False)

    assert event["detected"] is False
    assert event["status"] == "ok"
    assert _recovery_dialog.current_recovery_status() == {}


def test_auto_dismiss_clicks_matching_dialog_button(monkeypatch) -> None:
    monkeypatch.setenv(_recovery_dialog.ENV_AUTO_DISMISS_CRASH_DIALOG, "1")
    button = _FakeButton("Reopen")
    widget = _FakeWidget("Maya crash recovery", buttons=[button])

    event = _recovery_dialog.scan_recovery_dialog(qt_widgets=[widget])

    assert event["detected"] is True
    assert event["dismissal_attempted"] is True
    assert event["dismissed"] is True
    assert event["active"] is False
    assert event["status"] == "recovered"
    assert button.clicked == 1


def test_auto_dismiss_falls_back_to_accept_when_button_missing() -> None:
    widget = _FakeWidget("Maya has stopped working")

    event = _recovery_dialog.scan_recovery_dialog(qt_widgets=[widget], auto_dismiss=True)

    assert event["dismissed"] is True
    assert widget.accepted is True


def test_next_poll_marks_previous_active_dialog_recovered_when_cleared() -> None:
    widget = _FakeWidget("Maya has stopped working")
    _recovery_dialog.scan_recovery_dialog(qt_widgets=[widget], auto_dismiss=False)

    event = _recovery_dialog.scan_recovery_dialog(qt_widgets=[], auto_dismiss=False)

    assert event["detected"] is False
    assert event["active"] is False
    assert event["status"] == "recovered"
    assert _recovery_dialog.current_recovery_status()["maya_status"] == "recovered"


def test_poll_and_annotate_result_adds_recovery_context() -> None:
    widget = _FakeWidget("Maya has stopped working")
    result = {"success": True, "message": "ok", "context": {"existing": "kept"}}

    out = _recovery_dialog.poll_and_annotate_result(result, qt_widgets=[widget], auto_dismiss=False)

    assert out is not result
    assert out["context"]["existing"] == "kept"
    assert out["context"]["maya_recovered"] is True
    assert out["context"]["maya_status"] == "recovery_dialog_detected"
    assert out["context"]["maya_recovery_dialog"]["active"] is True
