"""List attributes on a Maya node."""

# Import future modules
from __future__ import annotations

# Import built-in modules

# Import local modules
from dcc_mcp_maya.api import maya_error, maya_from_exception, maya_success



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
    try:
        import maya.cmds as cmds  # noqa: PLC0415

        if not cmds.objExists(node_name):
            return maya_error(
                "Node not found: {}".format(node_name),
                "'{}' does not exist".format(node_name),
            )

        kwargs = {}
        if user_defined_only:
            kwargs["userDefined"] = True
        if keyable_only:
            kwargs["keyable"] = True

        attrs = cmds.listAttr(node_name, **kwargs) or []

        return maya_success(
            "Found {} attribute(s) on '{}'".format(len(attrs), node_name),
            prompt="Use get_attribute or set_attribute to inspect or modify values.",
            node_name=node_name,
            attributes=attrs,
            count=len(attrs),
        )
    except ImportError:
        return maya_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return maya_from_exception(exc, "Failed to list attributes")


def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`list_attributes`."""
    return list_attributes(**kwargs)


if __name__ == "__main__":
    import json

    result = list_attributes("pSphere1", keyable_only=True)
    print(json.dumps(result))
