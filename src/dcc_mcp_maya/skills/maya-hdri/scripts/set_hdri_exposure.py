"""Adjust the exposure of an HDRI / IBL dome node."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


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
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(light_node):
            return error_result(
                "Light node not found: {}".format(light_node),
                "Verify the node name with list_hdri_nodes",
            ).to_dict()

        # Resolve to shape if transform
        shapes = cmds.listRelatives(light_node, shapes=True) or []
        shape = shapes[0] if shapes else light_node
        node_type = cmds.objectType(shape)

        attr_set = ""
        if node_type == "aiSkyDomeLight" and cmds.attributeQuery("aiExposure", node=shape, exists=True):
            cmds.setAttr("{}.aiExposure".format(shape), exposure)
            attr_set = "{}.aiExposure".format(shape)
        elif cmds.attributeQuery("intensity", node=shape, exists=True):
            intensity = 2.0 ** exposure
            cmds.setAttr("{}.intensity".format(shape), intensity)
            attr_set = "{}.intensity (mapped from exposure)".format(shape)
        else:
            return error_result(
                "Cannot set exposure on node type: {}".format(node_type),
                "Only aiSkyDomeLight and standard lights are supported",
            ).to_dict()

        return success_result(
            "Exposure set to {} on '{}'".format(exposure, light_node),
            prompt="Use set_hdri_rotation to rotate the environment or list_hdri_nodes to inspect.",
            light_node=light_node,
            exposure=exposure,
            attribute_set=attr_set,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("set_hdri_exposure failed")
        return error_result("Failed to set HDRI exposure", str(exc)).to_dict()


def main(**kwargs):
    return set_hdri_exposure(**kwargs)


if __name__ == "__main__":
    import json

    print(json.dumps(set_hdri_exposure("hdriDome1", 1.0)))
