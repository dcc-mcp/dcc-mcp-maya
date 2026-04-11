"""Create a wire deformer that deforms meshes along one or more NURBS curves."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import List, Optional

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success


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
        return maya_error(
            "No curves specified",
            "Provide at least one NURBS curve name in 'curves'",
        )
    if not objects:
        return maya_error(
            "No objects specified",
            "Provide at least one mesh name in 'objects'",
        )

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        missing_curves = [c for c in curves if not cmds.objExists(c)]
        if missing_curves:
            return maya_error(
                "Curve(s) not found: {}".format(", ".join(missing_curves)),
                "Ensure all curves exist in the scene",
            )

        missing_objects = [o for o in objects if not cmds.objExists(o)]
        if missing_objects:
            return maya_error(
                "Object(s) not found: {}".format(", ".join(missing_objects)),
                "Ensure all objects exist in the scene",
            )

        wire_kwargs = {
            "wire": curves,
            "dropoffDistance": [(i, dropoff_distance) for i in range(len(curves))],
        }
        if name:
            wire_kwargs["name"] = name

        result = cmds.wire(objects, **wire_kwargs)
        wire_node = result[0] if result else None

        return maya_success(
            "Created wire deformer '{}' on {} object(s)".format(wire_node, len(objects)),
            wire_node=wire_node,
            curves=list(curves),
            objects=list(objects),
            dropoff_distance=dropoff_distance,
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to create wire deformer")


def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`wire_deformer`."""
    return wire_deformer(**kwargs)


if __name__ == "__main__":
    import json

    result = wire_deformer()
    print(json.dumps(result))
