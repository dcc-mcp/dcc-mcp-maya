"""Add a wake / boat-wake effect locator to a Maya ocean surface."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import Optional

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success


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
            return skill_error(
                "Node not found",
                "oceanShader '{}' does not exist".format(shader),
            )

        locator_transform = cmds.spaceLocator(name="{}_wake_loc".format(shader))[0]
        cmds.setAttr("{}.waveHeightScale".format(shader), wake_size)

        if wake_object and cmds.objExists(wake_object):
            cmds.parentConstraint(wake_object, locator_transform, maintainOffset=False)

        return skill_success(
            "Ocean wake added",
            prompt=(
                "Wake locator '{}' created. Animate the locator to simulate a moving vessel.".format(locator_transform)
            ),
            wake_locator=locator_transform,
            shader=shader,
            wake_size=wake_size,
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to add ocean wake")


@skill_entry
def main(**kwargs):
    return add_ocean_wake(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main
    run_main(main)
