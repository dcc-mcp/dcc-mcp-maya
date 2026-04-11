"""Add a target mesh to an existing blend shape deformer."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success

# Import built-in modules
from typing import Optional


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

    if not (0.0 <= weight <= 1.0):
        return maya_error(
            "Invalid weight: {}".format(weight),
            "weight must be between 0.0 and 1.0",
        )

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(blend_shape):
            return maya_error("Blend shape not found: {}".format(blend_shape))

        node_type = cmds.objectType(blend_shape)
        if node_type != "blendShape":
            return maya_error("'{}' is not a blendShape node (type: {})".format(blend_shape, node_type))

        if not cmds.objExists(target_mesh):
            return maya_error("Target mesh not found: {}".format(target_mesh))

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

        return maya_success(
            "Added target '{}' to blend shape '{}' at index {}".format(target_mesh, blend_shape, target_index),
            blend_shape=blend_shape,
            target_mesh=target_mesh,
            target_index=target_index,
            weight=weight,
            prompt="Check the result with list_rigging or use related actions to continue.",
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to add blend shape target")


def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`blend_shape_add_target`."""
    return blend_shape_add_target(**kwargs)


if __name__ == "__main__":
    import json

    result = blend_shape_add_target()
    print(json.dumps(result))
