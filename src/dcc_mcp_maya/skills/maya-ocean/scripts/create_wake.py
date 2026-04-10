"""Create a wake effect attached to a Maya ocean shader."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def create_wake(
    ocean_shader: str,
    object_name: Optional[str] = None,
    wake_intensity: float = 1.0,
) -> dict:
    """Create a wake effect driven by an object moving through an ocean surface.

    Uses Maya's ``oceanWake`` utility node to generate ripple/foam driven by
    an animated object. If no object is provided, a locator is created as a
    placeholder.

    Args:
        ocean_shader: Name of the oceanShader node to attach the wake to.
        object_name: Name of the animated object driving the wake (optional).
        wake_intensity: Intensity of the wake effect (0.0 – 10.0).

    Returns:
        ActionResultModel dict with ``context.wake_node`` and ``context.locator``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    if not ocean_shader:
        return error_result(
            "Missing required parameter 'ocean_shader'",
            "Provide the oceanShader node name.",
        ).to_dict()

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(ocean_shader):
            return error_result(
                "Ocean shader '{}' not found".format(ocean_shader),
                "Use list_oceans to find valid ocean names.",
            ).to_dict()

        node_type = cmds.objectType(ocean_shader)
        if node_type != "oceanShader":
            return error_result(
                "Node '{}' is not an oceanShader (got '{}')".format(ocean_shader, node_type),
                "Provide an oceanShader node name.",
            ).to_dict()

        driver = object_name
        locator = None
        if not driver:
            loc_result = cmds.spaceLocator(name="wakeDriver_loc")
            locator = loc_result[0] if isinstance(loc_result, (list, tuple)) else loc_result
            driver = locator

        # Create oceanWake node
        wake_node = cmds.createNode("oceanWake", name="oceanWake1")
        cmds.setAttr("{}.intensity".format(wake_node), wake_intensity)

        # Connect ocean shader time/phase attrs
        if cmds.attributeQuery("time", node=ocean_shader, exists=True):
            cmds.connectAttr(
                "{}.time".format(ocean_shader),
                "{}.time".format(wake_node),
                force=True,
            )

        return success_result(
            "Created wake '{}' on ocean '{}'".format(wake_node, ocean_shader),
            prompt=(
                "Wake node created. Animate '{}' to drive the wake pattern. "
                "Adjust intensity with set_ocean_attribute on the wake node.".format(driver)
            ),
            wake_node=wake_node,
            ocean_shader=ocean_shader,
            driver=driver,
            locator=locator,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("create_wake failed")
        return error_result("Failed to create wake", str(exc)).to_dict()


def main(**kwargs) -> dict:
    return create_wake(**kwargs)


if __name__ == "__main__":
    import json

    print(json.dumps(create_wake(ocean_shader="oceanShader1")))
