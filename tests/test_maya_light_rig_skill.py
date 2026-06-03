"""Unit tests for maya-light-rig skill scripts."""

from __future__ import annotations

from unittest.mock import MagicMock

from conftest import load_and_call


def test_create_light_returns_transform_and_shape_without_directional_command():
    cmds = MagicMock()

    def _create_node(node_type, **kwargs):
        if node_type == "transform":
            return kwargs["name"]
        return kwargs["name"]

    cmds.createNode.side_effect = _create_node

    result = load_and_call(
        "maya-light-rig/scripts/create_light.py",
        cmds,
        "main",
        name="key_light",
        light_type="directionalLight",
        intensity=2.0,
        color=[1.0, 0.9, 0.8],
        position=[1, 2, 3],
        rotation=[10, 20, 30],
    )

    assert result["success"] is True, result
    assert result["context"]["transform"] == "key_light"
    assert result["context"]["shape"] == "key_lightShape"
    cmds.createNode.assert_any_call("transform", name="key_light")
    cmds.createNode.assert_any_call("directionalLight", name="key_lightShape", parent="key_light")
    cmds.setAttr.assert_any_call("key_light.translate", 1.0, 2.0, 3.0, type="double3")
    cmds.setAttr.assert_any_call("key_light.rotate", 10.0, 20.0, 30.0, type="double3")
    assert not cmds.directionalLight.called


def test_create_light_rejects_unsupported_light_type():
    cmds = MagicMock()

    result = load_and_call(
        "maya-light-rig/scripts/create_light.py",
        cmds,
        "main",
        name="badLight",
        light_type="unsupportedLight",
    )

    assert result["success"] is False
    assert "Unsupported" in result["message"]
    cmds.createNode.assert_not_called()
