"""List all nodes connected to a material (textures, utilities, etc.)."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)

_SUPPORTED_SHADERS = ("lambert", "blinn", "phong", "phongE", "aiStandardSurface")


def get_material_connections(material_name: str) -> dict:
    """List all nodes connected to a material (textures, utilities, etc.).

    Returns the full set of incoming connections to every attribute on the
    material node, which lets an Agent understand the complete shading network.

    Args:
        material_name: Name of the material node to inspect.

    Returns:
        ActionResultModel dict with ``context.connections`` — a list of dicts
        with ``source_node``, ``source_attr``, ``dest_attr``, ``node_type``
        keys, and ``context.count``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(material_name):
            return error_result(
                "Material not found: {}".format(material_name),
                "'{}' does not exist in the scene".format(material_name),
            ).to_dict()

        # List all source plugs connected into this material
        raw_connections = (
            cmds.listConnections(
                material_name,
                source=True,
                destination=False,
                connections=True,
                plugs=True,
            )
            or []
        )

        # listConnections with connections=True returns pairs: [dest, src, dest, src, …]
        connections = []
        i = 0
        while i + 1 < len(raw_connections):
            dest_plug = raw_connections[i]
            src_plug = raw_connections[i + 1]
            # dest_plug is "material.attr"; src_plug is "node.attr"
            dest_attr = dest_plug.split(".", 1)[-1] if "." in dest_plug else dest_plug
            src_parts = src_plug.split(".", 1)
            src_node = src_parts[0]
            src_attr = src_parts[1] if len(src_parts) > 1 else ""
            node_type = cmds.nodeType(src_node) if cmds.objExists(src_node) else "unknown"
            connections.append(
                {
                    "source_node": src_node,
                    "source_attr": src_attr,
                    "dest_attr": dest_attr,
                    "node_type": node_type,
                }
            )
            i += 2

        return success_result(
            "Found {} connection(s) into material '{}'".format(len(connections), material_name),
            material_name=material_name,
            connections=connections,
            count=len(connections),
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("get_material_connections failed")
        return error_result("Failed to get connections for material '{}'".format(material_name), str(exc)).to_dict()


def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`get_material_connections`."""
    return get_material_connections(**kwargs)


if __name__ == "__main__":
    import json

    result = get_material_connections()
    print(json.dumps(result))
