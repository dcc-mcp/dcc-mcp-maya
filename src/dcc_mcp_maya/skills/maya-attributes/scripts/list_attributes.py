"""List attributes on a Maya node."""

# Import future modules
from __future__ import annotations

# Import built-in modules
import logging

logger = logging.getLogger(__name__)


def list_attributes(
    node_name: str,
    user_defined_only: bool = False,
    keyable_only: bool = False,
) -> dict:
    """List attributes on a Maya node.

    Args:
        node_name: Name of the Maya node.
        user_defined_only: If True, only return user-defined attributes.
        keyable_only: If True, only return keyable (channel-box) attributes.

    Returns:
        ActionResultModel dict with ``context.attributes`` list.
    """
    from dcc_mcp_core import error_result, success_result  # noqa: PLC0415

    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(node_name):
            return error_result(
                "Node not found: {}".format(node_name),
                "'{}' does not exist".format(node_name),
            ).to_dict()

        kwargs = {}
        if user_defined_only:
            kwargs["userDefined"] = True
        if keyable_only:
            kwargs["keyable"] = True

        attrs = cmds.listAttr(node_name, **kwargs) or []

        return success_result(
            "Found {} attribute(s) on '{}'".format(len(attrs), node_name),
            prompt="Use get_attribute or set_attribute to inspect or modify values.",
            node_name=node_name,
            attributes=attrs,
            count=len(attrs),
        ).to_dict()
    except ImportError:
        return error_result("Maya not available", "maya.cmds could not be imported").to_dict()
    except Exception as exc:
        logger.exception("list_attributes failed")
        return error_result("Failed to list attributes", str(exc)).to_dict()


def main(**kwargs):
    return list_attributes(**kwargs)


if __name__ == "__main__":
    import json

    result = list_attributes("pSphere1", keyable_only=True)
    print(json.dumps(result))
