"""Create any Maya utility or shading node by type."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def create_utility_node(
    node_type: str,
    name: Optional[str] = None,
) -> dict:
    """Create any Maya utility or shading node by type.

    This is a generic factory action that complements :func:`create_material`
    for cases where the Agent needs a specific utility node (e.g.
    ``multiplyDivide``, ``reverse``, ``condition``, ``remapValue``,
    ``blendColors``, ``samplerInfo``, etc.).

    Args:
        node_type: Maya node type string (e.g. ``"multiplyDivide"``,
            ``"condition"``, ``"reverse"``).
        name: Optional name for the created node.  When omitted Maya
            auto-generates one.

    Returns:
        ActionResultModel dict with ``context.node_name`` and
        ``context.node_type``.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not node_type or not node_type.strip():
            return error_result("Invalid node_type", "node_type must not be empty").to_dict()

        node = cmds.shadingNode(node_type, asUtility=True)

        if name and name.strip():
            node = cmds.rename(node, name)

        return success_result(
            "Created utility node '{}' of type '{}'".format(node, node_type),
            node_name=node,
            node_type=node_type,
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("create_utility_node failed")
        return error_result("Failed to create utility node of type '{}'".format(node_type), str(exc)).to_dict()


def main(**kwargs):
    return create_utility_node(**kwargs)


if __name__ == "__main__":
    import json

    result = create_utility_node()
    print(json.dumps(result))
