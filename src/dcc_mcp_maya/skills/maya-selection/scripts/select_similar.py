"""Select objects with similar topology or material."""

# Import future modules
from __future__ import annotations

from typing import Optional

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

_CRITERIA = ("topology", "material", "type", "name_prefix")


def select_similar(
    criteria: str = "topology",
    prefix: Optional[str] = None,
) -> dict:
    """Select objects similar to the current selection.

    Args:
        criteria: Similarity criterion. One of:
            "topology" — same vertex/edge/face count (default),
            "material"  — same shader assignment,
            "type"      — same Maya node type,
            "name_prefix" — objects sharing the same name prefix (requires ``prefix``).
        prefix: Name prefix when ``criteria="name_prefix"``.

    Returns:
        ActionResultModel dict with ``context.criteria``, ``context.count``.
    """
    if criteria not in _CRITERIA:
        return skill_error(
            "Invalid criteria",
            "'{}' is not valid. Choose from: {}".format(criteria, ", ".join(_CRITERIA)),
        )

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        current = cmds.ls(selection=True) or []
        if not current:
            return skill_error(
                "Nothing selected",
                "Select at least one object before calling select_similar",
                prompt="Use set_selection (maya-scene) to set an initial selection.",
            )

        similar = []

        if criteria == "topology":
            ref_verts = {}
            ref_edges = {}
            ref_faces = {}
            for obj in current:
                shapes = cmds.listRelatives(obj, shapes=True, noIntermediate=True) or []
                for shape in shapes:
                    if cmds.objectType(shape) == "mesh":
                        ref_verts[obj] = cmds.polyEvaluate(shape, vertex=True)
                        ref_edges[obj] = cmds.polyEvaluate(shape, edge=True)
                        ref_faces[obj] = cmds.polyEvaluate(shape, face=True)

            all_meshes = cmds.ls(type="mesh") or []
            for mesh in all_meshes:
                parent = (cmds.listRelatives(mesh, parent=True) or [mesh])[0]
                v = cmds.polyEvaluate(mesh, vertex=True)
                e = cmds.polyEvaluate(mesh, edge=True)
                f = cmds.polyEvaluate(mesh, face=True)
                for obj in current:
                    if (
                        obj in ref_verts
                        and ref_verts[obj] == v
                        and ref_edges[obj] == e
                        and ref_faces[obj] == f
                        and parent not in similar
                    ):
                        similar.append(parent)

        elif criteria == "material":

            def _get_material(obj):
                shapes = cmds.listRelatives(obj, shapes=True, noIntermediate=True) or []
                for shape in shapes:
                    sgs = cmds.listConnections(shape, type="shadingEngine") or []
                    return tuple(sorted(sgs))
                return ()

            ref_mats = set()
            for obj in current:
                ref_mats.update(_get_material(obj))

            for obj in cmds.ls(transforms=True) or []:
                mats = _get_material(obj)
                if any(m in ref_mats for m in mats) and obj not in similar:
                    similar.append(obj)

        elif criteria == "type":
            ref_types = set(cmds.objectType(o) for o in current)
            for obj in cmds.ls() or []:
                if cmds.objectType(obj) in ref_types and obj not in similar:
                    similar.append(obj)

        elif criteria == "name_prefix":
            pfx = prefix or current[0].rstrip("0123456789_")
            similar = [o for o in (cmds.ls() or []) if o.startswith(pfx)]

        if similar:
            cmds.select(similar)

        return skill_success(
            "Selected {} similar object(s) by {}".format(len(similar), criteria),
            prompt="Use get_selection (maya-scene) to inspect the full selection list.",
            criteria=criteria,
            count=len(similar),
            objects=similar,
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to select similar objects")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`select_similar`."""
    return select_similar(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
