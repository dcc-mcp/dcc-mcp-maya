"""Real mayapy coverage for the typed animation and rigging vocabulary."""

from __future__ import annotations

import pytest

from ._support import _load_script, _new_scene, cmds

pytestmark = pytest.mark.e2e


def test_batch_keyframes_round_trip_values_tangents_and_infinity():
    _new_scene()
    cmds.polyCube(name="rotorA")
    cmds.polyCube(name="rotorB")
    writer = _load_script("maya-animation", "set_keyframes")
    reader = _load_script("maya-animation", "get_anim_curves")

    written = writer.set_keyframes(
        objects=["rotorA", "rotorB"],
        attribute="rotateY",
        keys=[
            {"time": 1.0, "value": 0.0, "in_tangent": "linear", "out_tangent": "linear"},
            {"time": 24.0, "value": 360.0, "in_tangent": "linear", "out_tangent": "linear"},
        ],
    )
    assert written["success"] is True, written
    assert written["context"]["verified_key_count"] == 4

    readback = reader.get_anim_curves(targets=["rotorA.rotateY", "rotorB.rotateY"])
    assert readback["success"] is True, readback
    assert readback["context"]["curve_count"] == 2
    assert readback["context"]["total_key_count"] == 4
    assert all(curve["key_count"] == 2 for curve in readback["context"]["curves"])
    assert all(curve["keys"][1]["v"] == 360.0 for curve in readback["context"]["curves"])


def test_skin_weights_and_rig_state_round_trip_native_maya_state():
    _new_scene()
    mesh = cmds.polyPlane(name="body_geo", subdivisionsX=1, subdivisionsY=1)[0]
    cmds.select(clear=True)
    root = cmds.joint(name="root_jnt", position=(0.0, 0.0, 0.0))
    tip = cmds.joint(name="tip_jnt", position=(0.0, 1.0, 0.0))
    cluster = cmds.skinCluster([root, tip], mesh, name="bodySkin", toSelectedBones=True)[0]
    control = cmds.circle(name="hand_ctrl")[0]
    cmds.parentConstraint(root, control, maintainOffset=True, name="hand_parentConstraint")

    writer = _load_script("maya-rigging", "set_skin_weights")
    reader = _load_script("maya-rigging", "get_skin_weights")
    exporter = _load_script("maya-rigging", "export_rig_state")
    rows = [
        {
            "vertex": index,
            "weights": [
                {"influence": root, "weight": 1.0 - (index * 0.2)},
                {"influence": tip, "weight": index * 0.2},
            ],
        }
        for index in range(4)
    ]

    written = writer.set_skin_weights(mesh=mesh, skin_cluster=cluster, vertices=rows)
    assert written["success"] is True, written
    assert written["context"]["verified_vertex_count"] == 4

    readback = reader.get_skin_weights(mesh=mesh, skin_cluster=cluster)
    assert readback["success"] is True, readback
    assert readback["context"]["vertex_count"] == 4
    assert readback["context"]["unnormalized_vertices"] == 0

    state = exporter.export_rig_state(
        joints=[root, tip],
        skin_clusters=[cluster],
        controls=[control],
    )
    assert state["success"] is True, state
    assert state["context"]["joints"]["count"] == 2
    assert state["context"]["skins"][0]["unnormalized_vertices"] == 0
    assert state["context"]["controls"]["count"] == 1
