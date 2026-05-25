"""Unit tests for the maya-dynamics skill."""

from __future__ import annotations

from unittest.mock import MagicMock

from conftest import load_and_call


def test_make_rigid_body_uses_active_rigid_body_flags():
    cmds = MagicMock()
    cmds.objExists.return_value = True
    cmds.rigidBody.return_value = "rigidBody1"

    result = load_and_call(
        "maya-dynamics/scripts/make_rigid_body.py",
        cmds,
        "main",
        objects=["pCube1"],
        mode="active",
        name_prefix="hero_rb",
        mass=3.0,
        bounciness=0.75,
        damping=0.1,
        static_friction=0.4,
        dynamic_friction=0.25,
        collisions=True,
    )

    assert result["success"] is True, result
    cmds.rigidBody.assert_called_once_with(
        "pCube1",
        mass=3.0,
        bounciness=0.75,
        damping=0.1,
        staticFriction=0.4,
        dynamicFriction=0.25,
        collisions=True,
        active=True,
        name="hero_rb",
    )
    assert result["context"]["rigid_bodies"] == ["rigidBody1"]


def test_make_rigid_body_can_create_passive_bodies_from_selection():
    cmds = MagicMock()
    cmds.ls.return_value = ["floor"]
    cmds.objExists.return_value = True
    cmds.rigidBody.return_value = "floorRigidBody"

    result = load_and_call(
        "maya-dynamics/scripts/make_rigid_body.py",
        cmds,
        "main",
        mode="passive",
    )

    assert result["success"] is True, result
    _args, kwargs = cmds.rigidBody.call_args
    assert kwargs["passive"] is True
    assert "active" not in kwargs


def test_create_gravity_field_connects_targets():
    cmds = MagicMock()
    cmds.objExists.return_value = True
    cmds.gravity.return_value = ["gravity1", "gravityField1"]
    cmds.nodeType.side_effect = lambda node: "gravityField" if node == "gravityField1" else "transform"

    result = load_and_call(
        "maya-dynamics/scripts/create_gravity_field.py",
        cmds,
        "main",
        name="shotGravity",
        targets=["pCube1"],
        direction=[0.0, -1.0, 0.0],
        magnitude=9.8,
    )

    assert result["success"] is True, result
    cmds.gravity.assert_called_once_with(
        name="shotGravity",
        magnitude=9.8,
        attenuation=0.0,
        directionX=0.0,
        directionY=-1.0,
        directionZ=0.0,
    )
    cmds.connectDynamic.assert_called_once_with(["pCube1"], fields="gravityField1")
    assert result["context"]["field"] == "gravityField1"


def test_connect_dynamic_field_disconnects_when_requested():
    cmds = MagicMock()
    cmds.objExists.return_value = True

    result = load_and_call(
        "maya-dynamics/scripts/connect_dynamic_field.py",
        cmds,
        "main",
        targets="pCube1",
        field="gravityField1",
        disconnect=True,
    )

    assert result["success"] is True, result
    cmds.connectDynamic.assert_called_once_with(["pCube1"], fields="gravityField1", delete=True)
    assert result["context"]["disconnected"] is True


def test_set_rigid_body_properties_edits_only_provided_values():
    cmds = MagicMock()
    cmds.objExists.return_value = True

    result = load_and_call(
        "maya-dynamics/scripts/set_rigid_body_properties.py",
        cmds,
        "main",
        rigid_bodies=["rigidBody1"],
        mass=5.0,
        collisions=False,
    )

    assert result["success"] is True, result
    cmds.rigidBody.assert_called_once_with("rigidBody1", edit=True, mass=5.0, collisions=False)
    assert result["context"]["updates"] == {"mass": 5.0, "collisions": False}


def test_list_dynamics_summarizes_rigid_bodies_fields_and_constraints():
    cmds = MagicMock()

    def _ls(*_args, **kwargs):
        by_type = {
            "rigidBody": ["rigidBody1"],
            "gravityField": ["gravityField1"],
            "rigidConstraint": ["rigidConstraint1"],
        }
        return by_type.get(kwargs.get("type"), [])

    def _get_attr(plug):
        values = {
            "rigidBody1.mass": 2.5,
            "rigidBody1.bounciness": 0.8,
            "gravityField1.magnitude": 9.8,
            "gravityField1.directionY": -1.0,
        }
        return values.get(plug)

    cmds.ls.side_effect = _ls
    cmds.objExists.return_value = True
    cmds.nodeType.side_effect = lambda node: {
        "rigidBody1": "rigidBody",
        "gravityField1": "gravityField",
        "rigidConstraint1": "rigidConstraint",
    }.get(node, "transform")
    cmds.getAttr.side_effect = _get_attr
    cmds.listConnections.return_value = ["pCube1"]

    result = load_and_call(
        "maya-dynamics/scripts/list_dynamics.py",
        cmds,
        "main",
    )

    assert result["success"] is True, result
    assert result["context"]["counts"] == {"rigid_bodies": 1, "fields": 1, "constraints": 1}
    assert result["context"]["rigid_bodies"][0]["attrs"]["mass"] == 2.5
    assert result["context"]["fields"][0]["attrs"]["magnitude"] == 9.8
