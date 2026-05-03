"""List all nodes connected to a material (textures, utilities, etc.)."""

# Import future modules
from __future__ import annotations

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success

from dcc_mcp_maya.api import validate_node_exists

_SUPPORTED_SHADERS = ("lambert", "blinn", "phong", "phongE", "aiStandardSurface")


def get_material_connections(material_name: str) -> dict:
    """List all nodes connected to a material (textures, utilities, etc.).

    Returns the full set of incoming connections to every attribute on the
    material node, which lets an Agent understand the complete shading network.

    Args:
        material_name: Name of the material node to inspect.

    Returns:
        ToolResult dict with ``context.connections`` — a list of dicts
        with ``source_node``, ``source_attr``, ``dest_attr``, ``node_type``
        keys, and ``context.count``.
    """
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        err = validate_node_exists(cmds, material_name)
        if err:
            return err

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

        return skill_success(
            "Found {} connection(s) into material '{}'".format(len(connections), material_name),
            material_name=material_name,
            connections=connections,
            count=len(connections),
            prompt="Use set_material_attribute to modify or assign_material to reassign.",
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to get connections for material '{}'".format(material_name))


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`get_material_connections`."""
    return get_material_connections(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
