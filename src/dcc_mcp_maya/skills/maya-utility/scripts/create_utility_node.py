"""Create a Maya utility or shading network node by type."""

# Import future modules
from __future__ import annotations

# Import built-in modules
from typing import Optional

# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success


def create_utility_node(
    node_type: str,
    name: Optional[str] = None,
    connect_from: Optional[str] = None,
    connect_to_attr: str = "input1",
) -> dict:
    """Create a Maya utility or shading node of the given type.

    When *name* is provided, the node is first created without a name then
    renamed via ``cmds.rename`` so the final node bears exactly the requested
    name (consistent with how Round-3 tests mock the flow).

    Args:
        node_type: Maya node type (e.g. ``"multiplyDivide"``, ``"condition"``,
            ``"reverse"``, ``"clamp"``, ``"blendColors"``, ``"remapValue"``).
        name: Optional target node name.
        connect_from: Optional ``"node.attr"`` to connect into the new node's input.
        connect_to_attr: Attribute on the new node to receive the connection.
            Default ``"input1"``.

    Returns:
        ActionResultModel dict with ``context.node_name`` and ``context.node_type``.
    """

    if not node_type:
        return skill_error("No node_type provided", "Provide a valid Maya node type string.")

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        node = cmds.shadingNode(node_type, asUtility=True)

        if name:
            node = cmds.rename(node, name)

        if connect_from:
            dest = "{}.{}".format(node, connect_to_attr)
            cmds.connectAttr(connect_from, dest, force=True)

        return skill_success(
            "Created utility node: {}".format(node),
            prompt=(
                "Node '{}' created. Use set_material_attribute or connectAttr to wire it into your shading network."
            ).format(node),
            node_name=node,
            node_type=node_type,
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to create utility node")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`create_utility_node`."""
    return create_utility_node(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main

    run_main(main)
