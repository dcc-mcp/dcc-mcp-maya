"""Color preferences reported by successful frame renders."""

from pathlib import Path
from unittest.mock import MagicMock

from conftest import load_and_call
from test_maya_render_skill import _configure_render_cmds


def test_render_frame_reports_actual_configured_view_transform(tmp_path):
    cmds = MagicMock()
    prefix = _configure_render_cmds(cmds)
    cmds.colorManagementPrefs.return_value = "Un-tone-mapped (sRGB)"

    def render(*_args, **_kwargs):
        path = Path(prefix["prefix"] + ".png")
        path.write_bytes(b"rendered-image")
        return str(path)

    cmds.render.side_effect = render
    result = load_and_call(
        "maya-render/scripts/render_frame.py", cmds, "main", output_dir=str(tmp_path), return_base64=False
    )

    assert result["success"] is True, result
    assert result["context"]["view_transform"] == "Un-tone-mapped (sRGB)"
    cmds.colorManagementPrefs.assert_called_once_with(query=True, viewTransformName=True)


def test_render_frame_retains_image_when_color_preferences_are_unavailable(tmp_path):
    cmds = MagicMock()
    prefix = _configure_render_cmds(cmds)
    cmds.colorManagementPrefs.side_effect = RuntimeError("Color management is not initialized")

    def render(*_args, **_kwargs):
        path = Path(prefix["prefix"] + ".png")
        path.write_bytes(b"rendered-image")
        return str(path)

    cmds.render.side_effect = render
    result = load_and_call(
        "maya-render/scripts/render_frame.py", cmds, "main", output_dir=str(tmp_path), return_base64=False
    )

    assert result["success"] is True, result
    context = result["context"]
    assert Path(context["output_path"]).read_bytes() == b"rendered-image"
    assert context["view_transform"] is None
    assert context["color_management_error"] == "Color management is not initialized"


def test_render_frame_keeps_unavailable_arnold_as_a_render_failure(tmp_path):
    cmds = MagicMock()
    _configure_render_cmds(cmds, renderer="arnold")
    cmds.pluginInfo.return_value = False

    result = load_and_call(
        "maya-render/scripts/render_frame.py", cmds, "main", output_dir=str(tmp_path), return_base64=False
    )

    assert result["success"] is False
    assert "MtoA is not loaded" in result["message"]
    cmds.colorManagementPrefs.assert_not_called()
    cmds.render.assert_not_called()
