"""Unit tests for generic maya-node-graph node tools."""

from __future__ import annotations

from unittest.mock import MagicMock

from conftest import load_and_call


def _node_summary_mock(cmds: MagicMock, long_name: str = "|utility1", uuid: str = "uuid-utility1") -> None:
    def _ls(*args, **kwargs):
        if kwargs.get("uuid"):
            return [uuid]
        if kwargs.get("long"):
            return [long_name]
        return [str(args[0])] if args else []

    def _get_attr(plug):
        if plug.endswith(".translate"):
            return [(0.0, 0.0, 0.0)]
        if plug.endswith(".rotate"):
            return [(0.0, 0.0, 0.0)]
        if plug.endswith(".scale"):
            return [(1.0, 1.0, 1.0)]
        if plug.endswith(".visibility"):
            return True
        if plug.endswith(".input1X"):
            return 2.0
        if plug.endswith(".outputX"):
            return 4.0
        return None

    cmds.ls.side_effect = _ls
    cmds.objExists.return_value = True
    cmds.nodeType.return_value = "multiplyDivide"
    cmds.objectType.return_value = "multiplyDivide"
    cmds.listRelatives.return_value = []
    cmds.getAttr.side_effect = _get_attr
    cmds.exactWorldBoundingBox.return_value = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    cmds.file.return_value = "C:/show/scene.ma"


def test_create_node_uses_create_node_and_returns_summary():
    cmds = MagicMock()
    cmds.createNode.return_value = "utility1"
    _node_summary_mock(cmds)

    result = load_and_call(
        "maya-node-graph/scripts/create_node.py",
        cmds,
        "main",
        node_type="multiplyDivide",
        name="utility1",
        skip_select=True,
    )

    assert result["success"] is True, result
    cmds.createNode.assert_called_once_with(
        "multiplyDivide",
        skipSelect=True,
        shared=False,
        name="utility1",
    )
    assert result["context"]["node_name"] == "utility1"
    assert result["context"]["node"]["node_ref"]["uuid"] == "uuid-utility1"


def test_describe_node_can_include_attributes_and_connections():
    cmds = MagicMock()
    _node_summary_mock(cmds)
    cmds.listAttr.return_value = ["input1X", "outputX"]
    cmds.listConnections.return_value = ["utility1.outputX", "target.inputX"]

    result = load_and_call(
        "maya-node-graph/scripts/describe_node.py",
        cmds,
        "main",
        node_name="utility1",
        include_attributes=True,
        include_connections=True,
    )

    assert result["success"] is True, result
    assert result["context"]["attributes"][0]["plug"] == "utility1.input1X"
    assert result["context"]["connections"] == [{"plug": "utility1.outputX", "connected_plug": "target.inputX"}]


def test_delete_node_deletes_generic_nodes():
    cmds = MagicMock()
    cmds.objExists.return_value = True

    result = load_and_call(
        "maya-node-graph/scripts/delete_node.py",
        cmds,
        "main",
        nodes=["utility1", "utility2"],
    )

    assert result["success"] is True, result
    cmds.delete.assert_called_once_with(["utility1", "utility2"])
    assert result["context"]["count"] == 2
