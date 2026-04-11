"""Connect an existing dynamic field to particle/nCloth/nParticle objects."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import List

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya.api import validate_node_exists

_VALID_FIELD_TYPES = (
    "gravity",
    "turbulence",
    "radial",
    "uniform",
    "vortex",
    "drag",
    "newton",
    "air",
)

_VALID_MIRROR_AXES = ("x", "y", "z")


def connect_field_to_objects(
    field_node: str,
    objects: List[str],
) -> dict:
    """Connect an existing dynamic field to particle/nCloth/nParticle objects.

    Uses ``cmds.connectDynamic(fields=field_node)`` to wire the field
    forces to the given dynamic objects.

    Args:
        field_node: Name of the existing dynamic field node (or its
            transform).
        objects: List of dynamic object names (particle, nParticle,
            nCloth, nRigid) to receive the field influence.

    Returns:
        ActionResultModel dict with ``context.field_node`` and
        ``context.connected_objects``.
    """
    if not objects:
        return skill_error(
            "No objects specified",
            "Provide at least one dynamic object name",
        )

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        err = validate_node_exists(cmds, field_node)
        if err:
            return err

        missing = [o for o in objects if not cmds.objExists(o)]
        if missing:
            return skill_error(
                "Object(s) not found: {}".format(", ".join(missing)),
                "Ensure all objects exist before connecting the field",
            )

        cmds.connectDynamic(objects, fields=field_node)

        return skill_success(
            "Connected field '{}' to {} object(s)".format(field_node, len(objects)),
            field_node=field_node,
            connected_objects=list(objects),
            prompt="Check the result with list_dynamics or use related actions to continue.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to connect field '{}' to objects".format(field_node))


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`connect_field_to_objects`."""
    return connect_field_to_objects(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main
    run_main(main)
