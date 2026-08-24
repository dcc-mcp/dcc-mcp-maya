"""Create a polygon mesh by lofting bounded NURBS curve sections."""

from __future__ import annotations

from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya._mutation import MayaUndoChunk, node_uuid, uuid_inventory

_MAX_SECTIONS = 64


def _curve_shape(cmds, node):
    # type: (...) -> Optional[str]
    shapes = cmds.listRelatives(node, shapes=True, noIntermediate=True, fullPath=True) or []
    for shape in shapes:
        if cmds.objectType(shape) == "nurbsCurve":
            return str(shape)
    if cmds.objectType(node) == "nurbsCurve":
        return str(node)
    return None


def _mesh_shape(cmds, node):
    # type: (...) -> Optional[str]
    shapes = cmds.listRelatives(node, shapes=True, noIntermediate=True, fullPath=True) or []
    for shape in shapes:
        if cmds.objectType(shape) == "mesh":
            return str(shape)
    return None


def loft_sections(
    sections,  # type: List[str]
    name=None,  # type: Optional[str]
    degree=3,  # type: int
    close=False,  # type: bool
):
    # type: (...) -> dict
    """Loft two to 64 curve sections into a polygon mesh."""
    if not isinstance(sections, list) or not 2 <= len(sections) <= _MAX_SECTIONS:
        return skill_error(
            "Invalid loft sections",
            "sections must contain between 2 and {} curve names".format(_MAX_SECTIONS),
            sections=sections,
        )
    if any(not isinstance(section, str) or not section for section in sections):
        return skill_error("Invalid loft sections", "Every section must be a non-empty string")
    if len(set(sections)) != len(sections):
        return skill_error("Invalid loft sections", "sections must not contain duplicate curve names")
    if degree not in (1, 3):
        return skill_error("Invalid loft degree", "degree must be 1 or 3", degree=degree)
    if name is not None and (not isinstance(name, str) or not name):
        return skill_error("Invalid output name", "name must be a non-empty string when provided")

    transaction = None
    before_uuids = None
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        invalid = []
        section_shape_uuids = set()
        for section in sections:
            shape = _curve_shape(cmds, section) if cmds.objExists(section) else None
            if shape is None:
                invalid.append(section)
            else:
                section_shape_uuids.add(node_uuid(cmds, shape))
        if invalid:
            return skill_error(
                "Loft sections are unavailable",
                "Every section must resolve to an existing NURBS curve",
                invalid_sections=invalid,
            )

        before_uuids = uuid_inventory(cmds)
        transaction = MayaUndoChunk(cmds, "dcc_mcp_loft_sections")
        transaction.begin()
        result = cmds.loft(
            *sections,
            polygon=1,
            constructionHistory=True,
            uniform=True,
            close=bool(close),
            autoReverse=True,
            degree=degree,
            sectionSpans=1,
        )
        if not result:
            receipt = transaction.rollback(lambda: uuid_inventory(cmds) == before_uuids)
            return skill_error("Loft produced no result", "maya.cmds.loft returned no nodes", **receipt)

        object_name = str(result[0])
        if name:
            object_name = str(cmds.rename(object_name, name))
        shape = _mesh_shape(cmds, object_name)
        history_node = str(result[1]) if len(result) > 1 else None
        if not cmds.objExists(object_name) or shape is None or history_node is None:
            receipt = transaction.rollback(lambda: uuid_inventory(cmds) == before_uuids)
            return skill_error(
                "Loft result verification failed",
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
            or not section_shape_uuids.issubset(upstream_uuids)
        ):
            receipt = transaction.rollback(lambda: uuid_inventory(cmds) == before_uuids)
            return skill_error(
                "Loft provenance verification failed",
                "Maya did not prove new transform, mesh, history, and input-section ownership",
                object_name=object_name,
                **receipt,
            )

        transaction.commit()
        return skill_success(
            "Lofted {} sections into '{}'".format(len(sections), object_name),
            object_name=object_name,
            object_uuid=object_uuid,
            shape=shape,
            shape_uuid=shape_uuid,
            input_sections=list(sections),
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
        return skill_exception(exc, message="Failed to loft polygon sections", **receipt)


@skill_entry
def main(**kwargs):
    # type: (...) -> dict
    """Entry point; delegates to :func:`loft_sections`."""
    return loft_sections(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
