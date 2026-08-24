"""Create a polygon mesh by revolving one bounded NURBS profile."""

from __future__ import annotations

from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya._mutation import MayaUndoChunk, node_uuid, uuid_inventory


def _shape_of_type(cmds, node, node_type):
    # type: (...) -> Optional[str]
    shapes = cmds.listRelatives(node, shapes=True, noIntermediate=True, fullPath=True) or []
    for shape in shapes:
        if cmds.objectType(shape) == node_type:
            return str(shape)
    if cmds.objectType(node) == node_type:
        return str(node)
    return None


def lathe_profile(
    profile,  # type: str
    name=None,  # type: Optional[str]
    axis="y",  # type: str
    segments=16,  # type: int
    sweep_angle=360.0,  # type: float
    degree=3,  # type: int
):
    # type: (...) -> dict
    """Revolve a NURBS curve profile into a verified polygon mesh."""
    if not isinstance(profile, str) or not profile:
        return skill_error("Invalid lathe profile", "profile must be a non-empty Maya node name")
    if axis not in ("x", "y", "z"):
        return skill_error("Invalid lathe axis", "axis must be one of 'x', 'y', or 'z'", axis=axis)
    if isinstance(segments, bool) or not isinstance(segments, int) or not 3 <= segments <= 256:
        return skill_error("Invalid lathe segments", "segments must be an integer from 3 through 256")
    if isinstance(sweep_angle, bool) or not isinstance(sweep_angle, (int, float)) or not 0 < sweep_angle <= 360:
        return skill_error("Invalid lathe sweep", "sweep_angle must be greater than 0 and at most 360")
    if degree not in (1, 3):
        return skill_error("Invalid lathe degree", "degree must be 1 or 3", degree=degree)
    if name is not None and (not isinstance(name, str) or not name):
        return skill_error("Invalid output name", "name must be a non-empty string when provided")

    transaction = None
    before_uuids = None
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        profile_shape = _shape_of_type(cmds, profile, "nurbsCurve") if cmds.objExists(profile) else None
        if profile_shape is None:
            return skill_error(
                "Lathe profile is unavailable",
                "profile must resolve to an existing NURBS curve",
                profile=profile,
            )
        profile_shape_uuid = node_uuid(cmds, profile_shape)

        axis_vector = {"x": (1.0, 0.0, 0.0), "y": (0.0, 1.0, 0.0), "z": (0.0, 0.0, 1.0)}[axis]
        before_uuids = uuid_inventory(cmds)
        transaction = MayaUndoChunk(cmds, "dcc_mcp_lathe_profile")
        transaction.begin()
        result = cmds.revolve(
            profile,
            polygon=1,
            constructionHistory=True,
            axis=axis_vector,
            sections=segments,
            endSweep=float(sweep_angle),
            degree=degree,
        )
        if not result:
            receipt = transaction.rollback(lambda: uuid_inventory(cmds) == before_uuids)
            return skill_error("Lathe produced no result", "maya.cmds.revolve returned no nodes", **receipt)

        object_name = str(result[0])
        if name:
            object_name = str(cmds.rename(object_name, name))
        shape = _shape_of_type(cmds, object_name, "mesh")
        history_node = str(result[1]) if len(result) > 1 else None
        if not cmds.objExists(object_name) or shape is None or history_node is None:
            receipt = transaction.rollback(lambda: uuid_inventory(cmds) == before_uuids)
            return skill_error(
                "Lathe result verification failed",
                "The result must resolve to a polygon mesh with construction history",
                object_name=object_name,
                **receipt,
            )

        object_uuid = node_uuid(cmds, object_name)
        shape_uuid = node_uuid(cmds, shape)
        history_uuid = node_uuid(cmds, history_node)
        result_uuids = {object_uuid, shape_uuid, history_uuid}
        history_nodes = cmds.listHistory(object_name) or []
        history_uuids = {node_uuid(cmds, node) for node in history_nodes}
        upstream_nodes = cmds.listConnections(history_node, source=True, destination=False, shapes=True) or []
        upstream_uuids = {node_uuid(cmds, node) for node in upstream_nodes}
        if (
            len(result_uuids) != 3
            or bool(result_uuids & before_uuids)
            or history_uuid not in history_uuids
            or profile_shape_uuid not in upstream_uuids
        ):
            receipt = transaction.rollback(lambda: uuid_inventory(cmds) == before_uuids)
            return skill_error(
                "Lathe provenance verification failed",
                "Maya did not prove new transform, mesh, history, and profile ownership",
                object_name=object_name,
                **receipt,
            )

        transaction.commit()
        return skill_success(
            "Lathed '{}' into '{}'".format(profile, object_name),
            object_name=object_name,
            object_uuid=object_uuid,
            shape=shape,
            shape_uuid=shape_uuid,
            profile=profile,
            axis=axis,
            segments=segments,
            sweep_angle=float(sweep_angle),
            history_node=history_node,
            history_uuid=history_uuid,
            prompt="Use set_pivot, auto_uv, or assign_material to continue the modeling workflow.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        receipt = {}
        if transaction is not None and before_uuids is not None:
            receipt = transaction.rollback(lambda: uuid_inventory(cmds) == before_uuids)
        return skill_exception(exc, message="Failed to lathe polygon profile", **receipt)


@skill_entry
def main(**kwargs):
    # type: (...) -> dict
    """Entry point; delegates to :func:`lathe_profile`."""
    return lathe_profile(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
