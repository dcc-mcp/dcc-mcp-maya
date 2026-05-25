"""Unit tests for Maya render skill guard rails."""

from __future__ import annotations

from pathlib import Path
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


def test_get_viewport_camera_prefers_focused_model_panel():
    cmds = MagicMock()

    def _get_panel(*_args, **kwargs):
        if kwargs.get("withFocus"):
            return "modelPanel4"
        if kwargs.get("typeOf") == "modelPanel4":
            return "modelPanel"
        if kwargs.get("type") == "modelPanel":
            return ["modelPanel4"]
        if kwargs.get("visiblePanels"):
            return ["modelPanel4"]
        return None

    cmds.getPanel.side_effect = _get_panel
    cmds.modelPanel.return_value = "persp"
    cmds.ls.return_value = ["perspShape"]
    cmds.nodeType.side_effect = lambda node: "camera" if node == "perspShape" else "transform"
    cmds.listRelatives.side_effect = lambda node, **kwargs: (
        ["perspShape"] if kwargs.get("shapes") else ["persp"] if kwargs.get("parent") else []
    )
    cmds.objExists.return_value = True
    cmds.getAttr.return_value = 35.0

    result = load_and_call("maya-render/scripts/get_viewport_camera.py", cmds, "main")

    assert result["success"] is True, result
    assert result["context"]["camera"] == "persp"
    assert result["context"]["camera_shape"] == "perspShape"
    assert result["context"]["panel"] == "modelPanel4"
    assert result["context"]["source"] == "focused_model_panel"


def test_capture_playblast_sequence_writes_paths_and_camera_metadata(tmp_path):
    cmds = MagicMock()

    def _get_panel(*_args, **kwargs):
        if kwargs.get("withFocus"):
            return "modelPanel4"
        if kwargs.get("typeOf") == "modelPanel4":
            return "modelPanel"
        if kwargs.get("type") == "modelPanel":
            return ["modelPanel4"]
        if kwargs.get("visiblePanels"):
            return ["modelPanel4"]
        return None

    def _playblast(**kwargs):
        prefix = kwargs["filename"]
        compression = kwargs["compression"]
        for frame in range(kwargs["startTime"], kwargs["endTime"] + 1):
            Path("{}.{}.{}".format(prefix, str(frame).zfill(4), compression)).write_bytes(b"png")

    cmds.getPanel.side_effect = _get_panel
    cmds.modelPanel.return_value = "persp"
    cmds.about.return_value = False
    cmds.playblast.side_effect = _playblast
    cmds.nodeType.side_effect = lambda node: "camera" if node == "shotCamShape" else "transform"
    cmds.listRelatives.return_value = ["shotCamShape"]
    cmds.objExists.return_value = True
    cmds.getAttr.return_value = 50.0

    result = load_and_call(
        "maya-render/scripts/capture_playblast_sequence.py",
        cmds,
        "main",
        output_dir=str(tmp_path),
        prefix="shot 01",
        start_frame=1,
        end_frame=3,
        width=640,
        height=360,
        camera="shotCam",
        view_fit=True,
    )

    assert result["success"] is True, result
    context = result["context"]
    assert context["prefix"] == "shot_01"
    assert context["frame_count"] == 3
    assert len(context["files"]) == 3
    assert all(Path(path).exists() for path in context["files"])
    assert context["camera"] == "shotCam"
    assert context["camera_metadata"]["camera_shape"] == "shotCamShape"
    cmds.lookThru.assert_any_call("modelPanel4", "shotCam")
    cmds.lookThru.assert_any_call("modelPanel4", "persp")
    cmds.viewFit.assert_called_once_with("modelPanel4", allObjects=True, animate=False)
