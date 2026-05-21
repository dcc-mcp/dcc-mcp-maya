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


def test_get_scene_info_includes_node_refs():
    cmds = MagicMock()

    def _ls(*args, **kwargs):
        if kwargs.get("type") == "transform" and kwargs.get("long"):
            return ["|pCube1"]
        if kwargs.get("uuid"):
            return ["uuid-pCube1"]
        if kwargs.get("long"):
            return [str(args[0])]
        return [str(args[0])] if args else []

    def _get_attr(attr):
        if attr.endswith(".translate"):
            return [(1.0, 2.0, 3.0)]
        if attr.endswith(".rotate"):
            return [(0.0, 0.0, 0.0)]
        if attr.endswith(".scale"):
            return [(1.0, 1.0, 1.0)]
        if attr.endswith(".visibility"):
            return True
        return [(0.0, 0.0, 0.0)]

    cmds.ls.side_effect = _ls
    cmds.nodeType.return_value = "transform"
    cmds.objectType.return_value = "transform"
    cmds.objExists.return_value = True
    cmds.file.return_value = "C:/show/scene.ma"
    cmds.getAttr.side_effect = _get_attr
    cmds.listRelatives.return_value = []

    result = load_and_call("maya-scene/scripts/get_scene_info.py", cmds, "main")

    assert result["success"] is True
    node = result["context"]["nodes"][0]
    assert node["node_ref"]["uuid"] == "uuid-pCube1"
    assert node["node_ref"]["long_name"] == "|pCube1"
    assert node["node_ref"]["metadata"]["scene_path"] == "C:/show/scene.ma"
