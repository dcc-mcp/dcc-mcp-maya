"""Unit tests for the maya-scene skill."""

from __future__ import annotations

from unittest.mock import MagicMock

from conftest import load_and_call


def _scene_node_summary_mock(cmds: MagicMock, long_name: str = "|shotCam", uuid: str = "uuid-shotCam") -> None:
    def _ls(*args, **kwargs):
        if kwargs.get("uuid"):
            return [uuid]
        if kwargs.get("long"):
            return [long_name]
        return [str(args[0])] if args else []

    def _get_attr(plug):
        if plug.endswith(".translate"):
            return [(1.0, 2.0, 3.0)]
        if plug.endswith(".rotate"):
            return [(0.0, 0.0, 0.0)]
        if plug.endswith(".scale"):
            return [(1.0, 1.0, 1.0)]
        if plug.endswith(".visibility"):
            return True
        return 35.0

    cmds.ls.side_effect = _ls
    cmds.objExists.return_value = True
    cmds.nodeType.side_effect = lambda node: "camera" if str(node).endswith("Shape") else "transform"
    cmds.objectType.return_value = "transform"
    cmds.getAttr.side_effect = _get_attr
    cmds.exactWorldBoundingBox.return_value = [-1.0, -1.0, -1.0, 1.0, 1.0, 1.0]
    cmds.file.return_value = "C:/show/scene.ma"


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


def test_create_camera_sets_transform_shape_attrs_and_optional_aim():
    cmds = MagicMock()
    cmds.camera.return_value = ["camera1", "cameraShape1"]
    cmds.rename.return_value = "shotCam"
    cmds.listRelatives.side_effect = lambda node, **kwargs: ["shotCamShape"] if kwargs.get("shapes") else []
    cmds.spaceLocator.return_value = ["shotCam_look_at_tmp"]
    cmds.aimConstraint.return_value = ["aimConstraint1"]
    _scene_node_summary_mock(cmds)

    result = load_and_call(
        "maya-scene/scripts/create_camera.py",
        cmds,
        "main",
        name="shotCam",
        position=[1, 2, 3],
        look_at=[0, 1, 0],
        focal_length=50,
        renderable=True,
    )

    assert result["success"] is True, result
    assert result["context"]["camera"] == "shotCam"
    assert result["context"]["camera_shape"] == "shotCamShape"
    cmds.xform.assert_any_call("shotCam", worldSpace=True, translation=[1.0, 2.0, 3.0])
    cmds.aimConstraint.assert_called_once()
    cmds.setAttr.assert_any_call("shotCamShape.focalLength", 50.0)
    cmds.setAttr.assert_any_call("shotCamShape.renderable", True)


def test_set_camera_updates_transform_and_shape_attrs():
    cmds = MagicMock()
    cmds.listRelatives.side_effect = lambda node, **kwargs: ["shotCamShape"] if kwargs.get("shapes") else []
    _scene_node_summary_mock(cmds)

    result = load_and_call(
        "maya-scene/scripts/set_camera.py",
        cmds,
        "main",
        camera="shotCam",
        position=[4, 5, 6],
        rotation=[10, 20, 30],
        focal_length=70,
        orthographic=False,
    )

    assert result["success"] is True, result
    assert result["context"]["updates"]["focal_length"] == 70
    cmds.xform.assert_any_call("shotCam", worldSpace=True, translation=[4.0, 5.0, 6.0])
    cmds.xform.assert_any_call("shotCam", worldSpace=True, rotation=[10.0, 20.0, 30.0])
    cmds.setAttr.assert_any_call("shotCamShape.focalLength", 70)


def test_look_through_camera_uses_focused_panel_and_view_fit():
    cmds = MagicMock()
    cmds.objExists.return_value = True

    def _get_panel(*_args, **kwargs):
        if kwargs.get("withFocus"):
            return "modelPanel4"
        if kwargs.get("typeOf") == "modelPanel4":
            return "modelPanel"
        return None

    cmds.getPanel.side_effect = _get_panel
    cmds.modelPanel.return_value = "persp"

    result = load_and_call(
        "maya-scene/scripts/look_through_camera.py",
        cmds,
        "main",
        camera="shotCam",
        view_fit=True,
    )

    assert result["success"] is True, result
    cmds.lookThru.assert_called_once_with("modelPanel4", "shotCam")
    cmds.viewFit.assert_called_once_with("modelPanel4", allObjects=True, animate=False)
    assert result["context"]["previous_camera"] == "persp"
