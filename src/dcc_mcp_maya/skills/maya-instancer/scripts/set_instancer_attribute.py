"""Configure per-particle instancer attributes (rotation, scale, visibility, objectIndex)."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import Optional

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success

# Mapping of friendly names to Maya instancer attribute fields
ATTRIBUTE_MAP = {
    "position": "position",
    "rotation": "aimDirection",
    "scale": "generalScale",
    "visibility": "visibility",
    "object_index": "objectIndex",
    "age": "age",
    "age_normalized": "ageNormalized",
}


def set_instancer_attribute(
    particle_system: str,
    instancer_node: str,
    attribute: str,
    particle_attribute: Optional[str] = None,
) -> dict:
    """Map a per-particle attribute to an instancer field.

    Connects a per-particle attribute (e.g. ``nParticle1.rotationPP``) to one
    of the instancer's data fields so particles vary in rotation, scale, etc.

    Args:
        particle_system: Particle system transform name.
        instancer_node: Target instancer node name.
        attribute: Instancer field to configure.  One of: ``position``,
            ``rotation``, ``scale``, ``visibility``, ``object_index``, ``age``,
            ``age_normalized``.
        particle_attribute: Name of the per-particle attribute on the particle
            shape to connect.  Pass ``None`` to clear the mapping.

    Returns:
        ActionResultModel dict with ``context.instancer_node``,
        ``context.attribute``, and ``context.particle_attribute``.
    """
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        for name in (particle_system, instancer_node):
            if not cmds.objExists(name):
                return maya_error(
                    "Node not found: {}".format(name),
                    "'{}' does not exist".format(name),
                )

        if attribute not in ATTRIBUTE_MAP:
            return maya_error(
                "Unknown attribute: {}".format(attribute),
                "Choose from: {}".format(", ".join(sorted(ATTRIBUTE_MAP.keys()))),
            )

        instancer_field = ATTRIBUTE_MAP[attribute]
        edit_kwargs = {
            "edit": True,
            "name": instancer_node,
            instancer_field: particle_attribute or "",
        }
        cmds.particleInstancer(particle_system, **edit_kwargs)

        return maya_success(
            "Set instancer '{}' field '{}' → '{}'".format(
                instancer_node, instancer_field, particle_attribute or "(cleared)"
            ),
            prompt="Verify by playing the simulation. Use list_instancers to see all configured fields.",
            instancer_node=instancer_node,
            attribute=instancer_field,
            particle_attribute=particle_attribute,
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to set instancer attribute")


def main(**kwargs):
    return set_instancer_attribute(**kwargs)


if __name__ == "__main__":
    import json

    result = set_instancer_attribute("nParticle1", "instancer1", "object_index", "objectIndexPP")
    print(json.dumps(result, indent=2))
