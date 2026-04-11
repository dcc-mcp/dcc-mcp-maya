"""Create a wire deformer that deforms meshes along one or more NURBS curves."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import List, Optional

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya.api import batch_validate_nodes


def wire_deformer(
    curves: List[str],
    objects: List[str],
    name: Optional[str] = None,
    dropoff_distance: float = 100.0,
) -> dict:
    """Create a wire deformer that deforms meshes along one or more NURBS curves.

    Args:
        curves: List of NURBS curve names to use as wire wires.
        objects: List of mesh/surface names to deform.
        name: Optional name for the wire deformer node.
        dropoff_distance: Distance at which the wire influence falls off to
            zero.  Default: ``100.0``.

    Returns:
        ActionResultModel dict with ``context.wire_node``,
        ``context.curves``, ``context.objects``.
    """
    if not curves:
        return skill_error(
            "No curves specified",
            "Provide at least one NURBS curve name in 'curves'",
        )
    if not objects:
        return skill_error(
            "No objects specified",
            "Provide at least one mesh name in 'objects'",
        )

    try:
        import maya.cmds as cmds  # noqa: PLC0415


        err = batch_validate_nodes(cmds, list(curves))
        if err:
            return err

        err = batch_validate_nodes(cmds, list(objects))
        if err:
            return err

        wire_kwargs = {
            "wire": curves,
            "dropoffDistance": [(i, dropoff_distance) for i in range(len(curves))],
        }
        if name:
            wire_kwargs["name"] = name

        result = cmds.wire(objects, **wire_kwargs)
        wire_node = result[0] if result else None

        return skill_success(
            "Created wire deformer '{}' on {} object(s)".format(wire_node, len(objects)),
            wire_node=wire_node,
            curves=list(curves),
            objects=list(objects),
            dropoff_distance=dropoff_distance,
            prompt="Check the result with list_deformers or use related actions to continue.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to create wire deformer")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`wire_deformer`."""
    return wire_deformer(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main
    run_main(main)
