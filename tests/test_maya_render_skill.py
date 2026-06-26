"""Unit tests for Maya render skill guard rails."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from conftest import load_and_call, load_and_call_with_mel


def _write_playblast_bytes(data: bytes):
    def _write(**kwargs):
        frame = kwargs["frame"][0]
        path = "{}.{}.png".format(kwargs["filename"], str(frame).zfill(4))
        with open(path, "wb") as fh:
            fh.write(data)
        return path

    return _write


def _configure_render_cmds(cmds, renderer="mayaSoftware", current_frame=1.0):
    prefix_holder = {"prefix": ""}

    def _get_attr(attr):
        values = {
            "defaultRenderGlobals.currentRenderer": renderer,
            "defaultResolution.width": 640,
            "defaultResolution.height": 360,
            "defaultRenderGlobals.imageFormat": 8,
            "defaultRenderGlobals.imageFilePrefix": "",
        }
        return values.get(attr)

    def _set_attr(attr, value, **_kwargs):
        if attr == "defaultRenderGlobals.imageFilePrefix":
            prefix_holder["prefix"] = value

    def _current_time(*_args, **kwargs):
        if kwargs.get("q"):
            return current_frame
        return None

    def _workspace(*_args, **kwargs):
        if kwargs.get("q") and kwargs.get("rootDirectory"):
            return str(Path.cwd())
        if kwargs.get("fileRuleEntry") == "images":
            return "images"
        return None

    cmds.getAttr.side_effect = _get_attr
    cmds.setAttr.side_effect = _set_attr
    cmds.currentTime.side_effect = _current_time
    cmds.workspace.side_effect = _workspace
    cmds.ls.return_value = []
    cmds.objExists.side_effect = lambda node: node == "persp"
    cmds.listRelatives.return_value = ["perspShape"]
    return prefix_holder


def _configure_model_panel(cmds, panel="modelPanel4", renderer="vp2Renderer"):
    def _get_panel(*_args, **kwargs):
        if kwargs.get("withFocus"):
            return panel
        if kwargs.get("typeOf") == panel:
            return "modelPanel"
        if kwargs.get("type") == "modelPanel":
            return [panel]
        if kwargs.get("visiblePanels"):
            return [panel]
        return None

    cmds.getPanel.side_effect = _get_panel
    cmds.modelEditor.return_value = renderer


def test_capture_viewport_forces_offscreen_when_view_fit_fails():
    cmds = MagicMock()
    cmds.currentTime.return_value = 1.0
    _configure_model_panel(cmds)
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
    assert kwargs["editorPanelName"] == "modelPanel4"
    assert result["context"]["viewport_renderer"] == "vp2Renderer"


def test_capture_viewport_reports_zero_byte_playblast():
    cmds = MagicMock()
    cmds.currentTime.return_value = 1.0
    _configure_model_panel(cmds)
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
    assert result["context"]["model_panel"] == "modelPanel4"
    assert result["context"]["viewport_renderer"] == "vp2Renderer"


def test_playblast_reports_zero_byte_output():
    cmds = MagicMock()
    cmds.currentTime.return_value = 1.0
    _configure_model_panel(cmds)
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
    assert result["context"]["model_panel"] == "modelPanel4"


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
    cmds.modelEditor.return_value = "vp2Renderer"
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
    assert context["panel"] == "modelPanel4"
    assert context["viewport_renderer"] == "vp2Renderer"
    _args, playblast_kwargs = cmds.playblast.call_args
    assert playblast_kwargs["editorPanelName"] == "modelPanel4"
    cmds.lookThru.assert_any_call("modelPanel4", "shotCam")
    cmds.lookThru.assert_any_call("modelPanel4", "persp")
    cmds.viewFit.assert_called_once_with("modelPanel4", allObjects=True, animate=False)


def test_render_frame_uses_cmds_render_and_returns_nonempty_file(tmp_path):
    cmds = MagicMock()
    prefix_holder = _configure_render_cmds(cmds, renderer="mayaSoftware", current_frame=12.0)

    def _render(camera, **_kwargs):
        path = "{}.png".format(prefix_holder["prefix"])
        Path(path).write_bytes(b"render-bytes")
        return path

    cmds.render.side_effect = _render

    result = load_and_call(
        "maya-render/scripts/render_frame.py",
        cmds,
        "main",
        output_dir=str(tmp_path),
        output_name="shot 01",
        width=320,
        height=200,
    )

    assert result["success"] is True, result
    context = result["context"]
    assert context["renderer"] == "mayaSoftware"
    assert context["camera"] == "persp"
    assert context["width"] == 320
    assert context["height"] == 200
    assert context["output_size"] == len(b"render-bytes")
    assert context["image_base64"]
    cmds.render.assert_called_once_with("persp", x=320, y=200)
    assert Path(context["output_path"]).name == "shot_01.png"


def test_render_frame_uses_arnold_mel_when_current_renderer_is_arnold(tmp_path):
    cmds = MagicMock()
    mel = MagicMock()
    prefix_holder = _configure_render_cmds(cmds, renderer="arnold", current_frame=1.0)
    cmds.pluginInfo.return_value = True

    def _mel_eval(_command):
        path = "{}.png".format(prefix_holder["prefix"])
        Path(path).write_bytes(b"arnold-bytes")
        return path

    mel.eval.side_effect = _mel_eval

    result = load_and_call_with_mel(
        "maya-render/scripts/render_frame.py",
        cmds,
        mel,
        output_dir=str(tmp_path),
        camera="persp",
        frame=5,
        return_base64=False,
    )

    assert result["success"] is True, result
    assert result["context"]["renderer"] == "arnold"
    assert result["context"]["image_base64"] is None
    mel.eval.assert_called_once_with('arnoldRender -camera "persp" -frame 5.0')


def test_render_frame_rejects_zero_byte_output(tmp_path):
    cmds = MagicMock()
    prefix_holder = _configure_render_cmds(cmds, renderer="mayaSoftware", current_frame=1.0)

    def _render(camera, **_kwargs):
        path = "{}.png".format(prefix_holder["prefix"])
        Path(path).write_bytes(b"")
        return path

    cmds.render.side_effect = _render

    result = load_and_call(
        "maya-render/scripts/render_frame.py",
        cmds,
        "main",
        output_dir=str(tmp_path),
    )

    assert result["success"] is False
    assert result["context"]["error_code"] == "EMPTY_RENDER"
    assert result["context"]["empty_paths"]


def test_playblast_to_mp4_encodes_sequence(tmp_path, monkeypatch):
    cmds = MagicMock()
    _configure_model_panel(cmds)
    cmds.currentTime.return_value = 1.0
    cmds.playbackOptions.side_effect = lambda **kwargs: 1 if kwargs.get("minTime") else 2
    cmds.about.return_value = False

    def _playblast(**kwargs):
        prefix = kwargs["filename"]
        for frame in range(kwargs["startTime"], kwargs["endTime"] + 1):
            Path("{}.{:04d}.png".format(prefix, frame)).write_bytes(b"frame")

    def _run(command, stdout, stderr, text):
        Path(command[-1]).write_bytes(b"mp4")
        completed = MagicMock()
        completed.returncode = 0
        completed.stdout = ""
        completed.stderr = ""
        return completed

    cmds.playblast.side_effect = _playblast
    monkeypatch.setattr("shutil.which", lambda name: "ffmpeg" if name == "ffmpeg" else None)
    monkeypatch.setattr("subprocess.run", _run)

    result = load_and_call(
        "maya-render/scripts/playblast_to_mp4.py",
        cmds,
        "main",
        output_dir=str(tmp_path),
        prefix="anim preview",
        keep_frames=True,
    )

    assert result["success"] is True, result
    context = result["context"]
    assert Path(context["output_path"]).exists()
    assert context["frame_count"] == 2
    assert context["panel"] == "modelPanel4"
    assert context["viewport_renderer"] == "vp2Renderer"
    _args, playblast_kwargs = cmds.playblast.call_args
    assert playblast_kwargs["editorPanelName"] == "modelPanel4"


def test_debug_scene_snapshot_returns_summary_without_preview():
    cmds = MagicMock()
    cmds.ls.side_effect = lambda **kwargs: {
        "transform": ["|root", "|root|meshA"],
        "camera": ["perspShape"],
        "mesh": ["meshAShape"],
        "light": [],
        "directionalLight": [],
        "pointLight": [],
        "spotLight": [],
        "areaLight": [],
        "aiSkyDomeLight": [],
    }.get(kwargs.get("type"), [])
    cmds.objectType.side_effect = lambda node: "transform"
    cmds.listRelatives.side_effect = lambda node, **kwargs: (
        ["|root"] if kwargs.get("parent") and node != "|root" else []
    )
    cmds.getAttr.return_value = True
    cmds.file.return_value = "scene.ma"

    result = load_and_call(
        "maya-render/scripts/debug_scene_snapshot.py",
        cmds,
        "main",
        include_preview=False,
        include_ui=False,
        max_nodes=1,
    )

    assert result["success"] is True, result
    summary = result["context"]["scene_summary"]
    assert summary["transform_count"] == 2
    assert summary["mesh_count"] == 1
    assert summary["truncated"] is True
    assert result["context"]["preview"] is None
