"""Create a wire deformer that deforms meshes along one or more NURBS curves."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


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
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    if not curves:
        return error_result(
            "No curves specified",
            "Provide at least one NURBS curve name in 'curves'",
        ).to_dict()
    if not objects:
        return error_result(
            "No objects specified",
            "Provide at least one mesh name in 'objects'",
        ).to_dict()

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        missing_curves = [c for c in curves if not cmds.objExists(c)]
        if missing_curves:
            return error_result(
                "Curve(s) not found: {}".format(", ".join(missing_curves)),
                "Ensure all curves exist in the scene",
            ).to_dict()

        missing_objects = [o for o in objects if not cmds.objExists(o)]
        if missing_objects:
            return error_result(
                "Object(s) not found: {}".format(", ".join(missing_objects)),
                "Ensure all objects exist in the scene",
            ).to_dict()

        wire_kwargs = {
            "wire": curves,
            "dropoffDistance": [(i, dropoff_distance) for i in range(len(curves))],
        }
        if name:
            wire_kwargs["name"] = name

        result = cmds.wire(objects, **wire_kwargs)
        wire_node = result[0] if result else None

        return success_result(
            "Created wire deformer '{}' on {} object(s)".format(wire_node, len(objects)),
            wire_node=wire_node,
            curves=list(curves),
            objects=list(objects),
            dropoff_distance=dropoff_distance,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("wire_deformer failed")
        return error_result("Failed to create wire deformer", str(exc)).to_dict()


def main(**kwargs):
    return wire_deformer(**kwargs)


if __name__ == "__main__":
    import json

    result = wire_deformer()
    print(json.dumps(result))
