"""List attributes on a Maya node."""

# Import future modules
from __future__ import annotations

# Import built-in modules
# Import local modules
from dcc_mcp_core.skill import skill_entry, skill_error, skill_exception, skill_success


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
            return skill_error(
                "Node not found: {}".format(node_name),
                "'{}' does not exist".format(node_name),
            )

        kwargs = {}
        if user_defined_only:
            kwargs["userDefined"] = True
        if keyable_only:
            kwargs["keyable"] = True

        attrs = cmds.listAttr(node_name, **kwargs) or []

        return skill_success(
            "Found {} attribute(s) on '{}'".format(len(attrs), node_name),
            prompt="Use get_attribute or set_attribute to inspect or modify values.",
            node_name=node_name,
            attributes=attrs,
            count=len(attrs),
        )
    except ImportError:
        return skill_error("Maya not available", "maya.cmds could not be imported")
    except Exception as exc:
        return skill_exception(exc, message="Failed to list attributes")


@skill_entry
def main(**kwargs) -> dict:
    """Entry point; delegates to :func:`list_attributes`."""
    return list_attributes(**kwargs)


if __name__ == "__main__":
    from dcc_mcp_core.skill import run_main
    run_main(main)
