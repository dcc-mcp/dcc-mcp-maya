"""Adjust the exposure of an HDRI / IBL dome node."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success


def set_hdri_exposure(
    light_node: str,
    exposure: float,
) -> dict:
    """Set the exposure value on an Arnold aiSkyDomeLight or native light.

    For Arnold ``aiSkyDomeLight`` nodes the ``aiExposure`` attribute is used;
    for native lights the ``intensity`` attribute is mapped from the exposure
    value (``intensity = 2 ** exposure``).

    Args:
        light_node: Name of the dome light transform or shape.
        exposure: Exposure value in stops.  Negative values darken; positive brighten.

    Returns:
        ActionResultModel dict with ``light_node``, ``exposure``, ``attribute_set``.
    """
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(light_node):
            return skill_error(
                "Light node not found: {}".format(light_node),
                "Verify the node name with list_hdri_nodes",
            )

        # Resolve to shape if transform
        shapes = cmds.listRelatives(light_node, shapes=True) or []
        shape = shapes[0] if shapes else light_node
        node_type = cmds.objectType(shape)

        attr_set = ""
        if node_type == "aiSkyDomeLight" and cmds.attributeQuery("aiExposure", node=shape, exists=True):
            cmds.setAttr("{}.aiExposure".format(shape), exposure)
            attr_set = "{}.aiExposure".format(shape)
        elif cmds.attributeQuery("intensity", node=shape, exists=True):
            intensity = 2.0**exposure
            cmds.setAttr("{}.intensity".format(shape), intensity)
            attr_set = "{}.intensity (mapped from exposure)".format(shape)
        else:
            return skill_error(
                "Cannot set exposure on node type: {}".format(node_type),
                "Only aiSkyDomeLight and standard lights are supported",
            )

        return skill_success(
            "Exposure set to {} on '{}'".format(exposure, light_node),
            prompt="Use set_hdri_rotation to rotate the environment or list_hdri_nodes to inspect.",
            light_node=light_node,
            exposure=exposure,
            attribute_set=attr_set,
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to set HDRI exposure")


@skill_entry
def main(**kwargs):
    return set_hdri_exposure(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main
    run_main(main)
