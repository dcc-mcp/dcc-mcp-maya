"""Create a Maya dynamic field and optionally connect it to objects."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import List, Optional

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya.api import batch_validate_nodes

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


def create_dynamic_field(
    field_type: str = "gravity",
    name: Optional[str] = None,
    magnitude: float = 9.8,
    objects: Optional[List[str]] = None,
) -> dict:
    """Create a Maya dynamic field and optionally connect it to objects.

    Supported field types: ``gravity``, ``turbulence``, ``radial``,
    ``uniform``, ``vortex``, ``drag``, ``newton``, ``air``.

    Args:
        field_type: Type of dynamic field to create.  Default: ``"gravity"``.
        name: Optional name for the field node.  Maya auto-names if ``None``.
        magnitude: Field strength/magnitude.  Default: ``9.8``.
        objects: Optional list of particle/nParticle system names to connect
            the field to via ``cmds.connectDynamic(fields=...)``.

    Returns:
        ToolResult dict with ``context.field_node``,
        ``context.field_type``, ``context.magnitude``.
    """
    ft = field_type.lower()
    if ft not in _VALID_FIELD_TYPES:
        return skill_error(
            "Invalid field type: {}".format(field_type),
            "Supported types: {}".format(", ".join(_VALID_FIELD_TYPES)),
        )

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        create_fn = getattr(cmds, ft, None)
        if create_fn is None:
            return skill_error(
                "Field type not available: {}".format(ft),
                "cmds.{} is not accessible in this Maya version".format(ft),
            )

        field_kwargs = {}
        if name:
            field_kwargs["name"] = name

        result = create_fn(**field_kwargs)
        field_node = result[0] if isinstance(result, (list, tuple)) else result

        # Set magnitude
        mag_attr = "{}.magnitude".format(field_node)
        if cmds.objExists(mag_attr):
            cmds.setAttr(mag_attr, magnitude)

        # Connect to particle systems
        connected = []
        if objects:
            err = batch_validate_nodes(cmds, list(objects))
            if err:
                return err
            cmds.connectDynamic(objects, fields=field_node)
            connected = list(objects)

        return skill_success(
            "Created {} field '{}'".format(ft, field_node),
            field_node=field_node,
            field_type=ft,
            magnitude=magnitude,
            connected_objects=connected,
            prompt="Check the result with list_dynamics or use related actions to continue.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to create dynamic field")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`create_dynamic_field`."""
    return create_dynamic_field(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
