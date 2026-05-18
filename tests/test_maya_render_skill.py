"""Unit tests for Maya render skill guard rails."""

from __future__ import annotations

from unittest.mock import MagicMock

from conftest import load_and_call


def _write_playblast_bytes(data: bytes):
    def _write(**kwargs):
        frame = kwargs["frame"][0]
        path = "{}.{}.png".format(kwargs["filename"], str(frame).zfill(4))
        with open(path, "wb") as fh:
            fh.write(data)
        return path

    return _write


def test_capture_viewport_forces_offscreen_when_view_fit_fails():
    cmds = MagicMock()
    cmds.currentTime.return_value = 1.0
    cmds.viewFit.side_effect = RuntimeError("no usable panel")
    cmds.playblast.side_effect = _write_playblast_bytes(b"png-bytes")

    result = load_and_call(
        "maya-render/scripts/capture_viewport.py",
        cmds,
        "main",
        width=320,
        height=200,
        view_fit=True,
        off_screen=False,
    )

    assert result["success"] is True, result
    assert result["context"]["off_screen"] is True
    assert result["context"]["view_fit_applied"] is False
    assert result["context"]["off_screen_forced_by_view_fit_failure"] is True
    _args, kwargs = cmds.playblast.call_args
    assert kwargs["offScreen"] is True


def test_capture_viewport_reports_zero_byte_playblast():
    cmds = MagicMock()
    cmds.currentTime.return_value = 1.0
    cmds.playblast.side_effect = _write_playblast_bytes(b"")

    result = load_and_call(
        "maya-render/scripts/capture_viewport.py",
        cmds,
        "main",
        width=320,
        height=200,
    )

    assert result["success"] is False
    assert "0-byte" in result["message"] or "0-byte" in result["error"]


def test_playblast_reports_zero_byte_output():
    cmds = MagicMock()
    cmds.currentTime.return_value = 1.0
    cmds.playblast.side_effect = _write_playblast_bytes(b"")

    result = load_and_call(
        "maya-render/scripts/playblast.py",
        cmds,
        "main",
        width=320,
        height=200,
    )

    assert result["success"] is False
    assert "0-byte" in result["message"] or "0-byte" in result["error"]
