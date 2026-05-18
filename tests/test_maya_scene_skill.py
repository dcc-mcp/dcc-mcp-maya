"""Unit tests for the maya-scene skill."""

from __future__ import annotations

from unittest.mock import MagicMock

from conftest import load_and_call


def test_save_scene_without_path_rejects_unnamed_scene_before_prompt():
    cmds = MagicMock()
    cmds.file.return_value = ""

    result = load_and_call("maya-scene/scripts/save_scene.py", cmds, "main")

    assert result["success"] is False
    assert "file_path" in result["message"]
    cmds.file.assert_called_once_with(query=True, sceneName=True)
