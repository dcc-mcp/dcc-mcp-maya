"""Color preferences reported by successful frame renders."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest
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


@pytest.mark.parametrize("initial_renderable", [False, True])
@pytest.mark.parametrize("render_fails", [False, True])
@pytest.mark.parametrize("full_camera_path", [False, True])
def test_render_frame_temporarily_enables_selected_camera(tmp_path, initial_renderable, render_fails, full_camera_path):
    cmds = MagicMock()
    prefix = _configure_render_cmds(cmds)
    get_attr, set_attr = cmds.getAttr.side_effect, cmds.setAttr.side_effect
    state = {"renderable": initial_renderable, "other": True}
    selected = "|rig|perspShape" if full_camera_path else "perspShape"
    cmds.ls.side_effect = lambda *args, **kwargs: (
        [selected] if args else [selected if kwargs.get("long") else "perspShape", "otherShape"]
    )
    if full_camera_path:
        cmds.objExists.return_value = True
        cmds.objExists.side_effect = None
        cmds.nodeType.return_value = "camera"
        cmds.listRelatives.return_value = ["|rig|persp"]
    observed = []

    def get_value(attr):
        if attr == "otherShape.renderable":
            return state["other"]
        return (
            state["renderable"] if attr in ("perspShape.renderable", "|rig|perspShape.renderable") else get_attr(attr)
        )

    def set_value(attr, value, **kwargs):
        if attr == "otherShape.renderable":
            state["other"] = value
        elif attr in ("perspShape.renderable", "|rig|perspShape.renderable"):
            if full_camera_path and initial_renderable and not value:
                raise RuntimeError("selected renderable camera is locked")
            state["renderable"] = value
        else:
            set_attr(attr, value, **kwargs)

    def render(*_args, **_kwargs):
        observed.append((state["renderable"], state["other"]))
        assert state["renderable"] is True and state["other"] is False
        if render_fails:
            raise RuntimeError("native render failed")
        path = Path(prefix["prefix"] + ".png")
        path.write_bytes(b"rendered-image")
        return str(path)

    cmds.getAttr.side_effect, cmds.setAttr.side_effect = get_value, set_value
    cmds.render.side_effect = render
    result = load_and_call(
        "maya-render/scripts/render_frame.py",
        cmds,
        "main",
        camera="|rig|perspShape" if full_camera_path else "persp",
        output_dir=str(tmp_path),
        return_base64=False,
    )
    assert result["success"] is not render_fails, result
    assert observed == [(True, False)]
    assert state == {"renderable": initial_renderable, "other": True}


def test_render_frame_uses_maya_path_separators(tmp_path):
    cmds = MagicMock()
    prefix = _configure_render_cmds(cmds)

    def render(*_args, **_kwargs):
        assert "\\" not in prefix["prefix"]
        path = Path(prefix["prefix"] + ".png")
        path.write_bytes(b"rendered-image")
        return str(path)

    cmds.render.side_effect = render
    result = load_and_call(
        "maya-render/scripts/render_frame.py", cmds, "main", output_dir=str(tmp_path), return_base64=False
    )
    assert result["success"], result


def test_render_frame_preserves_full_transform_with_duplicate_shape_names(tmp_path):
    cmds = MagicMock()
    prefix = _configure_render_cmds(cmds)
    selected, other = "|shot|camera|sharedShape", "|other|camera|sharedShape"
    cmds.objExists.side_effect = None
    cmds.objExists.return_value = True
    cmds.nodeType.return_value = "transform"
    cmds.listRelatives.side_effect = lambda *args, **kwargs: [selected if kwargs.get("fullPath") else "sharedShape"]
    cmds.ls.side_effect = lambda *args, **kwargs: list(args) if args else [other, selected]
    state = {selected + ".renderable": True, other + ".renderable": True}
    get_attr, set_attr = cmds.getAttr.side_effect, cmds.setAttr.side_effect
    cmds.getAttr.side_effect = lambda attr: state[attr] if attr in state else get_attr(attr)

    def update(attr, value, **kwargs):
        if attr in state:
            state[attr] = value
        else:
            set_attr(attr, value, **kwargs)

    def render(*args, **kwargs):
        assert state == {selected + ".renderable": True, other + ".renderable": False}
        path = Path(prefix["prefix"] + ".png")
        path.write_bytes(b"rendered-image")
        return str(path)

    cmds.setAttr.side_effect, cmds.render.side_effect = update, render
    result = load_and_call(
        "maya-render/scripts/render_frame.py",
        cmds,
        "main",
        camera="|shot|camera",
        output_dir=str(tmp_path),
        return_base64=False,
    )
    assert result["success"], result
    assert state == {selected + ".renderable": True, other + ".renderable": True}


def test_render_frame_rejects_ambiguous_camera_shape(tmp_path):
    cmds = MagicMock()
    _configure_render_cmds(cmds)
    cmds.objExists.side_effect = None
    cmds.objExists.return_value = True
    cmds.nodeType.side_effect = RuntimeError("More than one object matches name")
    cmds.ls.side_effect = lambda *args, **kwargs: ["|shot|sharedShape", "|other|sharedShape"]
    result = load_and_call(
        "maya-render/scripts/render_frame.py", cmds, "main", camera="sharedShape", output_dir=str(tmp_path)
    )
    assert not result["success"]
    assert result["context"]["camera_source"] == "ambiguous"
    cmds.nodeType.assert_not_called()
    cmds.render.assert_not_called()


def test_render_frame_refuses_unisolatable_camera_and_restores_preparation(tmp_path):
    cmds = MagicMock()
    _configure_render_cmds(cmds)
    initial = {"otherShape.renderable": True, "lockedShape.renderable": True, "perspShape.renderable": False}
    state = dict(initial)
    get_attr, set_attr = cmds.getAttr.side_effect, cmds.setAttr.side_effect
    cmds.ls.side_effect = lambda *args, **kwargs: list(args) if args else ["otherShape", "lockedShape", "perspShape"]
    cmds.getAttr.side_effect = lambda attr: state[attr] if attr in state else get_attr(attr)

    def update(attr, value, **kwargs):
        if attr == "lockedShape.renderable":
            raise RuntimeError("referenced camera is locked")
        if attr in state:
            state[attr] = value
        else:
            set_attr(attr, value, **kwargs)

    cmds.setAttr.side_effect = update
    result = load_and_call(
        "maya-render/scripts/render_frame.py",
        cmds,
        "main",
        camera="persp",
        output_dir=str(tmp_path),
        return_base64=False,
    )
    assert not result["success"]
    assert result["context"]["error_code"] == "CAMERA_RENDERABLE_UPDATE_FAILED"
    assert state == initial
    cmds.render.assert_not_called()
