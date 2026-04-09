"""Add a target mesh to an existing blend shape deformer."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def blend_shape_add_target(
    blend_shape: str,
    target_mesh: str,
    weight: float = 0.0,
    index: Optional[int] = None,
) -> dict:
    """Add a target mesh to an existing blend shape deformer.

    Args:
        blend_shape: Name of the blendShape node to modify.
        target_mesh: Name of the mesh to use as the new blend shape target.
        weight: Initial weight value for the new target (0.0–1.0).
            Default: 0.0.
        index: Target index slot.  If None, Maya assigns the next available
            index automatically.

    Returns:
        ActionResultModel dict with ``context.blend_shape``,
        ``context.target_mesh``, ``context.target_index``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    if not (0.0 <= weight <= 1.0):
        return error_result(
            "Invalid weight: {}".format(weight),
            "weight must be between 0.0 and 1.0",
        ).to_dict()

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(blend_shape):
            return error_result("Blend shape not found: {}".format(blend_shape)).to_dict()

        node_type = cmds.objectType(blend_shape)
        if node_type != "blendShape":
            return error_result("'{}' is not a blendShape node (type: {})".format(blend_shape, node_type)).to_dict()

        if not cmds.objExists(target_mesh):
            return error_result("Target mesh not found: {}".format(target_mesh)).to_dict()

        # Determine target index
        if index is None:
            existing = cmds.blendShape(blend_shape, query=True, weightCount=True) or 0
            target_index = int(existing)
        else:
            target_index = int(index)

        cmds.blendShape(
            blend_shape,
            edit=True,
            target=(
                cmds.blendShape(blend_shape, query=True, geometry=True)[0],
                target_index,
                target_mesh,
                weight,
            ),
        )

        return success_result(
            "Added target '{}' to blend shape '{}' at index {}".format(target_mesh, blend_shape, target_index),
            blend_shape=blend_shape,
            target_mesh=target_mesh,
            target_index=target_index,
            weight=weight,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("blend_shape_add_target failed")
        return error_result("Failed to add blend shape target", str(exc)).to_dict()


def main(**kwargs):
    return blend_shape_add_target(**kwargs)


if __name__ == "__main__":
    import json

    result = blend_shape_add_target()
    print(json.dumps(result))
