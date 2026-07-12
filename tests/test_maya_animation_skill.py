"""Unit tests for the maya-animation skill."""

from __future__ import annotations

from unittest.mock import MagicMock

from conftest import load_and_call


def test_export_animation_curves_clears_with_an_empty_selection(tmp_path):
    output_path = tmp_path / "walk.ma"
    cmds = MagicMock()
    cmds.objExists.return_value = True
    cmds.listConnections.return_value = ["walk_curve"]

    result = load_and_call(
        "maya-animation/scripts/export_animation_curves.py",
        cmds,
        object_name="root_ctrl",
        file_path=str(output_path),
    )

    assert result["success"] is True, result
    assert cmds.select.call_args_list[-1].args == ([],)
    assert cmds.select.call_args_list[-1].kwargs == {"clear": True}


def test_import_animation_curves_disables_maya_import_prompts(tmp_path):
    anim_path = tmp_path / "walk.anim"
    anim_path.write_text("anim")
    cmds = MagicMock()

    result = load_and_call("maya-animation/scripts/import_animation_curves.py", cmds, "main", file_path=str(anim_path))

    assert result["success"] is True, result
    args, kwargs = cmds.file.call_args
    assert args[0] == str(anim_path)
    assert kwargs["i"] is True
    assert kwargs["force"] is True
    assert kwargs["prompt"] is False
