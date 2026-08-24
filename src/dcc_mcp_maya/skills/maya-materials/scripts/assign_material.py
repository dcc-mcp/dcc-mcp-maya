"""Assign a material to one or more objects."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import List

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

_SUPPORTED_SHADERS = ("lambert", "blinn", "phong", "phongE", "aiStandardSurface")
_MAX_OBJECTS = 256


def assign_material(material_name: str, objects: List[str]) -> dict:
    """Assign a material to one or more objects.

    Args:
        material_name: Name of the shading group **or** the material node.
        objects: List of mesh/transform object names.

    Returns:
        ToolResult dict.
    """
    if isinstance(objects, str):
        objects = [objects]
    if not isinstance(objects, list) or not objects or len(objects) > _MAX_OBJECTS:
        return skill_error(
            "Invalid material targets",
            "objects must contain between 1 and {} Maya node names".format(_MAX_OBJECTS),
        )
    if any(not isinstance(item, str) or not item for item in objects):
        return skill_error("Invalid material targets", "Every object must be a non-empty string")

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(material_name):
            return skill_error(
                "Material not found",
                "'{}' does not exist".format(material_name),
                material_name=material_name,
            )
        missing_objects = [item for item in objects if not cmds.objExists(item)]
        if missing_objects:
            return skill_error(
                "Material targets not found",
                "Every requested object must exist before assignment",
                missing_objects=missing_objects,
            )

        # Accept either SG or material name
        if cmds.objectType(material_name) != "shadingEngine":
            connections = cmds.listConnections(
                "{}.outColor".format(material_name),
                type="shadingEngine",
            )
            if not connections:
                return skill_error(
                    "No shading group found for '{}'".format(material_name),
                    "Connect material to a shading group first or use assign_material with the SG name",
                )
            sg = connections[0]
        else:
            sg = material_name

        existing = cmds.ls(objects)
        if not existing:
            return skill_error(
                "No objects found",
                "None of the requested objects exist: {}".format(objects),
            )

        cmds.sets(existing, edit=True, forceElement=sg)
        verified_objects = []
        unverified_objects = []
        for item in existing:
            assigned = bool(cmds.sets(item, isMember=sg))
            if not assigned:
                shapes = cmds.listRelatives(item, shapes=True, noIntermediate=True, fullPath=True) or []
                assigned = bool(shapes) and all(bool(cmds.sets(shape, isMember=sg)) for shape in shapes)
            if assigned:
                verified_objects.append(str(item))
            else:
                unverified_objects.append(str(item))

        if unverified_objects:
            return skill_error(
                "Material assignment verification failed",
                "Maya set membership does not include every requested object",
                shading_group=sg,
                verified_objects=verified_objects,
                unverified_objects=unverified_objects,
            )
        return skill_success(
            "Assigned '{}' to {} object(s)".format(sg, len(existing)),
            shading_group=sg,
            objects=existing,
            verified_objects=verified_objects,
            verified_count=len(verified_objects),
            prompt="Use set_material_attribute to fine-tune the material properties.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to assign material")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`assign_material`."""
    return assign_material(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
