"""Add a wake / boat-wake effect locator to a Maya ocean surface."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import Optional


# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success


def add_ocean_wake(
    shader: str,
    wake_object: Optional[str] = None,
    wake_size: float = 1.0,
) -> dict:
    """Add an ocean wake locator connected to the ocean shader.

    Args:
        shader: Name of the oceanShader node.
        wake_object: Optional transform whose world position drives the wake.
        wake_size: Wake size multiplier (sets ``waveHeightScale``). Default ``1.0``.

    Returns:
        ActionResultModel dict with ``context.wake_locator``.
    """

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(shader):
            return maya_error(
                "Node not found",
                "oceanShader '{}' does not exist".format(shader),
            )

        locator_transform = cmds.spaceLocator(name="{}_wake_loc".format(shader))[0]
        cmds.setAttr("{}.waveHeightScale".format(shader), wake_size)

        if wake_object and cmds.objExists(wake_object):
            cmds.parentConstraint(wake_object, locator_transform, maintainOffset=False)

        return maya_success(
            "Ocean wake added",
            prompt=(
                "Wake locator '{}' created. Animate the locator to simulate a moving vessel.".format(locator_transform)
            ),
            wake_locator=locator_transform,
            shader=shader,
            wake_size=wake_size,
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to add ocean wake")


def main(**kwargs):
    return add_ocean_wake(**kwargs)


if __name__ == "__main__":
    import json

    result = add_ocean_wake("oceanShader1")
    print(json.dumps(result))
