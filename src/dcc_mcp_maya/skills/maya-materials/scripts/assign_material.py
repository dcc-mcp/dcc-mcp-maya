"""Assign a material to one or more objects."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import List

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success

_SUPPORTED_SHADERS = ("lambert", "blinn", "phong", "phongE", "aiStandardSurface")


def assign_material(material_name: str, objects: List[str]) -> dict:
    """Assign a material to one or more objects.

    Args:
        material_name: Name of the shading group **or** the material node.
        objects: List of mesh/transform object names.

    Returns:
        ActionResultModel dict.
    """
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        # Accept either SG or material name
        if cmds.objectType(material_name) != "shadingEngine":
            connections = cmds.listConnections(
                "{}.outColor".format(material_name),
                type="shadingEngine",
            )
            if not connections:
                return maya_error(
                    "No shading group found for '{}'".format(material_name),
                    "Connect material to a shading group first or use assign_material with the SG name",
                )
            sg = connections[0]
        else:
            sg = material_name

        existing = cmds.ls(objects)
        if not existing:
            return maya_error(
                "No objects found",
                "None of the requested objects exist: {}".format(objects),
            )

        cmds.sets(existing, edit=True, forceElement=sg)
        return maya_success(
            "Assigned '{}' to {} object(s)".format(sg, len(existing)),
            shading_group=sg,
            objects=existing,
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to assign material")


def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`assign_material`."""
    return assign_material(**kwargs)


if __name__ == "__main__":
    import json

    result = assign_material()
    print(json.dumps(result))
