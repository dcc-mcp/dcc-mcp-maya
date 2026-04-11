"""Select all objects in the scene that use a given material."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success


def select_by_material(material_name: str) -> dict:
    """Select all objects in the scene that use a given material.

    Looks up the shading group(s) associated with *material_name*, then
    queries the group members to find polygon mesh transforms.

    Args:
        material_name: Name of the material (shader) node, e.g.
            ``"lambert1"``, ``"blinn1"``, ``"aiStandardSurface1"``.

    Returns:
        ActionResultModel dict with ``context.objects`` (list of selected
        object names), ``context.count``, ``context.material``.
    """
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(material_name):
            return maya_error(
                "Material not found: {}".format(material_name),
                "'{}' does not exist in the scene".format(material_name),
            )

        # Find all shading engines connected to this material
        shading_engines = (
            cmds.listConnections(material_name, type="shadingEngine", source=False, destination=True) or []
        )

        if not shading_engines:
            return maya_success(
                "Material '{}' is not assigned to any objects".format(material_name),
                objects=[],
                count=0,
                material=material_name,
            )

        # Collect all mesh members from shading groups
        objects = []
        seen = set()
        for sg in shading_engines:
            members = cmds.sets(sg, query=True) or []
            for member in members:
                # member can be a transform or a component (face assignment)
                node = member.split(".")[0] if "." in member else member
                if node in seen:
                    continue
                seen.add(node)
                # Resolve to transform
                node_type = cmds.objectType(node)
                if node_type == "mesh":
                    parents = cmds.listRelatives(node, parent=True, fullPath=False) or []
                    transform = parents[0] if parents else node
                elif node_type == "transform":
                    transform = node
                else:
                    continue
                if transform not in objects:
                    objects.append(transform)

        if objects:
            cmds.select(objects, replace=True)

        return maya_success(
            "Selected {} object(s) with material '{}'".format(len(objects), material_name),
            objects=objects,
            count=len(objects),
            material=material_name,
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to select by material")


def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`select_by_material`."""
    return select_by_material(**kwargs)


if __name__ == "__main__":
    import json

    result = select_by_material()
    print(json.dumps(result))
